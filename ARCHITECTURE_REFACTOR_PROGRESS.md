# Architecture Refactor Progress

## Goal

修正專案架構中已盤點出的核心問題：計算邏輯分散、資料真相不清、schema 漂移、前端 API/型別重複、安全設定不足。

## Phase 1 - Unified Calculation Services

Status: Complete

### Completed

- Added `FxService` as the single source for currency-to-TWD rates.
- Expanded `PriceService` quote shape with `exchange`, `currency`, and `source`.
- Added cached `PriceService.get_price_cached()`.
- Added `HoldingService` for computed holdings and shared position math.
- Added `PortfolioService` for portfolio summary, realized gain conversion, day change, and XIRR.
- Updated holdings and portfolio routers to delegate calculation to services.
- Removed the `portfolio -> holdings private function` dependency.
- Added a standard-library Phase 1 service calculation test.
- Added `pytest` to backend requirements because the existing backend tests require it but the environment did not include it.
- Gated existing ASGI, database, and external scraper tests behind explicit environment variables so default test runs do not hang on TestClient, real DB, or network calls.

### Verification

- Passed: `python3 -m compileall backend/app`
- Passed: `backend/venv/bin/python -m compileall backend/app`
- Passed: `backend/venv/bin/python -c "import sys; sys.path.insert(0, 'backend'); from app.main import app; print(app.title)"`
- Passed: `backend/venv/bin/python -c "import sys; sys.path.insert(0, 'backend'); from app.services.portfolio_service import PortfolioService; from app.services.holding_service import HoldingService; from app.services.fx_service import FxService; from app.services.price_service import PriceService; print('services ok')"`
- Passed: `backend/venv/bin/python backend/tests/test_phase1_services.py`
- Passed: `backend/venv/bin/python -m pytest backend/tests/test_api.py backend/tests/test_phase1_services.py -q`
  - Result: `1 passed, 8 skipped, 5 warnings`
  - Skips are intentional gates for ASGI (`RUN_ASGI_TESTS=1`), DB (`RUN_DB_TESTS=1`), and network scraper tests (`RUN_NETWORK_TESTS=1`).

### Notes

- System Python still cannot run backend tests because it does not have project dependencies such as `yfinance`.
- The project venv now has `pytest==8.3.3` installed.

## Phase 2 - Transaction Source of Truth

Status: Complete

### Target

- Make transaction writes the only supported way to change position quantities and costs.
- Prevent direct public mutation of holdings.
- Move holdings projection/recompute logic out of routers.

### Completed

- Added `HoldingProjectionService` and moved holdings recomputation out of `transactions.py`.
- Added `TransactionUpdate` schema.
- Added `PUT /transactions/{transaction_id}` so frontend edit flows can update transactions instead of holdings.
- Updated transaction create/delete to use `HoldingProjectionService`.
- Converted `POST /holdings`, `PUT /holdings/{id}`, and `DELETE /holdings/{id}` to `410 Gone` with guidance to use transactions.
- Added a Phase 2 projection unit test.

### Verification

- Passed: `backend/venv/bin/python -m compileall backend/app`
- Passed: `backend/venv/bin/python backend/tests/test_phase2_projection.py`
- Passed: `backend/venv/bin/python -m pytest backend/tests/test_api.py backend/tests/test_phase1_services.py backend/tests/test_phase2_projection.py -q`
  - Result: `2 passed, 8 skipped, 5 warnings`

## Phase 3 - Schema Drift Reconciliation

Status: Complete

### Target

- Align migrations with the application contract used by the current routers/services.
- Make transaction and holdings schema compatible with account-less flows.
- Document the intended schema boundary.

### Completed

- Added `021_accountless_transactions_holdings.sql`.
- Added `transactions.currency` alignment for explicit currency handling.
- Made `transactions.account_id` and `holdings.account_id` nullable for the account-less app flow.
- Added/verified `holdings.user_id`, `holdings.currency`, and `holdings.total_cost_twd`.
- Dropped the old blanket holdings write-blocking trigger so backend projection writes can work.
- Added `holdings_user_symbol_key UNIQUE (user_id, symbol)` to match Python upsert.
- Updated `backend/migrations/README.md`.
- Added a Phase 3 migration contract test.

### Verification

