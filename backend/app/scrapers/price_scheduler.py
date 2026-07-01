"""
APScheduler-based price collector service.

Runs entirely within the FastAPI process (no cron/external scheduler).
Starts as a daemon thread when start() is called.

DST-aware US market close times:
  - DST active  → US market closes 21:30 ET = 04:00 TWD next day
  - Non-DST     → US market closes 21:30 ET = 05:00 TWD next day
"""
import json
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import get_db
from app.logging_config import logger
from app.scrapers.price_collector import (
    _fetch_and_upsert,
    _detect_gaps,
    _discover_new_symbols,
    _alert_no_data,
)
from app.services.transaction_service import get_symbol_backfill_start_date

# Lazy import to avoid circular dependency issues at module level
_chinesecalendar = None


@dataclass
class ScraperRunRecord:
    run_id: str
    job_name: str
    trigger: str
    target: str
    symbol: str | None
    status: str
    started_at: str
    finished_at: str | None = None
    duration_ms: int | None = None
    success_count: int = 0
    failure_count: int = 0
    records_fetched: int = 0
    error_reason: str | None = None
    details: dict = field(default_factory=dict)


class ScraperRuntimeState:
    def __init__(self):
        self._lock = threading.RLock()
        self.enabled = False
        self.scheduler_running = False
        self.active_runs: dict[str, ScraperRunRecord] = {}
        self.recent_runs: deque[ScraperRunRecord] = deque(maxlen=40)
        self.last_error: str | None = None

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self.enabled = enabled

    def set_scheduler_running(self, running: bool) -> None:
        with self._lock:
            self.scheduler_running = running

    def begin_run(
        self,
        job_name: str,
        trigger: str,
        target: str,
        symbol: str | None = None,
        details: dict | None = None,
    ) -> ScraperRunRecord:
        record = ScraperRunRecord(
            run_id=uuid.uuid4().hex,
            job_name=job_name,
            trigger=trigger,
            target=target,
            symbol=symbol,
            status="running",
            started_at=datetime.now().isoformat(),
            details=details or {},
        )
        with self._lock:
            self.active_runs[record.run_id] = record
        return record

    def finish_run(
        self,
        record: ScraperRunRecord,
        *,
        status: str,
        success_count: int,
        failure_count: int,
        records_fetched: int,
        error_reason: str | None = None,
        details: dict | None = None,
    ) -> ScraperRunRecord:
        finished_at = datetime.now()
        record.status = status
        record.finished_at = finished_at.isoformat()
        record.duration_ms = int((finished_at - datetime.fromisoformat(record.started_at)).total_seconds() * 1000)
        record.success_count = success_count
        record.failure_count = failure_count
        record.records_fetched = records_fetched
        record.error_reason = error_reason
        if details:
            record.details.update(details)

        with self._lock:
            self.active_runs.pop(record.run_id, None)
            self.recent_runs.appendleft(record)
            if error_reason:
                self.last_error = error_reason
            elif status == "success":
                self.last_error = None
        return record

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "enabled": self.enabled,
                "running": self.scheduler_running,
                "active_runs": [asdict(run) for run in self.active_runs.values()],
                "recent_runs": [asdict(run) for run in list(self.recent_runs)[:10]],
                "last_error": self.last_error,
            }


SCRAPER_RUNTIME = ScraperRuntimeState()


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


