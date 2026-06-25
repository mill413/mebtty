import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.models import Plugin
from app.plugins.installer import install_plugin_package
from app.plugins.manifest import load_manifest


def _manifest(**overrides):
    data = {
        "schema": "https://mebtty.dev/schemas/plugin.v1.json",
        "id": "test.git-tools",
        "name": "Git Tools",
        "version": "1.0.0",
        "description": "Test plugin",
        "author": "MebTTY",
        "license": "MIT",
        "mebtty": ">=0.1.0",
        "type": "panel",
        "entry": {"frontend": "frontend/main.js"},
        "permissions": ["ui.panel"],
        "contributes": {"panels": [{"id": "git", "title": "Git"}]},
    }
    data.update(overrides)
    return data


def _package(files: dict[str, bytes | str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            archive.writestr(name, content)
    return buffer.getvalue()


class FakeUpload:
    def __init__(self, filename: str, data: bytes):
        self.filename = filename
        self._stream = io.BytesIO(data)

    async def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)


class FakeDb:
    def __init__(self, existing: Plugin | None = None):
        self.existing = existing
        self.added = None
        self.flushed = False

    async def get(self, model, plugin_id):
        return self.existing if plugin_id == getattr(self.existing, "id", None) else None

    def add(self, plugin):
        self.added = plugin

    async def flush(self):
        self.flushed = True


class PluginSecurityTest(unittest.IsolatedAsyncioTestCase):
    async def test_installs_valid_minimal_package(self):
        package = _package(
            {
                "mebtty.plugin.json": json.dumps(_manifest()),
                "frontend/main.js": "export function activate() {}",
            }
        )

        with tempfile.TemporaryDirectory() as plugin_dir:
            with patch("app.plugins.installer.settings.PLUGIN_DIR", plugin_dir):
                plugin = await install_plugin_package(
                    FakeDb(),
                    FakeUpload("git-tools.mtpx", package),
                )
                self.assertTrue(Path(plugin.install_path, "frontend/main.js").is_file())

        self.assertEqual(plugin.id, "test.git-tools")
        self.assertEqual(plugin.status, "installed")

    async def test_rejects_unsafe_zip_member_paths(self):
        for member_name in ("../evil.txt", "frontend\\evil.js", "/absolute.js", "./dot.js"):
            with self.subTest(member_name=member_name):
                package = _package(
                    {
                        "mebtty.plugin.json": json.dumps(_manifest()),
                        member_name: "bad",
                    }
                )

                with tempfile.TemporaryDirectory() as plugin_dir:
                    with patch("app.plugins.installer.settings.PLUGIN_DIR", plugin_dir):
                        with self.assertRaises(HTTPException) as raised:
                            await install_plugin_package(
                                FakeDb(),
                                FakeUpload("bad.mtpx", package),
                            )

                self.assertEqual(raised.exception.status_code, 400)

    async def test_rejects_unsafe_frontend_entry(self):
        data = _manifest(entry={"frontend": "../outside.js"})

        with self.assertRaises(ValueError) as raised:
            load_manifest(json.dumps(data).encode("utf-8"))

        self.assertIn("safe relative paths", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
