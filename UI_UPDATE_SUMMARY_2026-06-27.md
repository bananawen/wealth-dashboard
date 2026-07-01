# UI Update Summary - 2026-06-27

## 結論

本次同時完成兩項工作：

- 整理 `CHANGELOG.md`，改成依日期分組，避免多個重複 `## Change Log` 區塊持續堆疊。
- 優化 Dashboard 手機版列表，持倉與交易在手機上改成摘要卡，桌機仍保留原本表格與密集清單。
- 拆分 Dashboard 工作區路由，讓總覽、持倉、交易不再只存在同一頁的 tab 裡。
- 補上單一使用者部署的 owner/admin 狀態提示，避免登入後仍看起來像多使用者系統。

部署假設：

- 目前產品定位是單一使用者網站。
- 第一個註冊帳號會自動成為管理者。
- `admin` 角色只用來保護系統管理頁與備份/爬蟲工具，不代表系統內存在多種一般使用者角色。

## 修改內容

### 1. Changelog 整理

檔案：

- `CHANGELOG.md`

調整：

- 保留原本 Keep a Changelog 的基本格式。
- 新增 `2026-06-27` 日期分組。
- 新增 `2026-06-26` 日期分組。
- 將原本連續多段 `## Change Log` 合併成：
  - `Added`
  - `Changed`
  - `Fixed`
  - `Risk And Rollback`
  - `Next`
- 保留 `1.0.0` 初始版本紀錄。

目的：

- 讓專案文件更可追蹤。
- 未來查詢某一天做了什麼，不需要在多個重複標題中翻找。

### 1-1. 單一使用者部署提示

檔案：

- `frontend/src/components/DashboardLayout.tsx`
- `frontend/src/pages/AdminPage.tsx`
- `frontend/src/pages/LoginPage.tsx`
- `CHANGELOG.md`

調整：

- Login 註冊提示已明確說明第一個註冊帳號會自動成為管理者。
- Dashboard 頂部新增 owner/admin 狀態提示，桌機與手機都看得到。
- Admin 頁首頁首屏補上「這是 owner 系統工具區」說明，避免誤解成多租戶後台。
- `CHANGELOG.md` 內的 `admin`/`user` 描述改成符合單一使用者部署語境。
- 新增 `AUTH_MODEL.md`，把 owner 帳號規則、JWT 欄位與 `/admin` 保護方式集中寫清楚。
- `deploy/README.md` 補上單一使用者部署假設與 SQLite owner 帳號檢查方式。

目的：

- 把權限模型講清楚，降低使用與維護時的誤判。
- 讓 UI 呈現和目前實作一致，不再殘留多使用者產品語氣。

### 2. Dashboard 手機版持倉列表

檔案：

- `frontend/src/pages/DashboardPage.tsx`

調整：

- 手機版新增持倉摘要卡。
- 每張卡顯示：
  - 股票代號
  - 價格狀態
  - 市場 / 類型
  - 股數
  - 現值
  - 未實現損益
  - 報酬率
  - 現價
  - 成本
- 卡片仍可點選，會同步切換下方單一持倉詳情。
- 桌機版保留原本可排序表格。

目的：

- 手機上不再依賴橫向捲動表格。
- 保留工具型資訊密度，但更適合單手掃描。

### 3. Dashboard 手機版交易列表

檔案：

- `frontend/src/pages/DashboardPage.tsx`

調整：

- 手機版交易列改成卡片外觀。
- 每張卡保留：
  - 日期
  - 分類
  - 股票代號
  - 買入 / 賣出 badge
  - 股數、價格、成交額
  - 備註
  - 手續費、稅費、已實現損益
  - 刪除按鈕
- 點卡片仍可進入編輯。
- 桌機版保留原本較密集的列表表現。

目的：

- 手機交易列表更容易閱讀與點選。
- 刪除入口在手機上更容易找到，不需要 hover。

### 4. Dashboard 拆分頁面

檔案：

- `frontend/src/App.tsx`
- `frontend/src/pages/DashboardPage.tsx`

調整：