- Passed: `backend/venv/bin/python -m compileall backend/app`
- Passed: `backend/venv/bin/python backend/tests/test_phase3_migration.py`
- Passed: `backend/venv/bin/python -m pytest backend/tests/test_api.py backend/tests/test_phase1_services.py backend/tests/test_phase2_projection.py backend/tests/test_phase3_migration.py -q`
  - Result: `3 passed, 8 skipped, 5 warnings`

## Phase 4 - Frontend API and TypeScript Cleanup

Status: Complete

### Target

- Keep RTK Query as the only active API client.
- Remove stale JS/JSX duplicates.
- Remove hard-coded backend URLs.
- Remove direct holdings mutation UI/hooks.

### Completed

- Updated Vite entry from `src/main.jsx` to `src/main.tsx`.
- Removed duplicate ThemeProvider wrapping from `main.tsx`.
- Removed stale JSX/JS API files:
  - `src/main.jsx`
  - `src/components/AddTransactionForm.jsx`
  - `src/components/Header.jsx`
  - `src/components/ThemeToggle.jsx`
  - `src/context/ThemeContext.jsx`
  - `src/utils/api.js`
  - `src/utils/api.ts`
- Removed stale conflict artifacts:
  - `src/store/apiSlice.ts.orig`
  - `src/store/apiSlice.ts.rej`
- Removed direct holdings mutation endpoints/hooks from RTK Query.
- Removed holdings mutation hook usage from `DashboardPage.tsx`.
- Replaced hard-coded `http://localhost:8000/portfolio/summary` with `/api/portfolio/summary`.
- Added a TypeScript frontend smoke test.
- Updated Vitest include pattern to include TS/TSX tests.
- Removed stale `@testing-library/react` dependency from test setup.

### Verification

- Passed: `npm run build`
  - Warning remains: generated JS chunk is larger than 500 kB.
- Passed: `npm test -- --run`
  - Result: `1 passed`

## Phase 5 - Settings and Security Hardening

Status: Complete

### Target

- Remove hard-coded production-like secrets/default DB credentials.
- Restrict CORS by configuration.
- Protect admin routes with authentication.
- Disable background schedulers in tests.

### Completed

- Replaced hard-coded LAN database URL with a local development default.
- Replaced hard-coded generic secret with an explicit development default.
- Added production validation that rejects the default secret.
- Added `ENVIRONMENT`, `CORS_ORIGINS`, and `ENABLE_PRICE_SCHEDULER` settings.
- Replaced wildcard CORS with configured origins.
- Disabled the price scheduler by default; it now starts only when `ENABLE_PRICE_SCHEDULER=true`.
- Protected all `/admin/*` routes with `Depends(get_current_user)`.
- Added Phase 5 config/security tests.

### Verification

- Passed: `backend/venv/bin/python -m compileall backend/app`
- Passed: `backend/venv/bin/python backend/tests/test_phase5_config.py`
- Passed: `backend/venv/bin/python -m pytest backend/tests/test_api.py backend/tests/test_phase1_services.py backend/tests/test_phase2_projection.py backend/tests/test_phase3_migration.py backend/tests/test_phase5_config.py -q`
  - Result: `7 passed, 8 skipped, 4 warnings`

## Phase 6 - SQLite Runtime Architecture

Status: Complete

### Target

- Make SQLite the default local/runtime database.
- Keep active FastAPI routes compatible with SQLite while preserving PostgreSQL fallback support.
- Avoid working-directory-dependent database files.
- Verify transaction writes, holdings projection, portfolio summary, and admin endpoints against SQLite.

### Completed

- Changed default `DATABASE_URL` to `sqlite:///./wealth.db`.
- Updated `backend/.env` for SQLite local runtime and disabled the price scheduler by default.
- Added a SQLite/PostgreSQL adapter in `backend/app/database.py`.
- Added backend-relative SQLite path resolution so `sqlite:///./wealth.db` consistently maps to `backend/wealth.db`.
- Added SQLite schema auto-initialization for active app tables:
  - `users`
  - `accounts`
  - `transactions`
  - `holdings`
  - `portfolio_snapshots`
  - `currency_cache`
  - `audit_log`
  - `price_history_tw`
  - `price_history_us`
  - `stock_info`
- Added SQLite-compatible SQL normalization for the active `%s` placeholder style and common PostgreSQL-only expressions.
- Updated active transaction/admin/audit/action-log paths away from direct PostgreSQL-only calls.
- Moved transaction audit logging outside the main transaction commit path to avoid SQLite `database is locked` errors.
- Added `/admin/version` support for the frontend admin status call.
- Added SQLite path/adapter tests.

