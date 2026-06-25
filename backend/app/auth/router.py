import os
import pwd
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.rate_limit import (
    auth_rate_limit_key,
    check_auth_rate_limit,
    record_auth_failure,
    record_auth_success,
)
from app.auth.service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import settings as app_settings
from app.database import get_db
from app.models import User
from app.schemas import PasswordChange, TokenResponse, UserCreate, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def detect_login_shell() -> str:
    """Detect the current user's login shell."""
    try:
        shell = pwd.getpwuid(os.getuid()).pw_shell
        return shell if shell else "/bin/bash"
    except Exception:
        return os.environ.get("SHELL", "/bin/bash")


@router.get("/has-users")
async def has_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.count()).select_from(User))
    count = result.scalar_one()
    return {"has_users": count > 0, "registration_enabled": app_settings.REGISTRATION_ENABLED}


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    count_result = await db.execute(select(func.count()).select_from(User))
    user_count = count_result.scalar_one()

    # Block registration when disabled, but always allow first-time setup
    if not app_settings.REGISTRATION_ENABLED:
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration is disabled",
            )

    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        is_admin=user_count == 0,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    rate_limit_key = auth_rate_limit_key("web-login", body.username, request)
    check_auth_rate_limit(rate_limit_key)

    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        record_auth_failure(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    record_auth_success(rate_limit_key)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: dict, db: AsyncSession = Depends(get_db)):
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refresh_token is required",
        )

    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token = create_access_token({"sub": user.id})
    new_refresh_token = create_refresh_token({"sub": user.id})

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.login_shell is None:
        current_user.login_shell = detect_login_shell()
        await db.commit()
        await db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
    body: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    current_user.hashed_password = hash_password(body.new_password)
    await db.commit()
    return {"message": "Password changed successfully"}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate file type
    allowed_types = {"image/png", "image/jpeg", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG, JPEG, WebP, and GIF images are allowed")

    # Read file content
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:  # 2MB limit
        raise HTTPException(status_code=400, detail="File size must be under 2MB")

    # Determine file extension
    ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
    ext = ext_map.get(file.content_type, ".jpg")

    # Save file
    avatar_dir = Path(app_settings.UPLOAD_DIR) / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{current_user.id}{ext}"
    filepath = avatar_dir / filename

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    # Delete old avatar if exists
    if current_user.avatar:
        old_path = avatar_dir / current_user.avatar
        if old_path.exists():
            old_path.unlink()

    current_user.avatar = filename
    await db.commit()

    avatar_url = f"/api/auth/avatar/{filename}"
    return {"avatar_url": avatar_url}


@router.get("/avatar/{filename}")
async def get_avatar(filename: str):
    avatar_dir = Path(app_settings.UPLOAD_DIR) / "avatars"
    filepath = avatar_dir / filename
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="Avatar not found")
    return FileResponse(filepath)
