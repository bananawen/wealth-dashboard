import type { ReactNode } from 'react';
import { X } from 'lucide-react';
import { ErrorState, SemanticBadge } from './UIState';

interface InlineNoticeProps {
  message: ReactNode;
  onDismiss: () => void;
  tone?: 'error' | 'success' | 'info';
  title?: string;
}

export default function InlineNotice({
  message,
  onDismiss,
  tone = 'info',
  title,
}: InlineNoticeProps) {
  if (tone === 'error') {
    return (
      <div className="relative">
        <ErrorState
          title={title ?? '操作失敗'}
          description={message}
          action={(
            <button type="button" onClick={onDismiss} className="btn-secondary px-3 py-1 text-xs">
              關閉
            </button>
          )}
        />
      </div>
    );
  }

  return (
    <div className="card border-[var(--border-color)] bg-[var(--bg-secondary)]/70 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-1 flex items-center gap-2">
            <SemanticBadge tone={tone === 'success' ? 'success' : 'info'}>
              {title ?? (tone === 'success' ? '完成' : '通知')}
            </SemanticBadge>
          </div>
          <div className="text-sm text-[var(--text-secondary)]">{message}</div>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="rounded p-1 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
          aria-label="關閉通知"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
