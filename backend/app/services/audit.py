"""
Audit logging service.
All significant operations (holdings, transactions, scraper actions) write to audit_log.
"""
import json
from datetime import datetime
from app.database import get_db


def write_log(
    type: str,
    level: str,
    message: str,
    details: dict = None,
    symbol: str = None,
    user_id: int = None,
):
    """
    Write a record to the audit_log table.
    
    Args:
        type: 'transaction', 'scraper', 'auth', 'admin'
        level: 'INFO', 'WARNING', 'ERROR', 'DEBUG'
        message: Human-readable description
        details: Optional dict (stored as JSONB)
        symbol: Optional stock symbol
        user_id: Optional user ID
    """
    normalized_type = {
        "holdings": "transaction",
        "db_change": "transaction",
        "scrape": "scraper",
        "scraper": "scraper",
        "api_call": "admin",
        "error": "admin",
        "admin": "admin",
        "auth": "auth",
        "transaction": "transaction",
    }.get(type, type)
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO audit_log (timestamp, type, level, message, details, symbol, user_id)
                VALUES (CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s)
                """,
                (
                    normalized_type,
                    level,
                    message,
                    json.dumps(details) if details else None,
                    symbol,
                    user_id,
                ),
            )
            conn.commit()
            cur.close()
    except Exception as e:
        # Don't let audit failures break main operations
        import logging
        logging.getLogger(__name__).error(f"Failed to write audit log: {e}")


def log_auth(action: str, message: str, user_id: int = None, details: dict = None):
    write_log(
        type="auth",
        level="INFO",
        message=message,
        details={"action": action, **(details or {})},
        user_id=user_id,
    )


def log_holding_change(action: str, holding_id: int, symbol: str, user_id: int, details: dict = None):
    write_log(
        type="transaction",
        level="INFO",
        message=f"{action} holding id={holding_id} symbol={symbol}",
        details=details,
        symbol=symbol,
        user_id=user_id,
    )


def log_transaction(action: str, tx_id: int, symbol: str, tx_type: str, user_id: int, details: dict = None):
    write_log(
        type="transaction",
        level="INFO",
        message=f"{action} transaction id={tx_id} symbol={symbol} type={tx_type}",
        details=details,
        symbol=symbol,
        user_id=user_id,
    )
