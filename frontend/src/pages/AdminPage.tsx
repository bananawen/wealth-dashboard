import { useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Database,
  Download,
  FileText,
  HardDrive,
  Pause,
  Play,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Wifi,
  X,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import {
  useGetStatusQuery,
  useGetDbStatsQuery,
  useGetScraperStatusQuery,
  useGetAuditLogsQuery,
  useGetScraperRunsQuery,
  useTriggerScraperMutation,
  useSetScraperSchedulerMutation,
  useGetMissingDataReportQuery,
} from '../store/apiSlice';
import DatePicker from '../components/DatePicker';
import type {
  AdminStatus,
  AuditLog,
  DbStats,
  LogType,
  MissingDataItem,
  ScraperRunResponse,
} from '../types';
import { EmptyState, LoadingState, SemanticBadge } from '../components/UIState';

type AdminTab = 'overview' | 'database' | 'scraper' | 'logs';
type BadgeTone = 'neutral' | 'info' | 'success' | 'warning' | 'error' | 'loading' | 'stale' | 'estimated';

const LOG_TYPE_OPTIONS: { value: LogType | ''; label: string }[] = [
  { value: '', label: '全部' },
  { value: 'transaction', label: '交易異動' },
  { value: 'scraper', label: '爬蟲' },
  { value: 'auth', label: '帳號登入' },
  { value: 'admin', label: '系統管理' },
];

const ADMIN_TABS: { key: AdminTab; label: string; icon: LucideIcon }[] = [
  { key: 'overview', label: '總覽', icon: ShieldCheck },
  { key: 'database', label: '資料庫', icon: Database },
  { key: 'scraper', label: '價格與爬蟲', icon: Activity },
  { key: 'logs', label: 'Audit Log', icon: FileText },
];

const LOG_LABELS: Record<LogType, string> = {
  scraper: '爬蟲',
  transaction: '交易',
  auth: '帳號',
  admin: '系統',
};

function formatBytes(bytes?: number) {
  if (!bytes && bytes !== 0) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatTimestamp(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-TW', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

function formatDuration(ms?: number | null) {
  if (!ms && ms !== 0) return '—';
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
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

function statusTone(status?: string | null): BadgeTone {
  if (!status) return 'neutral';
  if (['success', 'fresh', 'ok', 'online', 'healthy'].includes(status)) return 'success';
  if (['warning', 'stale', 'running'].includes(status)) return 'warning';
  if (['error', 'missing', 'failed', 'offline'].includes(status)) return 'error';
  return 'info';
}

function detailValue(details: Record<string, unknown> | undefined, key: string) {
  const value = details?.[key];
  if (value === null || value === undefined || value === '') return null;
  return String(value);
}

function MetricCard({
  icon: Icon,
  label,
  value,
  detail,
  tone = 'neutral',
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
  detail?: string;
  tone?: BadgeTone;
}) {
  return (
    <div className="card p-4 min-h-28">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs text-[var(--text-secondary)]">{label}</div>
          <div className="mt-2 text-2xl font-semibold tabular-nums">{value}</div>
        </div>
        <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-2">
          <Icon className="h-4 w-4 text-[var(--text-secondary)]" />
        </div>
      </div>
      {detail ? <div className="mt-2 truncate text-xs text-[var(--text-muted)]" title={detail}>{detail}</div> : null}
      {tone !== 'neutral' ? <div className="mt-3"><SemanticBadge tone={tone}>{tone}</SemanticBadge></div> : null}
    </div>
  );
}

function SectionHeader({
  icon: Icon,
  title,
  meta,
  action,
}: {
  icon: LucideIcon;
  title: string;
  meta?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-color)] px-4 py-3">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-[var(--text-secondary)]" />
        <span className="text-sm font-semibold">{title}</span>
        {meta ? <span className="text-xs text-[var(--text-muted)]">{meta}</span> : null}
      </div>
      {action}
    </div>
  );
}

function IconButton({
  title,
  onClick,
  children,
  disabled = false,
}: {
  title: string;
  onClick: () => void;
  children: React.ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-color)] hover:bg-[var(--bg-secondary)] disabled:opacity-40"
    >
      {children}
    </button>
  );
}

