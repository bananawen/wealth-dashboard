import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Database, Activity, FileText, RefreshCw, Server } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

function StatCard({ icon: Icon, label, value, sub }) {
  return (
    <div className="card p-4 animate-fade-in">
      <div className="flex items-center gap-2 opacity-60 mb-2">
        <Icon className="w-4 h-4" />
        <span className="text-sm">{label}</span>
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {sub && <div className="text-xs opacity-50 mt-1">{sub}</div>}
    </div>
  )
}

export default function AdminPage() {
  const { isDark } = useTheme()
  const [dbStats, setDbStats] = useState(null)
  const [scraperStatus, setScraperStatus] = useState(null)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  const loadStats = async () => {
    setLoading(true)
    try {
      const [stats, scraper, logData] = await Promise.all([
        api.request('/admin/db/stats').catch(() => null),
        api.request('/admin/scraper/status').catch(() => null),
        api.request('/admin/logs/recent').catch(() => null),
      ])
      setDbStats(stats)
      setScraperStatus(scraper)
      setLogs(logData?.recent || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadStats() }, [])

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] transition-colors duration-300">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-[var(--border-color)] bg-[var(--bg-primary)]/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
          <h1 className="text-lg sm:text-xl font-bold flex items-center gap-2">
            <Server className="w-5 h-5" />
            <span>資料庫監控</span>
          </h1>
          <button 
            onClick={loadStats} 
            className="p-2 rounded-lg hover:bg-[var(--bg-secondary)] transition-colors flex items-center gap-1 text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </button>
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
                  <StatCard 
                    icon={Database} 
                    label="資料庫大小" 
                    value={dbStats.total_size_mb} 
                    sub="MB" 
                  />
                  <StatCard 
                    icon={Activity} 
                    label="資料表數量" 
                    value={dbStats.table_count} 
                  />
                  <StatCard 
                    icon={FileText} 
                    label="日誌行數" 
                    value={logs.length} 
                  />
                  <StatCard 
                    icon={Server} 
                    label="上次維護" 
                    value={dbStats.last_vacuum ? new Date(dbStats.last_vacuum).toLocaleDateString() : 'N/A'} 
                    sub={dbStats.last_analyze ? 'Analyze' : ''}
                  />
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
                  <Activity className="w-4 h-4" />
                  爬蟲狀態
                </h2>
                <div className="space-y-3">
                  {scraperStatus.scrapers.map(s => (
                    <div key={s.name} className="flex items-center justify-between p-3 bg-[var(--bg-secondary)] rounded-lg">
                      <div>
                        <div className="font-medium text-sm">{s.name}</div>
                        <div className="text-xs opacity-50">
                          {s.last_run ? `上次: ${new Date(s.last_run).toLocaleString()}` : '從未執行'}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`badge ${
                          s.status === 'running' ? 'badge-warning' :
                          s.status === 'error' ? 'badge-error' : 'badge-success'
                        }`}>
                          {s.status}
                        </span>
                      </div>
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

            {/* Recent Logs */}
            <div className="card overflow-hidden animate-fade-in">
              <div className="px-4 py-3 border-b border-[var(--border-color)] flex items-center gap-2">
                <FileText className="w-4 h-4 opacity-60" />
                <span className="text-sm font-semibold">最近日誌</span>
              </div>
              {logs.length > 0 ? (
                <div className="max-h-64 overflow-y-auto bg-[var(--bg-secondary)]">
                  <pre className="p-4 text-xs font-mono whitespace-pre-wrap">
                    {logs.join('')}
                  </pre>
                </div>
              ) : (
                <div className="p-8 text-center opacity-50">尚無日誌</div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}