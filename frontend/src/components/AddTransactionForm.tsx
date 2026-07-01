import { useState, useEffect, useRef, type ChangeEvent, type ReactNode } from 'react';
import {
  useCreateTransactionMutation,
  useUpdateTransactionMutation,
  useImportTransactionsMutation,
} from '../store/apiSlice';
import { Search, X, Plus, Upload, FileSpreadsheet } from 'lucide-react';
import DatePicker from './DatePicker';
import type { AssetClass, Sector, Transaction, TransactionCategory, TransactionType, TransactionImportResult } from '../types';
import InlineNotice from './InlineNotice';
import { SECTOR_LABELS, SECTOR_OPTIONS } from './dashboard/shared';

const STOCK_SUGGESTIONS = [
  'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'INTC', 'CSCO',
  'AMAT', 'ASML', 'LRCX', 'MU', 'SNPS', 'CDNS', 'PANW', 'CRWD', 'NET', 'ZS',
  'SPY', 'QQQ', 'VOO', 'VTI', 'IWM', 'VEA', 'VWO', 'BND', 'AGG', 'GLD', 'TLT', 'LQD',
  '0050', '0056', '00636', '006208', '00713', '00878', '00881', '00887', '00919', '00929',
  '2330', '2317', '2303', '2454', '2308', '2377', '2382', '2327', '2344',
  '3105', '3665',
  'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'C', 'AXP',
  'CAT', 'DE', 'BA', 'HON', 'UNP', 'RTX', 'LMT', 'NOC',
  'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD',
  'COST', 'WMT', 'HD', 'LOW', 'TGT', 'AMZN',
];

const CATEGORY_OPTIONS: Array<{ value: TransactionCategory; label: string }> = [
  { value: 'long_term', label: '長期投資' },
  { value: 'short_term', label: '短線' },
  { value: 'etf', label: 'ETF' },
  { value: 'stock', label: '個股' },
  { value: 'dca', label: '定期定額' },
];

const CATEGORY_LABELS: Record<TransactionCategory, string> = {
  long_term: '長期投資',
  short_term: '短線',
  etf: 'ETF',
  stock: '個股',
  dca: '定期定額',
};

const ASSET_CLASS_OPTIONS: Array<{ value: AssetClass; label: string }> = [
  { value: 'equity', label: '股票' },
  { value: 'bond', label: '債券' },
  { value: 'precious_metal', label: '貴金屬' },
  { value: 'cash', label: '現金' },
  { value: 'other', label: '其他' },
];

const ASSET_CLASS_LABELS: Record<AssetClass, string> = {
  equity: '股票',
  bond: '債券',
  precious_metal: '貴金屬',
  cash: '現金',
  other: '其他',
};

function normalizeDecimalInput(value: string): string {
  return value
    .replace(/[，、﹐]/g, ',')
    .replace(/[．。]/g, '.')
    .replace(/\s+/g, '')
    .replace(/,/g, '.');
}

function parseDecimalInput(value: string): number {
  const normalized = normalizeDecimalInput(value);
  return Number(normalized);
}

function normalizeSymbolInput(value: string): string {
  return value.trim().toUpperCase();
}

function isSuggestableSymbol(value: string): boolean {
  return /^[A-Z0-9._-]{2,12}$/.test(value);
}

interface FormState {
  symbol: string;
  type: TransactionType | '';
  shares: string;
  price: string;
  date: string;
  notes: string;
  category: TransactionCategory | '';
  assetClass: AssetClass | '';
  sector: Sector | '';
  fee: string;
  tax: string;
}

interface AddTransactionFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
  transactions?: Transaction[];
  editTransaction?: {
    id: number;
    symbol: string;
    type: TransactionType;
    shares: number;
    price: number;
    date: string;
    notes?: string | null;
    category?: TransactionCategory | null;
    asset_class?: AssetClass | null;
    sector?: Sector | null;
    fee?: number;
    tax?: number;
  };
  onEditComplete?: () => void;
  onCreated?: (entry: { type: 'create'; id: number }) => void;
}

type FormNotice = {
  tone: 'error' | 'success' | 'info';
  title: string;
  message: ReactNode;
};

