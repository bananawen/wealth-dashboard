import {
  CartesianGrid,
  Pie,
  PieChart,
  Bar,
  BarChart,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Wallet } from 'lucide-react';
import { ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react';
import { EmptyState, SemanticBadge } from '../UIState';
import { useGetPriceHistoryQuery } from '../../store/apiSlice';
import DashboardStatCard from './DashboardStatCard';
import {
  ASSET_CLASS_LABELS,
  formatByCurrency,
  formatDateMMMDDYY,
  formatShares,
  formatTWD,
  getHoldingGroup,
  getMarketLabel,
  getPriceStatusLabel,
  HOLDING_GROUP_LABELS,
  HOLDING_GROUP_ORDER,
  PIE_COLORS,
} from './shared';
import type { ComputedHolding, Transaction } from '../../types';
import type { HoldingsSortKey, SortDirection } from '../../types/dashboard';

interface HoldingsSectionProps {
  computedHoldings: ComputedHolding[];
  holdingsForDisplay: ComputedHolding[];
  holdingsSortDirection: SortDirection;
  holdingsSortKey: HoldingsSortKey;
  activeHoldingsSortLabel: string;
  selectedSymbol: string | null;
  setSelectedSymbol: (symbol: string | null) => void;
  summaryFxRate?: number;
  toggleHoldingsSort: (key: HoldingsSortKey) => void;
  transactions: Transaction[];
}

export default function HoldingsSection({
  computedHoldings,
  holdingsForDisplay,
  holdingsSortDirection,
  holdingsSortKey,
  activeHoldingsSortLabel,
  selectedSymbol,
  setSelectedSymbol,
  summaryFxRate = 1,
  toggleHoldingsSort,
  transactions,
}: HoldingsSectionProps) {
  const selectedHolding = selectedSymbol
    ? computedHoldings.find((holding) => holding.symbol === selectedSymbol) ?? null
    : null;

  const selectedTransactions = selectedSymbol
    ? transactions
        .filter((tx) => tx.symbol.toUpperCase() === selectedSymbol.toUpperCase())
        .slice()
        .sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id)
    : [];

  const firstTransactionDate = selectedTransactions[0]?.date?.slice(0, 10) ?? null;
  const historyDays = firstTransactionDate
    ? Math.min(
        3650,
        Math.max(
          30,
          Math.ceil(
            (new Date().getTime() - new Date(`${firstTransactionDate}T00:00:00`).getTime()) / 86_400_000,
          ) + 7,
        ),
      )
    : 30;
  const selectedMarket = selectedHolding?.currency === 'USD' ? 'US' : 'TW';
  const { data: selectedPriceHistory = [] } = useGetPriceHistoryQuery(
    selectedHolding
      ? { market: selectedMarket, symbol: selectedHolding.symbol, days: historyDays }
      : { market: 'TW', symbol: '', days: 30 },
    { skip: !selectedHolding || !firstTransactionDate },
  );

  const selectedTimeline = (() => {
    if (!selectedHolding) return [];
    const currency = selectedHolding.currency ?? 'TWD';
    let shares = 0;
    let totalCost = 0;
    let avgCost = 0;
    let realizedGain = 0;

    return selectedTransactions.map((tx) => {
      const txDate = tx.date.slice(0, 10);
      const quantity = Number(tx.shares) || 0;
      const price = Number(tx.price) || 0;
      const fee = Number(tx.fee ?? 0);
      const tax = Number(tx.tax ?? 0);
      if (tx.type === 'buy') {
        totalCost += quantity * price + fee + tax;
        shares += quantity;
        avgCost = shares > 0 ? totalCost / shares : 0;
      } else {
        realizedGain += Number(tx.realized_gain ?? ((price - avgCost) * quantity - fee - tax));
        shares = Math.max(0, shares - quantity);
        totalCost = shares > 0 ? avgCost * shares : 0;
      }
      const currentPriceTwd = Number(selectedHolding.current_price_twd ?? 0);
      const marketValueTwd = shares * currentPriceTwd;
      const costBasisTwd = currency === 'USD' ? totalCost * summaryFxRate : totalCost;
      return {
        chartPointKey: `${txDate}-${tx.id}`,
        date: txDate,
        displayDate: formatDateMMMDDYY(txDate),
        shares,
        avgCost,
        costBasisTwd,
        marketValueTwd,
        unrealizedGainTwd: marketValueTwd - costBasisTwd,
        realizedGain,
      };
    });
  })();

  const selectedPerformanceTimeline = (() => {
    if (!selectedHolding || !firstTransactionDate) return [];

    const historyRows = [...selectedPriceHistory]
      .map((row) => ({
        ...row,
        price_date: row.price_date.slice(0, 10),
      }))
      .filter((row) => row.price_date >= firstTransactionDate)
      .sort((a, b) => a.price_date.localeCompare(b.price_date));

    if (historyRows.length === 0) return selectedTimeline;

    const currency = selectedHolding.currency ?? 'TWD';
    const fxRate = summaryFxRate > 0 ? summaryFxRate : 1;
    const txQueue = selectedTransactions.map((tx) => ({
      ...tx,
      tradeDate: tx.date.slice(0, 10),
      shares: Number(tx.shares) || 0,
      price: Number(tx.price) || 0,
      fee: Number(tx.fee ?? 0),
      tax: Number(tx.tax ?? 0),
    }));

    let txIndex = 0;
    let shares = 0;
    let totalCost = 0;
    let avgCost = 0;

    const points = historyRows.map((row) => {
      while (txIndex < txQueue.length && txQueue[txIndex].tradeDate <= row.price_date) {
        const tx = txQueue[txIndex];
        if (tx.type === 'buy') {
          totalCost += tx.shares * tx.price + tx.fee + tx.tax;
          shares += tx.shares;
          avgCost = shares > 0 ? totalCost / shares : 0;
        } else {
          shares = Math.max(0, shares - tx.shares);
          totalCost = shares > 0 ? avgCost * shares : 0;
        }
        txIndex += 1;
      }

      const closePrice = Number(row.close ?? 0);
      const closePriceTwd = currency === 'USD' ? closePrice * fxRate : closePrice;
      const costBasisTwd = currency === 'USD' ? totalCost * fxRate : totalCost;
      const marketValueTwd = shares * closePriceTwd;

      return {
        chartPointKey: row.price_date,
        date: row.price_date,
        displayDate: formatDateMMMDDYY(row.price_date),
        shares,
        avgCost,
        costBasisTwd,
        marketValueTwd,
        unrealizedGainTwd: marketValueTwd - costBasisTwd,
        realizedGain: 0,
      };
    }).filter((point) => point.shares > 0 || point.costBasisTwd > 0);

    const today = new Date().toISOString().slice(0, 10);
    const lastPoint = points[points.length - 1];
    if (
      lastPoint
      && lastPoint.date < today
      && Number(selectedHolding.current_price_twd ?? 0) > 0
    ) {
      points.push({
        ...lastPoint,
        chartPointKey: today,
        date: today,
        displayDate: formatDateMMMDDYY(today),
        marketValueTwd: lastPoint.shares * Number(selectedHolding.current_price_twd ?? 0),
        unrealizedGainTwd: (lastPoint.shares * Number(selectedHolding.current_price_twd ?? 0)) - lastPoint.costBasisTwd,
      });
    }

    return points;
  })();
  const hasSelectedPriceHistory = selectedPriceHistory.some((row) => row.price_date.slice(0, 10) >= (firstTransactionDate ?? ''));

  const holdingGroups = HOLDING_GROUP_ORDER.map((group) => {
    const rows = computedHoldings.filter((holding) => getHoldingGroup(holding, transactions) === group);
    const marketValueTwd = rows.reduce((sum, holding) => sum + Number(holding.market_value_twd ?? holding.market_value ?? 0), 0);
    const costTwd = rows.reduce((sum, holding) => sum + Number(holding.total_cost_twd ?? holding.total_cost ?? 0), 0);
    return {
      group,
      label: HOLDING_GROUP_LABELS[group],
      count: rows.length,
      marketValueTwd,
      costTwd,
      unrealizedGainTwd: marketValueTwd - costTwd,
    };
  }).filter((item) => item.count > 0);

  const assetAllocation = HOLDING_GROUP_ORDER.map((group) => ({
    name: HOLDING_GROUP_LABELS[group],
    value: holdingGroups.find((item) => item.group === group)?.marketValueTwd ?? 0,
  })).filter((item) => item.value > 0);
  const portfolioValueTwd = holdingGroups.reduce((sum, group) => sum + group.marketValueTwd, 0);
  const assetAllocationTable = HOLDING_GROUP_ORDER.map((group) => {
    const currentValue = holdingGroups.find((item) => item.group === group)?.marketValueTwd ?? 0;
    const currentPercent = portfolioValueTwd > 0 ? (currentValue / portfolioValueTwd) * 100 : 0;
    return {
      group,
      label: ASSET_CLASS_LABELS[group],
      currentValue,
      currentPercent,
    };
  }).filter((item) => item.currentValue > 0);

  return (
    <div className="space-y-3 sm:space-y-4 animate-fade-in">
      <div className="card overflow-hidden">
        <div className="flex flex-col gap-2 border-b border-[var(--border-color)] px-3 py-2 sm:flex-row sm:items-center sm:justify-between sm:px-4 sm:py-3">
          <div className="flex items-center gap-2">
            <Wallet className="h-4 w-4 opacity-60" />
            <span className="text-sm font-semibold">持倉概覽</span>
          </div>
          <div className="rounded-full border border-[var(--accent)]/20 bg-[var(--accent)]/8 px-2 py-1 text-xs text-[var(--accent)]">
            持倉由交易自動計算
          </div>
        </div>

        <div className="space-y-1 border-b border-[var(--border-color)] px-3 py-3 text-xs sm:px-4 sm:text-sm">
          <div className="opacity-80">持倉不再提供直接編輯，所有數量與成本都由交易紀錄投影而來。</div>
          <div className="opacity-60">若現價抓不到，會顯示價格來源與暫缺狀態；市值會以均價暫估，但會明確標示。</div>
        </div>

        {holdingGroups.length > 0 ? (
          <div className="border-b border-[var(--border-color)] p-3 sm:p-4">
            <div className="grid grid-cols-2 gap-2 xl:grid-cols-5">
              {holdingGroups.map((group) => (
                <div key={group.group} className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)]/40 px-3 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-semibold">{group.label}</div>
                    <div className="text-xs opacity-60">{group.count} 檔</div>
                  </div>
                  <div className="mt-2 text-xs opacity-70">市值 {formatTWD(group.marketValueTwd)}</div>
                  <div className={`mt-1 text-sm font-semibold ${group.unrealizedGainTwd >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                    損益 {group.unrealizedGainTwd >= 0 ? '+' : ''}{formatTWD(Math.abs(group.unrealizedGainTwd))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="border-b border-[var(--border-color)] p-3 sm:p-4">
            <EmptyState title="目前沒有持倉" description="建立交易後，持倉與配置摘要才會出現。" />
          </div>
        )}

        {assetAllocation.length > 0 && (
          <div className="border-b border-[var(--border-color)] p-3 sm:p-4">
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
              <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)]/30 p-3">
                <div className="mb-2 text-sm font-semibold">資產配置</div>
                <ResponsiveContainer width="100%" height={190}>
                  <PieChart>
                    <Pie data={assetAllocation} dataKey="value" nameKey="name" innerRadius={42} outerRadius={72} paddingAngle={3}>
                      {assetAllocation.map((_, idx) => <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip formatter={(value: number) => [formatTWD(value), '市值']} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)]/30 p-3">
                <div className="mb-2 text-sm font-semibold">配置明細</div>
                <ResponsiveContainer width="100%" height={190}>
                  <BarChart data={assetAllocationTable} layout="vertical" margin={{ left: 16, right: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                    <XAxis type="number" tickFormatter={(v) => formatTWD(Number(v))} />
                    <YAxis type="category" dataKey="label" width={64} />
                    <Tooltip formatter={(value: number) => [formatTWD(value), '市值']} />
                    <Bar dataKey="currentValue" fill="#3B82F6" radius={[0, 8, 8, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}
        <div className="border-b border-[var(--border-color)] p-3 sm:p-4">
          <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)]/30 p-3">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <div className="text-sm font-semibold">目標配置與偏離提醒</div>
              <div className="text-xs opacity-60">暫時停用，待資產分類規則與目標模型確認後再恢復</div>
            </div>
            <div className="mt-3 overflow-x-auto rounded-xl border border-[var(--border-color)]">
              <table className="w-full text-xs sm:text-sm">
                <thead className="bg-[var(--bg-secondary)] text-[var(--text-secondary)]">
                  <tr>
                    <th className="px-3 py-2 text-left">資產類別</th>
                    <th className="px-3 py-2 text-right">市值</th>
                    <th className="px-3 py-2 text-right">占比</th>
                  </tr>
                </thead>
                <tbody>
                  {assetAllocationTable.map((item) => (
                    <tr key={item.group} className="border-t border-[var(--border-color)]">
                      <td className="px-3 py-2 font-semibold">{item.label}</td>
                      <td className="px-3 py-2 text-right">{formatTWD(item.currentValue)}</td>
                      <td className="px-3 py-2 text-right">{item.currentPercent.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="flex items-center justify-between gap-2 border-b border-[var(--border-color)] px-3 py-2 sm:px-4 sm:py-3">
          <div className="flex items-center gap-2">
            <Wallet className="h-4 w-4 opacity-60" />
            <span className="text-sm font-semibold">持倉列表</span>
          </div>
          <div className="text-right text-xs opacity-60">
            <div>點選任一列可看單一標的詳情</div>
            <div>排序：{activeHoldingsSortLabel}</div>
          </div>
        </div>

        {holdingsForDisplay.length === 0 ? (
          <div className="p-6 sm:p-8">
            <EmptyState title="尚無持倉資料" description="建立交易後，這裡會顯示可排序的持倉清單。" />
          </div>
        ) : (
          <>
            <div className="space-y-2 p-3 sm:hidden">
              {holdingsForDisplay.map((holding) => {
                const currency = holding.currency ?? 'TWD';
                const marketValue = Number(holding.market_value ?? 0);
                const marketValueTwd = Number(holding.market_value_twd ?? 0);
                const cost = Number(holding.total_cost ?? 0);
                const costTwd = Number(holding.total_cost_twd ?? 0);
                const gainTwd = Number(holding.unrealized_gain_twd ?? (marketValueTwd - costTwd));
                const gain = Number(holding.unrealized_gain ?? (marketValue - cost));
                const gainPct = cost > 0 ? (gain / cost) * 100 : 0;
                const avgPrice = Number(holding.avg_cost ?? (holding.shares > 0 ? cost / holding.shares : 0));
                const isSelected = selectedSymbol === holding.symbol;
                const displayPrice = holding.price_status === 'missing'
                  ? 'N/A'
                  : formatByCurrency(Number(holding.current_price ?? avgPrice), currency);

                return (
                  <button
                    key={holding.symbol}
                    type="button"
                    onClick={() => setSelectedSymbol(holding.symbol)}
                    className={`w-full rounded-xl border p-3 text-left transition-colors ${
                      isSelected
                        ? 'border-[var(--accent)] bg-[var(--accent)]/8'
                        : 'border-[var(--border-color)] bg-[var(--bg-secondary)]/35'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-base font-bold">{holding.symbol}</span>
                          <SemanticBadge tone={holding.price_status === 'live' ? 'success' : holding.price_status === 'estimated' ? 'estimated' : 'warning'} className="text-[10px]">
                            {holding.price_status === 'live' ? '即時' : holding.price_status === 'estimated' ? '估算' : '缺價'}
                          </SemanticBadge>
                        </div>
                        <div className="mt-1 text-xs text-[var(--text-muted)]">
                          {getMarketLabel(holding)} · {HOLDING_GROUP_LABELS[getHoldingGroup(holding, transactions)]} · {formatShares(Number(holding.shares))} 股
                        </div>
                      </div>
                      <div className={`shrink-0 text-right text-sm font-semibold ${gain >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                        {gainPct >= 0 ? '+' : ''}{gainPct.toFixed(2)}%
                      </div>
                    </div>

                    <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <div className="text-xs text-[var(--text-muted)]">現值</div>
                        <div className="font-semibold">{formatTWD(marketValueTwd)}</div>
                        <div className="text-[11px] text-[var(--text-muted)]">{formatByCurrency(marketValue, currency)}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-[var(--text-muted)]">損益</div>
                        <div className={`font-semibold ${gain >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                          {gain >= 0 ? '+' : '-'}{formatTWD(Math.abs(gainTwd))}
                        </div>
                        <div className="text-[11px] text-[var(--text-muted)]">{formatByCurrency(Math.abs(gain), currency)}</div>
                      </div>
                      <div>
                        <div className="text-xs text-[var(--text-muted)]">現價</div>
                        <div className="font-semibold">{displayPrice}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-[var(--text-muted)]">成本</div>
                        <div className="font-semibold">{formatTWD(costTwd)}</div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="hidden overflow-x-auto sm:block">
              <table className="w-full text-xs sm:text-sm">
                <thead className="bg-[var(--bg-secondary)] text-[var(--text-secondary)]">
                  <tr>
                    <th className="px-2 py-2 text-left sm:px-4">
                      <button className="inline-flex items-center gap-1 transition-colors hover:text-[var(--accent)]" onClick={() => toggleHoldingsSort('symbol')}>
                        商品
                        {holdingsSortKey === 'symbol' ? (holdingsSortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </button>
                    </th>
                    <th className="px-2 py-2 text-right sm:px-4">
                      <button className="inline-flex items-center gap-1 transition-colors hover:text-[var(--accent)]" onClick={() => toggleHoldingsSort('shares')}>
                        庫存
                        {holdingsSortKey === 'shares' ? (holdingsSortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </button>
                    </th>
                    <th className="px-2 py-2 text-right sm:px-4">
                      <button className="inline-flex items-center gap-1 transition-colors hover:text-[var(--accent)]" onClick={() => toggleHoldingsSort('price')}>
                        現價 / 來源
                        {holdingsSortKey === 'price' ? (holdingsSortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </button>
                    </th>
                    <th className="px-2 py-2 text-right sm:px-4">
                      <button className="inline-flex items-center gap-1 transition-colors hover:text-[var(--accent)]" onClick={() => toggleHoldingsSort('cost')}>
                        成本
                        {holdingsSortKey === 'cost' ? (holdingsSortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </button>
                    </th>
                    <th className="px-2 py-2 text-right sm:px-4">
                      <button className="inline-flex items-center gap-1 transition-colors hover:text-[var(--accent)]" onClick={() => toggleHoldingsSort('market_value')}>
                        現值
                        {holdingsSortKey === 'market_value' ? (holdingsSortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </button>
                    </th>
                    <th className="px-2 py-2 text-right sm:px-4">
                      <button className="inline-flex items-center gap-1 transition-colors hover:text-[var(--accent)]" onClick={() => toggleHoldingsSort('gain')}>
                        損益
                        {holdingsSortKey === 'gain' ? (holdingsSortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {holdingsForDisplay.map((holding) => {
                    const currency = holding.currency ?? 'TWD';
                    const marketValue = Number(holding.market_value ?? 0);
                    const marketValueTwd = Number(holding.market_value_twd ?? 0);
                    const cost = Number(holding.total_cost ?? 0);
                    const costTwd = Number(holding.total_cost_twd ?? 0);
                    const gainTwd = Number(holding.unrealized_gain_twd ?? (marketValueTwd - costTwd));
                    const gain = Number(holding.unrealized_gain ?? (marketValue - cost));
                    const gainPct = cost > 0 ? (gain / cost) * 100 : 0;
                    const avgPrice = Number(holding.avg_cost ?? (holding.shares > 0 ? cost / holding.shares : 0));
                    const isSelected = selectedSymbol === holding.symbol;
                    const displayPrice = holding.price_status === 'missing'
                      ? 'N/A'
                      : formatByCurrency(Number(holding.current_price ?? avgPrice), currency);

                    return (
                      <tr
                        key={holding.symbol}
                        onClick={() => setSelectedSymbol(holding.symbol)}
                        className={`cursor-pointer border-t border-[var(--border-color)] transition-colors hover:bg-[var(--bg-secondary)]/50 ${isSelected ? 'bg-[var(--accent)]/6 ring-1 ring-inset ring-[var(--accent)]/20' : ''}`}
                      >
                        <td className="px-2 py-2 sm:px-4 sm:py-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <div className="font-mono text-sm font-bold">{holding.symbol}</div>
                            <SemanticBadge tone={holding.price_status === 'live' ? 'success' : holding.price_status === 'estimated' ? 'estimated' : 'warning'} className="text-[10px]">
                              {holding.price_status === 'live' ? '即時' : holding.price_status === 'estimated' ? '估算' : '缺價'}
                            </SemanticBadge>
                          </div>
                          <div className="text-[10px] opacity-60 sm:text-xs">{getMarketLabel(holding)} · {HOLDING_GROUP_LABELS[getHoldingGroup(holding, transactions)]}</div>
                        </td>
                        <td className="px-2 py-2 text-right font-mono sm:px-4 sm:py-3">
                          {Number(holding.shares).toLocaleString('zh-TW', { maximumFractionDigits: 0 })}
                          <div className="text-[10px] opacity-60 sm:text-xs">股</div>
                        </td>
                        <td className="px-2 py-2 text-right sm:px-4 sm:py-3">
                          <div className="font-semibold">{displayPrice}</div>
                          <div className="text-[10px] opacity-60 sm:text-xs">{getPriceStatusLabel(holding)}</div>
                        </td>
                        <td className="px-2 py-2 text-right sm:px-4 sm:py-3">
                          <div className="font-semibold">{formatByCurrency(cost, currency)}</div>
                          <div className="text-[10px] opacity-60 sm:text-xs">{formatTWD(costTwd)}</div>
                        </td>
                        <td className="px-2 py-2 text-right sm:px-4 sm:py-3">
                          <div className="font-semibold">{formatByCurrency(marketValue, currency)}</div>
                          <div className="text-[10px] opacity-60 sm:text-xs">{formatTWD(marketValueTwd)}</div>
                        </td>
                        <td className={`px-2 py-2 text-right font-semibold sm:px-4 sm:py-3 ${gain >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                          <div>{gain >= 0 ? '+' : ''}{formatByCurrency(Math.abs(gain), currency)}</div>
                          <div className="text-[10px] opacity-70 sm:text-xs">
                            {formatTWD(Math.abs(gainTwd))}
                            <span className="ml-1">({gainPct >= 0 ? '+' : ''}{gainPct.toFixed(2)}%)</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {selectedHolding ? (
        <div className="card overflow-hidden">
          <div className="flex flex-col gap-2 border-b border-[var(--border-color)] px-3 py-2 sm:flex-row sm:items-center sm:justify-between sm:px-4 sm:py-3">
            <div>
              <div className="font-mono text-sm font-semibold">{selectedHolding.symbol}</div>
              <div className="text-xs opacity-60">{getMarketLabel(selectedHolding)} · {getPriceStatusLabel(selectedHolding)}</div>
            </div>
            <SemanticBadge tone={selectedHolding.price_is_estimated ? 'estimated' : 'success'}>
              {selectedHolding.price_is_estimated ? '價格以均價估算' : '價格來源正常'}
            </SemanticBadge>
          </div>

          <div className="space-y-4 p-3 sm:p-4">
            <div className="grid grid-cols-2 gap-2 sm:gap-3 lg:grid-cols-4">
              <DashboardStatCard label="現價" value={selectedHolding.price_status === 'missing' ? 'N/A' : formatByCurrency(Number(selectedHolding.current_price ?? 0), selectedHolding.currency ?? 'TWD')} sub={selectedHolding.price_source ? `來源 ${selectedHolding.price_source}` : '來源暫缺'} />
              <DashboardStatCard label="庫存成本(TWD)" value={formatTWD(Number(selectedHolding.total_cost_twd ?? 0))} />
              <DashboardStatCard label="現值(TWD)" value={formatTWD(Number(selectedHolding.market_value_twd ?? 0))} />
              <DashboardStatCard label="未實現損益(TWD)" value={formatTWD(Number(selectedHolding.unrealized_gain_twd ?? 0))} positive={(selectedHolding.unrealized_gain_twd ?? 0) >= 0} />
            </div>

            {selectedPerformanceTimeline.length > 0 ? (
              <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
                <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)]/30 p-3 xl:col-span-2">
                  <div className="mb-2 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <div className="text-sm font-semibold">損益走勢</div>
                      <div className="text-xs opacity-60">
                        {hasSelectedPriceHistory ? '依每日歷史收盤價計算至目前為止' : '歷史股價暫缺，目前先以交易節點顯示'}
                      </div>
                    </div>
                    <SemanticBadge tone={hasSelectedPriceHistory ? 'info' : 'warning'} className="w-fit">
                      {hasSelectedPriceHistory ? '歷史價格序列' : '交易節點 fallback'}
                    </SemanticBadge>
                  </div>
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={selectedPerformanceTimeline}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                      <XAxis
                        dataKey="chartPointKey"
                        tick={{ fontSize: 10, fill: 'var(--text-secondary)' }}
                        tickFormatter={(_, index) => selectedPerformanceTimeline[index]?.displayDate ?? ''}
                        minTickGap={24}
                      />
                      <YAxis tickFormatter={(v) => formatTWD(Number(v))} tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} />
                      <Tooltip
                        labelFormatter={(_, payload) => {
                          const point = payload?.[0]?.payload as { displayDate?: string } | undefined;
                          return point?.displayDate ?? '';
                        }}
                        formatter={(value: number, name: string) => [formatTWD(Number(value)), name === 'marketValueTwd' ? '現值' : '成本']}
                        contentStyle={{
                          backgroundColor: 'var(--card-bg)',
                          border: '1px solid var(--border-color)',
                          borderRadius: '0.75rem',
                          color: 'var(--text-primary)',
                        }}
                      />
                      <Legend />
                      <Line type="monotone" dataKey="costBasisTwd" name="成本" stroke="#F59E0B" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="marketValueTwd" name="現值" stroke="#3B82F6" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)]/30 p-3">
                  <div className="mb-2 text-sm font-semibold">交易摘要</div>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="opacity-60">交易筆數</span>
                      <span className="font-semibold">{selectedTransactions.length}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="opacity-60">目前庫存</span>
                      <span className="font-semibold">{formatShares(Number(selectedHolding.shares))}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="opacity-60">平均成本</span>
                      <span className="font-semibold">{formatByCurrency(Number(selectedHolding.avg_cost ?? 0), selectedHolding.currency ?? 'TWD')}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="opacity-60">價格狀態</span>
                      <span className="font-semibold">{getPriceStatusLabel(selectedHolding)}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}

            {selectedTransactions.length > 0 ? (
              <div className="overflow-x-auto rounded-2xl border border-[var(--border-color)]">
                <table className="w-full text-xs sm:text-sm">
                  <thead className="bg-[var(--bg-secondary)] text-[var(--text-secondary)]">
                    <tr>
                      <th className="px-3 py-2 text-left">日期</th>
                      <th className="px-3 py-2 text-left">類型</th>
                      <th className="px-3 py-2 text-right">股數</th>
                      <th className="px-3 py-2 text-right">均價</th>
                      <th className="px-3 py-2 text-right">成本基礎(TWD)</th>
                      <th className="px-3 py-2 text-right">損益(TWD)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedTimeline.map((point, idx) => {
                      const tx = selectedTransactions[idx];
                      return (
                        <tr key={tx.id} className="border-t border-[var(--border-color)]">
                          <td className="px-3 py-2 font-mono">{tx.date}</td>
                          <td className="px-3 py-2">{tx.type === 'buy' ? '買入' : '賣出'}</td>
                          <td className="px-3 py-2 text-right font-mono">{formatShares(point.shares)}</td>
                          <td className="px-3 py-2 text-right">{formatByCurrency(point.avgCost, selectedHolding.currency ?? 'TWD')}</td>
                          <td className="px-3 py-2 text-right">{formatTWD(point.costBasisTwd)}</td>
                          <td className={`px-3 py-2 text-right font-semibold ${(point.unrealizedGainTwd ?? 0) >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                            {formatTWD(point.unrealizedGainTwd)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState title="這檔沒有交易紀錄" description="選擇其他持倉，或新增這檔標的的交易。" />
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