function LogTypeBadge({ type }: { type: LogType }) {
  const tone: Record<LogType, BadgeTone> = {
    scraper: 'info',
    transaction: 'success',
    auth: 'neutral',
    admin: 'warning',
  };
  return <SemanticBadge tone={tone[type]}>{LOG_LABELS[type] || type}</SemanticBadge>;
}

function AuditLogRows({ logs }: { logs: AuditLog[] }) {
  return (
    <tbody>
      {logs.map(log => {
        const action = detailValue(log.details, 'action');
        const username = detailValue(log.details, 'username');
        const source = detailValue(log.details, 'source');
        const operation = detailValue(log.details, 'operation');
        const recordId = detailValue(log.details, 'record_id');
        return (
          <tr key={log.id} className="border-t border-[var(--border-color)] hover:bg-[var(--bg-secondary)]/50">
            <td className="whitespace-nowrap px-3 py-2 align-top font-mono text-xs">{formatTimestamp(log.timestamp)}</td>
            <td className="px-3 py-2 align-top">
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                <LogTypeBadge type={log.type} />
                {log.level ? <SemanticBadge tone={statusTone(log.level.toLowerCase())}>{log.level}</SemanticBadge> : null}
                <span className="min-w-0 flex-1 truncate text-sm" title={log.message}>{log.message}</span>
              </div>
              {log.details ? (
                <div className="mt-1 truncate font-mono text-xs text-[var(--text-muted)]" title={JSON.stringify(log.details)}>
                  {[action, username && `user=${username}`, source && `source=${source}`, operation, recordId && `id=${recordId}`]
                    .filter(Boolean)
                    .join(' · ')}
                </div>
              ) : null}
            </td>
            <td className="hidden px-3 py-2 text-right align-top text-xs text-[var(--text-muted)] md:table-cell">
              {log.symbol ?? '—'}
            </td>
          </tr>
        );
      })}
    </tbody>
  );
}

