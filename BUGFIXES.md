# Bugfix Log

This log tracks critical bugs, their root causes, and the fixes applied. It serves as a historical record and aids in preventing regressions.

---

## Bug: holdings.total_cost was exactly 2x the correct value

**Date:** 2026-05-31
**Severity:** Critical data error

**Root Cause:**
Two competing write mechanisms were both updating the `holdings` table:
1. PostgreSQL trigger `trg_sync_holdings` on the `transactions` table — increments shares/cost on each INSERT
2. Python function `_recompute_holdings()` in `backend/app/routers/transactions.py` — deletes and recreates holdings rows after each transaction

Both mechanisms write to `holdings`, so the cost was accumulated twice.

**Fix Applied:**
1. Dropped the redundant PostgreSQL trigger: `DROP TRIGGER trg_sync_holdings ON transactions;`
2. Recalculated and corrected all holdings rows from the transactions table

**Files changed:**
- `backend/app/routers/holdings.py` (unchanged — the Python code was correct)
- Database: `holdings` table corrected, `trg_sync_holdings` trigger dropped

**Verification SQL:**
```sql
SELECT h.symbol, h.total_cost,
       COALESCE(SUM(CASE WHEN t.type='BUY' THEN t.quantity * t.price ELSE 0 END), 0) as tx_cost
FROM holdings h
LEFT JOIN transactions t ON h.account_id = t.account_id AND h.symbol = t.symbol AND h.user_id = t.user_id
GROUP BY h.symbol, h.total_cost;
```
