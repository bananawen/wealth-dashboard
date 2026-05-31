-- [migration] 018_holdings_denormalized.sql
-- Purpose: Create a denormalized holdings table and sync after each transaction write
-- After this migration:
--   • holdings table is the source of truth for current positions
--   • Every INSERT/UPDATE/DELETE on transactions triggers a holdings sync
--   • holdings/computed API reads directly from holdings table (fast)

-- =============================================================================
-- STEP 1: Add account_id to transactions if not exists
-- =============================================================================
-- Note: transactions table already exists with portfolio_id; we add account_id
-- as a bridge to the new accounts table. Default all existing transactions
-- to account_id = 1 (first brokerage account).

-- Add account_id column
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS account_id INTEGER;
-- Populate from accounts if possible, default to 1
UPDATE transactions SET account_id = 1 WHERE account_id IS NULL;

-- =============================================================================
-- STEP 2: Create holdings table (if not exists)
-- =============================================================================
CREATE TABLE IF NOT EXISTS holdings (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    symbol VARCHAR(20) NOT NULL,
    shares DECIMAL NOT NULL DEFAULT 0,
    avg_cost DECIMAL NOT NULL DEFAULT 0,
    total_cost DECIMAL NOT NULL DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(account_id, symbol)
);

-- =============================================================================
-- STEP 3: Sync function — call after every transaction write
-- =============================================================================
CREATE OR REPLACE FUNCTION sync_holdings_after_transaction(_account_id INTEGER, _symbol VARCHAR, _type VARCHAR, _shares DECIMAL, _price DECIMAL)
RETURNS VOID AS $$
DECLARE
    _currency VARCHAR(3);
BEGIN
    -- Get currency from account
    SELECT currency INTO _currency FROM accounts WHERE id = _account_id;

    IF _type IN ('BUY', 'buy') THEN
        INSERT INTO holdings (account_id, symbol, shares, avg_cost, total_cost, currency)
        VALUES (_account_id, _symbol, _shares, _price, _shares * _price, _currency)
        ON CONFLICT (account_id, symbol) DO UPDATE SET
            shares = holdings.shares + EXCLUDED.shares,
            total_cost = holdings.total_cost + EXCLUDED.total_cost,
            avg_cost = (holdings.total_cost + EXCLUDED.total_cost) / (holdings.shares + EXCLUDED.shares),
            currency = EXCLUDED.currency,
            updated_at = NOW()
        WHERE holdings.account_id = _account_id AND holdings.symbol = _symbol;

    ELSIF _type IN ('SELL', 'sell') THEN
        UPDATE holdings
        SET shares = holdings.shares - _shares,
            avg_cost = holdings.avg_cost,  -- selling doesn't change avg cost
            updated_at = NOW()
        WHERE holdings.account_id = _account_id AND holdings.symbol = _symbol
          AND holdings.shares > 0;

        -- Delete if shares now zero
        DELETE FROM holdings WHERE account_id = _account_id AND symbol = _symbol AND shares <= 0;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- STEP 4: Backfill holdings from existing transactions (if any)
-- =============================================================================
-- Only if transactions table is not empty
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT t.account_id, t.symbol, t.type,
               SUM(CASE WHEN t.type IN ('BUY','buy') THEN t.quantity ELSE 0 END) AS buy_qty,
               SUM(CASE WHEN t.type IN ('SELL','sell') THEN t.quantity ELSE 0 END) AS sell_qty,
               SUM(CASE WHEN t.type IN ('BUY','buy') THEN t.quantity * t.price ELSE 0 END) AS buy_cost,
               MIN(a.currency) AS currency
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        GROUP BY t.account_id, t.symbol
        HAVING SUM(CASE WHEN t.type IN ('BUY','buy') THEN t.quantity ELSE 0 END) > 0
    LOOP
        INSERT INTO holdings (account_id, symbol, shares, avg_cost, total_cost, currency)
        VALUES (r.account_id, r.symbol,
                r.buy_qty - r.sell_qty,
                CASE WHEN r.buy_qty > 0 THEN r.buy_cost / r.buy_qty ELSE 0 END,
                (r.buy_qty - r.sell_qty) * CASE WHEN r.buy_qty > 0 THEN r.buy_cost / r.buy_qty ELSE 0 END,
                r.currency)
        ON CONFLICT (account_id, symbol) DO UPDATE SET
            shares = EXCLUDED.shares,
            avg_cost = EXCLUDED.avg_cost,
            total_cost = EXCLUDED.total_cost,
            currency = EXCLUDED.currency,
            updated_at = NOW();
    END LOOP;
END;
$$;

-- =============================================================================
-- VERIFY
-- =============================================================================
-- SELECT 'holdings rows:' AS check, COUNT(*) FROM holdings;
