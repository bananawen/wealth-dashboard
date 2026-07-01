"""
Structured audit logging for backend operations.
Persists structured records to PostgreSQL audit_log table and the rotating file log.
"""
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from ..database import get_db
from ..logging_config import logger

__all__ = ["ActionLogger", "LogType", "LogLevel"]


class LogType(str, Enum):
    SCRAPE = "scraper"         # 爬蟲執行
    DB_CHANGE = "transaction"  # 資料庫變更
    API_CALL = "admin"         # 管理操作
    ERROR = "admin"            # 系統/管理錯誤


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ActionLogger:
    """
    Structured audit logger for admin-facing operation logs.
    Writes to both:
      - PostgreSQL  audit_log  table (for the UI query)
      - /tmp/wealth.log        (rotating file, for ops debugging)
    """

    def __init__(self):
        self._file_logger = logger

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_scrape(self, symbol: str, records: int, start_date: str, end_date: str,
                   source: str, status: str = "success", market: str = "",
                   scrape_date: str = ""):
        """記錄爬蟲執行"""
        prefix = f"{market} " if market else ""
        self._write(
            log_type=LogType.SCRAPE,
            level=LogLevel.INFO if status == "success" else LogLevel.ERROR,
            message=f"爬蟲執行: {prefix}{symbol} | {records}筆 | {scrape_date}",
            details={
                "symbol": symbol,
                "records": records,
                "market": market or "TW",
                "date": scrape_date,
                "status": status,
            },
        )

    def log_db_change(self, operation: str, table: str, record_id: int,
                      changes: Optional[dict] = None, user_id: Optional[int] = None,
                      symbol: str = ""):
        """記錄資料庫異動"""
        op_map = {"insert": "新增", "update": "編輯", "delete": "刪除"}
        label = op_map.get(operation, operation)
        if symbol:
            msg = f"{label} {symbol} ({table})"
        else:
            msg = f"{label}: {table} id={record_id}"
        self._write(
            log_type=LogType.DB_CHANGE,
            level=LogLevel.INFO,
            message=msg,
            details={
                "operation": operation,
                "table": table,
                "record_id": record_id,
                "user_id": user_id,
                "symbol": symbol,
                "changes": changes or {},
            },
        )

    def log_api_call(self, endpoint: str, method: str, status_code: int,
                     duration_ms: float, user_id: Optional[int] = None,
                     client_ip: Optional[str] = None):
        """記錄 API 呼叫"""
        self._write(
            log_type=LogType.API_CALL,
            level=LogLevel.INFO if status_code < 400 else LogLevel.WARNING,
            message=f"API 呼叫: {method} {endpoint} | {status_code} | {duration_ms:.1f}ms",
            details={
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 1),
                "user_id": user_id,
                "client_ip": client_ip,
            },
        )

    def log_error(self, context: str, error_message: str, stack: Optional[str] = None):
        """記錄錯誤"""
        self._write(
            log_type=LogType.ERROR,
            level=LogLevel.ERROR,
            message=f"錯誤: {context} | {error_message}",
            details={
                "context": context,
                "error_message": error_message,
                "stack": stack,
            },
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write(self, log_type: LogType, level: LogLevel, message: str,
               details: Optional[dict] = None):
        ts = datetime.now(timezone.utc).isoformat()
        record = {
            "timestamp": ts,
            "type": log_type.value,
            "level": level.value,
            "message": message,
            "details": details or {},
            "symbol": details.get("symbol", "") if details else "",
            "user_id": details.get("user_id") if details else None,
        }

        # 1. File log (always)
        file_level = getattr(logging, level.value.upper())
        self._file_logger.log(file_level, message)

        # 2. PostgreSQL (best-effort, don't block on DB errors)
        self._persist_to_db(record)

    def _persist_to_db(self, record: dict):
        try:
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO audit_log (timestamp, type, level, message, details, symbol, user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record["timestamp"],
                        record["type"],
                        record["level"],
                        record["message"],
                        json.dumps(record["details"]),
                        record.get("symbol", ""),
                        record.get("user_id"),
                    ),
                )
                cur.close()
        except Exception:
            # Don't let DB errors break the request
            self._file_logger.warning(f"audit_log write failed: {record.get('message', '')[:80]}")


# Module-level singleton
_action_logger: Optional[ActionLogger] = None


def get_action_logger() -> ActionLogger:
    global _action_logger
    if _action_logger is None:
        _action_logger = ActionLogger()
    return _action_logger