- `/` 改為自動導向 `/overview`。
- 新增 `/overview` 作為總覽頁，只放核心數字與入口摘要。
- 新增 `/holdings` 作為持倉頁，集中持倉概覽、持倉列表、單檔明細與資產走勢。
- 新增 `/transactions` 作為交易頁，集中交易篩選、列表、編輯與刪除。
- 新增 `/transactions/new` 作為新增 / 編輯交易工作區。
- 原本的頁內 tab 改成 URL 導覽連結，手機與桌機都可直接切換。
- 新增 `OverviewPage.tsx`、`HoldingsPage.tsx`、`TransactionsPage.tsx`、`AddTransactionPage.tsx` 四個實體頁面檔。
- `App.tsx` 改由這四個頁面檔負責對應路由，而不是全部直接指向 `DashboardPage.tsx`。
- 新增 `DashboardLayout.tsx`，集中處理頁首、狀態列與路由導覽。
- 新增 `useDashboardState.ts`，集中處理 Dashboard 的 query、排序、篩選、undo 與交易操作狀態。
- 新增 `types/dashboard.ts`，統一 `view`、持倉排序與目標配置相關型別。
- 新增 `ConfirmDialog.tsx`，作為站內確認視窗。
- 新增 `InlineNotice.tsx`，作為 Dashboard 頁內通知列。
- 新增 `HoldingsSection.tsx` 與 `TransactionsSection.tsx`，把兩個大型工作區從 `DashboardPage.tsx` 拆出。
- 新增 `dashboard/shared.ts` 與 `DashboardStatCard.tsx`，集中 Dashboard 共用格式與卡片元件。
- 新增 `OverviewPerformanceSection.tsx`，將總覽圖表區塊獨立。
- 將右上角分散的 header 操作按鈕收斂為單一操作選單。
- 將左上角標題改為首頁按鈕，點擊後回到 `/overview`。
- 將版本資訊退到大螢幕才完整顯示，手機上不再佔用 header 空間。
- 將主導航列改成手機版四等分分段按鈕，桌機維持較完整的寬版導覽。
- 將 `LoginPage`、`ChangePasswordPage`、`AddTransactionForm` 的提示樣式統一到同一套站內 notice。
- 將交易新增 / 編輯與批次匯入結果改成一致的頁內回饋語言。
- 新增 `ChangePasswordForm.tsx`，將修改密碼邏輯抽成可重用元件。
- 將 Dashboard 內的「修改密碼」改成上層對話框，不再跳去獨立頁面。
- 將 `/change-password` 路由改為導回 `/overview`，避免舊入口繼續形成第二套主要流程。
- 移除獨立的 `ChangePasswordPage.tsx` 頁面檔，正式讓 dialog 成為唯一主流程。
- 移除未使用且仍指向舊路徑的 `Header.tsx` 舊元件。

目的：

- 符合「總覽一頁只看重點，細節放後面分頁」的方向。
- URL 可以直接代表目前工作區，後續要分享、重新整理或除錯都更明確。
- 先保留共用 Dashboard 元件，降低一次性大重構的風險。
- 先把頁面邊界拆乾淨，後續若要把共用邏輯抽成 hooks 或 layout，改動面會更可控。
- 現在殼層與 state 已經有明確切點，後續拆 `DashboardPage.tsx` 不需要再碰路由與頂部操作列。
- 現在主要工作區也已有清楚邊界，後續再做手機優化或功能追加，不需要直接在單一大檔案上修改。
- 現在錯誤提示也已回到站內 UI，主要工作流不再被瀏覽器原生對話框打斷。
- 現在 header 視覺更乾淨，主要導覽與次要操作的層級已分開。
- 手機 header 與導航的資訊重量又再降了一層，頁面更像工具面板而不是一般網站導覽列。
- 常見操作錯誤與成功回饋現在不再混用不同視覺樣式，整體一致性更高。
- 帳戶設定操作現在留在當前工作流中完成，不會打斷使用者所在頁面的上下文。
- 舊網址不會直接壞掉，但新的主路徑已明確只剩 dialog 入口。
- 與舊改密碼頁面相關的殘留路徑與舊 header 也已一起清掉，專案狀態更一致。

