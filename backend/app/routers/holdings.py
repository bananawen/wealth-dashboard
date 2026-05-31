from fastapi import APIRouter, HTTPException, Depends
from ..models import HoldingCreate, HoldingUpdate, HoldingOut
from ..database import get_db
from ..routers.auth import get_current_user
from ..services.audit import log_holding_change
import yfinance as yf

router = APIRouter(prefix="/holdings", tags=["holdings"])

# Known OTC stocks (上櫃) that need .OB suffix
OTC_STOCKS = {"00887"}


def _get_exchange(symbol: str) -> str:
    """Return exchange for a symbol: TWSE (上市), OTC (上櫃), US, etc."""
    if symbol in OTC_STOCKS:
        return "OTC"
    if symbol.isdigit():
        return "TWSE"
    return "US"


def _get_price(symbol: str, avg_cost: float = 0.0) -> tuple[float, float, str]:
    """
    Get price, day_change%, exchange for a symbol.
    上市用 .TW，上櫃用 .OB.
    Falls back to avg_cost if Yahoo Finance returns 0.
    Returns (price, day_change_pct, exchange).
    """
    exchange = _get_exchange(symbol)

    if exchange == "TWSE":
        try:
            ticker = yf.Ticker(f"{symbol}.TW")
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = float(hist["Close"].iloc[-2])
                curr_close = float(hist["Close"].iloc[-1])
                change_pct = (curr_close - prev_close) / prev_close * 100
                return curr_close, change_pct, exchange
            elif len(hist) == 1:
                curr_close = float(hist["Close"].iloc[-1])
                if curr_close > 0:
                    return curr_close, 0.0, exchange
        except Exception:
            pass

    if exchange == "OTC":
        try:
            ticker = yf.Ticker(f"{symbol}.OB")
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = float(hist["Close"].iloc[-2])
                curr_close = float(hist["Close"].iloc[-1])
                change_pct = (curr_close - prev_close) / prev_close * 100
                return curr_close, change_pct, exchange
            elif len(hist) == 1:
                curr_close = float(hist["Close"].iloc[-1])
                if curr_close > 0:
                    return curr_close, 0.0, exchange
        except Exception:
            pass

    if avg_cost > 0:
        return avg_cost, 0.0, exchange

    return 0.0, 0.0, exchange


def _row_to_holding(row) -> HoldingOut:
    """Map a holdings DB row to HoldingOut (uses actual DB schema)."""
    d = dict(row)
    return HoldingOut(
        id=d["id"],
        account_id=d["account_id"],
        symbol=d["symbol"],
        shares=float(d["shares"]),
        avg_cost=float(d["avg_cost"]),
        total_cost=float(d["total_cost"]),
        currency=d.get("currency", "TWD"),
    )


@router.get("", response_model=list[HoldingOut])
def list_holdings(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", 1)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, account_id, symbol, shares, avg_cost, total_cost, currency "
            "FROM holdings WHERE shares > 0 AND user_id = %s ORDER BY id",
            (user_id,)
        )
        rows = cur.fetchall()
        return [_row_to_holding(row) for row in rows]


