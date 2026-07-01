import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.sector_backfill import infer_sector


class SectorBackfillTest(unittest.TestCase):
    def test_infer_sector_prefers_existing_sector(self):
        result = infer_sector("QQQ", "equity", ["etf"], ["broad_market", "broad_market"])
        self.assertEqual(result, "broad_market")

    def test_infer_sector_returns_none_for_non_equity(self):
        result = infer_sector("GLD", "precious_metal", ["etf"], [])
        self.assertIsNone(result)

    def test_infer_sector_uses_symbol_map_for_equity_etf(self):
        result = infer_sector("00887", "equity", ["etf"], [])
        self.assertEqual(result, "broad_market")

    def test_infer_sector_keeps_unknown_symbol_blank(self):
        result = infer_sector("00922", "other", [], [])
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
