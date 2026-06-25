import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
