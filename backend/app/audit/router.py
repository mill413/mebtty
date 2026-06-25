from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.audit.service import get_session_commands, get_user_events
from app.models import AuditEvent, Session

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/commands/{session_id}")
async def list_session_commands(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.is_admin:
        stmt_check = select(Session).where(Session.id == session_id)
        result = await db.execute(stmt_check)
        session_obj = result.scalar_one_or_none()
        if session_obj is None or str(session_obj.user_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

    commands = await get_session_commands(db, session_id, skip=skip, limit=limit)
    return commands


@router.get("/events")
async def list_audit_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    stmt = (
        select(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/events/{user_id}")
async def list_user_events(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.is_admin and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    events = await get_user_events(db, user_id, skip=skip, limit=limit)
    return events