def _get_tracked_symbols() -> list[tuple[str, str]]:
    """Return tracked symbols and their inferred currency from transactions."""
    from app.database import get_db

    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT symbol, COALESCE(currency, '') AS currency
                FROM transactions
                ORDER BY symbol
            """)
            rows = cur.fetchall()
            cur.close()
        result: list[tuple[str, str]] = []
        for row in rows:
            symbol = str(row["symbol"])
            currency = str(row["currency"] or "").upper()
            if currency not in {"TWD", "USD"}:
                currency = "TWD" if symbol.isdigit() else "USD"
            result.append((symbol, currency))
        return result
    except Exception as e:
        logger.error(f"_get_tracked_symbols failed: {e}")
        return []


def _get_symbols_for_currency(currency: str) -> list[str]:
    return [symbol for symbol, tx_currency in _get_tracked_symbols() if tx_currency == currency]


def _is_taiwan_holiday(d: date) -> bool:
    """Return True if d is a Taiwan public holiday."""
    check = _get_chinesecalendar()
    try:
        return check(d)
    except Exception:
        return False


def _job_summary(
    job_name: str,
    trigger: str,
    target: str,
    symbol: str | None,
    started_at: datetime,
    success_count: int,
    failure_count: int,
    records_fetched: int,
    error_reason: str | None = None,
    details: dict | None = None,
) -> dict:
    finished_at = datetime.now()
    duration_ms = int((finished_at - started_at).total_seconds() * 1000)
    status = "error" if failure_count and success_count == 0 else ("warning" if failure_count else "success")
    if error_reason and status == "success":
        status = "warning"
    return {
        "job_name": job_name,
        "trigger": trigger,
        "target": target,
        "symbol": symbol,
        "status": status,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_ms": duration_ms,
        "success_count": success_count,
        "failure_count": failure_count,
        "records_fetched": records_fetched,
        "error_reason": error_reason,
        "details": details or {},
    }


def _log_job_summary(summary: dict) -> None:
    level = "ERROR" if summary["status"] == "error" else ("WARNING" if summary["status"] == "warning" else "INFO")
    write_details = dict(summary["details"])
    write_details.update(
        {
            "trigger": summary["trigger"],
            "target": summary["target"],
            "symbol": summary["symbol"],
            "status": summary["status"],
            "success_count": summary["success_count"],
            "failure_count": summary["failure_count"],
            "records_fetched": summary["records_fetched"],
            "duration_ms": summary["duration_ms"],
            "started_at": summary["started_at"],
            "finished_at": summary["finished_at"],
        }
    )
    if summary.get("error_reason"):
        write_details["error_reason"] = summary["error_reason"]
    write_log(
        type="scraper",
        level=level,
        message=f"{summary['job_name']} finished with {summary['status']}",
        details=write_details,
        symbol=summary["symbol"],
    )


def _run_guarded_job(
    job_name: str,
    trigger: str,
    target: str,
    symbol: str | None,
    runner,
) -> dict:
    started_at = datetime.now()
    record = SCRAPER_RUNTIME.begin_run(job_name, trigger, target, symbol)
    try:
        payload = runner()
        summary = _job_summary(
            job_name=job_name,
            trigger=trigger,
            target=target,
            symbol=symbol,
            started_at=started_at,
            success_count=int(payload.get("success_count", 0)),
            failure_count=int(payload.get("failure_count", 0)),
            records_fetched=int(payload.get("records_fetched", 0)),
            error_reason=payload.get("error_reason"),
            details=payload.get("details", {}),
        )
    except Exception as exc:
        summary = _job_summary(
            job_name=job_name,
            trigger=trigger,
            target=target,
            symbol=symbol,
            started_at=started_at,
            success_count=0,
            failure_count=1,
            records_fetched=0,
            error_reason=str(exc),
            details={"exception_type": exc.__class__.__name__},
        )
    SCRAPER_RUNTIME.finish_run(
        record,
        status=summary["status"],
        success_count=summary["success_count"],
        failure_count=summary["failure_count"],
        records_fetched=summary["records_fetched"],
        error_reason=summary.get("error_reason"),
        details=summary.get("details", {}),
    )
    _log_job_summary(summary)
    return summary


def _spawn_guarded_job(job_name: str, trigger: str, target: str, symbol: str | None, runner) -> dict:
    def _do():
        _run_guarded_job(job_name, trigger, target, symbol, runner)

    thread = threading.Thread(target=_do, daemon=True, name=f"{job_name}:{symbol or target}")
    thread.start()
    return {
        "accepted": True,
        "job_name": job_name,
        "trigger": trigger,
        "target": target,
        "symbol": symbol,
        "status": "running",
    }


# ─── job implementations ───────────────────────────────────────────────────────

def _collect_tw_daily():
    """Job: collect latest day for all TWD-account symbols. Runs 13:35 TWD Mon-Fri."""
    today = date.today()
    if _is_taiwan_holiday(today):
        logger.info("[TW collector] Taiwan holiday — skipping")
        return {
            "success_count": 0,
            "failure_count": 0,
            "records_fetched": 0,
            "details": {"skipped_reason": "taiwan_holiday"},
        }

    symbols = _get_symbols_for_currency("TWD")
    if not symbols:
        logger.info("[TW collector] No TWD symbols found")
        return {
            "success_count": 0,
            "failure_count": 0,
            "records_fetched": 0,
            "details": {"symbols": []},
        }

    success = 0
    failure = 0
    records = 0
    issues: list[dict] = []
    logger.info(f"[TW collector] Starting for {len(symbols)} symbols")
    for sym in symbols:
        count, err = _fetch_and_upsert(sym, "TW", today, today)
        records += count
        if err:
            failure += 1
            issues.append(err)
            _alert_no_data(sym, "TW", reason=json.dumps(err, ensure_ascii=False))
        else:
            success += 1
        time.sleep(0.3)
    logger.info("[TW collector] Done")
    return {
        "success_count": success,
        "failure_count": failure,
        "records_fetched": records,
        "details": {"symbols": symbols, "issues": issues},
    }


def _collect_us_daily():
    """Job: collect latest day for all USD-account symbols. Runs 04:00/05:00 TWD Mon-Fri."""
    symbols = _get_symbols_for_currency("USD")
    if not symbols:
        logger.info("[US collector] No USD symbols found")
        return {
            "success_count": 0,
            "failure_count": 0,
            "records_fetched": 0,
            "details": {"symbols": []},
        }

    today = date.today()
    success = 0
    failure = 0
    records = 0
    issues: list[dict] = []
    logger.info(f"[US collector] Starting for {len(symbols)} symbols")
    for sym in symbols:
        count, err = _fetch_and_upsert(sym, "US", today, today)
        records += count
        if err:
            failure += 1
            issues.append(err)
            _alert_no_data(sym, "US", reason=json.dumps(err, ensure_ascii=False))
        else:
            success += 1
        time.sleep(0.3)
    logger.info("[US collector] Done")
    return {
        "success_count": success,
        "failure_count": failure,
        "records_fetched": records,
        "details": {"symbols": symbols, "issues": issues},
    }


def _collect_backfill():
    """Job: detect gaps for all tracked symbols, fill gaps >7 days with full backfill."""
    today = date.today()

    # Gather all tracked symbols (TW + US)
    tw_symbols = _get_symbols_for_currency("TWD")
    us_symbols = _get_symbols_for_currency("USD")

    success = 0
    failure = 0
    records = 0
    issues: list[dict] = []

    def process_symbol(sym: str, region: str):
        nonlocal success, failure, records, issues
        has_gap, latest, gap_days = _detect_gaps(sym, region)
        if not has_gap:
            success += 1
            return

        logger.info(f"[backfill] {sym} ({region}): gap={gap_days} days, latest={latest}")

        if latest is None or gap_days < 0:
            start_date = get_symbol_backfill_start_date(sym)
            logger.info(f"[backfill] {sym} initial backfill: {start_date} -> {today}")
            count, err = _fetch_and_upsert(sym, region, start_date, today)
            records += count
            if err:
                failure += 1
                issues.append(err)
                _alert_no_data(sym, region, reason=f"initial backfill: {json.dumps(err, ensure_ascii=False)}")
            else:
                success += 1

        elif gap_days == 0:
            success += 1
            return

        elif 1 <= gap_days <= 7:
            # Incremental fill: just fetch the missing days
            start = latest + timedelta(days=1) if latest else today - timedelta(days=gap_days)
            end = today
            count, err = _fetch_and_upsert(sym, region, start, end)
            records += count
            if err:
                failure += 1
                issues.append(err)
                _alert_no_data(sym, region, reason=f"incremental backfill: {json.dumps(err, ensure_ascii=False)}")
            else:
                success += 1

        elif gap_days > 7:
            # Full backfill from earliest transaction date
            start_date = get_symbol_backfill_start_date(sym)
            logger.info(f"[backfill] {sym} full backfill: {start_date} → {today}")

            # Split into 30-day batches to avoid yfinance issues
            batch = 30
            current = start_date
            while current <= today:
                batch_end = min(current + timedelta(days=batch - 1), today)
                count, err = _fetch_and_upsert(sym, region, current, batch_end)
                records += count
                if err:
                    failure += 1
                    issues.append(err)
                    _alert_no_data(sym, region, reason=f"batch backfill: {json.dumps(err, ensure_ascii=False)}")
                else:
                    success += 1
                current = batch_end + timedelta(days=1)
                time.sleep(0.5)

        time.sleep(0.3)

    for sym in tw_symbols:
        process_symbol(sym, "TW")

    for sym in us_symbols:
        process_symbol(sym, "US")

    logger.info("[backfill] Done")
    return {
        "success_count": success,
        "failure_count": failure,
        "records_fetched": records,
        "details": {"tw_symbols": tw_symbols, "us_symbols": us_symbols, "issues": issues},
    }


def _check_new_symbols():
    """Job: discover new symbols from transactions and immediately backfill them."""
    new_symbols = _discover_new_symbols()
    if not new_symbols:
        logger.info("[new_symbols] No new symbols to backfill")
        return {
            "success_count": 0,
            "failure_count": 0,
            "records_fetched": 0,
            "details": {"symbols": []},
        }

    today = date.today()

    success = 0
    failure = 0
    records = 0
    issues: list[dict] = []

    for sym, region in new_symbols:
        start_date = get_symbol_backfill_start_date(sym)
        logger.info(f"[new_symbols] Backfilling new symbol {sym} ({region})")
        count, err = _fetch_and_upsert(sym, region, start_date, today)
        records += count
        if err or count == 0:
            failure += 1
            issue = err or {"kind": "no_data", "message": "no data returned after backfill"}
            issues.append(issue)
            _alert_no_data(sym, region, reason=json.dumps(issue, ensure_ascii=False))
        else:
            success += 1
        time.sleep(0.5)

    logger.info(f"[new_symbols] Done — processed {len(new_symbols)} symbols")
    return {
        "success_count": success,
        "failure_count": failure,
        "records_fetched": records,
        "details": {"symbols": new_symbols, "issues": issues},
    }


def _collect_all_holdings():
    tw_result = _collect_tw_daily()
    us_result = _collect_us_daily()
    return {
        "success_count": tw_result["success_count"] + us_result["success_count"],
        "failure_count": tw_result["failure_count"] + us_result["failure_count"],
        "records_fetched": tw_result["records_fetched"] + us_result["records_fetched"],
        "details": {"tw": tw_result, "us": us_result},
    }


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
        self._enabled = False

    def _build_scheduler(self) -> BlockingScheduler:
        tz_taiwan = pytz.timezone("Asia/Taipei")
        sched = BlockingScheduler(timezone=str(tz_taiwan))

        # Taiwan daily — 13:35 TWD Mon-Fri
        sched.add_job(
            lambda: _run_guarded_job(
                job_name="scheduled_tw_daily",
                trigger="schedule",
                target="tw_daily",
                symbol=None,
                runner=_collect_tw_daily,
            ),
            CronTrigger(hour=13, minute=35, day_of_week="mon-fri", timezone=str(tz_taiwan)),
            id="collect_tw_daily",
            name="Taiwan daily price collection",
            misfire_grace_time=60 * 30,  # 30 min grace
        )

        # US daily — DST-aware 04:00/05:00 TWD Mon-Fri
        us_hour = "04" if _is_us_dst_now() else "05"
        sched.add_job(
            lambda: _run_guarded_job(
                job_name="scheduled_us_daily",
                trigger="schedule",
                target="us_daily",
                symbol=None,
                runner=_collect_us_daily,
            ),
            CronTrigger(hour=int(us_hour), minute=0, day_of_week="mon-fri", timezone=str(tz_taiwan)),
            id="collect_us_daily",
            name="US daily price collection",
            misfire_grace_time=60 * 30,
        )

        # Backfill — 15:00 TWD daily
        sched.add_job(
            lambda: _run_guarded_job(
                job_name="scheduled_backfill_gaps",
                trigger="schedule",
                target="backfill_gaps",
                symbol=None,
                runner=_collect_backfill,
            ),
            CronTrigger(hour=15, minute=0, timezone=str(tz_taiwan)),
            id="collect_backfill",
            name="Daily gap backfill",
            misfire_grace_time=60 * 60,
        )

        # New symbol check — 08:00 TWD daily
        sched.add_job(
            lambda: _run_guarded_job(
                job_name="scheduled_new_symbols",
                trigger="schedule",
                target="new_symbols",
                symbol=None,
                runner=_check_new_symbols,
            ),
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
        self._enabled = True
        SCRAPER_RUNTIME.set_enabled(True)
        SCRAPER_RUNTIME.set_scheduler_running(True)
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
        self._enabled = False
        SCRAPER_RUNTIME.set_enabled(False)
        SCRAPER_RUNTIME.set_scheduler_running(False)

    def set_enabled(self, enabled: bool):
        if enabled:
            self.start()
        else:
            self.stop()

    def is_enabled(self) -> bool:
        return self._enabled and PriceCollectorService._started

    def status(self) -> dict:
        snapshot = SCRAPER_RUNTIME.snapshot()
        snapshot.update(
            {
                "scheduler_started": PriceCollectorService._started,
                "timezone": "Asia/Taipei",
                "next_runs": self._next_runs(),
            }
        )
        return snapshot

    def _next_runs(self) -> list[dict]:
        if self._scheduler is None:
            return []
        jobs = []
        for job in self._scheduler.get_jobs():
            next_run = getattr(job, "next_run_time", None)
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": next_run.isoformat() if next_run else None,
                    "trigger": str(job.trigger),
                }
            )
        return jobs

    def trigger(self, mode: str, symbol: str | None = None) -> dict:
        if mode == "single":
            if not symbol:
                raise ValueError("symbol is required for single trigger")

            def runner():
                today = date.today()
                region = "TW" if symbol.isdigit() else "US"
                count, err = _fetch_and_upsert(symbol, region, today, today)
                records = count
                failure = 0
                issues = []
                if err:
                    failure = 1
                    issues.append(err)
                    _alert_no_data(symbol, region, reason=json.dumps(err, ensure_ascii=False))
                return {
                    "success_count": 0 if failure else 1,
                    "failure_count": failure,
                    "records_fetched": records,
                    "error_reason": None if not err else err.get("message"),
                    "details": {"symbol": symbol, "region": region, "issues": issues},
                }

            return _spawn_guarded_job(
                job_name="manual_single_symbol",
                trigger="manual",
                target="single",
                symbol=symbol,
                runner=runner,
            )

        if mode == "all_holdings":
            return _spawn_guarded_job(
                job_name="manual_all_holdings",
                trigger="manual",
                target="all_holdings",
                symbol=None,
                runner=_collect_all_holdings,
            )

        if mode == "backfill_gaps":
            return _spawn_guarded_job(
                job_name="manual_backfill_gaps",
                trigger="manual",
                target="backfill_gaps",
                symbol=None,
                runner=_collect_backfill,
            )

        raise ValueError(f"Unsupported trigger mode: {mode}")


collector_service = PriceCollectorService()


def get_collector_service() -> PriceCollectorService:
    return collector_service


def get_scraper_status_snapshot() -> dict:
    return collector_service.status()


def set_scraper_scheduler_enabled(enabled: bool) -> dict:
    collector_service.set_enabled(enabled)
    return collector_service.status()


def trigger_scraper_run(mode: str, symbol: str | None = None) -> dict:
    return collector_service.trigger(mode, symbol=symbol)


def get_scraper_execution_records(limit: int = 20) -> list[dict]:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, timestamp, type, level, message, details, symbol
            FROM audit_log
            WHERE type = %s
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            ("scrape", limit),
        )
        rows = cur.fetchall()

    records: list[dict] = []
    for row in rows:
        details = row["details"]
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except Exception:
                details = {"raw": details}
        details = details or {}
        records.append(
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "level": row["level"],
                "message": row["message"],
                "symbol": row["symbol"],
                "job_name": details.get("job_name") or details.get("target") or "scrape",
                "trigger": details.get("trigger") or "scheduled",
                "target": details.get("target") or "unknown",
                "status": details.get("status") or row["level"].lower(),
                "success_count": int(details.get("success_count") or 0),
                "failure_count": int(details.get("failure_count") or 0),
                "records_fetched": int(details.get("records_fetched") or 0),
                "duration_ms": details.get("duration_ms"),
                "error_reason": details.get("error_reason"),
                "details": details,
            }
        )
    return records


def get_missing_data_report(limit: int = 200) -> list[dict]:
    today = date.today()
    report: list[dict] = []

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT symbol, COALESCE(currency, '') AS currency
            FROM transactions
            ORDER BY symbol
            """
        )
        rows = cur.fetchall()

    for row in rows[:limit]:
        symbol = row["symbol"]
        currency = str(row["currency"] or "").upper()
        if currency not in {"USD", "TWD"}:
            currency = "TWD" if symbol.isdigit() else "USD"
        region = "US" if currency == "USD" else "TW"
        table = "price_history_us" if region == "US" else "price_history_tw"
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT MAX(price_date) AS latest, COUNT(*) AS row_count
                FROM {table}
                WHERE symbol = %s
                """,
                (symbol,),
            )
            price_row = cur.fetchone()

        latest = price_row["latest"] if price_row else None
        row_count = int(price_row["row_count"] or 0) if price_row else 0
        if isinstance(latest, str):
            latest_date = datetime.strptime(latest, "%Y-%m-%d").date()
        else:
            latest_date = latest
        gap_days = (today - latest_date).days if latest_date else None
        missing_days = gap_days if gap_days and gap_days > 0 else 0
        report.append(
            {
                "symbol": symbol,
                "currency": currency,
                "region": region,
                "latest_price_date": latest_date.isoformat() if latest_date else None,
                "gap_days": gap_days,
                "missing_days": missing_days,
                "history_rows": row_count,
                "status": "missing" if latest_date is None else ("stale" if missing_days else "fresh"),
            }
        )

    return sorted(report, key=lambda item: (item["gap_days"] is None, -(item["gap_days"] or 0), item["symbol"]))
