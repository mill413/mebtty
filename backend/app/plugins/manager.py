import json

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plugin, utcnow


async def list_plugins(db: AsyncSession) -> list[Plugin]:
    result = await db.execute(select(Plugin).order_by(Plugin.builtin.desc(), Plugin.id))
    return list(result.scalars().all())


async def get_plugin_or_404(db: AsyncSession, plugin_id: str) -> Plugin:
    plugin = await db.get(Plugin, plugin_id)
    if plugin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found",
        )
    return plugin


async def enable_plugin(db: AsyncSession, plugin_id: str) -> Plugin:
    plugin = await get_plugin_or_404(db, plugin_id)
    plugin.status = "enabled"
    plugin.enabled_at = plugin.enabled_at or utcnow()
    await db.flush()
    return plugin


async def disable_plugin(db: AsyncSession, plugin_id: str) -> Plugin:
    plugin = await get_plugin_or_404(db, plugin_id)
    if plugin.builtin and plugin.id != "builtin.file-browser":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This built-in plugin is required as a fallback and cannot be disabled",
        )
    plugin.status = "disabled"
    await db.flush()
    return plugin


async def delete_plugin(db: AsyncSession, plugin_id: str) -> Plugin:
    plugin = await get_plugin_or_404(db, plugin_id)
    if plugin.builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in plugins cannot be deleted",
        )

    await db.delete(plugin)
    await db.flush()
    return plugin


def create_plugin_from_manifest(
    *,
    manifest: dict,
    install_path: str,
    source: str = "upload",
) -> Plugin:
    return Plugin(
        id=manifest["id"],
        name=manifest["name"],
        version=manifest["version"],
        type=manifest["type"],
        builtin=False,
        status="installed",
        source=source,
        install_path=install_path,
        manifest_json=json.dumps(manifest, separators=(",", ":"), sort_keys=True),
        permissions_json=json.dumps(manifest.get("permissions", []), separators=(",", ":")),
    )
