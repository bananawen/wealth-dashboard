import { RefreshCw } from 'lucide-react';
import ThemeToggle from './ThemeToggle';

interface HeaderProps {
  onRefresh: () => void;
  refreshing: boolean;
}

export default function Header({ onRefresh, refreshing }: HeaderProps) {
  return (
    <div className="bg-[var(--bg-primary)] border-b border-blue-500/20 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
          <span className="text-blue-400 text-lg">📈</span>
        </div>
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">個人財富管理</h1>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={onRefresh}
          className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg hover:bg-[var(--bg-secondary)] transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          刷新
        </button>
        <ThemeToggle />
      </div>
    </div>
  );
}