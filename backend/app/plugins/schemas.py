import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, computed_field


class PluginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    type: str
    builtin: bool
    status: str
    source: str
    install_path: str | None = None
    manifest_json: str
    permissions_json: str
    installed_at: datetime
    enabled_at: datetime | None = None
    updated_at: datetime

    @computed_field
    @property
    def manifest(self) -> dict[str, Any]:
        return json.loads(self.manifest_json or "{}")

    @computed_field
    @property
    def permissions(self) -> list[str]:
        return json.loads(self.permissions_json or "[]")


class PluginInstallResponse(BaseModel):
    plugin: PluginResponse
    restart_required: bool = False
    enabled: bool = False
    permissions: list[str]


class PluginActionResponse(BaseModel):
    id: str
    status: str
    restart_required: bool = False
