# 個人財富管理 - 前端重構規格書

## 目標
將現有 Vite + React + Tailwind 前端從 gray-900 配色重構為 Hermes 官網風格（藍色主題 + Dark/Light 切換 + 響應式）。

## 設計方向

### 配色方案

**Dark Mode（主要）:**
- 背景: `#07070d` (近黑)
- 卡片: `#0f0f18`
- 邊框: `rgba(59, 130, 246, 0.08)` (藍色透明)
- 主色: `#3B82F6` (藍色)
- Accent: `#FFD700` (金色 - Hermes 品牌色)
- 文字: `#e8e4dc`
- 次要文字: `#9a968e`
- 成功: `#10B981`
- 損失: `#EF4444`

**Light Mode:**
- 背景: `#F8F9FC`
- 卡片: `#FFFFFF`
- 邊框: `rgba(59, 130, 246, 0.12)`
- 主色: `#1D4ED8` (深藍)
- Accent: `#B8860B` (深金)
- 文字: `#1a1a2e`
- 次要文字: `#6B7280`

### 字體
- 主字體: Inter
- 等寬字體: JetBrains Mono

### 響應式斷點
- Mobile: `< 640px` (iPhone)
- Tablet: `640px - 1024px` (iPad)
- Desktop: `> 1024px` (MacBook)

## 功能不變
- 登入/註冊
- 儀表板（6統計卡片）
- 持倉表格（可排序）
- 交易紀錄
- 新增持倉表單
- 歷史淨值趨勢圖
- 金額隱藏切換
- localStorage 持久化

## 重構項目
1. `tailwind.config.js` - 新增 darkMode + 自訂顏色
2. `src/index.css` - Tailwind base layer + CSS 變數
3. `src/context/ThemeContext.jsx` - Dark/Light toggle
4. `src/components/ThemeToggle.jsx` - 主題切換按鈕
5. `src/components/Header.jsx` - 帶主題切換的導航列
6. `src/pages/LoginPage.jsx` - Herms 風格登入頁
7. `src/pages/DashboardPage.jsx` - 更新所有顏色 class
8. `src/utils/api.js` - 更新 logger 顏色
9. `index.html` - 更新 favicon/title + font import

## 技術棧
- React 18 + Vite
- Tailwind CSS v3 (custom theme)
- Recharts
- Lucide React icons