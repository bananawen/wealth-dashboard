# 個人財富管理網站 數據正確性稽核報告

> **稽核日期：**2026-06-06  
> **稽核對象：** `/home/lewis/wealth`（FastAPI + React + PostgreSQL）  
> **稽核帳號：** bananawen（user_id = 5）  
> **稽核方式：** 靜態程式碼審查 + 資料庫直接查詢 + API 呼叫驗證（未修改任何檔案）

---

## 摘要

Lewis 回報的三個現象，根因全部定位完畢。

| 現象 | 畫面顯示 |正確值 | 根因 |
|------|---------|--------|------|
| 總市值 | **NT$353,012** | **NT$967,184** | 前端取 `total_value`（混幣）而非 `total_value_twd` |
| 未實現損益 | **NT$-2,845** | **NT$-91,032** | 前端取 `unrealized_gain`（混幣）而非 `unrealized_gain_twd` |
| 各卡片數字不同步 | 卡片 vs 持倉表 | — | summary / computed 兩端點各自獨立抓 yfinance 報價，結果不一致 |

**核心問題只有一個：跨幣別的數字未換匯就直接相加或顯示。**

---

## 1. 資料庫現況（user_id = 5）

```sql
-- holdings
00887: account_id=4, shares=20000, avg_cost=16.66, total_cost=333,200, currency='TWD'
GLD  : account_id=5, shares=50,   avg_cost=453.13, total_cost=22,656.74, currency='USD'

-- currency_cache（實際查詢結果：空！沒有任何 rows）
-- → 後端所有 USD→TWD 匯率全部走 hardcoded default 32.0

-- accounts
id=4: 台新證券—台股,   currency='TWD'
id=5: 台新證券—複委託, currency='USD'
id=6: 凱基證券—台股,   currency='TWD'
```

---

## 2. StatCard 數據流向圖

```
PostgreSQL holdings (user_id=5)
 00887: TWD, cost=333,200
  GLD  : USD, cost=22,656.74
            │
            ▼
┌─────────────────────────────────────────────────────────┐
│  GET /portfolio/summary  (portfolio.py)               │
│  各 holding 各自呼叫 yfinance 抓即時價 │
│  ┌──────────────────────────────────────────────────┐ │
│  │ 00887 → get_otc_price("00887.OB") → 0 → 退回均價  │ │
│  │ GLD   → get_price_and_day_change("GLD") → 396.24  │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│  total_value      += mv           (USD當 TWD 直接加) ❌│
│  total_cost       += tc (USD 當 TWD 直接加) ❌│
│  total_value_twd  += mv * fx_rate  (有換匯)            ✅│
│  total_cost_twd   += tc * fx_rate  (有換匯)            ✅│
│  unrealized_gain  = total_value - total_cost           ❌│
│  unrealized_gain_twd = unrealized_gain * usd_rate     ❌ (Bug-4)│
└────────────┬────────────────────────────────────────────┘
             │ RTK Query: useGetPortfolioSummaryQuery
             ▼
┌─────────────────────────────────────────────────────────┐
│  DashboardPage.tsx:252-259 StatCards │
│                                                         │
│  總市值   → formatTWD(summary.total_value)      ❌     │
│          → formatTWD(summary.total_value_twd)  ✅ │
│  未實現   → formatTWD(summary.unrealized_gain)  ❌     │
│          → formatTWD(summary.unrealized_gain_twd)✅    │
│  已實現   → formatTWD(summary.realized_gain)    ⚠️     │
│  XIRR     → summary.annualized_return ❌     │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 各 StatCard 數據來源與計算公式

### 3-1. 總市值卡片

**前端：** `DashboardPage.tsx:254`
```tsx
<StatCard label="總市值" value={formatTWD(summary.total_value)} sub={`成本 ${formatTWD(summary.total_cost)}`} />
```

**實際餵給前端的值（API 回應）：**
```json
{
  "total_value":     353012.00,   // ❌ 混幣：333,200(TWD) + 19,812(USD當TWD)
  "total_value_twd": 967183.98,   // ✅ 正確台幣總市值
  "total_cost":      355856.74,   // ❌ 混幣
  "total_cost_twd": 1058215.83,   // ✅ 正確台幣成本
}
```

**後端計算邏輯（`portfolio.py:173-179`）：**
```python
for h in holdings_dicts:
    mv = price * shares           # 原幣市值
    mv_twd = mv * fx_rate             # 台幣市值
    tc     = float(h["total_cost"])   # 原幣成本
    tc_twd = tc * fx_rate             # 台幣成本

    total_value     += mv              # ❌ TWD + USD 直接加（USD 被當成1:1 TWD）
    total_cost      += tc              # ❌ 同上
    total_value_twd += mv_twd          # ✅
    total_cost_twd  += tc_twd          # ✅
