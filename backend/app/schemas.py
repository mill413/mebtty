from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---- User ----

class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    is_active: bool
    is_admin: bool
    avatar: Optional[str] = None
    login_shell: Optional[str] = None
    created_at: datetime


# ---- Auth ----

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ---- Session ----

class SessionCreate(BaseModel):
    title: str = ""
    shell: str = "bash"
    cwd: Optional[str] = None
    local_user: Optional[str] = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    shell: str
    local_user: Optional[str] = None
    runtime_type: str
    status: str
    cols: int
    rows: int
    created_at: datetime
    updated_at: datetime


# ---- Command Log ----

class CommandLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    command: str
    risk_level: str
    created_at: datetime


# ---- User Settings ----

class UserSettingsUpdate(BaseModel):
    theme_mode: Optional[str] = None
    accent_color: Optional[str] = None
    custom_theme_enabled: Optional[bool] = None
    custom_theme: Optional[str] = None
    tab_title_format: Optional[str] = None
    sidebar_position: Optional[str] = None
    session_timeout: Optional[int] = None
    file_auto_save: Optional[bool] = None
    file_show_line_numbers: Optional[bool] = None


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme_mode: str
    accent_color: str
    custom_theme_enabled: bool
    custom_theme: str
    tab_title_format: str
    sidebar_position: str
    session_timeout: int
    file_auto_save: bool
    file_show_line_numbers: bool


class PasswordChange(BaseModel):
    old_password: str
    new_password: str
