import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { EmptyState } from '../UIState';
import { PIE_COLORS } from './shared';

interface OverviewPerformanceSectionProps {
  benchmarkSeries: Array<{ name: string; points: Array<{ date: string; normalized_value: number }> }>;
  hasSummaryValue: boolean;
  performanceChartData: Array<Record<string, string | number>>;
  performanceRange: 'today' | 'week' | 'month' | 'year' | 'all';
  setPerformanceRange: (range: 'today' | 'week' | 'month' | 'year' | 'all') => void;
}

export default function OverviewPerformanceSection({
  benchmarkSeries,
  hasSummaryValue,
  performanceChartData,
  performanceRange,
  setPerformanceRange,
}: OverviewPerformanceSectionProps) {
  if (!(performanceChartData.length > 0 || hasSummaryValue)) return null;

  return (
    <div className="card p-3 sm:p-6 animate-fade-in">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold opacity-60">資產淨值走勢</h2>
          <div className="mt-1 text-xs opacity-50">作為總覽的補充視角，觀察組合整體變化。</div>
        </div>
        <div className="flex flex-wrap gap-2">
          {(['today', 'week', 'month', 'year', 'all'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setPerformanceRange(range)}
              className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                performanceRange === range
                  ? 'border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)]'
                  : 'border-[var(--border-color)] bg-[var(--bg-secondary)]/40 opacity-70 hover:opacity-100'
              }`}
            >
              {range === 'today' ? '今日' : range === 'week' ? '本週' : range === 'month' ? '本月' : range === 'year' ? '今年' : '成立以來'}
            </button>
          ))}
        </div>
      </div>

      {performanceChartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={180} className="text-xs">
          <LineChart data={performanceChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} />
            <YAxis tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} tickFormatter={(v) => `${Number(v).toFixed(0)}`} />
            <Tooltip
              formatter={(v: number, name: string) => {
                const labels: Record<string, string> = { portfolio: '投資組合' };
                return [`${Number(v).toFixed(2)}`, labels[name] ?? name];
              }}
              contentStyle={{
                backgroundColor: 'var(--card-bg)',
                border: '1px solid var(--border-color)',
                borderRadius: '0.75rem',
                color: 'var(--text-primary)',
              }}
              labelStyle={{ color: 'var(--text-secondary)' }}
            />
            <Legend />
            <Line type="monotone" dataKey="portfolio" stroke="#3B82F6" strokeWidth={3} dot={false} name="投資組合" />
            {benchmarkSeries.map((series, idx) => (
              <Line
                key={series.name}
                type="monotone"
                dataKey={series.name}
                stroke={PIE_COLORS[(idx + 1) % PIE_COLORS.length]}
                strokeWidth={2}
                dot={false}
                name={series.name}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <EmptyState title="尚無資產走勢" description="新增持倉後，這裡會顯示資產淨值與基準比較。" />
      )}
    </div>
  );
}
