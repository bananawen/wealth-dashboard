"""
Core price collection logic for the wealth dashboard.

Contains reusable functions for fetching, upserting, and gap-detecting
stock price history from Yahoo Finance into our local tables.
"""
import logging
import time
from datetime import date, timedelta
from typing import Optional

import yfinance as yf
from psycopg2.extras import Json

from app.database import get_db
from app.services.audit import write_log
from app.logging_config import logger

# Known OTC stocks (上櫃) that need .TWO suffix
OTC_STOCKS = {"00887"}


def _get_exchange(symbol: str) -> str:
    """Return exchange for a symbol: TWSE (上市), OTC (上櫃), US, etc."""
    if symbol in OTC_STOCKS:
        return "OTC"
    if symbol.isdigit():
        return "TWSE"
    return "US"


# ─── price fetch (reused from holdings.py) ───────────────────────────────────

def _get_price_impl(symbol: str, avg_cost: float = 0.0) -> tuple[float, float, str]:
    """
    Core price-fetching logic (no caching). Used by _get_price_cached.
    Get price, day_change%, exchange for a symbol.
    上市用 .TW，上櫃用 .TWO.
    Falls back to avg_cost if Yahoo Finance returns 0.
    Returns (price, day_change_pct, exchange).
    """
    exchange = _get_exchange(symbol)

    if exchange == "TWSE":
        try:
            ticker = yf.Ticker(f"{symbol}.TW")
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = float(hist["Close"].iloc[-2])
                curr_close = float(hist["Close"].iloc[-1])
                change_pct = (curr_close - prev_close) / prev_close * 100
                return curr_close, change_pct, exchange
            elif len(hist) == 1:
                curr_close = float(hist["Close"].iloc[-1])
                if curr_close > 0:
                    return curr_close, 0.0, exchange
        except Exception:
            pass

    if exchange == "OTC":
        try:
            ticker = yf.Ticker(f"{symbol}.TWO")
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = float(hist["Close"].iloc[-2])
                curr_close = float(hist["Close"].iloc[-1])
                change_pct = (curr_close - prev_close) / prev_close * 100
                return curr_close, change_pct, exchange
            elif len(hist) == 1:
                curr_close = float(hist["Close"].iloc[-1])
                if curr_close > 0:
                    return curr_close, 0.0, exchange
        except Exception:
            pass

    if exchange == "US":
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = float(hist["Close"].iloc[-2])
                curr_close = float(hist["Close"].iloc[-1])
                change_pct = (curr_close - prev_close) / prev_close * 100
                return curr_close, change_pct, exchange
            elif len(hist) == 1:
                curr_close = float(hist["Close"].iloc[-1])
                if curr_close > 0:
                    return curr_close, 0.0, exchange
        except Exception:
            pass

    if avg_cost > 0:
        return 0.0, 0.0, exchange

    return 0.0, 0.0, exchange


# ─── three-layer TW symbol resolution ─────────────────────────────────────────

def _try_tw_symbol(symbol: str) -> Optional[str]:
    """
    Try .TW first, then .TWO, return the working suffix or None.
    Three-layer search: 上市(.TW) → 上櫃(.TWO) → 興櫃 (bare symbol for emerging).
    For emerging (興櫃), yfinance uses the bare symbol.
    """
    for suffix in (".TW", ".TWO", ""):
        try:
            full = f"{symbol}{suffix}" if suffix else symbol
            ticker = yf.Ticker(full)
            hist = ticker.history(period="5d")
            if hist is not None and not hist.empty and float(hist["Close"].iloc[-1]) > 0:
                return suffix
        except Exception:
            pass
        time.sleep(0.2)
    return None


# ─── upsert helpers ───────────────────────────────────────────────────────────