## 驗證

已執行：

```bash
cd /home/lewis/wealth/frontend
npm run build
```

結果：

- Build 成功。
- 新版已輸出到 `frontend/dist`。
- Vite 仍有 chunk size warning，但不影響本次功能。

## 影響範圍

- `CHANGELOG.md`
- `frontend/src/App.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/OverviewPage.tsx`
- `frontend/src/pages/HoldingsPage.tsx`
- `frontend/src/pages/TransactionsPage.tsx`
- `frontend/src/pages/AddTransactionPage.tsx`
- `frontend/src/components/DashboardLayout.tsx`
- `frontend/src/components/ConfirmDialog.tsx`
- `frontend/src/components/InlineNotice.tsx`
- `frontend/src/components/dashboard/HoldingsSection.tsx`
- `frontend/src/components/dashboard/OverviewPerformanceSection.tsx`
- `frontend/src/components/dashboard/TransactionsSection.tsx`
- `frontend/src/components/dashboard/shared.ts`
- `frontend/src/components/dashboard/DashboardStatCard.tsx`
- `frontend/src/hooks/useDashboardState.ts`
- `frontend/src/types/dashboard.ts`
- `frontend/dist`

## 風險

- 低風險，主要是前端呈現調整。
- 桌機版保留原表格，主要變更集中在手機版。
- 路由已拆分，但目前仍共用同一個 Dashboard 元件；這是刻意降低風險的過渡方案。
- 目前的「實體頁面檔」主要負責路由入口，真正的大型商業邏輯仍在 `DashboardPage.tsx`。
- 雖然共用 state 與 layout 已抽出，但持倉區塊與交易區塊的 JSX 仍集中在 `DashboardPage.tsx`。
- 刪除交易已改成站內 modal，但其他舊的 `alert` 仍還在錯誤與 undo 流程內。
- Dashboard 的 delete / undo `alert` 已移除，但其他頁面若還有錯誤提示，仍可能使用各自的呈現方式。
- Header 選單目前是 Dashboard 專用實作；若未來全站都要一致，可再抽成通用 dropdown/menu 元件。
- 手機導覽目前以四個主要入口為固定結構；如果未來再新增主頁面，需重新評估分段按鈕寬度。
- 目前 notice 仍是頁面內局部狀態；若未來要做全站跨頁通知，應再升級成共用 toast store。
- `/change-password` 路由目前仍保留作為 fallback；若確認不再需要獨立頁面，可再考慮移除。
- 若未來真的需要獨立帳戶設定頁，建議重新以 `ChangePasswordForm.tsx` 為基礎建立，而不是恢復舊頁面。
- 若手機畫面仍覺得太長，可再壓縮卡片欄位，例如隱藏原幣金額，只保留 TWD。

## 下一步建議

- 把刪除交易的 browser `confirm` 改成 app 內 modal。
- 把交易新增 / 編輯做成更明確的單一工作區。
- 後續可針對手機版持倉卡增加快速排序選單。
- 下一步可把 `DashboardPage.tsx` 內的共用邏輯拆成 `useDashboardData` 與 `DashboardLayout`，再逐步把三個頁面真正獨立。
- 下一步更合理的方向是把持倉與交易區塊各拆成 `HoldingsSection` / `TransactionsSection`，而不是再擴大 `DashboardPage.tsx`。
- 下一步可以把錯誤提示也改成站內 toast / banner，讓 `alert` 一併退出主要流程。
- 下一步可把 `AddTransactionForm` 的成功提示也統一進同一套 notice / toast 流程。

## Change Log

日期：2026-06-27

修改內容：
- 新增：
  - 無
