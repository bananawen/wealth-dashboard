# 財富管理網站 數據同步問題稽核報告

> 稽核日期：2026-06-06
> 稽核對象：`/home/lewis/wealth`（FastAPI + React）
> 稽核帳號：bananawen（user_id = 5）
> 稽核方式：靜態程式碼審查 + 實際 API 呼叫驗證（未修改任何檔案）

---

## 1. 問題概覽

Lewis 回報的三個現象，全部已用實際 API 重現並定位到根因。

| 卡片 | 畫面顯示 | 正確值 | 狀態 |
|------|---------|--------|------|
| 總市值 | **NT$353,012** | **NT$967,184** | ❌ 錯誤 |
| 未實現損益 | **NT$-2,845** | **NT$-91,032** | ❌ 錯誤 |
| 各卡片不同步 | 卡片 vs 持倉表對不起來 | — | ❌ 錯誤 |

### 一句話結論

> **核心 bug 只有一個：把不同幣別的數字「直接相加」，沒有換匯。**
> 後端其實「有」算出正確的台幣欄位（`total_value_twd = 967,183.98`），
> 但前端卡片顯示的是「沒換匯的混幣欄位」（`total_value = 353,012`）。

實測 API 回應（`GET /portfolio/summary`，user_id=5）：

```json
{
  "total_value":        353012.0,      // ❌ 前端拿這個 → 混幣亂加（TWD+USD）
  "total_value_twd":    967183.98,     // ✅ 這才是正確的台幣總市值
  "total_cost":         355856.74,     // ❌ 混幣
  "total_cost_twd":     1058215.83,    // ✅ 正確台幣成本
  "unrealized_gain":    -2844.75,      // ❌ 前端拿這個 → 混幣亂減
  "unrealized_gain_twd": -91031.85,    // ✅ 這才是正確的台幣未實現損益
  "unrealized_pct":     -0.8,          // ❌ 混幣分母
  "annualized_return":  -10.8,         // ❌ XIRR 用混幣現金流
  "day_change":         -724.04        // ❌ 混幣
}
```

兩檔持倉（DB 實際資料）：

| 商品 | 股數 | 均價 | 成本(原幣) | 幣別 | 即時價 |
|------|------|------|-----------|------|--------|
| 00887 | 20,000 | 16.66 | 333,200 | TWD | 16.66（抓不到，退回均價）|
| GLD | 50 | 453.13 | 22,656.74 | USD | 396.24（真實價）|

---

## 2. 各卡片數據流向圖

```
                    ┌─────────────────────────────────────────────┐
                    │                PostgreSQL                    │
                    │  holdings(user_id=5)                         │
                    │   00887 / 20000股 / TWD / cost 333,200       │
                    │   GLD   / 50股   / USD / cost 22,656.74      │
                    │  currency_cache: USD→TWD = 32.0              │
                    └───────────────┬──────────────┬──────────────┘
                                    │              │
        ┌───────────────────────────┘              └──────────────────────────┐
        ▼                                                                      ▼
┌──────────────────────────┐                            ┌──────────────────────────────┐
│ GET /portfolio/summary   │                            │ GET /holdings/computed        │
│ portfolio.py             │                            │ holdings.py                   │
│                          │                            │                               │
│ 各 holding 各自抓價      │   ← 兩個端點各自獨立抓價 →  │ 各 holding 各自抓價           │
│ GLD 抓到 396.24 (真實)   │      (沒有共用 cache，      │ GLD 抓到 453.13 (退回均價)    │  ← 不同步點 A
│                          │       結果可能不一致)       │                               │
│ total_value      = TWD+USD 直接加  ❌                  │ 每列各自帶 market_value(原幣) │
│ total_value_twd  = 有換匯 ✅                            │ + market_value_twd(有換匯)    │
│ unrealized_gain  = TWD+USD 直接減  ❌                  │                               │
└────────────┬─────────────┘                            └───────────────┬──────────────┘
             │                                                          │
             ▼ (RTK Query: useGetPortfolioSummaryQuery)                 ▼ (useGetComputedHoldingsQuery)
┌──────────────────────────────────────┐          ┌──────────────────────────────────────┐
│  上方 4 張 StatCard                   │          │  下方「持倉列表」表格                 │
│  DashboardPage.tsx:252-259           │          │  DashboardPage.tsx:343-364            │
│                                      │          │                                       │
│ 總市值 = formatTWD(total_value) ❌   │   ≠      │ 每列用「原幣值」market_value 顯示      │  ← 不同步點 B
│       → NT$353,012 (混幣)            │ 對不起來 │  00887 → NT$333,200                   │
│ 未實現 = total_value(混幣)-...  ❌   │          │  GLD   → US$22,656 (原幣，非台幣)     │
│       → NT$-2,845                     │          │  (上方卡片硬掛 NT$，下方掛 US$)        │
└──────────────────────────────────────┘          └──────────────────────────────────────┘
```

