import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Plugin
from app.plugins.manager import create_plugin_from_manifest
from app.plugins.manifest import PLUGIN_PACKAGE_SUFFIX, load_manifest

MAX_PLUGIN_FILES = 1000


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

        existing = await db.get(Plugin, manifest.id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Plugin is already installed",
            )

        install_dir = Path(settings.PLUGIN_DIR).resolve() / manifest.id / manifest.version
        if install_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Plugin version is already installed on disk",
            )

        install_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(extract_dir, install_dir)

        plugin = create_plugin_from_manifest(
            manifest=manifest.model_dump(by_alias=True),
            install_path=str(install_dir),
        )
        db.add(plugin)
        await db.flush()
        return plugin
