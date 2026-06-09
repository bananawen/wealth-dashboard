from fastapi import APIRouter, HTTPException, Depends
from ..models import TransactionCreate, TransactionOut
from ..database import get_db
from ..routers.auth import get_current_user
from ..services.audit import log_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _recompute_holdings(conn, symbol: str, user_id: int):
    """
    根據 transactions 表重新計算某檔股票的持有股數與平均成本，
    結果寫回 holdings 表（upsert）。
    """
    cur = conn.cursor()
    # Get USD rate for total_cost_twd calculation
    cur.execute("SELECT currency, rate_to_twd FROM currency_cache")
    fx_rates = {row["currency"]: float(row["rate_to_twd"]) for row in cur.fetchall()}
    usd_rate = fx_rates.get("USD", 32.0)

    cur.execute(
        """SELECT
               COALESCE(SUM(CASE WHEN type='BUY' THEN quantity ELSE 0 END), 0) AS total_bought,
               COALESCE(SUM(CASE WHEN type='BUY' THEN quantity * price ELSE 0 END), 0) AS total_cost,
               COALESCE(SUM(CASE WHEN type='SELL' THEN quantity ELSE 0 END), 0) AS total_sold,
               currency
           FROM transactions
           WHERE symbol = %s AND user_id = %s
           GROUP BY currency""",
        (symbol.upper(), user_id),
    )
    rows = cur.fetchall()
    if not rows:
        cur.execute(
            "DELETE FROM holdings WHERE symbol = %s AND user_id = %s",
            (symbol.upper(), user_id),
        )
        return

    # Aggregate across currencies
    total_bought = sum(float(r["total_bought"]) for r in rows)
    total_cost = sum(float(r["total_cost"]) for r in rows)
    total_sold = sum(float(r["total_sold"]) for r in rows)
    # Use currency of first BUY row (all BUY rows for same symbol should have same currency)
    currency = next((r["currency"] for r in rows if r["total_bought"] > 0), 'TWD')
    net_shares = total_bought - total_sold

    if net_shares <= 0:
        cur.execute(
            "DELETE FROM holdings WHERE symbol = %s AND user_id = %s",
            (symbol.upper(), user_id),
        )
    else:
        avg_cost = total_cost / total_bought if total_bought > 0 else 0.0
        total_cost_calc = avg_cost * net_shares
        fx_rate = 1.0 if currency == 'TWD' else usd_rate
        total_cost_twd = total_cost_calc * fx_rate
        cur.execute(
            """INSERT INTO holdings (symbol, shares, avg_cost, total_cost, currency, total_cost_twd, user_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (user_id, symbol) DO UPDATE SET
                   shares = EXCLUDED.shares,
                   avg_cost = EXCLUDED.avg_cost,
                   total_cost = EXCLUDED.total_cost,
                   currency = EXCLUDED.currency,
                   total_cost_twd = EXCLUDED.total_cost_twd""",
            (symbol.upper(), net_shares, avg_cost, total_cost_calc, currency, total_cost_twd, user_id),
        )


@router.get("", response_model=list[TransactionOut])
def list_transactions(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, symbol, LOWER(type::text) AS type,
                      quantity AS shares, price, transaction_date AS date, realized_gain
               FROM transactions
               WHERE user_id = %s
               ORDER BY transaction_date DESC""",
            (user_id,)
        )
        rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            tx_date = d["date"]
            if hasattr(tx_date, 'date'):
                tx_date = tx_date.date()
            result.append(TransactionOut(
                id=d["id"],
                symbol=d["symbol"],
                type=d["type"],
                shares=float(d["shares"]),
                price=float(d["price"]),
                date=tx_date,
                realized_gain=float(d["realized_gain"]) if d["realized_gain"] else 0.0,
            ))
        return result


@router.post("", response_model=TransactionOut)
def create_transaction(tx: TransactionCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    with get_db() as conn:
        cur = conn.cursor()

        realized_gain = 0.0
        if tx.type.lower() == "sell":
            # Validate: cannot sell more shares than currently held
            cur.execute(
                "SELECT shares, avg_cost FROM holdings WHERE symbol = %s AND user_id = %s",
                (tx.symbol.upper(), user_id),
            )
            h = cur.fetchone()
            current_shares = float(h["shares"]) if h and h["shares"] else 0.0
            if current_shares < tx.shares:
                raise HTTPException(
                    status_code=400,
                    detail=f"賣出股數不足：目前持有 {current_shares} 股，欲賣出 {tx.shares} 股"
                )
            if current_shares > 0:
                shares = float(h["shares"])
                avg_cost = float(h["avg_cost"])
                realized_gain = (tx.price - avg_cost) * tx.shares

        # Determine currency: use TWD for TW stocks, USD for US stocks as default
        symbol = tx.symbol.upper()
        if symbol.isdigit():
            currency = "TWD"
        else:
            currency = "USD"

        cur.execute(
            """INSERT INTO transactions (symbol, type, quantity, price, transaction_date, realized_gain, user_id, currency)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id, symbol, LOWER(type::text) AS type,
                         quantity AS shares, price, transaction_date AS date, realized_gain""",
            (symbol, tx.type.upper(), tx.shares, tx.price, tx.date, realized_gain, user_id, currency),
        )
        row = cur.fetchone()

        # Recompute holdings after BUY or SELL
        _recompute_holdings(conn, symbol, user_id)

        d = dict(row)
        result = TransactionOut(
            id=d["id"],
            symbol=d["symbol"],
            type=d["type"],
            shares=float(d["shares"]),
            price=float(d["price"]),
            date=d["date"],
            realized_gain=float(d["realized_gain"]) if d["realized_gain"] else 0.0,
        )

        log_transaction(
            action="create",
            tx_id=result.id,
            symbol=symbol,
            tx_type=tx.type.upper(),
            user_id=user_id,
            details={"shares": tx.shares, "price": tx.price},
        )

        return result


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT symbol FROM transactions WHERE id = %s AND user_id = %s",
            (transaction_id, user_id)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="找不到該交易")
        symbol = row["symbol"]

        cur.execute(
            "DELETE FROM transactions WHERE id = %s AND user_id = %s",
            (transaction_id, user_id)
        )

        _recompute_holdings(conn, symbol, user_id)

        log_transaction(
            action="delete",
            tx_id=transaction_id,
            symbol=symbol,
            tx_type="UNKNOWN",
            user_id=user_id,
            details={"reason": "user_deleted"},
        )

    return {"ok": True}