**為什麼「卡片之間 / 卡片 vs 表格」全部對不起來：**

1. **不同步點 A**：`/portfolio/summary` 與 `/holdings/computed` 是**兩個獨立端點、各自打 yfinance**，沒有共用報價。實測同一時間 GLD 在 summary 抓到 396.24、在 computed 退回 453.13 → 兩邊市值天生不一致。
2. **不同步點 B**：上方卡片把混幣總和硬貼 `NT$`，下方表格每列用各自原幣（US$/NT$）顯示，使用者用台幣腦袋去加表格，永遠加不出卡片的數字。

---

## 3. StatCard 計算邏輯（逐卡片）

前端來源：`frontend/src/pages/DashboardPage.tsx:252-259`

```tsx
<StatCard label="總市值"   value={formatTWD(summary.total_value)}      sub={`成本 ${formatTWD(summary.total_cost)}`} />
<StatCard label="未實現損益" value={formatTWD(summary.unrealized_gain)}  sub={formatPct(summary.unrealized_pct)} positive={summary.unrealized_gain >= 0} />
<StatCard label="已實現損益" value={formatTWD(summary.realized_gain)}    positive={summary.realized_gain >= 0} />
<StatCard label="XIRR"      value={... summary.annualized_return ...} />
```

| 卡片 | 用的欄位 | 應該用的欄位 | 問題 |
|------|---------|-------------|------|
| **總市值** | `total_value` (混幣) | `total_value_twd` | ❌ `formatTWD()` 把混幣數字貼上 NT$。333,200(TWD)+19,812(USD) = 353,012，被當成台幣顯示 |
| **未實現損益** | `unrealized_gain` (混幣) | `unrealized_gain_twd` | ❌ 同上，`total_value(混幣) − total_cost(混幣)` = -2,844.75 被當台幣 |
| **未實現 %** | `unrealized_pct` | 用台幣口徑重算 | ❌ 分子分母都是混幣 → -0.8% 無意義 |
| **已實現損益** | `realized_gain` | `realized_gain_twd` | ⚠️ 目前為 0 沒爆，但 `SUM(realized_gain)` 跨幣別直接加，未來會出錯 |
| **XIRR** | `annualized_return` | 用台幣現金流 | ❌ 現金流 `quantity*price` 混 TWD/USD（見 §4） |

`formatTWD()`（DashboardPage.tsx:42）只是無腦在數字前加 `NT$`，**不做任何換匯**，所以餵錯欄位就直接錯。

---

## 4. API → DB 查詢（逐端點）

### 4-1. `GET /portfolio/summary` — `backend/app/routers/portfolio.py:119-220`

逐 holding 累加迴圈（`portfolio.py:160-177`）：

```python
for h in holdings_dicts:
    shares    = float(h["shares"])
    cost_basis= float(h["avg_cost"])
    currency  = h.get("currency", "TWD")
    fx_rate   = _get_currency_rate(currency_cache, currency)   # USD=32, TWD=1

    price, day_chg = _get_price(symbol, cost_basis)
    mv     = price * shares          # 原幣市值
    mv_twd = mv * fx_rate            # 台幣市值 ✅
    tc     = float(h["total_cost"])  # 原幣成本
    tc_twd = tc * fx_rate            # 台幣成本 ✅

    total_value     += mv            # ❌ 把 TWD 和 USD 直接相加
    total_cost      += tc            # ❌ 同上
    total_value_twd += mv_twd        # ✅ 正確
    total_cost_twd  += tc_twd        # ✅ 正確
    day_change      += mv * day_chg / 100   # ❌ 混幣
```

實際代入：

