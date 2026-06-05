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
    Trigger also does this, but this is used for consistency checks
    and for cases where trigger might not fire (e.g., SELL).
    """
    cur = conn.cursor()
    cur.execute(
        """SELECT
               COALESCE(SUM(CASE WHEN type='BUY' THEN quantity ELSE 0 END), 0) AS total_bought,
               COALESCE(SUM(CASE WHEN type='BUY' THEN quantity * price ELSE 0 END), 0) AS total_cost,
               COALESCE(SUM(CASE WHEN type='SELL' THEN quantity ELSE 0 END), 0) AS total_sold
           FROM transactions
           WHERE symbol = %s AND user_id = %s""",
        (symbol.upper(), user_id),
    )
    row = cur.fetchone()
    total_bought = float(row["total_bought"])
    total_cost = float(row["total_cost"])
    total_sold = float(row["total_sold"])
    net_shares = total_bought - total_sold

    if net_shares <= 0:
        cur.execute(
            "DELETE FROM holdings WHERE symbol = %s AND user_id = %s",
            (symbol.upper(), user_id),
        )
    else:
        avg_cost = total_cost / total_bought if total_bought > 0 else 0.0
        total_cost_calc = avg_cost * net_shares
        cur.execute(
            "SELECT account_id FROM holdings WHERE symbol = %s AND user_id = %s LIMIT 1",
            (symbol.upper(), user_id),
        )
        existing = cur.fetchone()
        account_id = existing["account_id"] if existing else 1

        cur.execute(
            """INSERT INTO holdings (account_id, symbol, shares, avg_cost, total_cost, currency, user_id)
               VALUES (%s, %s, %s, %s, %s,
                       (SELECT currency FROM accounts WHERE id = %s LIMIT 1),
                       %s)
               ON CONFLICT (account_id, symbol) DO UPDATE SET
                   shares = EXCLUDED.shares,
                   avg_cost = EXCLUDED.avg_cost,
                   total_cost = EXCLUDED.total_cost,
                   user_id = COALESCE(holdings.user_id, EXCLUDED.user_id)""",
            (account_id, symbol.upper(), net_shares, avg_cost, total_cost_calc, account_id, user_id),
        )


@router.get("", response_model=list[TransactionOut])
def list_transactions(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", 1)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, account_id, symbol, LOWER(type::text) AS type,
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
            # Cast timestamp to date (date_from_datetime_inexact if time component present)
            tx_date = d["date"]
            if hasattr(tx_date, 'date'):
                tx_date = tx_date.date()
            result.append(TransactionOut(
                id=d["id"],
                account_id=d["account_id"],
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
    user_id = current_user.get("user_id", 1)
    with get_db() as conn:
        cur = conn.cursor()

        realized_gain = 0.0
        if tx.type.lower() == "sell":
            # Validate: cannot sell more shares than currently held
            cur.execute(
                "SELECT shares FROM holdings WHERE symbol = %s AND user_id = %s",
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

        cur.execute(
            """INSERT INTO transactions (account_id, symbol, type, quantity, price, transaction_date, realized_gain, user_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id, account_id, symbol, LOWER(type::text) AS type,
                         quantity AS shares, price, transaction_date AS date, realized_gain""",
            (tx.account_id, tx.symbol.upper(), tx.type.upper(), tx.shares, tx.price, tx.date, realized_gain, user_id),
        )
        row = cur.fetchone()

        # Recompute holdings after BUY or SELL
        _recompute_holdings(conn, tx.symbol, user_id)

        d = dict(row)
        result = TransactionOut(
            id=d["id"],
            account_id=d["account_id"],
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
            symbol=tx.symbol.upper(),
            tx_type=tx.type.upper(),
            user_id=user_id,
            details={"shares": tx.shares, "price": tx.price},
        )

        return result


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", 1)
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