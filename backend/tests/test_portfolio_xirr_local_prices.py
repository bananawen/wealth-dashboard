import sys
import unittest
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import portfolio_service
from app.services.portfolio_service import PortfolioService, xirr


class _FakeCursor:
    def __init__(self, holdings, tx_rows, history_by_key):
        self.holdings = holdings
        self.tx_rows = tx_rows
        self.history_by_key = history_by_key
        self._result_all = []
        self._result_one = None

    def execute(self, sql, params=None):
        normalized_sql = " ".join(sql.split())
        params = params or ()

        if "FROM holdings WHERE shares > 0" in normalized_sql:
            self._result_all = self.holdings
            self._result_one = None
            return

        if "FROM transactions WHERE user_id = %s GROUP BY transaction_date, currency ORDER BY transaction_date" in normalized_sql:
            self._result_all = self.tx_rows
            self._result_one = None
            return

        if "FROM price_history_" in normalized_sql and "ORDER BY price_date DESC LIMIT 1" in normalized_sql:
            symbol = params[0]
            as_of_date = str(params[1])
            rows = self.history_by_key.get((symbol, as_of_date), [])
            self._result_one = rows[0] if rows else None
            self._result_all = rows
            return

        raise AssertionError(f"Unexpected SQL: {normalized_sql}")

    def fetchall(self):
        return self._result_all

    def fetchone(self):
        return self._result_one


class _FakeConnection:
    def __init__(self, holdings, tx_rows, history_by_key):
        self.holdings = holdings
        self.tx_rows = tx_rows
        self.history_by_key = history_by_key

    def cursor(self):
        return _FakeCursor(self.holdings, self.tx_rows, self.history_by_key)


class PortfolioXirrLocalPriceTest(unittest.TestCase):
    def setUp(self):
        self.original_get_db = portfolio_service.get_db
        self.original_get_symbol_profile = portfolio_service.MarketService.get_symbol_profile
        self.original_normalize_symbol = portfolio_service.MarketService.normalize_symbol

    def tearDown(self):
        portfolio_service.get_db = self.original_get_db
        portfolio_service.MarketService.get_symbol_profile = self.original_get_symbol_profile
        portfolio_service.MarketService.normalize_symbol = self.original_normalize_symbol

    def _install_fake_db(self, holdings, tx_rows, history_by_key):
        @contextmanager
        def fake_get_db():
            yield _FakeConnection(holdings, tx_rows, history_by_key)

        portfolio_service.get_db = fake_get_db
        portfolio_service.MarketService.normalize_symbol = classmethod(lambda cls, symbol: symbol)
        portfolio_service.MarketService.get_symbol_profile = classmethod(
            lambda cls, conn, symbol: SimpleNamespace(
                symbol=symbol,
                history_table="price_history_tw" if symbol.isdigit() else "price_history_us",
                currency="TWD" if symbol.isdigit() else "USD",
            )
        )

    def test_xirr_terminal_value_uses_latest_local_history_prices(self):
        self._install_fake_db(
            holdings=[
                {"symbol": "00636", "shares": 100.0, "avg_cost": 10.0, "currency": "TWD"},
                {"symbol": "GLD", "shares": 2.0, "avg_cost": 100.0, "currency": "USD"},
            ],
            tx_rows=[],
            history_by_key={
                ("00636", "2026-07-03"): [{"price_date": "2026-07-02", "close": 11.0}],
                ("GLD", "2026-07-03"): [{"price_date": "2026-07-01", "close": 90.0}],
            },
        )

        total_value_twd, status, message = PortfolioService._get_xirr_terminal_value_twd(
            user_id=1,
            as_of_date=date(2026, 7, 3),
            rates={"TWD": 1.0, "USD": 32.0},
        )

        self.assertEqual(total_value_twd, 6860.0)
        self.assertEqual(status, "ok")
        self.assertIn("依本地歷史收盤價計算", message)
        self.assertIn("非即時報價", message)

    def test_xirr_terminal_value_marks_estimated_when_local_history_missing(self):
        self._install_fake_db(
            holdings=[
                {"symbol": "QQQ", "shares": 3.0, "avg_cost": 50.0, "currency": "USD"},
            ],
            tx_rows=[],
            history_by_key={
                ("QQQ", "2026-07-03"): [],
            },
        )

        total_value_twd, status, message = PortfolioService._get_xirr_terminal_value_twd(
            user_id=1,
            as_of_date=date(2026, 7, 3),
            rates={"TWD": 1.0, "USD": 32.0},
        )

        self.assertEqual(total_value_twd, 4800.0)
        self.assertEqual(status, "estimated")
        self.assertIn("成本價估算", message)

    def test_annualized_return_uses_local_history_terminal_value(self):
        self._install_fake_db(
            holdings=[],
            tx_rows=[
                {"transaction_date": "2026-01-01", "currency": "TWD", "cf": -1000.0},
            ],
            history_by_key={},
        )

        original_terminal_value = PortfolioService._get_xirr_terminal_value_twd
        PortfolioService._get_xirr_terminal_value_twd = classmethod(
            lambda cls, user_id, as_of_date, rates: (1100.0, "ok", "依本地歷史收盤價計算（價格日：2026-07-02）")
        )
        try:
            annualized, status, message = PortfolioService._get_annualized_return(
                user_id=1,
                rates={"TWD": 1.0},
            )
        finally:
            PortfolioService._get_xirr_terminal_value_twd = original_terminal_value

        expected = xirr([-1000.0, 1100.0], [date(2026, 1, 1), date.today()]) * 100
        self.assertAlmostEqual(annualized, expected)
        self.assertEqual(status, "ok")
        self.assertIn("依本地歷史收盤價計算", message)


if __name__ == "__main__":
    unittest.main()
