from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from math import isfinite

from ..database import get_db
from ..models import BenchmarkSeries, PerformancePoint, PortfolioPerformance, PortfolioSummary
from .fx_service import FxService
from .holding_service import HoldingService
from .market_service import MarketService


def xirr(cash_flows: list[float], dates: list[date]) -> float | None:
    def npv(rate):
        return sum(cf / (1 + rate) ** ((d - dates[0]).days / 365.0) for cf, d in zip(cash_flows, dates))

    try:
        low = -0.99
        high = 100.0
        low_value = npv(low)
        high_value = npv(high)
        if low_value * high_value > 0:
            return None

        for _ in range(1000):
            mid = (low + high) / 2
            mid_value = npv(mid)
            if abs(mid_value) < 1e-7:
                return mid
            if low_value * mid_value < 0:
                high = mid
                high_value = mid_value
            else:
                low = mid
                low_value = mid_value
        return (low + high) / 2
    except Exception:
        return None


class PortfolioService:
    BENCHMARKS = {
        "sp500": {"name": "S&P 500", "symbol": "SPY", "market": "US"},
        "nasdaq": {"name": "NASDAQ", "symbol": "QQQ", "market": "US"},
        "twii": {"name": "台灣加權", "symbol": "0050", "market": "TW"},
        "0050": {"name": "0050", "symbol": "0050", "market": "TW"},
    }

    @staticmethod
    def _format_xirr_price_message(
        price_dates: list[date],
        missing_symbols: list[str],
        as_of_date: date,
    ) -> tuple[str, str | None]:
        if not price_dates and missing_symbols:
            return "estimated", f"XIRR 缺少本地歷史價格，{len(missing_symbols)} 檔暫以成本價估算"
        if not price_dates:
            return "ok", "目前無持倉，XIRR 不含期末持倉估值"

        min_price_date = min(price_dates)
        max_price_date = max(price_dates)
        if min_price_date == max_price_date:
            base_message = f"依本地歷史收盤價計算（價格日：{max_price_date.isoformat()}）"
        else:
            base_message = (
                "依本地歷史收盤價計算"
                f"（價格日介於 {min_price_date.isoformat()} 至 {max_price_date.isoformat()}）"
            )

        if missing_symbols:
            return (
                "estimated",
                f"{base_message}；{len(missing_symbols)} 檔缺本地價格，改以成本價估算",
            )

        if max_price_date < as_of_date:
            return "ok", f"{base_message}（非即時報價）"
        return "ok", base_message

    @classmethod
    def _get_xirr_terminal_value_twd(
        cls,
        user_id: int,
        as_of_date: date,
        rates: dict[str, float],
    ) -> tuple[float, str, str | None]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT symbol, shares, avg_cost, currency "
                "FROM holdings WHERE shares > 0 AND user_id = %s ORDER BY symbol",
                (user_id,),
            )
            holdings = [dict(row) for row in cur.fetchall()]

            total_value_twd = 0.0
            price_dates: list[date] = []
            missing_symbols: list[str] = []

            for row in holdings:
                symbol = MarketService.normalize_symbol(str(row["symbol"]))
                shares = float(row["shares"] or 0.0)
                avg_cost = float(row["avg_cost"] or 0.0)
                currency = FxService.normalize_currency(row.get("currency"))
                profile = MarketService.get_symbol_profile(conn, symbol)

                cur.execute(
                    f"""
                    SELECT price_date, close
                    FROM {profile.history_table}
                    WHERE symbol = %s AND price_date <= %s
                    ORDER BY price_date DESC
                    LIMIT 1
                    """,
                    (symbol, as_of_date),
                )
                latest_row = cur.fetchone()

                if latest_row and float(latest_row["close"] or 0.0) > 0:
                    price = float(latest_row["close"])
                    price_dates.append(date.fromisoformat(str(latest_row["price_date"])[:10]))
                else:
                    price = avg_cost
                    missing_symbols.append(symbol)

                fx_rate = FxService.get_rate_to_twd_from_rates(rates, currency)
                total_value_twd += shares * price * fx_rate

        status, message = cls._format_xirr_price_message(price_dates, missing_symbols, as_of_date)
        return total_value_twd, status, message

    @staticmethod
    def _get_realized_gain_twd(user_id: int, rates: dict[str, float]) -> float:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT currency, SUM(realized_gain) AS total_realized "
                "FROM transactions WHERE type = 'SELL' AND user_id = %s "
                "GROUP BY currency",
                (user_id,),
            )
            rows = cur.fetchall()

        total = 0.0
        for row in rows:
            currency = row["currency"]
            realized = float(row["total_realized"] or 0.0)
            total += realized * FxService.get_rate_to_twd_from_rates(rates, currency)
        return total

    @staticmethod
    def _get_realized_gain_by_currency(user_id: int) -> dict[str, float]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT currency, SUM(realized_gain) AS total_realized "
                "FROM transactions WHERE type = 'SELL' AND user_id = %s "
                "GROUP BY currency",
                (user_id,),
            )
            rows = cur.fetchall()
        return {
            FxService.normalize_currency(row["currency"]): round(float(row["total_realized"] or 0.0), 2)
            for row in rows
        }

    @staticmethod
    def _build_currency_breakdowns(positions: list, rates: dict[str, float]) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
        total_value_by_currency: dict[str, float] = defaultdict(float)
        total_cost_by_currency: dict[str, float] = defaultdict(float)
        unrealized_gain_by_currency: dict[str, float] = defaultdict(float)

        for position in positions:
            currency = FxService.normalize_currency(position.currency)
            total_value_by_currency[currency] += float(position.market_value)
            total_cost_by_currency[currency] += float(position.total_cost)
            unrealized_gain_by_currency[currency] += float(position.unrealized_gain)

        return (
            {k: round(v, 2) for k, v in total_value_by_currency.items()},
            {k: round(v, 2) for k, v in total_cost_by_currency.items()},
            {k: round(v, 2) for k, v in unrealized_gain_by_currency.items()},
        )

    @classmethod
    def _get_annualized_return(
        cls,
        user_id: int,
        rates: dict[str, float],
    ) -> tuple[float | None, str, str | None]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT transaction_date, currency, "
                "  SUM(CASE WHEN type = 'BUY' THEN -quantity * price "
                "          WHEN type = 'SELL' THEN quantity * price ELSE 0 END) AS cf "
                "FROM transactions WHERE user_id = %s "
                "GROUP BY transaction_date, currency ORDER BY transaction_date",
                (user_id,),
            )
            rows = cur.fetchall()

        if not rows:
            return None, "insufficient_data", "沒有足夠交易資料可計算 XIRR"

        all_dates = [date.fromisoformat(str(dict(row)["transaction_date"])[:10]) for row in rows]
        all_cash_flows = []
        for row in rows:
            d = dict(row)
            cf_twd = float(d["cf"] or 0.0) * FxService.get_rate_to_twd_from_rates(rates, d.get("currency"))
            all_cash_flows.append(cf_twd)

        terminal_value_twd, terminal_status, terminal_message = cls._get_xirr_terminal_value_twd(
            user_id,
            as_of_date=date.today(),
            rates=rates,
        )
        all_dates.append(date.today())
        all_cash_flows.append(terminal_value_twd)
        if len(all_cash_flows) < 2:
            return None, "insufficient_data", "交易筆數不足，無法計算 XIRR"

        result = xirr(all_cash_flows, all_dates)
        if result is None or not isfinite(result):
            return None, "failed", "XIRR 計算失敗，請確認現金流方向與資料完整性"

        return result * 100, terminal_status, terminal_message

    @staticmethod
    def _get_history_rows(user_id: int, start_date: date | None = None) -> list[dict]:
        with get_db() as conn:
            cur = conn.cursor()
            params: list[object] = [user_id]
            sql = "SELECT date, total_value FROM portfolio_snapshots WHERE user_id = %s"
            if start_date is not None:
                sql += " AND date >= %s"
                params.append(start_date)
            sql += " ORDER BY date"
            cur.execute(sql, tuple(params))
            return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _get_transaction_rows(user_id: int, end_date: date) -> list[dict]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT symbol, type, quantity, price, transaction_date, currency, id
                FROM transactions
                WHERE user_id = %s AND transaction_date <= %s
                ORDER BY transaction_date, id
                """,
                (user_id, end_date),
            )
            return [dict(row) for row in cur.fetchall()]

    @classmethod
    def _build_fallback_history_rows(
        cls,
        user_id: int,
        start_date: date | None,
        end_date: date,
        current_total_value: float,
    ) -> list[dict]:
        tx_rows = cls._get_transaction_rows(user_id, end_date)
        if not tx_rows:
            return []

        parsed_transactions: list[dict] = []
        symbols: set[str] = set()
        first_tx_date: date | None = None
        for row in tx_rows:
            tx_date = date.fromisoformat(str(row["transaction_date"])[:10])
            parsed_row = {
                "symbol": MarketService.normalize_symbol(str(row["symbol"])),
                "type": str(row["type"]).upper(),
                "quantity": float(row["quantity"] or 0.0),
                "price": float(row["price"] or 0.0),
                "currency": FxService.normalize_currency(row.get("currency")),
                "transaction_date": tx_date,
            }
            parsed_transactions.append(parsed_row)
            symbols.add(parsed_row["symbol"])
            if first_tx_date is None or tx_date < first_tx_date:
                first_tx_date = tx_date

        if first_tx_date is None:
            return []

        series_start = max(first_tx_date, start_date) if start_date is not None else first_tx_date
        if series_start > end_date:
            return []

        rates = FxService.load_rates()
        txs_by_date: dict[date, list[dict]] = defaultdict(list)
        for row in parsed_transactions:
            txs_by_date[row["transaction_date"]].append(row)

        with get_db() as conn:
            symbol_profiles = {symbol: MarketService.get_symbol_profile(conn, symbol) for symbol in symbols}
            price_history_by_symbol: dict[str, list[tuple[date, float]]] = {}
            for symbol, profile in symbol_profiles.items():
                cur = conn.cursor()
                cur.execute(
                    f"""
                    SELECT price_date, close
                    FROM {profile.history_table}
                    WHERE symbol = %s AND price_date >= %s AND price_date <= %s
                    ORDER BY price_date
                    """,
                    (symbol, first_tx_date, end_date),
                )
                price_history_by_symbol[symbol] = [
                    (date.fromisoformat(str(row["price_date"])[:10]), float(row["close"] or 0.0))
                    for row in cur.fetchall()
                ]

        held_shares: dict[str, float] = defaultdict(float)
        fallback_trade_price: dict[str, float] = {}
        latest_close: dict[str, float] = {}
        price_index: dict[str, int] = {symbol: 0 for symbol in symbols}
        rows: list[dict] = []
        cursor = first_tx_date

        while cursor <= end_date:
            for tx in txs_by_date.get(cursor, []):
                quantity = tx["quantity"]
                if tx["type"] == "BUY":
                    held_shares[tx["symbol"]] += quantity
                elif tx["type"] == "SELL":
                    held_shares[tx["symbol"]] = max(0.0, held_shares[tx["symbol"]] - quantity)
                if tx["price"] > 0:
                    fallback_trade_price[tx["symbol"]] = tx["price"]

            for symbol in symbols:
                history = price_history_by_symbol.get(symbol, [])
                idx = price_index[symbol]
                while idx < len(history) and history[idx][0] <= cursor:
                    latest_close[symbol] = history[idx][1]
                    idx += 1
                price_index[symbol] = idx

            if cursor >= series_start:
                total_value_twd = 0.0
                for symbol, shares in held_shares.items():
                    if shares <= 0:
                        continue
                    price = latest_close.get(symbol) or fallback_trade_price.get(symbol)
                    if not price or price <= 0:
                        continue
                    currency = symbol_profiles[symbol].currency
                    fx_rate = FxService.get_rate_to_twd_from_rates(rates, currency)
                    total_value_twd += shares * price * fx_rate
                if total_value_twd > 0:
                    rows.append({"date": cursor, "total_value": round(total_value_twd, 2)})

            cursor += timedelta(days=1)

        if rows:
            rows[-1] = {"date": end_date, "total_value": round(current_total_value, 2)}
        return rows

    @staticmethod
    def _normalize_series(rows: list[dict], key: str = "total_value") -> list[PerformancePoint]:
        if not rows:
            return []
        first_value = float(rows[0][key] or 0.0)
        if first_value <= 0:
            return []
        return [
            PerformancePoint(
                date=str(row["date"]),
                value=round(float(row[key] or 0.0), 2),
                normalized_value=round(float(row[key] or 0.0) / first_value * 100, 2),
            )
            for row in rows
        ]

    @classmethod
    def _get_benchmark_series(cls, start_date: date, end_date: date) -> list[BenchmarkSeries]:
        benchmarks: list[BenchmarkSeries] = []
        with get_db() as conn:
            cur = conn.cursor()
            for cfg in cls.BENCHMARKS.values():
                table = "price_history_us" if cfg["market"] == "US" else "price_history_tw"
                cur.execute(
                    f"""
                    SELECT price_date, close
                    FROM {table}
                    WHERE symbol = %s AND price_date >= %s AND price_date <= %s
                    ORDER BY price_date
                    """,
                    (cfg["symbol"], start_date, end_date),
                )
                rows = [dict(row) for row in cur.fetchall()]
                if not rows:
                    continue
                first = float(rows[0]["close"] or 0.0)
                if first <= 0:
                    continue
                points = [
                    PerformancePoint(
                        date=str(row["price_date"]),
                        value=round(float(row["close"] or 0.0), 2),
                        normalized_value=round(float(row["close"] or 0.0) / first * 100, 2),
                    )
                    for row in rows
                ]
                benchmarks.append(
                    BenchmarkSeries(
                        name=cfg["name"],
                        symbol=cfg["symbol"],
                        market=cfg["market"],
                        points=points,
                    )
                )
        return benchmarks

    @classmethod
    def get_summary(cls, user_id: int) -> PortfolioSummary:
        rates = FxService.load_rates()
        positions = HoldingService.get_computed_positions(user_id)
        total_value_by_currency, total_cost_by_currency, unrealized_gain_by_currency = cls._build_currency_breakdowns(positions, rates)
        realized_gain_by_currency = cls._get_realized_gain_by_currency(user_id)

        total_value_twd = sum(position.market_value_twd for position in positions)
        total_cost_twd = sum(position.total_cost_twd for position in positions)
        unrealized_gain_twd = total_value_twd - total_cost_twd
        unrealized_pct = (unrealized_gain_twd / total_cost_twd * 100) if total_cost_twd > 0 else 0.0
        day_change_twd = sum(position.day_change_twd for position in positions)
        previous_value_twd = total_value_twd - day_change_twd
        day_change_pct = (day_change_twd / previous_value_twd * 100) if previous_value_twd > 0 else 0.0
        realized_gain_twd = cls._get_realized_gain_twd(user_id, rates)
        annualized, annualized_status, annualized_message = cls._get_annualized_return(user_id, rates)
        now = datetime.now(timezone.utc).isoformat()

        return PortfolioSummary(
            total_value=round(total_value_twd, 2),
            total_value_twd=round(total_value_twd, 2),
            total_value_by_currency=total_value_by_currency,
            total_cost=round(total_cost_twd, 2),
            total_cost_twd=round(total_cost_twd, 2),
            total_cost_by_currency=total_cost_by_currency,
            unrealized_gain=round(unrealized_gain_twd, 2),
            unrealized_gain_twd=round(unrealized_gain_twd, 2),
            unrealized_gain_by_currency=unrealized_gain_by_currency,
            unrealized_pct=round(unrealized_pct, 2),
            realized_gain=round(realized_gain_twd, 2),
            realized_gain_twd=round(realized_gain_twd, 2),
            realized_gain_by_currency=realized_gain_by_currency,
            annualized_return=round(annualized, 2) if annualized is not None else None,
            annualized_return_status=annualized_status,
            annualized_return_message=annualized_message,
            day_change=round(day_change_twd, 2),
            day_change_pct=round(day_change_pct, 2),
            fx_rate=round(FxService.get_rate_to_twd_from_rates(rates, "USD"), 6),
            last_updated=now,
        )

    @classmethod
    def get_performance(cls, user_id: int, range_key: str = "all") -> PortfolioPerformance:
        today = date.today()
        range_key = (range_key or "all").lower()
        range_map = {
            "today": 0,
            "week": 7,
            "month": 30,
            "year": 365,
            "all": None,
        }
        days = range_map.get(range_key, None)
        start_date = today - timedelta(days=days) if days is not None else None
        current_summary = cls.get_summary(user_id)
        rows = cls._get_history_rows(user_id, start_date)

        if not rows:
            rows = cls._build_fallback_history_rows(
                user_id,
                start_date=start_date,
                end_date=today,
                current_total_value=current_summary.total_value_twd or current_summary.total_value,
            )

        if not rows or str(rows[-1]["date"]) != str(today):
            rows.append({"date": today, "total_value": current_summary.total_value_twd or current_summary.total_value})

        if not rows:
            return PortfolioPerformance(range=range_key, start_date=str(today), end_date=str(today), portfolio=[], benchmarks=[])

        portfolio = cls._normalize_series(rows)
        if not portfolio:
            return PortfolioPerformance(range=range_key, start_date=str(rows[0]["date"]), end_date=str(rows[-1]["date"]), portfolio=[], benchmarks=[])

        first_date = date.fromisoformat(str(rows[0]["date"]))
        last_date = date.fromisoformat(str(rows[-1]["date"]))
        benchmarks = cls._get_benchmark_series(first_date, last_date)
        return PortfolioPerformance(
            range=range_key,
            start_date=str(rows[0]["date"]),
            end_date=str(rows[-1]["date"]),
            portfolio=portfolio,
            benchmarks=benchmarks,
        )