export default function AddTransactionForm({
  onSuccess,
  onCancel,
  transactions = [],
  editTransaction,
  onEditComplete,
  onCreated,
}: AddTransactionFormProps) {
  const [form, setForm] = useState<FormState>({
    symbol: '',
    type: '',
    shares: '',
    price: '',
    date: new Date().toISOString().split('T')[0],
    notes: '',
    category: '',
    assetClass: 'equity',
    sector: '',
    fee: '',
    tax: '',
  });
  const [editId, setEditId] = useState<number | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [notice, setNotice] = useState<FormNotice | null>(null);
  const [importResult, setImportResult] = useState<TransactionImportResult | null>(null);
  const [importFileName, setImportFileName] = useState<string>('');
  const [createTransaction] = useCreateTransactionMutation();
  const [updateTransaction] = useUpdateTransactionMutation();
  const [importTransactions] = useImportTransactionsMutation();
  const inputRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const symbolFieldRef = useRef<HTMLDivElement>(null);
  const actualSymbolSet = new Set<string>();
  const actualSymbolStats = new Map<string, { count: number; latestDate: string }>();

  transactions.forEach((tx) => {
    const symbol = normalizeSymbolInput(tx.symbol);
    if (!symbol) return;
    actualSymbolSet.add(symbol);
    const current = actualSymbolStats.get(symbol);
    if (!current) {
      actualSymbolStats.set(symbol, { count: 1, latestDate: tx.date });
      return;
    }
    current.count += 1;
    if (tx.date > current.latestDate) current.latestDate = tx.date;
  });

  const actualSymbols = Array.from(actualSymbolStats.entries())
    .sort((a, b) => {
      if (b[1].count !== a[1].count) return b[1].count - a[1].count;
      if (b[1].latestDate !== a[1].latestDate) return b[1].latestDate.localeCompare(a[1].latestDate);
      return a[0].localeCompare(b[0]);
    })
    .map(([symbol]) => symbol);

  // Pre-fill form when editing
  useEffect(() => {
    if (editTransaction) {
      setForm({
        symbol: editTransaction.symbol,
        type: editTransaction.type,
        shares: String(editTransaction.shares),
        price: String(editTransaction.price),
        date: editTransaction.date,
        notes: editTransaction.notes ?? '',
        category: editTransaction.category ?? '',
        assetClass: editTransaction.asset_class ?? 'equity',
        sector: editTransaction.sector ?? '',
        fee: String(editTransaction.fee ?? ''),
        tax: String(editTransaction.tax ?? ''),
      });
      setEditId(editTransaction.id);
    }
  }, [editTransaction]);

  useEffect(() => {
    const handlePointerDown = (event: Event) => {
      if (symbolFieldRef.current && !symbolFieldRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };

    window.addEventListener('pointerdown', handlePointerDown);
    window.addEventListener('touchstart', handlePointerDown);
    return () => {
      window.removeEventListener('pointerdown', handlePointerDown);
      window.removeEventListener('touchstart', handlePointerDown);
    };
  }, []);

  const selectSuggestion = (sym: string) => {
    setNotice(null);
    setForm(f => ({ ...f, symbol: sym }));
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const updateSuggestions = (rawValue: string) => {
    const value = normalizeSymbolInput(rawValue);
    const rankedSuggestions = [
      ...actualSymbols,
      ...STOCK_SUGGESTIONS.filter((symbol) => !actualSymbolSet.has(symbol)),
    ];
    const filtered = rankedSuggestions
      .filter((symbol) => (value.length >= 1 ? symbol.includes(value) : true))
      .slice(0, 8);
    const combined = (
      value.length >= 1 && isSuggestableSymbol(value) && !filtered.includes(value)
        ? [value, ...filtered]
        : filtered
    ).slice(0, 8);
    setSuggestions(combined);
    setShowSuggestions(combined.length > 0);
  };

  const handleSymbolChange = (event: ChangeEvent<HTMLInputElement>) => {
    const value = normalizeSymbolInput(event.target.value);
    setNotice(null);
    setForm((f) => ({ ...f, symbol: value }));
    updateSuggestions(value);
  };

  const downloadTemplate = () => {
    const rows = [
      ['symbol', 'type', 'shares', 'price', 'date', 'notes', 'category', 'asset_class', 'sector', 'fee', 'tax'],
      ['AAPL', 'buy', '10', '150', '2026-06-20', '買入理由', 'long_term', 'equity', 'technology', '1', '0'],
      ['0050', 'buy', '100', '150', '2026-06-20', '台灣大盤配置', 'etf', 'equity', 'broad_market', '0', '0'],
      ['00679B', 'buy', '100', '30', '2026-06-20', '債券 ETF 配置', 'etf', 'bond', '', '0', '0'],
    ];
    const csv = rows.map(row => row.map(cell => `"${String(cell).replaceAll('"', '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'transactions_template.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const resetForm = () => {
    setForm({
      symbol: '',
      type: '',
      shares: '',
      price: '',
      date: new Date().toISOString().split('T')[0],
      notes: '',
      category: '',
      assetClass: 'equity',
      sector: '',
      fee: '',
      tax: '',
    });
    setEditId(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const symbol = form.symbol.trim().toUpperCase();
    const shares = parseDecimalInput(form.shares);
    const price = parseDecimalInput(form.price);
    const fee = form.fee.trim() ? parseDecimalInput(form.fee) : 0;
    const tax = form.tax.trim() ? parseDecimalInput(form.tax) : 0;
    const notes = form.notes.trim();
    const category = form.category || undefined;
    const assetClass = form.assetClass || undefined;
    const sector = form.assetClass === 'equity' ? form.sector || undefined : undefined;

    if (!symbol) {
      setNotice({ tone: 'error', title: isEditing ? '編輯失敗' : '新增失敗', message: '股票代號不可空' });
      return;
    }
    if (!form.type) {
      setNotice({ tone: 'error', title: isEditing ? '編輯失敗' : '新增失敗', message: '請先選擇交易類型' });
      return;
    }
    if (!Number.isFinite(shares) || shares <= 0) {
      setNotice({ tone: 'error', title: isEditing ? '編輯失敗' : '新增失敗', message: '股數必須大於 0' });
      return;
    }
    if (!Number.isFinite(price) || price <= 0) {
      setNotice({ tone: 'error', title: isEditing ? '編輯失敗' : '新增失敗', message: '價格必須大於 0' });
      return;
    }
    if (!Number.isFinite(fee) || fee < 0) {
      setNotice({ tone: 'error', title: isEditing ? '編輯失敗' : '新增失敗', message: '手續費不能小於 0' });
      return;
    }
    if (!Number.isFinite(tax) || tax < 0) {
      setNotice({ tone: 'error', title: isEditing ? '編輯失敗' : '新增失敗', message: '稅費不能小於 0' });
      return;
    }
    setNotice(null);

    const payload = {
      symbol,
      type: form.type as TransactionType,
      shares,
      price,
      date: form.date,
      notes: notes || undefined,
      category: category as TransactionCategory | undefined,
      asset_class: assetClass as AssetClass | undefined,
      sector: sector as Sector | undefined,
      fee,
      tax,
    };
    const promise = editId
      ? updateTransaction({ id: editId, data: payload }).unwrap()
      : createTransaction(payload).unwrap();

    promise.then((result) => {
      if (!editId && 'id' in result) {
        onCreated?.({ type: 'create', id: (result as { id: number }).id });
      }
      onSuccess?.();
      onEditComplete?.();
      setImportResult(null);
      const normalizedSymbol = 'symbol' in result ? result.symbol : symbol;
      const symbolMessage = normalizedSymbol !== symbol
        ? `${symbol} 已自動正規化為 ${normalizedSymbol}，交易已${isEditing ? '更新' : '新增'}。`
        : `${normalizedSymbol} 交易已${isEditing ? '更新' : '新增'}。`;
      setNotice({
        tone: 'success',
        title: isEditing ? '編輯完成' : '新增完成',
        message: symbolMessage,
      });
      resetForm();
    }).catch((err: Error) => setNotice({
      tone: 'error',
      title: isEditing ? '編輯失敗' : '新增失敗',
      message: err.message,
    }));
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportFileName(file.name);
    setNotice(null);
    setImportResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const result = await importTransactions(formData).unwrap();
      setImportResult(result);
      setNotice({
        tone: 'success',
        title: '匯入完成',
        message: `新增 ${result.created} 筆，略過 ${result.skipped} 筆。`,
      });
      onSuccess?.();
      if (fileRef.current) fileRef.current.value = '';
    } catch (err) {
      setNotice({ tone: 'error', title: '匯入失敗', message: err instanceof Error ? err.message : '匯入失敗' });
    }
  };

  const isEditing = editId !== null;
  const isTwdSymbol = /^\d+$/.test(form.symbol.trim());
  const formatMoney = (value: number) => (
    isTwdSymbol
      ? 'NT$' + Number(value).toLocaleString('zh-TW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : 'US$' + Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  );
  const summarySymbol = editTransaction?.symbol || form.symbol || 'N/A';
  const summaryType = editTransaction?.type || (form.type as TransactionType | '') || 'N/A';
  const summaryShares = editTransaction?.shares ?? (form.shares ? parseDecimalInput(form.shares) : null);
  const summaryPrice = editTransaction?.price ?? (form.price ? parseDecimalInput(form.price) : null);
  const summaryFee = editTransaction?.fee ?? (form.fee ? parseDecimalInput(form.fee) : 0);
  const summaryTax = editTransaction?.tax ?? (form.tax ? parseDecimalInput(form.tax) : 0);
  const summaryCategory = editTransaction?.category ?? (form.category || null);
  const summaryAssetClass = editTransaction?.asset_class ?? (form.assetClass || null);
  const summarySector = editTransaction?.sector ?? (form.sector || null);
  const summaryNotes = editTransaction?.notes ?? form.notes;
  const isEquityAssetClass = form.assetClass === 'equity';

  return (
    <div className="card relative overflow-visible p-4 sm:p-6 animate-fade-in" style={{ minWidth: 0 }}>
      <div className="flex items-center justify-between mb-4" style={{ minWidth: 0 }}>
        <h2 className="text-base sm:text-lg font-semibold flex items-center gap-2" style={{ minWidth: 0 }}>
          <Plus className="w-5 h-5 text-[var(--accent)]" />{isEditing ? '編輯交易' : '新增交易'}
        </h2>
        {onCancel && (
          <button onClick={onCancel} className="p-1 hover:bg-[var(--bg-secondary)] rounded">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      <div className="mb-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)]/40 p-4 space-y-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <FileSpreadsheet className="w-4 h-4 text-[var(--accent)]" />
          批次匯入
        </div>
        <div className="text-xs sm:text-sm opacity-70">
          支援 CSV 與 Excel (.xlsx / .xlsm)。欄位可用：symbol、type、shares、price、date，可選 notes、category、asset_class、sector、fee、tax。
        </div>
        <div className="text-xs opacity-60">
          台股商品若官方代號含尾碼，系統會依市場清單自動正規化；例如唯一對應的 `00631` 會改寫為 `00631L`。
        </div>
        <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx,.xlsm"
            onChange={handleImport}
            className="text-sm"
          />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="btn-secondary inline-flex items-center justify-center gap-2 text-sm"
          >
            <Upload className="w-4 h-4" />
            選擇檔案
          </button>
          <button
            type="button"
            onClick={downloadTemplate}
            className="btn-secondary inline-flex items-center justify-center gap-2 text-sm"
          >
            <FileSpreadsheet className="w-4 h-4" />
            下載範本
          </button>
        </div>
        {importFileName && (
          <div className="text-xs opacity-60">已選檔案：{importFileName}</div>
        )}
        {importResult && importResult.errors.length > 0 ? (
          <InlineNotice
            tone="info"
            title="匯入明細"
            message={(
              <div className="space-y-1 text-xs sm:text-sm">
                {importResult.errors.slice(0, 5).map((err, index) => (
                  <div key={index}>{err}</div>
                ))}
                {importResult.errors.length > 5 ? <div>還有 {importResult.errors.length - 5} 筆錯誤未顯示。</div> : null}
              </div>
            )}
            onDismiss={() => setImportResult(null)}
          />
        ) : null}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3 sm:space-y-4">
        {isEditing && (
          <div className="space-y-3">
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-300">
              修改後會重算持倉，並重新計算這檔股票的已實現損益。
            </div>
            <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)]/40 px-3 py-3 text-sm space-y-2">
              <div className="flex items-center justify-between gap-3">
                <div className="font-semibold">編輯前摘要</div>
                <div className="text-xs opacity-60">先確認這筆交易，再送出修改</div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 text-xs sm:text-sm">
                <div><span className="opacity-60">股票代號：</span>{summarySymbol}</div>
                <div><span className="opacity-60">交易類型：</span>{summaryType === 'buy' ? '買入' : summaryType === 'sell' ? '賣出' : 'N/A'}</div>
                <div><span className="opacity-60">股數：</span>{summaryShares ?? 'N/A'}</div>
                <div><span className="opacity-60">價格：</span>{summaryPrice != null ? formatMoney(Number(summaryPrice)) : 'N/A'}</div>
                <div><span className="opacity-60">手續費：</span>{formatMoney(Number(summaryFee))}</div>
                <div><span className="opacity-60">稅費：</span>{formatMoney(Number(summaryTax))}</div>
                <div><span className="opacity-60">日期：</span>{editTransaction?.date ?? form.date}</div>
                <div><span className="opacity-60">分類：</span>{summaryCategory ? CATEGORY_LABELS[summaryCategory as TransactionCategory] : '未分類'}</div>
                <div><span className="opacity-60">資產類別：</span>{summaryAssetClass ? ASSET_CLASS_LABELS[summaryAssetClass as AssetClass] : '未設定'}</div>
                <div><span className="opacity-60">產業：</span>{summarySector ? SECTOR_LABELS[summarySector as Sector] : '未設定'}</div>
              </div>
              {summaryNotes && (
                <div className="text-xs sm:text-sm">
                  <span className="opacity-60">備註：</span>
                  <span className="whitespace-pre-wrap">{summaryNotes}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {notice ? (
          <InlineNotice
            tone={notice.tone}
            title={notice.title}
            message={notice.message}
            onDismiss={() => setNotice(null)}
          />
        ) : null}

        <div ref={symbolFieldRef} className="relative z-20">
          <label className="block text-sm opacity-60 mb-1">股票代號</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 opacity-40" />
            <input
              ref={inputRef}
              value={form.symbol}
              onChange={handleSymbolChange}
              onFocus={() => updateSuggestions(form.symbol)}
              onClick={() => updateSuggestions(form.symbol)}
              placeholder="輸入代碼，如 0050、AAPL"
              className="input-field pl-10 pr-8"
              autoComplete="off"
              onInput={() => setNotice(null)}
              required
            />
            {form.symbol && (
              <button
                type="button"
                onClick={() => {
                  setNotice(null);
                  setForm(f => ({ ...f, symbol: '' }));
                  updateSuggestions('');
                  inputRef.current?.focus();
                }}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-[var(--bg-secondary)] rounded"
              >
                <X className="w-3 h-3 opacity-40" />
              </button>
            )}
          </div>
          {showSuggestions && suggestions.length > 0 && (
            <div className="mt-2 max-h-64 overflow-y-auto rounded-lg border border-[var(--border-color)] bg-[var(--card-bg)] shadow-lg sm:absolute sm:left-0 sm:right-0 sm:z-30 sm:mt-1">
              {suggestions.map(sym => (
                <button
                  key={sym}
                  type="button"
                  onTouchStart={(event) => {
                    event.preventDefault();
                    selectSuggestion(sym);
                  }}
                  onMouseDown={(event) => {
                    event.preventDefault();
                    selectSuggestion(sym);
                  }}
                  className="flex w-full items-center justify-between gap-3 px-4 py-2 text-left hover:bg-[var(--bg-secondary)]"
                >
                  <span className="font-mono text-sm">{sym}</span>
                  {actualSymbolSet.has(sym) ? (
                    <span className="rounded-full bg-[var(--accent)]/10 px-2 py-0.5 text-[10px] font-semibold text-[var(--accent)]">
                      已交易
                    </span>
                  ) : sym === normalizeSymbolInput(form.symbol) ? (
                    <span className="rounded-full bg-[var(--border-color)] px-2 py-0.5 text-[10px] font-semibold opacity-70">
                      直接使用
                    </span>
                  ) : null}
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <label className="block text-sm opacity-60 mb-1">交易類型</label>
          <div className="flex gap-2">
            {(['buy', 'sell'] as TransactionType[]).map(t => (
              <button
                key={t}
                type="button"
                onClick={() => {
                  setNotice(null);
                  setForm(f => ({ ...f, type: t }));
                }}
                className={`flex-1 py-2 rounded-lg font-medium transition-colors text-sm border ${
                  form.type === t
                    ? t === 'buy' ? 'bg-[var(--profit)] text-white border-[var(--profit)]' : 'bg-[var(--loss)] text-white border-[var(--loss)]'
                    : 'border-[var(--border-color)] opacity-50'
                }`}
              >
                {t === 'buy' ? '買入' : '賣出'}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm opacity-60 mb-1">交易分類</label>
          <select
            value={form.category}
            onChange={e => {
              setNotice(null);
              setForm(f => ({ ...f, category: e.target.value as TransactionCategory | '' }));
            }}
            className="input-field"
          >
            <option value="">未分類</option>
            {CATEGORY_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm opacity-60 mb-1">資產類別</label>
          <select
            value={form.assetClass}
            onChange={e => {
              setNotice(null);
              const nextAssetClass = e.target.value as AssetClass | '';
              setForm(f => ({ ...f, assetClass: nextAssetClass, sector: nextAssetClass === 'equity' ? f.sector : '' }));
            }}
            className="input-field"
          >
            <option value="">未設定</option>
            {ASSET_CLASS_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm opacity-60 mb-1">產業 / ETF類型</label>
          <select
            value={isEquityAssetClass ? form.sector : ''}
            onChange={e => {
              setNotice(null);
              setForm(f => ({ ...f, sector: e.target.value as Sector | '' }));
            }}
            className="input-field"
            disabled={!isEquityAssetClass}
          >
            <option value="">未設定</option>
            {SECTOR_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <div className="mt-1 text-xs opacity-60">
            {isEquityAssetClass ? '個股填產業，ETF 可填大盤ETF / 高股息ETF / 主題ETF。' : '只有股票類資產可設定產業。'}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:gap-4">
          <div>
            <label className="block text-sm opacity-60 mb-1">股數</label>
            <input
              type="text"
              inputMode="decimal"
              autoComplete="off"
              value={form.shares}
              onChange={e => {
                setNotice(null);
                setForm(f => ({ ...f, shares: normalizeDecimalInput(e.target.value) }));
              }}
              className="input-field"
              placeholder="例如 10000 或 10.5"
              required
            />
          </div>
          <div>
            <label className="block text-sm opacity-60 mb-1">價格</label>
            <input
              type="text"
              inputMode="decimal"
              autoComplete="off"
              value={form.price}
              onChange={e => {
                setNotice(null);
                setForm(f => ({ ...f, price: normalizeDecimalInput(e.target.value) }));
              }}
              className="input-field"
              placeholder="例如 29.3"
              required
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:gap-4">
          <div>
            <label className="block text-sm opacity-60 mb-1">手續費</label>
            <input
              type="text"
              inputMode="decimal"
              autoComplete="off"
              value={form.fee}
              onChange={e => {
                setNotice(null);
                setForm(f => ({ ...f, fee: normalizeDecimalInput(e.target.value) }));
              }}
              className="input-field"
              placeholder="0"
            />
          </div>
          <div>
            <label className="block text-sm opacity-60 mb-1">稅費</label>
            <input
              type="text"
              inputMode="decimal"
              autoComplete="off"
              value={form.tax}
              onChange={e => {
                setNotice(null);
                setForm(f => ({ ...f, tax: normalizeDecimalInput(e.target.value) }));
              }}
              className="input-field"
              placeholder="0"
            />
          </div>
        </div>

        <div style={{ minWidth: 0 }}>
          <label className="block text-sm opacity-60 mb-1">交易日期</label>
          <DatePicker
            value={form.date}
            onChange={val => {
              setNotice(null);
              setForm(f => ({ ...f, date: val }));
            }}
          />
        </div>

        <div>
          <label className="block text-sm opacity-60 mb-1">備註</label>
          <textarea
            value={form.notes}
            onChange={e => {
              setNotice(null);
              setForm(f => ({ ...f, notes: e.target.value }));
            }}
            className="input-field min-h-[100px]"
            placeholder="可記錄買入理由、策略、交易紀錄、心得等"
          />
        </div>

        {form.shares && form.price && Number.isFinite(parseDecimalInput(form.shares)) && Number.isFinite(parseDecimalInput(form.price)) && (
          <div className="text-sm opacity-60 text-right">
            總金額：${(parseDecimalInput(form.shares) * parseDecimalInput(form.price)).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            {form.category ? ` · ${CATEGORY_LABELS[form.category as TransactionCategory]}` : ''}
            {form.assetClass ? ` · ${ASSET_CLASS_LABELS[form.assetClass as AssetClass]}` : ''}
            {isEquityAssetClass && form.sector ? ` · ${SECTOR_LABELS[form.sector as Sector]}` : ''}
          </div>
        )}

        <button type="submit" className="btn-primary w-full text-sm sm:text-base">
          送出交易
        </button>
      </form>
    </div>
  );
}
