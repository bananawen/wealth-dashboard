from datetime import date, datetime
from fastapi import APIRouter, Depends
from ..models import PortfolioSummary, SnapshotCreate
from ..database import get_db
from ..routers.auth import get_current_user
from ..routers.holdings import _get_price_cached
from scipy.optimize import brentq

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


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

            price, day_chg, _ = _get_price_cached(symbol, cost_basis)
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

        # XIRR calculation — all cash flows in TWD
        cur.execute(
            "SELECT transaction_date, currency, "
            "  SUM(CASE WHEN type = 'BUY' THEN -quantity * price "
            "          WHEN type = 'SELL' THEN quantity * price ELSE 0 END) AS cf "
            "FROM transactions WHERE user_id = %s "
            "GROUP BY transaction_date, currency ORDER BY transaction_date",
            (user_id,)
        )
        tx_rows = cur.fetchall()
        if tx_rows:
            all_dates = [date.fromisoformat(str(dict(r)["transaction_date"])[:10]) for r in tx_rows]
            all_cfs = []
            for r in tx_rows:
                cf_twd = float(dict(r)["cf"]) * _get_currency_rate(currency_cache, dict(r)["currency"])
                all_cfs.append(cf_twd)
            # Add current portfolio value as final cash flow (already in TWD)
            all_dates.append(date.today())
            all_cfs.append(total_value_twd)
        else:
            all_dates = [date.today()]
            all_cfs = [total_value_twd]
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
            "SELECT date, total_value FROM portfolio_snapshots WHERE user_id = %s ORDER BY date",
            (user_id,)
        )
        rows = cur.fetchall()
        return [{"date": str(dict(r)["date"]), "value": float(dict(r)["total_value"])} for r in rows]


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