import { useEffect, useMemo, useRef, useState } from 'react';
import { RefreshCw, Search, Trash2, X } from 'lucide-react';
import DatePicker from '../DatePicker';
import { EmptyState, SemanticBadge } from '../UIState';
import { ASSET_CLASS_LABELS, formatCurrency, formatDateMMMDDYY, formatShares, SECTOR_LABELS, TRANSACTION_CATEGORY_LABELS, TRANSACTION_CATEGORY_OPTIONS } from './shared';
import type { Sector, Transaction, TransactionCategory, UndoEntry } from '../../types';

interface TransactionsSectionProps {
  availableUndoStack: UndoEntry[];
  clearEditTransaction: () => void;
  clearTransactionFilters: () => void;
  currentHoldingSymbols: string[];
  handleEdit: (tx: Transaction) => void;
  handleUndoLast: () => Promise<void>;
  lastUndoEntry?: UndoEntry;
  lossTransactionCount: number;
  navigateToNew: () => void;
  profitTransactionCount: number;
  requestDeleteTransaction: (tx: Transaction) => void;
  setTxCategoryFilter: (value: 'all' | TransactionCategory) => void;
  setTxFromDate: (value: string) => void;
  setTxGainFilter: (value: 'all' | 'profit' | 'loss') => void;
  setTxQuery: (value: string) => void;
  setTxToDate: (value: string) => void;
  setTxTypeFilter: (value: 'all' | 'buy' | 'sell') => void;
  transactions: Transaction[];
  txCategoryFilter: 'all' | TransactionCategory;
  txFromDate: string;
  txGainFilter: 'all' | 'profit' | 'loss';
  txQuery: string;
  txToDate: string;
  txTypeFilter: 'all' | 'buy' | 'sell';
  visibleTransactions: Transaction[];
}

