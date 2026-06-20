import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# Import models so they're registered with Base.metadata before init_db
from app.models import User, Session, CommandLog, AuditEvent, UserSettings  # noqa: F401

from app.auth.router import router as auth_router
from app.session.router import router as session_router
from app.terminal.router import router as terminal_router
from app.audit.router import router as audit_router
from app.file.router import router as file_router
from app.settings.router import router as settings_router
from app.database import init_db, async_session_factory

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


async def cleanup_stale_sessions():
    """Mark sessions that were running/starting when server shut down as stopped."""
    from sqlalchemy import select
    from app.models import Session

    async with async_session_factory() as db:
        result = await db.execute(
            select(Session).where(Session.status.in_(["running", "starting", "created"]))
        )
        stale = result.scalars().all()
        for s in stale:
            s.status = "stopped"
        if stale:
            await db.commit()
            logger.info(f"Cleaned up {len(stale)} stale session(s)")


async def cleanup_expired_sessions():
    """Delete sessions that have been stopped/detached for too long based on user settings.

    NOTE: In production, this should run as a periodic background scheduler job.
    Currently runs once at startup for simplicity.
    """
    from sqlalchemy import select
    from datetime import datetime, timedelta, timezone
    from app.models import Session, UserSettings

    async with async_session_factory() as db:
        # Get all user settings with session_timeout > 0
        result = await db.execute(
            select(UserSettings).where(UserSettings.session_timeout > 0)
        )
        settings_list = result.scalars().all()

        now = datetime.now(timezone.utc)
        deleted_count = 0

        for user_settings in settings_list:
            timeout_hours = user_settings.session_timeout
            cutoff = now - timedelta(hours=timeout_hours)

            result = await db.execute(
                select(Session).where(
                    Session.user_id == user_settings.user_id,
                    Session.status.in_(["stopped", "detached", "error"]),
                    Session.updated_at < cutoff,
                )
            )
            expired = result.scalars().all()
            for s in expired:
                await db.delete(s)
                deleted_count += 1

        if deleted_count > 0:
            await db.commit()
            logger.info(f"Auto-deleted {deleted_count} expired session(s)")


async def migrate_db():
    """Add new columns to existing tables (SQLite does not support ALTER TABLE ADD COLUMN via SQLAlchemy)."""
    from sqlalchemy import text, inspect as sa_inspect
    from app.database import engine

    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(users)"))
        existing_columns = {row[1] for row in result.fetchall()}

        if "avatar" not in existing_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN avatar VARCHAR(512)"))
            logger.info("Migration: added 'avatar' column to users")

        if "login_shell" not in existing_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN login_shell VARCHAR(64)"))
            logger.info("Migration: added 'login_shell' column to users")

        result = await conn.execute(text("PRAGMA table_info(user_settings)"))
        settings_columns = {row[1] for row in result.fetchall()}

        if "file_auto_save" not in settings_columns:
            await conn.execute(text("ALTER TABLE user_settings ADD COLUMN file_auto_save BOOLEAN DEFAULT 1 NOT NULL"))
            logger.info("Migration: added 'file_auto_save' column to user_settings")

        if "file_show_line_numbers" not in settings_columns:
            await conn.execute(text("ALTER TABLE user_settings ADD COLUMN file_show_line_numbers BOOLEAN DEFAULT 0 NOT NULL"))
            logger.info("Migration: added 'file_show_line_numbers' column to user_settings")

        if "custom_theme_enabled" not in settings_columns:
            await conn.execute(text("ALTER TABLE user_settings ADD COLUMN custom_theme_enabled BOOLEAN DEFAULT 0 NOT NULL"))
            logger.info("Migration: added 'custom_theme_enabled' column to user_settings")

        if "custom_theme" not in settings_columns:
            await conn.execute(text("ALTER TABLE user_settings ADD COLUMN custom_theme TEXT DEFAULT '{}' NOT NULL"))
            logger.info("Migration: added 'custom_theme' column to user_settings")

        result = await conn.execute(text("PRAGMA table_info(sessions)"))
        session_columns = {row[1] for row in result.fetchall()}

        if "local_user" not in session_columns:
            await conn.execute(text("ALTER TABLE sessions ADD COLUMN local_user VARCHAR(64)"))
            logger.info("Migration: added 'local_user' column to sessions")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    await init_db()
    await migrate_db()
    await cleanup_stale_sessions()
    await cleanup_expired_sessions()
    logger.info("MebTTY started")
    yield
    logger.info("MebTTY shutting down")


app = FastAPI(
    title="MebTTY",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - applies to both HTTP and WebSocket
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(session_router)
app.include_router(terminal_router)
app.include_router(audit_router)
app.include_router(file_router)
app.include_router(settings_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# Serve frontend static files in production mode.
from app.config import settings as app_settings

STATIC_DIR = Path(app_settings.STATIC_DIR) if app_settings.STATIC_DIR else None
if STATIC_DIR is None or not STATIC_DIR.is_dir():
    # Auto-detect: relative path from backend/ or Docker path
    STATIC_DIR = Path(__file__).resolve().parent.parent / ".." / "frontend" / "dist"
if not STATIC_DIR.is_dir():
    STATIC_DIR = Path("/app/frontend/dist")

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Try to serve the exact static file first
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Fall back to index.html for SPA client-side routing
        return FileResponse(STATIC_DIR / "index.html")

    logger.info(f"Serving frontend from {STATIC_DIR}")
