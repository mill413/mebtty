import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.audit.router import list_user_events


class AuditAccessTest(unittest.IsolatedAsyncioTestCase):
    async def test_non_admin_cannot_read_other_user_events(self):
        current_user = SimpleNamespace(id="user-1", is_admin=False)

        with self.assertRaises(HTTPException) as raised:
            await list_user_events(
                user_id="user-2",
                db=None,
                current_user=current_user,
            )

        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
