# 一次性腳本歸檔

這些是一次性使用的資料庫修補 / backfill 腳本，**不需要也不應該加入 cron 排程**。

---

## fix_snapshot.py

用於修正 `portfolio_snapshots` 表中的錯誤資料。

**何時使用：**
- 發現快照計算邏輯有誤，需要重新計算並寫入
- 手動修補特定日期的總資產值

**執行方式：**
```bash
cd /home/lewis/wealth/backend
python fix_snapshot.py
```

---

## backfill_db.py

用於一次性建立投資組合快照歷史（從 2026-03-09 起的每日記錄）。

**何時使用：**
- 系統初期導入時，一次性補填歷史快照
- 已有一籃子標的（GLD、00887）的歷史價格，用假設的持股數計算總值

**執行方式：**
```bash
cd /home/lewis/wealth/backend
python backfill_db.py
```

**注意：** 此腳本使用硬編碼的持股數量（GLD=33/50 股、00887=20000 股）和固定 FX 匯率（33.0），僅適用於一次性資料初始化。

---

## backfill_history.py

透過 API 介面逐一建立快照記錄（HTTP POST `/portfolio/snapshot`）。

**何時使用：**
- 需要透過 REST API 注入資料，而非直接寫入資料庫
- 驗證 API 層的 snapshot 寫入邏輯

**執行方式：**
```bash
cd /home/lewis/wealth/backend
python backfill_history.py
```

**注意：** 包含硬編碼的登入憑證（`bananawen`）和 API URL（`http://localhost:8000`），**嚴禁用於生產環境**。

---

## app/scrapers/backfill_lewis.py

Lewis 個人使用的歷史股價補填腳本，針對特定標的（GLD、VOO、QQQ、AAPL、00887、0050）從 1990 年補到現在。

**何時使用：**
- 為 Lewis 的實際持倉補全歷史價格資料
- 使用 yfinance（美股）和 twstock（台股）兩種來源

**執行方式：**
```bash
cd /home/lewis/wealth/backend
python -m app.scrapers.backfill_lewis
```

**注意：** 這是 `app/scrapers/` 目錄下的腳本，不是根目錄，但它也是一次性使用（已由 scheduler 接管日常爬蟲）。

---

## app/scrapers/backfill.py

通用歷史資料補填腳本，可選擇標的列表與起始年份。

**何時使用：**
- 初始導入新標的（如 AAPL、VOO 等）時一次性補歷史
- 之後由 scheduler 的 `--full` 模式接管日常爬蟲

**執行方式：**
```bash
cd /home/lewis/wealth/backend
python -m app.scrapers.backfill
```

**注意：** 目前 `upsert_records` 已有實作（寫入 DB），並非只是 fetch 不寫入。

---

## asset_class_backfill.py

用於一次性補齊 `transactions.asset_class` 缺值，將既有交易分到 `股票 / 債券 / 貴金屬 / 現金 / 其他`。

**何時使用：**
- 已經新增 `asset_class` 欄位，但舊交易資料尚未補值
- 想先用保守規則做預覽，再決定是否實際寫入

**執行方式：**
```bash
cd /home/lewis/wealth/backend
venv/bin/python scripts/asset_class_backfill.py
venv/bin/python scripts/asset_class_backfill.py --apply
```

**注意：**
- 預設是 dry-run，只會列出預計回填結果，不會寫入資料庫。
- 規則偏保守：已知分類放在 `scripts/asset_class_symbol_map.py`；不確定的 ETF 或台灣代號先歸 `other`，避免誤判。

---

## sector_backfill.py

用於一次性補齊 `transactions.sector` 缺值，採用「股票個股產業 + ETF 類型標籤」的保守回填規則。

**何時使用：**
- 已經新增 `sector` 欄位，但舊交易資料尚未補值
- 想只補高把握標的，其餘先保留空白

**執行方式：**
```bash
cd /home/lewis/wealth/backend
venv/bin/python scripts/sector_backfill.py
venv/bin/python scripts/sector_backfill.py --apply
```

**注意：**
- 預設是 dry-run，只會列出預計回填結果，不會寫入資料庫。
- 規則對照表在 `scripts/sector_symbol_map.py`。
- 非 `equity` 的交易不會補 sector；不確定的台灣 ETF 也會先保留空白，不強制塞 `other`。