- 修改：
  - 調整 `frontend/src/index.css` 的全域寬度與 overflow 規則，移除 `body` 左右 safe-area padding，改為由容器自行控制。
  - 調整 `frontend/src/components/StatusBar.tsx` 的手機版資訊排列，隱藏次要時間資訊並加入 `min-w-0` / `overflow-x-hidden`。
  - 調整 `frontend/src/components/DashboardLayout.tsx` 的 header、主導航與主內容容器，避免 iPhone 14 Pro 寬度超出 viewport。
  - 調整 `frontend/src/components/DashboardLayout.tsx` 的主內容容器裁切策略，避免交易頁 autocomplete 下拉選單被共用版型裁掉。
  - 調整 `frontend/src/components/AddTransactionForm.tsx` 的商品搜尋互動，補上穩定的 focus/click 建議清單、外部點擊收合與較高層級的下拉選單。
  - 調整 `frontend/src/components/AddTransactionForm.tsx` 的 autocomplete 排序邏輯，優先顯示實際交易過的商品，並依交易次數與最近交易日期排序。
  - 清理 `frontend/src/components/AddTransactionForm.tsx` 內殘留的 `setError` 呼叫，統一改為 `setNotice`。
  - 調整 `frontend/src/components/dashboard/TransactionsSection.tsx` 的交易篩選搜尋框，補上商品 autocomplete，並區分為桌機浮動清單與手機版內嵌清單。
  - 調整 `frontend/src/components/dashboard/TransactionsSection.tsx` 的篩選建議來源，改為優先顯示目前仍有持倉的商品，其次才是曾交易但已清倉的商品，並移除固定商品清單。
  - 調整 `frontend/src/components/dashboard/TransactionsSection.tsx` 的起迄日期篩選布局，手機版改為直向堆疊並限制原生日期欄位寬度，避免 iPhone 溢出。
  - 調整 `frontend/src/pages/AdminPage.tsx` 的 Audit Log 起迄日期篩選布局，手機版改為直向標籤與全寬日期欄位，避免再次撐出頁面。
  - 調整 `frontend/src/components/DatePicker.tsx` 成為可清空、可配置年份範圍的共用日期選擇元件，供交易篩選、Audit Log 與新增交易共用。
  - 將 `frontend/src/components/dashboard/TransactionsSection.tsx` 與 `frontend/src/pages/AdminPage.tsx` 的原生 `date` 輸入改為共用 `DatePicker`，避開 iOS WebKit 原生日期浮層寬度問題。
  - 修正 `frontend/dist` 的靜態檔權限，恢復 `nginx` 對首頁與資產檔的讀取權限，排除站點 `403 Forbidden`。
  - 調整交易頁與 Audit Log 的日期篩選初始狀態，將「結束日期」預設為當天，清除篩選後也回到當天。
  - 調整 `frontend/package.json` 的 `build` 腳本，固定以 `umask 022` 產出前端靜態檔，並在 build 後自動將 `dist` 目錄設為 `755`、檔案設為 `644`，避免每次修改後再次觸發 `403`。
  - 進一步調整交易頁與 Audit Log 的日期篩選預設區間，改為「開始日期預設前 30 天、結束日期預設今天」，清除篩選後也回到同一組近 30 天區間。
  - 調整 `frontend/src/pages/LoginPage.tsx` 與 `frontend/src/components/PasswordField.tsx` 的登入欄位樣式，強化邊框、背景層次與 focus 狀態，讓帳號與密碼輸入框更容易被辨識。
- 刪除：
  - 無

修改原因：

