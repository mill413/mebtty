import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.auth.service import create_terminal_ws_token
from app.models import Session, User
from app.terminal.ws_handler import _authorize_terminal_ws


class _FakeDb:
    def __init__(self, session=None, user=None):
        self.session = session
        self.user = user

    async def get(self, model, object_id):
        if model is Session:
            return self.session if self.session and self.session.id == object_id else None
        if model is User:
            return self.user if self.user and self.user.id == object_id else None
        return None


class _FakeSessionFactory:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        return False


class TerminalWebSocketAuthTest(unittest.IsolatedAsyncioTestCase):
    async def test_missing_ticket_is_rejected(self):
        self.assertFalse(await _authorize_terminal_ws("session-1", None))

    async def test_ticket_session_mismatch_is_rejected(self):
        ticket = create_terminal_ws_token("user-1", "session-1")

        self.assertFalse(await _authorize_terminal_ws("session-2", ticket))

    async def test_ticket_requires_session_owner(self):
        ticket = create_terminal_ws_token("user-1", "session-1")
        db = _FakeDb(
            session=SimpleNamespace(id="session-1", user_id="user-2"),
            user=SimpleNamespace(id="user-1", is_active=True),
        )

        with patch("app.terminal.ws_handler.async_session_factory", return_value=_FakeSessionFactory(db)):
            self.assertFalse(await _authorize_terminal_ws("session-1", ticket))

    async def test_valid_ticket_for_active_owner_is_allowed(self):
        ticket = create_terminal_ws_token("user-1", "session-1")
        db = _FakeDb(
            session=SimpleNamespace(id="session-1", user_id="user-1"),
            user=SimpleNamespace(id="user-1", is_active=True),
        )

        with patch("app.terminal.ws_handler.async_session_factory", return_value=_FakeSessionFactory(db)):
            self.assertTrue(await _authorize_terminal_ws("session-1", ticket))


if __name__ == "__main__":
    unittest.main()
