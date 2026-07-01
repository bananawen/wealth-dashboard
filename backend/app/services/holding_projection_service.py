from __future__ import annotations


class HoldingProjectionService:
    @staticmethod
    def recompute_holding(conn, symbol: str, user_id: int) -> None:
        """
        Rebuild one holdings row from transactions.

        Transactions are the source of truth. Holdings is a projection used for
        fast reads and should not be directly mutated by public API handlers.
        """
        normalized_symbol = symbol.upper()
        cur = conn.cursor()
        cur.execute("SELECT currency, rate_to_twd FROM currency_cache")
        fx_rates = {row["currency"]: float(row["rate_to_twd"]) for row in cur.fetchall()}
        usd_rate = fx_rates.get("USD", 32.0)

        cur.execute(
            """SELECT
                   COALESCE(SUM(CASE WHEN type='BUY' THEN quantity ELSE 0 END), 0) AS total_bought,
                   COALESCE(SUM(CASE WHEN type='BUY' THEN quantity * price + COALESCE(fee, 0) + COALESCE(tax, 0) ELSE 0 END), 0) AS total_cost,
                   COALESCE(SUM(CASE WHEN type='SELL' THEN quantity ELSE 0 END), 0) AS total_sold,
                   currency
               FROM transactions
               WHERE symbol = %s AND user_id = %s
               GROUP BY currency""",
            (normalized_symbol, user_id),
        )
        rows = cur.fetchall()
        if not rows:
            cur.execute(
                "DELETE FROM holdings WHERE symbol = %s AND user_id = %s",
                (normalized_symbol, user_id),
            )
            return

        total_bought = sum(float(row["total_bought"]) for row in rows)
        total_cost = sum(float(row["total_cost"]) for row in rows)
        total_sold = sum(float(row["total_sold"]) for row in rows)
        currency = next((row["currency"] for row in rows if row["total_bought"] > 0), "TWD")
        net_shares = total_bought - total_sold

        if net_shares <= 0:
            cur.execute(
                "DELETE FROM holdings WHERE symbol = %s AND user_id = %s",
                (normalized_symbol, user_id),
            )
            return

        avg_cost = total_cost / total_bought if total_bought > 0 else 0.0
        total_cost_calc = avg_cost * net_shares
        fx_rate = 1.0 if currency == "TWD" else usd_rate
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
            (normalized_symbol, net_shares, avg_cost, total_cost_calc, currency, total_cost_twd, user_id),
        )
