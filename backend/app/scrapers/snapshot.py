"""
Daily portfolio snapshot - writes total_value to portfolio_snapshots.
Run AFTER scraper has updated price_history tables.

Usage after scraper:
    python -m app.scrapers.snapshot
"""
import json
from datetime import date, datetime, timezone

from app.database import get_db
from app.logging_config import logger
from app.middleware import log_scraper_event
from app.services.fx_service import FxService


def _get_usd_to_twd() -> float:
    rates = FxService.load_rates()
    return FxService.get_rate_to_twd_from_rates(rates, "USD")


def _latest_close(conn, symbol: str, currency: str) -> float:
    table = "price_history_tw" if FxService.normalize_currency(currency) == "TWD" else "price_history_us"
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT close
        FROM {table}
        WHERE symbol = %s
        ORDER BY price_date DESC
        LIMIT 1
        """,
        (symbol,),
    )
    row = cur.fetchone()
    return float(row["close"]) if row and row["close"] is not None else 0.0


def compute_snapshot_for_user(user_id: int) -> dict:
    fx_rate = _get_usd_to_twd()
    breakdown = []
    total_twd = 0.0

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT symbol, shares, total_cost, currency
            FROM holdings
            WHERE user_id = %s AND shares > 0
            ORDER BY symbol
            """,
            (user_id,),
        )
        holdings_rows = cur.fetchall()

        for row in holdings_rows:
            symbol = row["symbol"]
            shares = float(row["shares"])
            total_cost = float(row["total_cost"])
            currency = row["currency"] or ("TWD" if symbol.isdigit() else "USD")
            price = _latest_close(conn, symbol, currency)
            rate_to_twd = 1.0 if FxService.normalize_currency(currency) == "TWD" else fx_rate
            value_twd = price * shares * rate_to_twd
            cost_twd = total_cost * rate_to_twd
            total_twd += value_twd
            breakdown.append(
                {
                    "symbol": symbol,
                    "shares": shares,
                    "price": price,
                    "value_twd": round(value_twd, 2),
                    "cost_twd": round(cost_twd, 2),
                    "gain_twd": round(value_twd - cost_twd, 2),
                    "currency": currency,
                }
            )

    return {
        "user_id": user_id,
        "total_value": round(total_twd, 2),
        "breakdown": breakdown,
        "date": date.today().strftime("%Y-%m-%d"),
        "fx_rate": round(fx_rate, 4),
    }


def _write_snapshot(user_id: int, total_value: float, snapshot_date: date):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO portfolio_snapshots (date, total_value, user_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, date) DO UPDATE SET total_value = EXCLUDED.total_value
            RETURNING id
            """,
            (snapshot_date, total_value, user_id),
        )
        row = cur.fetchone()
        return row["id"] if row else None


def _write_audit(user_id: int, symbols: list[str], total_value: float, snapshot_date: str, status: str):
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO audit_log (timestamp, type, level, message, details, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    "transaction",
                    "INFO" if status == "SUCCESS" else "ERROR",
                    f"庫存快照: user={user_id} | {len(symbols)}筆持倉 | {snapshot_date} | 總值 NT${total_value:,.2f} | {status}",
                    json.dumps(
                        {
                            "symbols": symbols,
                            "total_value": total_value,
                            "date": snapshot_date,
                            "status": status,
                        }
                    ),
                    user_id,
                ),
            )
    except Exception as exc:
        logger.error("Audit log write failed: %s", exc)


def run_snapshot() -> dict | None:
    today = date.today()
    logger.info("=" * 60)
    logger.info("Portfolio snapshot starting | date=%s", today)
    logger.info("=" * 60)

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT user_id FROM holdings WHERE shares > 0 ORDER BY user_id")
        user_ids = [int(row["user_id"]) for row in cur.fetchall()]

    if not user_ids:
        logger.warning("No snapshot computed - no active holdings")
        return None

    snapshots = []
    for user_id in user_ids:
        snapshot = compute_snapshot_for_user(user_id)
        symbols = [item["symbol"] for item in snapshot["breakdown"]]
        total = snapshot["total_value"]
        row_id = _write_snapshot(user_id, total, today)
        logger.info("Snapshot written: id=%s | user=%s | %s | total=NT$%s", row_id, user_id, today, f"{total:,.2f}")
        _write_audit(user_id, symbols, total, str(today), "SUCCESS")
        log_scraper_event(
            "snapshot",
            "complete",
            symbols=symbols,
            total_value=total,
            date=str(today),
            fx_rate=snapshot["fx_rate"],
            records=len(symbols),
            user_id=user_id,
        )
        snapshots.append(snapshot)

    logger.info("Snapshot complete: %d user snapshots", len(snapshots))
    return {"date": str(today), "snapshots": snapshots}


if __name__ == "__main__":
    result = run_snapshot()
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
