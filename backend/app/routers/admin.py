"""
Database monitoring API
"""
import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..config import get_settings
from ..database import get_db, is_sqlite_url
from ..logging_config import logger
from ..scrapers.price_scheduler import (
    get_scraper_execution_records,
    get_scraper_status_snapshot,
    get_missing_data_report,
    set_scraper_scheduler_enabled,
    trigger_scraper_run,
)
from ..routers.auth import require_admin_user

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_user)])

settings = get_settings()


def _get_sqlite_table_stats():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        table_names = [row["name"] for row in cur.fetchall()]
        tables = []
        for name in table_names:
            cur.execute(f'SELECT COUNT(*) AS row_count FROM "{name}"')
            row = cur.fetchone()
            tables.append(
                {
                    "table_name": name,
                    "row_count": int(row["row_count"]),
                    "size_bytes": 0,
                }
            )
        return tables


def _get_postgres_table_stats():
    import psycopg2

    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            schemaname || '.' || relname as table_name,
            n_live_tup as row_count,
            pg_total_relation_size(schemaname || '.' || relname) as size_bytes
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname || '.' || relname) DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {"table_name": row[0], "row_count": row[1], "size_bytes": row[2]}
        for row in rows
    ]


def _get_table_stats():
    if is_sqlite_url(settings.DATABASE_URL):
        return _get_sqlite_table_stats()
    return _get_postgres_table_stats()


def _sqlite_database_path() -> Path:
    database_url = settings.DATABASE_URL
    raw_path = ""
    if database_url.startswith("sqlite:///./"):
        raw_path = database_url.removeprefix("sqlite:///")
    else:
        from urllib.parse import urlparse

        parsed = urlparse(database_url)
        raw_path = parsed.path or ""
        if database_url.startswith("sqlite:///:memory:"):
            raw_path = ":memory:"
    if raw_path == ":memory:":
        return Path(raw_path)
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    return path


def _get_database_size_bytes() -> int:
    if is_sqlite_url(settings.DATABASE_URL):
        path = _sqlite_database_path()
        if str(path) == ":memory:" or not path.exists():
            return 0
        return path.stat().st_size

    import psycopg2

    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT pg_database_size(current_database())")
    size = int(cur.fetchone()[0] or 0)
    cur.close()
    conn.close()
    return size


def _get_version_info() -> tuple[str, str | None]:
    root = Path(__file__).resolve().parents[2]
    version_file = root / "VERSION"
    version = version_file.read_text().strip() if version_file.exists() else "unknown"
    deployed_at = None
    if version_file.exists():
        deployed_at = datetime.fromtimestamp(version_file.stat().st_mtime).isoformat()
    return version, deployed_at


def _normalize_audit_type(raw_type: str | None) -> str:
    value = (raw_type or "").strip().lower()
    if value in {"scraper", "scrape"}:
        return "scraper"
    if value in {"transaction", "db_change", "holdings"}:
        return "transaction"
    if value in {"auth"}:
        return "auth"
    if value in {"admin", "api_call", "error"}:
        return "admin"
    return "admin"


def _audit_type_synonyms(log_type: str) -> list[str]:
    normalized = _normalize_audit_type(log_type)
    mapping = {
        "scraper": ["scraper", "scrape"],
        "transaction": ["transaction", "db_change", "holdings"],
        "auth": ["auth"],
        "admin": ["admin", "api_call", "error"],
    }
    return mapping.get(normalized, [normalized])


def _price_source_health(recent_runs: list[dict]) -> list[PriceSourceStatus]:
    sources = [
        ("Taiwan price source", ("TW", "Taiwan", "TWSE")),
        ("US price source", ("US", "USA", "NYSE", "NASDAQ")),
    ]
    result: list[PriceSourceStatus] = []
    for label, needles in sources:
        matched = None
        for entry in recent_runs:
            blob = " ".join(
                str(entry.get(key, "") or "")
                for key in ("job_name", "target", "symbol", "message", "status")
            ).upper()
            if any(needle.upper() in blob for needle in needles):
                matched = entry
                break
        if matched:
            status = "healthy" if matched.get("status") == "success" else ("degraded" if matched.get("status") in {"warning", "running"} else "error")
            result.append(
                PriceSourceStatus(
                    name=label,
                    status=status,
                    last_run=matched.get("timestamp"),
                    records_fetched=int(matched.get("records_fetched") or 0),
                    message=matched.get("error_reason") or matched.get("message"),
                )
            )
        else:
            result.append(PriceSourceStatus(name=label, status="unknown"))
    return result