```

**實際代入（USD→TWD 匯率 hardcoded 32.0）：**
```
00887: mv = 16.66 × 20000 = 333,200 TWD,   fx=1   → mv_twd = 333,200
GLD  : mv = 396.24 × 50    = 19,812 USD,   fx=32  → mv_twd = 633,984

total_value     = 333,200 + 19,812 = 353,012    ❌（USD部位被當成TWD，低估32倍）
total_value_twd = 333,200 + 633,984 = 967,184 ✅
```

**正確公式：**
```
總市值(TWD) = Σ(持股數 × 即時報價 × 該幣別→TWD匯率)
            = 00887_mv_twd + GLD_mv_twd
            = 333,200 + 633,984 = 967,184
```

---

### 3-2. 未實現損益卡片

**前端：** `DashboardPage.tsx:255`
```tsx
<StatCard label="未實現損益" value={formatTWD(summary.unrealized_gain)} sub={formatPct(summary.unrealized_pct)} positive={summary.unrealized_gain >= 0} />
```

**後端算式（`portfolio.py:179, 214`）：**
```python
unrealized_gain     = total_value - total_cost              # line 179：混幣相減 ❌
unrealized_gain_twd = round(unrealized_gain * usd_rate, 2)  # line 214：整包×32 ❌
```

**實際計算：**
```
unrealized_gain     = 353,012 - 355,856.74 = -2,844.74   ❌（只反映 GLD 的美元虧損，被貼 NT$）
unrealized_gain_twd = -2,844.74 × 32 = -91,031.68 ❌（僥倖對，但邏輯錯誤）
```

**為什麼本案「剛好」對：**  
00887 的 `unrealized_gain = 0`（因退回均價，mv = tc），所以 `unrealized_gain ×32` 剛好等於 `GLD未實現 × 32`，等於正確答案。但只要 00887 有真實報價（不等於均價），這個算式就會錯。

**正確公式：**
```
未實現損益(TWD) = total_value_twd - total_cost_twd
               = 967,183.98 - 1,058,215.83 = -91,031.85
```

---

### 3-3. 未實現%卡片

**前端：** 同3-2 的 `sub={formatPct(summary.unrealized_pct)}`

**後端算式（`portfolio.py:180`）：**
```python
unrealized_pct = (unrealized_gain_twd / total_cost_twd * 100) if total_cost_twd > 0 else 0.0
```

這行是對的，但 `unrealized_gain_twd`本身已經是錯的（Bug-4），所以結果跟著錯。

---

### 3-4. 已實現損益卡片

**前端：** `DashboardPage.tsx:256`
```tsx
<StatCard label="已實現損益" value={formatTWD(summary.realized_gain)} positive={summary.realized_gain >= 0} />
```

**後端算式（`portfolio.py:183`）：**
```python
realized_gain = sum(float(s["total_realized"]) for s in sells_dicts)
```
```sql
-- portfolio.py:143-148
SELECT DATE(transaction_date) as sell_date, SUM(realized_gain) as total_realized
FROM transactions WHERE type = 'SELL' AND user_id = %s
GROUP BY DATE(transaction_date)
```

目前無任何 SELL 交易，所以為0 未爆。但 `realized_gain`欄位是 `NUMERIC(18,4)` 的美元/台幣混加值，未來有 SELL 時會錯。

---

### 3-5. XIRR（年化報酬率）卡片

**前端：** `DashboardPage.tsx:257`
```tsx
<StatCard label="XIRR" value={summary.annualized_return != null ? formatPct(summary.annualized_return) : 'N/A'} ... />
```

**後端算式（`portfolio.py:186-204`）：**
```python
# SQL：各日期的淨現金流（未換匯）
SELECT transaction_date,
 SUM(CASE WHEN type='BUY' THEN -quantity*price
 WHEN type='SELL' THEN quantity*price ELSE 0 END) AS cf
