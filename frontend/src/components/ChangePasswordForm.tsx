import { useState } from 'react';
import { useChangePasswordMutation } from '../store/apiSlice';
import InlineNotice from './InlineNotice';
import PasswordField from './PasswordField';

const PASSWORD_MIN_LENGTH = 8;

type PasswordNotice = { tone: 'error' | 'success'; title: string; message: string };

function validatePassword(password: string) {
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `密碼至少需要 ${PASSWORD_MIN_LENGTH} 個字元`;
  }
  if (/\s/.test(password)) {
    return '密碼不能包含空白字元';
  }
  return '';
}

function getFriendlyError(err: unknown) {
  if (typeof err === 'object' && err !== null && 'status' in err) {
    const status = (err as { status?: number | string }).status;
    const data = (err as { data?: { detail?: string } }).data;

    if (status === 'FETCH_ERROR' || status === 'TIMEOUT_ERROR' || status === 'PARSING_ERROR') {
      return '連線失敗，請稍後再試';
    }

    if (data?.detail) {
      return data.detail;
    }
  }

  if (err instanceof Error && err.message) {
    return err.message;
  }

  return '發生未知錯誤，請稍後再試';
}

interface ChangePasswordFormProps {
  doneLabel?: string;
  onCancel?: () => void;
  onDone?: () => void;
  title?: string;
  subtitle?: string;
}

export default function ChangePasswordForm({
  doneLabel = '完成',
  onCancel,
  onDone,
  title = '修改密碼',
  subtitle = '更換您的帳戶密碼',
}: ChangePasswordFormProps) {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [notice, setNotice] = useState<PasswordNotice | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [changePassword] = useChangePasswordMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setNotice(null);

    const newPasswordError = validatePassword(newPassword);
    if (newPasswordError) {
      setNotice({ tone: 'error', title: '修改失敗', message: `新密碼：${newPasswordError}` });
      return;
    }

    if (newPassword !== confirmPassword) {
      setNotice({ tone: 'error', title: '修改失敗', message: '新密碼與確認密碼不符' });
      return;
    }

    if (oldPassword === newPassword) {
      setNotice({ tone: 'error', title: '修改失敗', message: '新密碼不能與舊密碼相同' });
      return;
    }

    setLoading(true);
    try {
      await changePassword({ old_password: oldPassword, new_password: newPassword }).unwrap();
      setSuccess(true);
      setNotice({ tone: 'success', title: '修改成功', message: '密碼已更新，之後請使用新密碼登入。' });
    } catch (err: unknown) {
      setNotice({ tone: 'error', title: '修改失敗', message: getFriendlyError(err) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mb-3 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--accent)]/20">
          <span className="text-2xl">🔐</span>
        </div>
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">{title}</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">{subtitle}</p>
      </div>

      {success ? (
        <div className="space-y-4 text-center">
          {notice ? (
            <InlineNotice
              tone={notice.tone}
              title={notice.title}
              message={notice.message}
              onDismiss={() => setNotice(null)}
            />
          ) : null}
          <button
            type="button"
            onClick={onDone}
            className="w-full rounded-lg bg-[var(--accent)] py-2.5 font-semibold text-white transition-all duration-150 hover:bg-[var(--accent-hover)]"
          >
            {doneLabel}
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <PasswordField
            label="舊密碼"
            value={oldPassword}
            onChange={setOldPassword}
            placeholder="輸入舊密碼"
            autoComplete="current-password"
            minLength={PASSWORD_MIN_LENGTH}
            required
          />
          <PasswordField
            label="新密碼"
            value={newPassword}
            onChange={setNewPassword}
            placeholder="輸入新密碼"
            autoComplete="new-password"
            minLength={PASSWORD_MIN_LENGTH}
            required
            helperText={`至少 ${PASSWORD_MIN_LENGTH} 個字元，不能包含空白`}
          />
          <PasswordField
            label="確認密碼"
            value={confirmPassword}
            onChange={setConfirmPassword}
            placeholder="再次輸入新密碼"
            autoComplete="new-password"
            minLength={PASSWORD_MIN_LENGTH}
            required
          />
          {notice ? (
            <InlineNotice
              tone={notice.tone}
              title={notice.title}
              message={notice.message}
              onDismiss={() => setNotice(null)}
            />
          ) : null}
          <div className="flex gap-3">
            {onCancel ? (
              <button
                type="button"
                onClick={onCancel}
                className="flex-1 rounded-lg border border-[var(--border-color)] py-2.5 font-semibold text-[var(--text-primary)] transition-all duration-150 hover:bg-[var(--bg-secondary)]"
              >
                取消
              </button>
            ) : null}
            <button
              type="submit"
              disabled={loading}
              className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] py-2.5 font-semibold text-white transition-all duration-150 hover:bg-[var(--accent-hover)] disabled:opacity-50"
            >
              {loading ? (
                <>
                  <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  處理中...
                </>
              ) : (
                '確認修改'
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
