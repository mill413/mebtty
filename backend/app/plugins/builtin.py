from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plugin, utcnow


BUILTIN_PLUGIN_MANIFESTS: list[dict[str, Any]] = [
    {
        "schema": "https://mebtty.dev/schemas/plugin.v1.json",
        "id": "builtin.file-browser",
        "name": "File Browser",
        "version": "1.0.0",
        "description": "Browse, preview, and edit files from the terminal workspace.",
        "author": "MebTTY",
        "license": "MIT",
        "mebtty": "builtin",
        "type": "file-provider",
        "entry": {"frontend": "builtin"},
        "permissions": [
            "ui.panel",
            "ui.settings",
            "filesystem.read",
            "filesystem.write",
            "filesystem.upload",
            "filesystem.download",
            "filesystem.delete",
        ],
        "contributes": {
            "panels": [
                {
                    "slot": "terminal.sidebar",
                    "id": "builtin.file-browser.panel",
                    "title": "Files",
                }
            ],
            "fileProviders": [
                {
                    "id": "builtin.local-files",
                    "label": "Local Files",
                    "capabilities": [
                        "browse",
                        "read",
                        "write",
                        "upload",
                        "download",
                        "mkdir",
                        "rename",
                        "delete",
                    ],
                }
            ],
        },
    },
    {
        "schema": "https://mebtty.dev/schemas/plugin.v1.json",
        "id": "builtin.catppuccin-theme",
        "name": "Default Theme",
        "version": "1.0.0",
        "description": "Built-in dark and light theme tokens.",
        "author": "MebTTY",
        "license": "MIT",
        "mebtty": "builtin",
        "type": "theme",
        "entry": {"frontend": "builtin"},
        "permissions": ["theme.provide", "ui.settings"],
        "contributes": {
            "themes": [
                {
                    "id": "default-custom",
                    "label": "Default",
                    "modes": {
                        "dark": {
                            "bg": "#1e1e2e",
                            "bgDeep": "#181825",
                            "surface": "#313244",
                            "surfaceHover": "#3b3d52",
                            "overlay": "#45475a",
                            "text": "#cdd6f4",
                            "subtext": "#a6adc8",
                            "border": "#585b70",
                            "accent": "#7c3aed",
                        },
                        "light": {
                            "bg": "#eff1f5",
                            "bgDeep": "#e6e9ef",
                            "surface": "#ccd0da",
                            "surfaceHover": "#bcc0cc",
                            "overlay": "#acb0be",
                            "text": "#4c4f69",
                            "subtext": "#6c6f85",
                            "border": "#9ca0b0",
                            "accent": "#7c3aed",
                        },
                    },
                }
            ]
        },
    },
    {
        "schema": "https://mebtty.dev/schemas/plugin.v1.json",
        "id": "builtin.catppuccin-icons",
        "name": "Catppuccin Icons",
        "version": "1.0.0",
        "description": "Built-in Catppuccin file and terminal icon pack.",
        "author": "MebTTY",
        "license": "MIT",
        "mebtty": "builtin",
        "type": "icon-pack",
        "entry": {"frontend": "builtin"},
        "permissions": ["icons.provide", "ui.settings"],
        "contributes": {
            "iconPacks": [
                {
                    "id": "catppuccin",
                    "label": "Catppuccin",
                    "assetsBase": "/catppuccin-icons",
                    "fallbackFile": "_file.svg",
                    "fallbackFolder": "folder.svg",
                }
            ]
        },
    },
]


async def ensure_builtin_plugins(db: AsyncSession) -> None:
    for manifest in BUILTIN_PLUGIN_MANIFESTS:
        plugin = await db.get(Plugin, manifest["id"])
        manifest_json = json.dumps(manifest, separators=(",", ":"), sort_keys=True)
        permissions_json = json.dumps(manifest["permissions"], separators=(",", ":"))

        if plugin is None:
            plugin = Plugin(
                id=manifest["id"],
                name=manifest["name"],
                version=manifest["version"],
                type=manifest["type"],
                builtin=True,
                status="enabled",
                source="builtin",
                install_path=None,
                manifest_json=manifest_json,
                permissions_json=permissions_json,
                enabled_at=utcnow(),
            )
            db.add(plugin)
            continue

        plugin.name = manifest["name"]
        plugin.version = manifest["version"]
        plugin.type = manifest["type"]
        plugin.builtin = True
        plugin.source = "builtin"
        plugin.install_path = None
        plugin.manifest_json = manifest_json
        plugin.permissions_json = permissions_json
        if plugin.status not in {"enabled", "disabled"}:
            plugin.status = "enabled"
            plugin.enabled_at = utcnow()

    await db.flush()
