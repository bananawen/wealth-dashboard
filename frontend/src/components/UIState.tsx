import type { ReactNode } from 'react';
import { AlertCircle, CheckCircle2, Clock3, Loader2, type LucideIcon } from 'lucide-react';

type BadgeTone = 'neutral' | 'info' | 'success' | 'warning' | 'error' | 'loading' | 'stale' | 'estimated';

const BADGE_CLASS_MAP: Record<BadgeTone, string> = {
  neutral: 'badge-neutral',
  info: 'badge-info',
  success: 'badge-success',
  warning: 'badge-warning',
  error: 'badge-error',
  loading: 'badge-loading',
  stale: 'badge-stale',
  estimated: 'badge-estimated',
};

const BADGE_ICON_MAP: Record<Exclude<BadgeTone, 'loading'>, LucideIcon | null> = {
  neutral: null,
  info: Clock3,
  success: CheckCircle2,
  warning: AlertCircle,
  error: AlertCircle,
  stale: Clock3,
  estimated: Clock3,
};

export function SemanticBadge({
  tone = 'neutral',
  children,
  className = '',
}: {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
}) {
  const Icon = tone === 'loading' ? Loader2 : BADGE_ICON_MAP[tone];
  return (
    <span className={`badge ${BADGE_CLASS_MAP[tone]} ${className}`.trim()}>
      {Icon && <Icon className={`w-3 h-3 ${tone === 'loading' ? 'animate-spin' : ''}`} />}
      <span>{children}</span>
    </span>
  );
}

export function LoadingState({
  title = '載入中',
  description = '請稍候，資料正在同步。',
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className="state-panel">
      <div className="inline-flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-[var(--accent)]" />
        <div className="state-title">{title}</div>
      </div>
      <div className="state-copy">{description}</div>
    </div>
  );
}

export function EmptyState({
  title = '尚無資料',
  description,
  icon,
  action,
}: {
  title?: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="state-panel">
      {icon ? <div className="mb-2 flex justify-center">{icon}</div> : null}
      <div className="state-title">{title}</div>
      {description ? <div className="state-copy">{description}</div> : null}
      {action ? <div className="state-action">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  title = '發生錯誤',
  description = '請稍後再試。',
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="state-panel border-[var(--error)]/30 bg-[var(--error)]/8">
      <div className="inline-flex items-center gap-2">
        <AlertCircle className="w-4 h-4 text-[var(--error)]" />
        <div className="state-title text-[var(--error)]">{title}</div>
      </div>
      <div className="state-copy">{description}</div>
      {action ? <div className="state-action">{action}</div> : null}
    </div>
  );
}

export function DataTimestamp({
  label = '資料時間',
  value,
  hint,
}: {
  label?: string;
  value?: string | null;
  hint?: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs opacity-60">
      <span>{label}：{value ?? 'N/A'}</span>
      {hint ? <span>· {hint}</span> : null}
    </div>
  );
}
