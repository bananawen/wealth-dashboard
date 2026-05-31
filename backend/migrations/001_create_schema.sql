-- Migration 001: Create clean wealth schema
-- Date: 2026-05-31
-- Description: Full schema for the wealth tracking system
-- All holdings are COMPUTED from transactions — holdings table is write-once via recompute

-- =============================================================================
-- USERS
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    email           VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

-- =============================================================================
-- ACCOUNTS (brokerage / bank / crypto)
-- =============================================================================
CREATE TABLE IF NOT EXISTS accounts (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    type        VARCHAR(20) NOT NULL CHECK (type IN ('brokerage', 'bank', 'crypto')),
    currency    VARCHAR(3) NOT NULL DEFAULT 'TWD',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts (user_id);

-- =============================================================================
-- TRANSACTIONS (source of truth for all positions)
-- =============================================================================
CREATE TABLE IF NOT EXISTS transactions (
    id              SERIAL PRIMARY KEY,
    account_id      INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    symbol          VARCHAR(20) NOT NULL,
    type            VARCHAR(4) NOT NULL CHECK (type IN ('BUY', 'SELL')),
    quantity        NUMERIC(18, 6) NOT NULL,
    price           NUMERIC(18, 4) NOT NULL,
    fee             NUMERIC(12, 2) NOT NULL DEFAULT 0,
    transaction_date DATE NOT NULL,
    notes           TEXT,
    realized_gain   NUMERIC(18, 4) NOT NULL DEFAULT 0,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id     ON transactions (user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_account_id  ON transactions (account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_symbol       ON transactions (symbol);
CREATE INDEX IF NOT EXISTS idx_transactions_date         ON transactions (transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_type         ON transactions (type);

-- =============================================================================
-- HOLDINGS (system-maintained, derived from transactions — READ ONLY for app)
-- =============================================================================
-- holdings can only be written by _recompute_holdings() triggered from transaction writes
-- Key constraint: (account_id, symbol) unique per user
-- user_id is denormalised for fast filtering; the account_id → user_id chain is the authoritative path

CREATE TABLE IF NOT EXISTS holdings (
    id          SERIAL PRIMARY KEY,
    account_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    symbol      VARCHAR(20) NOT NULL,
    shares      NUMERIC(18, 6) NOT NULL DEFAULT 0,
    avg_cost    NUMERIC(18, 4) NOT NULL DEFAULT 0,
    total_cost  NUMERIC(18, 2) NOT NULL DEFAULT 0,
    currency    VARCHAR(3) NOT NULL DEFAULT 'TWD',
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (account_id, symbol, user_id)
);

CREATE INDEX IF NOT EXISTS idx_holdings_user_id    ON holdings (user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_account_id ON holdings (account_id);
CREATE INDEX IF NOT EXISTS idx_holdings_symbol      ON holdings (symbol);

-- Trigger: prevent direct writes to holdings (all writes must go through _recompute_holdings)
CREATE OR REPLACE FUNCTION block_holdings_manual_write()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'holdings is system-maintained; all changes must go through transactions';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS block_holdings_write ON holdings;
CREATE TRIGGER block_holdings_write
    BEFORE INSERT OR UPDATE OR DELETE ON holdings
    FOR EACH ROW EXECUTE FUNCTION block_holdings_manual_write();

-- =============================================================================
-- PORTFOLIOS
-- =============================================================================
CREATE TABLE IF NOT EXISTS portfolios (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    asset_type  VARCHAR(20),  -- 'stock', 'etf', 'bond', 'crypto', 'cash'
    symbol      VARCHAR(20),  -- underlying symbol if applicable
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portfolios_user_id ON portfolios (user_id);

-- =============================================================================
-- PORTFOLIO SNAPSHOTS (daily NAV)
-- =============================================================================
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date        DATE NOT NULL,
    total_value NUMERIC(18, 2) NOT NULL,
    currency    VARCHAR(3) NOT NULL DEFAULT 'TWD',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_user_id ON portfolio_snapshots (user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_date    ON portfolio_snapshots (date DESC);

-- =============================================================================
-- PRICE HISTORY TAIWAN (TWSE + TPEx)
-- =============================================================================
CREATE TABLE IF NOT EXISTS price_history_tw (
    id          SERIAL PRIMARY KEY,
    symbol      VARCHAR(10) NOT NULL,
    price_date  DATE NOT NULL,
    open        NUMERIC(12, 4) NOT NULL DEFAULT 0,
    high        NUMERIC(12, 4) NOT NULL DEFAULT 0,
    low         NUMERIC(12, 4) NOT NULL DEFAULT 0,
    close       NUMERIC(12, 4) NOT NULL DEFAULT 0,
    volume      BIGINT NOT NULL DEFAULT 0,
    currency    VARCHAR(3) NOT NULL DEFAULT 'TWD',
    source      VARCHAR(10) NOT NULL,  -- 'TWSE' or 'TPEx'
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (symbol, price_date)
);

CREATE INDEX IF NOT EXISTS idx_price_history_tw_symbol_date ON price_history_tw (symbol, price_date DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_tw_price_date  ON price_history_tw (price_date DESC);

-- =============================================================================
-- PRICE HISTORY US (NYSE / NASDAQ / AMEX)
-- =============================================================================
CREATE TABLE IF NOT EXISTS price_history_us (
    id          SERIAL PRIMARY KEY,
    symbol      VARCHAR(10) NOT NULL,
    price_date  DATE NOT NULL,
    open        NUMERIC(12, 4) NOT NULL DEFAULT 0,
    high        NUMERIC(12, 4) NOT NULL DEFAULT 0,
    low         NUMERIC(12, 4) NOT NULL DEFAULT 0,
    close       NUMERIC(12, 4) NOT NULL DEFAULT 0,
    volume      BIGINT NOT NULL DEFAULT 0,
    currency    VARCHAR(3) NOT NULL DEFAULT 'USD',
    source      VARCHAR(10) NOT NULL DEFAULT 'US',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (symbol, price_date)
);

CREATE INDEX IF NOT EXISTS idx_price_history_us_symbol_date ON price_history_us (symbol, price_date DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_us_price_date  ON price_history_us (price_date DESC);

-- =============================================================================
-- STOCK INFO (reference data)
-- =============================================================================
CREATE TABLE IF NOT EXISTS stock_info (
    symbol           VARCHAR(20) PRIMARY KEY,
    name             VARCHAR(255),
    exchange         VARCHAR(20),   -- 'TWSE', 'TPEx', 'NYSE', 'NASDAQ', 'AMEX', 'OTC'
    is_delisted      BOOLEAN NOT NULL DEFAULT FALSE,
    last_known_price NUMERIC(12, 4),
    last_updated     TIMESTAMPTZ
);

-- =============================================================================
-- CURRENCY CACHE
-- =============================================================================
CREATE TABLE IF NOT EXISTS currency_cache (
    currency     VARCHAR(3) PRIMARY KEY,
    rate_to_twd  NUMERIC(12, 6) NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed default rates
INSERT INTO currency_cache (currency, rate_to_twd, updated_at) VALUES
    ('USD', 32.0, NOW()),
    ('TWD', 1.0,  NOW()),
    ('HKD', 4.1,  NOW()),
    ('JPY', 0.21, NOW()),
    ('EUR', 35.0, NOW()),
    ('GBP', 40.0, NOW())
ON CONFLICT (currency) DO NOTHING;

-- =============================================================================
-- AUDIT LOG (unified operation log)
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    type        VARCHAR(20) NOT NULL CHECK (type IN ('scrape', 'trade', 'holding_change', 'system', 'auth')),
    level       VARCHAR(10) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR')),
    message     TEXT NOT NULL,
    details     JSONB NOT NULL DEFAULT '{}',
    symbol      VARCHAR(20),
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_type      ON audit_log (type);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id   ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_symbol    ON audit_log (symbol);