FROM transactions WHERE user_id = %s GROUP BY transaction_date

#加上期末 portfolio value（混幣 total_value）
all_cfs.append(total_value)   # ❌ 混幣值當期末現金流
annualized = xirr(all_cfs, all_dates) * 100
```

問題：每筆交易的 `quantity*price` 是原幣金額（GLD 的 BUYs 是 USD），直接混入同一條現金流序列；且期末值用了混幣的 `total_value` 而非 `total_value_twd`。

---

## 4. 各 API 端點 SQL 查詢

### 4-1. `GET /portfolio/summary`

**檔案：** `backend/app/routers/portfolio.py:119-220`

**SQL-1：抓所有 holdings（portfolio.py:128-135）**
```sql
SELECT id, account_id, symbol, shares, avg_cost, total_cost, currency
FROM holdings
WHERE shares > 0 AND user_id = %s
```

**SQL-2：抓已實現損益（portfolio.py:143-148）**
```sql
SELECT DATE(transaction_date) as sell_date, SUM(realized_gain) as total_realized
FROM transactions
WHERE type = 'SELL' AND user_id = %s
GROUP BY DATE(transaction_date)
```

**SQL-3：抓 XIRR 現金流（portfolio.py:186-194）**
```sql
SELECT transaction_date,
 SUM(CASE WHEN type='BUY' THEN -quantity*price
                WHEN type='SELL' THEN quantity*price ELSE 0 END) AS cf
FROM transactions
WHERE user_id = %s
GROUP BY transaction_date
ORDER BY transaction_date
```

**SQL-4：讀匯率（portfolio.py:123-126）**
```sql
SELECT currency, rate_to_twd FROM currency_cache
```
> ⚠️實際查詢結果：`currency_cache` 表是**空的**（0 rows）。後端所有匯率都走到 hardcoded default `32.0`，即使 DB 有值也查不到。

---

### 4-2. `GET /holdings/computed`

**檔案：** `backend/app/routers/holdings.py:198-261`

**SQL-1：抓 holdings（holdings.py:205-210）**
```sql
SELECT id, account_id, symbol, shares, avg_cost, total_cost, currency
FROM holdings
WHERE shares > 0 AND user_id = %s
ORDER BY symbol
```

**SQL-2：讀匯率（holdings.py:186-195，`@lru_cache`）**
```sql
SELECT rate_to_twd FROM currency_cache WHERE currency = %s
```
> ⚠️ 同上，`currency_cache` 是空的。同時這個 FX 查詢有 `@lru_cache(maxsize=8)`（`holdings.py:186`），匯率結果會被快取在程序記憶體中，DB 更新後不會自動刷新。

**FX匯率快取邏輯（holdings.py:219-221）：**
```python
currency_rates = {}
for row in rows:
    curr = d.get("currency", "TWD")
    if curr not in currency_rates:
        currency_rates[curr] = _get_currency_rate(curr)   # 每次重新查 DB
```

---

### 4-3. `GET /holdings`

**檔案：** `backend/app/routers/holdings.py:147-162`

```sql
SELECT id, account_id, symbol, shares, avg_cost, total_cost, currency
FROM holdings
WHERE shares > 0 AND user_id = %s
ORDER BY id
```
純粹回傳 DB 持倉，無報價計算。

---

### 4-4. `GET /transactions`

**檔案：** `backend/app/routers/transactions.py:62-82`

```sql
SELECT id, account_id, symbol, LOWER(type::text) AS type,
       quantity AS shares, price, transaction_date AS date, realized_gain
