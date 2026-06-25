import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.file import router


class _FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeDb:
    def __init__(self, local_username):
        self.local_username = local_username
        self.executed = False

    async def execute(self, query):
        self.executed = True
        return _FakeResult(self.local_username)


class BrowseRootTest(unittest.IsolatedAsyncioTestCase):
    async def test_configured_browse_root_wins(self):
        db = _FakeDb("haruto")

        with patch.dict(os.environ, {"MEBTTY_BROWSE_ROOT": "/tmp"}, clear=False):
            root = await router._get_browse_root("user-id", db)

        self.assertEqual(str(root), "/tmp")
        self.assertFalse(db.executed)

    async def test_recent_local_session_user_home_is_default_root(self):
        db = _FakeDb("haruto")

        with (
            patch.dict(os.environ, {"HOME": "/var/lib/mebtty"}, clear=False),
            patch.object(
                router,
                "resolve_local_user",
                return_value=SimpleNamespace(home="/home/haruto"),
            ),
        ):
            os.environ.pop("MEBTTY_BROWSE_ROOT", None)
            root = await router._get_browse_root("user-id", db)

        self.assertEqual(str(root), "/home/haruto")
        self.assertTrue(db.executed)

    async def test_process_home_is_fallback_without_local_session(self):
        db = _FakeDb(None)

        with patch.dict(os.environ, {"HOME": "/var/lib/mebtty"}, clear=False):
            os.environ.pop("MEBTTY_BROWSE_ROOT", None)
            root = await router._get_browse_root("user-id", db)

        self.assertEqual(str(root), "/var/lib/mebtty")
        self.assertTrue(db.executed)

    async def test_browse_path_allows_paths_inside_root(self):
        db = _FakeDb(None)

        with tempfile.TemporaryDirectory() as root:
            nested = Path(root) / "nested"
            nested.mkdir()
            with patch.dict(os.environ, {"MEBTTY_BROWSE_ROOT": root}, clear=False):
                target = await router._validate_browse_path("user-id", "nested", db)

        self.assertEqual(target, nested.resolve())

    async def test_browse_path_treats_slash_as_browse_root(self):
        db = _FakeDb(None)

        with tempfile.TemporaryDirectory() as root:
            with patch.dict(os.environ, {"MEBTTY_BROWSE_ROOT": root}, clear=False):
                target = await router._validate_browse_path("user-id", "/", db)

        self.assertEqual(target, Path(root).resolve())

    async def test_browse_path_rejects_absolute_path_outside_root(self):
        db = _FakeDb(None)

        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            with patch.dict(os.environ, {"MEBTTY_BROWSE_ROOT": root}, clear=False):
                with self.assertRaises(HTTPException) as raised:
                    await router._validate_browse_path("user-id", outside, db)

        self.assertEqual(raised.exception.status_code, 403)

    async def test_browse_path_rejects_relative_escape(self):
        db = _FakeDb(None)

        with tempfile.TemporaryDirectory() as root:
            sibling = Path(root).parent / f"{Path(root).name}-sibling"
            sibling.mkdir()
            with patch.dict(os.environ, {"MEBTTY_BROWSE_ROOT": root}, clear=False):
                try:
                    with self.assertRaises(HTTPException) as raised:
                        await router._validate_browse_path("user-id", f"../{sibling.name}", db)
                finally:
                    sibling.rmdir()

        self.assertEqual(raised.exception.status_code, 403)

    def test_child_name_rejects_path_segments(self):
        for value in ("../evil", "a/b", "a\\b", ".", "..", ""):
            with self.subTest(value=value):
                with self.assertRaises(HTTPException):
                    router._validate_child_name(value)


if __name__ == "__main__":
    unittest.main()
