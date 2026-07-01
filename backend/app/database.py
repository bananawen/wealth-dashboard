import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import get_settings

settings = get_settings()
_sqlite_initialized_paths: set[str] = set()
_postgres_initialized = False
BACKEND_DIR = Path(__file__).resolve().parents[1]


SQLITE_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('BUY', 'SELL')),
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    fee REAL NOT NULL DEFAULT 0,
    tax REAL NOT NULL DEFAULT 0,
    transaction_date TEXT NOT NULL,
    notes TEXT,
    category TEXT,
    asset_class TEXT,
    sector TEXT,
    realized_gain REAL NOT NULL DEFAULT 0,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    currency TEXT NOT NULL DEFAULT 'TWD',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions (user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_symbol ON transactions (symbol);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions (transaction_date DESC);

CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    shares REAL NOT NULL DEFAULT 0,
    avg_cost REAL NOT NULL DEFAULT 0,
    total_cost REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'TWD',
    total_cost_twd REAL NOT NULL DEFAULT 0,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON holdings (user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON holdings (symbol);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    total_value REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'TWD',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, date)
);

CREATE TABLE IF NOT EXISTS currency_cache (
    currency TEXT PRIMARY KEY,
    rate_to_twd REAL NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO currency_cache (currency, rate_to_twd) VALUES
    ('TWD', 1.0),
    ('USD', 32.0),
    ('HKD', 4.1),
    ('JPY', 0.21),
    ('EUR', 35.0),
    ('GBP', 40.0);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    type TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT,
    symbol TEXT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_type ON audit_log (type);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log (user_id);

CREATE TABLE IF NOT EXISTS price_history_tw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    price_date TEXT NOT NULL,
    open REAL NOT NULL DEFAULT 0,
    high REAL NOT NULL DEFAULT 0,
    low REAL NOT NULL DEFAULT 0,
    close REAL NOT NULL DEFAULT 0,
    volume INTEGER NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'TWD',
    source TEXT NOT NULL DEFAULT 'TW',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (symbol, price_date)
);

CREATE TABLE IF NOT EXISTS price_history_us (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    price_date TEXT NOT NULL,
    open REAL NOT NULL DEFAULT 0,
    high REAL NOT NULL DEFAULT 0,
    low REAL NOT NULL DEFAULT 0,
    close REAL NOT NULL DEFAULT 0,
    volume INTEGER NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'USD',
    source TEXT NOT NULL DEFAULT 'US',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (symbol, price_date)
);

