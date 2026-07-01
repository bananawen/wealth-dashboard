import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLoginMutation, useRegisterMutation } from '../store/apiSlice';
import InlineNotice from '../components/InlineNotice';
import PasswordField from '../components/PasswordField';

const PASSWORD_MIN_LENGTH = 8;
type LoginNotice = { tone: 'error' | 'success'; title: string; message: string };

function getFriendlyError(err: unknown, isRegister: boolean) {
  const extractDetail = (detail: unknown): string | null => {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown; message?: unknown; loc?: unknown };
      if (typeof first?.msg === 'string') return first.msg;
      if (typeof first?.message === 'string') return first.message;
    }
    return null;
  };

  if (typeof err === 'object' && err !== null && 'status' in err) {
    const status = (err as { status?: number | string }).status;
    const data = (err as { data?: { detail?: string } }).data;

    if (status === 'FETCH_ERROR' || status === 'TIMEOUT_ERROR' || status === 'PARSING_ERROR') {
      return '連線失敗，請稍後再試';
    }

    if (status === 401 && !isRegister) {
      return '帳號或密碼錯誤';
    }

    const detail = extractDetail((data as { detail?: unknown } | undefined)?.detail);
    if (detail) {
      return detail;
    }

    if (status === 400 && isRegister) {
      return '註冊資料有誤，請檢查帳號與密碼';
    }
    if (typeof status === 'number' && status >= 500) {
      return '登入服務暫時異常，請稍後再試';
    }
  }

  if (err instanceof Error && err.message) {
    if (err.message.toLowerCase().includes('failed to fetch')) {
      return '連線失敗，請稍後再試';
    }
    return err.message;
  }

  return '登入服務暫時異常，請稍後再試';
}

function validatePassword(password: string) {
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `密碼至少需要 ${PASSWORD_MIN_LENGTH} 個字元`;
  }
  if (/\s/.test(password)) {
    return '密碼不能包含空白字元';
  }
  return '';
}

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [notice, setNotice] = useState<LoginNotice | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const [login] = useLoginMutation();
  const [register] = useRegisterMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setNotice(null);

    if (isRegister) {
      const passwordError = validatePassword(password);
      if (passwordError) {
        setNotice({ tone: 'error', title: '註冊失敗', message: passwordError });
        return;
      }

      if (password !== confirmPassword) {
        setNotice({ tone: 'error', title: '註冊失敗', message: '密碼與確認密碼不一致' });
        return;
      }
    }

    setLoading(true);
    try {
      if (isRegister) {
        await register({ username, password }).unwrap();
        setIsRegister(false);
        setPassword('');
        setConfirmPassword('');
        setNotice({
          tone: 'success',
          title: '註冊成功',
          message: '帳號已建立，請使用新帳號登入。單一使用者部署中，第一個註冊帳號會自動擁有系統管理權限。',
        });
      } else {
        const data = await login({ username, password }).unwrap();
        localStorage.setItem('token', data.access_token);
        navigate('/');
      }
    } catch (err: unknown) {
      setNotice({
        tone: 'error',
        title: isRegister ? '註冊失敗' : '登入失敗',
        message: getFriendlyError(err, isRegister),
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
      <div className="bg-[var(--card-bg)] border border-[var(--border-color)] p-8 rounded-2xl shadow-2xl w-full max-w-md animate-fade-in-up">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[var(--accent)]/20 mb-3">
            <span className="text-2xl">📈</span>
          </div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">個人財富管理</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">輸入帳號密碼存取您的投資組合</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[var(--text-secondary)] text-sm mb-1">帳號</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-4 py-3 text-[var(--text-primary)] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/45 focus:border-[var(--accent)]"
              placeholder="帳號"
              autoComplete="username"
              required
            />
          </div>
          <PasswordField
            label="密碼"
            value={password}
            onChange={setPassword}
            placeholder="密碼"
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            minLength={PASSWORD_MIN_LENGTH}
            required
            helperText={isRegister ? `至少 ${PASSWORD_MIN_LENGTH} 字元，不能有空白` : undefined}
          />
          {isRegister && (
            <>
              <PasswordField
                label="確認密碼"
                value={confirmPassword}
                onChange={setConfirmPassword}
                placeholder="再次輸入密碼"
                autoComplete="new-password"
                minLength={PASSWORD_MIN_LENGTH}
                required={isRegister}
              />
              <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)]/55 px-3 py-2 text-xs text-[var(--text-secondary)]">
                單一使用者部署：第一個註冊帳號會自動成為管理者，登入後可存取系統管理頁。
              </div>
            </>
          )}
          {notice ? (
            <InlineNotice
              tone={notice.tone}
              title={notice.title}
              message={notice.message}
              onDismiss={() => setNotice(null)}
            />
          ) : null}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white font-semibold py-2.5 rounded-lg transition-all duration-150 disabled:opacity-50 flex items-center justify-center gap-2"
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
              isRegister ? '註冊' : '登入'
            )}
          </button>
        </form>
        <p
          className="text-[var(--accent)] hover:text-[var(--accent-hover)] text-sm text-center mt-4 cursor-pointer hover:underline transition-colors"
          onClick={() => {
            setIsRegister(!isRegister);
            setNotice(null);
            setConfirmPassword('');
          }}
        >
          {isRegister ? '已有帳號？登入' : '沒有帳號？註冊'}
        </p>
      </div>
    </div>
  );
}
