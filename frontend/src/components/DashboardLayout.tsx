import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Clock, Database, Plus, Settings, Sun, Moon, Wallet, ArrowUpCircle, LogOut, TrendingUp, ChevronDown, X } from 'lucide-react';
import ChangePasswordForm from './ChangePasswordForm';
import { useTheme } from '../context/ThemeContext';
import StatusBar from './StatusBar';
import type { VersionInfo } from '../types';
import type { DashboardView } from '../types/dashboard';

interface DashboardLayoutProps {
  children: ReactNode;
  isAdmin: boolean;
  onLogout: () => void;
  onNavigateToAdmin: () => void;
  versionInfo?: VersionInfo;
  view: DashboardView;
}

export default function DashboardLayout({
  children,
  isAdmin,
  onLogout,
  onNavigateToAdmin,
  versionInfo,
  view,
}: DashboardLayoutProps) {
  const { toggleTheme, isDark } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuOpen) return undefined;

    const handlePointerDown = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuOpen(false);
    };

    window.addEventListener('mousedown', handlePointerDown);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('mousedown', handlePointerDown);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [menuOpen]);

  useEffect(() => {
    if (!changePasswordOpen) return undefined;

    const handlePointerDown = (event: MouseEvent) => {
      if (dialogRef.current && !dialogRef.current.contains(event.target as Node)) {
        setChangePasswordOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setChangePasswordOpen(false);
    };

    window.addEventListener('mousedown', handlePointerDown);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('mousedown', handlePointerDown);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [changePasswordOpen]);

  const handleThemeToggle = () => {
    toggleTheme();
    setMenuOpen(false);
  };

  const handleLogoutClick = () => {
    setMenuOpen(false);
    onLogout();
  };

  const handleAdminClick = () => {
    setMenuOpen(false);
    onNavigateToAdmin();
  };

  const handleChangePasswordClick = () => {
    setMenuOpen(false);
    setChangePasswordOpen(true);
  };

  return (
    <div className="min-h-screen overflow-x-hidden bg-[var(--bg-primary)] text-[var(--text-primary)] transition-colors duration-300">
      <header className="sticky top-0 z-50 border-b border-[var(--border-color)] bg-[var(--bg-primary)]/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl min-w-0 items-center justify-between gap-3 px-3 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Link
              to="/overview"
              className="flex min-w-0 items-center gap-2 rounded-lg px-1 py-1 text-base font-bold transition-colors hover:text-[var(--accent)] sm:text-lg"
            >
              <span className="shrink-0 text-xl">📈</span>
              <span className="hidden truncate sm:inline">個人財富管理</span>
              <span className="truncate sm:hidden">總覽</span>
            </Link>
            <div className={`hidden rounded-lg border px-2 py-1 text-[11px] sm:block ${
              isAdmin
                ? 'border-[var(--accent)]/30 bg-[var(--accent)]/10 text-[var(--accent)]'
                : 'border-[var(--border-color)] bg-[var(--bg-secondary)]/50 text-[var(--text-muted)]'
            }`}>
              {isAdmin ? 'Owner / 系統管理已啟用' : '單一使用者模式'}
            </div>
          </div>
          {versionInfo && (
            <div className="hidden items-center gap-3 text-xs opacity-60 lg:flex">
              <span className="font-mono">v{versionInfo.version}</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {versionInfo.last_updated ? new Date(versionInfo.last_updated).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' }) : ''}
              </span>
            </div>
          )}
          <div ref={menuRef} className="relative flex shrink-0 items-center">
            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm transition-colors ${
                menuOpen
                  ? 'border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)]'
                  : 'border-[var(--border-color)] bg-[var(--bg-secondary)]/55 hover:border-[var(--accent)]/40 hover:bg-[var(--bg-secondary)]'
              }`}
              aria-expanded={menuOpen}
              aria-haspopup="menu"
            >
              <span className="hidden sm:inline">操作</span>
              <span className="sm:hidden">選單</span>
              <ChevronDown className={`h-4 w-4 transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-[calc(100%+0.5rem)] z-50 w-56 rounded-2xl border border-[var(--border-color)] bg-[var(--card-bg)] p-2 shadow-2xl">
                <div className="px-3 py-2 text-xs text-[var(--text-muted)]">
                  快捷操作
                </div>
                {isAdmin && (
                  <button
                    type="button"
                    onClick={handleAdminClick}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm transition-colors hover:bg-[var(--bg-secondary)]"
                  >
                    <Database className="h-4 w-4 text-[var(--accent)]" />
                    <span>系統管理</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleChangePasswordClick}
                  className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm transition-colors hover:bg-[var(--bg-secondary)]"
                >
                  <Settings className="h-4 w-4 text-[var(--text-secondary)]" />
                  <span>修改密碼</span>
                </button>
                <button
                  type="button"
                  onClick={handleThemeToggle}
                  className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm transition-colors hover:bg-[var(--bg-secondary)]"
                >
                  {isDark ? <Sun className="h-4 w-4 text-[var(--warning)]" /> : <Moon className="h-4 w-4 text-[var(--text-secondary)]" />}
                  <span>{isDark ? '切換為淺色' : '切換為深色'}</span>
                </button>
                <div className="my-2 border-t border-[var(--border-color)]" />
                <button
                  type="button"
                  onClick={handleLogoutClick}
                  className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm text-[var(--error)] transition-colors hover:bg-[var(--error)]/8"
                >
                  <LogOut className="h-4 w-4" />
                  <span>登出</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <StatusBar isAdmin={isAdmin} />

      <main className="mx-auto max-w-7xl px-3 py-3 sm:px-6 sm:py-6">
        <div className="space-y-3 sm:space-y-6">
          <div className={`flex items-center justify-between gap-3 rounded-xl border px-3 py-2 text-xs sm:hidden ${
            isAdmin
              ? 'border-[var(--accent)]/30 bg-[var(--accent)]/10 text-[var(--accent)]'
              : 'border-[var(--border-color)] bg-[var(--bg-secondary)]/55 text-[var(--text-muted)]'
          }`}>
            <span>{isAdmin ? 'Owner / 系統管理已啟用' : '單一使用者模式'}</span>
            <span className="opacity-80">{isAdmin ? '可進入系統管理頁' : '投資資料由目前帳號管理'}</span>
          </div>
          <div className="grid grid-cols-4 gap-1 overflow-hidden rounded-2xl border border-[var(--border-color)] bg-[var(--bg-secondary)]/45 p-1 sm:flex sm:gap-2 sm:rounded-none sm:border-0 sm:bg-transparent sm:p-0 sm:border-b sm:border-[var(--border-color)] sm:overflow-x-auto sm:pb-px">
            {[
              { key: 'overview' as DashboardView, label: '總覽', mobileLabel: '總覽', icon: TrendingUp, path: '/overview' },
              { key: 'holdings' as DashboardView, label: '持倉', mobileLabel: '持倉', icon: Wallet, path: '/holdings' },
              { key: 'transactions' as DashboardView, label: '交易', mobileLabel: '交易', icon: ArrowUpCircle, path: '/transactions' },
              { key: 'add' as DashboardView, label: '新增', mobileLabel: '新增', icon: Plus, path: '/transactions/new' },
            ].map((item) => (
              <Link
                key={item.key}
                className={`flex min-w-0 flex-col items-center justify-center gap-1 rounded-xl px-2 py-2 text-xs font-medium transition-colors sm:flex-row sm:whitespace-nowrap sm:px-4 sm:text-sm ${
                  view === item.key
                    ? 'bg-[var(--accent)]/12 text-[var(--accent)] sm:border-b-2 sm:border-[var(--accent)] sm:bg-transparent'
                    : 'opacity-70 hover:opacity-100 sm:border-b-2 sm:border-transparent'
                }`}
                to={item.path}
              >
                <item.icon className="h-4 w-4 shrink-0" />
                <span className="truncate sm:hidden">{item.mobileLabel}</span>
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            ))}
          </div>
          {children}
        </div>
      </main>

      {changePasswordOpen && (
        <div className="fixed inset-0 z-[70] flex items-end justify-center bg-slate-950/55 p-3 sm:items-center sm:p-6">
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            className="card w-full max-w-md rounded-2xl border border-[var(--border-color)] bg-[var(--card-bg)] p-5 shadow-2xl sm:p-6"
          >
            <div className="mb-4 flex items-center justify-end">
              <button
                type="button"
                onClick={() => setChangePasswordOpen(false)}
                className="rounded-lg p-2 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)]"
                aria-label="關閉修改密碼"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <ChangePasswordForm
              doneLabel="完成"
              onCancel={() => setChangePasswordOpen(false)}
              onDone={() => setChangePasswordOpen(false)}
              title="修改密碼"
              subtitle="直接在目前頁面完成密碼更新"
            />
          </div>
        </div>
      )}
    </div>
  );
}
