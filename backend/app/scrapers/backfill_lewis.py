"""
Backfill GLD + 00887 historical data from 1990 to present for Lewis.
Run: python -m app.scrapers.backfill_lewis
"""
import sys
sys.path.insert(0, '/home/lewis/wealth/backend')

import time
import logging
import yfinance as yf
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
from app.config import get_settings
from app.middleware import log_scraper_event
from app.logging_config import logger
import json

settings = get_settings()

# Lewis's actual holdings
US_SYMBOLS = ["GLD", "VOO", "QQQ", "AAPL"]
TW_SYMBOLS = ["00887", "0050"]

YFINANCE_MAP = {
    "GLD": "GLD",
    "VOO": "VOO",
    "QQQ": "QQQ",
    "AAPL": "AAPL",
    "00887": "00887.TW",   # twstock handles this differently
    "0050": "0050.TW",
}

START = "1990-01-01"
TODAY = date.today().strftime("%Y-%m-%d")


def get_yf_data(symbol: str) -> dict:
    """Fetch from Yahoo Finance, returns {date: close_price}"""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(start=START, end=TODAY)
    result = {}
    for idx, row in hist.iterrows():
        ds = str(idx)[:10]
        result[ds] = {
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
        }
    return result


def get_tw_data(symbol: str) -> dict:
    """Fetch Taiwan stock via twstock"""
    import twstock
    result = {}
    current_year = datetime.now().year

    # 00887 is TPEx (上櫃), twstock handles separately
    is_tpex = symbol in ("00887",)

    for year in range(1990, current_year + 1):
        for month in range(1, 13):
            if year == current_year and month > datetime.now().month:
                break
            try:
                if is_tpex:
                    stock = twstock.Stock(symbol)
                    data = stock.fetch(year, month)
                else:
                    stock = twstock.Stock(symbol)
                    data = stock.fetch(year, month)

                for d in data:
                    ds = str(d.date)[:10]
                    result[ds] = {
                        "open": round(float(d.open), 4),
                        "high": round(float(d.high), 4),
                        "low": round(float(d.low), 4),
                        "close": round(float(d.close), 4),
                        "volume": int(d.capacity) if hasattr(d, 'capacity') else 0,
                    }
            except Exception as e:
                pass  # skip months with no data
        time.sleep(0.3)

    return result


def upsert_us(symbol: str, prices: dict) -> int:
    """Upsert US stock into price_history_us"""
    conn = psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    inserted = 0
    for ds, vals in prices.items():
        try:
            cur.execute("""
                INSERT INTO price_history_us (symbol, price_date, open, high, low, close, volume, currency, source)
                VALUES (%(symbol)s, %(price_date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s, 'USD', 'US')
                ON CONFLICT (symbol, price_date) DO UPDATE SET
                    open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                    close=EXCLUDED.close, volume=EXCLUDED.volume
            """, {"symbol": symbol, "price_date": ds, **vals})
            inserted += 1
        except Exception as e:
            pass
    conn.commit()
    cur.close()
    conn.close()
    return inserted


def upsert_tw(symbol: str, prices: dict, market: str) -> int:
    """Upsert Taiwan stock into price_history_tw"""
    conn = psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    inserted = 0
    for ds, vals in prices.items():
        try:
            cur.execute("""
                INSERT INTO price_history_tw (symbol, price_date, open, high, low, close, volume, currency, source)
                VALUES (%(symbol)s, %(price_date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s, 'TWD', %(market)s)
                ON CONFLICT (symbol, price_date) DO UPDATE SET
                    open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                    close=EXCLUDED.close, volume=EXCLUDED.volume
            """, {"symbol": symbol, "price_date": ds, "market": market, **vals})
            inserted += 1
        except Exception as e:
            pass
    conn.commit()
    cur.close()
    conn.close()
    return inserted


def main():
    logger.info("=" * 60)
    logger.info("BACKFILL: Lewis holdings from 1990")
    logger.info("=" * 60)

    total = 0

    # --- US Stocks ---
    for sym in US_SYMBOLS:
        yf_sym = YFINANCE_MAP[sym]
        logger.info(f"[US] Fetching {sym} ({yf_sym})...")
        try:
            prices = get_yf_data(yf_sym)
            n = upsert_us(sym, prices)
            total += n
            logger.info(f"  → {len(prices)} records fetched, {n} upserted")
            log_scraper_event(sym, "fetched", records=len(prices), inserted=n,
                              start=START, end=TODAY, source="yfinance")
            # Write to audit_log DB
            _write_audit(sym, "US", len(prices), START, TODAY, "SUCCESS", n)
        except Exception as e:
            logger.error(f"  → ERROR {sym}: {e}")
            _write_audit(sym, "US", 0, START, TODAY, f"ERROR: {e}", 0)
        time.sleep(0.5)

    # --- TW Stocks ---
    for sym in TW_SYMBOLS:
        logger.info(f"[TW] Fetching {sym} (twstock)...")
        try:
            prices = get_tw_data(sym)
            market = "TPEx" if sym in ("00887",) else "TWSE"
            n = upsert_tw(sym, prices, market)
            total += n
            logger.info(f"  → {len(prices)} records, {n} upserted")
            log_scraper_event(sym, "fetched", records=len(prices), inserted=n,
                              start=START, end=TODAY, source="twstock")
            _write_audit(sym, "TW", len(prices), START, TODAY, "SUCCESS", n)
        except Exception as e:
            logger.error(f"  → ERROR {sym}: {e}")
            _write_audit(sym, "TW", 0, START, TODAY, f"ERROR: {e}", 0)
        # twstock has built-in sleep

    logger.info(f"=" * 60)
    logger.info(f"BACKFILL COMPLETE: {total} total records upserted")
    logger.info(f"=" * 60)


def _write_audit(symbol: str, market: str, records: int, start: str, end: str, status: str, inserted: int):
    """Write audit_log entry"""
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        message = f"爬蟲執行: {market} {symbol} | {records}筆 | {start}~{end} | source={'yfinance' if market=='US' else 'twstock'} | {status}"
        cur.execute("""
            INSERT INTO audit_log (timestamp, type, level, message, details)
            VALUES (%s, 'scraper', %s, %s, %s)
        """, (
            ts,
            "INFO" if status == "SUCCESS" else "ERROR",
            message,
            json.dumps({"symbol": symbol, "market": market, "records": records,
                        "start_date": start, "end_date": end, "source": "yfinance" if market == "US" else "twstock",
                        "status": status, "inserted": inserted})
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Audit log write failed: {e}")


if __name__ == "__main__":
    main()
