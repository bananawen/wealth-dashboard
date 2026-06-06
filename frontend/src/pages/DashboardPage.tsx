import { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Wallet, RefreshCw, Plus, Trash2, ArrowDownCircle, ArrowUpCircle, Sun, Moon, Database, Server, Clock
} from 'lucide-react';
import {
  AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts';
import {
  useGetPortfolioSummaryQuery,
  useGetComputedHoldingsQuery,
  useGetTransactionsQuery,
  useGetAccountsQuery,
  useGetHistoryQuery,
  useGetVersionQuery,
  useDeleteTransactionMutation,
  useCreateHoldingMutation,
  useDeleteHoldingMutation,
} from '../store/apiSlice';
import { useTheme } from '../context/ThemeContext';
import AddTransactionForm from '../components/AddTransactionForm';
import StatusBar from '../components/StatusBar';
import type {
  DashboardTab,
  ComputedHolding,
  Transaction,
  Account,
  VersionInfo,
  UndoEntry,
} from '../types';

// ---------- Formatters ----------
function formatCurrency(v: number, currency = 'USD') {
  if (v == null || isNaN(v)) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(v);
}

function formatTWD(v: number) {
  if (v == null || isNaN(v)) return 'N/A';
  return 'NT$' + Number(v).toLocaleString('zh-TW', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

// 根據原幣值顯示（持倉列表用）
// 顯示 2 位小數以避免四捨五入造成均價×股數 ≠成本的錯覺
function formatByCurrency(v: number, currency = 'TWD') {
  if (v == null || isNaN(v)) return 'N/A';
  if (currency === 'USD') {
    return 'US$' + Number(v).toLocaleString('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
  }
  return 'NT$' + Number(v).toLocaleString('zh-TW', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function formatPct(v: number) {
  if (v == null || isNaN(v)) return 'N/A';
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
}

function formatDateMMMDDYY(dateStr: string) {
  const d = new Date(dateStr);
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${months[d.getMonth()]}-${String(d.getDate()).padStart(2,'0')}-${String(d.getFullYear()).slice(-2)}`;
}

function formatShares(v: number) {
  if (v == null || isNaN(v)) return '0';
  return Number.isInteger(v) ? v.toString() : v.toFixed(2);
}

// ---------- StatCard ----------
interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  positive?: boolean;
}

function StatCard({ label, value, sub, positive }: StatCardProps) {
  return (
    <div className="card p-3 sm:p-4 animate-fade-in min-w-0">
      <div className="text-xs sm:text-sm opacity-60 truncate">{label}</div>
      <div className={`text-lg sm:text-2xl font-bold mt-1 ${positive === undefined ? 'text-inherit' : positive ? 'text-[var(--success)]' : 'text-[var(--error)]'} truncate`}>
        {value}
      </div>
      {sub && <div className="text-xs opacity-50 mt-1 truncate">{sub}</div>}
    </div>
  );
}

// ---------- Page ----------
export default function DashboardPage() {
  const { toggleTheme, isDark } = useTheme();

  // RTK Query hooks
  const { data: summary } = useGetPortfolioSummaryQuery(undefined);
  const { data: computedHoldings = [] } = useGetComputedHoldingsQuery(undefined);
  const { data: transactions = [] } = useGetTransactionsQuery(undefined);
  const { data: accounts = [] } = useGetAccountsQuery(undefined);
  const { data: history = [] } = useGetHistoryQuery(undefined);
  const { data: versionInfo } = useGetVersionQuery(undefined);

  const [tab, setTab] = useState<DashboardTab>('portfolio');
  const [undoStack, setUndoStack] = useState<UndoEntry[]>([]);
  const [editTransaction, setEditTransaction] = useState<Transaction | null>(null);

  const [deleteTransaction] = useDeleteTransactionMutation();
  const [createHolding] = useCreateHoldingMutation();
  const [deleteHolding] = useDeleteHoldingMutation();

  // Chart: seed from /portfolio/history, then live-poll today\'s value every 30s
  const [chartData, setChartData] = useState<{date: string; value: number}[]>(() =>
    (history as {date: string; value: number}[]).slice().sort((a, b) => a.date.localeCompare(b.date))
  );

  // When history loads, merge into chartData (keep live points if already populated)
  useEffect(() => {
    if (!history || history.length === 0) return;
    setChartData(prev => {
      const sorted = (history as {date: string; value: number}[]).slice().sort((a, b) => a.date.localeCompare(b.date));
      const today = new Date().toISOString().slice(0, 10);
      const livePoint = prev.find(d => d.date === today);
      if (!livePoint) return sorted;
      // Keep live point, drop any duplicate date from history
      const withoutToday = sorted.filter(d => d.date !== today);
      return [...withoutToday, livePoint].sort((a, b) => a.date.localeCompare(b.date));
    });
  }, [history]);

  // Live update: poll /portfolio/summary every 30s
  useEffect(() => {
    const fetchLive = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) return;
        const res = await fetch('http://localhost:8000/portfolio/summary', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const data = await res.json();
        const today = new Date().toISOString().slice(0, 10);
        setChartData(prev => {
          const withoutToday = prev.filter(d => d.date !== today);
          return [...withoutToday, { date: today, value: data.total_value }];
        });
      } catch {}
    };
    fetchLive();
    const id = setInterval(fetchLive, 30_000);
    return () => clearInterval(id);
  }, []);

  const handleDeleteHolding = useCallback(async (id: number) => {
    if (!confirm('刪除這筆持倉？')) return;
    try {
      await deleteHolding(id).unwrap();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed');
    }
  }, [deleteHolding]);

  const navigateToAdmin = () => {
    window.location.href = '/admin';
  };

  const handleEdit = (tx: Transaction) => {
    setTab('add');
    setEditTransaction(tx);
  };

  const handleDelete = useCallback(async (id: number) => {
    if (!confirm('刪除這筆交易？')) return;
    try {
      await deleteTransaction(id).unwrap();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed');
    }
  }, [deleteTransaction]);

  // Undo support: Ctrl+Z reverts last added transaction
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && undoStack.length > 0) {
        e.preventDefault();
        const last = undoStack[undoStack.length - 1];
        if (last.type === 'create') {
          deleteTransaction(last.id)
            .then(() => {
              setUndoStack(s => s.slice(0, -1));
            })
            .catch(err => alert(err instanceof Error ? err.message : 'Undo failed'));
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [undoStack, deleteTransaction]);

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] transition-colors duration-300">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-[var(--border-color)] bg-[var(--bg-primary)]/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-3 flex items-center justify-between">
          <h1 className="text-base sm:text-lg font-bold flex items-center gap-2">
            <span className="text-xl">📈</span>
            <span className="hidden xs:inline">個人財富管理</span>
            <span className="xs:hidden">財富</span>
          </h1>
          {versionInfo && (
            <div className="flex items-center gap-3 text-xs opacity-60">
              <span className="hidden sm:inline font-mono">v{versionInfo.version}</span>
              <span className="hidden sm:inline flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {versionInfo.last_updated ? new Date(versionInfo.last_updated).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' }) : ''}
              </span>
            </div>
          )}
          <div className="flex items-center gap-1 sm:gap-3">
            <button
              onClick={navigateToAdmin}
              className="p-2 rounded-lg hover:bg-[var(--bg-secondary)] transition-colors"
              title="資料庫監控"
            >
              <Database className="w-5 h-5" />
            </button>
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-[var(--bg-secondary)] transition-colors"
              aria-label="切換主題"
            >
              {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </header>

      <StatusBar />

      <main className="max-w-7xl mx-auto px-3 sm:px-6 py-3 sm:py-6 space-y-3 sm:space-y-6">
        {/* Summary Stats */}
        {summary && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
            <StatCard label="總市值" value={formatTWD(summary.total_value_twd)} sub={`成本 ${formatTWD(summary.total_cost_twd)}`} />
            <StatCard label="未實現損益" value={formatTWD(summary.unrealized_gain_twd)} sub={formatPct(summary.unrealized_pct)} positive={summary.unrealized_gain_twd >= 0} />
            <StatCard label="已實現損益" value={formatTWD(summary.realized_gain)} positive={summary.realized_gain >= 0} />
            <StatCard label="XIRR" value={summary.annualized_return != null ? formatPct(summary.annualized_return) : 'N/A'} positive={summary.annualized_return != null && summary.annualized_return >= 0} />
          </div>
        )}

        {/* Portfolio Chart — live from /portfolio/summary every 30s */}
        {(chartData.length > 0 || (summary && summary.total_value_twd > 0)) ? (
          <div className="card p-3 sm:p-6 animate-fade-in">
            <h2 className="text-sm font-semibold opacity-60 mb-4">歷史淨值趨勢</h2>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={180} className="text-xs">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} />
                  <YAxis tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} tickFormatter={v => '$' + v.toLocaleString()} />
                  <Tooltip
                    formatter={(v: number) => ['$' + Number(v).toLocaleString(), '淨值']}
                    contentStyle={{
                      backgroundColor: 'var(--card-bg)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '0.75rem',
                      color: 'var(--text-primary)'
                    }}
                    labelStyle={{ color: 'var(--text-secondary)' }}
                  />
                  <Area type="monotone" dataKey="value" stroke="#3B82F6" strokeWidth={2} fill="url(#colorValue)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-44 flex items-center justify-center opacity-50 text-sm">
                新增持倉後即可看到圖表
              </div>
            )}
          </div>
        ) : null}

        {/* Tabs */}
        <div className="flex gap-2 border-b border-[var(--border-color)] overflow-x-auto pb-px">
          {[
            { key: 'portfolio' as DashboardTab, label: '持倉', icon: Wallet },
            { key: 'transactions' as DashboardTab, label: '交易', icon: ArrowUpCircle },
            { key: 'add' as DashboardTab, label: '新增', icon: Plus },
          ].map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-3 sm:px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-1 sm:gap-2 ${
                tab === t.key
                  ? 'border-blue-500 text-blue-500'
                  : 'border-transparent opacity-60 hover:opacity-100'
              }`}
            >
              <t.icon className="w-4 h-4" />
              <span>{t.label}</span>
            </button>
          ))}
        </div>

        {/* Holdings */}
        {tab === 'portfolio' && (
          <div className="card overflow-hidden animate-fade-in">
            <div className="px-3 sm:px-4 py-2 sm:py-3 border-b border-[var(--border-color)] flex items-center gap-2">
              <Wallet className="w-4 h-4 opacity-60" />
              <span className="text-sm font-semibold">持倉列表</span>
            </div>
            {computedHoldings.length === 0 ? (
              <div className="p-6 sm:p-8 text-center opacity-50 text-sm">尚無持倉資料</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs sm:text-sm">
                  <thead className="bg-[var(--bg-secondary)] text-[var(--text-secondary)]">
                    <tr>
                      <th className="text-left px-2 sm:px-4 py-2">商品</th>
                      <th className="text-right px-2 sm:px-4 py-2">庫存</th>
                      <th className="text-right px-2 sm:px-4 py-2">均價</th>
                      <th className="text-right px-2 sm:px-4 py-2">成本</th>
                      <th className="text-right px-2 sm:px-4 py-2">現值</th>
                      <th className="text-right px-2 sm:px-4 py-2">損益</th>
                    </tr>
                  </thead>
                  <tbody>
                    {computedHoldings.map((h: ComputedHolding) => {
                      const currency = h.currency ?? 'TWD';
                      // 持倉列表用原幣值顯示，*_twd 只做 Summary 統一台幣時的後備
                      const mv = h.market_value ?? h.market_value_twd ?? 0;
                      const cost = h.total_cost ?? h.total_cost_twd ?? 0;
                      const gain = mv - cost;
                      const gainPct = cost > 0 ? (gain / cost * 100) : 0;
                      const avgPrice = h.avg_cost ?? (h.shares > 0 ? cost / h.shares : 0);
                      return (
                        <tr key={h.symbol} className="border-t border-[var(--border-color)] hover:bg-[var(--bg-secondary)]/50 transition-colors">
                          <td className="px-2 sm:px-4 py-2 sm:py-3 font-mono font-bold text-sm">{h.symbol}</td>
                          <td className="px-2 sm:px-4 py-2 sm:py-3 text-right font-mono">{Number(h.shares).toLocaleString('zh-TW', { maximumFractionDigits: 0 })}</td>
                          <td className="px-2 sm:px-4 py-2 sm:py-3 text-right">{formatByCurrency(avgPrice, currency)}</td>
                          <td className="px-2 sm:px-4 py-2 sm:py-3 text-right font-semibold">{formatByCurrency(cost, currency)}</td>
                          <td className="px-2 sm:px-4 py-2 sm:py-3 text-right font-semibold">{formatByCurrency(mv, currency)}</td>
                          <td className={`px-2 sm:px-4 py-2 sm:py-3 text-right font-semibold ${gain >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                            {gain >= 0 ? '+' : ''}{formatByCurrency(Math.abs(gain), currency)}
                            <span className="text-xs opacity-70 ml-1">({gainPct >= 0 ? '+' : ''}{gainPct.toFixed(2)}%)</span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Transactions */}
        {tab === 'transactions' && (
          <div className="card overflow-hidden animate-fade-in">
            <div className="px-3 sm:px-4 py-2 sm:py-3 border-b border-[var(--border-color)] flex items-center justify-between">
              <span className="text-sm font-semibold">交易紀錄</span>
              {undoStack.length > 0 && (
                <button
                  onClick={() => {
                    const last = undoStack[undoStack.length - 1];
                    if (!confirm('復原上一筆交易？')) return;
                    deleteTransaction(last.id)
                      .then(() => setUndoStack(s => s.slice(0, -1)))
                      .catch(err => alert(err instanceof Error ? err.message : 'Undo failed'));
                  }}
                  className="flex items-center gap-1 text-xs px-2 py-1 rounded hover:bg-[var(--bg-secondary)] opacity-60 hover:opacity-100"
                >
                  <RefreshCw className="w-3 h-3" /> 復原
                </button>
              )}
            </div>
            {transactions.length === 0 ? (
              <div className="p-6 sm:p-8 text-center opacity-50 text-sm">尚無交易紀錄</div>
            ) : (
              <div className="divide-y divide-[var(--border-color)]">
                {transactions.map((tx: Transaction) => {
                  const account = accounts.find((a: Account) => a.id === tx.account_id);
                  const dateFormatted = formatDateMMMDDYY(tx.date);
                  return (
                    <div
                      key={tx.id}
                      onClick={() => handleEdit(tx)}
                      className="px-3 sm:px-4 py-2 sm:py-3 cursor-pointer hover:bg-[var(--bg-secondary)]/50 transition-colors group relative"
                    >
                      {/* Line 1: date | account | type badge */}
                      <div className="flex items-center gap-2 text-xs opacity-70 mb-0.5">
                        <span className="font-mono">{dateFormatted}</span>
                        <span className="opacity-50">|</span>
                        <span>{account?.name || tx.account_id}</span>
                      </div>
                      {/* Line 2: symbol | amount */}
                      <div className="flex items-center justify-between pr-6">
                        <span className="font-mono font-bold text-sm">{tx.symbol}</span>
                        <span className="text-sm font-semibold">
                          {tx.type.toUpperCase() === 'BUY'
                            ? <span className="text-[var(--profit)]">買</span>
                            : <span className="text-[var(--loss)]">賣</span>
                          }
                          {' '}
                          {formatShares(tx.shares)} × {formatCurrency(tx.price)} = {formatCurrency(tx.shares * tx.price)}
                        </span>
                      </div>
                      {/* Delete button - appears on hover */}
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(tx.id); }}
                        className="absolute right-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-60 hover:!opacity-100 text-[var(--error)] transition-all"
                        title="刪除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Add Transaction Form */}
        {tab === 'add' && (
          <AddTransactionForm
            onSuccess={() => {}}
            onCancel={() => { setTab('transactions'); setEditTransaction(null); }}
            editTransaction={editTransaction ?? undefined}
            onEditComplete={() => setEditTransaction(null)}
            onCreated={(entry) => setUndoStack(s => [...s, entry])}
          />
        )}
      </main>
    </div>
  );
}
