import { useState, useEffect, useRef } from 'react';
import { useGetAccountsQuery, useCreateTransactionMutation, useUpdateTransactionMutation } from '../store/apiSlice';
import { Search, X, Plus } from 'lucide-react';
import DatePicker from './DatePicker';
import type { TransactionType } from '../types';

const STOCK_SUGGESTIONS = [
  'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'INTC', 'CSCO',
  'AMAT', 'ASML', 'LRCX', 'MU', 'SNPS', 'CDNS', 'PANW', 'CRWD', 'NET', 'ZS',
  'SPY', 'QQQ', 'VOO', 'VTI', 'IWM', 'VEA', 'VWO', 'BND', 'AGG', 'GLD', 'TLT', 'LQD',
  '0050', '0056', '006208', '00878', '00713', '00881', '00919', '00929',
  '2330', '2317', '2303', '2454', '2308', '2377', '2382', '2327', '2344',
  'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'C', 'AXP',
  'CAT', 'DE', 'BA', 'HON', 'UNP', 'RTX', 'LMT', 'NOC',
  'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD',
  'COST', 'WMT', 'HD', 'LOW', 'TGT', 'AMZN',
];

interface FormState {
  account_id: string;
  symbol: string;
  type: TransactionType | '';
  shares: string;
  price: string;
  date: string;
}

interface AddTransactionFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
  editTransaction?: {
    id: number;
    account_id: number;
    symbol: string;
    type: TransactionType;
    shares: number;
    price: number;
    date: string;
  };
  onEditComplete?: () => void;
  onCreated?: (entry: { type: 'create'; id: number }) => void;
}

export default function AddTransactionForm({
  onSuccess,
  onCancel,
  editTransaction,
  onEditComplete,
  onCreated,
}: AddTransactionFormProps) {
  const [form, setForm] = useState<FormState>({
    account_id: '',
    symbol: '',
    type: '',
    shares: '',
    price: '',
    date: new Date().toISOString().split('T')[0],
  });
  const [editId, setEditId] = useState<number | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: accounts = [] } = useGetAccountsQuery(undefined);
  const [createTransaction] = useCreateTransactionMutation();
  const [updateTransaction] = useUpdateTransactionMutation();

  // Pre-fill form when editing
  useEffect(() => {
    if (editTransaction) {
      setForm({
        account_id: String(editTransaction.account_id),
        symbol: editTransaction.symbol,
        type: editTransaction.type,
        shares: String(editTransaction.shares),
        price: String(editTransaction.price),
        date: editTransaction.date,
      });
      setEditId(editTransaction.id);
    }
  }, [editTransaction]);

  useEffect(() => {
    if (form.symbol.length >= 1) {
      const search = form.symbol.toUpperCase();
      const filtered = STOCK_SUGGESTIONS.filter(s => s.includes(search)).slice(0, 8);
      setSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  }, [form.symbol]);

  const selectSuggestion = (sym: string) => {
    setForm(f => ({ ...f, symbol: sym }));
    setShowSuggestions(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      account_id: Number(form.account_id),
      symbol: form.symbol.toUpperCase(),
      type: form.type as TransactionType,
      shares: Number(form.shares),
      price: Number(form.price),
      date: form.date,
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
      setForm({
        account_id: form.account_id,
        symbol: '',
        type: '',
        shares: '',
        price: '',
        date: new Date().toISOString().split('T')[0],
      });
      setEditId(null);
    }).catch((err: Error) => alert(err.message));
  };

  return (
    <div className="card p-4 sm:p-6 animate-fade-in" style={{ minWidth: 0 }}>
      <div className="flex items-center justify-between mb-4" style={{ minWidth: 0 }}>
        <h2 className="text-base sm:text-lg font-semibold flex items-center gap-2" style={{ minWidth: 0 }}>
          <Plus className="w-5 h-5 text-blue-500" />{editId ? '編輯交易' : '新增交易'}
        </h2>
        {onCancel && (
          <button onClick={onCancel} className="p-1 hover:bg-[var(--bg-secondary)] rounded">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3 sm:space-y-4">
        <div>
          <label className="block text-sm opacity-60 mb-1">券商帳號</label>
          <select
            value={form.account_id}
            onChange={e => setForm(f => ({ ...f, account_id: e.target.value }))}
            className="input-field"
            required
          >
            <option value="">選擇帳號</option>
            {accounts.map(a => (
              <option key={a.id} value={a.id}>{a.name} ({a.type})</option>
            ))}
          </select>
        </div>

        <div className="relative">
          <label className="block text-sm opacity-60 mb-1">股票代號</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 opacity-40" />
            <input
              ref={inputRef}
              value={form.symbol}
              onChange={e => setForm(f => ({ ...f, symbol: e.target.value.toUpperCase() }))}
              onFocus={() => {
                if (form.symbol.length >= 1) {
                  const search = form.symbol.toUpperCase();
                  const filtered = STOCK_SUGGESTIONS.filter(s => s.includes(search)).slice(0, 8);
                  setSuggestions(filtered);
                  setShowSuggestions(filtered.length > 0);
                } else {
                  setSuggestions(STOCK_SUGGESTIONS.slice(0, 8));
                  setShowSuggestions(true);
                }
              }}
              placeholder="輸入代碼，如 0050、AAPL"
              className="input-field pl-10 pr-8"
              autoComplete="off"
              required
            />
            {form.symbol && (
              <button
                type="button"
                onClick={() => setForm(f => ({ ...f, symbol: '' }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-[var(--bg-secondary)] rounded"
              >
                <X className="w-3 h-3 opacity-40" />
              </button>
            )}
          </div>
          {showSuggestions && suggestions.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg shadow-lg overflow-hidden">
              {suggestions.map(sym => (
                <button
                  key={sym}
                  type="button"
                  onClick={() => selectSuggestion(sym)}
                  className="w-full px-4 py-2 text-left hover:bg-[var(--bg-secondary)] font-mono text-sm"
                >
                  {sym}
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
                onClick={() => setForm(f => ({ ...f, type: t }))}
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

        <div className="grid grid-cols-2 gap-3 sm:gap-4">
          <div>
            <label className="block text-sm opacity-60 mb-1">股數</label>
            <input
              type="number"
              step="0.0001"
              value={form.shares}
              onChange={e => setForm(f => ({ ...f, shares: e.target.value }))}
              className="input-field"
              required
            />
          </div>
          <div>
            <label className="block text-sm opacity-60 mb-1">價格</label>
            <input
              type="number"
              step="0.01"
              value={form.price}
              onChange={e => setForm(f => ({ ...f, price: e.target.value }))}
              className="input-field"
              required
            />
          </div>
        </div>

        <div style={{ minWidth: 0 }}>
          <label className="block text-sm opacity-60 mb-1">交易日期</label>
          <DatePicker value={form.date} onChange={val => setForm(f => ({ ...f, date: val }))} />
        </div>

        {form.shares && form.price && (
          <div className="text-sm opacity-60 text-right">
            總金額：${(Number(form.shares) * Number(form.price)).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        )}

        <button type="submit" className="btn-primary w-full text-sm sm:text-base">
          送出交易
        </button>
      </form>
    </div>
  );
}