"""
Taiwan Stock Scraper using Twstock
"""
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
import twstock

from ..logging_config import logger
from ..middleware import log_scraper_event

class TaiwanStockScraper:
    """Scraper for Taiwan stock market data"""
    
    def __init__(self):
        self.name = "Taiwan Stock Scraper"
    
    def get_all_twse_stocks(self) -> List[str]:
        """Get list of all TWSE (Taiwan Stock Exchange) stock codes"""
        try:
            # Get all stock codes from Twstock
            stocks = twstock.twse
            return list(stocks.keys())
        except Exception as e:
            logger.error(f"Failed to fetch TWSE stock list: {e}")
            return []
    
    def get_all_otc_stocks(self) -> List[str]:
        """Get list of all OTC (Over-The-Counter) stock codes"""
        try:
            stocks = twstock.otc
            return list(stocks.keys())
        except Exception as e:
            logger.error(f"Failed to fetch OTC stock list: {e}")
            return []
    
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """Get basic info for a Taiwan stock symbol"""
        try:
            stock = twstock.Stock(symbol)
            return {
                "symbol": symbol,
                "name": stock.name,
                "group": "TWSE" if len(symbol) == 4 and symbol.isdigit() else "OTC"
            }
        except Exception as e:
            log_scraper_event(symbol, "fetch_failed", error=str(e))
            return None
    
    def get_historical_data(self, symbol: str, year: int, month: int) -> List[Dict]:
        """Fetch monthly historical data for a Taiwan stock"""
        try:
            stock = twstock.Stock(symbol)
            # Fetch data for the specified month
            data = stock.fetch(year, month)
            
            records = []
            for d in data:
                records.append({
                    "symbol": symbol,
                    "date": d.date.strftime("%Y-%m-%d"),
                    "open": d.open,
                    "high": d.high,
                    "low": d.low,
                    "close": d.close,
                    "volume": d.capacity,
                    "source": "TWSE" if len(symbol) == 4 and symbol[0].isdigit() else "OTC"
                })
            
            log_scraper_event(symbol, "month_fetched", year=year, month=month, records=len(records))
            return records
            
        except Exception as e:
            log_scraper_event(symbol, "fetch_error", year=year, month=month, error=str(e))
            return []
    
    def get_realtime(self, symbol: str) -> Optional[Dict]:
        """Get real-time quote for a Taiwan stock"""
        try:
            stock = twstock.Stock(symbol)
            return {
                "symbol": symbol,
                "price": stock.price,
                "open": stock.open,
                "high": stock.high,
                "low": stock.low,
                "volume": stock.capacity,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to fetch realtime for {symbol}: {e}")
            return None
    
    def get_batch_realtime(self, symbols: List[str]) -> List[Dict]:
        """Get real-time quotes for multiple Taiwan stocks"""
        results = []
        for sym in symbols:
            data = self.get_realtime(sym)
            if data:
                results.append(data)
        return results