import type { AssetClass, ComputedHolding, Sector, Transaction, TransactionCategory } from '../../types';

export const HOLDING_GROUP_LABELS = {
  equity: '股票',
  bond: '債券',
  precious_metal: '貴金屬',
  cash: '現金',
  other: '其他',
} as const;

export type HoldingGroupKey = keyof typeof HOLDING_GROUP_LABELS;

export const HOLDING_GROUP_ORDER: HoldingGroupKey[] = ['equity', 'bond', 'precious_metal', 'cash', 'other'];
export const PIE_COLORS = ['#3B82F6', '#22C55E', '#F59E0B', '#A855F7', '#EF4444', '#14B8A6'];
export const CASH_SYMBOLS = new Set(['CASH', 'USD', 'TWD', 'NTD', 'NT$', '現金']);

export const TRANSACTION_CATEGORY_LABELS: Record<TransactionCategory, string> = {
  long_term: '長期投資',
  short_term: '短線',
  etf: 'ETF',
  stock: '個股',
  dca: '定期定額',
};

export const TRANSACTION_CATEGORY_OPTIONS: Array<{ value: 'all' | TransactionCategory; label: string }> = [
  { value: 'all', label: '全部分類' },
  { value: 'long_term', label: '長期投資' },
  { value: 'short_term', label: '短線' },
  { value: 'etf', label: 'ETF' },
  { value: 'stock', label: '個股' },
  { value: 'dca', label: '定期定額' },
];

export const ASSET_CLASS_LABELS: Record<AssetClass, string> = {
  equity: '股票',
  bond: '債券',
  precious_metal: '貴金屬',
  cash: '現金',
  other: '其他',
};

export const SECTOR_LABELS: Record<Sector, string> = {
  semiconductor: '半導體',
  technology: '科技',
  financial: '金融',
  communication: '通訊',
  consumer: '消費',
  industrial: '工業',
  healthcare: '醫療保健',
  energy: '能源',
  materials: '原物料',
  utilities: '公用事業',
  real_estate: '不動產',
  broad_market: '大盤ETF',
  high_dividend: '高股息ETF',
  thematic: '主題ETF',
  other: '其他',
};

export const SECTOR_OPTIONS: Array<{ value: Sector; label: string }> = [
  { value: 'semiconductor', label: '半導體' },
  { value: 'technology', label: '科技' },
  { value: 'financial', label: '金融' },
  { value: 'communication', label: '通訊' },
  { value: 'consumer', label: '消費' },
  { value: 'industrial', label: '工業' },
  { value: 'healthcare', label: '醫療保健' },
  { value: 'energy', label: '能源' },
  { value: 'materials', label: '原物料' },
  { value: 'utilities', label: '公用事業' },
  { value: 'real_estate', label: '不動產' },
  { value: 'broad_market', label: '大盤ETF' },
  { value: 'high_dividend', label: '高股息ETF' },
  { value: 'thematic', label: '主題ETF' },
  { value: 'other', label: '其他' },
];

export function formatCurrency(v: number, currency = 'USD') {
  if (v == null || Number.isNaN(v)) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(v);
}

export function formatTWD(v: number) {
  if (v == null || Number.isNaN(v)) return 'N/A';
  return `NT$${Number(v).toLocaleString('zh-TW', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

export function formatByCurrency(v: number, currency = 'TWD') {
  if (v == null || Number.isNaN(v)) return 'N/A';
  if (currency === 'USD') {
    return `US$${Number(v).toLocaleString('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    })}`;
  }
  if (currency === 'TWD') {
    return `NT$${Number(v).toLocaleString('zh-TW', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    })}`;
  }
  return `${currency} ${Number(v).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
}

export function formatPct(v: number) {
  if (v == null || Number.isNaN(v)) return 'N/A';
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
}

export function formatDateMMMDDYY(dateStr: string) {
  const d = new Date(dateStr);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[d.getMonth()]}-${String(d.getDate()).padStart(2, '0')}-${String(d.getFullYear()).slice(-2)}`;
}

export function formatShares(v: number) {
  if (v == null || Number.isNaN(v)) return '0';
  return Number.isInteger(v) ? v.toString() : v.toFixed(2);
}

export function formatCurrencyBreakdown(values?: Record<string, number>) {
  if (!values || Object.keys(values).length === 0) return 'N/A';
  return Object.entries(values)
    .filter(([, value]) => Number.isFinite(value) && value !== 0)
    .map(([currency, value]) => `${currency} ${value >= 0 ? '+' : '-'}${formatByCurrency(Math.abs(value), currency)}`)
    .join(' · ');
}

export function getTransactionCategoryCount(symbol: string, transactions: Transaction[]) {
  const counts = new Map<TransactionCategory, number>();
  transactions.forEach((tx) => {
    if (tx.symbol.toUpperCase() !== symbol.toUpperCase() || !tx.category) return;
    counts.set(tx.category, (counts.get(tx.category) ?? 0) + 1);
  });
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
}

export function getTransactionAssetClass(symbol: string, transactions: Transaction[]): AssetClass | null {
  const counts = new Map<AssetClass, number>();
  transactions.forEach((tx) => {
    if (tx.symbol.toUpperCase() !== symbol.toUpperCase() || !tx.asset_class) return;
    counts.set(tx.asset_class, (counts.get(tx.asset_class) ?? 0) + 1);
  });
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
}

export function getHoldingGroup(h: ComputedHolding, transactions: Transaction[]): HoldingGroupKey {
  const symbol = h.symbol.toUpperCase();
  if (CASH_SYMBOLS.has(symbol) || symbol.includes('CASH')) return 'cash';
  const assetClass = getTransactionAssetClass(symbol, transactions);
  if (assetClass) return assetClass;
  if (symbol === 'GLD' || symbol === 'IAU' || symbol === 'SLV') return 'precious_metal';
  if (symbol === 'BND' || symbol === 'AGG' || symbol === 'TLT' || symbol === 'LQD') return 'bond';
  const primaryCategory = getTransactionCategoryCount(symbol, transactions);
  if (primaryCategory === 'stock' || primaryCategory === 'etf' || h.exchange === 'US' || h.exchange === 'TWSE' || h.exchange === 'OTC') {
    return 'equity';
  }
  return 'other';
}

export function getPriceStatusLabel(h: ComputedHolding) {
  if (h.price_status === 'live') return h.price_source ? `即時 / ${h.price_source}` : '即時';
  if (h.price_status === 'estimated') return '價格暫缺，均價估算';
  return '價格暫缺';
}

export function getMarketLabel(h: ComputedHolding) {
  if (h.exchange === 'US') return '美股';
  if (h.exchange === 'TWSE' || h.exchange === 'OTC') return '台股';
  return '其他';
}
