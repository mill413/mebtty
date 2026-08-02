import unittest

from pydantic import ValidationError

from app.schemas import UserSettingsUpdate


class SettingsSchemaTest(unittest.TestCase):
    def test_sidebar_mode_accepts_supported_values(self):
        for mode in ("docked", "overlay"):
            with self.subTest(mode=mode):
                settings = UserSettingsUpdate(sidebar_mode=mode)

                self.assertEqual(settings.sidebar_mode, mode)

    def test_sidebar_mode_rejects_unknown_values(self):
        with self.assertRaises(ValidationError):
            UserSettingsUpdate(sidebar_mode="floating")
