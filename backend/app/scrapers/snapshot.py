"""
Daily portfolio snapshot — writes total_value to portfolio_snapshots.
Run AFTER scraper has updated price_history tables.

Usage after scraper:
    python -m app.scrapers.snapshot

Or as standalone cron (30min after US scraper):
    python -m app.scrapers.snapshot us
    python -m app.scrapers.snapshot tw
"""
import sys
sys.path.insert(0, '/home/lewis/wealth/backend')

import argparse
import json
import logging
from datetime import date, datetime, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import get_settings
from app.middleware import log_scraper_event
from app.logging_config import logger

settings = get_settings()


def _conn():
    return psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)


def _write_snapshot(total_value: float, snapshot_date: date, market: str = "ALL"):
    """Write one snapshot record. Returns id."""
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO portfolio_snapshots (date, total_value)
        VALUES (%s, %s)
        ON CONFLICT (date) DO UPDATE SET total_value = EXCLUDED.total_value
        RETURNING id
    """, (snapshot_date, total_value))
    row_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return row_id


def _get_price_from_db(symbol: str) -> float:
    """Get latest close price from local price_history tables."""
    tables = [
        ("price_history_us", "USD", "US"),
        ("price_history_tw", "TWD", "TWSE"),
    ]
    for table, currency, source in tables:
        try:
            conn = _conn()
            cur = conn.cursor()
            cur.execute(f"""
                SELECT close FROM {table}
                WHERE symbol = %s
                ORDER BY price_date DESC LIMIT 1
            """, (symbol,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return float(row["close"])
        except Exception:
            pass
    return 0.0


def _get_usd_to_twd() -> float:
    """Get USD/TWD rate from DB or fallback to yfinance."""
    # Try DB first
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM price_history_us
            WHERE symbol = 'USDTWD=X'
            ORDER BY price_date DESC LIMIT 1
        """)
        row = cur.fetchone()
        cur.close()
        if row:
            return float(row["close"])
    # fallback: yfinance live
    try:
        import yfinance as yf
        ticker = yf.Ticker("USDTWD=X")
        hist = ticker.history(period="5d")
        if len(hist) > 0:
            return round(float(hist["Close"].iloc[-1]), 4)
    except Exception:
        pass
    return 32.5  # hard fallback


def compute_snapshot() -> dict:
    """
    Compute total portfolio value using LOCAL price_history.
    Returns {total_value, breakdown, date, fx_rate}
    """
    fx_rate = _get_usd_to_twd()
    breakdown = []
    total_twd = 0.0

    with _conn() as conn:
        cur = conn.cursor()

        # Get holdings grouped by account
        cur.execute("""
            SELECT h.account_id, h.symbol, h.shares, h.total_cost,
                   a.currency
            FROM holdings h
            JOIN accounts a ON a.id = h.account_id
        """)

        holdings_rows = cur.fetchall()
        cur.close()

    for row in holdings_rows:
        sym = row["symbol"]
        shares = float(row["shares"])
        cost_basis = float(row["total_cost"])
        currency = row["currency"]

        price = _get_price_from_db(sym)

        if currency == "USD":
            value_twd = price * shares * fx_rate
            cost_twd = cost_basis * shares * fx_rate
        else:
            value_twd = price * shares
            cost_twd = cost_basis * shares

        total_twd += value_twd
        breakdown.append({
            "symbol": sym,
            "shares": shares,
            "price": price,
            "value_twd": round(value_twd, 2),
            "cost_twd": round(cost_twd, 2),
            "gain_twd": round(value_twd - cost_twd, 2),
            "currency": currency,
        })

    return {
        "total_value": round(total_twd, 2),
        "breakdown": breakdown,
        "date": date.today().strftime("%Y-%m-%d"),
        "fx_rate": round(fx_rate, 4),
    }


def _write_audit(symbols: list, total_value: float, date: str, status: str):
    """Write audit log entry for snapshot."""
    try:
        conn = _conn()
        cur = conn.cursor()
        ts = datetime.now(timezone.utc).isoformat()
        type_ = "db_change"
        level = "INFO" if status == "SUCCESS" else "ERROR"
        message = f"庫存快照: {len(symbols)}筆持倉 | {date} | 總值 NT${total_value:,.2f} | SUCCESS"
        cur.execute("""
            INSERT INTO audit_log (timestamp, type, level, message, details)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            ts, type_, level, message,
            json.dumps({"symbols": symbols, "total_value": total_value,
                        "date": date, "status": status})
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error("Audit log write failed: %s", e)


def run_snapshot(only_market: str = None) -> dict:
    """
    Full snapshot run. Optionally restrict to US/TW market.
    Returns summary dict.
    """
    today = date.today()
    logger.info("=" * 60)
    logger.info("Portfolio snapshot starting | market=%s | date=%s", only_market or "ALL", today)
    logger.info("=" * 60)

    snapshot = compute_snapshot()
    if not snapshot:
        logger.error("No snapshot computed — no accounts?")
        return None

    symbols = [b["symbol"] for b in snapshot["breakdown"]]
    total = snapshot["total_value"]

    row_id = _write_snapshot(total, today)

    logger.info("Snapshot written: id=%s | %s | total=NT$%s", row_id, today, f"{total:,.2f}")
    for b in snapshot["breakdown"]:
        logger.info("  %s: %s shares × price=%s = NT$%s  (gain: %s)",
                    b["symbol"], f"{b['shares']:,}", b["price"],
                    f"{b['value_twd']:,.2f}", f"{b['gain_twd']:,.2f}")

    # Write to audit_log
    _write_audit(symbols, total, str(today), "SUCCESS")

    # Also log as scraper_event for UI visibility
    log_scraper_event(
        "snapshot", "complete",
        symbols=symbols, total_value=total,
        date=str(today), fx_rate=snapshot["fx_rate"],
        records=len(symbols)
    )

    logger.info("Snapshot complete: %d holdings, NT$%s total", len(symbols), f"{total:,.2f}")
    return snapshot


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Portfolio snapshot after scraper runs")
    parser.add_argument("market", nargs="?", choices=["us", "tw"],
                        help="'us' or 'tw' to filter by market, omit for full snapshot")
    args = parser.parse_args()

    result = run_snapshot(only_market=args.market)
    if result:
        print(json.dumps({
            "date": result["date"],
            "total_value": result["total_value"],
            "fx_rate": result["fx_rate"],
            "holdings": result["breakdown"],
        }, indent=2, ensure_ascii=False))
