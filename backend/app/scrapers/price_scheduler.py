"""
APScheduler-based price collector service.

Runs entirely within the FastAPI process (no cron/external scheduler).
Starts as a daemon thread when start() is called.

DST-aware US market close times:
  - DST active  → US market closes 21:30 ET = 04:00 TWD next day
  - Non-DST     → US market closes 21:30 ET = 05:00 TWD next day
"""
import threading
import logging
from datetime import date, datetime, timedelta

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.logging_config import logger
from app.scrapers.price_collector import (
    _fetch_and_upsert,
    _detect_gaps,
    _discover_new_symbols,
    _alert_no_data,
)

# Lazy import to avoid circular dependency issues at module level
_chinesecalendar = None


def _get_chinesecalendar():
    global _chinesecalendar
    if _chinesecalendar is None:
        try:
            from chinese_calendar import is_holiday as _check_holiday
            _chinesecalendar = _check_holiday
        except ImportError as e:
            logger.warning(f"chinesecalendar not installed; Taiwan holiday check disabled: {e}")
            _chinesecalendar = lambda d: False
    return _chinesecalendar


# ─── helpers ───────────────────────────────────────────────────────────────────

def _is_us_dst_now() -> bool:
    """Check if US (America/New_York) is currently in DST."""
    eastern = pytz.timezone("America/New_York")
    now_et = datetime.now(eastern)
    return bool(now_et.dst())


def _get_tw_symbols_for_currency(currency: str) -> list[str]:
    """Return DISTINCT symbols from transactions for the given account currency."""
    from app.database import get_db
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT t.symbol
                FROM transactions t
                JOIN accounts a ON a.id = t.account_id
                WHERE a.currency = %s
                ORDER BY t.symbol
            """, (currency,))
            rows = cur.fetchall()
            cur.close()
        return [row["symbol"] for row in rows]
    except Exception as e:
        logger.error(f"_get_tw_symbols_for_currency failed: {e}")
        return []


def _get_earliest_transaction_date(symbol: str) -> date:
    """Return earliest transaction_date for a symbol, or 5 years ago as fallback."""
    from app.database import get_db
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT MIN(transaction_date) as earliest FROM transactions
                WHERE symbol = %s
            """, (symbol,))
            row = cur.fetchone()
            cur.close()
        if row and row["earliest"]:
            from datetime import datetime
            earliest = row["earliest"]
            if isinstance(earliest, str):
                return datetime.strptime(earliest, "%Y-%m-%d").date()
            return earliest
    except Exception:
        pass
    return date.today() - timedelta(days=365 * 5)


def _is_taiwan_holiday(d: date) -> bool:
    """Return True if d is a Taiwan public holiday."""
    check = _get_chinesecalendar()
    try:
        return check(d)
    except Exception:
        return False


# ─── job implementations ───────────────────────────────────────────────────────

def _collect_tw_daily():
    """Job: collect latest day for all TWD-account symbols. Runs 13:35 TWD Mon-Fri."""
    today = date.today()
    if _is_taiwan_holiday(today):
        logger.info("[TW collector] Taiwan holiday — skipping")
        return

    symbols = _get_tw_symbols_for_currency("TWD")
    if not symbols:
        logger.info("[TW collector] No TWD symbols found")
        return

    logger.info(f"[TW collector] Starting for {len(symbols)} symbols")
    for sym in symbols:
        count, err = _fetch_and_upsert(sym, "TW", today, today)
        if err:
            _alert_no_data(sym, "TW", reason=err)
        import time
        time.sleep(0.3)
    logger.info("[TW collector] Done")


def _collect_us_daily():
    """Job: collect latest day for all USD-account symbols. Runs 04:00/05:00 TWD Mon-Fri."""
    symbols = _get_tw_symbols_for_currency("USD")
    if not symbols:
        logger.info("[US collector] No USD symbols found")
        return

    today = date.today()
    logger.info(f"[US collector] Starting for {len(symbols)} symbols")
    for sym in symbols:
        count, err = _fetch_and_upsert(sym, "US", today, today)
        if err:
            _alert_no_data(sym, "US", reason=err)
        import time
        time.sleep(0.3)
    logger.info("[US collector] Done")


