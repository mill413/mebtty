import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Plugin, utcnow
from app.plugins.manager import create_plugin_from_manifest
from app.plugins.manifest import PLUGIN_PACKAGE_SUFFIX, load_manifest

MAX_PLUGIN_FILES = 1000


def _replace_tree(source: Path, target: Path) -> None:
    staging = target.with_name(f".{target.name}.tmp")
    shutil.rmtree(staging, ignore_errors=True)
    shutil.copytree(source, staging)
    if target.exists():
        shutil.rmtree(target)
    staging.replace(target)


def _update_plugin_from_manifest(plugin: Plugin, manifest: dict, install_path: str) -> Plugin:
    plugin.name = manifest["name"]
    plugin.version = manifest["version"]
    plugin.type = manifest["type"]
    plugin.source = "upload"
    plugin.install_path = install_path
    plugin.manifest_json = json.dumps(manifest, separators=(",", ":"), sort_keys=True)
    plugin.permissions_json = json.dumps(manifest.get("permissions", []), separators=(",", ":"))
    plugin.updated_at = utcnow()
    if plugin.status not in {"enabled", "disabled", "installed", "error"}:
        plugin.status = "installed"
    return plugin


def _safe_zip_members(package: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = package.infolist()
    if len(members) > MAX_PLUGIN_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plugin package contains too many files. Maximum is {MAX_PLUGIN_FILES}",
        )

    for member in members:
        name = member.filename
        path = Path(name)
        if name.startswith("/") or ".." in path.parts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plugin package contains unsafe paths",
            )

    return members


def _extract_plugin_package(package_path: Path, target_dir: Path) -> None:
    if not zipfile.is_zipfile(package_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plugin package must be a zip archive with .mtpx extension",
        )

    with zipfile.ZipFile(package_path) as package:
        _safe_zip_members(package)
        package.extractall(target_dir)


async def _save_upload(upload: UploadFile, target: Path) -> int:
    size = 0
    with target.open("wb") as f:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.PLUGIN_MAX_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Plugin package is too large. Maximum is {settings.PLUGIN_MAX_SIZE} bytes",
                )
            f.write(chunk)
    return size


async def install_plugin_package(
    db: AsyncSession,
    upload: UploadFile,
) -> Plugin:
    if not settings.PLUGIN_INSTALL_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plugin installation is disabled",
        )

    filename = upload.filename or ""
    if not filename.endswith(PLUGIN_PACKAGE_SUFFIX):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plugin package must use the .mtpx extension",
        )

    with tempfile.TemporaryDirectory(prefix="mebtty-plugin-") as tmp:
        tmp_dir = Path(tmp)
        package_path = tmp_dir / filename
        extract_dir = tmp_dir / "extract"
        extract_dir.mkdir()

        await _save_upload(upload, package_path)
        _extract_plugin_package(package_path, extract_dir)

        manifest_path = extract_dir / "mebtty.plugin.json"
        if not manifest_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plugin package must contain mebtty.plugin.json",
            )

        try:
            manifest = load_manifest(manifest_path.read_bytes())
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        install_dir = Path(settings.PLUGIN_DIR).resolve() / manifest.id / manifest.version
        install_dir.parent.mkdir(parents=True, exist_ok=True)
        existing = await db.get(Plugin, manifest.id)

        if existing is not None and existing.builtin:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Built-in plugins cannot be replaced",
            )

        previous_install_path = Path(existing.install_path).resolve() if existing and existing.install_path else None
        _replace_tree(extract_dir, install_dir)

        manifest_data = manifest.model_dump(by_alias=True)
        if existing is None:
            plugin = create_plugin_from_manifest(
                manifest=manifest_data,
                install_path=str(install_dir),
            )
            db.add(plugin)
        else:
            plugin = _update_plugin_from_manifest(existing, manifest_data, str(install_dir))
            if previous_install_path and previous_install_path != install_dir and previous_install_path.exists():
                shutil.rmtree(previous_install_path, ignore_errors=True)
        await db.flush()
        return plugin