```
00887: mv = 16.66 × 20000 = 333,200 (TWD), fx=1  → mv_twd = 333,200
GLD  : mv = 396.24 × 50   = 19,812   (USD), fx=32 → mv_twd = 633,984

total_value     = 333,200 + 19,812   = 353,012      ❌（混幣）
total_value_twd = 333,200 + 633,984  = 967,184      ✅
```

> ⚠️ 注意：`total_value` 把 19,812 **美元** 當成 19,812 **台幣** 加進去，等於把 GLD 砍成 1/32，所以總市值少了約 NT$614,000。

### 4-2. `GET /holdings/computed` — `backend/app/routers/holdings.py:198-261`

這個端點 **每列都正確**：同時回傳原幣（`market_value`）與台幣（`market_value_twd`）。問題不在這支，而在：

1. **它和 summary 各自打 yfinance**（`holdings.py:24` 的 `_get_price` vs `portfolio.py:92` 的 `_get_price` 是兩份各自實作），報價可能不同步（實測 GLD 一邊 396.24 一邊 453.13）。
2. **FX 匯率用了 process 級 `@lru_cache`**（`holdings.py:186-195`），匯率變動不會更新，和 summary 每次重讀 DB 的行為不一致 → 另一個不同步來源。

### 4-3. XIRR 現金流（`portfolio.py:186-204`）

```sql
SUM(CASE WHEN type='BUY' THEN -quantity*price WHEN type='SELL' THEN quantity*price END) AS cf
```

`quantity*price` 是**原幣**金額，跨 TWD/USD 交易直接混入同一條現金流序列，最後再把混幣的 `total_value` 當期末值丟進 `xirr()` → 算出來的 -10.8% 無意義。

---

## 5. 貨幣混加問題分析

這是本案的**唯一根因**，貫穿所有錯誤卡片。

### 數學上發生什麼

```
正確做法：先各自換成台幣，再相加
   Σ (原幣金額 × 匯率)
   = 333,200×1 + 19,812×32 = 967,184  ✅

錯誤做法（現況 total_value）：先相加，再當台幣
   Σ (原幣金額)
   = 333,200 + 19,812 = 353,012  ❌
   （USD 部位被當成 1:1 台幣，被低估 32 倍）
```

### 為什麼「未實現損益」剛好 -2,845

```
unrealized_gain = total_value - total_cost
                = 353,012 - 355,856.74 = -2,844.75
```

拆開看：
- 00887 部位：mv 333,200 − cost 333,200 = **0**（因為抓不到價，退回均價，見 §6 Bug-3）
- GLD 部位：mv 19,812 − cost 22,656.74 = **-2,844.74**（美元，GLD 現價 396 < 均價 453，確實虧）

所以畫面的 -2,845 其實是「**GLD 的美元虧損**」，卻被貼上 `NT$`。
**真實的台幣未實現損益是 `total_value_twd − total_cost_twd = 967,183.98 − 1,058,215.83 = -91,031.85`，即約 NT$-91,032**（GLD 換算台幣後虧約 9 萬）。

> 補充：後端 `unrealized_gain_twd` 欄位本案「剛好」算對（-91,031.85），但那是巧合 —
> 它的算式是 `unrealized_gain × usd_rate`（`portfolio.py:214`），只因 00887 的未實現為 0，
> 才沒被這個錯誤算式波及。只要 00887 抓得到真實價（不等於均價），這個欄位就會錯（見 Bug-4）。

---

## 6. 發現的 Bug（具體行號）

### 🔴 Bug-1（最關鍵）前端總市值/未實現顯示混幣欄位
**檔案**：`frontend/src/pages/DashboardPage.tsx:254-255`
```tsx
<StatCard label="總市值"   value={formatTWD(summary.total_value)} ... />       // 應為 total_value_twd
<StatCard label="未實現損益" value={formatTWD(summary.unrealized_gain)} ... />  // 應為 unrealized_gain_twd
```
**影響**：總市值 967,184 → 顯示 353,012；未實現 -91,032 → 顯示 -2,845。
**這是 Lewis 看到的兩個錯誤數字的直接來源。**

