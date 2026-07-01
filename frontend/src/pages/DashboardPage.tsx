import { Link } from 'react-router-dom';
import AddTransactionForm from '../components/AddTransactionForm';
import DashboardLayout from '../components/DashboardLayout';
import ConfirmDialog from '../components/ConfirmDialog';
import InlineNotice from '../components/InlineNotice';
import DashboardStatCard from '../components/dashboard/DashboardStatCard';
import HoldingsSection from '../components/dashboard/HoldingsSection';
import OverviewPerformanceSection from '../components/dashboard/OverviewPerformanceSection';
import TransactionsSection from '../components/dashboard/TransactionsSection';
import { DataTimestamp } from '../components/UIState';
import { formatCurrencyBreakdown, formatPct, formatShares, formatTWD } from '../components/dashboard/shared';
import { useDashboardState } from '../hooks/useDashboardState';
import type { DashboardView } from '../types/dashboard';

interface DashboardPageProps {
  view?: DashboardView;
}

// ---------- Page ----------
export default function DashboardPage({ view = 'overview' }: DashboardPageProps) {
  const {
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
  } = useDashboardState();

  const lastUndoEntry = availableUndoStack[availableUndoStack.length - 1];

  const benchmarkSeries = performance?.benchmarks ?? [];
  const performanceChartData = (performance?.portfolio ?? []).map(point => {
    const row: Record<string, string | number> = {
      date: point.date,
      portfolio: point.normalized_value,
      portfolioValue: point.value,
    };
    benchmarkSeries.forEach(series => {
      const match = series.points.find(p => p.date === point.date);
      if (match) row[series.name] = match.normalized_value;
    });
    return row;
  });

  return (
    <DashboardLayout
      isAdmin={isAdmin}
      onLogout={handleLogout}
      onNavigateToAdmin={navigateToAdmin}
      versionInfo={versionInfo}
      view={view}
    >
        {notice ? (
          <InlineNotice
            message={notice.message}
            onDismiss={clearNotice}
            tone={notice.tone}
            title={notice.title}
          />
        ) : null}

        {/* Summary Stats */}
        {view === 'overview' && summary && (
          <div className="space-y-2 sm:space-y-3">
            <DataTimestamp
              value={summary.last_updated ? new Date(summary.last_updated).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' }) : 'N/A'}
              hint={`區間：${performanceRange === 'all' ? '成立以來' : performanceRange === 'today' ? '今日' : performanceRange === 'week' ? '本週' : performanceRange === 'month' ? '本月' : '今年'}`}
            />
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
              <DashboardStatCard
                label="總市值"
                value={formatTWD(summary.total_value_twd)}
                sub={`成本 ${formatTWD(summary.total_cost_twd)} · ${formatCurrencyBreakdown(summary.total_value_by_currency)}`}
              />
              <DashboardStatCard
                label="未實現損益"
                value={formatTWD(summary.unrealized_gain_twd)}
                sub={`${formatPct(summary.unrealized_pct)} · ${formatCurrencyBreakdown(summary.unrealized_gain_by_currency)}`}
                positive={(summary.unrealized_gain_twd ?? 0) >= 0}
              />
              <DashboardStatCard
                label="已實現損益"
                value={formatTWD(summary.realized_gain_twd ?? summary.realized_gain)}
                sub={formatCurrencyBreakdown(summary.realized_gain_by_currency)}
                positive={(summary.realized_gain_twd ?? summary.realized_gain) >= 0}
              />
              <DashboardStatCard
                label="XIRR"
                value={summary.annualized_return != null ? formatPct(summary.annualized_return) : '資料不足'}
                sub={summary.annualized_return_message ?? (summary.annualized_return_status && summary.annualized_return_status !== 'ok' ? '計算失敗' : undefined)}
                positive={summary.annualized_return != null && summary.annualized_return >= 0}
              />
            </div>
          </div>
        )}

        {view === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 sm:gap-4 animate-fade-in">
            <div className="card p-3 sm:p-4">
              <div className="text-xs opacity-60 mb-1">持倉摘要</div>
              <div className="text-xl font-bold">{computedHoldings.length} 檔</div>
              <div className="text-xs opacity-60 mt-1">詳細配置、排序與單檔交易請到持倉頁查看。</div>
              <Link to="/holdings" className="btn-secondary inline-flex mt-3 px-3 py-1.5 text-xs">
                查看持倉
              </Link>
            </div>
            <div className="card p-3 sm:p-4">
              <div className="text-xs opacity-60 mb-1">交易摘要</div>
              <div className="text-xl font-bold">{transactions.length} 筆</div>
              <div className="text-xs opacity-60 mt-1">篩選、編輯、刪除與復原操作集中在交易頁。</div>
              <Link to="/transactions" className="btn-secondary inline-flex mt-3 px-3 py-1.5 text-xs">
                查看交易
              </Link>
            </div>
            <div className="card p-3 sm:p-4">
              <div className="text-xs opacity-60 mb-1">資料狀態</div>
              <div className="text-xl font-bold">{summary?.last_updated ? '已更新' : '待同步'}</div>
              <div className="text-xs opacity-60 mt-1">
                {summary?.last_updated ? new Date(summary.last_updated).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' }) : '尚無更新時間'}
              </div>
            </div>
          </div>
        )}

        {view === 'holdings' && (
          <HoldingsSection
            computedHoldings={computedHoldings}
            holdingsForDisplay={holdingsForDisplay}
            holdingsSortDirection={holdingsSortDirection}
            holdingsSortKey={holdingsSortKey}
            activeHoldingsSortLabel={activeHoldingsSortLabel}
            selectedSymbol={selectedSymbol}
            setSelectedSymbol={setSelectedSymbol}
            summaryFxRate={summary?.fx_rate ?? 1}
            toggleHoldingsSort={toggleHoldingsSort}
            transactions={transactions}
          />
        )}

        {view === 'overview' ? (
          <OverviewPerformanceSection
            benchmarkSeries={benchmarkSeries}
            hasSummaryValue={Boolean(summary && summary.total_value_twd > 0)}
            performanceChartData={performanceChartData}
            performanceRange={performanceRange}
            setPerformanceRange={setPerformanceRange}
          />
        ) : null}

        {view === 'transactions' && (
          <TransactionsSection
            availableUndoStack={availableUndoStack}
            clearEditTransaction={clearEditTransaction}
            clearTransactionFilters={clearTransactionFilters}
            currentHoldingSymbols={computedHoldings.filter((holding) => Number(holding.shares) > 0).map((holding) => holding.symbol)}
            handleEdit={handleEdit}
            handleUndoLast={handleUndoLast}
            lastUndoEntry={lastUndoEntry}
            lossTransactionCount={lossTransactionCount}
            navigateToNew={() => navigate('/transactions/new')}
            profitTransactionCount={profitTransactionCount}
            requestDeleteTransaction={requestDeleteTransaction}
            setTxCategoryFilter={setTxCategoryFilter}
            setTxFromDate={setTxFromDate}
            setTxGainFilter={setTxGainFilter}
            setTxQuery={setTxQuery}
            setTxToDate={setTxToDate}
            setTxTypeFilter={setTxTypeFilter}
            transactions={transactions}
            txCategoryFilter={txCategoryFilter}
            txFromDate={txFromDate}
            txGainFilter={txGainFilter}
            txQuery={txQuery}
            txToDate={txToDate}
            txTypeFilter={txTypeFilter}
            visibleTransactions={visibleTransactions}
          />
        )}

        <ConfirmDialog
          open={Boolean(pendingDeleteTransaction)}
          title="刪除這筆交易？"
          description={pendingDeleteTransaction ? (
            <div className="space-y-2">
              <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)]/50 px-3 py-2 text-xs text-[var(--text-primary)]">
                <div className="font-mono">{pendingDeleteTransaction.date} · {pendingDeleteTransaction.symbol}</div>
                <div className="mt-1">
                  {pendingDeleteTransaction.type === 'buy' ? '買入' : '賣出'} {formatShares(pendingDeleteTransaction.shares)} 股
                </div>
                <div className="mt-1">
                  單價 {Number(pendingDeleteTransaction.price).toLocaleString('zh-TW', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
              <div>刪除後會重算持倉，且此動作無法復原。</div>
            </div>
          ) : undefined}
          confirmLabel="確認刪除"
          confirmTone="danger"
          onCancel={cancelDeleteTransaction}
          onConfirm={() => { void confirmDeleteTransaction(); }}
        />

        {/* Add Transaction Form */}
        {view === 'add' && (
          <AddTransactionForm
            onSuccess={() => {}}
            onCancel={() => { clearEditTransaction(); navigate('/transactions'); }}
            transactions={transactions}
            editTransaction={editTransaction ?? undefined}
            onEditComplete={clearEditTransaction}
            onCreated={handleCreated}
          />
        )}
    </DashboardLayout>
  );
}
