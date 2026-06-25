import logging
import os
import pwd
import shutil

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.service import create_terminal_ws_token
from app.database import get_db
from app.local_users import (
    authenticate_local_user,
    resolve_local_user,
)
from app.session.service import SessionService
from app.terminal.manager import RuntimeManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions")


class SessionCreate(BaseModel):
    title: str
    shell: str = "/bin/bash"
    cwd: str | None = None
    local_user: str | None = None
    local_password: str | None = None
    cols: int = 80
    rows: int = 24


class SessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    shell: str
    local_user: str | None = None
    cwd: str | None
    status: str
    cols: int
    rows: int
    username: str = ""
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class TerminalWsTicketResponse(BaseModel):
    ticket: str
    expires_in: int


def _session_to_response(session) -> dict:
    """Convert a session ORM object to a response dict with username."""
    data = {c.key: getattr(session, c.key) for c in session.__table__.columns}
    data["username"] = session.local_user or _get_system_username_fallback()
    return data


def _get_system_username_fallback() -> str:
    try:
        import os

        return pwd.getpwuid(os.getuid()).pw_name
    except Exception:
        return "unknown"


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sessions = await SessionService.list_user_sessions(db, user_id=current_user.id)
    return [_session_to_response(s) for s in sessions]


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.local_user or not body.local_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Local username and password are required",
        )

    try:
        local_user = resolve_local_user(body.local_user)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        authenticated = authenticate_local_user(local_user.username, body.local_password)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid local username or password",
        )

    cwd = body.cwd or local_user.home
    shell = body.shell or local_user.shell

    session = await SessionService.create_session(
        db,
        user_id=current_user.id,
        title=body.title,
        shell=shell,
        local_user=local_user.username,
        cwd=cwd,
        cols=body.cols,
        rows=body.rows,
    )

    # Start the runtime for this session
    manager = RuntimeManager()
    try:
        await manager.create_runtime(
            session_id=session.id,
            shell=shell,
            cols=body.cols,
            rows=body.rows,
            cwd=cwd,
            local_user=local_user,
        )
        await SessionService.update_session_status(db, session.id, "running")
    except Exception as e:
        await SessionService.update_session_status(db, session.id, "error")
        logger.exception("Failed to start runtime for session '%s'", session.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start terminal: {str(e)}",
        )

    # Refresh to get updated status
    session = await SessionService.get_session(db, session.id)
    return _session_to_response(session)


@router.get("/shells")
async def list_available_shells(
    current_user=Depends(get_current_user),
):
    """Return list of shells available on the system."""

    SHELL_LABELS = {
        "bash": ("Bash", "$"),
        "zsh": ("Zsh", "%"),
        "fish": ("Fish", ">"),
        "sh": ("SH", "$"),
        "dash": ("Dash", "$"),
        "ksh": ("Ksh", "$"),
        "csh": ("Csh", "%"),
        "tcsh": ("Tcsh", "%"),
        "nu": ("Nushell", ">"),
    }

    # Shells that are not useful as interactive terminals
    NON_INTERACTIVE = {
        "rbash", "rshell", "false", "true", "nologin",
        "git-shell", "systemd-home-fallback-shell",
    }

    # Preferred ordering for common shells
    PREFERENCE = ["bash", "zsh", "fish", "nu", "sh", "dash", "ksh", "csh", "tcsh"]

    # Read /etc/shells for the system's registered shells
    system_shells = set()
    try:
        with open("/etc/shells", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    system_shells.add(line)
    except OSError:
        pass

    # Also check common shell paths via PATH
    for name in SHELL_LABELS:
        path = shutil.which(name)
        if path:
            system_shells.add(path)

    # Build the result list
    shells = []
    seen = set()
    for shell_path in sorted(system_shells):
        if shell_path in seen:
            continue
        # Verify the shell actually exists and is executable
        if not os.path.isfile(shell_path) or not os.access(shell_path, os.X_OK):
            continue

        name = os.path.basename(shell_path)
        if name in seen or name in NON_INTERACTIVE:
            continue
        seen.add(name)
        seen.add(shell_path)

        label, _ = SHELL_LABELS.get(name, (name.capitalize(), "$"))
        shells.append({"path": shell_path, "name": name, "label": label})

    # Sort by preference (common interactive shells first)
    def sort_key(s):
        try:
            return PREFERENCE.index(s["name"])
        except ValueError:
            return len(PREFERENCE)

    shells.sort(key=sort_key)

    # Ensure at least the user's default shell is listed
    default_shell = os.environ.get("SHELL", "/bin/sh")
    if not any(s["path"] == default_shell for s in shells):
        if os.path.isfile(default_shell) and os.access(default_shell, os.X_OK):
            name = os.path.basename(default_shell)
            if name not in NON_INTERACTIVE:
                label, _ = SHELL_LABELS.get(name, (name.capitalize(), "$"))
                shells.insert(0, {"path": default_shell, "name": name, "label": label})

    return shells


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await SessionService.get_session(db, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return _session_to_response(session)


@router.post("/{session_id}/ws-ticket", response_model=TerminalWsTicketResponse)
async def create_terminal_ws_ticket(
    session_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await SessionService.get_session(db, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    expires_in = 60
    return TerminalWsTicketResponse(
        ticket=create_terminal_ws_token(current_user.id, session_id, expires_in),
        expires_in=expires_in,
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await SessionService.get_session(db, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Destroy the runtime
    manager = RuntimeManager()
    await manager.destroy_runtime(session_id)

    # Delete the session record
    await SessionService.delete_session(db, session_id)


@router.post("/{session_id}/reconnect", response_model=SessionResponse)
async def reconnect_session(
    session_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await SessionService.get_session(db, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Check if the runtime is still alive
    manager = RuntimeManager()
    runtime = await manager.get_runtime(session_id)

    if runtime is not None and runtime.is_alive:
        await SessionService.update_session_status(db, session_id, "running")
        logger.info("Reconnected to existing runtime for session '%s'", session_id)
    else:
        # Runtime is dead, start a new one
        try:
            local_user = resolve_local_user(session.local_user)
            await manager.create_runtime(
                session_id=session_id,
                shell=session.shell,
                cols=session.cols,
                rows=session.rows,
                cwd=session.cwd,
                local_user=local_user,
            )
            await SessionService.update_session_status(db, session_id, "running")
            logger.info("Created new runtime for reconnected session '%s'", session_id)
        except Exception as e:
            await SessionService.update_session_status(db, session_id, "error")
            logger.exception(
                "Failed to restart runtime for session '%s'", session_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reconnect terminal: {str(e)}",
            )

    # Refresh to get updated status
    session = await SessionService.get_session(db, session_id)
    return _session_to_response(session)
