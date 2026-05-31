-- Migration: Create audit_log table for operation logs
-- Run this against the PostgreSQL database

CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    type        VARCHAR(20) NOT NULL,   -- 'scrape' | 'db_change' | 'api_call' | 'error'
    level       VARCHAR(10) NOT NULL,   -- 'debug' | 'info' | 'warning' | 'error'
    message     TEXT NOT NULL,
    details     JSONB NOT NULL DEFAULT '{}'
);

-- Index for time-range queries (Admin page shows latest first)
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log (timestamp DESC);

-- Index for type filtering
CREATE INDEX IF NOT EXISTS idx_audit_log_type ON audit_log (type);