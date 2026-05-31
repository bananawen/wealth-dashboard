"""
Transaction service — all transaction CRUD operations.
Keeps routers thin; handles DB + holdings sync internally.
"""
import json
import logging
import threading
from datetime import date, datetime
from typing import Optional
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pgres_insert

from ..models import Transaction, Holding, Account
from .price_service import PriceService

logger = logging.getLogger("wealth")


class TransactionService:

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def list_transactions(self) -> list[Transaction]:
        result = await self.session.execute(
            select(Transaction).order_by(Transaction.transaction_date.desc())
        )
        return list(result.scalars().all())

    async def get_transaction(self, tx_id: int) -> Optional[Transaction]:
        result = await self.session.execute(
            select(Transaction).where(Transaction.id == tx_id)
        )
        return result.scalar_one_or_none()

    async def create_transaction(
        self,
        account_id: int,
        symbol: str,
        tx_type: str,
        shares: float,
        price: float,
        tx_date: date,
        user_id: Optional[int] = None,
    ) -> Transaction:
        # Write transaction record via psycopg2 (needed for proper PostgreSQL enum handling)
        import psycopg2
        from ..config import get_settings
        settings = get_settings()
        raw_conn = psycopg2.connect(settings.DATABASE_URL)
        raw_cur = raw_conn.cursor()
        raw_cur.execute("""
            INSERT INTO transactions (account_id, symbol, type, quantity, price, fee, transaction_date, notes, realized_gain)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (account_id, symbol.upper(), tx_type.upper(), shares, price, 0, tx_date, symbol.upper(), 0))
        tx_id = raw_cur.fetchone()[0]
        raw_conn.commit()
        raw_conn.close()

        await self.session.commit()

        # Reload the inserted row to get a proper ORM object for return
        result2 = await self.session.execute(
            select(Transaction).where(Transaction.id == tx_id)
        )
        tx = result2.scalar_one()

        # Trigger `trg_sync_holdings` on transactions table handles holdings sync automatically.
        # DO NOT call sync_holdings_after_transaction() here — that would cause double counting.
        return tx

    async def update_transaction(
        self,
        tx_id: int,
        account_id: int,
        symbol: str,
        tx_type: str,
        shares: float,
        price: float,
        tx_date: date,
    ) -> Optional[Transaction]:
        tx = await self.get_transaction(tx_id)
        if not tx:
            return None

        tx.account_id = account_id
        tx.symbol = symbol.upper()
        tx.type = tx_type.upper()
        tx.quantity = shares
        tx.price = price
        tx.transaction_date = tx_date

        await self.session.commit()
        return tx

    async def delete_transaction(self, tx_id: int) -> bool:
        tx = await self.get_transaction(tx_id)
        if not tx:
            return False

        old = tx
        await self.session.execute(
            delete(Transaction).where(Transaction.id == tx_id)
        )

        # Sync holdings table: reverse the effect
        _type = old.type
        _shares = float(old.quantity)
        _price = float(old.price)
        _account_id = int(old.account_id)
        _symbol = old.symbol

        if _type in ("BUY", "buy"):
            # No trigger fires on DELETE — manually reverse: subtract shares/cost
            await self.session.execute(
                text("""
                    UPDATE holdings
                    SET shares = holdings.shares - :shares,
                        total_cost = holdings.total_cost - :total_cost,
                        avg_cost = CASE
                            WHEN holdings.shares - :shares > 0
                            THEN (holdings.total_cost - :total_cost) / (holdings.shares - :shares)
                            ELSE 0 END
                    WHERE holdings.account_id = :account_id AND holdings.symbol = :symbol
                """),
                {
                    "account_id": _account_id,
                    "symbol": _symbol,
                    "shares": _shares,
                    "total_cost": _shares * _price,
                },
            )
            # Clean up zero/negative holdings
            await self.session.execute(
                delete(Holding).where(
                    Holding.account_id == _account_id,
                    Holding.symbol == _symbol,
                    Holding.shares <= 0,
                )
            )
        else:
            # Undo sell: add back shares
            await self.session.execute(
                text("""
                    INSERT INTO holdings (account_id, symbol, shares, avg_cost, total_cost, currency)
                    VALUES (:account_id, :symbol, :shares, :price, :total_cost, :currency)
                    ON CONFLICT (account_id, symbol) DO UPDATE SET
                        shares = holdings.shares + EXCLUDED.shares,
                        total_cost = holdings.total_cost + EXCLUDED.total_cost,
                        avg_cost = (holdings.total_cost + EXCLUDED.total_cost) / (holdings.shares + EXCLUDED.shares)
                    WHERE holdings.account_id = :account_id AND holdings.symbol = :symbol
                """),
                {
                    "account_id": _account_id,
                    "symbol": _symbol,
                    "shares": _shares,
                    "price": _price,
                    "total_cost": _shares * _price,
                    "currency": (await self.session.execute(
                        select(Account.currency).where(Account.id == _account_id)
                    )).scalar_one_or_none() or "USD",
                },
            )

        await self.session.commit()
        return True


# ── Backfill helpers (run in background thread) ──────────────────────────────────

def auto_backfill_symbol(symbol: str):
    """Check if symbol has price history; backfill from 1990 if missing. Non-blocking."""
    def _do():
        try:
            from .price_service import PriceService
            ps = PriceService()
            # Simple check via sync DB for now (background thread can't use async session)
            import psycopg2
            from ..config import get_settings
            settings = get_settings()
            conn = psycopg2.connect(settings.DATABASE_URL)
            cur = conn.cursor()

            if symbol.isdigit():
                cur.execute("SELECT MIN(price_date) FROM price_history_tw WHERE symbol = %s", (symbol,))
                row = cur.fetchone()
                has_history = row and row[0] is not None
                table = "tw"
            else:
                cur.execute("SELECT MIN(price_date) FROM price_history_us WHERE symbol = %s", (symbol,))
                row = cur.fetchone()
                has_history = row and row[0] is not None
                table = "us"
            conn.close()

            if has_history:
                logger.info(f"[Backfill] {symbol} already has history, skipping")
                return

            logger.info(f"[Backfill] {symbol} has no history, starting backfill from 1990-01-01...")
            start_date = "1990-01-01"
            end_date = datetime.today().strftime("%Y-%m-%d")

            if table == "tw":
                _backfill_tw_symbol(symbol, start_date, end_date)
            else:
                _backfill_us_symbol(symbol, start_date, end_date)
        except Exception as e:
            logger.error(f"[Backfill] Error for {symbol}: {e}")

    t = threading.Thread(target=_do, daemon=True)
    t.start()


def _backfill_us_symbol(symbol: str, start_date: str, end_date: str):
    import yfinance as yf
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date)
        if hist.empty:
            logger.warning(f"[Backfill] {symbol} - no data from yfinance")
            return

        import psycopg2
        from ..config import get_settings
        settings = get_settings()
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        inserted = 0
        for idx, row in hist.iterrows():
            ds = str(idx)[:10]
            try:
                cur.execute("""
                    INSERT INTO price_history_us (symbol, price_date, open, high, low, close, volume, currency, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'USD', 'US')
                    ON CONFLICT (symbol, price_date) DO UPDATE SET
                        open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                        close=EXCLUDED.close, volume=EXCLUDED.volume
                """, (symbol, ds, round(float(row["Open"]), 4), round(float(row["High"]), 4),
                      round(float(row["Low"]), 4), round(float(row["Close"]), 4), int(row["Volume"])))
                inserted += 1
            except Exception:
                pass
        conn.commit()
        conn.close()
        logger.info(f"[Backfill] {symbol} done, {inserted} records")
    except Exception as e:
        logger.error(f"[Backfill] {symbol} failed: {e}")


def _backfill_tw_symbol(symbol: str, start_date: str, end_date: str):
    import twstock
    import time as time_sleep
    try:
        stock = twstock.Stock(symbol)
        current_year = datetime.now().year
        all_data = {}
        for year in range(1990, current_year + 1):
            for month in range(1, 13):
                if year == current_year and month > datetime.now().month:
                    break
                try:
                    data = stock.fetch(year, month)
                    for d in data:
                        ds = str(d.date)[:10]
                        all_data[ds] = {
                            "open": round(float(d.open), 4),
                            "high": round(float(d.high), 4),
                            "low": round(float(d.low), 4),
                            "close": round(float(d.close), 4),
                            "volume": int(d.capacity) if hasattr(d, 'capacity') else 0,
                        }
                except Exception:
                    pass
                time_sleep(0.3)

        if not all_data:
            logger.warning(f"[Backfill] {symbol} - no data from twstock")
            return

        is_tpex = symbol in ("00887",)
        market = "TPEx" if is_tpex else "TWSE"

        import psycopg2
        from ..config import get_settings
        settings = get_settings()
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        inserted = 0
        for ds, vals in all_data.items():
            try:
                cur.execute("""
                    INSERT INTO price_history_tw (symbol, price_date, open, high, low, close, volume, currency, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'TWD', %s)
                    ON CONFLICT (symbol, price_date) DO UPDATE SET
                        open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                        close=EXCLUDED.close, volume=EXCLUDED.volume
                """, (symbol, ds, vals["open"], vals["high"], vals["low"], vals["close"], vals["volume"], market))
                inserted += 1
            except Exception:
                pass
        conn.commit()
        conn.close()
        logger.info(f"[Backfill] {symbol} done, {inserted} records")
    except Exception as e:
        logger.error(f"[Backfill] {symbol} failed: {e}")