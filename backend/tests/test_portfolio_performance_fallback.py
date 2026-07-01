import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import PortfolioSummary
from app.services import portfolio_service
from app.services.portfolio_service import PortfolioService


class _FakeCursor:
    def __init__(self, price_rows_by_symbol):
        self.price_rows_by_symbol = price_rows_by_symbol
        self.current_symbol = None

    def execute(self, sql, params):
        self.current_symbol = params[0]

    def fetchall(self):
        return self.price_rows_by_symbol.get(self.current_symbol, [])


class _FakeConn:
    def __init__(self, price_rows_by_symbol):
        self.price_rows_by_symbol = price_rows_by_symbol

    def cursor(self):
        return _FakeCursor(self.price_rows_by_symbol)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class PortfolioPerformanceFallbackTest(unittest.TestCase):
    def setUp(self):
        self.original_get_db = portfolio_service.get_db
        self.original_get_history_rows = PortfolioService._get_history_rows
        self.original_get_transaction_rows = PortfolioService._get_transaction_rows
        self.original_get_summary = PortfolioService.get_summary
        self.original_load_rates = portfolio_service.FxService.load_rates
        self.original_normalize_symbol = portfolio_service.MarketService.normalize_symbol
        self.original_get_symbol_profile = portfolio_service.MarketService.get_symbol_profile
        self.original_get_benchmark_series = PortfolioService._get_benchmark_series

    def tearDown(self):
        portfolio_service.get_db = self.original_get_db
        PortfolioService._get_history_rows = self.original_get_history_rows
        PortfolioService._get_transaction_rows = self.original_get_transaction_rows
        PortfolioService.get_summary = self.original_get_summary
        portfolio_service.FxService.load_rates = self.original_load_rates
        portfolio_service.MarketService.normalize_symbol = self.original_normalize_symbol
        portfolio_service.MarketService.get_symbol_profile = self.original_get_symbol_profile
        PortfolioService._get_benchmark_series = self.original_get_benchmark_series

    def test_get_performance_rebuilds_series_from_transactions_when_snapshots_missing(self):
        PortfolioService._get_history_rows = staticmethod(lambda user_id, start_date=None: [])
        PortfolioService._get_transaction_rows = staticmethod(
            lambda user_id, end_date: [
                {
                    "symbol": "TEST",
                    "type": "BUY",
                    "quantity": 10.0,
                    "price": 100.0,
                    "currency": "TWD",
                    "transaction_date": "2026-06-01",
                },
                {
                    "symbol": "TEST",
                    "type": "BUY",
                    "quantity": 5.0,
                    "price": 120.0,
                    "currency": "TWD",
                    "transaction_date": "2026-06-03",
                },
            ]
        )
        PortfolioService.get_summary = classmethod(
            lambda cls, user_id: PortfolioSummary(
                total_value=1900.0,
                total_value_twd=1900.0,
                total_cost=1600.0,
                total_cost_twd=1600.0,
                unrealized_gain=300.0,
                unrealized_gain_twd=300.0,
                unrealized_pct=18.75,
                realized_gain=0.0,
                realized_gain_twd=0.0,
                day_change=0.0,
                day_change_pct=0.0,
            )
        )
        portfolio_service.FxService.load_rates = staticmethod(lambda: {"TWD": 1.0})
        portfolio_service.MarketService.normalize_symbol = classmethod(lambda cls, symbol: symbol)
        portfolio_service.MarketService.get_symbol_profile = classmethod(
            lambda cls, conn, symbol: SimpleNamespace(currency="TWD", history_table="price_history_tw")
        )
        PortfolioService._get_benchmark_series = classmethod(lambda cls, start_date, end_date: [])
        price_rows_by_symbol = {
            "TEST": [
                {"price_date": "2026-06-01", "close": 100.0},
                {"price_date": "2026-06-02", "close": 102.0},
                {"price_date": "2026-06-03", "close": 121.0},
            ]
        }
        portfolio_service.get_db = lambda: _FakeConn(price_rows_by_symbol)

        result = PortfolioService.get_performance(user_id=1, range_key="all")

        self.assertEqual(result.range, "all")
        self.assertEqual(result.start_date, "2026-06-01")
        self.assertGreater(len(result.portfolio), 2)
        self.assertEqual(result.portfolio[0].value, 1000.0)
        self.assertEqual(result.portfolio[1].value, 1020.0)
        self.assertEqual(result.portfolio[-1].value, 1900.0)
        self.assertEqual(result.end_date, str(result.portfolio[-1].date))


if __name__ == "__main__":
    unittest.main()