def _collect_backfill():
    """Job: detect gaps for all tracked symbols, fill gaps >7 days with full backfill."""
    from app.scrapers.price_collector import _try_tw_symbol
    from app.database import get_db

    today = date.today()

    # Gather all tracked symbols (TW + US)
    tw_symbols = _get_tw_symbols_for_currency("TWD")
    us_symbols = _get_tw_symbols_for_currency("USD")

    def process_symbol(sym: str, region: str):
        has_gap, latest, gap_days = _detect_gaps(sym, region)
        if not has_gap or gap_days <= 0:
            return

        logger.info(f"[backfill] {sym} ({region}): gap={gap_days} days, latest={latest}")

        if 1 <= gap_days <= 7:
            # Incremental fill: just fetch the missing days
            start = latest + timedelta(days=1) if latest else today - timedelta(days=gap_days)
            end = today
            count, err = _fetch_and_upsert(sym, region, start, end)
            if err:
                _alert_no_data(sym, region, reason=f"incremental backfill: {err}")

        elif gap_days > 7:
            # Full backfill from earliest transaction date
            start_date = _get_earliest_transaction_date(sym)
            logger.info(f"[backfill] {sym} full backfill: {start_date} → {today}")

            # Split into 30-day batches to avoid yfinance issues
            batch = 30
            current = start_date
            while current <= today:
                batch_end = min(current + timedelta(days=batch - 1), today)
                count, err = _fetch_and_upsert(sym, region, current, batch_end)
                if err:
                    _alert_no_data(sym, region, reason=f"batch backfill: {err}")
                current = batch_end + timedelta(days=1)
                import time
                time.sleep(0.5)

        import time
        time.sleep(0.3)

    for sym in tw_symbols:
        process_symbol(sym, "TW")

    for sym in us_symbols:
        process_symbol(sym, "US")

    logger.info("[backfill] Done")


def _check_new_symbols():
    """Job: discover new symbols from transactions and immediately backfill them."""
    new_symbols = _discover_new_symbols()
    if not new_symbols:
        logger.info("[new_symbols] No new symbols to backfill")
        return

    today = date.today()
    # backfill up to 1 year for new symbols
    start_date = today - timedelta(days=365)

    for sym, region in new_symbols:
        logger.info(f"[new_symbols] Backfilling new symbol {sym} ({region})")
        count, err = _fetch_and_upsert(sym, region, start_date, today)
        if err or count == 0:
            _alert_no_data(sym, region, reason=err or "no data returned after backfill")
        import time
        time.sleep(0.5)

    logger.info(f"[new_symbols] Done — processed {len(new_symbols)} symbols")


# ─── service class ────────────────────────────────────────────────────────────

class PriceCollectorService:
    """
    APScheduler-based price collector that runs inside the FastAPI process.

    Usage:
        collector = PriceCollectorService()
        collector.start()   # called on FastAPI startup
        collector.stop()    # called on FastAPI shutdown
    """

    _instance_lock = threading.Lock()
    _started = False

    def __init__(self):
        self._scheduler: BlockingScheduler = None
        self._thread: threading.Thread = None

    def _build_scheduler(self) -> BlockingScheduler:
        tz_taiwan = pytz.timezone("Asia/Taipei")
        sched = BlockingScheduler(timezone=str(tz_taiwan))

        # Taiwan daily — 13:35 TWD Mon-Fri
        sched.add_job(
            _collect_tw_daily,
            CronTrigger(hour=13, minute=35, day_of_week="mon-fri", timezone=str(tz_taiwan)),
            id="collect_tw_daily",
            name="Taiwan daily price collection",
            misfire_grace_time=60 * 30,  # 30 min grace
        )

        # US daily — DST-aware 04:00/05:00 TWD Mon-Fri
        us_hour = "04" if _is_us_dst_now() else "05"
        sched.add_job(
            _collect_us_daily,
            CronTrigger(hour=int(us_hour), minute=0, day_of_week="mon-fri", timezone=str(tz_taiwan)),
            id="collect_us_daily",
            name="US daily price collection",
            misfire_grace_time=60 * 30,
        )

        # Backfill — 15:00 TWD daily
        sched.add_job(
            _collect_backfill,
            CronTrigger(hour=15, minute=0, timezone=str(tz_taiwan)),
            id="collect_backfill",
            name="Daily gap backfill",
            misfire_grace_time=60 * 60,
        )

        # New symbol check — 08:00 TWD daily
        sched.add_job(
            _check_new_symbols,
            CronTrigger(hour=8, minute=0, timezone=str(tz_taiwan)),
            id="check_new_symbols",
            name="Discover and backfill new symbols",
            misfire_grace_time=60 * 30,
        )

        return sched

    def start(self):
        """Start the scheduler in a daemon thread."""
        with self._instance_lock:
            if PriceCollectorService._started:
                logger.warning("[PriceCollectorService] already started, skipping")
                return
            PriceCollectorService._started = True

        self._scheduler = self._build_scheduler()
        self._thread = threading.Thread(target=self._scheduler.start, daemon=True, name="PriceCollectorThread")
        self._thread.start()
        logger.info(
            f"[PriceCollectorService] started in daemon thread. "
            f"Jobs: TW@13:35, US@{'04' if _is_us_dst_now() else '05'}:00, "
            f"backfill@15:00, new_symbols@08:00 (TWD)"
        )

    def stop(self):
        """Shutdown the scheduler gracefully."""
        with self._instance_lock:
            if not PriceCollectorService._started:
                return

        if self._scheduler is not None:
            try:
                self._scheduler.shutdown(wait=False)
                logger.info("[PriceCollectorService] stopped")
            except Exception as e:
                logger.error(f"[PriceCollectorService] stop error: {e}")

        PriceCollectorService._started = False