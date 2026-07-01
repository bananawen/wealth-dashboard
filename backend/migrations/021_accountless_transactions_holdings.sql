-- Migration 021: Align schema with account-less transaction source-of-truth flow
-- Date: 2026-06-20
--
-- Application contract after architecture refactor:
--   1. transactions is the only public write source for position changes.
--   2. holdings is a system-maintained projection written by backend services.
--   3. account_id is optional because the current app no longer exposes accounts.
--   4. currency lives on transactions and holdings so TWD aggregation is explicit.

-- =============================================================================
-- TRANSACTIONS
-- =============================================================================

ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'TWD';

UPDATE transactions
SET currency = CASE WHEN symbol ~ '^[0-9]+$' THEN 'TWD' ELSE 'USD' END
WHERE currency IS NULL;

ALTER TABLE transactions
    ALTER COLUMN currency SET NOT NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'transactions'
          AND column_name = 'account_id'
    ) THEN
        ALTER TABLE transactions ALTER COLUMN account_id DROP NOT NULL;
    END IF;
END;
$$;

-- =============================================================================
-- HOLDINGS PROJECTION
-- =============================================================================

ALTER TABLE holdings
    ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'TWD',
    ADD COLUMN IF NOT EXISTS total_cost_twd NUMERIC(18, 2) DEFAULT 0;

UPDATE holdings
SET currency = CASE WHEN symbol ~ '^[0-9]+$' THEN 'TWD' ELSE 'USD' END
WHERE currency IS NULL;

UPDATE holdings
SET total_cost_twd = total_cost
WHERE total_cost_twd IS NULL;

ALTER TABLE holdings
    ALTER COLUMN currency SET NOT NULL,
    ALTER COLUMN total_cost_twd SET NOT NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'holdings'
          AND column_name = 'account_id'
    ) THEN
        ALTER TABLE holdings ALTER COLUMN account_id DROP NOT NULL;
    END IF;
END;
$$;

-- The app now protects public holdings mutation at the API layer while still
-- allowing backend projection writes. Remove the old blanket DB trigger if it
-- came from 001_create_schema.sql.
DROP TRIGGER IF EXISTS block_holdings_write ON holdings;
DROP FUNCTION IF EXISTS block_holdings_manual_write();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'holdings_user_symbol_key'
          AND conrelid = 'holdings'::regclass
    ) THEN
        ALTER TABLE holdings
            ADD CONSTRAINT holdings_user_symbol_key UNIQUE (user_id, symbol);
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_holdings_user_symbol ON holdings (user_id, symbol);

-- =============================================================================
-- VERIFY
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'transactions.currency exists: %',
        EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'transactions' AND column_name = 'currency'
        );
    RAISE NOTICE 'holdings.total_cost_twd exists: %',
        EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'holdings' AND column_name = 'total_cost_twd'
        );
    RAISE NOTICE 'holdings_user_symbol_key exists: %',
        EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'holdings_user_symbol_key'
              AND conrelid = 'holdings'::regclass
        );
END;
$$;