export default function TransactionsSection({
  availableUndoStack,
  clearEditTransaction,
  clearTransactionFilters,
  currentHoldingSymbols,
  handleEdit,
  handleUndoLast,
  lastUndoEntry,
  lossTransactionCount,
  navigateToNew,
  profitTransactionCount,
  requestDeleteTransaction,
  setTxCategoryFilter,
  setTxFromDate,
  setTxGainFilter,
  setTxQuery,
  setTxToDate,
  setTxTypeFilter,
  transactions,
  txCategoryFilter,
  txFromDate,
  txGainFilter,
  txQuery,
  txToDate,
  txTypeFilter,
  visibleTransactions,
}: TransactionsSectionProps) {
  const [showQuerySuggestions, setShowQuerySuggestions] = useState(false);
  const queryFieldRef = useRef<HTMLDivElement>(null);

  const holdingSymbolSet = useMemo(
    () => new Set(currentHoldingSymbols.map((symbol) => symbol.trim().toUpperCase()).filter(Boolean)),
    [currentHoldingSymbols],
  );
  const actualSymbolSet = useMemo(() => new Set(transactions.map((tx) => tx.symbol.trim().toUpperCase()).filter(Boolean)), [transactions]);
  const rankedSymbols = useMemo(() => {
    const stats = new Map<string, { count: number; latestDate: string }>();
    transactions.forEach((tx) => {
      const symbol = tx.symbol.trim().toUpperCase();
      if (!symbol) return;
      const current = stats.get(symbol);
      if (!current) {
        stats.set(symbol, { count: 1, latestDate: tx.date });
        return;
      }
      current.count += 1;
      if (tx.date > current.latestDate) current.latestDate = tx.date;
    });

    const actualSymbols = Array.from(stats.entries())
      .sort((a, b) => {
        if (b[1].count !== a[1].count) return b[1].count - a[1].count;
        if (b[1].latestDate !== a[1].latestDate) return b[1].latestDate.localeCompare(a[1].latestDate);
        return a[0].localeCompare(b[0]);
      })
      .map(([symbol]) => symbol);

    const activeHoldings = actualSymbols.filter((symbol) => holdingSymbolSet.has(symbol));
    const closedSymbols = actualSymbols.filter((symbol) => !holdingSymbolSet.has(symbol));

    return [...activeHoldings, ...closedSymbols];
  }, [holdingSymbolSet, transactions]);

  const querySuggestions = useMemo(() => {
    const search = txQuery.trim().toUpperCase();
    return rankedSymbols
      .filter((symbol) => (search ? symbol.includes(search) : true))
      .slice(0, 8);
  }, [rankedSymbols, txQuery]);

  useEffect(() => {
    const handlePointerDown = (event: Event) => {
      if (queryFieldRef.current && !queryFieldRef.current.contains(event.target as Node)) {
        setShowQuerySuggestions(false);
      }
    };

    window.addEventListener('pointerdown', handlePointerDown);
    window.addEventListener('touchstart', handlePointerDown);
    return () => {
      window.removeEventListener('pointerdown', handlePointerDown);
      window.removeEventListener('touchstart', handlePointerDown);
    };
  }, []);

  const categoryStats = (Object.keys(TRANSACTION_CATEGORY_LABELS) as TransactionCategory[])
    .map((category) => {
      const rows = transactions.filter((tx) => tx.category === category);
      return {
        category,
        label: TRANSACTION_CATEGORY_LABELS[category],
        tradeCount: rows.length,
        grossAmount: rows.reduce((sum, tx) => sum + (Number(tx.shares) * Number(tx.price)), 0),
        realizedGain: rows.reduce((sum, tx) => sum + Number(tx.realized_gain ?? 0), 0),
      };
    })
    .filter((item) => item.tradeCount > 0);

  return (
    <div className="card overflow-hidden animate-fade-in">
      <div className="space-y-3 border-b border-[var(--border-color)] px-3 py-3 sm:px-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="text-sm font-semibold">交易工作區</div>
            <div className="mt-1 text-xs opacity-60">列表用來查找與編輯，右上角按鈕可直接切到新增交易。</div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={clearTransactionFilters}
              className="btn-secondary px-3 py-1.5 text-xs"
              disabled={!txQuery && txTypeFilter === 'all' && txCategoryFilter === 'all' && txGainFilter === 'all' && !txFromDate && !txToDate}
            >
              清除篩選
            </button>
            <button
              onClick={() => {
                clearEditTransaction();
                navigateToNew();
              }}
              className="btn-primary px-3 py-1.5 text-xs"
            >
              新增交易
            </button>
            {availableUndoStack.length > 0 ? (
              <button
                onClick={() => { void handleUndoLast(); }}
                className="rounded border border-[var(--border-color)] px-2 py-1.5 text-xs opacity-70 transition-colors hover:bg-[var(--bg-secondary)] hover:opacity-100"
              >
                <span className="inline-flex items-center gap-1">
                  <RefreshCw className="h-3 w-3" /> 復原
                </span>
              </button>
            ) : null}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <SemanticBadge tone="info">總筆數 {transactions.length}</SemanticBadge>
          <SemanticBadge tone="success">獲利 {profitTransactionCount}</SemanticBadge>
          <SemanticBadge tone="error">虧損 {lossTransactionCount}</SemanticBadge>
          <SemanticBadge tone="neutral">顯示 {visibleTransactions.length} 筆</SemanticBadge>
        </div>
      </div>

      <div className="space-y-3 border-b border-[var(--border-color)] px-3 py-3 sm:px-4">
        {lastUndoEntry ? (
          <div className="flex flex-col gap-2 rounded-lg border border-[var(--accent)]/20 bg-[var(--accent)]/8 px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between">
            <div className="opacity-80">
              {lastUndoEntry.type === 'delete'
                ? `已刪除 ${lastUndoEntry.transaction.symbol}，${Math.max(0, Math.ceil((lastUndoEntry.expiresAt - Date.now()) / 1000))} 秒內可復原`
                : '剛新增交易，可復原'}
            </div>
            <button type="button" onClick={() => { void handleUndoLast(); }} className="btn-secondary px-3 py-1 text-xs">
              立即復原
            </button>
          </div>
        ) : null}

        {categoryStats.length > 0 ? (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-5">
            {categoryStats.map((stat) => {
              const isGainPositive = stat.realizedGain >= 0;
              const formatMoney = (value: number) => `NT$${Number(value).toLocaleString('zh-TW', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
              return (
                <div key={stat.category} className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)]/40 px-3 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-semibold">{stat.label}</div>
                    <div className="text-xs opacity-60">{stat.tradeCount} 筆</div>
                  </div>
                  <div className="mt-2 text-xs opacity-70">成交額 {formatMoney(stat.grossAmount)}</div>
                  <div className={`mt-1 text-sm font-semibold ${isGainPositive ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                    已實現損益 {isGainPositive ? '+' : ''}{formatMoney(Math.abs(stat.realizedGain))}
                  </div>
                </div>
              );
            })}
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4">
          <div ref={queryFieldRef} className="relative min-w-0">
            <Search className="pointer-events-none absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              value={txQuery}
              onChange={(e) => {
                setTxQuery(e.target.value.toUpperCase());
                setShowQuerySuggestions(true);
              }}
              onFocus={() => setShowQuerySuggestions(true)}
              onClick={() => setShowQuerySuggestions(true)}
              className="input-field min-w-0 pl-10 pr-9"
              placeholder="搜尋股票代號"
              autoComplete="off"
            />
            {txQuery ? (
              <button
                type="button"
                onClick={() => {
                  setTxQuery('');
                  setShowQuerySuggestions(true);
                }}
                className="absolute right-3 top-1/2 z-10 -translate-y-1/2 rounded p-1 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)]"
                aria-label="清除商品搜尋"
              >
                <X className="h-3 w-3" />
              </button>
            ) : null}
            {showQuerySuggestions && querySuggestions.length > 0 ? (
              <div className="mt-2 max-h-64 overflow-y-auto rounded-lg border border-[var(--border-color)] bg-[var(--card-bg)] shadow-lg sm:absolute sm:left-0 sm:right-0 sm:z-30 sm:mt-1">
                {querySuggestions.map((symbol) => (
                  <button
                    key={symbol}
                    type="button"
                    onTouchStart={(event) => {
                      event.preventDefault();
                      setTxQuery(symbol);
                      setShowQuerySuggestions(false);
                    }}
                    onMouseDown={(event) => {
                      event.preventDefault();
                      setTxQuery(symbol);
                      setShowQuerySuggestions(false);
                    }}
                    className="flex w-full items-center justify-between gap-3 px-4 py-2 text-left hover:bg-[var(--bg-secondary)]"
                  >
                    <span className="font-mono text-sm">{symbol}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        holdingSymbolSet.has(symbol)
                          ? 'bg-[var(--accent)]/10 text-[var(--accent)]'
                          : 'bg-[var(--text-muted)]/12 text-[var(--text-secondary)]'
                      }`}
                    >
                      {holdingSymbolSet.has(symbol) ? '持倉中' : '已清倉'}
                    </span>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <select value={txTypeFilter} onChange={(e) => setTxTypeFilter(e.target.value as 'all' | 'buy' | 'sell')} className="input-field min-w-0">
            <option value="all">全部買賣</option>
            <option value="buy">買入</option>
            <option value="sell">賣出</option>
          </select>
          <select value={txCategoryFilter} onChange={(e) => setTxCategoryFilter(e.target.value as 'all' | TransactionCategory)} className="input-field min-w-0">
            {TRANSACTION_CATEGORY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <select value={txGainFilter} onChange={(e) => setTxGainFilter(e.target.value as 'all' | 'profit' | 'loss')} className="input-field min-w-0">
            <option value="all">全部損益</option>
            <option value="profit">獲利</option>
            <option value="loss">虧損</option>
          </select>
          <div className="grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 xl:col-span-4">
            <div className="min-w-0">
              <label className="mb-1 block text-xs text-[var(--text-muted)]">起始日期</label>
              <DatePicker value={txFromDate} onChange={setTxFromDate} allowClear placeholderLabel="年" yearRange={12} />
            </div>
            <div className="min-w-0">
              <label className="mb-1 block text-xs text-[var(--text-muted)]">結束日期</label>
              <DatePicker value={txToDate} onChange={setTxToDate} allowClear placeholderLabel="年" yearRange={12} />
            </div>
          </div>
        </div>
      </div>

      {transactions.length === 0 ? (
        <div className="p-6 sm:p-8">
          <EmptyState title="尚無交易紀錄" description="先新增一筆交易，這裡才會開始累積明細。" />
        </div>
      ) : visibleTransactions.length === 0 ? (
        <div className="p-6 sm:p-8">
          <EmptyState title="沒有符合篩選條件的交易" description="請調整搜尋、日期或損益篩選條件。" />
        </div>
      ) : (
        <div className="space-y-2 p-3 sm:space-y-0 sm:divide-y sm:divide-[var(--border-color)] sm:p-0">
          {visibleTransactions.map((tx) => {
            const dateFormatted = formatDateMMMDDYY(tx.date);
            const categoryLabel = tx.category ? TRANSACTION_CATEGORY_LABELS[tx.category] : '';
            const assetClassLabel = tx.asset_class ? ASSET_CLASS_LABELS[tx.asset_class] : '';
            const sectorLabel = tx.sector ? SECTOR_LABELS[tx.sector as Sector] : '';
            const isTwdSymbol = /^\d+$/.test(tx.symbol);
            const formatMoney = (value: number) => (
              isTwdSymbol
                ? `NT$${Number(value).toLocaleString('zh-TW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                : formatCurrency(value)
            );

            return (
              <div
                key={tx.id}
                onClick={() => handleEdit(tx)}
                className="group relative cursor-pointer rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)]/35 px-3 py-3 transition-colors hover:bg-[var(--bg-secondary)]/60 sm:rounded-none sm:border-0 sm:bg-transparent sm:px-4"
              >
                <div className="flex flex-col gap-2 pr-8 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-wrap items-center gap-2 text-xs opacity-75">
                    <span className="font-mono">{dateFormatted}</span>
                    {categoryLabel ? <SemanticBadge tone="neutral" className="text-[10px]">{categoryLabel}</SemanticBadge> : null}
                    {assetClassLabel ? <SemanticBadge tone="info" className="text-[10px]">{assetClassLabel}</SemanticBadge> : null}
                    {sectorLabel ? <SemanticBadge tone="neutral" className="text-[10px]">{sectorLabel}</SemanticBadge> : null}
                  </div>
                  <div className="hidden text-[10px] uppercase tracking-wide opacity-40 sm:block">點擊可編輯</div>
                </div>

                <div className="mt-2 flex flex-col gap-2 pr-8 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold">{tx.symbol}</span>
                    <SemanticBadge tone={tx.type === 'buy' ? 'success' : 'error'} className="text-[10px]">
                      {tx.type === 'buy' ? '買入' : '賣出'}
                    </SemanticBadge>
                  </div>
                  <div className="text-left text-sm font-semibold sm:text-right">
                    {formatShares(tx.shares)} × {formatMoney(tx.price)} = {formatMoney(tx.shares * tx.price)}
                  </div>
                </div>

                {(tx.notes || tx.fee || tx.tax) ? (
                  <div className="mt-2 space-y-1 pr-8 text-xs opacity-60">
                    {tx.notes ? <div className="line-clamp-2">備註：{tx.notes}</div> : null}
                    <div className="flex flex-wrap gap-x-3 gap-y-1">
                      <span>{`手續費 ${formatMoney(Number(tx.fee ?? 0))}`}</span>
                      <span>{`稅費 ${formatMoney(Number(tx.tax ?? 0))}`}</span>
                      <span>{`已實現損益 ${formatMoney(Number(tx.realized_gain ?? 0))}`}</span>
                    </div>
                  </div>
                ) : null}

                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    requestDeleteTransaction(tx);
                  }}
                  className="absolute right-3 top-3 text-[var(--error)] opacity-70 transition-all hover:!opacity-100 sm:top-1/2 sm:-translate-y-1/2 sm:opacity-0 sm:group-hover:opacity-60"
                  title="刪除"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
