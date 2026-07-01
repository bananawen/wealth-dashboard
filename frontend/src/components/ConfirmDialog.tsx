import { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import type { ReactNode } from 'react';

interface ConfirmDialogProps {
  cancelLabel?: string;
  confirmLabel?: string;
  confirmTone?: 'danger' | 'primary';
  description?: ReactNode;
  onCancel: () => void;
  onConfirm: () => void;
  open: boolean;
  title: string;
}

export default function ConfirmDialog({
  cancelLabel = '取消',
  confirmLabel = '確認',
  confirmTone = 'primary',
  description,
  onCancel,
  onConfirm,
  open,
  title,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onCancel, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[70] flex items-end justify-center bg-slate-950/55 p-3 sm:items-center sm:p-6">
      <div
        role="dialog"
        aria-modal="true"
        className="card w-full max-w-md rounded-2xl border border-[var(--border-color)] bg-[var(--card-bg)] shadow-2xl"
      >
        <div className="flex items-start gap-3 border-b border-[var(--border-color)] px-4 py-4">
          <div className="mt-0.5 rounded-full bg-[var(--warning)]/10 p-2 text-[var(--warning)]">
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <div className="text-base font-semibold">{title}</div>
            {description ? <div className="mt-1 text-sm text-[var(--text-secondary)]">{description}</div> : null}
          </div>
        </div>

        <div className="flex flex-col-reverse gap-2 px-4 py-4 sm:flex-row sm:justify-end">
          <button type="button" onClick={onCancel} className="btn-secondary px-4 py-2 text-sm">
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={confirmTone === 'danger'
              ? 'rounded-lg bg-[var(--error)] px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90'
              : 'btn-primary px-4 py-2 text-sm'}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