function DatabaseTable({ dbStats }: { dbStats: DbStats }) {
  return (
    <div className="card overflow-hidden">
      <SectionHeader icon={Database} title="資料表" meta={`${dbStats.table_count} tables`} />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-sm">
          <thead className="bg-[var(--bg-secondary)] text-[var(--text-secondary)]">
            <tr>
              <th className="px-4 py-3 text-left">資料表</th>
              <th className="px-4 py-3 text-right">行數</th>
              <th className="px-4 py-3 text-right">大小</th>
            </tr>
          </thead>
          <tbody>
            {dbStats.tables.map(table => (
              <tr key={table.table_name} className="border-t border-[var(--border-color)] hover:bg-[var(--bg-secondary)]/50">
                <td className="px-4 py-3 font-mono">{table.table_name}</td>
                <td className="px-4 py-3 text-right tabular-nums">{table.row_count.toLocaleString()}</td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--text-secondary)]">{formatBytes(table.size_bytes)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ScraperRunsTable({ runs }: { runs: ScraperRunResponse[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-sm">
        <thead className="bg-[var(--bg-secondary)] text-[var(--text-secondary)]">
          <tr>
            <th className="px-3 py-2 text-left">時間</th>
            <th className="px-3 py-2 text-left">作業</th>
            <th className="px-3 py-2 text-left">結果</th>
            <th className="px-3 py-2 text-right">成功 / 失敗</th>
            <th className="px-3 py-2 text-right">筆數</th>
            <th className="px-3 py-2 text-right">耗時</th>
            <th className="px-3 py-2 text-left">原因</th>
          </tr>
        </thead>
        <tbody>
          {runs.map(run => (
            <tr key={run.id} className="border-t border-[var(--border-color)] hover:bg-[var(--bg-secondary)]/50">
              <td className="whitespace-nowrap px-3 py-2 align-top font-mono text-xs">{formatTimestamp(run.timestamp)}</td>
              <td className="px-3 py-2 align-top">
                <div className="font-medium">{run.job_name}</div>
                <div className="text-xs text-[var(--text-muted)]">{run.trigger} / {run.target}{run.symbol ? ` / ${run.symbol}` : ''}</div>
              </td>
              <td className="px-3 py-2 align-top">
                <SemanticBadge tone={statusTone(run.status)}>{run.status}</SemanticBadge>
              </td>
              <td className="px-3 py-2 text-right tabular-nums">{run.success_count} / {run.failure_count}</td>
              <td className="px-3 py-2 text-right tabular-nums">{run.records_fetched.toLocaleString()}</td>
              <td className="px-3 py-2 text-right tabular-nums">{formatDuration(run.duration_ms)}</td>
              <td className="max-w-56 truncate px-3 py-2 text-xs text-[var(--text-muted)]" title={run.error_reason ?? ''}>{run.error_reason ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MissingDataTable({ items }: { items: MissingDataItem[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-sm">
        <thead className="bg-[var(--bg-secondary)] text-[var(--text-secondary)]">
          <tr>
            <th className="px-3 py-2 text-left">股票</th>
            <th className="px-3 py-2 text-left">最新日期</th>
            <th className="px-3 py-2 text-right">缺口(日)</th>
            <th className="px-3 py-2 text-right">歷史筆數</th>
            <th className="px-3 py-2 text-left">狀態</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={`${item.region}-${item.symbol}`} className="border-t border-[var(--border-color)] hover:bg-[var(--bg-secondary)]/50">
              <td className="px-3 py-2">
                <div className="font-medium">{item.symbol}</div>
                <div className="text-xs text-[var(--text-muted)]">{item.region} / {item.currency}</div>
              </td>
              <td className="px-3 py-2 font-mono text-xs">{item.latest_price_date ?? '—'}</td>
              <td className="px-3 py-2 text-right tabular-nums">{item.gap_days ?? '—'}</td>
              <td className="px-3 py-2 text-right tabular-nums">{item.history_rows.toLocaleString()}</td>
              <td className="px-3 py-2"><SemanticBadge tone={statusTone(item.status)}>{item.status}</SemanticBadge></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminPage() {
  const defaultLogDateRange = getRelativeDateRange(30);
  const [activeTab, setActiveTab] = useState<AdminTab>('overview');
  const [logTypeFilter, setLogTypeFilter] = useState<LogType | ''>('');
  const [logSearch, setLogSearch] = useState('');
  const [logStartDate, setLogStartDate] = useState(() => defaultLogDateRange.start);
  const [logEndDate, setLogEndDate] = useState(() => defaultLogDateRange.end);
  const [manualSymbol, setManualSymbol] = useState('');
  const [triggerMode, setTriggerMode] = useState<'single' | 'all_holdings' | 'backfill_gaps'>('single');

  const { data: status } = useGetStatusQuery(undefined, { pollingInterval: 30_000 });
  const { data: dbStats, isLoading: dbLoading, refetch: refetchDbStats } = useGetDbStatsQuery(undefined, { pollingInterval: 30_000 });
  const { data: scraperStatus, refetch: refetchScraperStatus } = useGetScraperStatusQuery(undefined, { pollingInterval: 30_000 });
  const { data: scraperRuns, refetch: refetchRuns } = useGetScraperRunsQuery(20, { pollingInterval: 60_000 });
  const { data: missingData, refetch: refetchMissingData } = useGetMissingDataReportQuery(undefined, { pollingInterval: 120_000 });
  const { data: auditData, isLoading: logLoading, refetch: refetchLogs } = useGetAuditLogsQuery(
    {
      log_type: logTypeFilter || undefined,
      q: logSearch || undefined,
      start_date: logStartDate || undefined,
      end_date: logEndDate || undefined,
      limit: 100,
    },
    { pollingInterval: 15_000 },
  );
  const [triggerScraper, { isLoading: triggerLoading }] = useTriggerScraperMutation();
  const [setScraperScheduler, { isLoading: toggleLoading }] = useSetScraperSchedulerMutation();

  const adminStatus = status as AdminStatus | undefined;
  const runtime = scraperStatus;
  const totalLogs = auditData?.total ?? 0;
  const auditLogs = auditData?.logs ?? [];
  const runs = scraperRuns ?? [];
  const missingItems = missingData ?? [];

  const systemIssues = useMemo(() => {
    const issues: string[] = [];
    if (adminStatus && !adminStatus.connected) issues.push('資料庫連線異常');
    if (runtime?.last_error) issues.push(runtime.last_error);
    if (adminStatus?.price_sources?.some(source => source.status === 'error')) issues.push('價格來源有錯誤');
    if (runs.some(run => run.status === 'error')) issues.push('最近爬蟲執行失敗');
    return issues;
  }, [adminStatus, runtime, runs]);

  const buildLogQueryString = () => {
    const params = new URLSearchParams();
    if (logTypeFilter) params.set('log_type', logTypeFilter);
    if (logSearch) params.set('q', logSearch);
    if (logStartDate) params.set('start_date', logStartDate);
    if (logEndDate) params.set('end_date', logEndDate);
    return params.toString();
  };

  const applyLogDateRange = (range: 'today' | '7d' | '30d' | 'all') => {
    if (range === 'all') {
      setLogStartDate('');
      setLogEndDate('');
      return;
    }
    const days = range === 'today' ? 1 : range === '7d' ? 7 : 30;
    const nextRange = getRelativeDateRange(days);
    setLogStartDate(nextRange.start);
    setLogEndDate(nextRange.end);
  };

  const clearLogFilters = () => {
    setLogSearch('');
    const nextRange = getRelativeDateRange(30);
    setLogStartDate(nextRange.start);
    setLogEndDate(nextRange.end);
    setLogTypeFilter('');
  };

  const handleDownload = async (url: string, filename: string) => {
    const token = localStorage.getItem('token');
    const response = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!response.ok) throw new Error(`下載失敗：${response.status}`);
    const blob = await response.blob();
    const objectUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objectUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(objectUrl);
  };

  const refreshActiveTab = async () => {
    if (activeTab === 'database') {
      await refetchDbStats();
      return;
    }
    if (activeTab === 'scraper') {
      await Promise.all([refetchScraperStatus(), refetchRuns(), refetchMissingData()]);
      return;
    }
    if (activeTab === 'logs') {
      await refetchLogs();
      return;
    }
    await Promise.all([refetchDbStats(), refetchScraperStatus(), refetchRuns(), refetchMissingData(), refetchLogs()]);
  };

  const handleToggleScheduler = async (enabled: boolean) => {
    await setScraperScheduler({ enabled }).unwrap();
    await refetchScraperStatus();
  };

  const handleTriggerScraper = async () => {
    const body = triggerMode === 'single'
      ? { mode: triggerMode, symbol: manualSymbol.trim().toUpperCase() }
      : { mode: triggerMode };
    await triggerScraper(body as { mode: 'single' | 'all_holdings' | 'backfill_gaps'; symbol?: string }).unwrap();
    await Promise.all([refetchScraperStatus(), refetchRuns(), refetchMissingData()]);
  };

  const renderOverview = () => {
    const priceSources = adminStatus?.price_sources ?? [];
    const healthyPriceSources = priceSources.filter(source => source.status !== 'error').length;
    const latestRun = runs[0];
    const statusMessage = systemIssues[0]
      ?? (runtime?.running ? '爬蟲正在執行' : '核心服務正常');

    return (
      <div className="space-y-3 sm:space-y-4">
        <div className="card p-3 sm:p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="text-sm font-semibold">Owner 系統工具區</div>
              <div className="mt-1 text-xs text-[var(--text-muted)]">
                目前站點採單一使用者部署，`admin` 權限只用於備份、爬蟲、版本與操作日誌管理。
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <SemanticBadge tone="info">單一使用者</SemanticBadge>
              <SemanticBadge tone="warning">Owner / Admin</SemanticBadge>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:gap-3 xl:grid-cols-4">
          <div className="card p-3 sm:p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-[11px] text-[var(--text-muted)] sm:text-xs">系統健康</div>
                <div className={`mt-1 text-lg font-semibold sm:text-2xl ${systemIssues.length === 0 ? 'text-[var(--success)]' : 'text-[var(--warning)]'}`}>
                  {systemIssues.length === 0 ? '正常' : '注意'}
                </div>
              </div>
              <ShieldCheck className="h-5 w-5 shrink-0 text-[var(--text-secondary)]" />
            </div>
          </div>

          <div className="card p-3 sm:p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-[11px] text-[var(--text-muted)] sm:text-xs">資料庫</div>
                <div className="mt-1 truncate text-lg font-semibold tabular-nums sm:text-2xl">
                  {formatBytes(adminStatus?.database_size_bytes ?? dbStats?.total_size_bytes)}
                </div>
              </div>
              <HardDrive className="h-5 w-5 shrink-0 text-[var(--text-secondary)]" />
            </div>
          </div>

          <div className="card p-3 sm:p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-[11px] text-[var(--text-muted)] sm:text-xs">排程</div>
                <div className="mt-1 text-lg font-semibold sm:text-2xl">
                  {runtime?.enabled ? '啟用' : '停用'}
                </div>
              </div>
              <Activity className="h-5 w-5 shrink-0 text-[var(--text-secondary)]" />
            </div>
          </div>

          <div className="card p-3 sm:p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-[11px] text-[var(--text-muted)] sm:text-xs">Audit Log</div>
                <div className="mt-1 text-lg font-semibold tabular-nums sm:text-2xl">
                  {totalLogs.toLocaleString()}
                </div>
              </div>
              <FileText className="h-5 w-5 shrink-0 text-[var(--text-secondary)]" />
            </div>
          </div>
        </div>

        <div className="card p-3 sm:p-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="flex min-w-0 items-center gap-2">
              {systemIssues.length === 0 ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-[var(--success)]" />
              ) : (
                <AlertTriangle className="h-4 w-4 shrink-0 text-[var(--warning)]" />
              )}
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{statusMessage}</div>
                <div className="text-xs text-[var(--text-muted)]">重點狀態</div>
              </div>
            </div>

            <div className="flex min-w-0 items-center gap-2">
              <Wifi className="h-4 w-4 shrink-0 text-[var(--text-secondary)]" />
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">
                  價格來源 {healthyPriceSources} / {priceSources.length}
                </div>
                <div className="text-xs text-[var(--text-muted)]">詳細狀態在價格與爬蟲</div>
              </div>
            </div>

            <div className="flex min-w-0 items-center gap-2">
              <Clock3 className="h-4 w-4 shrink-0 text-[var(--text-secondary)]" />
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">
                  {latestRun ? formatTimestamp(latestRun.timestamp) : '尚無執行紀錄'}
                </div>
                <div className="text-xs text-[var(--text-muted)]">最近爬蟲執行</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderDatabase = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard icon={Database} label="資料庫大小" value={`${dbStats?.total_size_mb ?? 0} MB`} />
        <MetricCard icon={Activity} label="資料表數量" value={dbStats?.table_count ?? 0} />
        <MetricCard icon={Server} label="上次 Vacuum" value={dbStats?.last_vacuum ? new Date(dbStats.last_vacuum).toLocaleDateString('zh-TW') : 'N/A'} />
        <MetricCard icon={CheckCircle2} label="上次 Analyze" value={dbStats?.last_analyze ? new Date(dbStats.last_analyze).toLocaleDateString('zh-TW') : 'N/A'} />
      </div>
      {dbStats ? <DatabaseTable dbStats={dbStats} /> : <LoadingState title="載入資料庫資訊" />}
    </div>
  );

  const renderScraper = () => (
    <div className="grid min-w-0 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
      <div className="min-w-0 space-y-4">
        <div className="card min-w-0 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="text-sm font-semibold">排程控制</div>
              <div className="mt-1 text-xs text-[var(--text-muted)]">{runtime?.timezone ?? 'Asia/Taipei'}</div>
            </div>
            <div className="flex flex-wrap gap-2">
              <SemanticBadge tone={runtime?.enabled ? 'success' : 'neutral'}>
                {runtime?.enabled ? '啟用' : '停用'}
              </SemanticBadge>
              <SemanticBadge tone={runtime?.running ? 'warning' : 'neutral'}>
                {runtime?.running ? '執行中' : '閒置'}
              </SemanticBadge>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleToggleScheduler(true)}
              disabled={toggleLoading || Boolean(runtime?.enabled)}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-[var(--success)]/15 px-3 py-2 text-sm text-[var(--success)] disabled:opacity-40"
            >
              <Play className="h-4 w-4" /> 啟用
            </button>
            <button
              type="button"
              onClick={() => handleToggleScheduler(false)}
              disabled={toggleLoading || !runtime?.enabled}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-[var(--error)]/15 px-3 py-2 text-sm text-[var(--error)] disabled:opacity-40"
            >
              <Pause className="h-4 w-4" /> 停用
            </button>
          </div>
          {runtime?.last_error ? (
            <div className="mt-3 flex gap-2 rounded-lg border border-[var(--error)]/30 bg-[var(--error)]/10 p-3 text-xs text-[var(--error)]">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{runtime.last_error}</span>
            </div>
          ) : null}
        </div>

        <div className="card min-w-0 p-4">
          <div className="text-sm font-semibold">手動觸發</div>
          <div className="mt-3 space-y-2">
            <select
              value={triggerMode}
              onChange={e => setTriggerMode(e.target.value as 'single' | 'all_holdings' | 'backfill_gaps')}
              className="input-field py-2 text-sm"
            >
              <option value="single">單一股票</option>
              <option value="all_holdings">全部持倉</option>
              <option value="backfill_gaps">補缺口</option>
            </select>
            {triggerMode === 'single' ? (
              <input
                value={manualSymbol}
                onChange={e => setManualSymbol(e.target.value)}
                placeholder="輸入股票代號"
                className="input-field py-2 text-sm uppercase"
              />
            ) : null}
            <button
              type="button"
              onClick={handleTriggerScraper}
              disabled={triggerLoading || (triggerMode === 'single' && !manualSymbol.trim())}
              className="btn-primary inline-flex w-full items-center justify-center gap-2 disabled:opacity-40"
            >
              <Zap className="h-4 w-4" /> 觸發執行
            </button>
          </div>
        </div>

        <div className="card min-w-0 overflow-hidden">
          <SectionHeader icon={Clock3} title="下一次排程" />
          <div className="divide-y divide-[var(--border-color)]">
            {(runtime?.next_runs ?? []).map(job => (
              <div key={job.id} className="min-w-0 px-4 py-3 text-sm">
                <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
                  <span className="min-w-0 truncate font-medium">{job.name}</span>
                  <span className="max-w-full truncate font-mono text-xs text-[var(--text-muted)]">{job.id}</span>
                </div>
                <div className="mt-1 break-words text-xs text-[var(--text-muted)]">{job.trigger}</div>
                <div className="mt-1 text-xs">{formatTimestamp(job.next_run_time)}</div>
              </div>
            ))}
            {(runtime?.next_runs?.length ?? 0) === 0 ? <div className="p-4"><EmptyState title="目前沒有排程" /></div> : null}
          </div>
        </div>
      </div>

      <div className="min-w-0 space-y-4">
        <div className="card min-w-0 overflow-hidden">
          <SectionHeader
            icon={Activity}
            title="爬蟲執行紀錄"
            meta={`${runs.length} rows`}
            action={
              <IconButton title="重新整理" onClick={() => void Promise.all([refetchRuns(), refetchScraperStatus(), refetchMissingData()])}>
                <RefreshCw className="h-4 w-4" />
              </IconButton>
            }
          />
          {runs.length ? <ScraperRunsTable runs={runs} /> : <div className="p-4"><EmptyState title="尚無執行紀錄" /></div>}
        </div>

        <div className="card min-w-0 overflow-hidden">
          <SectionHeader
            icon={FileText}
            title="缺資料掃描報告"
            meta={`${missingItems.length} rows`}
            action={
              <IconButton title="重新整理" onClick={() => void refetchMissingData()}>
                <RefreshCw className="h-4 w-4" />
              </IconButton>
            }
          />
          {missingItems.length ? <MissingDataTable items={missingItems} /> : <div className="p-4"><EmptyState title="沒有找到缺資料項目" /></div>}
        </div>
      </div>
    </div>
  );

  const renderLogs = () => (
    <div className="card overflow-hidden">
      <SectionHeader
        icon={FileText}
        title="操作日誌"
        meta={`共 ${totalLogs.toLocaleString()} 筆`}
        action={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleDownload(`/api/admin/logs/export.csv?${buildLogQueryString()}`, 'audit-logs.csv')}
              className="inline-flex items-center gap-2 rounded-lg border border-[var(--border-color)] px-3 py-2 text-sm hover:bg-[var(--bg-secondary)]"
            >
              <Download className="h-4 w-4" /> CSV
            </button>
            <IconButton title="重新整理" onClick={() => void refetchLogs()}>
              <RefreshCw className={`h-4 w-4 ${logLoading ? 'animate-spin' : ''}`} />
            </IconButton>
          </div>
        }
      />
      <div className="space-y-3 border-b border-[var(--border-color)] bg-[var(--bg-secondary)]/50 p-3">
        <div className="grid min-w-0 gap-2 lg:grid-cols-[minmax(0,1fr)_180px]">
          <div className="relative min-w-0">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              value={logSearch}
              onChange={e => setLogSearch(e.target.value)}
              placeholder="搜尋訊息 / 詳細內容"
              className="input-field min-w-0 py-2 pl-9 text-sm"
            />
          </div>
          <select
            value={logTypeFilter}
            onChange={e => setLogTypeFilter(e.target.value as LogType | '')}
            className="input-field min-w-0 py-2 text-sm"
          >
            {LOG_TYPE_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </div>

        <div className="grid min-w-0 gap-2 xl:grid-cols-[auto_minmax(0,1fr)_auto]">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            {[
              { label: '今天', value: 'today' as const },
              { label: '7 天', value: '7d' as const },
              { label: '30 天', value: '30d' as const },
              { label: '全部', value: 'all' as const },
            ].map(option => (
              <button
                key={option.value}
                type="button"
                onClick={() => applyLogDateRange(option.value)}
                className="rounded-lg border border-[var(--border-color)] px-3 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-primary)] hover:text-[var(--text-primary)]"
              >
                {option.label}
              </button>
            ))}
          </div>

          <div className="grid min-w-0 gap-2 sm:grid-cols-2">
            <label className="min-w-0 text-xs text-[var(--text-muted)]">
              <span className="mb-1 block">起始日期</span>
              <DatePicker value={logStartDate} onChange={setLogStartDate} allowClear placeholderLabel="年" yearRange={12} />
            </label>
            <label className="min-w-0 text-xs text-[var(--text-muted)]">
              <span className="mb-1 block">結束日期</span>
              <DatePicker value={logEndDate} onChange={setLogEndDate} allowClear placeholderLabel="年" yearRange={12} />
            </label>
          </div>

          <button
            type="button"
            onClick={clearLogFilters}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-[var(--border-color)] px-3 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-primary)] hover:text-[var(--text-primary)]"
          >
            <X className="h-4 w-4" />
            清除
          </button>
        </div>

        <div className="flex min-w-0 items-center gap-2 text-xs text-[var(--text-muted)]">
          <CalendarDays className="h-4 w-4 shrink-0" />
          <span className="truncate">
            目前範圍：{logStartDate || '最早'} - {logEndDate || '最新'}
          </span>
        </div>
      </div>

      {logLoading ? (
        <div className="p-8"><LoadingState title="載入操作日誌" /></div>
      ) : auditLogs.length === 0 ? (
        <div className="p-8">
          <EmptyState
            title={totalLogs === 0 ? '尚無操作日誌' : '尚無符合條件的日誌'}
            description={totalLogs === 0 ? '系統操作會顯示在這裡。' : '請調整搜尋條件或時間範圍。'}
          />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-sm">
            <thead className="bg-[var(--bg-secondary)] text-[var(--text-secondary)]">
              <tr>
                <th className="px-3 py-2 text-left">時間</th>
                <th className="px-3 py-2 text-left">類型 / 訊息</th>
                <th className="hidden px-3 py-2 text-right md:table-cell">標的</th>
              </tr>
            </thead>
            <AuditLogRows logs={auditLogs} />
          </table>
        </div>
      )}
    </div>
  );

  const isInitialLoading = dbLoading && !dbStats;

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <header className="sticky top-0 z-50 border-b border-[var(--border-color)] bg-[var(--bg-primary)]/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => { window.location.href = '/'; }}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg hover:bg-[var(--bg-secondary)]"
              title="返回 Dashboard"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div className="min-w-0">
              <h1 className="flex items-center gap-2 text-lg font-semibold sm:text-xl">
                <Server className="h-5 w-5" />
                <span>系統管理</span>
              </h1>
              <div className="mt-0.5 truncate text-xs text-[var(--text-muted)]">
                {adminStatus?.version?.version ?? 'unknown'} · {formatTimestamp(adminStatus?.version?.deployed_at)}
              </div>
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-lg border border-[var(--accent)]/25 bg-[var(--accent)]/10 px-3 py-2 text-xs text-[var(--accent)] sm:flex">
            <ShieldCheck className="h-4 w-4" />
            <span>單一使用者部署 / Owner 系統工具</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleDownload('/api/admin/export/transactions.csv', 'transactions.csv')}
              className="inline-flex items-center gap-2 rounded-lg border border-[var(--border-color)] px-3 py-2 text-sm hover:bg-[var(--bg-secondary)]"
            >
              <Download className="h-4 w-4" />
              <span className="hidden sm:inline">交易 CSV</span>
            </button>
            <button
              type="button"
              onClick={() => handleDownload('/api/admin/backup/sqlite', 'wealth-backup.db')}
              className="inline-flex items-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm text-white hover:bg-[var(--accent-hover)]"
            >
              <HardDrive className="h-4 w-4" />
              <span className="hidden sm:inline">SQLite 備份</span>
            </button>
            <IconButton title="重新整理目前頁籤" onClick={() => void refreshActiveTab()}>
              <RefreshCw className="h-4 w-4" />
            </IconButton>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 px-4 py-4 sm:px-6 sm:py-6">
        <div className="flex gap-2 overflow-x-auto border-b border-[var(--border-color)] pb-2">
          {ADMIN_TABS.map(tab => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
                  active
                    ? 'bg-[var(--accent)] text-white'
                    : 'border border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {isInitialLoading ? (
          <div className="py-12">
            <LoadingState title="載入系統管理資料" description="正在同步資料庫、排程與日誌資訊。" />
          </div>
        ) : (
          <>
            {activeTab === 'overview' ? renderOverview() : null}
            {activeTab === 'database' ? renderDatabase() : null}
            {activeTab === 'scraper' ? renderScraper() : null}
            {activeTab === 'logs' ? renderLogs() : null}
          </>
        )}
      </main>
    </div>
  );
}
