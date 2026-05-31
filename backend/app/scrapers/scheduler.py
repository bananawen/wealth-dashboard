"""
Scheduled stock data fetcher
Runs daily after market close: US at 21:30 ET, Taiwan at 13:30 TT
"""
import logging
from datetime import datetime, date
from typing import List, Dict

from psycopg2.extras import Json

from app.logging_config import logger
from app.scrapers import TaiwanStockScraper, USStockScraper
from app.middleware import log_scraper_event
from app.database import get_db

# Symbols to track daily
US_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "SPY", "QQQ", "VOO", "VTI", "GLD",  # GLD added
    "0050", "0056", "006208", "00878",  # Taiwan ETFs tracked in US
]


def _write_audit_log(symbol: str, records: int, status: str, error_msg: str = None):
    """Write an audit_log entry for scrape events."""
    try:
        with get_db() as conn:
            cur = conn.cursor()
            if status == "success":
                details = {"symbol": symbol, "records": records, "market": "US", "date": str(date.today()), "status": "success"}
                cur.execute("""
                    INSERT INTO audit_log (timestamp, type, level, message, details, symbol)
                    VALUES (NOW(), 'scrape', 'INFO', %s, %s, %s)
                """, (f"scrape {symbol} success: {records} records", Json(details), symbol))
            else:
                details = {"symbol": symbol, "market": "US", "date": str(date.today()), "status": "error", "error": error_msg or "unknown"}
                cur.execute("""
                    INSERT INTO audit_log (timestamp, type, level, message, details, symbol)
                    VALUES (NOW(), 'scrape', 'ERROR', %s, %s, %s)
                """, (f"scrape {symbol} ERROR: {error_msg}", Json(details), symbol))
    except Exception as e:
        logger.error(f"Failed to write audit_log for {symbol}: {e}")


def _upsert_price_history_us(records: List[Dict]):
    """Insert or update price_history_us records. Returns count of upserted rows."""
    if not records:
        return 0
    upserted = 0
    with get_db() as conn:
        cur = conn.cursor()
        for rec in records:
            cur.execute("""
                INSERT INTO price_history_us (symbol, price_date, open, high, low, close, volume, currency, source, created_at)
                VALUES (%(symbol)s, %(date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s, 'USD', %(source)s, NOW())
                ON CONFLICT (symbol, price_date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    created_at = NOW()
            """, rec)
            upserted += 1
    return upserted

TW_SYMBOLS = [
    "0050", "0056", "2330", "2317", "2303", "2454", "2308",
    "2881", "2882", "2883", "2884", "2885",
]


def fetch_us_market_close():
    """Fetch US market data at market close (21:30 ET)"""
    logger.info("=" * 50)
    logger.info("Starting US market close data fetch")
    logger.info("=" * 50)
    
    scraper = USStockScraper()
    end_date = date.today().strftime("%Y-%m-%d")
    start_date = f"{date.today().year}-01-01"
    
    results = {"success": 0, "failed": 0, "errors": []}
    
    for symbol in US_SYMBOLS:
        try:
            log_scraper_event(symbol, "daily_fetch_start")
            records = scraper.get_historical_data(symbol, start_date, end_date)
            
            if records:
                upserted = _upsert_price_history_us(records)
                _write_audit_log(symbol, len(records), "success")
                log_scraper_event(symbol, "daily_fetch_success", records=len(records), upserted=upserted)
                results["success"] += 1
            else:
                _write_audit_log(symbol, 0, "error", "no data returned")
                log_scraper_event(symbol, "daily_fetch_empty")
                results["failed"] += 1
                
        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            _write_audit_log(symbol, 0, "error", str(e))
            log_scraper_event(symbol, "daily_fetch_error", error=str(e))
            results["errors"].append(f"{symbol}: {str(e)}")
        
        # Rate limiting
        import time
        time.sleep(0.3)
    
    logger.info(f"US market fetch complete: {results['success']} success, {results['failed']} failed")
    return results


def fetch_taiwan_market_close():
    """Fetch Taiwan market data at market close (13:30 TT)"""
    logger.info("=" * 50)
    logger.info("Starting Taiwan market close data fetch")
    logger.info("=" * 50)
    
    scraper = TaiwanStockScraper()
    today = date.today()
    
    results = {"success": 0, "failed": 0, "errors": []}
    
    for symbol in TW_SYMBOLS:
        try:
            log_scraper_event(symbol, "daily_fetch_start")
            records = scraper.get_historical_data(symbol, today.year, today.month)
            
            # Filter to just today's records
            today_str = today.strftime("%Y-%m-%d")
            today_records = [r for r in records if r["date"] == today_str]
            
            if today_records:
                log_scraper_event(symbol, "daily_fetch_success", records=len(today_records))
                results["success"] += 1
            else:
                log_scraper_event(symbol, "daily_fetch_no_today")
                results["failed"] += 1
                
        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            results["errors"].append(f"{symbol}: {str(e)}")
        
        import time
        time.sleep(0.5)
    
    logger.info(f"Taiwan market fetch complete: {results['success']} success, {results['failed']} failed")
    return results


if __name__ == "__main__":
    import sys
    
    market = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if market in ["us", "all"]:
        fetch_us_market_close()
    
    if market in ["tw", "all"]:
        fetch_taiwan_market_close()
    
    logger.info("Scheduled fetch complete!")