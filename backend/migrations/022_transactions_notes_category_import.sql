-- Migration 022: transaction notes, category, fee/tax accounting, and import readiness
-- Date: 2026-06-20

ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS category TEXT,
    ADD COLUMN IF NOT EXISTS tax NUMERIC(18, 4) NOT NULL DEFAULT 0;

UPDATE transactions
SET tax = 0
WHERE tax IS NULL;

ALTER TABLE transactions
    ALTER COLUMN tax SET NOT NULL;

-- Keep existing fee column as-is; it already exists in the live schema.

-- Optional helper indexes for filtering by category and type.
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions (category);
CREATE INDEX IF NOT EXISTS idx_transactions_type_category ON transactions (type, category);
