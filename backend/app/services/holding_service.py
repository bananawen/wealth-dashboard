from __future__ import annotations

from dataclasses import dataclass

from ..database import get_db
from .fx_service import FxService
from .price_service import PriceService, PriceQuote


@dataclass
class ComputedHolding:
    symbol: str
    shares: float
    avg_cost: float
    total_cost: float
    total_cost_twd: float
    market_value: float
    market_value_twd: float
    unrealized_gain: float
    unrealized_gain_twd: float
    unrealized_pct: float
    current_price: float
    current_price_twd: float
    day_change: float
    day_change_twd: float
    day_change_pct: float
    currency: str
    exchange: str
    price_source: str
    price_status: str
    price_is_estimated: bool

    def to_api_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "shares": self.shares,
            "avg_cost": self.avg_cost,
            "total_cost": round(self.total_cost, 2),
            "total_cost_twd": round(self.total_cost_twd, 2),
            "market_value": round(self.market_value, 2),
            "market_value_twd": round(self.market_value_twd, 2),
            "unrealized_gain": round(self.unrealized_gain, 2),
            "unrealized_gain_twd": round(self.unrealized_gain_twd, 2),
            "unrealized_pct": round(self.unrealized_pct, 2),
            "current_price": round(self.current_price, 2),
            "current_price_twd": round(self.current_price_twd, 2),
            "day_change": round(self.day_change, 2),
            "day_change_twd": round(self.day_change_twd, 2),
            "day_change_pct": round(self.day_change_pct, 2),
            "currency": self.currency,
            "exchange": self.exchange,
            "price_source": self.price_source,
            "price_status": self.price_status,
            "price_is_estimated": self.price_is_estimated,
        }


class HoldingService:
    @staticmethod
    def fetch_active_holdings(user_id: int) -> list[dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, symbol, shares, avg_cost, total_cost, currency "
                "FROM holdings WHERE shares > 0 AND user_id = %s ORDER BY symbol",
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    @classmethod
    def compute_holding(cls, row: dict, rates: dict[str, float]) -> ComputedHolding:
        symbol = row["symbol"]
        shares = float(row["shares"])
        avg_cost = float(row["avg_cost"])
        total_cost = float(row["total_cost"])
        currency = FxService.normalize_currency(row.get("currency"))
        quote: PriceQuote = PriceService.get_price_cached(symbol)

        price_available = quote.price > 0
        price_is_estimated = not price_available and avg_cost > 0
        price = quote.price if price_available else avg_cost
        price_status = "live" if price_available else ("estimated" if price_is_estimated else "missing")

        market_value = price * shares
        unrealized_gain = market_value - total_cost
        unrealized_pct = (unrealized_gain / total_cost * 100) if total_cost > 0 else 0.0

        fx_rate = FxService.get_rate_to_twd_from_rates(rates, currency)
        market_value_twd = market_value * fx_rate
        total_cost_twd = total_cost * fx_rate
        current_price_twd = price * fx_rate
        unrealized_gain_twd = market_value_twd - total_cost_twd
        day_change = market_value * quote.change_pct / 100 if price_available else 0.0
        day_change_twd = day_change * fx_rate

        return ComputedHolding(
            symbol=symbol,
            shares=shares,
            avg_cost=avg_cost,
            total_cost=total_cost,
            total_cost_twd=total_cost_twd,
            market_value=market_value,
            market_value_twd=market_value_twd,
            unrealized_gain=unrealized_gain,
            unrealized_gain_twd=unrealized_gain_twd,
            unrealized_pct=unrealized_pct,
            current_price=price,
            current_price_twd=current_price_twd,
            day_change=day_change,
            day_change_twd=day_change_twd,
            day_change_pct=quote.change_pct,
            currency=currency,
            exchange=quote.exchange,
            price_source=quote.source,
            price_status=price_status,
            price_is_estimated=price_is_estimated,
        )

    @classmethod
    def get_computed_positions(cls, user_id: int) -> list[ComputedHolding]:
        holdings = cls.fetch_active_holdings(user_id)
        rates = FxService.load_rates()
        return [cls.compute_holding(row, rates) for row in holdings]

    @classmethod
    def get_computed_holdings(cls, user_id: int) -> list[dict]:
        return [position.to_api_dict() for position in cls.get_computed_positions(user_id)]
