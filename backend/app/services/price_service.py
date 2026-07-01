"""
Price fetching service — unified single get_price().
All routers should call PriceService.get_price() instead of duplicating logic.

Async wrappers use asyncio.to_thread() so the sync yfinance/twstock calls
don't block the event loop when called from async FastAPI endpoints.
"""
import asyncio
import time
from dataclasses import dataclass

import yfinance as yf
import twstock

from ..database import get_db
from .market_service import MarketService


@dataclass
class PriceQuote:
    price: float
    change_pct: float
    exchange: str
    currency: str
    source: str


class PriceService:
    CACHE_TTL_SECONDS = 300
    _price_cache: dict[str, tuple[float, PriceQuote]] = {}

    @classmethod
    def get_exchange(cls, symbol: str) -> str:
        """Return exchange for a symbol using DB-backed market rules."""
        with get_db() as conn:
            profile = MarketService.ensure_symbol_profile(conn, symbol.upper())
        return profile.exchange

    @classmethod
    def empty_quote(cls, symbol: str, source: str = "none") -> PriceQuote:
        exchange = cls.get_exchange(symbol)
        currency = "TWD" if exchange in {"TWSE", "OTC"} else "USD"
        return PriceQuote(price=0.0, change_pct=0.0, exchange=exchange, currency=currency, source=source)

    @classmethod
    def get_twstock_price(cls, symbol: str, exchange: str) -> PriceQuote:
        try:
            stock = twstock.Stock(symbol)
            prices = stock.price
            if prices and len(prices) >= 2:
                curr = float(prices[-1])
                prev = float(prices[-2])
                pct = (curr - prev) / prev * 100
                return PriceQuote(price=curr, change_pct=pct, exchange=exchange, currency="TWD", source="twstock")
            if prices:
                return PriceQuote(price=float(prices[-1]), change_pct=0.0, exchange=exchange, currency="TWD", source="twstock")
        except Exception:
            pass
        return cls.empty_quote(symbol, source="twstock")

    @classmethod
    def get_tpex_price(cls, symbol: str) -> PriceQuote:
        """上櫃股：twstock"""
        return cls.get_twstock_price(symbol, "OTC")

    @classmethod
    def get_twse_price(cls, symbol: str) -> PriceQuote:
        """上市股：Yahoo Finance {symbol}.TW"""
        try:
            ticker = yf.Ticker(f"{symbol}.TW")
            hist = ticker.history(period="5d")
            if len(hist) >= 2:
                prev = float(hist["Close"].iloc[-2])
                curr = float(hist["Close"].iloc[-1])
                return PriceQuote(
                    price=curr,
                    change_pct=(curr - prev) / prev * 100,
                    exchange="TWSE",
                    currency="TWD",
                    source="yfinance_twse",
                )
            elif len(hist) == 1:
                return PriceQuote(
                    price=float(hist["Close"].iloc[-1]),
                    change_pct=0.0,
                    exchange="TWSE",
                    currency="TWD",
                    source="yfinance_twse",
                )
        except Exception:
            pass
        return cls.empty_quote(symbol, source="yfinance_twse")

    @classmethod
    def get_otc_yahoo_price(cls, symbol: str) -> PriceQuote:
        """上櫃股 Yahoo fallback: {symbol}.TWO."""
        try:
            ticker = yf.Ticker(f"{symbol}.TWO")
            hist = ticker.history(period="5d")
            if len(hist) >= 2:
                prev = float(hist["Close"].iloc[-2])
                curr = float(hist["Close"].iloc[-1])
                return PriceQuote(
                    price=curr,
                    change_pct=(curr - prev) / prev * 100,
                    exchange="OTC",
                    currency="TWD",
                    source="yfinance_tpex",
                )
            elif len(hist) == 1:
                return PriceQuote(
                    price=float(hist["Close"].iloc[-1]),
                    change_pct=0.0,
                    exchange="OTC",
                    currency="TWD",
                    source="yfinance_tpex",
                )
        except Exception:
            pass
        return cls.empty_quote(symbol, source="yfinance_tpex")

    @classmethod
    def get_us_price(cls, symbol: str) -> PriceQuote:
        """美股：Yahoo Finance (原始代碼)"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if len(hist) >= 2:
                prev = float(hist["Close"].iloc[-2])
                curr = float(hist["Close"].iloc[-1])
                return PriceQuote(
                    price=curr,
                    change_pct=(curr - prev) / prev * 100,
                    exchange="US",
                    currency="USD",
                    source="yfinance_us",
                )
            elif len(hist) == 1:
                return PriceQuote(
                    price=float(hist["Close"].iloc[-1]),
                    change_pct=0.0,
                    exchange="US",
                    currency="USD",
                    source="yfinance_us",
                )
        except Exception:
            pass
        return cls.empty_quote(symbol, source="yfinance_us")

    @classmethod
    def get_price(cls, symbol: str) -> PriceQuote:
        """
        Unified price fetch. Taiwan digit-symbols use twstock + TWSE fallback;
        everything else falls through to US yfinance.
        """
        symbol = symbol.upper()
        with get_db() as conn:
            profile = MarketService.ensure_symbol_profile(conn, symbol)

        if profile.exchange == "OTC":
            quote = cls.get_tpex_price(symbol)
            if quote.price > 0:
                return quote
            return cls.get_otc_yahoo_price(symbol)
        if profile.exchange == "TWSE":
            quote = cls.get_twse_price(symbol)
            if quote.price > 0:
                return quote
            fallback = cls.get_twstock_price(symbol, "TWSE")
            if fallback.price > 0:
                return fallback
            return cls.get_twse_price(symbol)
        return cls.get_us_price(symbol)

    @classmethod
    def get_price_cached(cls, symbol: str) -> PriceQuote:
        symbol = symbol.upper()
        now = time.time()
        cached = cls._price_cache.get(symbol)
        if cached and now - cached[0] < cls.CACHE_TTL_SECONDS:
            return cached[1]
        quote = cls.get_price(symbol)
        cls._price_cache[symbol] = (now, quote)
        return quote

    @classmethod
    def clear_price_cache(cls, symbol: str | None = None) -> None:
        if symbol is None:
            cls._price_cache.clear()
            return
        cls._price_cache.pop(symbol.upper(), None)

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
