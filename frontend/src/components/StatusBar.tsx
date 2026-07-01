import { useGetStatusQuery } from '../store/apiSlice';
import { Database, AlertCircle, CheckCircle, RefreshCw, Clock } from 'lucide-react';
import { SemanticBadge } from './UIState';

const REFRESH_INTERVAL = 60_000;

function StatusDot({ ok }: { ok?: boolean }) {
  if (ok) return <CheckCircle className="w-3 h-3 text-[var(--success)] inline-block" />;
  return <AlertCircle className="w-3 h-3 text-[var(--error)] inline-block" />;
}

interface StatusBarProps {
  isAdmin: boolean;
}

export default function StatusBar({ isAdmin }: StatusBarProps) {
  const { data: status, isLoading: loading, refetch } = useGetStatusQuery(undefined, {
    pollingInterval: REFRESH_INTERVAL,
    skip: !isAdmin,
  });

  const tableCount = status?.tables?.length ?? 0;
  const totalRows = status?.tables?.reduce((s, t) => s + t.row_count, 0) ?? 0;
  const scraper = status?.scrapers?.[0];
  const lastScraperTime = scraper?.last_run
    ? new Date(scraper.last_run).toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : null;

  return (
    <div className="overflow-x-hidden border-b border-[var(--accent)]/20 bg-[var(--bg-secondary)] px-3 py-1.5 sm:px-6">
      <div className="mx-auto flex max-w-7xl min-w-0 flex-wrap items-center gap-x-3 gap-y-1.5">
        {!isAdmin ? (
          <div className="flex min-w-0 items-center gap-1.5 text-xs text-[var(--text-muted)]">
            <Database className="w-3.5 h-3.5 text-[var(--accent)]" />
            <span>一般使用模式</span>
          </div>
        ) : (
          <>
        <div className="flex shrink-0 items-center gap-1.5 text-xs">
          <StatusDot ok={status?.connected} />
          <span className="text-[var(--text-secondary)] hidden sm:inline">DB</span>
          <SemanticBadge tone={status ? (status.connected ? 'success' : 'error') : 'loading'}>
            {status ? (status.connected ? '連線中' : '連線失敗') : '載入中…'}
          </SemanticBadge>
        </div>

        <div className="w-px h-4 bg-[var(--border-color)] hidden sm:block" />

        <div className="flex min-w-0 items-center gap-1.5 text-xs">
          <Database className="w-3.5 h-3.5 text-[var(--accent)]" />
          <span className="text-[var(--text-secondary)]">{tableCount} 表</span>
          <span className="text-[var(--text-muted)]">/</span>
          <span className="truncate text-[var(--text-primary)]">{totalRows.toLocaleString()} 筆</span>
        </div>

        <div className="w-px h-4 bg-[var(--border-color)] hidden sm:block" />

        <div className="hidden md:flex items-center gap-2 flex-1 min-w-0 overflow-hidden">
          <div className="flex-1 min-w-0 overflow-hidden">
            {status?.tables?.slice(0, 4).map(t => (
              <span key={t.table_name} className="inline-block">
                <span className="font-mono text-xs text-[var(--text-primary)]">{t.table_name}</span>
                <span className="text-xs text-[var(--text-muted)] mx-1">({t.row_count.toLocaleString()})</span>
              </span>
            ))}
            {status?.tables && status.tables.length > 4 && (
              <span className="text-xs text-[var(--text-muted)]">+{status.tables.length - 4} more</span>
            )}
          </div>
        </div>

        {lastScraperTime && (
          <>
            <div className="w-px h-4 bg-[var(--border-color)] hidden sm:block" />
            <div className="hidden items-center gap-1 text-xs sm:flex">
              <Clock className="w-3 h-3 text-[var(--text-muted)]" />
              <span className="text-[var(--text-muted)]">更新</span>
              <SemanticBadge tone="info" className="text-[10px]">
                {lastScraperTime}
              </SemanticBadge>
            </div>
          </>
        )}
          </>
        )}

        <button
          onClick={() => refetch()}
          disabled={!isAdmin}
          className="ml-auto flex shrink-0 items-center gap-1 rounded p-1 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-secondary)]"
          title="重新整理"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">{new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })}</span>
        </button>
      </div>
    </div>
  );
}
