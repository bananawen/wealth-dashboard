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

from app.database import get_db
from app.services.market_service import MarketService
from app.services.audit import write_log
from app.logging_config import logger

def _get_exchange(symbol: str) -> str:
    """Return exchange using DB-backed stock_info rules."""
    with get_db() as conn:
        profile = MarketService.ensure_symbol_profile(conn, symbol.upper())
    return profile.exchange


def _classify_fetch_error(exc: Exception) -> str:
    message = str(exc).lower()
    if "timed out" in message or "timeout" in message:
        return "timeout"
    if "too many requests" in message or "rate limit" in message or "429" in message:
        return "rate_limit"
    if "dns" in message or "name or service not known" in message or "connection" in message:
        return "network"
    if "not found" in message or "no data" in message or "empty" in message:
        return "no_data"
    return "unknown"


def _fetch_history_with_retry(
    yf_symbol: str,
    start_date: date,
    end_date: date,
    attempts: int = 3,
    timeout: int = 15,
):
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            ticker = yf.Ticker(yf_symbol)
            request_end = end_date + timedelta(days=1)
            return ticker.history(
                start=start_date.isoformat(),
                end=request_end.isoformat(),
                timeout=timeout,
            ), None
        except Exception as exc:
            last_error = exc
            kind = _classify_fetch_error(exc)
            logger.warning(
                f"[{yf_symbol}] history fetch attempt {attempt}/{attempts} failed: {kind} - {exc}"
            )
            if attempt < attempts and kind in {"timeout", "network", "rate_limit"}:
                time.sleep(min(2 * attempt, 5))
                continue
            return None, {
                "kind": kind,
                "message": str(exc),
                "attempts": attempt,
                "symbol": yf_symbol,
            }

    if last_error is not None:
        return None, {
            "kind": _classify_fetch_error(last_error),
            "message": str(last_error),
            "attempts": attempts,
            "symbol": yf_symbol,
        }
    return None, None


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


# ─── upsert helpers ───────────────────────────────────────────────────────────

def _fetch_and_upsert(
    symbol: str,
    region: str,
    start_date: date,
    end_date: date,
) -> tuple[int, Optional[dict]]:
    """
    Fetch historical data from yfinance and UPSERT into price_history_tw or price_history_us.
    Returns (inserted_count, error_msg or None).
    """
    with get_db() as conn:
        profile = MarketService.ensure_symbol_profile(conn, symbol.upper())
    normalized_symbol = profile.symbol
    if profile.history_region != region:
        profile = MarketService.profile_from_exchange(normalized_symbol, "US" if region == "US" else "TWSE")
        normalized_symbol = profile.symbol

    table = profile.history_table
    currency = profile.currency
    yf_symbol = profile.yahoo_symbol
    source = profile.history_source
    logger.info(f"[{normalized_symbol}] resolved to market={profile.exchange} yfinance symbol {yf_symbol}")

    try:
        hist, fetch_error = _fetch_history_with_retry(yf_symbol, start_date, end_date)
        if fetch_error is not None:
            return 0, {
                "kind": fetch_error.get("kind", "unknown"),
                "message": fetch_error.get("message"),
                "attempts": fetch_error.get("attempts", 1),
                "symbol": normalized_symbol,
                "yf_symbol": yf_symbol,
                "region": region,
            }

        if hist is None or hist.empty:
            return 0, {
                "kind": "no_data",
                "message": "history returned no rows",
                "attempts": 1,
                "symbol": normalized_symbol,
                "yf_symbol": yf_symbol,
                "region": region,
            }

        count = 0
        with get_db() as conn:
            cur = conn.cursor()
            for idx, row in hist.iterrows():
                price_date = idx.strftime("%Y-%m-%d")
                cur.execute(f"""
                    INSERT INTO {table} (symbol, price_date, open, high, low, close, volume, currency, source, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (symbol, price_date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        source = EXCLUDED.source,
                        created_at = NOW()
                """, (
                    normalized_symbol,
                    price_date,
                    round(float(row["Open"]), 2),
                    round(float(row["High"]), 2),
                    round(float(row["Low"]), 2),
                    round(float(row["Close"]), 2),
                    int(row["Volume"]),
                    currency,
                    source,
                ))
                count += 1
            cur.close()

        logger.info(f"[{normalized_symbol}] upserted {count} records into {table}")
        return count, None

    except Exception as e:
        error_kind = _classify_fetch_error(e)
        logger.error(f"[{normalized_symbol}] _fetch_and_upsert failed: {error_kind} - {e}")
        return 0, {
            "kind": error_kind,
            "message": str(e),
            "attempts": 1,
            "symbol": normalized_symbol,
            "yf_symbol": yf_symbol,
            "region": region,
        }


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
                SELECT DISTINCT symbol, COALESCE(currency, '') AS currency
                FROM transactions
                ORDER BY symbol
            """)
            tx_rows = cur.fetchall()
            cur.close()

        for row in tx_rows:
            symbol = row["symbol"]
            currency = str(row["currency"] or "").upper()
            if currency not in {"USD", "TWD"}:
                currency = "TWD" if symbol.isdigit() else "USD"

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
