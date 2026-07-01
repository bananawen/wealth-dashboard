"""
Transaction service helpers.

The router currently only needs the non-blocking backfill helper, so we keep
this module intentionally small to avoid importing stale ORM symbols during
application startup.
"""

from __future__ import annotations

import logging
import threading
from datetime import date, datetime, timedelta

logger = logging.getLogger("wealth")


def get_symbol_backfill_start_date(symbol: str) -> date:
    """
    Resolve the history backfill start date for a symbol.

    Rules:
    - Prefer the earliest BUY transaction date.
    - If no BUY exists, fall back to the earliest transaction date.
    - If the symbol has no transactions, fall back to 5 years ago.
    """
    from app.database import get_db
    from app.services.market_service import MarketService

    normalized_symbol = MarketService.normalize_symbol(symbol)
    fallback_date = date.today() - timedelta(days=365 * 5)

    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    MIN(CASE WHEN type = 'BUY' THEN transaction_date END) AS first_buy_date,
                    MIN(transaction_date) AS first_transaction_date
                FROM transactions
                WHERE UPPER(symbol) = %s
                """,
                (normalized_symbol,),
            )
            row = cur.fetchone()
            cur.close()

        if not row:
            return fallback_date

        start_date = row["first_buy_date"] or row["first_transaction_date"]
        if isinstance(start_date, str):
            return datetime.strptime(start_date, "%Y-%m-%d").date()
        if start_date:
            return start_date
    except Exception as exc:
        logger.warning("[Backfill] failed to resolve start date for %s: %s", normalized_symbol, exc)

    return fallback_date


def auto_backfill_symbol(symbol: str):
    """Check if symbol has price history; backfill from purchase date if missing."""

    def _do():
        try:
            from app.database import get_db
            from app.services.market_service import MarketService
            from app.scrapers.price_collector import _fetch_and_upsert

            normalized_symbol = MarketService.normalize_symbol(symbol)
            with get_db() as conn:
                profile = MarketService.ensure_symbol_profile(conn, normalized_symbol)
                table = profile.history_table
                region = profile.history_region
                cur = conn.cursor()
                cur.execute(f"SELECT MIN(price_date) AS earliest FROM {table} WHERE symbol = %s", (normalized_symbol,))
                row = cur.fetchone()
                has_history = bool(row and row["earliest"] is not None)

            if has_history:
                logger.info(f"[Backfill] {normalized_symbol} already has history, skipping")
                return

            start_date = get_symbol_backfill_start_date(normalized_symbol)
            end_date = date.today()
            logger.info(f"[Backfill] {normalized_symbol} has no history, starting backfill from {start_date}...")
            count, err = _fetch_and_upsert(normalized_symbol, region, start_date, end_date)
            if err:
                logger.error(f"[Backfill] {normalized_symbol} failed: {err}")
            else:
                logger.info(f"[Backfill] {normalized_symbol} done, {count} records")
        except Exception as e:
            logger.error(f"[Backfill] Error for {symbol}: {e}")

    t = threading.Thread(target=_do, daemon=True)
    t.start()