def _normalize_details(details):
    if details is None:
        return {}
    if isinstance(details, dict):
        return details
    if isinstance(details, str):
        try:
            parsed = json.loads(details)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            return {"raw": details}
    return {"value": details}


def _row_value(row, key, default=None):
    if hasattr(row, "keys") and key in row.keys():
        return row[key]
    if isinstance(row, dict):
        return row.get(key, default)
    return default


class TableInfo(BaseModel):
    table_name: str
    row_count: int
    size_bytes: int


class DatabaseStats(BaseModel):
    total_size_bytes: int
    total_size_mb: float
    table_count: int
    tables: list[TableInfo]
    last_vacuum: str | None
    last_analyze: str | None


class ScraperStatus(BaseModel):
    name: str
    last_run: str | None
    records_fetched: int
    status: str  # 'idle', 'running', 'error'


class VersionInfo(BaseModel):
    version: str
    last_updated: str | None = None
    deployed_at: str | None = None


class PriceSourceStatus(BaseModel):
    name: str
    status: str
    last_run: str | None = None
    records_fetched: int = 0
    message: str | None = None


class SystemHealth(BaseModel):
    connected: bool
    database_size_bytes: int
    database_size_mb: float
    database_path: str | None = None
    table_count: int
    price_sources: list[PriceSourceStatus]
    scraper_enabled: bool
    scraper_running: bool
    recent_runs: list[dict]
    version: VersionInfo


class ScraperTriggerRequest(BaseModel):
    mode: Literal["single", "all_holdings", "backfill_gaps"]
    symbol: str | None = Field(default=None, description="Required for single symbol triggers")


class SchedulerToggleRequest(BaseModel):
    enabled: bool


class ScraperRunInfo(BaseModel):
    id: int
    timestamp: str
    level: str
    message: str
    symbol: str | None = None
    job_name: str
    trigger: str
    target: str
    status: str
    success_count: int
    failure_count: int
    records_fetched: int
    duration_ms: int | None = None
    error_reason: str | None = None
    details: dict = Field(default_factory=dict)


class MissingDataItem(BaseModel):
    symbol: str
    currency: str
    region: str
    latest_price_date: str | None = None
    gap_days: int | None = None
    missing_days: int
    history_rows: int
    status: str


class ScraperRuntimeInfo(BaseModel):
    enabled: bool
    running: bool
    active_runs: list[dict]
    recent_runs: list[dict]
    last_error: str | None = None
    scheduler_started: bool
    timezone: str
    next_runs: list[dict]


@router.get("/version", response_model=VersionInfo)
async def get_version():
    version, deployed_at = _get_version_info()
    return VersionInfo(version=version, last_updated=datetime.now().isoformat(), deployed_at=deployed_at)


@router.get("/db/stats", response_model=DatabaseStats)
async def get_database_stats():
    """Get database statistics and table info"""
    try:
        tables_data = _get_table_stats()
        tables = [
            TableInfo(
                table_name=row["table_name"],
                row_count=row["row_count"],
                size_bytes=row["size_bytes"],
            )
            for row in tables_data
        ]
        total_bytes = _get_database_size_bytes()
        
        logger.info(f"Database stats fetched: {len(tables)} tables")
        
        return DatabaseStats(
            total_size_bytes=total_bytes,
            total_size_mb=round(total_bytes / (1024 * 1024), 2),
            table_count=len(tables),
            tables=tables,
            last_vacuum=None,
            last_analyze=None,
        )
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise


@router.get("/status")
async def get_admin_status():
    """Combined admin status: DB connection + table stats + scraper runtime status"""
    connected = False
    tables = []
    try:
        tables = _get_table_stats()
        connected = True
    except Exception as e:
        logger.error(f"Failed to connect to DB: {e}")

    scraper_status = get_scraper_status_snapshot()
    version, deployed_at = _get_version_info()
    price_sources = _price_source_health(scraper_status["recent_runs"])
    database_size_bytes = _get_database_size_bytes()
    return {
        "connected": connected,
        "tables": tables,
        "database_size_bytes": database_size_bytes,
        "database_size_mb": round(database_size_bytes / (1024 * 1024), 2),
        "database_path": str(_sqlite_database_path()) if is_sqlite_url(settings.DATABASE_URL) else None,
        "scraper_enabled": scraper_status["enabled"],
        "scraper_running": scraper_status["running"],
        "price_sources": price_sources,
        "scrapers": price_sources,
        "recent_runs": scraper_status["recent_runs"],
        "runtime": scraper_status,
        "version": {
            "version": version,
            "last_updated": datetime.now().isoformat(),
            "deployed_at": deployed_at,
        },
    }


