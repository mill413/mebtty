import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    avatar = Column(String(512), nullable=True)  # path to avatar file
    login_shell = Column(String(64), nullable=True)  # auto-detected login shell
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    command_logs = relationship("CommandLog", back_populates="user", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(256), default="", nullable=False)
    shell = Column(String(64), default="bash", nullable=False)
    runtime_type = Column(String(32), default="host", nullable=False)
    status = Column(
        String(16),
        default="created",
        nullable=False,
        index=True,
    )  # created / starting / running / detached / stopped / destroyed
    cols = Column(Integer, default=80, nullable=False)
    rows = Column(Integer, default=24, nullable=False)
    cwd = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="sessions")
    command_logs = relationship("CommandLog", back_populates="session", cascade="all, delete-orphan")


class CommandLog(Base):
    __tablename__ = "command_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    command = Column(Text, nullable=False)
    output = Column(Text, nullable=True)
    risk_level = Column(String(16), default="low", nullable=False)  # low / medium / high / critical
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    session = relationship("Session", back_populates="command_logs")
    user = relationship("User", back_populates="command_logs")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(128), nullable=False)
    resource = Column(String(256), nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="audit_events")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    theme_mode = Column(String(16), default="system", nullable=False)
    accent_color = Column(String(32), default="#7c3aed", nullable=False)
    tab_title_format = Column(String(256), default="{user}: {cwd}", nullable=False)
    sidebar_position = Column(String(16), default="right", nullable=False)
    session_timeout = Column(Integer, default=0, nullable=False)  # 0 = disabled, value in hours
    file_auto_save = Column(Boolean, default=True, nullable=False)
    file_show_line_numbers = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="settings")
