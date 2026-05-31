"""
Database monitoring API
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime
import psycopg2
from ..config import get_settings
from ..logging_config import logger

router = APIRouter(prefix="/admin", tags=["admin"])

settings = get_settings()


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


@router.get("/db/stats", response_model=DatabaseStats)
async def get_database_stats():
    """Get database statistics and table info"""
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        
        # Get total database size
        cur.execute("""
            SELECT pg_size_pretty(pg_database_size(current_database()))
        """)
        total_size_pretty = cur.fetchone()[0]
        
        cur.execute("""
            SELECT pg_size_pretty(pg_database_size(current_database()))
        """)
        total_bytes = cur.fetchone()[0]
        
        # Get table info
        cur.execute("""
            SELECT 
                schemaname || '.' || tablename as table_name,
                row_count,
                pg_total_relation_size(schemaname || '.' || tablename) as size_bytes
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
        """)
        tables_data = cur.fetchall()
        
        # Get last vacuum/analyze
        cur.execute("""
            SELECT last_vacuum, last_analyze 
            FROM pg_stat_user_tables 
            ORDER BY last_vacuum DESC NULLS LAST, last_analyze DESC NULLS LAST 
            LIMIT 1
        """)
        vac_analyze = cur.fetchone()
        
        tables = [
            TableInfo(
                table_name=row[0],
                row_count=row[1],
                size_bytes=row[2]
            )
            for row in tables_data
        ]
        
        cur.close()
        conn.close()
        
        logger.info(f"Database stats fetched: {len(tables)} tables")
        
        return DatabaseStats(
            total_size_bytes=total_bytes,
            total_size_mb=round(total_bytes / (1024 * 1024), 2),
            table_count=len(tables),
            tables=tables,
            last_vacuum=vac_analyze[0].isoformat() if vac_analyze and vac_analyze[0] else None,
            last_analyze=vac_analyze[1].isoformat() if vac_analyze and vac_analyze[1] else None,
        )
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise


@router.get("/status")
async def get_admin_status():
    """Combined admin status: DB connection + table stats + scraper status"""
    import psycopg2
    connected = False
    tables = []
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            SELECT schemaname || '.' || relname as table_name,
                   n_live_tup as row_count,
                   pg_total_relation_size(schemaname || '.' || relname) as size_bytes
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname || '.' || relname) DESC
        """)
        tables_data = cur.fetchall()
        tables = [
            {"table_name": row[0], "row_count": row[1], "size_bytes": row[2]}
            for row in tables_data
        ]
        cur.close()
        conn.close()
        connected = True
    except Exception as e:
        logger.error(f"Failed to connect to DB: {e}")

    return {
        "connected": connected,
        "tables": tables,
        "scrapers": [
            {
                "name": "Taiwan Stock Scraper",
                "last_run": datetime.now().isoformat(),
                "records_fetched": 0,
                "status": "idle"
            },
            {
                "name": "US Stock Scraper",
                "last_run": datetime.now().isoformat(),
                "records_fetched": 0,
                "status": "idle"
            }
        ]
    }


@router.get("/scraper/status")
async def get_scraper_status():
    """Get scraper status (mock for now - in production would check actual scraper logs)"""
    # In production, this would read from a scraper_status table
    # For now, return mock data
    return {
        "scrapers": [
            {
                "name": "Taiwan Stock Scraper",
                "last_run": datetime.now().isoformat(),
                "records_fetched": 0,
                "status": "idle"
            },
            {
                "name": "US Stock Scraper", 
                "last_run": datetime.now().isoformat(),
                "records_fetched": 0,
                "status": "idle"
            }
        ],
        "next_scheduled_run": {
            "us_market": "21:30 ET",
            "tw_market": "13:30 TT"
        }
    }


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