@router.get("/health", response_model=SystemHealth)
async def get_system_health():
    connected = False
    tables = []
    try:
        tables = _get_table_stats()
        connected = True
    except Exception as e:
        logger.error(f"Failed to connect to DB: {e}")

    runtime = get_scraper_status_snapshot()
    version, deployed_at = _get_version_info()
    size_bytes = _get_database_size_bytes()
    return SystemHealth(
        connected=connected,
        database_size_bytes=size_bytes,
        database_size_mb=round(size_bytes / (1024 * 1024), 2),
        database_path=str(_sqlite_database_path()) if is_sqlite_url(settings.DATABASE_URL) else None,
        table_count=len(tables),
        price_sources=_price_source_health(runtime["recent_runs"]),
        scraper_enabled=runtime["enabled"],
        scraper_running=runtime["running"],
        recent_runs=runtime["recent_runs"],
        version=VersionInfo(version=version, last_updated=datetime.now().isoformat(), deployed_at=deployed_at),
    )


@router.get("/scraper/status", response_model=ScraperRuntimeInfo)
async def get_scraper_status():
    """Get live scraper runtime status."""
    status = get_scraper_status_snapshot()
    return ScraperRuntimeInfo(
        enabled=bool(status["enabled"]),
        running=bool(status["running"]),
        active_runs=status["active_runs"],
        recent_runs=status["recent_runs"],
        last_error=status.get("last_error"),
        scheduler_started=bool(status["scheduler_started"]),
        timezone=status["timezone"],
        next_runs=status["next_runs"],
    )


@router.get("/scraper/runs", response_model=list[ScraperRunInfo])
async def get_scraper_runs(limit: int = 20):
    records = get_scraper_execution_records(limit=max(1, min(limit, 100)))
    return [
        ScraperRunInfo(
            id=entry["id"],
            timestamp=entry["timestamp"],
            level=entry["level"],
            message=entry["message"],
            symbol=entry.get("symbol"),
            job_name=entry["job_name"],
            trigger=entry["trigger"],
            target=entry["target"],
            status=entry["status"],
            success_count=entry["success_count"],
            failure_count=entry["failure_count"],
            records_fetched=entry["records_fetched"],
            duration_ms=entry.get("duration_ms"),
            error_reason=entry.get("error_reason"),
            details=_normalize_details(entry.get("details")),
        )
        for entry in records
    ]


@router.post("/scraper/trigger")
async def trigger_scraper(request: ScraperTriggerRequest):
    if request.mode == "single" and not request.symbol:
        raise HTTPException(status_code=400, detail="單一股票觸發時必須提供 symbol")
    symbol = request.symbol.strip().upper() if request.symbol else None
    return trigger_scraper_run(request.mode, symbol=symbol)


@router.post("/scraper/scheduler")
async def set_scraper_scheduler(request: SchedulerToggleRequest):
    return set_scraper_scheduler_enabled(request.enabled)


@router.get("/scraper/missing-data", response_model=list[MissingDataItem])
async def get_missing_data():
    items = get_missing_data_report()
    return [
        MissingDataItem(
            symbol=item["symbol"],
            currency=item["currency"],
            region=item["region"],
            latest_price_date=item.get("latest_price_date"),
            gap_days=item.get("gap_days"),
            missing_days=int(item.get("missing_days") or 0),
            history_rows=int(item.get("history_rows") or 0),
            status=item["status"],
        )
        for item in items
    ]


