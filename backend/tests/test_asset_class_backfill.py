import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.asset_class_backfill import infer_asset_class


class AssetClassBackfillTest(unittest.TestCase):
    def test_infer_asset_class_prefers_existing_asset_class(self):
        result = infer_asset_class("QQQ", ["etf"], ["bond", "bond"])
        self.assertEqual(result, "bond")

    def test_infer_asset_class_classifies_known_bond_symbol(self):
        result = infer_asset_class("00679B", ["etf"], [])
        self.assertEqual(result, "bond")

    def test_infer_asset_class_classifies_precious_metal_symbol(self):
        result = infer_asset_class("GLD", ["etf"], [])
        self.assertEqual(result, "precious_metal")

    def test_infer_asset_class_keeps_unknown_etf_conservative(self):
        result = infer_asset_class("00999X", ["etf"], [])
        self.assertEqual(result, "other")

    def test_infer_asset_class_keeps_unknown_tw_symbol_conservative(self):
        result = infer_asset_class("00922", [], [])
        self.assertEqual(result, "other")


if __name__ == "__main__":
    unittest.main()
