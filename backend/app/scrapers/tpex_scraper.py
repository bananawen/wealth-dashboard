"""
TPEx (Taiwan OTC / 興櫃) Stock Scraper using direct API
TPEx = 財團法人中華民國證券櫃檯買賣中心
https://www.tpex.org.tw
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
import httpx

from ..logging_config import logger
from ..middleware import log_scraper_event


class TPExScraper:
    """Scraper for Taiwan TPEx (OTC) market data"""

    BASE_URL = "https://www.tpex.org.tw"
    TABLE = "price_history_tw"

    def __init__(self, db_pool=None):
        self._db_pool = db_pool

    def _get_connection(self):
        if self._db_pool:
            return self._db_pool.connection()
        import psycopg2
        from ..config import get_settings
        settings = get_settings()
        return psycopg2.connect(settings.DATABASE_URL)

    def get_all_tpex_stocks(self) -> List[str]:
        """Get list of all TPEx stock codes from official source"""
        try:
            url = f"{self.BASE_URL}/web/stock/ifrinfo/last_ir_results.php"
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            codes = set()
            for item in data.get('aaData', []):
                if len(item) > 1:
                    code = str(item[1]).strip()
                    if len(code) == 4 and code.isdigit():
                        codes.add(code)
            logger.info(f"Fetched {len(codes)} TPEx stock codes")
            return sorted(codes)
        except Exception as e:
            logger.error(f"Failed to fetch TPEx stock list: {e}")
            return []

    def get_realtime(self, symbol: str) -> Optional[Dict]:
        """Get real-time quote for a TPEx stock"""
        try:
            url = f"{self.BASE_URL}/web/stock/ifrinfo/last_ir_results.php"
            params = {"stk_code": symbol}
            resp = httpx.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if not data or len(data) == 0:
                return None

            # Response format: list of dicts with fields like 'c' (close), 'o' (open), etc.
            item = data[0] if isinstance(data, list) else data
            return {
                "symbol": symbol,
                "price": float(item.get('c') or item.get('a', 0)),
                "open": float(item.get('o', 0)),
                "high": float(item.get('h', 0)),
                "low": float(item.get('l', 0)),
                "volume": int(item.get('v', 0)),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to fetch realtime for TPEx {symbol}: {e}")
        return None

    def get_historical_data(self, symbol: str, year: int, month: int) -> List[Dict]:
        """Fetch monthly historical data for a TPEx stock"""
        records = []
        try:
            # Fixed URL: no space in path
            url = f"{self.BASE_URL}/web/stock/monthly/api/get_monthly_recent.php"
            params = {
                "stk_code": symbol,
                "year": year,
                "month": month,
            }
            resp = httpx.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get('aaData', []):
                if len(item) < 6:
                    continue
                try:
                    date_str = str(item[0]).strip()
                    close = float(str(item[2]).strip().replace(',', ''))
                    volume = int(str(item[3]).strip().replace(',', ''))
                    open_ = float(str(item[4]).strip().replace(',', '')) if len(item) > 4 and item[4] else close
                    high = float(str(item[5]).strip().replace(',', '')) if len(item) > 5 and item[5] else close
                    low = float(str(item[6]).strip().replace(',', '')) if len(item) > 6 and item[6] else close

                    records.append({
                        "symbol": symbol,
                        "price_date": date_str,
                        "open": open_,
                        "high": high,
                        "low": low,
                        "close": close,
                        "volume": volume,
                        "currency": "TWD",
                        "source": "TPEx",
                    })
                except (ValueError, IndexError) as e:
                    logger.warning(f"TPEx {symbol} parse error: {e}, item={item}")
                    continue

            logger.info(f"TPEx {symbol} {year}/{month}: {len(records)} records")
        except Exception as e:
            logger.error(f"TPEx historical fetch failed for {symbol} {year}/{month}: {e}")
        return records

    def fetch_full_history(self, symbol: str, start_year: int = 2006) -> List[Dict]:
        """Fetch full history from start_year to current month"""
        all_records = []
        now = datetime.now()
        for year in range(start_year, now.year + 1):
            month_start = 1
            month_end = 12
            if year == now.year:
                month_end = now.month
            for month in range(month_start, month_end + 1):
                records = self.get_historical_data(symbol, year, month)
                all_records.extend(records)
                import time
                time.sleep(0.5)
        return all_records

    def upsert_records(self, records: List[Dict]) -> int:
        """Insert or update TPEx records into price_history_tw. Returns count of inserted rows."""
        if not records:
            return 0
        conn = self._get_connection()
        cur = conn.cursor()
        inserted = 0
        for rec in records:
            try:
                cur.execute("""
                    INSERT INTO price_history_tw
                        (symbol, price_date, open, high, low, close, volume, currency, source)
                    VALUES
                        (%(symbol)s, %(price_date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s, %(currency)s, %(source)s)
                    ON CONFLICT (symbol, price_date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        source = EXCLUDED.source
                """, rec)
                inserted += 1
            except Exception as e:
                logger.error(f"TPEx DB insert error for {rec.get('symbol')}: {e}")
        conn.commit()
        cur.close()
        conn.close()
        return inserted

    def scrape_symbol(self, symbol: str, fetch_full: bool = False) -> Dict:
        """Scrape one TPEx symbol: fetch and persist to DB. Returns summary."""
        import time
        if fetch_full:
            records = self.fetch_full_history(symbol)
        else:
            now = datetime.now()
            records = self.get_historical_data(symbol, now.year, now.month)

        inserted = self.upsert_records(records)
        log_scraper_event(symbol, "tpex_scrape_complete", records=len(records), inserted=inserted,
                          full=fetch_full)
        return {"symbol": symbol, "records": len(records), "inserted": inserted}


if __name__ == "__main__":
    scraper = TPExScraper()
    # Test 00887 (TPEx listed)
    print("Testing 00887...")
    result = scraper.get_realtime("00887")
    print("Realtime:", result)
    result = scraper.get_historical_data("00887", 2024, 1)
    print(f"Historical 2024/01: {len(result)} records")
    if result:
        print("Sample:", result[0])
