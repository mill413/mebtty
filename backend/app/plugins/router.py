from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.audit.service import log_event
from app.database import get_db
from app.models import Plugin, User
from app.plugins.installer import install_plugin_package
from app.plugins.manager import (
    delete_plugin,
    disable_plugin,
    enable_plugin,
    get_plugin_or_404,
    list_plugins,
)
from app.plugins.schemas import PluginActionResponse, PluginInstallResponse, PluginResponse

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


def resolve_plugin_asset(plugin: Plugin, asset_path: str) -> Path:
    if plugin.builtin or plugin.status != "enabled" or not plugin.install_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin asset not found")

    if not asset_path or asset_path.startswith(("/", "\\")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin asset not found")

    root = Path(plugin.install_path).resolve()
    asset = (root / asset_path).resolve()
    if asset != root and root not in asset.parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin asset not found")
    if not asset.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin asset not found")
    return asset


@router.get("", response_model=list[PluginResponse])
async def get_plugins(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_plugins(db)


@router.get("/{plugin_id}/assets/{asset_path:path}")
async def get_plugin_asset(
    plugin_id: str,
    asset_path: str,
    db: AsyncSession = Depends(get_db),
):
    plugin = await db.get(Plugin, plugin_id)
    if plugin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin asset not found")
    return FileResponse(resolve_plugin_asset(plugin, asset_path))


@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_plugin_or_404(db, plugin_id)


@router.post("/install", response_model=PluginInstallResponse, status_code=status.HTTP_201_CREATED)
async def install_plugin(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plugin = await install_plugin_package(db, file)
    await log_event(
        db,
        user_id=current_user.id,
        action="plugin.install",
        resource=plugin.id,
        detail=plugin.version,
    )
    return PluginInstallResponse(
        plugin=PluginResponse.model_validate(plugin),
        restart_required=False,
        enabled=False,
        permissions=PluginResponse.model_validate(plugin).permissions,
    )


@router.post("/{plugin_id}/enable", response_model=PluginActionResponse)
async def enable_plugin_endpoint(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plugin = await enable_plugin(db, plugin_id)
    await log_event(
        db,
        user_id=current_user.id,
        action="plugin.enable",
        resource=plugin.id,
        detail=plugin.version,
    )
    return PluginActionResponse(id=plugin.id, status=plugin.status)


@router.post("/{plugin_id}/disable", response_model=PluginActionResponse)
async def disable_plugin_endpoint(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plugin = await disable_plugin(db, plugin_id)
    await log_event(
        db,
        user_id=current_user.id,
        action="plugin.disable",
        resource=plugin.id,
        detail=plugin.version,
    )
    return PluginActionResponse(id=plugin.id, status=plugin.status)


@router.delete("/{plugin_id}", response_model=PluginActionResponse)
async def delete_plugin_endpoint(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plugin = await get_plugin_or_404(db, plugin_id)
    if plugin.builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in plugins cannot be deleted",
        )

    deleted = await delete_plugin(db, plugin_id)
    await log_event(
        db,
        user_id=current_user.id,
        action="plugin.delete",
        resource=deleted.id,
        detail=deleted.version,
    )
    return PluginActionResponse(id=deleted.id, status="deleted")