### 🔴 Bug-2 後端 `total_value` / `total_cost` / `unrealized_gain` 混幣累加
**檔案**：`backend/app/routers/portfolio.py:173-179`
```python
total_value += mv          # 混 TWD + USD
total_cost  += tc          # 混 TWD + USD
...
unrealized_gain = total_value - total_cost   # line 179，混幣相減
```
**影響**：這三個欄位（及 `unrealized_pct`、`day_change`）對多幣別帳戶永遠是錯的。

### 🟠 Bug-3 00887 用錯交易所後綴 `.OB`，永遠抓不到價、退回均價
**檔案**：`backend/app/routers/holdings.py:12`、`portfolio.py:73`
```python
OTC_STOCKS = {"00887"}        # 把 00887 當上櫃
ticker = yf.Ticker(f"{symbol}.OB")   # 用 .OB → Yahoo 查無資料
```
**事實**：00887（永豐美國500大ETF）是**上市(TWSE)**，後綴應為 `.TW`。實測 `00887.OB` 回傳空、退回 `avg_cost`（16.66），導致 00887 的市值＝成本、未實現恆為 0、無漲跌幅。
**影響**：00887 看起來「永遠不賺不賠」，且總市值用的是成本而非市價。

### 🟠 Bug-4 `unrealized_gain_twd` 算式錯誤（本案僥倖正確）
**檔案**：`backend/app/routers/portfolio.py:214`
```python
unrealized_gain_twd = round(unrealized_gain * usd_rate, 2)   # 把混幣數字整包 ×32
```
**問題**：正確應為 `total_value_twd - total_cost_twd`。現在的寫法把（含 TWD 部位的）混幣未實現整包乘以美元匯率，只有在「非美元部位未實現為 0」時才碰巧對。

### 🟡 Bug-5 兩端點各自抓價 / FX 快取不一致 → 卡片與表格對不上
**檔案**：`portfolio.py:92` 的 `_get_price` vs `holdings.py:24` 的 `_get_price`（兩份重複實作）；`holdings.py:186` 的 `@lru_cache` FX。
**影響**：summary 與 computed 在同一刷新可能拿到不同股價/匯率（實測 GLD 396.24 vs 453.13），使「上方總市值」與「下方持倉表加總」天生對不齊。

### 🟡 Bug-6 XIRR 用混幣現金流
**檔案**：`portfolio.py:186-204`
**影響**：`quantity*price` 跨幣別混入同一序列、期末值用混幣 `total_value`，年化報酬率失真。

### ⚪ Bug-7 已實現損益跨幣別直接加總（潛在）
**檔案**：`portfolio.py:143-148, 183`
`SUM(realized_gain)` 不分幣別。目前為 0 未爆，有賣出紀錄後會錯。

---

## 7. 修正建議

> 原則：**所有「跨持倉的彙總」一律以台幣（TWD）為唯一口徑**；原幣值只用於單列顯示。

### 後端（治本，建議優先）

1. **portfolio.py：彙總全部改用台幣欄位**
   - `unrealized_gain`（line 179）改為 `total_value_twd - total_cost_twd`。
   - `unrealized_pct` 改用 `total_*_twd` 計算分子分母。
   - `unrealized_gain_twd`（line 214）直接用 `total_value_twd - total_cost_twd`，不要 `× usd_rate`。
   - `day_change` 改累加 `mv_twd * day_chg / 100`。
   - 建議保留 `total_value`（原幣，僅供除錯）但**明確標示不可作為總額**，或乾脆移除避免誤用。

2. **修正 00887 交易所別（Bug-3）**：把 00887 從 `OTC_STOCKS` 移除，改走 `.TW`；或建立正確的「上市/上櫃」對照表，不要硬編在兩個檔案。

3. **統一報價與匯率來源（Bug-5）**：
   - 把 `_get_price` 抽成單一共用服務，summary 與 computed 共用同一份（最好加短期 cache）。
   - 移除 `holdings.py:186` 的 `@lru_cache` FX，改成和 summary 一樣每次讀 DB，或兩邊都走同一個帶 TTL 的匯率服務。

4. **XIRR 改台幣現金流（Bug-6）**：`quantity*price*fx_rate`，期末值用 `total_value_twd`。

5. **已實現損益（Bug-7）**：`SUM(realized_gain)` 依幣別換匯後加總，填 `realized_gain_twd`。

### 前端（最快止血）