- 使用者回報 iPhone 14 Pro 各頁面出現橫向溢出，問題集中在共用殼層與全域寬度設定，而非單一功能頁。
- 使用者回報交易頁輸入商品時沒有出現自動完成下拉選單，需確認是否被共用容器裁切或互動事件失效。
- 使用者希望實際交易過的商品排在自動完成清單前面，降低重複輸入常用商品的成本。
- 後續確認截圖後發現問題欄位其實是「交易列表篩選框」，不是「新增交易表單」的商品欄位，因此需在 `TransactionsSection` 另行補上 autocomplete。
- 使用者確認篩選頁的合理邏輯應為「目前仍有庫存的商品優先」，而不是顯示泛用商品名單。
- 使用者回報交易頁起迄日期在手機上仍然溢出，因此需針對原生 `date` 欄位做更保守的版型收斂。
- 使用者回報 Admin Audit Log 的起迄日期也有相同問題，因此需同步套用同一類手機版收斂策略。
- 使用者提供 iOS Edge 截圖後，確認問題根因是 iOS WebKit 原生日期選擇器浮層，而不是一般 CSS 容器 overflow。
- 使用者後續回報網站 `403 Forbidden`，檢查後確認是最新前端 build 產物在 `umask 0077` 下被寫成 `600/700` 權限，導致 `nginx` 無法讀取。
- 使用者希望交易頁與 Audit Log 的結束日期更符合日常查詢習慣，因此改為預設今天而不是空值。
- 使用者追問為何每次修改後都會再出現 `403`，進一步確認根因是本機 shell 的 `umask 0077` 會在每次前端 build 後重新把部署檔權限鎖死。
- 使用者後續希望開始日期也更貼近日常檢視習慣，因此預設查詢區間從「只帶結束日期」調整為完整的「近 30 天」。
- 使用者回報登入頁的帳號密碼輸入框邊界不夠明顯，因此需在不影響流程的前提下提升欄位辨識度。

影響範圍：

- `frontend/src/index.css`
- `frontend/src/components/StatusBar.tsx`
- `frontend/src/components/DashboardLayout.tsx`
- `frontend/src/components/AddTransactionForm.tsx`
- `frontend/src/components/dashboard/TransactionsSection.tsx`
- 手機版 `/overview`、`/holdings`、`/transactions`、`/transactions/new` 共用版型
- 交易頁 `/transactions/new` 的商品搜尋 autocomplete
- 交易頁 `/transactions` 篩選列的商品搜尋 autocomplete

下一步：

- 直接在 iPhone 14 Pro 實機重新檢查四個主要頁面是否仍能左右滑動。
- 在新增交易頁測試點擊、輸入 `00`、`AAP`、清空再重點擊，確認自動完成選單都能正常出現。
- 確認常用交易商品是否排在建議清單前段，且帶有 `已交易` 標記。
- 在交易列表頁的篩選框測試 `005`、`233`、`AAP`，確認手機鍵盤打開時也能看到建議清單。
- 確認交易篩選頁的建議標記已改為 `持倉中` / `已清倉`，且目前持倉商品確實排在最前面。
- 在 iPhone 上確認交易頁起始日期與結束日期已不再橫向撐出卡片。
- 在 iPhone 上確認 Admin Audit Log 的起始日期與結束日期已不再橫向撐出篩選區。
- 確認交易頁與 Audit Log 已不再使用原生 `input[type=\"date\"]`，改由共用 `DatePicker` 處理日期選擇。
- 確認首頁與主要資產檔已恢復 `644/755` 權限，`http://192.168.0.215/` 與 `/assets/*` 重新回到 `200 OK`。
- 確認交易頁與 Audit Log 首次進入時，結束日期都會自動帶入當天。
- 確認新的 `npm run build` 執行後，首頁仍維持 `200 OK`，且 `dist` 檔案權限不再回到 `600/700`。
- 確認交易頁與 Audit Log 首次進入時，會自動帶入「30 天前 ～ 今天」的篩選區間。
- 確認登入頁的帳號、密碼、確認密碼欄位在深色背景下有更清楚的框線與 focus 回饋。
- 若 Admin 頁仍有個別區塊溢出，再針對該頁的表格與篩選器做局部收斂。

## Change Log

日期：2026-06-30

修改內容：
- 新增：
  - `backend/tests/test_portfolio_performance_fallback.py`，補上「沒有 `portfolio_snapshots` 時仍能重建投資走勢」的單元測試。
- 修改：
  - 調整 `backend/app/services/portfolio_service.py` 的投資走勢資料來源邏輯。
  - 新增 `transactions + price_history` 的 fallback 歷史重建流程，讓沒有 snapshot 的帳號仍可顯示週/月/年/全部區間走勢。
  - 保留當日點位由 `get_summary()` 覆寫，避免最後一天只停留在前一個交易日收盤價。
