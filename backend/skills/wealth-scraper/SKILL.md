# Wealth Scraper 系統技能

## 排程時刻表（devops-worker profile）

| 時間（Taiwan）| Job | Cron ID | Command |
|--------------|-----|---------|---------|
| 08:00 | US Stock Scraper | `7cfcac16325b` | `cd /home/lewis/wealth/backend && source venv/bin/activate && python -m app.scrapers.scheduler us` |
| 08:30 | Portfolio Snapshot (US) | `a547fb053da6` | `cd /home/lewis/wealth/backend && source venv/bin/activate && python -m app.scrapers.snapshot us` |
| 14:30 | Taiwan Stock Scraper | `35c8826a70c4` | `cd /home/lewis/wealth/backend && source venv/bin/activate && python -m app.scrapers.scheduler tw` |
| 15:00 | Portfolio Snapshot (TW) | `989613772898` | `cd /home/lewis/wealth/backend && source venv/bin/activate && python -m app.scrapers.snapshot tw` |

## 日誌寫入
每次成功都寫入 `audit_log`：
- 爬蟲：`type=SCRAPE`, `level=INFO`
- 快照：`type=db_change`, `level=INFO`
- 失敗：`level=ERROR`

## 資料庫
- Host: 192.168.0.11:5432
- DB: wealth
- Tables: price_history_us (AAPL/GLD/QQQ/VOO), price_history_tw (0050/00887), portfolio_snapshots, holdings, accounts, audit_log
- 歷史記錄數：30,637 筆（1990 起）

## 歷史補爬（已完成）
```bash
python -m app.scrapers.backfill_lewis
```
1990 年起，GLD/VOO/QQQ/AAPL（yfinance）+ 00887/0050（twstock）。

## Snapshot 計算邏輯
`python -m app.scrapers.snapshot` → 從本地 price_history 讀取現價 → 算出總淨值 → 寫入 portfolio_snapshots。
Accounts 無 user_id 欄位，取全部帳戶全部持股。