6. **DashboardPage.tsx:254-255 立即改用台幣欄位**（即使後端先不動，也能修正畫面）：
   ```tsx
   value={formatTWD(summary.total_value_twd)}      // 總市值 → 967,184
   sub={`成本 ${formatTWD(summary.total_cost_twd)}`}
   value={formatTWD(summary.unrealized_gain_twd)}  // 未實現 → -91,032
   ```
   ⚠️ 但 `unrealized_pct` 仍是後端混幣算的，需一併在後端修（Bug-2/4），否則 % 仍錯。

> **最小修復路徑**：只改 §7-6（前端 2 行）即可讓「總市值 / 未實現」兩張卡片正確顯示 967,184 / -91,032。但 `unrealized_pct`、XIRR、卡片與表格不同步（Bug-3/5/6）仍需後端處理才會徹底乾淨。

---

## 8. 驗證方式

### 本次稽核實際執行的步驟（可重現）

1. 確認後端運行：`curl http://localhost:8000/docs` → 200（uvicorn pid 99684）。
2. 以 SECRET_KEY 簽發 user_id=5 的 JWT（`.env` 內 `wealth-secret-key-change-in-production`）。
3. 實際呼叫並比對：

```bash
# summary（重現錯誤數字）
curl -s http://localhost:8000/portfolio/summary -H "Authorization: Bearer <TOKEN_uid5>"
#   total_value = 353012.0   ← 與 Lewis 畫面一致 ✅ 重現
#   total_value_twd = 967183.98  ← 與 Lewis 期望值 967,184 一致 ✅
#   unrealized_gain = -2844.75   ← 與畫面 -2,845 一致 ✅ 重現
#   unrealized_gain_twd = -91031.85  ← 真實台幣未實現

# computed（證明兩端點報價不同步）
curl -s http://localhost:8000/holdings/computed -H "Authorization: Bearer <TOKEN_uid5>"
#   GLD current_price = 453.13（退回均價）vs summary 用 396.24（真實）
```

4. yfinance 報價驗證（證明 Bug-3）：
```
00887.OB -> NO DATA（空）→ 退回均價 16.66
00887.TW -> （Yahoo 亦間歇性無資料，但 .OB 為錯誤後綴）
GLD      -> 396.24  → 佐證 333,200 + 50×396.24 = 353,012 ✅
```

### 修復後應達成的驗收標準

| 項目 | 驗收條件 |
|------|---------|
| 總市值卡片 | 顯示 **NT$967,184**（= `total_value_twd`）|
| 未實現損益卡片 | 顯示約 **NT$-91,032**（= `total_value_twd − total_cost_twd`）|
| 卡片 vs 持倉表 | 「總市值」≈ 持倉表各列 `market_value_twd` 之和（誤差僅來自報價時間差）|
| 00887 | 有真實市價與漲跌幅，未實現不再恆為 0 |
| 兩端點 | summary 與 computed 對同一商品回傳相同股價/匯率 |

### 建議的回歸測試（單元測試）

針對「00887(TWD) + GLD(USD)」這組固定資料寫一個測試：
- 斷言 `total_value_twd == 333200 + 50*price_gld*usd_rate`；
- 斷言 `total_value_twd != total_value`（防止有人又把彙總改回混幣）；
- 斷言 `unrealized_gain_twd == total_value_twd - total_cost_twd`。

---

### 附錄：相關檔案與行號速查

| 議題 | 檔案:行號 |
|------|----------|
| 前端卡片餵錯欄位 | `frontend/src/pages/DashboardPage.tsx:254-255` |
| `formatTWD` 只貼 NT$ 不換匯 | `frontend/src/pages/DashboardPage.tsx:42-48` |
| 持倉表用原幣顯示 | `frontend/src/pages/DashboardPage.tsx:343-360` |
| 後端混幣累加 | `backend/app/routers/portfolio.py:173-179` |
| `unrealized_gain_twd` 錯誤算式 | `backend/app/routers/portfolio.py:214` |
| 00887 用 `.OB` | `backend/app/routers/holdings.py:12` / `portfolio.py:73` |
| FX `@lru_cache` 不同步 | `backend/app/routers/holdings.py:186-195` |
| XIRR 混幣現金流 | `backend/app/routers/portfolio.py:186-204` |