- 刪除：
  - 無

修改原因：

- 使用者回報首頁「資產淨值走勢」圖表無論切到哪個區間都只顯示當天。
- 實際檢查後確認前端圖表元件正常，根因是使用者帳號在 `portfolio_snapshots` 沒有任何歷史資料，後端原本只能補一筆今天的總值。
- 目前資料庫其實已有大部分商品的 `price_history` 與完整交易紀錄，因此更合理的修法是先在後端補保守 fallback，而不是要求使用者手動先補 snapshot。

影響範圍：

- `backend/app/services/portfolio_service.py`
- `backend/tests/test_portfolio_performance_fallback.py`
- 首頁 `/overview` 的 `資產淨值走勢` API 回傳內容

風險與回滾方式：

- 風險低到中，影響範圍集中在 `GET /portfolio/performance`；若 fallback 計算與既有 snapshot 不一致，優先以既有 snapshot 為準。
- 如需回滾，可移除 `backend/app/services/portfolio_service.py` 的 `_build_fallback_history_rows()` 與 `get_performance()` 內的 fallback 呼叫，再重新啟動後端。

下一步：

- 重新啟動後端後，在首頁確認 `week / month / year / all` 都不再只剩 1 個點。
- 後續可考慮加一個 Admin 手動補建 `portfolio_snapshots` 的工具，讓歷史走勢資料來源更一致。

## Change Log

日期：2026-07-01

修改內容：
- 新增：
  - `frontend/src/context/ThemeContext.test.tsx`，補上主題切換不會遞迴失效的前端測試。
- 修改：
  - 調整 `frontend/src/context/ThemeContext.tsx`，將 Redux action creator 改用別名，避免與 hook 內的本地 `toggleTheme` 函式同名。
  - 調整 `frontend/src/test/setup.js`，補上 `window.matchMedia` mock，讓主題相關測試可在 `jsdom` 環境執行。
  - 重新 build `frontend/dist`，讓站上的淺色/深色主題切換修正生效。
- 刪除：
  - 無

修改原因：

- 使用者回報點選「淺色主題」後完全沒有作用。
- 實際檢查後確認問題不是 CSS 缺失，而是 `useTheme()` 內本地函式名稱覆蓋了 Redux 的 `toggleTheme` action creator，導致點擊後進入遞迴呼叫而非 dispatch。
- 因為這類 bug 容易在重構 hook 時再次出現，所以同步補上測試保護。

影響範圍：

- `frontend/src/context/ThemeContext.tsx`
- `frontend/src/context/ThemeContext.test.tsx`
- `frontend/src/test/setup.js`
- `frontend/dist`

風險與回滾方式：

- 風險低，影響範圍集中在前端主題切換。
- 如需回滾，可還原 `frontend/src/context/ThemeContext.tsx` 與本次 build 產物，再重新 build 前端。

下一步：

- 在手機與桌機上各測一次「切換為淺色 / 切換為深色」是否都會立即生效。
- 若後續要擴充主題系統，建議把 `ThemeContext` 的 hook 與 action 命名規則統一，避免再次發生同名覆蓋。

## Change Log

日期：2026-07-01

修改內容：
- 新增：
  - 無
- 修改：
  - 調整 `frontend/src/index.css` 的淺色主題全域色票，將純白背景改為暖灰白方案。
  - 保留既有深色主題、版型結構與 accent 藍色，只降低淺色模式的刺眼感。
  - 重新 build `frontend/dist`，讓 live 站點直接套用新的暖灰白淺色主題。
- 刪除：
  - 無

修改原因：

- 使用者確認想採用暖灰白方案，因為原本的純白淺色主題雖然乾淨，但在手機上觀看太刺眼。
- 目前網站的工具型結構已經穩定，因此這次只調整色票，不改動版面層級與互動行為，以控制風險。

影響範圍：

- `frontend/src/index.css`
- `frontend/dist`
- 全站淺色主題背景、卡片、邊框與文字層級

風險與回滾方式：

