-- Migration: Create price_history_tw table for Taiwan stock historical prices
-- TWSE (上市) + TPEx (上櫃) historical OHLCV data
--
-- Tools: twstock (TWSE/OTC), direct TPEx API

CREATE TABLE IF NOT EXISTS price_history_tw (
    id            SERIAL PRIMARY KEY,
    symbol        VARCHAR(10) NOT NULL,
    price_date    DATE NOT NULL,
    open          NUMERIC(12, 4) NOT NULL DEFAULT 0,
    high          NUMERIC(12, 4) NOT NULL DEFAULT 0,
    low           NUMERIC(12, 4) NOT NULL DEFAULT 0,
    close         NUMERIC(12, 4) NOT NULL DEFAULT 0,
    volume        BIGINT NOT NULL DEFAULT 0,
    currency      VARCHAR(3) NOT NULL DEFAULT 'TWD',
    source        VARCHAR(10) NOT NULL,  -- 'TWSE' or 'TPEx'
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (symbol, price_date)
);

CREATE INDEX IF NOT EXISTS idx_price_history_tw_symbol_date
    ON price_history_tw (symbol, price_date DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_tw_price_date
    ON price_history_tw (price_date DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_tw_symbol
    ON price_history_tw (symbol);
