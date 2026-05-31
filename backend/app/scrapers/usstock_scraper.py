"""
US Stock Scraper using yfinance
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
import yfinance as yf

from ..logging_config import logger
from ..middleware import log_scraper_event

class USStockScraper:
    """Scraper for US stock market data using yfinance"""
    
    def __init__(self):
        self.name = "US Stock Scraper"
    
    def get_historical_data(self, symbol: str, start_date: str, end_date: str = None) -> List[Dict]:
        """
        Fetch historical OHLCV data for a US stock
        
        Args:
            symbol: Stock ticker (e.g., 'AAPL', 'QQQ', 'SPY')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format (defaults to today)
        
        Returns:
            List of dicts with OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date or datetime.now().strftime("%Y-%m-%d"))
            
            if hist.empty:
                log_scraper_event(symbol, "no_data", start=start_date, end=end_date)
                return []
            
            records = []
            for idx, row in hist.iterrows():
                records.append({
                    "symbol": symbol.upper(),
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(float(row['Open']), 2),
                    "high": round(float(row['High']), 2),
                    "low": round(float(row['Low']), 2),
                    "close": round(float(row['Close']), 2),
                    "volume": int(row['Volume']),
                    "source": "US"
                })
            
            log_scraper_event(symbol, "fetched", records=len(records), start=start_date, end=end_date or "today")
            return records
            
        except Exception as e:
            log_scraper_event(symbol, "fetch_error", error=str(e), start=start_date)
            return []
    
    def get_realtime(self, symbol: str) -> Optional[Dict]:
        """Get real-time quote for a US stock"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            
            return {
                "symbol": symbol.upper(),
                "price": info.last_price,
                "open": info.open,
                "high": info.day_high,
                "low": info.day_low,
                "volume": info.last_volume,
                "market_cap": info.market_cap,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to fetch realtime for {symbol}: {e}")
            return None
    
    def get_batch_realtime(self, symbols: List[str]) -> List[Dict]:
        """Get real-time quotes for multiple US stocks"""
        results = []
        for sym in symbols:
            data = self.get_realtime(sym)
            if data:
                results.append(data)
        return results
    
    def get_etf_holdings(self, symbol: str) -> List[str]:
        """Get list of holdings for an ETF (approximation using major ETFs)"""
        # Common ETF holdings - in production you'd use a proper data source
        major_etfs = {
            "QQQ": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AMD", "INTC", "CSCO"],
            "VOO": ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "V"],
            "SPY": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "UNH"]
        }
        return major_etfs.get(symbol.upper(), [])
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if a US stock symbol exists"""
        try:
            ticker = yf.Ticker(symbol)
            # Try to get info - will fail if symbol is invalid
            ticker.info
            return True
        except:
            return False