### Manual SQLite API Verification

- Started backend with `venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- Started frontend dev server with `npm run dev`; Vite selected `http://localhost:3001/` because port 3000 was already in use.
- Confirmed Vite returns `200 OK` for LAN/Tailscale host headers after `allowedHosts: true`.
- Confirmed frontend proxy `GET /api/health` returns `{"status":"ok"}`.
- Passed: `POST /auth/register`
- Passed: `POST /auth/login`
- Passed: `POST /transactions`
- Passed: `GET /holdings`
- Passed: `GET /portfolio/summary`
- Passed: `GET /admin/version`
- Confirmed no `database is locked` error after moving audit logging outside the active transaction.

### Verification

- Passed: `backend/venv/bin/python -m compileall backend/app`
- Passed: `backend/venv/bin/python -m pytest backend/tests/test_api.py backend/tests/test_phase1_services.py backend/tests/test_phase2_projection.py backend/tests/test_phase3_migration.py backend/tests/test_phase5_config.py backend/tests/test_sqlite_database.py -q`
  - Result: `9 passed, 8 skipped, 4 warnings`
- Passed: `npm test -- --run`
  - Result: `1 passed`
- Passed: `npm run build`
  - Warning remains: generated JS chunk is larger than 500 kB.

### Remaining SQLite Follow-Up

- Legacy scraper/backfill modules still contain direct `psycopg2.connect()` calls and should be converted before enabling those background jobs in SQLite mode.
- `backend/app/services/transaction_service.py` is currently not exported or used by active routers, but it still contains PostgreSQL-specific code and should be removed or rewritten in a cleanup phase.
- Existing generated database files outside the canonical `backend/wealth.db` should be reviewed before deletion.

## Final Verification

Status: Complete

### Backend

- Passed: `backend/venv/bin/python -m compileall backend/app`
- Passed: `backend/venv/bin/python -m pytest backend/tests/test_api.py backend/tests/test_phase1_services.py backend/tests/test_phase2_projection.py backend/tests/test_phase3_migration.py backend/tests/test_phase5_config.py backend/tests/test_sqlite_database.py -q`
  - Result: `9 passed, 8 skipped, 4 warnings`
  - Skipped tests are gated integration tests:
    - `RUN_ASGI_TESTS=1`
    - `RUN_DB_TESTS=1`
    - `RUN_NETWORK_TESTS=1`

### Frontend

- Passed: `npm test -- --run`
  - Result: `1 passed`
- Passed: `npm run build`
  - Warning remains: generated JS chunk is larger than 500 kB.

## Phase 7 - Holdings and P/L UX Expansion

Status: Planned

### Target

- Keep holdings strictly read-only and make the UI state that positions are "automatically derived from transactions".
- Make currency and price provenance explicit so users can tell when a quote is live, estimated, or missing.
- Unify portfolio views around TWD while still preserving original-currency context where it matters.
- Add higher-level views for allocation, grouping, and symbol-level drill-downs without weakening the transaction-as-source-of-truth model.

### Recommended Implementation Order

1. UI clarity for the existing holdings table
   - Add a visible label that holdings are computed from transactions.
   - Show `price_source` and a `price missing` state when live price fetch fails.
   - Keep original-currency values visible, but add TWD columns for cost, market value, and unrealized gain.

2. Holdings grouping and allocation summaries
   - Group holdings by Taiwan stocks, US stocks, ETFs, cash, and other.
   - Add allocation charts by market, currency, industry, and instrument type.
   - Reuse `currency`, `exchange`, and symbol metadata already present in computed holdings where possible.

3. Symbol detail view
   - Add a single-symbol detail page with transaction history, average-cost changes, and P/L trend.
   - Reuse transaction and holdings projection data rather than introducing a second source of truth.

4. Income and cost modeling
   - Add dividend / distribution records.
   - Add fee, transaction tax, and FX fee breakdowns to the cost model.
   - Keep realized and unrealized P/L calculations aligned with the same currency conversion rules.

### Notes

- The backend already exposes a good part of the required shape for step 1:
  - `HoldingService` returns `currency`, `exchange`, and `price_source`.
  - `HoldingService` and `PortfolioService` already compute TWD-converted values.