CREATE TABLE IF NOT EXISTS stock_info (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    exchange TEXT NOT NULL,
    is_delisted INTEGER NOT NULL DEFAULT 0,
    last_known_price REAL,
    last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_info_exchange ON stock_info (exchange);
"""


def is_sqlite_url(database_url: str | None = None) -> bool:
    url = database_url or settings.DATABASE_URL
    return url.startswith("sqlite:///") or url.startswith("sqlite://")


def _sqlite_path(database_url: str) -> Path:
    parsed = urlparse(database_url)
    raw_path = parsed.path or ""
    if database_url.startswith("sqlite:///./"):
        raw_path = database_url.removeprefix("sqlite:///")
    elif database_url.startswith("sqlite:///:memory:"):
        raw_path = ":memory:"

    if raw_path == ":memory:":
        return Path(raw_path)
    path = Path(raw_path)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return path


def _initialize_sqlite(conn: sqlite3.Connection, path: Path) -> None:
    key = str(path)
    if key in _sqlite_initialized_paths:
        return
    conn.executescript(SQLITE_SCHEMA)
    conn.commit()
    _ensure_sqlite_users_role_column(conn)
    _ensure_sqlite_transaction_columns(conn)
    _ensure_sqlite_stock_info_table(conn)
    _migrate_sqlite_accountless_schema(conn)
    _sqlite_initialized_paths.add(key)


def _ensure_sqlite_users_role_column(conn: sqlite3.Connection) -> None:
    cur = conn.execute("PRAGMA table_info(users)")
    columns = {row[1] for row in cur.fetchall()}
    if "role" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        conn.commit()


def _ensure_sqlite_transaction_columns(conn: sqlite3.Connection) -> None:
    def _columns(table: str) -> set[str]:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cur.fetchall()}

    tx_cols = _columns("transactions")
    if "tax" not in tx_cols:
        conn.execute("ALTER TABLE transactions ADD COLUMN tax REAL NOT NULL DEFAULT 0")
    if "category" not in tx_cols:
        conn.execute("ALTER TABLE transactions ADD COLUMN category TEXT")
    if "asset_class" not in tx_cols:
        conn.execute("ALTER TABLE transactions ADD COLUMN asset_class TEXT")
    if "sector" not in tx_cols:
        conn.execute("ALTER TABLE transactions ADD COLUMN sector TEXT")
    conn.commit()


def _ensure_sqlite_stock_info_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_info (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            exchange TEXT NOT NULL,
            is_delisted INTEGER NOT NULL DEFAULT 0,
            last_known_price REAL,
            last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_info_exchange ON stock_info (exchange)")
    conn.commit()


def _sqlite_has_table(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    )
    return cur.fetchone() is not None


def _sqlite_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def _migrate_sqlite_accountless_schema(conn: sqlite3.Connection) -> None:
    has_accounts_table = _sqlite_has_table(conn, "accounts")
    tx_has_account_id = _sqlite_has_table(conn, "transactions") and "account_id" in _sqlite_columns(conn, "transactions")
    holdings_has_account_id = _sqlite_has_table(conn, "holdings") and "account_id" in _sqlite_columns(conn, "holdings")

    if not any((has_accounts_table, tx_has_account_id, holdings_has_account_id)):
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        if tx_has_account_id:
            conn.execute(
                """
                CREATE TABLE transactions_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('BUY', 'SELL')),
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    fee REAL NOT NULL DEFAULT 0,
                    tax REAL NOT NULL DEFAULT 0,
                    transaction_date TEXT NOT NULL,
                    notes TEXT,
                    category TEXT,
                    asset_class TEXT,
                    sector TEXT,
                    realized_gain REAL NOT NULL DEFAULT 0,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    currency TEXT NOT NULL DEFAULT 'TWD',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                INSERT INTO transactions_new (
                    id, symbol, type, quantity, price, fee, tax, transaction_date,
                    notes, category, asset_class, sector, realized_gain, user_id, currency, created_at
                )
                SELECT
                    id, symbol, type, quantity, price, COALESCE(fee, 0), COALESCE(tax, 0), transaction_date,
                    notes, category, NULL, NULL, COALESCE(realized_gain, 0), user_id, COALESCE(currency, 'TWD'), created_at
                FROM transactions
                """
            )
            conn.execute("DROP TABLE transactions")
            conn.execute("ALTER TABLE transactions_new RENAME TO transactions")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions (user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_symbol ON transactions (symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions (transaction_date DESC)")

        if holdings_has_account_id:
            conn.execute(
                """
                CREATE TABLE holdings_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    shares REAL NOT NULL DEFAULT 0,
                    avg_cost REAL NOT NULL DEFAULT 0,
                    total_cost REAL NOT NULL DEFAULT 0,
                    currency TEXT NOT NULL DEFAULT 'TWD',
                    total_cost_twd REAL NOT NULL DEFAULT 0,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (user_id, symbol)
                )
                """
            )
            conn.execute(
                """
                INSERT INTO holdings_new (
                    id, symbol, shares, avg_cost, total_cost, currency, total_cost_twd, user_id, updated_at
                )
                SELECT
                    id, symbol, shares, avg_cost, total_cost, COALESCE(currency, 'TWD'),
                    COALESCE(total_cost_twd, 0), user_id, updated_at
                FROM holdings
                """
            )
            conn.execute("DROP TABLE holdings")
            conn.execute("ALTER TABLE holdings_new RENAME TO holdings")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON holdings (user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON holdings (symbol)")

        if has_accounts_table:
            conn.execute("DROP TABLE accounts")

        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def _ensure_postgres_users_role_column(conn) -> None:
    global _postgres_initialized
    if _postgres_initialized:
        return

    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'role'
        """
    )
    has_role = cur.fetchone() is not None
    if not has_role:
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'")
    cur.execute("UPDATE users SET role = 'user' WHERE role IS NULL OR role = ''")
    conn.commit()
    cur.close()
    _postgres_initialized = True


def _ensure_postgres_transaction_columns(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        ALTER TABLE transactions
        ADD COLUMN IF NOT EXISTS asset_class TEXT
        """
    )
    cur.execute(
        """
        ALTER TABLE transactions
        ADD COLUMN IF NOT EXISTS sector TEXT
        """
    )
    conn.commit()
    cur.close()


def _ensure_postgres_stock_info_table(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_info (
            symbol VARCHAR(20) PRIMARY KEY,
            name VARCHAR(255),
            exchange VARCHAR(20) NOT NULL,
            is_delisted BOOLEAN NOT NULL DEFAULT FALSE,
            last_known_price NUMERIC(12, 4),
            last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stock_info_exchange ON stock_info (exchange)")
    conn.commit()
    cur.close()


def _normalize_sql_for_sqlite(sql: str) -> str:
    sql = sql.replace("%s", "?")
    sql = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", sql, flags=re.IGNORECASE)
    sql = sql.replace("type::text", "type")
    sql = sql.replace("price_date::text", "price_date")
    return sql


class SQLiteCursor:
    def __init__(self, cursor: sqlite3.Cursor):
        self._cursor = cursor

    def execute(self, sql: str, params=None):
        return self._cursor.execute(_normalize_sql_for_sqlite(sql), params or ())

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        return self._cursor.close()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid


class SQLiteConnection:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def cursor(self):
        return SQLiteCursor(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def execute(self, sql: str, params=None):
        return self._conn.execute(_normalize_sql_for_sqlite(sql), params or ())


def get_connection():
    if is_sqlite_url():
        path = _sqlite_path(settings.DATABASE_URL)
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(":memory:" if str(path) == ":memory:" else path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _initialize_sqlite(conn, path)
        return SQLiteConnection(conn)

    conn = psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)
    _ensure_postgres_users_role_column(conn)
    _ensure_postgres_transaction_columns(conn)
    _ensure_postgres_stock_info_table(conn)
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
