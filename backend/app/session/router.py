import logging

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.session.service import SessionService
from app.terminal.manager import RuntimeManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions")


class SessionCreate(BaseModel):
    title: str
    shell: str = "/bin/bash"
    cwd: str | None = None
    cols: int = 80
    rows: int = 24


class SessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    shell: str
    cwd: str | None
    status: str
    cols: int
    rows: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sessions = await SessionService.list_user_sessions(db, user_id=current_user.id)
    return sessions


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await SessionService.create_session(
        db,
        user_id=current_user.id,
        title=body.title,
        shell=body.shell,
        cwd=body.cwd,
        cols=body.cols,
        rows=body.rows,
    )

    # Start the runtime for this session
    manager = RuntimeManager()
    try:
        await manager.create_runtime(
            session_id=session.id,
            shell=body.shell,
            cols=body.cols,
            rows=body.rows,
            cwd=body.cwd,
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
    return session


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
    return session


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
            await manager.create_runtime(
                session_id=session_id,
                shell=session.shell,
                cols=session.cols,
                rows=session.rows,
                cwd=session.cwd,
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
    return session
