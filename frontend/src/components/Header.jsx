import { RefreshCw } from 'lucide-react'
import ThemeToggle from './ThemeToggle'

export default function Header({ onRefresh, refreshing }) {
  return (
    <div className="bg-[var(--hermes-bg)] border-b border-blue-500/20 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
          <span className="text-blue-400 text-lg">📈</span>
        </div>
        <h1 className="text-xl font-semibold text-slate-100">個人財富管理</h1>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={onRefresh}
          className="text-slate-400 hover:text-white flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg hover:bg-white/10 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          刷新
        </button>
        <ThemeToggle />
      </div>
    </div>
  )
}