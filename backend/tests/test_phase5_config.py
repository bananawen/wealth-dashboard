import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings
from app.routers.admin import router as admin_router


class Phase5ConfigSecurityTest(unittest.TestCase):
    def test_cors_origins_are_parsed_from_comma_separated_setting(self):
        settings = Settings(CORS_ORIGINS="http://localhost:3000, https://wealth.example.com ")

        self.assertEqual(
            settings.cors_origins_list,
            ["http://localhost:3000", "https://wealth.example.com"],
        )

    def test_default_scheduler_is_disabled(self):
        self.assertFalse(Settings().ENABLE_PRICE_SCHEDULER)

    def test_production_rejects_default_secret(self):
        with self.assertRaises(ValueError):
            Settings(ENVIRONMENT="production", SECRET_KEY="dev-secret-key-change-me")

    def test_admin_router_has_auth_dependency(self):
        self.assertGreaterEqual(len(admin_router.dependencies), 1)


if __name__ == "__main__":
    unittest.main()
