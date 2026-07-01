import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.holding_projection_service import HoldingProjectionService


class FakeCursor:
    def __init__(self):
        self.calls = []
        self.fetchall_results = [
            [{"currency": "USD", "rate_to_twd": 32.0}],
            [
                {
                    "total_bought": 10,
                    "total_cost": 1000,
                    "total_sold": 4,
                    "currency": "USD",
                }
            ],
        ]

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.fetchall_results.pop(0)


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()

    def cursor(self):
        return self.cursor_obj


class Phase2ProjectionTest(unittest.TestCase):
    def test_recompute_holding_projects_remaining_position_from_transactions(self):
        conn = FakeConnection()

        HoldingProjectionService.recompute_holding(conn, "AAPL", 5)

        insert_call = conn.cursor_obj.calls[-1]
        self.assertIn("INSERT INTO holdings", insert_call[0])
        self.assertEqual(insert_call[1], ("AAPL", 6.0, 100.0, 600.0, "USD", 19200.0, 5))


if __name__ == "__main__":
    unittest.main()
