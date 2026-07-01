from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import get_db
from scripts.sector_symbol_map import SECTOR_SYMBOL_MAP

SECTOR_LABELS = {
    "semiconductor": "半導體",
    "technology": "科技",
    "financial": "金融",
    "communication": "通訊",
    "consumer": "消費",
    "industrial": "工業",
    "healthcare": "醫療保健",
    "energy": "能源",
    "materials": "原物料",
    "utilities": "公用事業",
    "real_estate": "不動產",
    "broad_market": "大盤ETF",
    "high_dividend": "高股息ETF",
    "thematic": "主題ETF",
    "other": "其他",
}


def _normalize_symbol(symbol: str | None) -> str:
    return str(symbol or "").strip().upper()


def infer_sector(
    symbol: str,
    asset_class: str | None,
    categories: list[str | None],
    current_sectors: list[str | None],
) -> str | None:
    normalized_symbol = _normalize_symbol(symbol)
    current_counter = Counter(value for value in current_sectors if value)
    if current_counter:
        return current_counter.most_common(1)[0][0]

    if asset_class != "equity":
        return None

    if normalized_symbol in SECTOR_SYMBOL_MAP:
        return SECTOR_SYMBOL_MAP[normalized_symbol]

    category_counter = Counter(value for value in categories if value)
    dominant_category = category_counter.most_common(1)[0][0] if category_counter else None
    if dominant_category == "stock" and normalized_symbol.isalpha():
        return "technology" if normalized_symbol in {"AAPL", "MSFT", "GOOGL"} else None
    return None


def build_backfill_plan(limit: int | None = None) -> list[dict]:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, symbol, category, asset_class, sector
            FROM transactions
            ORDER BY transaction_date ASC, id ASC
            """
        )
        rows = [dict(row) for row in cur.fetchall()]

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[_normalize_symbol(row["symbol"])].append(row)

    plan: list[dict] = []
    for symbol in sorted(grouped):
        symbol_rows = grouped[symbol]
        categories = [row.get("category") for row in symbol_rows]
        current_sectors = [row.get("sector") for row in symbol_rows]
        asset_class = next((row.get("asset_class") for row in symbol_rows if row.get("asset_class")), None)
        inferred = infer_sector(symbol, asset_class, categories, current_sectors)
        if not inferred:
            continue

        for row in symbol_rows:
            if row.get("sector"):
                continue
            plan.append({
                "id": int(row["id"]),
                "symbol": symbol,
                "asset_class": row.get("asset_class"),
                "category": row.get("category"),
                "from": row.get("sector"),
                "to": inferred,
            })

    if limit is not None:
        return plan[:limit]
    return plan


def print_plan(plan: list[dict]) -> None:
    total = len(plan)
    by_sector = Counter(item["to"] for item in plan)
    by_symbol = Counter(item["symbol"] for item in plan)

    print(f"待回填交易筆數：{total}")
    if total == 0:
        print("沒有需要補值的交易。")
        return

    print("回填分布：")
    for sector, count in sorted(by_sector.items(), key=lambda item: (-item[1], item[0])):
        print(f"- {SECTOR_LABELS.get(sector, sector)} ({sector}): {count} 筆")

    print("影響標的前 20 名：")
    for symbol, count in by_symbol.most_common(20):
        target = next(item["to"] for item in plan if item["symbol"] == symbol)
        print(f"- {symbol}: {count} 筆 -> {SECTOR_LABELS.get(target, target)}")

    print("預覽前 20 筆：")
    for item in plan[:20]:
        category = item["category"] or "未分類"
        asset_class = item["asset_class"] or "未分類"
        print(f"- id={item['id']} symbol={item['symbol']} asset_class={asset_class} category={category} -> {item['to']}")


def apply_plan(plan: list[dict]) -> int:
    if not plan:
        return 0

    with get_db() as conn:
        cur = conn.cursor()
        for item in plan:
            cur.execute(
                "UPDATE transactions SET sector = %s WHERE id = %s",
                (item["to"], item["id"]),
            )
    return len(plan)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill missing transactions.sector values.")
    parser.add_argument("--apply", action="store_true", help="實際寫入資料庫；未指定時只做預覽")
    parser.add_argument("--limit", type=int, default=None, help="只預覽前 N 筆待回填交易")
    args = parser.parse_args()

    plan = build_backfill_plan(limit=args.limit)
    print_plan(plan)

    if not args.apply:
        print("\n目前為預覽模式，未寫入資料庫。")
        print("如要實際回填，請執行：")
        print("  cd /home/lewis/wealth/backend && venv/bin/python scripts/sector_backfill.py --apply")
        return 0

    updated = apply_plan(plan)
    print(f"\n已回填 {updated} 筆交易。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
