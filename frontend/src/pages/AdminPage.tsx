import { useState, useEffect, useCallback } from 'react';
import { Database, Activity, FileText, RefreshCw, Server } from 'lucide-react';
import { useGetDbStatsQuery, useGetScraperStatusQuery, useGetAuditLogsQuery } from '../store/apiSlice';
import { useTheme } from '../context/ThemeContext';
import type { DbStats, LogType, AuditLog } from '../types';

function LogTypeBadge({ type }: { type: LogType }) {
  const styles: Record<LogType, string> = {
    scrape: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    db_change: 'bg-green-500/20 text-green-400 border-green-500/30',
    api_call: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    error: 'bg-red-500/20 text-red-400 border-red-500/30',
  };
  const labels: Record<LogType, string> = { scrape: '爬蟲', db_change: '異動', api_call: 'API', error: '錯誤' };
  return (
    <span className={`text-xs px-2 py-0.5 rounded border font-mono ${styles[type] || ''}`}>
      {labels[type] || type}
    </span>
  );
}

const LOG_TYPE_OPTIONS: { value: LogType | ''; label: string }[] = [
  { value: '', label: '全部 - ' },
  { value: 'scrape', label: '爬蟲執行' },
  { value: 'db_change', label: '資料庫異動' },
  { value: 'api_call', label: 'API 呼叫' },
  { value: 'error', label: '錯誤' },
];

