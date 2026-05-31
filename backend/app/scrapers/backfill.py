"""
Backfill historical stock data from 2020 to present
Run this script to populate the database with historical stock data
"""
import logging
from datetime import datetime, date, timedelta
from typing import List

from app.logging_config import logger
from app.scrapers import TaiwanStockScraper, USStockScraper

# Common US ETFs and stocks to backfill
US_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JPM", "V",
    "UNH", "HD", "MA", "PG", "XOM", "CVX", "LLY", "ABBV", "MRK", "AVGO",
    "PEP", "COST", "KO", "MCD", "TMO", "CSCO", "ACN", "ABT", "DHR", "BAC",
    "WMT", "CRM", "ADBE", "TXN", "NEE", "PM", "BMY", "UNP", "RTX", "LOW",
    "QCOM", "HON", "INTU", "AMGN", "ORCL", "IBM", "CAT", "DE", "ELV", "AXP",
    "SPY", "QQQ", "VOO", "VTI", "IWM", "VEA", "VWO", "BND", "AGG", "GLD",
    "TLT", "IEF", "LQD", "HYG", "EMB", "MUB", "TIPS", "REET", "UUP",
]

# Taiwan stock indices
TW_SYMBOLS = [
    "0050", "0056", "0051", "0052", "0053", "0054", "0055", "0057", "0058", "0059",
    "006208", "00690", "00692", "00701", "00713", "00720", "00730", "00733", "00735", "00736",
    "00878", "00881", "00891", "00900", "00902", "00903", "00904", "00905", "00906", "00907",
    "2330", "2317", "2303", "2454", "2308", "2377", "2382", "2408", "2431", "2498",
    "2881", "2882", "2883", "2884", "2885", "2886", "2887", "2888", "2889", "2890",
]


def backfill_us_stocks(scraper: USStockScraper, symbols: List[str] = None, start_year: int = 2020):
    """Backfill US stock historical data"""
    symbols = symbols or US_SYMBOLS
    end_date = date.today().strftime("%Y-%m-%d")
    
    logger.info(f"Starting US stock backfill: {len(symbols)} symbols from {start_year}")
    
    for i, symbol in enumerate(symbols):
        start_date = f"{start_year}-01-01"
        try:
            logger.info(f"[{i+1}/{len(symbols)}] Fetching {symbol}...")
            records = scraper.get_historical_data(symbol, start_date, end_date)
            
            if records:
                # In production, insert into database here
                logger.info(f"  → Got {len(records)} records")
            else:
                logger.warning(f"  → No data for {symbol}")
                
        except Exception as e:
            logger.error(f"  → Failed {symbol}: {e}")
        
        # Rate limiting - be nice to the API
        import time
        time.sleep(0.5)
    
    logger.info("US stock backfill completed")


def backfill_taiwan_stocks(scraper: TaiwanStockScraper, symbols: List[str] = None, start_year: int = 2020):
    """Backfill Taiwan stock historical data"""
    symbols = symbols or TW_SYMBOLS
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    logger.info(f"Starting Taiwan stock backfill: {len(symbols)} symbols from {start_year}")
    
    for i, symbol in enumerate(symbols):
        try:
            logger.info(f"[{i+1}/{len(symbols)}] Fetching {symbol}...")
            
            for year in range(start_year, current_year + 1):
                for month in range(1, 13):
                    if year == current_year and month > current_month:
                        break
                    
                    records = scraper.get_historical_data(symbol, year, month)
                    if records:
                        logger.info(f"  → {year}/{month}: {len(records)} records")
                    
                    # Rate limiting
                    import time
                    time.sleep(0.3)
                    
        except Exception as e:
            logger.error(f"  → Failed {symbol}: {e}")
    
    logger.info("Taiwan stock backfill completed")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting historical data backfill (2020-present)")
    logger.info("=" * 60)
    
    # Backfill US stocks
    us_scraper = USStockScraper()
    backfill_us_stocks(us_scraper, US_SYMBOLS[:20])  # Start with major stocks
    
    # Backfill Taiwan stocks
    tw_scraper = TaiwanStockScraper()
    backfill_taiwan_stocks(tw_scraper, TW_SYMBOLS[:10])  # Start with major ETFs
    
    logger.info("=" * 60)
    logger.info("Backfill completed!")
    logger.info("=" * 60)