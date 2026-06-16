import mimetypes
import os
import pathlib
import shutil
import uuid
from datetime import datetime, timezone

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings
from app.auth.dependencies import get_current_user
from app.auth.service import decode_token
from app.database import get_db
from app.models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/files", tags=["files"])

CHUNK_SIZE = 4 * 1024 * 1024  # 4MB
MAX_TEXT_FILE_SIZE = 2 * 1024 * 1024  # 2MB
TEXT_MIME_TYPES = {
    "application/javascript",
    "application/json",
    "application/toml",
    "application/xml",
    "application/x-sh",
    "application/x-yaml",
    "image/svg+xml",
}
TEXT_EXTENSIONS = {
    ".bashrc",
    ".conf",
    ".css",
    ".csv",
    ".env",
    ".fish",
    ".gitignore",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".log",
    ".lua",
    ".md",
    ".py",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
    ".zsh",
}


class FileWriteRequest(BaseModel):
    path: str
    content: str
    mtime: float | None = None


async def get_user_from_token_or_header(
    token: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get user from query param token or fall back to header auth."""
    if token:
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            token_type = payload.get("type")
            if user_id and token_type == "access":
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    return user
        except ValueError:
            pass
    raise HTTPException(status_code=401, detail="Authentication required")


def _user_upload_dir(user_id: str) -> pathlib.Path:
    return pathlib.Path(settings.UPLOAD_DIR) / str(user_id)


def _session_upload_dir(user_id: str, session_id: str) -> pathlib.Path:
    return _user_upload_dir(user_id) / session_id


def _validate_path(user_id: str, session_id: str, relative_path: str) -> pathlib.Path:
    """Resolve and validate that the requested path stays within the user's upload directory."""
    base = _user_upload_dir(user_id).resolve()
    target = (_session_upload_dir(user_id, session_id) / relative_path).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid path")
    return target


def _get_browse_root(user_id: str) -> pathlib.Path:
    """Get the root directory for file browsing."""
    # Default to user's home directory, or use configured root
    browse_root = os.environ.get("MEBTTY_BROWSE_ROOT", os.path.expanduser("~"))
    return pathlib.Path(browse_root).resolve()


def _validate_browse_path(user_id: str, path: str) -> pathlib.Path:
    """Resolve browse path. If path is absolute, use it directly; otherwise relative to browse root."""
    if path and path.startswith('/'):
        # Absolute path — resolve directly, rely on OS permissions
        target = pathlib.Path(path).resolve()
    else:
        # Empty or relative path — start from browse root
        root = _get_browse_root(user_id)
        target = (root / path).resolve() if path else root

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    # Basic security check: don't allow accessing paths outside the real filesystem root
    if not str(target).startswith('/'):
        raise HTTPException(status_code=400, detail="Invalid path")

    return target


def _guess_mime(path: pathlib.Path) -> str:
    return mimetypes.guess_type(str(path))[0] or "application/octet-stream"


def _is_probably_text_file(path: pathlib.Path) -> bool:
    mime = _guess_mime(path)
    if mime.startswith("text/") or mime in TEXT_MIME_TYPES:
        return True
    if path.suffix.lower() in TEXT_EXTENSIONS or path.name in TEXT_EXTENSIONS:
        return True
    try:
        with path.open("rb") as f:
            sample = f.read(4096)
    except OSError:
        return False
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _file_metadata(path: pathlib.Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "mime": _guess_mime(path),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


@router.post("/upload")
async def upload_file(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    dest_dir = _session_upload_dir(current_user.id, session_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    file_path = dest_dir / file.filename
    size = 0

    async with aiofiles.open(file_path, "wb") as f:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.MAX_UPLOAD_SIZE:
                await f.close()
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE} bytes",
                )
            await f.write(chunk)

    return {"filename": file.filename, "size": size}


@router.get("/download")
async def download_file(
    session_id: str = Query(...),
    path: str = Query(...),
    current_user=Depends(get_current_user),
):
    target = _validate_path(current_user.id, session_id, path)

    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(target),
        filename=target.name,
        media_type="application/octet-stream",
    )


@router.get("/list")
async def list_files(
    session_id: str = Query(...),
    current_user=Depends(get_current_user),
):
    session_dir = _session_upload_dir(current_user.id, session_id)

    if not session_dir.is_dir():
        return []

    files = []
    for entry in session_dir.iterdir():
        if entry.is_file():
            stat = entry.stat()
            files.append(
                {
                    "filename": entry.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )

    return files


@router.post("/upload-browse")
async def upload_to_browse_dir(
    target_dir: str = Form(""),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """Upload a file to a specific directory within the browse root."""
    dest = _validate_browse_path(current_user.id, target_dir)
    if not dest.is_dir():
        raise HTTPException(status_code=400, detail="Target directory does not exist")

    file_path = dest / file.filename
    size = 0

    async with aiofiles.open(file_path, "wb") as f:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.MAX_UPLOAD_SIZE:
                await f.close()
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE} bytes",
                )
            await f.write(chunk)

    return {"filename": file.filename, "size": size, "path": str(file_path)}


@router.get("/browse")
async def browse_directory(
    path: str = Query(""),
    show_hidden: bool = Query(False),
    current_user=Depends(get_current_user),
):
    """Browse directory contents with full metadata."""
    target = _validate_browse_path(current_user.id, path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Skip hidden files unless explicitly requested
            if not show_hidden and entry.name.startswith('.'):
                continue
            try:
                stat = entry.stat()
                accessible = True
                if entry.is_dir():
                    try:
                        # Try to list the directory to verify actual readability
                        next(os.scandir(entry), None)
                    except PermissionError:
                        accessible = False
                items.append({
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size if entry.is_file() else None,
                    "mime": _guess_mime(entry) if entry.is_file() else None,
                    "is_text": _is_probably_text_file(entry) if entry.is_file() else False,
                    "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    "permissions": oct(stat.st_mode)[-3:],
                    "accessible": accessible,
                })
            except (PermissionError, OSError):
                # Include inaccessible items with accessible=false
                items.append({
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                    "size": None,
                    "mime": None,
                    "is_text": False,
                    "modified": None,
                    "permissions": None,
                    "accessible": False,
                })
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    return {
        "path": str(target),
        "absolute_path": str(target),
        "parent": str(target.parent) if target != pathlib.Path("/") else None,
        "items": items,
    }


@router.get("/read")
async def read_text_file(
    path: str = Query(...),
    current_user=Depends(get_current_user),
):
    """Read a UTF-8 text file from the browse filesystem."""
    target = _validate_browse_path(current_user.id, path)

    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    stat = target.stat()
    if stat.st_size > MAX_TEXT_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File is too large to edit")

    if not _is_probably_text_file(target):
        raise HTTPException(status_code=415, detail="File is not a supported text file")

    try:
        async with aiofiles.open(target, "rb") as f:
            raw = await f.read()
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="Only UTF-8 text files can be edited")

    return {
        **_file_metadata(target),
        "encoding": "utf-8",
        "is_text": True,
        "content": content,
    }


@router.put("/write")
async def write_text_file(
    body: FileWriteRequest,
    current_user=Depends(get_current_user),
):
    """Write a UTF-8 text file from the browse filesystem."""
    target = _validate_browse_path(current_user.id, body.path)

    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    if not _is_probably_text_file(target):
        raise HTTPException(status_code=415, detail="File is not a supported text file")

    encoded = body.content.encode("utf-8")
    if len(encoded) > MAX_TEXT_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File is too large to edit")

    stat = target.stat()
    if body.mtime is not None and abs(stat.st_mtime - body.mtime) > 0.001:
        raise HTTPException(status_code=409, detail="File changed on disk")

    tmp_path = target.with_name(f".{target.name}.mebtty-{uuid.uuid4().hex}.tmp")
    try:
        async with aiofiles.open(tmp_path, "wb") as f:
            await f.write(encoded)
        os.chmod(tmp_path, stat.st_mode)
        os.replace(tmp_path, target)
    except PermissionError:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as e:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")

    return {
        **_file_metadata(target),
        "encoding": "utf-8",
        "is_text": True,
        "saved": True,
    }


@router.post("/mkdir")
async def create_directory(
    path: str = Form(""),
    name: str = Form(...),
    current_user=Depends(get_current_user),
):
    """Create a new directory."""
    target = _validate_browse_path(current_user.id, path)
    new_dir = (target / name).resolve()

    if new_dir.exists():
        raise HTTPException(status_code=409, detail="Directory already exists")

    try:
        new_dir.mkdir(parents=True, exist_ok=False)
        return {"path": str(new_dir), "created": True}
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to create directory: {str(e)}")


@router.post("/delete")
async def delete_file(
    path: str = Form(...),
    current_user=Depends(get_current_user),
):
    """Delete a file or directory."""
    target = _validate_browse_path(current_user.id, path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    try:
        if target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        return {"deleted": True}
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")


@router.post("/rename")
async def rename_file(
    path: str = Form(...),
    new_name: str = Form(...),
    current_user=Depends(get_current_user),
):
    """Rename a file or directory."""
    target = _validate_browse_path(current_user.id, path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    new_path = target.parent / new_name

    if new_path.exists():
        raise HTTPException(status_code=409, detail="Target already exists")

    try:
        target.rename(new_path)
        return {
            "old_path": path,
            "new_path": str(new_path),
            "renamed": True,
        }
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename: {str(e)}")


@router.get("/download-browse")
async def download_from_browse(
    path: str = Query(...),
    current_user: User = Depends(get_user_from_token_or_header),
):
    """Download a file from the browse directory."""
    target = _validate_browse_path(current_user.id, path)

    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(target),
        filename=target.name,
        media_type="application/octet-stream",
    )
