-- Migration: Create price_history_us table for US stock historical prices
-- NYSE, NASDAQ, AMEX historical OHLCV data
--
-- Tool: yfinance

CREATE TABLE IF NOT EXISTS price_history_us (
    id            SERIAL PRIMARY KEY,
    symbol        VARCHAR(10) NOT NULL,
    price_date    DATE NOT NULL,
    open          NUMERIC(12, 4) NOT NULL DEFAULT 0,
    high          NUMERIC(12, 4) NOT NULL DEFAULT 0,
    low           NUMERIC(12, 4) NOT NULL DEFAULT 0,
    close         NUMERIC(12, 4) NOT NULL DEFAULT 0,
    volume        BIGINT NOT NULL DEFAULT 0,
    currency      VARCHAR(3) NOT NULL DEFAULT 'USD',
    source        VARCHAR(10) NOT NULL DEFAULT 'US',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (symbol, price_date)
);

CREATE INDEX IF NOT EXISTS idx_price_history_us_symbol_date
    ON price_history_us (symbol, price_date DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_us_price_date
    ON price_history_us (price_date DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_us_symbol
    ON price_history_us (symbol);
