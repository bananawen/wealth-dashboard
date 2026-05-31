# 資料庫遷移腳本

所有 `.sql` 檔案需按數字前綴順序執行。PostgreSQL `IF NOT EXISTS` 和 `CREATE INDEX IF NOT EXISTS` 確保 idempotent。

---

## 執行順序

```
002_create_audit_log.sql       → 建立 audit_log 表
014_holdings_readonly.sql       → holdings 唯讀化設計參考（無實際寫入）
016_price_history_tw.sql         → 建立 price_history_tw 表（台股）
017_price_history_us.sql        → 建立 price_history_us 表（美股）
018_holdings_denormalized.sql   → 建立 holdings 表 + sync_holdings_after_transaction 函式 + 回填
019_add_symbol_to_transactions.sql → transactions 新增 symbol 欄位 + 回填 + holdings 重建
020_fix_portfolio_id_nullable.sql → transactions.portfolio_id 改為 nullable + 新增 realized_gain
```

> 注意：中間跳過了 `003`–`013`，表示這些編號的 migration 從未建立或已廢棄。

---

## 002_create_audit_log.sql

**用途：** 建立作業日誌表，作為 Admin 頁面的查詢來源。

**內容：**
- 建立 `audit_log` 表，欄位：`id`, `timestamp`, `type`, `level`, `message`, `details (JSONB)`, `symbol`, `user_id`
- 建立 `idx_audit_log_timestamp` 索引（時間範圍查詢）
- 建立 `idx_audit_log_type` 索引（類型過濾）

**注意事項：**
- `type` 可選值：`scrape` | `db_change` | `api_call` | `error`
- `level` 可選值：`debug` | `info` | `warning` | `error`

---

## 014_holdings_readonly.sql

**用途：** holdings 唯讀化重構的設計參考文件（純 SQL 備註，無實際 DDL）。

**內容：**
- 記錄三種 holdings 唯讀化方案：REVOKE 權限、View 取代 Table、Trigger 阻擋寫入
- 為最終採用的「DB Trigger 阻擋 + Python 程式維護」做文件說明

**注意事項：**
- 此 migration 不執行任何實際寫入操作
- holdings 的實際寫入由 `sync_holdings_after_transaction`  stored procedure 控制在 DB 層

---

## 016_price_history_tw.sql

**用途：** 建立台股歷史價格表（TWSE 上市 + TPEx 上櫃）。

**內容：**
- 建立 `price_history_tw` 表，unique constraint：`symbol` + `price_date`
- 建立三個索引：`(symbol, price_date DESC)`, `(price_date DESC)`, `(symbol)`

**工具來源：** twstock（TWSE/OTC）、TPEx 直接 API

---

## 017_price_history_us.sql

**用途：** 建立美股歷史價格表（NYSE, NASDAQ, AMEX）。

**內容：**
- 建立 `price_history_us` 表，unique constraint：`symbol` + `price_date`
- 建立三個索引：`(symbol, price_date DESC)`, `(price_date DESC)`, `(symbol)`

**工具來源：** yfinance

---

## 018_holdings_denormalized.sql

**用途：** 建立反正規化的 holdings 表，並以 stored procedure 控制在交易寫入時自動同步。

**內容（4 步）：**
1. `transactions` 表新增 `account_id` 欄位（若不存在），預設填 1
2. 建立 `holdings` 表，含 unique constraint `(account_id, symbol)`
3. 建立 `sync_holdings_after_transaction()` stored procedure：
   - `BUY`：upsert holdings（更新 shares, total_cost, avg_cost）
   - `SELL`：扣減 shares，歸零時刪除列
4. 對現有交易記錄執行回填，建立初始 holdings 資料

**注意事項：**
- `sync_holdings_after_transaction` 需在每次 `transactions` 寫入後呼叫
- Python 層（`TransactionService`）已實作呼叫

---

## 019_add_symbol_to_transactions.sql

**用途：** 修復 `transactions` 表缺少 `symbol` 欄位的問題。

**內容（3 步）：**
1. 新增 `symbol VARCHAR(20)` 欄位
2. 透過 `JOIN portfolios ON transactions.portfolio_id = portfolios.id` 回填 symbol
3. 將 `symbol` 改為 `NOT NULL`

**副作用：**
- 同時清除並重建 `holdings` 表（基於有 symbol 的完整交易資料重新彙總）

**注意事項：**
- 此 migration 會刪除並重建所有 holdings 記錄，確保與 transactions 完全一致

---

## 020_fix_portfolio_id_nullable.sql

**用途：** 將 `transactions.portfolio_id` 從 NOT NULL 改為 nullable，支援只靠 `account_id` 運作的新寫入路徑。

**內容：**
1. 將現有 NULL 的 `portfolio_id` 填入 `accounts` 所屬用戶的第一個 portfolio_id 或 1
2. 將 `portfolio_id` 改為 nullable
3. 新增 `realized_gain DECIMAL DEFAULT 0` 欄位（若不存在）

**注意事項：**
- 新流程（`account_id` 僅引用）下 `portfolio_id` 可為 NULL
- `realized_gain` 由 `TransactionService` 在每次 SELL 時計算寫入

---

## 執行建議

```bash
# 依序執行（建議在 psql session 中執行）
psql "$DATABASE_URL" -f 002_create_audit_log.sql
psql "$DATABASE_URL" -f 014_holdings_readonly.sql
psql "$DATABASE_URL" -f 016_price_history_tw.sql
psql "$DATABASE_URL" -f 017_price_history_us.sql
psql "$DATABASE_URL" -f 018_holdings_denormalized.sql
psql "$DATABASE_URL" -f 019_add_symbol_to_transactions.sql
psql "$DATABASE_URL" -f 020_fix_portfolio_id_nullable.sql
```

或確認 PostgreSQL 已有的 `app/scrapers/backfill_lewis.py` 之類的 Migration 機制後再執行。