FROM transactions
WHERE user_id = %s
ORDER BY transaction_date DESC
```

---

## 5. 貨幣混加問題根因分析

### 5-1. 數學上發生了什麼

```
正確做法：各幣別先換匯，再相加
  Σ(原幣金額 × 匯率)
= 333,200(TWD) × 1 + 19,812(USD) × 32
= 333,200 + 633,984
= 967,184 ✅

錯誤做法（current total_value）：
  Σ(原幣金額)
= 333,200 + 19,812
= 353,012 ❌
= 333,200(TWD) + 19,812(USD被當成1:1 TWD)
```

GLD 的19,812 USD 被當成 19,812 TWD，**低估了 32 倍**，導致總市值少了約 NT$614,000。

### 5-2. 為什麼「未實現損益」剛好是 -2,845

```
unrealized_gain = total_value - total_cost
                = 353,012 - 355,856.74
                = -2,844.74
```

00887 部位：`mv = 16.66 × 20000 = 333,200 = tc`，未實現 = **0**（因為退回均價）  
GLD 部位：`mv = 396.24 × 50 = 19,812`，`tc = 22,656.74`，未實現 = **-2,844.74 USD**

所以 -2,845 其實是「**GLD 的美元虧損**」，被前端直接貼上 `NT$` 符號顯示。

**真實台幣未實現損益：**
```
total_value_twd - total_cost_twd
= 967,183.98 - 1,058,215.83
= -91,031.85  (約 NT$-91,032)
```

---

## 6. 發現的具體 Bug（檔案 + 行號）

### 🔴 Bug-1（最關鍵）前端 StatCard 取錯欄位

**檔案：** `frontend/src/pages/DashboardPage.tsx:254-255`

```tsx
// ❌ 現況：取混幣欄位
<StatCard label="總市值"   value={formatTWD(summary.total_value)}      sub={`成本 ${formatTWD(summary.total_cost)}`} />
<StatCard label="未實現損益" value={formatTWD(summary.unrealized_gain)}  sub={formatPct(summary.unrealized_pct)} ... />

// ✅ 應改為：
<StatCard label="總市值"   value={formatTWD(summary.total_value_twd)}    sub={`成本 ${formatTWD(summary.total_cost_twd)}`} />
<StatCard label="未實現損益" value={formatTWD(summary.unrealized_gain_twd)} sub={formatPct(summary.unrealized_pct)} ... />
```

`formatTWD()`（`DashboardPage.tsx:42-48`）僅在數字前加 `NT$` 字樣，**不做任何換匯**，餵錯欄位就直接錯。

---

### 🔴 Bug-2 後端混幣累加（所有彙總欄位的源頭）

**檔案：** `backend/app/routers/portfolio.py:173-179`

```python
for h in holdings_dicts:
    mv = price * shares
    mv_twd = mv * fx_rate
    tc     = float(h["total_cost"])
    tc_twd = tc * fx_rate

    total_value     += mv              # ❌ 混 TWD + USD
    total_cost      += tc              # ❌ 混 TWD + USD
    total_value_twd += mv_twd          # ✅
    total_cost_twd  += tc_twd          # ✅
    day_change      += mv * day_chg / 100 # ❌ 混幣
```

導致 `total_value`、`total_cost`、`unrealized_gain`、`day_change`全部錯誤。

---

### 🔴 Bug-3 `unrealized_gain_twd` 算式錯誤

**檔案：** `backend/app/routers/portfolio.py:214`

```python
unrealized_gain_twd = round(unrealized_gain * usd_rate, 2)
```

**問題：** 正確應為 `total_value_twd - total_cost_twd`。現在是把「含 TWD 部位的混幣未實現」整包乘以美元匯率 32，只有在「非美元部位未實現為 0」時才碰巧對。

本案：00887 未實現 = 0（退回均價），所以 `混幣未實現 × 32 = GLD未實現USD × 32`，數值湊巧等於真實台幣未實現。但邏輯是錯的。

---

### 🟠 Bug-400887 交易所後綴錯誤，永遠抓不到真實報價

**檔案：** `backend/app/routers/holdings.py:12`、`portfolio.py:73`

```python
# holdings.py:12
OTC_STOCKS = {"00887"}    # 把 00887 當上櫃股票