def _fetch_and_upsert(
    symbol: str,
    region: str,
    start_date: date,
    end_date: date,
) -> tuple[int, Optional[str]]:
    """
    Fetch historical data from yfinance and UPSERT into price_history_tw or price_history_us.
    Returns (inserted_count, error_msg or None).
    """
    table = "price_history_tw" if region == "TW" else "price_history_us"
    currency = "TWD" if region == "TW" else "USD"

    # Resolve TW symbol suffix
    yf_symbol = symbol
    if region == "TW":
        suffix = _try_tw_symbol(symbol)
        if suffix is None:
            return 0, f"Could not resolve TW symbol {symbol} in any layer (.TW/.TWO/bare)"
        yf_symbol = f"{symbol}{suffix}" if suffix else symbol
        logger.info(f"[{symbol}] resolved to yfinance symbol {yf_symbol}")

    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(start=start_date.isoformat(), end=end_date.isoformat())

        if hist is None or hist.empty:
            return 0, None  # empty is not an error, just no data

        count = 0
        with get_db() as conn:
            cur = conn.cursor()
            for idx, row in hist.iterrows():
                price_date = idx.strftime("%Y-%m-%d")
                rec = {
                    "symbol": symbol.upper(),
                    "date": price_date,
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                    "currency": currency,
                    "source": region,
                }
                cur.execute(f"""
                    INSERT INTO {table} (symbol, price_date, open, high, low, close, volume, currency, source, created_at)
                    VALUES (%(symbol)s, %(date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s, %(currency)s, %(source)s, NOW())
                    ON CONFLICT (symbol, price_date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        created_at = NOW()
                """, rec)
                count += 1
            cur.close()

        logger.info(f"[{symbol}] upserted {count} records into {table}")
        return count, None

    except Exception as e:
        logger.error(f"[{symbol}] _fetch_and_upsert failed: {e}")
        return 0, str(e)


# ─── gap detection ────────────────────────────────────────────────────────────

def _detect_gaps(symbol: str, region: str) -> tuple[bool, Optional[date], int]:
    """
    Query DB for latest price_date for this symbol.
    Returns (has_gap: bool, latest_date: date or None, gap_days: int).
    """
    table = "price_history_tw" if region == "TW" else "price_history_us"
    today = date.today()

    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                SELECT MAX(price_date) as latest FROM {table}
                WHERE symbol = %s
            """, (symbol,))
            row = cur.fetchone()
            cur.close()

        if row and row["latest"]:
            latest = row["latest"]
            if isinstance(latest, str):
                from datetime import datetime
                latest = datetime.strptime(latest, "%Y-%m-%d").date()
            gap_days = (today - latest).days
            return gap_days > 0, latest, gap_days
        else:
            return True, None, -1  # no data at all

    except Exception as e:
        logger.error(f"[{symbol}] _detect_gaps failed: {e}")
        return True, None, -1


# ─── new symbol discovery ──────────────────────────────────────────────────────

def _discover_new_symbols() -> list[tuple[str, str]]:
    """
    Query transactions DISTINCT symbol, check which ones have no price_history_tw/us entry.
    Returns list of (symbol, region_hint) tuples where region_hint is 'TW' or 'US'
    based on the account currency.
    """
    discovered = []

    try:
        with get_db() as conn:
            cur = conn.cursor()

            # Get all symbols that have at least one transaction
            cur.execute("""
                SELECT DISTINCT t.symbol, a.currency
                FROM transactions t
                JOIN accounts a ON a.id = t.account_id
                ORDER BY t.symbol
            """)
            tx_rows = cur.fetchall()
            cur.close()

        for row in tx_rows:
            symbol = row["symbol"]
            currency = row["currency"]

            if currency == "USD":
                region = "US"
                table = "price_history_us"
            else:
                region = "TW"
                table = "price_history_tw"

            # Check if price history exists
            with get_db() as conn2:
                cur2 = conn2.cursor()
                cur2.execute(f"SELECT 1 FROM {table} WHERE symbol = %s LIMIT 1", (symbol,))
                exists = cur2.fetchone() is not None
                cur2.close()

            if not exists:
                discovered.append((symbol, region))

        logger.info(f"_discover_new_symbols found {len(discovered)} new symbols")
        return discovered

    except Exception as e:
        logger.error(f"_discover_new_symbols failed: {e}")
        return []


# ─── alerting ─────────────────────────────────────────────────────────────────

def _alert_no_data(symbol: str, exchange_hint: str, reason: str = None):
    """Write ERROR (or CRITICAL) to audit_log when no data could be fetched."""
    level = "CRITICAL" if exchange_hint in ("TW", "TWO", "興櫃") else "ERROR"
    write_log(
        type="scraper",
        level=level,
        message=f"No price data for symbol {symbol} (hint={exchange_hint})",
        details={"symbol": symbol, "exchange_hint": exchange_hint, "reason": reason},
        symbol=symbol,
    )