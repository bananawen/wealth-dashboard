import yfinance as yf
from datetime import date, datetime
from fastapi import APIRouter, Depends
from ..models import PortfolioSummary, SnapshotCreate
from ..database import get_db
from ..routers.auth import get_current_user
from scipy.optimize import brentq

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def get_price_and_day_change(symbol: str) -> tuple[float, float]:
    """Fetch current price and day % change for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if len(hist) >= 2:
            prev_close = float(hist["Close"].iloc[-2])
            curr_close = float(hist["Close"].iloc[-1])
            change_pct = (curr_close - prev_close) / prev_close * 100
            return curr_close, change_pct
        elif len(hist) == 1:
            curr_close = float(hist["Close"].iloc[-1])
            return curr_close, 0.0
    except Exception:
        pass
    return 0.0, 0.0


def get_twse_price(symbol: str) -> tuple[float, float]:
    """Fetch Taiwan stock price from Yahoo Finance."""
    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(period="2d")
        if len(hist) >= 2:
            prev_close = float(hist["Close"].iloc[-2])
            curr_close = float(hist["Close"].iloc[-1])
            change_pct = (curr_close - prev_close) / prev_close * 100
            return curr_close, change_pct
        elif len(hist) == 1:
            return float(hist["Close"].iloc[-1]), 0.0
    except Exception:
        pass
    return 0.0, 0.0


def get_otc_price(symbol: str) -> tuple[float, float]:
    """Fetch Taiwan OTC stock price from Yahoo Finance."""
    try:
        ticker = yf.Ticker(f"{symbol}.OB")
        hist = ticker.history(period="2d")
        if len(hist) >= 2:
            prev_close = float(hist["Close"].iloc[-2])
            curr_close = float(hist["Close"].iloc[-1])
            change_pct = (curr_close - prev_close) / prev_close * 100
            return curr_close, change_pct
        elif len(hist) == 1:
            curr_close = float(hist["Close"].iloc[-1])
            if curr_close > 0:
                return curr_close, 0.0
    except Exception:
        pass
    return 0.0, 0.0


def is_taiwan_stock(symbol: str) -> bool:
    """Determine if symbol is a Taiwan stock (numeric code)."""
    return symbol.isdigit()


def is_otc_stock(symbol: str) -> bool:
    """Known OTC stocks that need .OB suffix."""
    return symbol.upper() in ["00887"]


def xirr(cash_flows: list, dates: list) -> float:
    """
    Calculate XIRR (extended internal rate of return).
    cash_flows: list of floats (negative = outflow, positive = inflow)
    dates: list of date objects
    """
    def npv(rate):
        return sum(cf / (1 + rate) ** ((d - dates[0]).days / 365.0) for cf, d in zip(cash_flows, dates))

    try:
        result = brentq(npv, -0.99, 100.0, maxiter=1000)
        return result
    except Exception:
        return 0.0


def _get_price(symbol: str, avg_cost: float = 0.0) -> tuple[float, float]:
    """Get price and day_change% for a symbol."""
    if is_otc_stock(symbol):
        price, day_chg = get_otc_price(symbol)
        if price == 0 and avg_cost > 0:
            return avg_cost, 0.0
        return price, day_chg
    if is_taiwan_stock(symbol):
        price, day_chg = get_twse_price(symbol)
        if price == 0 and avg_cost > 0:
            return avg_cost, 0.0
        return price, day_chg
    price, day_chg = get_price_and_day_change(symbol)
    if price == 0 and avg_cost > 0:
        return avg_cost, 0.0
    return price, day_chg


def _get_currency_rate(currency_cache: dict, currency: str) -> float:
    """Get USD→TWD rate from cache, default to 32.0."""
    if currency == "TWD":
        return 1.0
    if currency == "USD":
        return currency_cache.get("USD", 32.0)
    return 1.0


@router.get("/summary", response_model=PortfolioSummary)
def get_portfolio_summary(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", 1)

    # Get USD→TWD rate from currency_cache
    currency_cache = {}
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT currency, rate_to_twd FROM currency_cache")
        for row in cur.fetchall():
            currency_cache[row["currency"]] = float(row["rate_to_twd"])
    usd_rate = currency_cache.get("USD", 32.0)

    with get_db() as conn:
        cur = conn.cursor()
        # Filter to active holdings for this user
        cur.execute(
            "SELECT id, account_id, symbol, shares, avg_cost, total_cost, currency "
            "FROM holdings WHERE shares > 0 AND user_id = %s",
            (user_id,)
        )
        holdings = cur.fetchall()

        # Realized gains from SELL transactions for this user
        cur.execute(
            "SELECT DATE(transaction_date) as sell_date, SUM(realized_gain) as total_realized "
            "FROM transactions WHERE type = 'SELL' AND user_id = %s "
            "GROUP BY DATE(transaction_date)",
            (user_id,)
        )
        sells = cur.fetchall()

        holdings_dicts = [dict(h) for h in holdings]
        sells_dicts = [dict(s) for s in sells]

        total_value = 0.0
        total_cost = 0.0
        total_value_twd = 0.0
        total_cost_twd = 0.0
        day_change = 0.0

        for h in holdings_dicts:
            shares = float(h["shares"])
            cost_basis = float(h["avg_cost"])
            symbol = h["symbol"]
            currency = h.get("currency", "TWD")
            fx_rate = _get_currency_rate(currency_cache, currency)

            price, day_chg = _get_price(symbol, cost_basis)
            mv = price * shares
            mv_twd = mv * fx_rate
            tc = float(h["total_cost"])
            tc_twd = tc * fx_rate

            total_value += mv
            total_cost += tc
            total_value_twd += mv_twd
            total_cost_twd += tc_twd
            day_change += mv * day_chg / 100

        unrealized_gain = total_value - total_cost
        unrealized_gain_twd = total_value_twd - total_cost_twd
        unrealized_pct = (unrealized_gain_twd / total_cost_twd * 100) if total_cost_twd > 0 else 0.0

        # Realized gains
        realized_gain = sum(float(s["total_realized"]) for s in sells_dicts)

        # XIRR calculation — use actual transaction dates filtered by user
        cur.execute(
            "SELECT transaction_date, "
            "  SUM(CASE WHEN type = 'BUY' THEN -quantity * price "
            "          WHEN type = 'SELL' THEN quantity * price ELSE 0 END) AS cf "
            "FROM transactions WHERE user_id = %s "
            "GROUP BY transaction_date ORDER BY transaction_date",
            (user_id,)
        )
        tx_rows = cur.fetchall()
        if tx_rows:
            all_dates = [date.fromisoformat(str(dict(r)["transaction_date"])[:10]) for r in tx_rows]
            all_cfs = [float(dict(r)["cf"]) for r in tx_rows]
            # Add current portfolio value as final cash flow
            all_dates.append(date.today())
            all_cfs.append(total_value)
        else:
            all_dates = [date.today()]
            all_cfs = [total_value]
        annualized = xirr(all_cfs, all_dates) * 100 if len(all_cfs) >= 2 else None

        day_change_pct = (day_change / (total_value - day_change) * 100) if (total_value - day_change) > 0 else 0.0

        return PortfolioSummary(
            total_value=round(total_value_twd, 2),
            total_value_twd=round(total_value_twd, 2),
            total_cost=round(total_cost_twd, 2),
            total_cost_twd=round(total_cost_twd, 2),
            unrealized_gain=round(unrealized_gain_twd, 2),
            unrealized_gain_twd=round(unrealized_gain_twd, 2),
            unrealized_pct=round(unrealized_pct, 2),
            realized_gain=round(realized_gain, 2),
            annualized_return=round(annualized, 2) if annualized else None,
            day_change=round(day_change, 2),
            day_change_pct=round(day_change_pct, 2),
        )


@router.get("/history")
def get_history(current_user: dict = Depends(get_current_user)):
    """歷史總市值趨勢（從 portfolio_snapshots）"""
    user_id = current_user.get("user_id", 1)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT transaction_date, total_value FROM portfolio_snapshots WHERE user_id = %s ORDER BY date",
            (user_id,)
        )
        rows = cur.fetchall()
        return [{"date": str(dict(r)["transaction_date"]), "value": float(dict(r)["total_value"])} for r in rows]


@router.post("/snapshot")
def create_snapshot(snap: SnapshotCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", 1)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO portfolio_snapshots (date, total_value, user_id)
               VALUES (%s, %s, %s)
               ON CONFLICT (date, user_id) DO UPDATE SET total_value = EXCLUDED.total_value""",
            (snap.date, snap.total_value, user_id)
        )
    return {"ok": True}