# portfolio.py:73
def is_otc_stock(symbol: str) -> bool:
    return symbol.upper() in ["00887"]   # 同樣 hardcoded
```

**行為鏈：**
```
00887 → is_otc_stock() = True
 → get_otc_price("00887.OB") → Yahoo 回傳空 → (0.0, 0.0)
      → _get_price()收到 price=0, avg_cost=16.66
      → return (16.66, 0.0)  ← 退回均價，day_change=0
```

**實測：** `00887.OB` 在 Yahoo Finance 無資料，`00887.TW` 有資料（但 code 不用 `.TW`）。

**影響：**
- 00887 的市值永遠等於 `成本`，未實現損益恆為 0
- 00887 的日漲跌幅永遠為 0%
- 00887 的「總市值」用的是成本而非市價（偏低或偏高，端視真實價位）

**DB現況：** `stock_info` 表記 `exchange='OTC'`，但 `00887`（SPDR MSCI ACWI ETF）是 TWSE 上市股票，應為 `'TWSE'`。

---

### 🟡 Bug-5 兩端點各自獨立抓 yfinance，報價不同步

**檔案：** `portfolio.py:92` 的 `_get_price` vs `holdings.py:24` 的 `_get_price`

```python
# portfolio.py:92 — _get_price（portfolio 用）
def _get_price(symbol: str, avg_cost: float = 0.0) -> tuple[float, float]:
    if is_otc_stock(symbol):
        price, day_chg = get_otc_price(symbol) # 用 .OB
        ...
    if is_taiwan_stock(symbol):
        price, day_chg = get_twse_price(symbol)    # 用 .TW
        ...

# holdings.py:24 — _get_price（holdings 用，幾乎相同但各自實作）
def _get_price(symbol: str, avg_cost: float = 0.0) -> tuple[float, float, str]:
    if exchange == "TWSE":
        ticker = yf.Ticker(f"{symbol}.TW") # 這裡 00887 也不會被標 TWSE
        ...
    if exchange == "OTC":
        ticker = yf.Ticker(f"{symbol}.OB")
        ...
```

兩份 `_get_price` 是**獨立的各自實作**，同一時間可能對同一股票抓到不同價格。

**實測差異：**
```
GLD in /portfolio/summary → price = 396.24 (真實報價)
GLD in /holdings/computed → price = 453.13 (退回均價，因 holdings.py 的 lru_cache)
```

`holdings.py` 的 `_get_currency_rate` 有 `@lru_cache(maxsize=8)`（`holdings.py:186`），匯率結果被快取在程序記憶體中，和 `portfolio.py` 每次重新查 DB 的行為不一致。

---

### 🟡 Bug-6 XIRR 用混幣現金流

**檔案：** `backend/app/routers/portfolio.py:186-204`

```python
# SQL: quantity*price 未換匯，跨 TWD/USD 直接混入同一序列
all_cfs.append(total_value)   # ❌ 混幣 total_value當期末值
annualized = xirr(all_cfs, all_dates) * 100
```

---

### ⚪ Bug-7 `currency_cache` 表為空

**驗證：** `SELECT * FROM currency_cache` → **0 rows**

後端所有匯率都走到 hardcoded default `32.0`（`portfolio.py:148`、`holdings.py:195`）。

---

### ⚪ Bug-8 已實現損益跨幣別直接加總

**檔案：** `portfolio.py:143-148, 183`

```python
cur.execute("""
    SELECT DATE(transaction_date) as sell_date, SUM(realized_gain) as total_realized
    FROM transactions WHERE type = 'SELL' AND user_id = %s
    GROUP BY DATE(transaction_date)
""", (user_id,))
...
realized_gain = sum(float(s["total_realized"]) for s in sells_dicts)
```

`realized_gain` 是 `NUMERIC(18,4)` 的原幣金額，跨幣別直接 SUM。目前無 SELL 交易所以為 0 未爆。

---

## 7. 修正建議

### 高優先（直接修2 行就能止血）

**Step 1：前端緊急修復（`DashboardPage.tsx:254-255`）**
```tsx
//總市值
value={formatTWD(summary.total_value_twd)}
sub={`成本 ${formatTWD(summary.total_cost_twd)}`}

