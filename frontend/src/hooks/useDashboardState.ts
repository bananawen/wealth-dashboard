import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  useCreateTransactionMutation,
  useDeleteTransactionMutation,
  useGetComputedHoldingsQuery,
  useGetPerformanceQuery,
  useGetPortfolioSummaryQuery,
  useGetTransactionsQuery,
  useGetVersionQuery,
} from '../store/apiSlice';
import type { ComputedHolding, Transaction, TransactionCategory, UndoEntry } from '../types';
import type { HoldingsSortKey, SortDirection } from '../types/dashboard';

type DashboardNotice = {
  message: string;
  tone: 'error' | 'success' | 'info';
  title?: string;
};

const PRICE_STATUS_ORDER: Record<NonNullable<ComputedHolding['price_status']>, number> = {
  live: 0,
  estimated: 1,
  missing: 2,
};

const HOLDINGS_SORT_LABELS: Record<HoldingsSortKey, string> = {
  cost: '成本',
  market_value: '市值',
  gain: '損益',
  gain_pct: '報酬率',
  shares: '股數',
  price: '現價',
  symbol: '代號',
};

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
    const json = atob(normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '='));
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function toLocalDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function getRelativeDateRange(days: number) {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - (days - 1));
  return {
    start: toLocalDateInputValue(start),
    end: toLocalDateInputValue(end),
  };
}

