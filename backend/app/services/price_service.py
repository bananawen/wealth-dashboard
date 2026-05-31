"""
Price fetching service — unified single get_price().
All routers should call PriceService.get_price() instead of duplicating logic.

Async wrappers use asyncio.to_thread() so the sync yfinance/twstock calls
don't block the event loop when called from async FastAPI endpoints.
"""
import asyncio
import yfinance as yf
import twstock
from dataclasses import dataclass


@dataclass
class PriceQuote:
    price: float
    change_pct: float


class PriceService:

    @staticmethod
    def get_tpex_price(symbol: str) -> PriceQuote:
        """上櫃股：twstock"""
        try:
            stock = twstock.Stock(symbol)
            prices = stock.price
            if prices and len(prices) >= 2:
                curr = float(prices[-1])
                prev = float(prices[-2])
                pct = (curr - prev) / prev * 100
                return PriceQuote(price=curr, change_pct=pct)
            elif prices:
                return PriceQuote(price=float(prices[-1]), change_pct=0.0)
        except Exception:
            pass
        return PriceQuote(price=0.0, change_pct=0.0)

    @staticmethod
    def get_twse_price(symbol: str) -> PriceQuote:
        """上市股：Yahoo Finance {symbol}.TW"""
        try:
            ticker = yf.Ticker(f"{symbol}.TW")
            hist = ticker.history(period="5d")
            if len(hist) >= 2:
                prev = float(hist["Close"].iloc[-2])
                curr = float(hist["Close"].iloc[-1])
                return PriceQuote(price=curr, change_pct=(curr - prev) / prev * 100)
            elif len(hist) == 1:
                return PriceQuote(price=float(hist["Close"].iloc[-1]), change_pct=0.0)
        except Exception:
            pass
        return PriceQuote(price=0.0, change_pct=0.0)

    @staticmethod
    def get_us_price(symbol: str) -> PriceQuote:
        """美股：Yahoo Finance (原始代碼)"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if len(hist) >= 2:
                prev = float(hist["Close"].iloc[-2])
                curr = float(hist["Close"].iloc[-1])
                return PriceQuote(price=curr, change_pct=(curr - prev) / prev * 100)
            elif len(hist) == 1:
                return PriceQuote(price=float(hist["Close"].iloc[-1]), change_pct=0.0)
        except Exception:
            pass
        return PriceQuote(price=0.0, change_pct=0.0)

    @classmethod
    def get_price(cls, symbol: str) -> PriceQuote:
        """
        Unified price fetch. Taiwan digit-symbols use twstock + TWSE fallback;
        everything else falls through to US yfinance.
        """
        if symbol.isdigit():
            # 優先用 twstock（支援上市+上櫃）
            quote = cls.get_tpex_price(symbol)
            if quote.price > 0:
                return quote
            # fallback 上市 YAHOO
            return cls.get_twse_price(symbol)
        return cls.get_us_price(symbol)

    @staticmethod
    def get_usd_to_twd_rate() -> float:
        """Fetch USD/TWD exchange rate from Yahoo Finance."""
        try:
            ticker = yf.Ticker("USDTWD=X")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception:
            pass
        return 33.0  # fallback default rate

    # ── Async wrappers (for use from async FastAPI endpoints) ──────────────────

    @classmethod
    async def get_tpex_price_async(cls, symbol: str) -> PriceQuote:
        return await asyncio.to_thread(cls.get_tpex_price, symbol)

    @classmethod
    async def get_twse_price_async(cls, symbol: str) -> PriceQuote:
        return await asyncio.to_thread(cls.get_twse_price, symbol)

    @classmethod
    async def get_us_price_async(cls, symbol: str) -> PriceQuote:
        return await asyncio.to_thread(cls.get_us_price, symbol)

    @classmethod
    async def get_price_async(cls, symbol: str) -> PriceQuote:
        """
        Async version of get_price(). Runs the full fetch logic in a thread pool
        so it never blocks the asyncio event loop.
        """
        return await asyncio.to_thread(cls.get_price, symbol)

    @classmethod
    async def get_usd_to_twd_rate_async(cls) -> float:
        return await asyncio.to_thread(cls.get_usd_to_twd_rate)