// 未實現損益
value={formatTWD(summary.unrealized_gain_twd)}
sub={formatPct(summary.unrealized_pct)}
```

⚠️ 但 `unrealized_pct` 仍以 `unrealized_gain_twd`計算，若後端 Bug-3 未修，% 仍會輕微偏差。

---

### 中優先（後端根本修復）

**Step 2：後端 `portfolio.py` 彙總改用台幣欄位（`portfolio.py:179, 214`）**
```python
# unrealized_gain：直接用台幣相減
unrealized_gain = total_value_twd - total_cost_twd   # 取代 total_value - total_cost

# unrealized_gain_twd：直接等於上述
unrealized_gain_twd = round(unrealized_gain, 2) # 取代 unrealized_gain * usd_rate

# day_change：改用台幣累加
day_change += mv_twd * day_chg / 100                  # 取代 mv * day_chg / 100
```

**Step 3：移除前端混幣欄位**  
`PortfolioSummary` 模型仍會回傳 `total_value`、`total_cost`、`unrealized_gain` 等混幣欄位（`models.py:74-85`）。建議在回傳前直接刪除這些欄位，或標注為 `deprecated`。

**Step 4：統一報價服務**  
將 `_get_price` 抽成共用的 service（`backend/app/services/price_service.py`），讓 `portfolio.py` 和 `holdings.py` 共用同一實例，杜絕同一時間拿到不同價格的問題。

**Step 5：移除 `holdings.py` 的 `@lru_cache` FX（`holdings.py:186`）**  
改為和 `portfolio.py` 一樣每次從 DB 讀，確保兩端點使用相同匯率。

---

### 低優先（治本）

**Step 6：修正 00887交易所後綴**
```python
# holdings.py:12 —從 OTC_STOCKS 移除 00887，或改用 stock_info.exchange 動態判斷
OTC_STOCKS = set()   # 不再 hardcode

# portfolio.py:73 — 同上
def is_otc_stock(symbol: str) -> bool:
    return False     # 或動態查 stock_info
```

並將 `stock_info.exchange`從 `'OTC'` 糾正為 `'TWSE'`（00887 是 TWSE 上市 ETF）。

**Step 7：修正 XIRR 現金流（`portfolio.py:186-204`）**
```python
# quantity*price 乘以該帳戶的匯率
all_cfs.append(total_value_twd)   # 期末值用台幣
```

**Step 8：修正已實現損益（`portfolio.py:143-148`）**
依各筆交易的 `account_id` 查出 `currency`，換匯後再加總。

**Step 9：填補 `currency_cache` 表**
```sql
INSERT INTO currency_cache (currency, rate_to_twd, updated_at) VALUES
    ('USD', 32.0, NOW()),
    ('TWD', 1.0, NOW())
