import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import BACKEND_DIR, SQLITE_SCHEMA, _sqlite_path, is_sqlite_url


class SQLiteDatabaseConfigTest(unittest.TestCase):
    def test_sqlite_url_detection(self):
        self.assertTrue(is_sqlite_url("sqlite:///./wealth.db"))
        self.assertFalse(is_sqlite_url("postgresql://localhost/db"))

    def test_relative_sqlite_path_is_backend_relative(self):
        self.assertEqual(_sqlite_path("sqlite:///./wealth.db"), BACKEND_DIR / "wealth.db")

    def test_sqlite_schema_is_accountless(self):
        self.assertNotIn("CREATE TABLE IF NOT EXISTS accounts", SQLITE_SCHEMA)
        self.assertNotIn("account_id INTEGER", SQLITE_SCHEMA)


if __name__ == "__main__":
    unittest.main()
