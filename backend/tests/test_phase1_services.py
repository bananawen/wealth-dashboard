import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.holding_service import HoldingService
from app.services.price_service import PriceQuote, PriceService


class Phase1ServiceCalculationTest(unittest.TestCase):
    def setUp(self):
        self.original_get_price_cached = PriceService.get_price_cached
        PriceService.get_price_cached = classmethod(
            lambda cls, symbol: PriceQuote(
                price=110.0,
                change_pct=10.0,
                exchange="US",
                currency="USD",
                source="test",
            )
        )

    def tearDown(self):
        PriceService.get_price_cached = self.original_get_price_cached

    def test_compute_holding_converts_market_value_and_day_change_to_twd(self):
        row = {
            "symbol": "AAPL",
            "shares": 2,
            "avg_cost": 100,
            "total_cost": 200,
            "currency": "USD",
        }
        holding = HoldingService.compute_holding(row, {"USD": 32.0, "TWD": 1.0})

        self.assertEqual(holding.market_value, 220.0)
        self.assertEqual(holding.market_value_twd, 7040.0)
        self.assertEqual(holding.total_cost_twd, 6400.0)
        self.assertEqual(holding.unrealized_gain_twd, 640.0)
        self.assertEqual(holding.day_change_twd, 704.0)


if __name__ == "__main__":
    unittest.main()
