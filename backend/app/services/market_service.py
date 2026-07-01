from __future__ import annotations

import re
from dataclasses import dataclass

import twstock


@dataclass(frozen=True)
class SymbolProfile:
    symbol: str
    exchange: str
    currency: str
    yahoo_symbol: str
    history_table: str
    history_region: str
    history_source: str
    quote_primary_source: str
    quote_fallback_source: str | None = None


class MarketService:
    SYMBOL_ALIASES = {
        "00631": "00631L",
    }
    EXCHANGE_OVERRIDES = {
        "00887": "OTC",
        "00881": "OTC",
    }
    TAIWAN_SYMBOL_PATTERN = re.compile(r"^\d{4,6}[A-Z]?$")
    _twse_symbols: set[str] | None = None
    _otc_symbols: set[str] | None = None
    _suffix_aliases: dict[str, str] | None = None

    @classmethod
    def normalize_symbol(cls, symbol: str) -> str:
        normalized = (symbol or "").strip().upper()
        manual_alias = cls.SYMBOL_ALIASES.get(normalized)
        if manual_alias:
            return manual_alias

        twse_symbols, otc_symbols = cls._load_tw_symbols()
        all_tw_symbols = twse_symbols | otc_symbols
        if normalized in all_tw_symbols:
            return normalized

        return cls._load_suffix_aliases().get(normalized, normalized)

    @classmethod
    def normalize_exchange(cls, exchange: str | None, symbol: str | None = None) -> str:
        raw = (exchange or "").strip().upper()
        if raw in {"TPEX", "OTC"}:
            return "OTC"
        if raw == "TWSE":
            return "TWSE"
        if raw in {"NASDAQ", "NYSE", "AMEX", "US"}:
            return "US"
        if symbol and symbol.isdigit():
            return cls.infer_exchange(symbol)
        return "US"

    @classmethod
    def _load_tw_symbols(cls) -> tuple[set[str], set[str]]:
        if cls._twse_symbols is None:
            try:
                cls._twse_symbols = set(twstock.twse.keys())
            except Exception:
                cls._twse_symbols = set()
        if cls._otc_symbols is None:
            try:
                cls._otc_symbols = set(getattr(twstock, "otc", getattr(twstock, "tpex", {})).keys())
            except Exception:
                cls._otc_symbols = set()
        return cls._twse_symbols, cls._otc_symbols

    @classmethod
    def _load_suffix_aliases(cls) -> dict[str, str]:
        if cls._suffix_aliases is not None:
            return cls._suffix_aliases

        twse_symbols, otc_symbols = cls._load_tw_symbols()
        all_tw_symbols = twse_symbols | otc_symbols
        suffix_candidates: dict[str, list[str]] = {}
        for symbol in all_tw_symbols:
            match = re.match(r"^(\d{4,6})([A-Z])$", symbol)
            if not match:
                continue
            base_symbol = match.group(1)
            suffix_candidates.setdefault(base_symbol, []).append(symbol)

        aliases: dict[str, str] = {}
        for base_symbol, candidates in suffix_candidates.items():
            if base_symbol in all_tw_symbols:
                continue
            if len(candidates) == 1:
                aliases[base_symbol] = candidates[0]

        aliases.update(cls.SYMBOL_ALIASES)
        cls._suffix_aliases = aliases
        return cls._suffix_aliases

    @classmethod
    def infer_exchange(cls, symbol: str) -> str:
        symbol = cls.normalize_symbol(symbol)
        if not cls.TAIWAN_SYMBOL_PATTERN.match(symbol):
            return "US"
        if symbol in cls.EXCHANGE_OVERRIDES:
            return cls.EXCHANGE_OVERRIDES[symbol]
        twse_symbols, otc_symbols = cls._load_tw_symbols()
        if symbol in otc_symbols:
            return "OTC"
        if symbol in twse_symbols:
            return "TWSE"
        return "TWSE"

    @classmethod
    def infer_exchange_from_existing_data(cls, conn, symbol: str) -> str | None:
        symbol = cls.normalize_symbol(symbol)
        if not cls.TAIWAN_SYMBOL_PATTERN.match(symbol):
            return "US"
        cur = conn.cursor()
        cur.execute(
            """
            SELECT source
            FROM price_history_tw
            WHERE symbol = %s
            ORDER BY price_date DESC
            LIMIT 1
            """,
            (symbol,),
        )
        row = cur.fetchone()
        cur.close()
        if not row or not row["source"]:
            return None
        source = str(row["source"]).strip().lower()
        if "tpex" in source or "two" in source or source == "otc":
            return "OTC"
        if "twse" in source:
            return "TWSE"
        return None

    @classmethod
    def lookup_exchange(cls, conn, symbol: str) -> str | None:
        symbol = cls.normalize_symbol(symbol)
        cur = conn.cursor()
        cur.execute("SELECT exchange FROM stock_info WHERE symbol = %s", (symbol,))
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return cls.normalize_exchange(row["exchange"], symbol)

    @classmethod
    def ensure_symbol_profile(cls, conn, symbol: str, exchange: str | None = None) -> SymbolProfile:
        symbol = cls.normalize_symbol(symbol)
        normalized_exchange = cls.normalize_exchange(exchange, symbol) if exchange else cls.lookup_exchange(conn, symbol)
        if not normalized_exchange:
            normalized_exchange = cls.infer_exchange_from_existing_data(conn, symbol) or cls.infer_exchange(symbol)

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO stock_info (symbol, exchange, last_updated)
            VALUES (%s, %s, NOW())
            ON CONFLICT (symbol) DO UPDATE SET
                exchange = EXCLUDED.exchange,
                last_updated = NOW()
            """,
            (symbol, normalized_exchange),
        )
        cur.close()
        return cls.profile_from_exchange(symbol, normalized_exchange)

    @classmethod
    def sync_symbols_from_transactions(cls, conn) -> list[SymbolProfile]:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM transactions ORDER BY symbol")
        symbols = [cls.normalize_symbol(str(row["symbol"])) for row in cur.fetchall()]
        cur.close()
        profiles: list[SymbolProfile] = []
        for symbol in symbols:
            inferred_exchange = cls.infer_exchange_from_existing_data(conn, symbol) or cls.infer_exchange(symbol)
            profiles.append(cls.ensure_symbol_profile(conn, symbol, exchange=inferred_exchange))
        return profiles

    @classmethod
    def get_symbol_profile(cls, conn, symbol: str) -> SymbolProfile:
        symbol = cls.normalize_symbol(symbol)
        exchange = cls.lookup_exchange(conn, symbol)
        if not exchange:
            exchange = cls.infer_exchange_from_existing_data(conn, symbol) or cls.infer_exchange(symbol)
        return cls.profile_from_exchange(symbol, exchange)

    @classmethod
    def profile_from_exchange(cls, symbol: str, exchange: str) -> SymbolProfile:
        normalized_exchange = cls.normalize_exchange(exchange, symbol)
        if normalized_exchange == "TWSE":
            return SymbolProfile(
                symbol=symbol,
                exchange="TWSE",
                currency="TWD",
                yahoo_symbol=f"{symbol}.TW",
                history_table="price_history_tw",
                history_region="TW",
                history_source="yfinance_twse",
                quote_primary_source="yfinance",
                quote_fallback_source="twstock",
            )
        if normalized_exchange == "OTC":
            return SymbolProfile(
                symbol=symbol,
                exchange="OTC",
                currency="TWD",
                yahoo_symbol=f"{symbol}.TWO",
                history_table="price_history_tw",
                history_region="TW",
                history_source="yfinance_tpex",
                quote_primary_source="twstock",
                quote_fallback_source="yfinance",
            )
        return SymbolProfile(
            symbol=symbol,
            exchange="US",
            currency="USD",
            yahoo_symbol=symbol,
            history_table="price_history_us",
            history_region="US",
            history_source="yfinance_us",
            quote_primary_source="yfinance",
            quote_fallback_source=None,
        )