export default function AdminPage() {
  const { isDark } = useTheme();
  const [logTypeFilter, setLogTypeFilter] = useState<LogType | ''>('');

  const { data: dbStats, isLoading: loading } = useGetDbStatsQuery(undefined, { pollingInterval: 30_000 });
  const { data: scraperStatus } = useGetScraperStatusQuery(undefined, { pollingInterval: 30_000 });
  const { data: auditData, isLoading: logLoading, refetch } = useGetAuditLogsQuery(
    { log_type: logTypeFilter || undefined, limit: 100 },
    { pollingInterval: 15_000 }
  );

  const loadAuditLogs = useCallback(() => {
    refetch();
  }, [refetch]);

  useEffect(() => { loadAuditLogs(); }, [logTypeFilter]);

  const formatTimestamp = (ts: string) => {
    if (!ts) return '—';
    const d = new Date(ts);
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const mm = months[d.getMonth()];
    const dd = String(d.getDate()).padStart(2, '0');
    const yyyy = d.getFullYear();
    const yy = String(yyyy).slice(-2);
    const hh = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    const ss = String(d.getSeconds()).padStart(2, '0');
    return (
      <span className="whitespace-nowrap">
        {mm}-{dd}-{yy}<br/>{hh}:{min}:{ss}
      </span>
    );
  };

  const totalLogs = auditData?.total ?? 0;
  const auditLogs = auditData?.logs ?? [];

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <header className="sticky top-0 z-50 border-b border-[var(--border-color)] bg-[var(--bg-primary)]/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => window.location.href = '/'} className="p-2 rounded-lg hover:bg-[var(--bg-secondary)] transition-colors" title="返回Dashboard">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <h1 className="text-lg sm:text-xl font-bold flex items-center gap-2">
              <Server className="w-5 h-5" />
              <span>系統管理</span>
            </h1>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-4 sm:py-6 space-y-4 sm:space-y-6">
        {loading && !dbStats ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="animate-spin text-blue-500 w-8 h-8" />
          </div>
        ) : (
          <>
            {/* Database Stats */}
            {dbStats && (
              <>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                  <div className="card p-4 animate-fade-in">
                    <div className="flex items-center gap-2 opacity-60 mb-2"><Database className="w-4 h-4" /><span className="text-sm">資料庫大小</span></div>
                    <div className="text-2xl font-bold">{dbStats.total_size_mb} <span className="text-sm font-normal opacity-50">MB</span></div>
                  </div>
                  <div className="card p-4 animate-fade-in">
                    <div className="flex items-center gap-2 opacity-60 mb-2"><Activity className="w-4 h-4" /><span className="text-sm">資料表數量</span></div>
                    <div className="text-2xl font-bold">{dbStats.table_count}</div>
                  </div>
                  <div className="card p-4 animate-fade-in">
                    <div className="flex items-center gap-2 opacity-60 mb-2"><FileText className="w-4 h-4" /><span className="text-sm">日誌總數</span></div>
                    <div className="text-2xl font-bold">{totalLogs}</div>
                  </div>
                  <div className="card p-4 animate-fade-in">
                    <div className="flex items-center gap-2 opacity-60 mb-2"><Server className="w-4 h-4" /><span className="text-sm">上次維護</span></div>
                    <div className="text-2xl font-bold">{dbStats.last_vacuum ? new Date(dbStats.last_vacuum).toLocaleDateString() : 'N/A'}</div>
                    {dbStats.last_analyze && <div className="text-xs opacity-50 mt-1">Analyze</div>}
                  </div>
                </div>

                {/* Tables */}
                <div className="card overflow-hidden animate-fade-in">
                  <div className="px-4 py-3 border-b border-[var(--border-color)] flex items-center gap-2">
                    <Database className="w-4 h-4 opacity-60" />
                    <span className="text-sm font-semibold">資料表</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-[var(--bg-secondary)] text-[var(--text-secondary)]">
                        <tr>
                          <th className="text-left px-4 py-3">資料表</th>
                          <th className="text-right px-4 py-3">行數</th>
                          <th className="text-right px-4 py-3">大小</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dbStats.tables.map(t => (
                          <tr key={t.table_name} className="border-t border-[var(--border-color)] hover:bg-[var(--bg-secondary)]/50 transition-colors">
                            <td className="px-4 py-3 font-mono text-sm">{t.table_name}</td>
                            <td className="px-4 py-3 text-right">{t.row_count.toLocaleString()}</td>
                            <td className="px-4 py-3 text-right opacity-70">{(t.size_bytes / 1024).toFixed(1)} KB</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}

            {/* Scraper Status */}
            {scraperStatus && (
              <div className="card p-4 animate-fade-in">
                <h2 className="text-sm font-semibold opacity-60 mb-4 flex items-center gap-2">
                  <Activity className="w-4 h-4" /> 爬蟲狀態
                </h2>
                <div className="space-y-3">
                  {scraperStatus.scrapers.map(s => (
                    <div key={s.name} className="flex items-center justify-between p-3 bg-[var(--bg-secondary)] rounded-lg">
                      <div>
                        <div className="font-medium text-sm">{s.name}</div>
                        <div className="text-xs opacity-50">{s.last_run ? `上次: ${new Date(s.last_run).toLocaleString()}` : '從未執行'}</div>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded ${
                        s.status === 'running' ? 'bg-yellow-500/20 text-yellow-400' :
                        s.status === 'error' ? 'bg-red-500/20 text-red-400' :
                        'bg-green-500/20 text-green-400'
                      }`}>{s.status}</span>
                    </div>
                  ))}
                  {scraperStatus.next_scheduled_run && (
                    <div className="text-xs opacity-50 pt-2 border-t border-[var(--border-color)]">
                      排程: 美股 {scraperStatus.next_scheduled_run.us_market} / 台股 {scraperStatus.next_scheduled_run.tw_market}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Audit Log Table */}
            <div className="card overflow-hidden animate-fade-in">
              <div className="px-4 py-3 border-b border-[var(--border-color)] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 opacity-60" />
                  <span className="text-sm font-semibold">操作日誌</span>
                  <span className="text-xs opacity-50 ml-1">共 {totalLogs} 筆</span>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={logTypeFilter}
                    onChange={e => setLogTypeFilter(e.target.value as LogType | '')}
                    className="text-sm bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded px-2 py-1"
                  >
                    {LOG_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                  <button onClick={loadAuditLogs} className="p-1.5 rounded hover:bg-[var(--bg-secondary)] transition-colors" title="重新整理">
                    <RefreshCw className={`w-4 h-4 ${logLoading ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>

              {logLoading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="animate-spin text-blue-500 w-6 h-6" />
                </div>
              ) : auditLogs.length === 0 ? (
                <div className="p-8 text-center opacity-50 text-sm">
                  {totalLogs === 0 ? '尚無操作日誌' : '尚無符合條件的日誌'}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm min-w-[600px]">
                    <thead className="bg-[var(--bg-secondary)] text-[var(--text-secondary)]">
                      <tr>
                        <th className="text-left px-3 py-2 w-24">時間</th>
                        <th className="text-left px-3 py-2">類型 / 訊息</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.map((log: AuditLog) => (
                        <tr key={log.id} className="border-t border-[var(--border-color)] hover:bg-[var(--bg-secondary)]/50 transition-colors">
                          <td className="px-3 py-2 text-xs font-mono whitespace-nowrap align-top">{formatTimestamp(log.timestamp)}</td>
                          <td className="px-3 py-2 align-top">
                            <div className="flex items-center gap-2 min-w-0 flex-wrap">
                              <LogTypeBadge type={log.type} />
                              <span className="text-sm truncate flex-1" style={{minWidth:0}} title={log.message}>{log.message}</span>
                            </div>
                            {log.details && (
                              <div className="text-xs opacity-50 mt-1 pl-1 font-mono" title={JSON.stringify(log.details)}>
                                {log.type === 'scrape' ? (
                                  <>
                                    {log.details.source && `source=${log.details.source} `}
                                    {log.details.status && `status=${log.details.status}`}
                                  </>
                                ) : (
                                  <>
                                    {log.details.operation && `${log.details.operation} `}
                                    {log.details.table && `${log.details.table} `}
                                    {log.details.record_id != null && `id=${log.details.record_id}`}
                                  </>
                                )}
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