- 風險低，主要影響視覺色彩，不涉及資料或互動邏輯。
- 如需回滾，可將 `frontend/src/index.css` 的 `:root` 色票還原為純白版本後重新 build。

下一步：

- 在手機上切換到淺色模式，確認總覽、持倉、交易、Admin 四頁的可讀性是否都符合預期。
- 若局部區塊仍太亮，可再只微調卡片底色或邊框，不必重做整套主題。

## Change Log

日期：2026-07-01

修改內容：
- 新增：
  - 無
- 修改：
  - 進一步調整 `frontend/src/index.css` 的淺色與深色主題層次變數，補上 `panel`、`input`、`card shadow` 等全域視覺變數。
  - 強化 `.card`、`.card-hover`、`.state-panel` 與 `.input-field` 的邊框、底色與陰影，讓卡片和頁面背景更容易分離。
  - 深色主題同步調整 `bg-secondary`、`bg-tertiary`、`card-bg` 與 `border-color`，避免卡片與背景黏在一起。
  - 重新 build `frontend/dist`，讓淺色與深色的新卡片層次套用到 live 站點。
- 刪除：
  - 無

修改原因：

- 使用者希望不只淺色主題，連深色主題的卡片層次也一起調整。
- 目前站點的主要問題不是版型，而是卡片、次背景、輸入框與頁面底色在部分頁面太接近，導致閱讀節點不夠明確。
- 因此這次維持現有工具型版面，只從全域視覺 token 下手，讓變更可控且可回滾。

影響範圍：

- `frontend/src/index.css`
- `frontend/dist`
- 全站卡片、狀態面板、輸入框與次背景層次

風險與回滾方式：

- 風險低，主要影響視覺層級，不涉及功能邏輯。
- 如需回滾，可將 `frontend/src/index.css` 內新增的 `panel/input/shadow` 變數與 `.card`/`.state-panel` 調整還原後重新 build。

下一步：

- 在 `/overview`、`/holdings`、`/transactions`、`/admin` 各看一次淺色與深色，確認卡片與背景分離是否已經足夠。
- 如果特定頁面仍覺得擠或不夠清楚，下一步應做局部區塊微調，而不是再改整站色票。

## Change Log

日期：2026-07-01

修改內容：
- 新增：
  - 無
- 修改：
  - 調整 `frontend/src/pages/AdminPage.tsx` 的「價格與爬蟲」頁籤容器，讓左右兩區塊在手機寬度下可正確收縮。
  - 為排程控制卡、手動觸發卡、下一次排程卡，以及右側兩張表格卡加入 `min-w-0`，避免 grid/flex 子項目以內容寬度撐破頁面。
  - 調整「排程控制」頂部 badges 改為可換行。
  - 調整「下一次排程」清單的 job name / job id / trigger 顯示方式，長字串改為可截斷或換行，避免卡片橫向溢出。
  - 重新 build `frontend/dist`，讓 Admin 爬蟲頁手機版修正套用到 live 站點。
- 刪除：
  - 無

修改原因：

- 使用者回報 Admin 內的爬蟲頁面卡片在手機上仍會橫向溢出。
- 問題集中在爬蟲頁的卡片內容寬度管理，而不是整個 Admin 主框架；尤其 grid 子項與長字串在沒有 `min-w-0` 時，容易強制擴張卡片寬度。

影響範圍：

- `frontend/src/pages/AdminPage.tsx`
- `frontend/dist`
- Admin 頁 `/admin` 的 `價格與爬蟲` 分頁

風險與回滾方式：

- 風險低，主要影響手機版排版，不涉及資料邏輯。
- 如需回滾，可還原 `frontend/src/pages/AdminPage.tsx` 內 `renderScraper()` 區塊相關 className 後重新 build。

下一步：

- 在手機上重新檢查 Admin 的 `價格與爬蟲` 分頁，特別看排程控制卡、下一次排程卡與兩張表格卡是否仍可左右滑出頁面。
- 若還有局部溢出，再針對具體卡片做第二輪局部收斂，而不改整個 Admin 版型。