export function useDashboardState() {
  const defaultTransactionDateRange = getRelativeDateRange(30);
  const navigate = useNavigate();
  const tokenPayload = typeof window !== 'undefined'
    ? decodeJwtPayload(localStorage.getItem('token') ?? '')
    : null;
  const isAdmin = tokenPayload ? (!('role' in tokenPayload) || tokenPayload.role === 'admin') : false;
  const { data: summary } = useGetPortfolioSummaryQuery(undefined);
  const { data: computedHoldings = [] } = useGetComputedHoldingsQuery(undefined);
  const { data: transactions = [] } = useGetTransactionsQuery(undefined);
  const { data: versionInfo } = useGetVersionQuery(undefined, { skip: !isAdmin });
  const [performanceRange, setPerformanceRange] = useState<'today' | 'week' | 'month' | 'year' | 'all'>('all');
  const { data: performance } = useGetPerformanceQuery({ range: performanceRange });

  const [undoStack, setUndoStack] = useState<UndoEntry[]>([]);
  const [editTransaction, setEditTransaction] = useState<Transaction | null>(null);
  const [pendingDeleteTransaction, setPendingDeleteTransaction] = useState<Transaction | null>(null);
  const [notice, setNotice] = useState<DashboardNotice | null>(null);
  const [txQuery, setTxQuery] = useState('');
  const [txTypeFilter, setTxTypeFilter] = useState<'all' | 'buy' | 'sell'>('all');
  const [txCategoryFilter, setTxCategoryFilter] = useState<'all' | TransactionCategory>('all');
  const [txGainFilter, setTxGainFilter] = useState<'all' | 'profit' | 'loss'>('all');
  const [txFromDate, setTxFromDate] = useState(() => defaultTransactionDateRange.start);
  const [txToDate, setTxToDate] = useState(() => defaultTransactionDateRange.end);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [holdingsSortKey, setHoldingsSortKey] = useState<HoldingsSortKey>('market_value');
  const [holdingsSortDirection, setHoldingsSortDirection] = useState<SortDirection>('desc');

  const [createTransaction] = useCreateTransactionMutation();
  const [deleteTransaction] = useDeleteTransactionMutation();

  const navigateToAdmin = () => {
    window.location.href = '/admin';
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  const handleEdit = (tx: Transaction) => {
    setEditTransaction(tx);
    navigate('/transactions/new');
  };

  const requestDeleteTransaction = useCallback((tx: Transaction) => {
    setPendingDeleteTransaction(tx);
  }, []);

  const cancelDeleteTransaction = useCallback(() => {
    setPendingDeleteTransaction(null);
  }, []);

  const confirmDeleteTransaction = useCallback(async () => {
    if (!pendingDeleteTransaction) return;
    const tx = pendingDeleteTransaction;
    setPendingDeleteTransaction(null);
    try {
      const deleted = await deleteTransaction(tx.id).unwrap();
      setUndoStack((stack) => [...stack, {
        type: 'delete',
        transaction: deleted,
        expiresAt: Date.now() + 120_000,
      }]);
      setNotice({ tone: 'success', title: '已刪除', message: `${deleted.symbol} 已移除，可在 120 秒內復原。` });
    } catch (err) {
      setNotice({ tone: 'error', title: '刪除失敗', message: err instanceof Error ? err.message : 'Failed' });
    }
  }, [deleteTransaction, pendingDeleteTransaction]);

  const availableUndoStack = undoStack.filter((entry) => entry.type === 'create' || entry.expiresAt > Date.now());
  const lastUndoEntry = availableUndoStack[availableUndoStack.length - 1];

  const handleUndoLast = useCallback(async () => {
    if (!lastUndoEntry) return;
    try {
      if (lastUndoEntry.type === 'create') {
        await deleteTransaction(lastUndoEntry.id).unwrap();
      } else {
        const tx = lastUndoEntry.transaction;
        await createTransaction({
          symbol: tx.symbol,
          type: tx.type,
          shares: tx.shares,
          price: tx.price,
          date: tx.date,
          notes: tx.notes ?? undefined,
          category: tx.category ?? undefined,
          asset_class: tx.asset_class ?? undefined,
          fee: tx.fee ?? 0,
          tax: tx.tax ?? 0,
        }).unwrap();
      }
      setUndoStack((stack) => stack.filter((entry) => entry !== lastUndoEntry));
      setNotice({
        tone: 'success',
        title: '已復原',
        message: lastUndoEntry.type === 'create'
          ? '已撤回最後新增的交易。'
          : `已復原 ${lastUndoEntry.transaction.symbol} 的刪除操作。`,
      });
    } catch (err) {
      setNotice({ tone: 'error', title: '復原失敗', message: err instanceof Error ? err.message : 'Undo failed' });
    }
  }, [createTransaction, deleteTransaction, lastUndoEntry]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && availableUndoStack.length > 0) {
        e.preventDefault();
        void handleUndoLast();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [availableUndoStack.length, handleUndoLast]);

  const visibleTransactions = transactions.filter((tx) => {
    const query = txQuery.trim().toUpperCase();
    const matchQuery = !query || tx.symbol.toUpperCase().includes(query);
    const matchType = txTypeFilter === 'all' || tx.type === txTypeFilter;
    const matchCategory = txCategoryFilter === 'all' || tx.category === txCategoryFilter;
    const txDate = tx.date.slice(0, 10);
    const matchFrom = !txFromDate || txDate >= txFromDate;
    const matchTo = !txToDate || txDate <= txToDate;
    const gain = Number(tx.realized_gain ?? 0);
    const matchGain =
      txGainFilter === 'all' ||
      (txGainFilter === 'profit' && gain > 0) ||
      (txGainFilter === 'loss' && gain < 0);
    return matchQuery && matchType && matchCategory && matchFrom && matchTo && matchGain;
  });

  const profitTransactionCount = transactions.filter((tx) => Number(tx.realized_gain ?? 0) > 0).length;
  const lossTransactionCount = transactions.filter((tx) => Number(tx.realized_gain ?? 0) < 0).length;

  const clearTransactionFilters = () => {
    setTxQuery('');
    setTxTypeFilter('all');
    setTxCategoryFilter('all');
    setTxGainFilter('all');
    const nextRange = getRelativeDateRange(30);
    setTxFromDate(nextRange.start);
    setTxToDate(nextRange.end);
  };

  const holdingsForDisplay = [...computedHoldings].sort((a, b) => {
    const direction = holdingsSortDirection === 'asc' ? 1 : -1;
    const aMarketValue = Number(a.market_value_twd ?? a.market_value ?? 0);
    const bMarketValue = Number(b.market_value_twd ?? b.market_value ?? 0);
    const aCost = Number(a.total_cost_twd ?? a.total_cost ?? 0);
    const bCost = Number(b.total_cost_twd ?? b.total_cost ?? 0);
    const aGain = Number(a.unrealized_gain_twd ?? a.unrealized_gain ?? 0);
    const bGain = Number(b.unrealized_gain_twd ?? b.unrealized_gain ?? 0);
    const aGainPct = Number(a.unrealized_pct ?? 0);
    const bGainPct = Number(b.unrealized_pct ?? 0);
    const aShares = Number(a.shares ?? 0);
    const bShares = Number(b.shares ?? 0);
    const aPrice = Number(a.current_price_twd ?? a.current_price ?? 0);
    const bPrice = Number(b.current_price_twd ?? b.current_price ?? 0);

    switch (holdingsSortKey) {
      case 'cost':
        return (bCost - aCost) * direction;
      case 'market_value':
        return (bMarketValue - aMarketValue) * direction;
      case 'gain':
        return (bGain - aGain) * direction;
      case 'gain_pct':
        return (bGainPct - aGainPct) * direction;
      case 'shares':
        return (bShares - aShares) * direction;
      case 'price':
        return ((PRICE_STATUS_ORDER[a.price_status ?? 'missing'] - PRICE_STATUS_ORDER[b.price_status ?? 'missing']) * 1000)
          + ((bPrice - aPrice) * direction);
      case 'symbol':
        return a.symbol.localeCompare(b.symbol, 'en', { numeric: true, sensitivity: 'base' }) * direction;
      default:
        return 0;
    }
  });

  const activeHoldingsSortLabel = `${HOLDINGS_SORT_LABELS[holdingsSortKey]} ${holdingsSortDirection === 'asc' ? '由小到大' : '由大到小'}`;

  const toggleHoldingsSort = (key: HoldingsSortKey) => {
    setSelectedSymbol(null);
    setHoldingsSortKey((currentKey) => {
      if (currentKey === key) {
        setHoldingsSortDirection((currentDirection) => (currentDirection === 'asc' ? 'desc' : 'asc'));
        return currentKey;
      }
      setHoldingsSortDirection(key === 'symbol' ? 'asc' : 'desc');
      return key;
    });
  };

  useEffect(() => {
    if (!selectedSymbol && holdingsForDisplay.length > 0) {
      setSelectedSymbol(holdingsForDisplay[0].symbol);
      return;
    }
    if (selectedSymbol && holdingsForDisplay.length > 0 && !holdingsForDisplay.some((h) => h.symbol === selectedSymbol)) {
      setSelectedSymbol(holdingsForDisplay[0].symbol);
    }
  }, [holdingsForDisplay, selectedSymbol]);

  const clearEditTransaction = () => setEditTransaction(null);
  const handleCreated = (entry: UndoEntry) => setUndoStack((stack) => [...stack, entry]);
  const clearNotice = () => setNotice(null);

  return {
    summary,
    computedHoldings,
    transactions,
    versionInfo,
    performance,
    performanceRange,
    setPerformanceRange,
    editTransaction,
    clearEditTransaction,
    notice,
    clearNotice,
    pendingDeleteTransaction,
    txQuery,
    setTxQuery,
    txTypeFilter,
    setTxTypeFilter,
    txCategoryFilter,
    setTxCategoryFilter,
    txGainFilter,
    setTxGainFilter,
    txFromDate,
    setTxFromDate,
    txToDate,
    setTxToDate,
    selectedSymbol,
    setSelectedSymbol,
    holdingsSortKey,
    holdingsSortDirection,
    holdingsForDisplay,
    activeHoldingsSortLabel,
    visibleTransactions,
    profitTransactionCount,
    lossTransactionCount,
    availableUndoStack,
    isAdmin,
    navigate,
    navigateToAdmin,
    handleLogout,
    handleEdit,
    requestDeleteTransaction,
    cancelDeleteTransaction,
    confirmDeleteTransaction,
    handleUndoLast,
    clearTransactionFilters,
    toggleHoldingsSort,
    handleCreated,
  };
}