- The current frontend still hides some of that information, so the first win is mostly presentation and copy, not a database redesign.
- Deeper features such as dividends, fee allocation, and allocation charts will likely need new API endpoints and/or a small set of new tables or aggregates.

## Change Log

日期：2026-06-20

修改內容：
- 新增：`/admin/scraper/status` 真實 runtime 狀態、`/admin/scraper/runs` 執行紀錄、`/admin/scraper/trigger` 手動觸發、`/admin/scraper/missing-data` 缺資料報告、`/admin/scraper/scheduler` 開關。
- 修改：排程器改成回寫 audit log 與 runtime registry，並把 `PriceCollectorService` 交給單一 singleton 管理。
- 修改：價格抓取加入 retry / timeout / error classification，`_alert_no_data` 改為 `scrape` 類型。
- 修改：`transactions` 新增後自動觸發 history backfill，舊的 backfill 腳本改為 `get_db()` 相容。
- 修改：Admin 頁新增排程開關、手動觸發、執行紀錄與缺資料掃描區塊。

修改原因：
- 讓管理頁顯示真實 runtime 狀態，不再依賴 mock。
- 讓排程與回填流程能被觀測、可手動補救，並降低 SQLite / PostgreSQL 雙軌不一致風險。

影響範圍：
- `backend/app/scrapers/price_scheduler.py`
- `backend/app/routers/admin.py`
- `backend/app/routers/transactions.py`
- `backend/app/services/transaction_service.py`
- `backend/backfill_prices.py`
- `frontend/src/pages/AdminPage.tsx`
- `frontend/src/store/apiSlice.ts`
- `frontend/src/types/index.ts`

風險與回滾方式：
- 風險：排程器與抓價回補流程變成新 runtime 路徑，若 yfinance 或 APScheduler 行為不符預期，可能影響背景作業。
- 回滾：先停用 `ENABLE_PRICE_SCHEDULER`，再回退上述變更檔案到前一版；前端可先維持舊 Admin 頁不操作新功能。

下一步：
- 執行後端與前端的編譯/測試確認，補齊任何欄位或型別差異。
- 如要長期保留執行紀錄，下一輪可把 scrape run summary 從 audit_log 進一步抽成專門表。

## Change Log

日期：2026-06-29

修改內容：
- 新增：交易資料模型與匯入流程新增 `asset_class`，用來獨立描述股票、債券、貴金屬、現金、其他。
- 修改：持倉頁的配置摘要改為以 `asset_class` 為主，不再同時以市場與幣別重複呈現。
- 修改：目標配置與偏離提醒先停用，改成只顯示目前資產配置占比。
- 刪除：無

修改原因：
- 交易策略分類與資產配置分類原本混在一起，導致持倉頁的市場/幣別/類型資訊高度重複，且再平衡邏輯缺乏一致基礎。

