import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator


PLUGIN_PACKAGE_SUFFIX = ".mtpx"
PLUGIN_SCHEMA = "https://mebtty.dev/schemas/plugin.v1.json"
PLUGIN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]+$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")

ALLOWED_PERMISSIONS = {
    "ui.panel",
    "ui.toolbar",
    "ui.settings",
    "theme.provide",
    "icons.provide",
    "filesystem.read",
    "filesystem.write",
    "filesystem.delete",
    "filesystem.upload",
    "filesystem.download",
    "network.client",
    "terminal.read",
    "terminal.write",
}

ALLOWED_TYPES = {
    "theme",
    "icon-pack",
    "file-provider",
    "panel",
    "integration",
}


class PluginEntry(BaseModel):
    frontend: str | None = None
    backend: str | None = None


class PluginManifest(BaseModel):
    schema_: str = Field(alias="schema")
    id: str
    name: str
    version: str
    description: str | None = None
    author: str | None = None
    license: str | None = None
    mebtty: str
    type: Literal["theme", "icon-pack", "file-provider", "panel", "integration"]
    entry: PluginEntry | None = None
    permissions: list[str]
    contributes: dict[str, Any]

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not PLUGIN_ID_RE.match(value):
            raise ValueError("plugin id must contain only lowercase letters, numbers, dots, underscores, or hyphens")
        if value.startswith("builtin."):
            raise ValueError("third-party plugins cannot use the builtin.* namespace")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not SEMVER_RE.match(value):
            raise ValueError("plugin version must be SemVer")
        return value

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, value: list[str]) -> list[str]:
        unsupported = sorted(set(value) - ALLOWED_PERMISSIONS)
        if unsupported:
            raise ValueError(f"unsupported plugin permissions: {', '.join(unsupported)}")
        return value

    @field_validator("schema_")
    @classmethod
    def validate_schema(cls, value: str) -> str:
        if value != PLUGIN_SCHEMA:
            raise ValueError(f"plugin schema must be {PLUGIN_SCHEMA}")
        return value


def load_manifest(raw: bytes) -> PluginManifest:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("plugin manifest must be valid UTF-8 JSON") from exc

    try:
        return PluginManifest.model_validate(data)
    except ValidationError as exc:
        message = "; ".join(
            f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        raise ValueError(message) from exc
