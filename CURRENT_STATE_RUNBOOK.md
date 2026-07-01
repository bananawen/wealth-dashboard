# Current-State Runbook

日期：2026-07-01

## 結論

目前 `/home/lewis/wealth` 已收斂為單一使用者、SQLite 為主的部署型專案。

- Active database: `backend/wealth.db`
- Active auth model: first registered owner account has `users.role = 'admin'`
- Active system-management surface: `/admin`
- Active frontend entry: `frontend/dist`
- Active backend entry: `app.main:app`

## 目前架構

### Backend

- Framework: FastAPI
- Main app: `backend/app/main.py`
- Database adapter: `backend/app/database.py`
- Core routers:
  - `auth`
  - `transactions`
  - `holdings`
  - `portfolio`
  - `admin`

### Frontend

- Framework: React + Vite
- Router entry: `frontend/src/App.tsx`
- Shared dashboard shell: `frontend/src/components/DashboardLayout.tsx`
- Admin console: `frontend/src/pages/AdminPage.tsx`

## 單一使用者規則

- 第一個註冊帳號為 owner
- owner 帳號 role = `admin`
- `admin` 僅代表系統管理權限，不代表多租戶角色系統

參考：

- `AUTH_MODEL.md`
- `SINGLE_USER_SCHEMA_AUDIT_2026-06-28.md`

## Active Tables

- `users`
- `transactions`
- `holdings`
- `portfolio_snapshots`
- `currency_cache`
- `audit_log`
- `price_history_tw`
- `price_history_us`

已移除：

- `stock_info`
- `accounts`
- `transactions.account_id`
- `holdings.account_id`

## 日常操作

### 檢查 owner 帳號

```bash
sqlite3 /home/lewis/wealth/backend/wealth.db "select id, username, role, created_at from users order by id;"
```

### 啟動 frontend 開發伺服器

```bash
cd /home/lewis/wealth/frontend
npm run dev
```

### 啟動 backend 開發伺服器

```bash
cd /home/lewis/wealth/backend
venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 執行主要測試

```bash
cd /home/lewis/wealth
backend/venv/bin/python -m pytest backend/tests/test_sqlite_database.py backend/tests/test_auth_password_rules.py backend/tests/test_phase4_transactions.py backend/tests/test_admin_utils.py -q
cd frontend
npm test -- --run
```

## 目前已知注意事項

- `backend/migrations/README.md` 主要是歷史 PostgreSQL / transitional migration 說明
- `DATA_AUDIT_REPORT.md` 與 `TEST_REPORT_2026-06-06.md` 是歷史快照，不應直接視為現況
- frontend bundle 雖已做 route-level lazy loading 與 manual chunks，但仍應持續觀察 build 體積

## 下一步建議

- 持續清理舊報告與舊 migration 說明
- 針對 frontend bundle 再做二次分包與大元件延遲載入
- 若之後不再需要 test helper scripts，可再盤點 `backend/check_*.py` 類檔案是否要保留