@router.post("", response_model=HoldingOut)
def create_holding(holding: HoldingCreate, current_user: dict = Depends(get_current_user)):
    """
    Create a holding by inserting a BUY transaction.
    The trigger on transactions table will sync holdings automatically.
    """
    user_id = current_user.get("user_id", 1)
    
    with get_db() as conn:
        cur = conn.cursor()
        
        # Insert a BUY transaction - trigger will create holdings entry
        cur.execute(
            """INSERT INTO transactions (account_id, symbol, type, quantity, price, transaction_date, user_id)
               VALUES (%s, %s, 'BUY', %s, %s, NOW(), %s)
               RETURNING id, account_id, symbol, quantity, price, user_id""",
            (holding.account_id, holding.symbol.upper(), holding.shares, holding.avg_cost, user_id),
        )
        tx_row = cur.fetchone()
        conn.commit()
        
        # Fetch the newly created holding (trigger created it)
        cur.execute(
            "SELECT id, account_id, symbol, shares, avg_cost, total_cost, currency "
            "FROM holdings WHERE account_id = %s AND symbol = %s AND user_id = %s",
            (holding.account_id, holding.symbol.upper(), user_id),
        )
        h_row = cur.fetchone()
        
        if h_row:
            result = _row_to_holding(h_row)
            log_holding_change(
                action="create",
                holding_id=result.id,
                symbol=holding.symbol.upper(),
                user_id=user_id,
                details={"shares": holding.shares, "avg_cost": holding.avg_cost, "tx_id": tx_row["id"]},
            )
            return result
        
        raise HTTPException(status_code=500, detail="Failed to create holding")


@router.put("/{holding_id}", response_model=HoldingOut)
def update_holding(holding_id: int, holding: HoldingUpdate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", 1)
    fields = []
    vals = []
    if holding.symbol is not None:
        fields.append("symbol = %s")
        vals.append(holding.symbol.upper())
    if holding.shares is not None:
        fields.append("shares = %s")
        vals.append(holding.shares)
    if holding.avg_cost is not None:
        fields.append("avg_cost = %s")
        vals.append(holding.avg_cost)
    if holding.total_cost is not None:
        fields.append("total_cost = %s")
        vals.append(holding.total_cost)
    if holding.currency is not None:
        fields.append("currency = %s")
        vals.append(holding.currency)
    if not fields:
        raise HTTPException(status_code=400, detail="沒有欄位要更新")
    vals.append(holding_id)
    vals.append(user_id)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE holdings SET {', '.join(fields)} WHERE id = %s AND user_id = %s "
            f"RETURNING id, account_id, symbol, shares, avg_cost, total_cost, currency",
            vals
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="找不到該持倉")
        result = _row_to_holding(row)
        log_holding_change(
            action="update",
            holding_id=holding_id,
            symbol=row["symbol"],
            user_id=user_id,
        )
        return result


@router.get("/computed")
def get_computed_holdings(current_user: dict = Depends(get_current_user)):
    """Fetch all active holdings with real-time market prices computed."""
    user_id = current_user.get("user_id", 1)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, account_id, symbol, shares, avg_cost, total_cost, currency "
            "FROM holdings WHERE shares > 0 AND user_id = %s ORDER BY symbol",
            (user_id,)
        )
        rows = cur.fetchall()

    result = []
    for row in rows:
        d = dict(row)
        symbol = d["symbol"]
        shares = float(d["shares"])
        avg_cost = float(d["avg_cost"])
        total_cost = float(d["total_cost"])
        currency = d.get("currency", "TWD")

        price, day_chg, exchange = _get_price(symbol, avg_cost)

        if price == 0 and avg_cost > 0:
            price = avg_cost

        market_value = price * shares
        unrealized_gain = market_value - total_cost
        unrealized_pct = (unrealized_gain / total_cost * 100) if total_cost > 0 else 0.0

        result.append({
            "symbol": symbol,
            "shares": shares,
            "avg_cost": avg_cost,
            "total_cost": round(total_cost, 2),
            "market_value": round(market_value, 2),
            "unrealized_gain": round(unrealized_gain, 2),
            "unrealized_pct": round(unrealized_pct, 2),
            "current_price": round(price, 2),
            "day_change_pct": round(day_chg, 2),
            "currency": currency,
            "exchange": exchange,
        })

    return result


@router.delete("/{holding_id}")
def delete_holding(holding_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", 1)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM holdings WHERE id = %s AND user_id = %s RETURNING id, symbol",
            (holding_id, user_id)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="找不到該持倉")
        log_holding_change(
            action="delete",
            holding_id=holding_id,
            symbol=row["symbol"],
            user_id=user_id,
        )
    return {"ok": True}