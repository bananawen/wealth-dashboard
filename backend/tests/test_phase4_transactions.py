import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers.transactions import (
    _coerce_asset_class_and_sector,
    _normalize_asset_class,
    _parse_import_row,
    _rebuild_symbol_transaction_state,
    _validate_transaction_fields,
)
from app.services.holding_projection_service import HoldingProjectionService


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.cursor_obj = FakeCursor(rows)

    def cursor(self):
        return self.cursor_obj


class TransactionRouterTest(unittest.TestCase):
    def test_validate_transaction_fields_rejects_empty_or_nonpositive_values(self):
        with self.assertRaises(HTTPException):
            _validate_transaction_fields("", 1, 10, "buy")

        with self.assertRaises(HTTPException):
            _validate_transaction_fields("AAPL", 0, 10, "buy")

        with self.assertRaises(HTTPException):
            _validate_transaction_fields("AAPL", 1, 0, "buy")

    def test_rebuild_symbol_transaction_state_recalculates_average_cost_realized_gain(self):
        rows = [
            {"id": 1, "type": "buy", "shares": 10, "price": 100, "date": "2026-06-01"},
            {"id": 2, "type": "sell", "shares": 4, "price": 120, "date": "2026-06-02"},
            {"id": 3, "type": "buy", "shares": 2, "price": 150, "date": "2026-06-03"},
        ]
        conn = FakeConnection(rows)

        with patch.object(HoldingProjectionService, "recompute_holding") as recompute_holding:
            _rebuild_symbol_transaction_state(conn, "aapl", 5)

        update_calls = [call for call in conn.cursor_obj.calls if call[0].startswith("UPDATE transactions")]
        self.assertEqual(update_calls[0][1], (0.0, 1, 5))
        self.assertEqual(update_calls[1][1], (80.0, 2, 5))
        self.assertEqual(update_calls[2][1], (0.0, 3, 5))
        recompute_holding.assert_called_once_with(conn, "AAPL", 5)

    def test_rebuild_symbol_transaction_state_includes_fee_and_tax_in_gain(self):
        rows = [
            {"id": 1, "type": "buy", "shares": 10, "price": 100, "fee": 5, "tax": 0, "date": "2026-06-01"},
            {"id": 2, "type": "sell", "shares": 4, "price": 120, "fee": 2, "tax": 1, "date": "2026-06-02"},
        ]
        conn = FakeConnection(rows)

        with patch.object(HoldingProjectionService, "recompute_holding"):
            _rebuild_symbol_transaction_state(conn, "AAPL", 5)

        update_calls = [call for call in conn.cursor_obj.calls if call[0].startswith("UPDATE transactions")]
        self.assertEqual(update_calls[1][1], (75.0, 2, 5))

    def test_parse_import_row_supports_chinese_headers(self):
        raw_row = {
            "股票代號": "0050",
            "交易類型": "買入",
            "股數": 10,
            "價格": 123.45,
            "交易日期": "2026-06-20",
            "備註": "長期持有",
            "分類": "長期投資",
            "資產類別": "股票",
            "產業": "半導體",
            "手續費": 1.23,
            "稅費": 0.0,
        }
        parsed = _parse_import_row(raw_row, 2)

        self.assertEqual(parsed["symbol"], "0050")
        self.assertEqual(parsed["type"], "買入")
        self.assertEqual(parsed["category"], "long_term")
        self.assertEqual(parsed["asset_class"], "equity")
        self.assertEqual(parsed["sector"], "semiconductor")
        self.assertEqual(parsed["fee"], 1.23)
        self.assertEqual(parsed["notes"], "長期持有")

    def test_normalize_asset_class_rejects_unknown_value(self):
        with self.assertRaises(HTTPException):
            _normalize_asset_class("crypto")

    def test_coerce_asset_class_and_sector_defaults_equity_when_sector_is_set(self):
        asset_class, sector = _coerce_asset_class_and_sector(None, "科技")
        self.assertEqual(asset_class, "equity")
        self.assertEqual(sector, "technology")

    def test_coerce_asset_class_and_sector_rejects_non_equity_sector(self):
        with self.assertRaises(HTTPException):
            _coerce_asset_class_and_sector("bond", "科技")

    def test_rebuild_symbol_transaction_state_rejects_oversell(self):
        rows = [
            {"id": 1, "type": "buy", "shares": 5, "price": 100, "date": "2026-06-01"},
            {"id": 2, "type": "sell", "shares": 8, "price": 120, "date": "2026-06-02"},
        ]
        conn = FakeConnection(rows)

        with patch.object(HoldingProjectionService, "recompute_holding"):
            with self.assertRaises(HTTPException):
                _rebuild_symbol_transaction_state(conn, "AAPL", 5)


if __name__ == "__main__":
    unittest.main()
