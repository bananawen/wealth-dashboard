from __future__ import annotations

from functools import lru_cache

from ..database import get_db


class FxService:
    DEFAULT_RATES_TO_TWD = {
        "TWD": 1.0,
        "USD": 32.0,
        "HKD": 4.1,
        "JPY": 0.21,
        "EUR": 35.0,
        "GBP": 40.0,
    }

    @staticmethod
    def normalize_currency(currency: str | None) -> str:
        return (currency or "TWD").upper()

    @classmethod
    def load_rates(cls, conn=None) -> dict[str, float]:
        rates = dict(cls.DEFAULT_RATES_TO_TWD)
        if conn is not None:
            cur = conn.cursor()
            cur.execute("SELECT currency, rate_to_twd FROM currency_cache")
            for row in cur.fetchall():
                rates[cls.normalize_currency(row["currency"])] = float(row["rate_to_twd"])
            return rates

        with get_db() as db_conn:
            return cls.load_rates(db_conn)

    @classmethod
    def get_rate_to_twd_from_rates(cls, rates: dict[str, float], currency: str | None) -> float:
        normalized = cls.normalize_currency(currency)
        return float(rates.get(normalized, cls.DEFAULT_RATES_TO_TWD.get(normalized, 1.0)))

    @classmethod
    @lru_cache(maxsize=16)
    def get_rate_to_twd(cls, currency: str | None) -> float:
        rates = cls.load_rates()
        return cls.get_rate_to_twd_from_rates(rates, currency)
