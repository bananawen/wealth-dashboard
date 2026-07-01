# Wealth Dashboard

個人投資管理網站，現況以單一使用者、SQLite、LAN/本機部署為主。

## 結論

- 後端：FastAPI
- 前端：React + Vite
- 資料庫：SQLite
- 架構前提：單一使用者
- 主要用途：交易管理、持倉投影、投資組合績效、價格資料維護、管理後台

目前專案的實際運行狀態，請以 [CURRENT_STATE_RUNBOOK.md](/home/lewis/wealth/CURRENT_STATE_RUNBOOK.md) 為準。

## 技術棧

| 類別 | 技術 |
| --- | --- |
| Frontend | React 18, React Router, Redux Toolkit, Vite, Tailwind CSS |
| Chart | Recharts |
| Backend | FastAPI, Uvicorn, Pydantic |
| Auth | JWT, Passlib |
| Database | SQLite（目前主架構）, 保留部分 PostgreSQL 相容層 |
| Market Data | yfinance, twstock |
| Scheduler | APScheduler |
| Test | pytest, vitest |
| Deployment | systemd, Nginx |

## 主要功能

### 1. 單一使用者登入與系統管理權限

- 第一個註冊帳號會成為 owner
- owner 帳號的 `users.role = 'admin'`
- `admin` 僅代表系統管理權限，不代表多租戶或多人協作模型

相關文件：

- [AUTH_MODEL.md](/home/lewis/wealth/AUTH_MODEL.md)

### 2. 交易管理

- 新增、編輯、刪除交易
- 支援 BUY / SELL
- 自動重算已實現損益
- 支援交易分類、資產類別、產業類別
- 支援匯入交易資料

主要 API：

- `POST /auth/login`
- `GET /transactions`
- `POST /transactions`
- `PUT /transactions/{transaction_id}`
- `DELETE /transactions/{transaction_id}`
- `POST /transactions/import`

### 3. 唯讀持倉投影

- 持倉不允許手動修改
- 所有持倉由交易紀錄自動投影
- 支援原幣 / 台幣金額
- 顯示價格來源、缺價狀態、估算狀態

主要 API：

- `GET /holdings`
- `GET /holdings/computed`

### 4. 投資組合總覽與績效

- 投資組合摘要
- 已實現 / 未實現損益
- XIRR
- 區間績效走勢
- 單一標的損益走勢

主要 API：

- `GET /portfolio/summary`
- `GET /portfolio/performance`
- `GET /portfolio/history`
- `POST /portfolio/snapshot`

### 5. 價格資料與歷史資料

- 台股 / 美股價格歷史查詢
- 最新價格查詢
- 價格缺口檢查
- 針對持有標的自動收集價格資料

主要 API：

- `GET /prices/tw`
- `GET /prices/us`
- `GET /prices/latest`

### 6. 管理後台

- 系統版本資訊
- 資料庫統計
- 系統健康狀態
- 價格來源健康檢查
- 爬蟲執行狀態與最近執行紀錄
- 缺資料報告
- Audit Log 查詢與匯出
- 交易匯出
- SQLite 備份下載

主要 API：

- `GET /admin/version`
- `GET /admin/db/stats`
- `GET /admin/health`
- `GET /admin/scraper/status`
- `POST /admin/scraper/trigger`
- `POST /admin/scraper/scheduler`
- `GET /admin/logs`
- `GET /admin/logs/export.csv`
- `GET /admin/export/transactions.csv`
- `GET /admin/backup/sqlite`

### 7. 內建價格排程與後端維運功能

- 價格收集器跑在 FastAPI process 內
- 可由設定決定啟用或停用
- 可手動觸發單一標的、全部持倉、缺口回補
- 會保留近期執行紀錄與錯誤摘要

說明：

- `ENABLE_PRICE_SCHEDULER=false` 時，後端啟動不會自動啟用排程
- 目前預設是保守模式，避免在不確認資料來源與資源配置時自動執行

## 使用方法

### 環境需求

- Node.js 18+
- Python 3.11+ 建議
- npm
- 已建立的 Python virtual environment：`backend/venv`

### 1. 啟動 Backend

