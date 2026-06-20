import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


def is_hex_color(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 7 or value[0] != "#":
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value[1:])


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

    @field_validator("theme_mode")
    @classmethod
    def validate_theme_mode(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in {"system", "dark", "light"}:
            raise ValueError("theme_mode must be one of: system, dark, light")
        return value

    @field_validator("accent_color")
    @classmethod
    def validate_accent_color(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not is_hex_color(value):
            raise ValueError("accent_color must be a 6-digit hex color")
        return value.lower() if value else value

    @field_validator("custom_theme")
    @classmethod
    def validate_custom_theme(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("custom_theme must be valid JSON") from exc

        if not isinstance(parsed, dict):
            raise ValueError("custom_theme must be a JSON object")

        allowed_modes = {"dark", "light"}
        allowed_keys = {"bg", "bgDeep", "surface", "surfaceHover", "overlay", "text", "subtext", "border", "accent"}

        for mode, palette in parsed.items():
            if mode not in allowed_modes:
                raise ValueError("custom_theme only supports dark and light palettes")
            if not isinstance(palette, dict):
                raise ValueError("custom_theme palettes must be JSON objects")

            for key, color in palette.items():
                if key not in allowed_keys:
                    raise ValueError(f"custom_theme contains unsupported color key: {key}")
                if not is_hex_color(color):
                    raise ValueError("custom_theme colors must be 6-digit hex colors")

        return json.dumps(parsed, separators=(",", ":"))


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