ON CONFLICT DO NOTHING;
```

---

## 8. 驗證步驟

### 8-1. 確認後端正在運行
```bash
curl -s http://localhost:8000/docs | head -5  #預期 200
```

### 8-2.簽發 JWT 並呼叫 API
```bash
TOKEN=$(python3 -c "
import jwt, datetime
payload = {'user_id': 5, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}
print(jwt.encode(payload, 'wealth-secret-key-change-in-production', algorithm='HS256'))
")
curl -s http://localhost:8000/portfolio/summary \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**預期（修復後）：**
```json
{
  "total_value":     353012.00,   // 仍為混幣（未來可移除）
  "total_value_twd":  967183.98,   // ✅ 前端應取這個
  "unrealized_gain": -2844.74,     // 仍為混幣
  "unrealized_gain_twd": -91031.85,// ✅ 前端應取這個
 "unrealized_pct":  -8.60,        // 需後端 Bug-2/3 修復後才正確
  "day_change":       -724.04,     // 需後端 Bug-2 修復後才正確
  "day_change_pct":   -0.17 // 需後端 Bug-2 修復後才正確
}
```

### 8-3. 驗證前端卡片（修復後預期）
```
總市值   → NT$967,184 （= total_value_twd）
未實現   → NT$-91,032   （= unrealized_gain_twd）
已實現   → NT$0         （無 SELL 交易）
XIRR     → 有意義的數字（需 Bug-6 修復）
```

### 8-4. 驗證 00887報價（修復後預期）
```python
import yfinance as yf
ticker = yf.Ticker("00887.TW") # 應有資料
hist = ticker.history(period="2d")
print(hist["Close"].iloc[-1])     # 應有真實報價（非16.66）
```

### 8-5. 驗證 currency_cache
```sql
SELECT * FROM currency_cache;  -- 應有 USD, TWD 等 rows
```

---

## 9. 最小修復路徑（總結）

| 順序 | 改哪裡 | 改什麼 | 預期效果 |
|------|--------|--------|---------|
| 1 | `DashboardPage.tsx:254` | `summary.total_value` → `summary.total_value_twd` | 總市值顯示 967,184 |
| 2 | `DashboardPage.tsx:254` | `summary.total_cost` → `summary.total_cost_twd` |成本顯示 1,058,216 |
| 3 | `DashboardPage.tsx:255` | `summary.unrealized_gain` → `summary.unrealized_gain_twd` | 未實現顯示 -91,032 |
| 4 | `portfolio.py:179` | `total_value - total_cost` → `total_value_twd - total_cost_twd` | 後端 API 欄位正確 |
| 5 | `portfolio.py:214` | `unrealized_gain * usd_rate` → `total_value_twd - total_cost_twd` | unrealized_gain_twd邏輯正確 |
| 6 | `holdings.py:12`, `portfolio.py:73` | 移除 00887 的 OTC hardcode | 00887 抓得到真實報價 |
| 7 | `holdings.py:186` | 移除 `@lru_cache` FX |匯率及時更新 |
| 8 | `portfolio.py:173` | `day_change += mv * day_chg / 100` → `mv_twd * day_chg / 100` | 日漲跌正確 |

---

## 附錄：相關檔案與行號速查

|問題 | 檔案:行號 |
|------|----------|
| 前端 StatCard 取錯欄位 | `frontend/src/pages/DashboardPage.tsx:254-255` |
| `formatTWD` 只貼 NT$ 不換匯 | `frontend/src/pages/DashboardPage.tsx:42-48` |
| 後端混幣累加 | `backend/app/routers/portfolio.py:173-179` |
| `unrealized_gain_twd` 錯誤算式 | `backend/app/routers/portfolio.py:214` |
| `day_change` 混幣 | `backend/app/routers/portfolio.py:177` |
| 00887 用 `.OB` 後綴 | `backend/app/routers/holdings.py:12` / `portfolio.py:73` |
| FX `@lru_cache` 不同步 | `backend/app/routers/holdings.py:186` |
| XIRR 混幣現金流 | `backend/app/routers/portfolio.py:186-204` |
| 兩端點各自獨立抓 yfinance | `portfolio.py:92` vs `holdings.py:24` |
| `currency_cache` 表為空 | DB 驗證：0 rows |
| 已實現損益跨幣加總 | `backend/app/routers/portfolio.py:143-148, 183` |
| `PortfolioSummary` 模型 | `backend/app/models.py:74-85` |
| holdings觸發後重算 | `backend/app/routers/transactions.py:93-117` (`_recompute_holdings`) |
