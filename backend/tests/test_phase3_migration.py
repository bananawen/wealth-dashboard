import unittest
from pathlib import Path


class Phase3MigrationTest(unittest.TestCase):
    def test_accountless_migration_contains_required_schema_contracts(self):
        migration = Path("backend/migrations/021_accountless_transactions_holdings.sql").read_text()

        self.assertIn("ADD COLUMN IF NOT EXISTS currency", migration)
        self.assertIn("ALTER COLUMN account_id DROP NOT NULL", migration)
        self.assertIn("ADD COLUMN IF NOT EXISTS total_cost_twd", migration)
        self.assertIn("DROP TRIGGER IF EXISTS block_holdings_write", migration)
        self.assertIn("UNIQUE (user_id, symbol)", migration)


if __name__ == "__main__":
    unittest.main()
