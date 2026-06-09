import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useChangePasswordMutation } from '../store/apiSlice';
import { useTheme } from '../context/ThemeContext';

export default function ChangePasswordPage() {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const [changePassword] = useChangePasswordMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('新密碼與確認密碼不符');
      return;
    }

    if (oldPassword === newPassword) {
      setError('新密碼不能與舊密碼相同');
      return;
    }

    setLoading(true);
    try {
      await changePassword({ old_password: oldPassword, new_password: newPassword }).unwrap();
      setSuccess(true);
    } catch (err: unknown) {
      const message =
        typeof err === 'object' && err !== null && 'data' in err
          ? (err as { data: { detail?: string } }).data?.detail ?? String((err as { status?: number }).status ?? '')
          : err instanceof Error
          ? err.message
          : 'Request failed';
      setError(message || 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
      <div className="bg-[var(--card-bg)] border border-[var(--border-color)] p-8 rounded-2xl shadow-2xl w-full max-w-md animate-fade-in-up">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[var(--accent)]/20 mb-3">
            <span className="text-2xl">🔐</span>
          </div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">修改密碼</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">更換您的帳戶密碼</p>
        </div>

        {success ? (
          <div className="text-center space-y-4">
            <div className="text-[var(--success)] text-4xl">✓</div>
            <p className="text-[var(--text-primary)] font-medium">密碼修改成功</p>
            <button
              onClick={() => navigate('/')}
              className="w-full bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white font-semibold py-2.5 rounded-lg transition-all duration-150"
            >
              返回首頁
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[var(--text-secondary)] text-sm mb-1">舊密碼</label>
              <input
                type="password"
                value={oldPassword}
                onChange={e => setOldPassword(e.target.value)}
                className="w-full rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  borderColor: 'var(--border-color)',
                  color: 'var(--text-primary)',
                }}
                placeholder="輸入舊密碼"
                required
              />
            </div>
            <div>
              <label className="block text-[var(--text-secondary)] text-sm mb-1">新密碼</label>
              <input
                type="password"
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                className="w-full rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  borderColor: 'var(--border-color)',
                  color: 'var(--text-primary)',
                }}
                placeholder="輸入新密碼"
                required
              />
            </div>
            <div>
              <label className="block text-[var(--text-secondary)] text-sm mb-1">確認密碼</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                className="w-full rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  borderColor: 'var(--border-color)',
                  color: 'var(--text-primary)',
                }}
                placeholder="再次輸入新密碼"
                required
              />
            </div>
            {error && (
              <div className="text-[var(--error)] text-sm text-center py-2 rounded-lg" style={{ backgroundColor: 'color-mix(in srgb, var(--error) 10%, transparent)' }}>
                {error}
              </div>
            )}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="flex-1 border border-[var(--border-color)] text-[var(--text-primary)] font-semibold py-2.5 rounded-lg transition-all duration-150 hover:bg-[var(--bg-secondary)]"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white font-semibold py-2.5 rounded-lg transition-all duration-150 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
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
    </div>
  );
}