def _build_audit_filters(
    log_type: str = '',
    q: str = '',
    start_date: str = '',
    end_date: str = '',
):
    type_filters = _audit_type_synonyms(log_type) if log_type else []
    query = q.strip()
    clauses = []
    params: list[object] = []
    if type_filters:
        placeholders = ", ".join(["%s"] * len(type_filters))
        clauses.append(f"LOWER(type) IN ({placeholders})")
        params.extend(type_filters)
    if query:
        clauses.append("(LOWER(message) LIKE %s OR LOWER(COALESCE(CAST(details AS TEXT), '')) LIKE %s)")
        like = f"%{query.lower()}%"
        params.extend([like, like])
    if start_date:
        clauses.append("SUBSTR(timestamp, 1, 10) >= %s")
        params.append(start_date)
    if end_date:
        clauses.append("SUBSTR(timestamp, 1, 10) <= %s")
        params.append(end_date)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def _fetch_audit_logs(
    *,
    log_type: str = '',
    q: str = '',
    start_date: str = '',
    end_date: str = '',
    limit: int = 100,
):
    limit = max(1, min(limit, 500))
    where_sql, params = _build_audit_filters(log_type, q, start_date, end_date)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
                SELECT id, type, message, timestamp, details, symbol, user_id, level
                FROM audit_log
                {where_sql}
                ORDER BY timestamp DESC
                LIMIT %s
            """,
            (*params, limit),
        )
        rows = cur.fetchall()
        cur.execute(
            f"""
                SELECT COUNT(*) AS total
                FROM audit_log
                {where_sql}
            """,
            params,
        )
        count_row = cur.fetchone()
        total = count_row["total"] if isinstance(count_row, dict) else count_row["total"]
    logs = [
        {
            "id": row["id"],
            "type": _normalize_audit_type(row["type"]),
            "raw_type": row["type"],
            "message": row["message"],
            "timestamp": row["timestamp"],
            "details": _normalize_details(row["details"]),
            "symbol": _row_value(row, "symbol"),
            "user_id": _row_value(row, "user_id"),
            "level": _row_value(row, "level"),
        }
        for row in rows
    ]
    return logs, total


@router.get("/logs", response_model=dict)
async def get_audit_logs(log_type: str = '', q: str = '', start_date: str = '', end_date: str = '', limit: int = 100):
    """Get audit log entries from the audit_log table"""
    try:
        logs, total = _fetch_audit_logs(log_type=log_type, q=q, start_date=start_date, end_date=end_date, limit=limit)
        
        logger.info(f"Audit logs fetched: {len(logs)} entries")
        
        return {"logs": logs, "total": total}
        
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        return {"logs": [], "total": 0, "error": str(e)}


@router.get("/logs/export.csv")
async def export_audit_logs_csv(log_type: str = '', q: str = '', start_date: str = '', end_date: str = ''):
    logs, _ = _fetch_audit_logs(log_type=log_type, q=q, start_date=start_date, end_date=end_date, limit=500)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "timestamp", "type", "raw_type", "level", "message", "symbol", "user_id", "details"])
    for log in logs:
        writer.writerow([
            log["id"],
            log["timestamp"],
            log["type"],
            log.get("raw_type"),
            log.get("level"),
            log["message"],
            log.get("symbol"),
            log.get("user_id"),
            json.dumps(log.get("details", {}), ensure_ascii=False),
        ])
    output.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="audit-logs.csv"'}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8", headers=headers)


@router.get("/logs/recent")
async def get_recent_logs(limit: int = 100):
    """Get recent log entries from /tmp/wealth.log"""
    try:
        with open("/tmp/wealth.log", "r") as f:
            lines = f.readlines()
        return {
            "total_lines": len(lines),
            "recent": lines[-limit:] if len(lines) >= limit else lines
        }
    except Exception as e:
        return {
            "total_lines": 0,
            "recent": [],
            "error": str(e)
        }


@router.get("/export/transactions.csv")
async def export_transactions_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "transaction_date",
        "symbol",
        "type",
        "shares",
        "price",
        "fee",
        "tax",
        "category",
        "asset_class",
        "sector",
        "notes",
        "currency",
        "realized_gain",
        "user_id",
    ])

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, transaction_date, symbol, type, quantity, price, fee, tax,
                   category, asset_class, sector, notes, currency, realized_gain, user_id
            FROM transactions
            ORDER BY transaction_date DESC, id DESC
            """
        )
        for row in cur.fetchall():
            writer.writerow([
                row["id"],
                row["transaction_date"],
                row["symbol"],
                row["type"],
                row["quantity"],
                row["price"],
                row["fee"],
                row["tax"],
                row["category"],
                row["asset_class"],
                row["sector"],
                row["notes"],
                row["currency"],
                row["realized_gain"],
                row["user_id"],
            ])

    output.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="transactions.csv"'}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8", headers=headers)


@router.get("/backup/sqlite")
async def download_sqlite_backup():
    if not is_sqlite_url(settings.DATABASE_URL):
        raise HTTPException(status_code=400, detail="目前僅支援 SQLite 備份下載")
    db_path = _sqlite_database_path()
    if str(db_path) == ":memory:" or not db_path.exists():
        raise HTTPException(status_code=404, detail="找不到 SQLite 資料庫檔案")
    return FileResponse(
        path=db_path,
        filename=f"{db_path.stem}-backup{db_path.suffix}",
        media_type="application/x-sqlite3",
    )
