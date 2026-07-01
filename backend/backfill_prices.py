#!/usr/bin/env python3
"""
One-off historical price backfill script.

Compatible with the application's current database abstraction so it can run
against SQLite or PostgreSQL without a separate psycopg2 code path.
"""
from datetime import date

from app.database import get_db
from app.scrapers.price_collector import _fetch_and_upsert


def get_transaction_symbols() -> list[str]:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM transactions ORDER BY symbol")
        return [row["symbol"] for row in cur.fetchall()]


def get_date_range() -> tuple[date, date]:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MIN(transaction_date) AS start_date, CURRENT_DATE AS end_date FROM transactions")
        row = cur.fetchone()
        start_date = row["start_date"] if row else None
        end_date = row["end_date"] if row else None
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date[:10])
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date[:10])
    return start_date or date.today(), end_date or date.today()


def backfill_symbol(symbol: str, start_date: date, end_date: date) -> int:
    region = "TW" if symbol.isdigit() else "US"
    count, err = _fetch_and_upsert(symbol, region, start_date, end_date)
    if err:
        print(f"  [WARN] {symbol} ({region}) failed: {err}")
    else:
        print(f"  [OK] {symbol} ({region}) -> {count} rows")
    return count


def main():
    print("=" * 50)
    print("Historical price backfill")
    print("=" * 50)
    symbols = get_transaction_symbols()
    start_dt, end_dt = get_date_range()
    print(f"Symbols: {symbols}")
    print(f"Range: {start_dt} ~ {end_dt}")

    total = 0
    for sym in sorted(set(symbols)):
        total += backfill_symbol(sym, start_dt, end_dt)

    print(f"\nDone. Rows fetched: {total}")


if __name__ == "__main__":
    main()