影響範圍：
- `backend/app/models.py`
- `backend/app/database.py`
- `backend/app/routers/transactions.py`
- `backend/app/routers/admin.py`
- `backend/migrations/023_transactions_asset_class.sql`
- `backend/tests/test_phase4_transactions.py`
- `frontend/src/types/index.ts`
- `frontend/src/hooks/useDashboardState.ts`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/components/AddTransactionForm.tsx`
- `frontend/src/components/dashboard/HoldingsSection.tsx`
- `frontend/src/components/dashboard/TransactionsSection.tsx`
- `frontend/src/components/dashboard/shared.ts`

風險與回滾方式：
- 風險：既有交易若尚未補上 `asset_class`，持倉頁會先依既有 symbol/exchange 規則推估，少數 ETF 或特殊商品可能暫時落在較粗略的分類。
- 回滾：回退上述檔案與 migration，或先保留欄位但恢復 `HoldingsSection` 的舊分組邏輯。

下一步：
- 補一輪既有交易的 `asset_class` 整理規則，再討論要不要恢復目標配置與偏離提醒。

## Change Log

日期：2026-06-29

修改內容：
- 新增：交易資料模型新增 `sector`，採用「股票個股產業 + ETF 類型標籤」混合模型。
- 新增：`backend/scripts/sector_symbol_map.py` 作為後續 sector 對照表基礎。
- 修改：交易新增 / 編輯表單可設定 `sector`，並限制只有 `asset_class=equity` 時可填。
- 修改：CSV / Excel 匯入、交易 API、Admin 匯出、交易列表 badge 均支援 `sector`。
- 刪除：無

修改原因：
- 單靠 `asset_class` 不足以表達股票內部的產業曝險，但 ETF 又不適合被硬塞進傳統單一產業，因此需要一層可兼容個股與 ETF 策略型態的 `sector`。

影響範圍：
- `backend/app/models.py`
- `backend/app/database.py`
- `backend/app/routers/transactions.py`
- `backend/app/routers/admin.py`
- `backend/migrations/024_transactions_sector.sql`
- `backend/tests/test_phase4_transactions.py`
- `frontend/src/types/index.ts`
- `frontend/src/components/AddTransactionForm.tsx`
- `frontend/src/components/dashboard/shared.ts`
- `frontend/src/components/dashboard/TransactionsSection.tsx`
- `backend/scripts/sector_symbol_map.py`

風險與回滾方式：
- 風險：ETF 的 `sector` 不是傳統產業，而是 `broad_market / high_dividend / thematic` 這類策略標籤；若後續圖表把它當成純產業解讀，會造成語意混淆。
- 回滾：保留欄位但停止前端編輯與顯示；或回退上述檔案與 migration，將 `sector` 視為未啟用欄位。

下一步：
- 補一份你實際持有標的的 sector 對照表，再決定是否要做批次回填或 sector 配置視圖。

## Change Log

日期：2026-06-29

修改內容：
- 新增：`stock_info` 資料表納入 SQLite / PostgreSQL runtime schema，作為 `symbol -> exchange` 的資料庫主規則。
- 新增：`backend/app/services/market_service.py`，統一管理 `TWSE / OTC / US` 判斷、歷史表、Yahoo symbol 與來源規則。
- 修改：交易新增 / 匯入時會同步 upsert `stock_info.exchange`，不再只靠 `symbol.isdigit()` 推斷市場。
- 修改：即時價格與歷史回填改為優先讀取 `stock_info.exchange`，並將來源明確寫成 `yfinance_twse / yfinance_tpex / yfinance_us`。
- 修改：`PriceService` 快取改為 5 分鐘 TTL，避免持倉頁長時間顯示舊報價。
- 刪除：無

修改原因：
- 將上市、上櫃與美股的市場判斷移入資料庫，避免即時價、歷史價、排程與缺資料報告各自維護一套不一致的規則。

影響範圍：
- `backend/app/database.py`
- `backend/app/services/market_service.py`
- `backend/app/services/price_service.py`
- `backend/app/scrapers/price_collector.py`
- `backend/app/routers/transactions.py`
- `backend/app/services/transaction_service.py`

風險與回滾方式：
- 風險：既有歷史資料中舊的 `source='TW' / 'US'` 仍會存在於未重寫的舊日期列，只有新寫入或被覆寫的資料會帶入新規則來源值。
- 回滾：回退上述檔案，或保留 `stock_info` 但讓價格服務恢復原本的 symbol 規則判斷。

下一步：
- 重啟目前實際執行的 backend process，讓 live API 載入新的 `stock_info` 與市場規則。
- 針對 `00631` 補查正確市場與可用來源，決定是修正代號、補白名單，或標記為無法抓取。

## Change Log

日期：2026-06-29

修改內容：
- 新增：`backend/tests/test_scheduler_utils.py` 新增 backfill 起始日規則測試，覆蓋最早 BUY、最早交易日、5 年 fallback。
- 修改：`backend/app/services/transaction_service.py` 新增共用 `get_symbol_backfill_start_date()`，統一回補起始日規則。
- 修改：`backend/app/services/transaction_service.py` 的 `auto_backfill_symbol()` 改為從最早 BUY 日期開始補歷史價。
- 修改：`backend/app/scrapers/price_scheduler.py` 的缺口補價與新股票自動 backfill 改為共用同一條起始日規則。
- 修改：`CHANGELOG.md` 補充本次 scraper backfill 規則修正。
- 刪除：無

修改原因：
- 先前不同爬蟲路徑分別使用 1990 年、最近 1 年、最早交易日，導致新標的歷史價格補齊範圍不一致，與「從購入日開始回補」的需求不符。

影響範圍：
- `backend/app/services/transaction_service.py`
- `backend/app/scrapers/price_scheduler.py`
- `backend/tests/test_scheduler_utils.py`
- `CHANGELOG.md`

下一步：
- 重啟後端後手動觸發一次 `all_holdings` 與 `backfill_gaps`，確認新增標的與缺口回補都從正確購入日開始執行。

## Change Log

日期：2026-06-29

修改內容：
- 新增：`MarketService.SYMBOL_ALIASES`，先納入 `00631 -> 00631L` 的台股代號正規化規則。
- 修改：`backend/app/services/market_service.py` 支援台股尾碼代號判斷，並修正上櫃代號來源為 `twstock.tpex` fallback。
- 修改：`backend/app/routers/transactions.py`、`backend/app/services/transaction_service.py`、`backend/app/scrapers/price_collector.py` 改為全程使用正規化後的 symbol。
- 修改：將 SQLite 既有交易、持倉、`stock_info`、`audit_log` 中的 `00631` 改為 `00631L`，並重建持倉與歷史價格。
- 修改：重啟 `wealth-backend.service`，讓 live backend 載入新規則。
- 刪除：無

修改原因：
- `00631` 實際應為 `00631L`。若只修交易資料、不修 symbol 正規化與 price write path，後續仍可能再次把錯代號寫回資料庫或誤判為美股。

影響範圍：
- `backend/app/services/market_service.py`
- `backend/app/routers/transactions.py`
- `backend/app/services/transaction_service.py`
- `backend/app/scrapers/price_collector.py`
- `backend/tests/test_scheduler_utils.py`
- `backend/wealth.db`
- `CHANGELOG.md`

風險與回滾方式：
- 風險：目前 alias 表僅包含已確認的 `00631 -> 00631L`；若未來還有其他台股尾碼代號輸入錯誤，仍需逐筆確認後再加入規則，避免過度自動修正。
- 回滾：將資料庫中的 `00631L` 改回 `00631`，回退上述檔案中的 alias 與 symbol normalization 變更，並重啟 backend。

下一步：
- 在 Admin 頁補上 symbol alias / 手動修正工具，避免同類代號錯誤只能靠直接改 DB。

## Change Log

日期：2026-06-29

修改內容：
- 新增：`backend/app/services/market_service.py` 加入官方清單驅動的 suffix alias 規則，對唯一尾碼代號自動正規化，對歧義尾碼保持原值不猜測。
- 新增：`backend/tests/test_scheduler_utils.py` 補上 exact symbol、unique suffix alias、ambiguous suffix 三類測試。
- 修改：重新掃描現有交易、持倉、`stock_info`、歷史價格的 symbol 正規化狀態，確認目前資料已與新規則一致。
- 修改：對所有已追蹤標的執行一次從首次 `BUY` 日期開始的全量歷史價格回補。
- 修改：重啟 `wealth-backend.service`，讓 live backend 載入通用 suffix normalization 規則。
- 刪除：無

修改原因：
- 僅靠手工 alias 無法覆蓋其他台股尾碼商品；需要把尾碼正規化提升為可維護、可驗證、且避免誤判的通用規則。

影響範圍：
- `backend/app/services/market_service.py`
- `backend/tests/test_scheduler_utils.py`
- `backend/wealth.db`
- `CHANGELOG.md`

風險與回滾方式：
- 風險：官方清單中的 unique suffix base 會被自動補尾碼；若未來有少數商品需要保留非 canonical 輸入格式，需另外加白名單或關閉該 alias。
- 回滾：回退 `market_service.py` 與測試變更，必要時依交易紀錄把個別 symbol 改回舊值，然後重啟 backend。

下一步：
- 在交易新增與匯入流程增加「symbol 已自動正規化」提示，讓使用者知道輸入值是否被補尾碼。

## Change Log

日期：2026-06-29

修改內容：
- 新增：交易匯入區塊補充台股尾碼自動正規化說明。
- 修改：`frontend/src/components/AddTransactionForm.tsx` 成功通知改為根據後端實際回傳 symbol 顯示是否發生自動正規化。
- 修改：更新 `CHANGELOG.md` 記錄本次前端提示調整。
- 刪除：無

修改原因：
- 尾碼正規化如果只發生在後端寫入，使用者看不到輸入值被補尾碼，容易誤解系統自動改寫了資料；前端需要把這件事明講。

影響範圍：
- `frontend/src/components/AddTransactionForm.tsx`
- `CHANGELOG.md`

下一步：
- 若要更進一步，可在送出前就加一個即時「預計正規化結果」提示，而不是等成功後才顯示。
