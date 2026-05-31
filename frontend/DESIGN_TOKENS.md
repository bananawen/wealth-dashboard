# Wealth Design Tokens

## Convention A — P/L Direction（通用）

所有**投資損益**顯示統一用這套：

| 意思 | class | 實際顏色 |
|------|-------|---------|
| 漲／獲利 | `!text-success` / `!bg-success` | 綠（emerald） |
| 跌／虧損 | `!text-error` / `!bg-error` | 紅（red） |
| 持平 | `!text-warning` | 黃（amber） |
| 強調 | `!text-accent` | 藍色系 |

### 元件清單
- `StatCard`（Summary 總損益）
- `HoldingsTable` P/L 欄

---

## Convention B — Transaction Type（買賣動作）

此 convention 用於**交易歷史**列表，區分**現金流向**而非投資績效：

| 意思 | class | 實際顏色 | 意義 |
|------|-------|---------|------|
| 買進（出金） | `!text-error` | 紅 | 錢付出去了 |
| 賣出（入金的） | `!text-success` | 綠 | 錢收进来了 |

此區域**不受 Convention A 約束**，需另外引用。

---

## 通用規則

```tsx
// ✅ P/L 顯示（Convention A）
<span className="!text-success">+$123.45</span>
<span className="!text-error">-$67.89</span>

// ✅ 交易動作（Convention B）
<span className="!text-error">買</span>
<span className="!text-success">賣</span>

// ❌ 錯誤：裸寫色值
<span className="text-emerald-500">...</span>
<span className="text-red-500">...</span>
```

## 禁止事項

- 嚴禁新 компонент 使用 `text-emerald-*` / `text-red-*` 等裸寫色值
- 禁止在 P/L 顯示區塊使用 Convention B（反之亦然）
