# Single-User Schema Audit - 2026-06-28

## 結論

目前這個網站雖然已明確定位成單一使用者部署，但後端資料結構仍保留一部分早期多使用者設計痕跡；原本的 `accounts` 結構已在 2026-06-28 退出 active schema。

結論分三類：

- 應保留：
  - `users`
  - `users.role`
  - 各主表上的 `user_id`
  - `portfolio_snapshots.user_id`
- 應優先列為後續清理目標：
  - 文件與舊報告中殘留的錯誤資料庫路徑與過時 `user_id` 描述
- 已於 2026-06-28 移除：
  - `stock_info` table（空表，且沒有 active code path 使用）
  - `accounts` table
  - `/accounts` router
  - `transactions.account_id`
  - `holdings.account_id`

## 盤點依據

- 目前 auth / admin 規則：
  - `backend/app/routers/auth.py`
  - `AUTH_MODEL.md`
- 目前交易 / 持倉 /投資組合主流程：
  - `backend/app/routers/transactions.py`
  - `backend/app/routers/holdings.py`
  - `backend/app/routers/portfolio.py`
  - `backend/app/services/*`
- 已改為 accountless schema：
  - `backend/app/scrapers/snapshot.py`

## 保留項目

### 1. `users`

保留原因：

- 即使是單一使用者網站，仍然需要登入、密碼變更、JWT 發放與 owner 權限判斷。
- 目前 owner / test account 的操作仍以 `users` 為基礎。

優點：

- 既有 auth 流程穩定。
- 不需要把認證機制硬改成「只有一組固定帳密」。

缺點：

- 從 schema 角度看，仍然像是可以支援多帳號。

風險：

- 如果只看資料表名稱，維護者可能誤以為這是正式多使用者產品。

替代方案：

- 改成單一固定 owner 設定檔登入。
- 不建議，因為會增加認證與密碼維護風險。

### 2. `users.role`

保留原因：

- 目前 `/admin` 仍需要一個清楚的系統管理 gate。
- owner 帳號與測試帳號的權限差異，需要有最小可用的標記。

優點：

- 可維持 owner / non-owner 邊界。

缺點：

- `admin` 命名容易讓人聯想到多角色產品。

風險：

- 只要文件沒同步，容易被誤讀。

替代方案：

- 把 `role` 改成 `is_owner`。
- 可以考慮，但屬於 schema 變更，這一輪不建議直接做。

### 3. 各主表的 `user_id`

包含：

- `transactions.user_id`
- `holdings.user_id`
- `portfolio_snapshots.user_id`
- `audit_log.user_id`

保留原因：

- 目前交易、持倉、投資組合、快照、Audit Log 全部直接依賴 `user_id` 過濾。
- 雖然網站是單一使用者，但保留 `user_id` 可以讓資料隔離規則保持簡單且一致。

優點：

- 不需要大規模重寫 router / service / query。
- 對現行 SQLite 架構風險最低。

缺點：

- 仍保留多使用者味道。

風險：

- 若硬移除 `user_id`，會影響交易 CRUD、持倉投影、快照、稽核與 admin export。

替代方案：

- 長期可考慮在完全確認只保留一個 owner 帳號後，再逐步移除 `user_id`。
- 但這必須是獨立 phase，不能和一般 UI / bugfix 混做。

## 已完成的 accountless 收斂

- `accounts` table 已從 active SQLite schema 移除。
- `/accounts` router 已從 FastAPI app 移除。
- `transactions.account_id` / `holdings.account_id` 已從 active SQLite schema 移除。
- `frontend/src/store/apiSlice.ts` 中 `/accounts` API 定義已移除。
- `backend/app/scrapers/snapshot.py` 已改成直接使用 `holdings.user_id` 與本地價格表，不再依賴 `accounts`。

## 優先清理目標

### 1. 過時文件與報告

目前看到的風險點：

- `deploy/README.md` 原本寫錯 SQLite 路徑。
- `DATA_AUDIT_REPORT.md`、`TEST_REPORT_2026-06-06.md` 仍有舊 `user_id` 與舊環境描述。

建議：

- 部署與操作文件優先修正。
- 歷史報告可以保留，但要加上「舊環境快照」或「可能已過時」標記。

## 建議 Phase

### Phase 1：已完成

- 修正 canonical SQLite 路徑為 `backend/wealth.db`
- 移除 `accounts` active surface
- 重寫 `snapshot.py` 成為 accountless / SQLite 相容版本

### Phase 2：後續清理

- 檢查 admin export / audit / backfill 是否仍殘留舊 schema 心智模型
- 為 snapshot 與 accountless migration 補更多自動化測試

### Phase 3：長期評估

- 最後才評估 `user_id` 是否值得收斂

優點：

- 可真正降低歷史結構複雜度

缺點：

- 風險最高
- 需要 migration、回滾與完整測試

## 建議結論

若以你的優先順序 `安全性 > 穩定性 > 可維護性` 來看：

- 現在不應直接砍掉 `user_id`
- `accounts` 已經退出 active schema，但 `user_id` 仍應保留
- 下一個最值得動手的技術目標，是清理舊報告 / 舊 migration 說明中的過時描述
