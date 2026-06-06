"""
Backfill historical stock data from 2020 to present.

Can be run standalone:
    python -m app.scrapers.backfill

Or called as functions by the scheduler.
"""
import logging
import time
from datetime import date, datetime, timedelta
from typing import List, Optional

from app.logging_config import logger
from app.database import get_db
from app.scrapers.price_collector import _fetch_and_upsert, _alert_no_data

# ─── constants ────────────────────────────────────────────────────────────────

US_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JPM", "V",
    "UNH", "HD", "MA", "PG", "XOM", "CVX", "LLY", "ABBV", "MRK", "AVGO",
    "PEP", "COST", "KO", "MCD", "TMO", "CSCO", "ACN", "ABT", "DHR", "BAC",
    "WMT", "CRM", "ADBE", "TXN", "NEE", "PM", "BMY", "UNP", "RTX", "LOW",
    "QCOM", "HON", "INTU", "AMGN", "ORCL", "IBM", "CAT", "DE", "ELV", "AXP",
    "SPY", "QQQ", "VOO", "VTI", "IWM", "VEA", "VWO", "BND", "AGG", "GLD",
    "TLT", "IEF", "LQD", "HYG", "EMB", "MUB", "TIPS", "REET", "UUP",
]

TW_SYMBOLS = [
    "0050", "0056", "0051", "0052", "0053", "0054", "0055", "0057", "0058", "0059",
    "006208", "00690", "00692", "00701", "00713", "00720", "00730", "00733", "00735", "00736",
    "00878", "00881", "00891", "00900", "00902", "00903", "00904", "00905", "00906", "00907",
    "2330", "2317", "2303", "2454", "2308", "2377", "2382", "2408", "2431", "2498",
    "2881", "2882", "2883", "2884", "2885", "2886", "2887", "2888", "2889", "2890",
]


# ─── callable functions ───────────────────────────────────────────────────────

def backfill_symbol(
    symbol: str,
    region: str,
    start_date: date,
    end_date: date,
) -> int:
    """
    Backfill a single symbol for the given date range.
    Returns the number of records inserted/updated.
    """
    count, err = _fetch_and_upsert(symbol, region, start_date, end_date)
    if err:
        logger.error(f"[backfill_symbol] {symbol} ({region}) error: {err}")
        _alert_no_data(symbol, region, reason=f"backfill: {err}")
    return count


def backfill_all_tracked_symbols(
    symbols: Optional[List[str]] = None,
    region: str = "TW",
    start_year: int = 2020,
    limit: Optional[int] = None,
) -> dict:
    """
    Backfill a list of symbols (or the default TW/US lists).
    Returns a summary dict with success/failure counts.

    Args:
        symbols: list of symbols to backfill, or None to use defaults
        region: 'TW' or 'US'
        start_year: start year for backfill
        limit: max number of symbols to process (for testing)
    """
    today = date.today()
    syms = symbols or (TW_SYMBOLS if region == "TW" else US_SYMBOLS)
    if limit:
        syms = syms[:limit]

    results = {"success": 0, "failed": 0, "errors": []}

    for i, sym in enumerate(syms):
        start = date(start_year, 1, 1)
        try:
            if region == "TW":
                # Taiwan: batch by year
                for year in range(start_year, today.year + 1):
                    y_end = min(date(year, 12, 31), today)
                    count, err = _fetch_and_upsert(sym, region, date(year, 1, 1), y_end)
                    if err:
                        logger.warning(f"[{i+1}/{len(syms)}] {sym} year={year} error: {err}")
                    time.sleep(0.3)
                results["success"] += 1
            else:
                # US: single range split into 30-day batches
                current = start
                while current <= today:
                    batch_end = min(current + timedelta(days=29), today)
                    count, err = _fetch_and_upsert(sym, region, current, batch_end)
                    if err:
                        logger.warning(f"[{i+1}/{len(syms)}] {sym} {current}→{batch_end} error: {err}")
                    current = batch_end + timedelta(days=1)
                    time.sleep(0.3)
                results["success"] += 1

        except Exception as e:
            logger.error(f"[{i+1}/{len(syms)}] {sym} failed: {e}")
            results["failed"] += 1
            results["errors"].append(f"{sym}: {e}")

    logger.info(
        f"[backfill_all_tracked] region={region} done: "
        f"{results['success']} success, {results['failed']} failed"
    )
    return results


# ─── standalone CLI ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backfill historical stock prices")
    parser.add_argument("--region", choices=["TW", "US"], default="TW",
                        help="Market region")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of symbols (for testing)")
    parser.add_argument("--start-year", type=int, default=2020)
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info(f"Starting backfill: region={args.region}, limit={args.limit}, start={args.start_year}")
    logger.info("=" * 60)

    result = backfill_all_tracked_symbols(
        region=args.region,
        limit=args.limit,
        start_year=args.start_year,
    )

    logger.info("=" * 60)
    logger.info(f"Backfill complete: {result}")
    logger.info("=" * 60)