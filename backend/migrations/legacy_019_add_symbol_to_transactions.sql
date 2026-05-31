-- [migration] 019_add_symbol_to_transactions.sql
-- Purpose: transactions table is missing symbol column (it was removed at some point).
-- This migration:
--   1. Adds symbol VARCHAR(20) to transactions
--   2. Backfills symbol from JOIN portfolios ON transactions.portfolio_id = portfolios.id
--   3. Makes symbol NOT NULL going forward

-- =============================================================================
-- STEP 1: Add symbol column
-- =============================================================================
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS symbol VARCHAR(20);

-- =============================================================================
-- STEP 2: Backfill symbol from portfolio join
-- =============================================================================
UPDATE transactions t
SET symbol = p.symbol
FROM portfolios p
WHERE t.portfolio_id = p.id AND t.symbol IS NULL;

-- =============================================================================
-- STEP 3: Mark symbol as NOT NULL (after backfill is complete)
-- =============================================================================
ALTER TABLE transactions ALTER COLUMN symbol SET NOT NULL;

-- =============================================================================
-- VERIFY
-- =============================================================================
DO $$
DECLARE
    missing_count INTEGER;
    holdings_before INTEGER;
    holdings_after INTEGER;
BEGIN
    -- Count any still-null symbols
    SELECT COUNT(*) INTO missing_count FROM transactions WHERE symbol IS NULL;
    RAISE NOTICE 'Transactions with NULL symbol: %', missing_count;

    -- Count holdings before
    SELECT COUNT(*) INTO holdings_before FROM holdings;

    -- =============================================================================
    -- Backfill holdings from existing transactions (same logic as 018, but now works)
    -- =============================================================================
    DELETE FROM holdings;

    INSERT INTO holdings (account_id, symbol, shares, avg_cost, total_cost, currency)
    SELECT
        t.account_id,
        t.symbol,
        COALESCE(SUM(CASE WHEN t.type IN ('BUY','buy') THEN t.quantity ELSE 0 END) -
                 SUM(CASE WHEN t.type IN ('SELL','sell') THEN t.quantity ELSE 0 END), 0) AS shares,
        CASE
            WHEN SUM(CASE WHEN t.type IN ('BUY','buy') THEN t.quantity ELSE 0 END) > 0
            THEN SUM(CASE WHEN t.type IN ('BUY','buy') THEN t.quantity * t.price ELSE 0 END) /
                 SUM(CASE WHEN t.type IN ('BUY','buy') THEN t.quantity ELSE 0 END)
            ELSE 0
        END AS avg_cost,
        COALESCE(SUM(CASE WHEN t.type IN ('BUY','buy') THEN t.quantity ELSE 0 END) -
                 SUM(CASE WHEN t.type IN ('SELL','sell') THEN t.quantity ELSE 0 END), 0) *
        CASE
            WHEN SUM(CASE WHEN t.type IN ('BUY','buy') THEN t.quantity ELSE 0 END) > 0
            THEN SUM(CASE WHEN t.type IN ('BUY','buy') THEN t.quantity * t.price ELSE 0 END) /
                 SUM(CASE WHEN t.type IN ('BUY','buy') THEN t.quantity ELSE 0 END)
            ELSE 0
        END AS total_cost,
        a.currency
    FROM transactions t
    JOIN accounts a ON t.account_id = a.id
    GROUP BY t.account_id, t.symbol, a.currency
    HAVING COALESCE(SUM(CASE WHEN t.type IN ('BUY','buy') THEN t.quantity ELSE 0 END) -
                  SUM(CASE WHEN t.type IN ('SELL','sell') THEN t.quantity ELSE 0 END), 0) > 0;

    -- Count holdings after
    SELECT COUNT(*) INTO holdings_after FROM holdings;
    RAISE NOTICE 'Holdings before: %, after: %', holdings_before, holdings_after;
END;
$$;

-- =============================================================================
-- FINAL VERIFY
-- =============================================================================
SELECT 'transactions' AS tbl, COUNT(*) AS rows, COUNT(symbol) AS with_symbol FROM transactions;
SELECT 'holdings' AS tbl, COUNT(*) AS rows FROM holdings;
SELECT account_id, symbol, shares, avg_cost, total_cost, currency FROM holdings ORDER BY account_id, symbol;