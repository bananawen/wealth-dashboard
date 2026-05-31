/**
 * Wealth Dashboard Theme — 統一一站式樣式範本
 *
 * 台灣股市顏色慣例：
 *   綠色 (#22C55E) = 漲/賺/買 = 上漲、正向
 *   紅色 (#EF4444) = 跌/賠/賣 = 下跌、負向
 *
 * 使用方式：
 *   import { theme } from '@/styles/theme';
 *   color: theme.profit   // 綠色（賺）
 *   color: theme.loss     // 紅色（賠）
 *   或直接用 CSS var:     color: var(--profit)
 */

export const theme = {
  // ---------- 漲跌/損益 顏色（台灣慣用） ----------
  profit: '#22C55E',    // 綠色：漲、賺、盈餘、買入
  loss:   '#EF4444',    // 紅色：跌、賠、虧損、賣出

  // ---------- 狀態顏色 ----------
  success:  '#22C55E', // 同 profit（保留向後相容）
  error:    '#EF4444', // 同 loss（保留向後相容）
  warning:  '#F59E0B', // 黃色：警告
  info:     '#3B82F6', // 藍色：資訊/主要動作

  // ---------- 明暗模式共同 ----------
  accent:       '#3B82F6',
  accentHover:  '#2563EB',

  // ---------- 深色模式增強（for .dark class） ----------
  dark: {
    profit:    '#4ADE80', // 亮綠（深色背景下更明顯）
    loss:      '#F87171', // 亮紅
    success:   '#4ADE80',
    error:     '#F87171',
    warning:   '#FBBF24',
    accent:    '#60A5FA',
    accentHover:'#3B82F6',
  },

  // ---------- 間距 ----------
  radius: {
    sm:  '0.375rem',  // 6px
    md:  '0.75rem',   // 12px
    lg:  '1rem',      // 16px
    xl:  '1.5rem',    // 24px
  },
} as const;

/** Utility: apply theme CSS vars to document root */
export function applyThemeVars(isDark: boolean) {
  // Handled by index.css :root / .dark class — no-op but kept for API compat
}

// 便利函式：根據正負值回傳顏色（台灣慣用）
export function profitLossColor(value: number): string {
  if (value > 0) return theme.profit;
  if (value < 0) return theme.loss;
  return 'var(--text-secondary)';
}

// 便利函式：gain >= 0 → profit color, else loss color
export function gainColor(gain: number): string {
  return gain >= 0 ? theme.profit : theme.loss;
}