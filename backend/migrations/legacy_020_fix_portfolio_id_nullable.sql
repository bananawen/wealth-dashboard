-- [migration] 020_fix_portfolio_id_nullable.sql
-- transactions.portfolio_id is NOT NULL but the column is being dropped from the write path.
-- We need it nullable for transactions that only reference account_id (new flow).
-- Strategy: set DEFAULT 1 for existing NULLs, then allow NULL

-- First, set any NULL portfolio_id to account's first portfolio or 1
UPDATE transactions t
SET portfolio_id = COALESCE(
    (SELECT p.id FROM portfolios p WHERE p.user_id = (SELECT user_id FROM accounts WHERE id = t.account_id) LIMIT 1),
    1
)
WHERE t.portfolio_id IS NULL;

-- If still NULL, set to 1
UPDATE transactions SET portfolio_id = 1 WHERE portfolio_id IS NULL;

-- Now make it nullable
ALTER TABLE transactions ALTER COLUMN portfolio_id DROP NOT NULL;
ALTER TABLE transactions ALTER COLUMN portfolio_id SET DEFAULT NULL;

-- Also add realized_gain DEFAULT 0 if not exists
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS realized_gain DECIMAL DEFAULT 0;

-- Verify
DO $$
BEGIN
    RAISE NOTICE 'transactions.portfolio_id NOT NULL: %',
        (SELECT COUNT(*) = 0 FROM transactions WHERE portfolio_id IS NULL);
    RAISE NOTICE 'transactions.realized_gain exists: %',
        EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='transactions' AND column_name='realized_gain');
END;
$$;