```bash
cd /home/lewis/wealth/backend
venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康檢查：

```bash
curl http://127.0.0.1:8000/health
```

### 2. 啟動 Frontend

```bash
cd /home/lewis/wealth/frontend
npm install
npm run dev
```

### 3. 建置 Frontend

```bash
cd /home/lewis/wealth/frontend
npm run build
```

### 4. 執行測試

Backend：

```bash
cd /home/lewis/wealth
backend/venv/bin/python -m pytest backend/tests/test_sqlite_database.py backend/tests/test_auth_password_rules.py backend/tests/test_phase4_transactions.py backend/tests/test_admin_utils.py -q
```

Frontend：

```bash
cd /home/lewis/wealth/frontend
npm test -- --run
```

### 5. 環境變數

後端設定來源：`backend/app/config.py`

常用變數：

```env
DATABASE_URL=sqlite:///./wealth.db
SECRET_KEY=replace-me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ENABLE_PRICE_SCHEDULER=false
```

## 目前資料表

Active tables：

- `users`
- `transactions`
- `holdings`
- `portfolio_snapshots`
- `currency_cache`
- `audit_log`
- `price_history_tw`
- `price_history_us`

已移除或不再作為主架構使用：

- `accounts`
- `stock_info`
- `transactions.account_id`
- `holdings.account_id`

## 專案結構

```text
wealth/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── scrapers/
│   │   └── database.py
│   ├── tests/
│   └── wealth.db
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── store/
│   └── dist/
├── deploy/
├── AUTH_MODEL.md
├── CURRENT_STATE_RUNBOOK.md
└── CHANGELOG.md
```

## 部署方式

目前專案偏向本機 / LAN 部署：

- Frontend 靜態檔：`frontend/dist`
- Backend：`127.0.0.1:8000`
- 反向代理：Nginx
- 服務管理：systemd

部署細節請看：

- [deploy/README.md](/home/lewis/wealth/deploy/README.md)

## 我建議的事項

以下建議以目前這個專案的現況為前提：單一使用者、SQLite、個人投資管理工具、重視穩定與可追蹤。

### 建議 1：持續維持單一使用者模型

優點：

- 架構清楚
- 權限邏輯簡單
- 維護成本低

缺點：

- 未來若要擴成多人使用，需要重新設計資料隔離

風險：

- 若文件與 UI 沒有持續強調單一使用者，後續維護者可能誤以為這是多人系統

替代方案：

- 保留現在資料表中的 `user_id`，但不在產品層面承諾多使用者能力

### 建議 2：把「交易是來源、持倉是投影」當成長期不變原則

優點：

- 資料真實性高
- 問題排查比較直接
- 不容易出現交易和持倉互相打架

缺點：

- 每次交易異動後要重算相關投影

風險：

- 若之後又偷偷加入持倉手動編輯入口，資料一致性會再次惡化

替代方案：

- 若真的要手動調整，只能做成「校正交易」而不是直接改持倉

### 建議 3：把價格資料狀態做得更明確，而不是只顯示數字

優點：

- 使用者能判斷資料可信度
- 比較符合投資工具需要的風險感知

缺點：

- UI 會稍微多一些狀態欄位

風險：

- 如果只顯示市值、不顯示來源與新鮮度，容易誤判損益

替代方案：

- 最少也要保留 `live / estimated / missing` 三種狀態

### 建議 4：持續收斂文件，讓 README 成為入口

優點：

- 新增維護者或未來自己回頭看時成本較低
- 比較不會被舊文件誤導

缺點：

- 需要持續更新

風險：

- 如果 README 不更新，維護者還是會跑去看過時文件

替代方案：

- README 只放入口與現況，細節統一導到 `CURRENT_STATE_RUNBOOK.md`

### 建議 5：前端繼續做小步整理，不做大改版

優點：

- 風險低
- 比較不會影響已經穩定的功能

缺點：

- 視覺與元件一致性改善速度較慢

風險：

- 若一次做大規模 UI 重寫，很容易把目前已經修好的資料顯示與權限行為一起弄壞

替代方案：

- 以頁面為單位做局部收斂，例如先整理 `/overview`、再整理 `/holdings`

## 補充

- 歷史性文件如 `DATA_AUDIT_REPORT.md`、`TEST_REPORT_2026-06-06.md`、`backend/migrations/README.md` 不應直接當作現況依據。
- 若 README 與實際行為不一致，應優先檢查：
  - `backend/app/main.py`
  - `backend/app/config.py`
  - `CURRENT_STATE_RUNBOOK.md`
