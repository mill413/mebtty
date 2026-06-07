import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Session

logger = logging.getLogger(__name__)


class SessionService:
    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: str,
        title: str,
        shell: str,
        cwd: str | None = None,
        cols: int = 80,
        rows: int = 24,
    ):

        session_id = str(uuid.uuid4())
        session = Session(
            id=session_id,
            user_id=user_id,
            title=title,
            shell=shell,
            cwd=cwd,
            cols=cols,
            rows=rows,
            status="created",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        logger.info(
            "Created session '%s' for user '%s' (shell=%s)", session_id, user_id, shell
        )
        return session

    @staticmethod
    async def get_session(db: AsyncSession, session_id: str):
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_user_sessions(db: AsyncSession, user_id: str) -> list:
        result = await db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_session_status(
        db: AsyncSession,
        session_id: str,
        status: str,
        cols: int | None = None,
        rows: int | None = None,
    ):
        session = await SessionService.get_session(db, session_id)
        if session is None:
            logger.warning("Session '%s' not found for status update", session_id)
            return None

        session.status = status
        if cols is not None:
            session.cols = cols
        if rows is not None:
            session.rows = rows
        session.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(session)
        logger.info("Updated session '%s' status to '%s'", session_id, status)
        return session

    @staticmethod
    async def delete_session(db: AsyncSession, session_id: str) -> bool:
        session = await SessionService.get_session(db, session_id)
        if session is None:
            return False

        await db.delete(session)
        await db.commit()
        logger.info("Deleted session '%s'", session_id)
        return True
