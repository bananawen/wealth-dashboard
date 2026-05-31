import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLoginMutation, useRegisterMutation } from '../store/apiSlice';
import { useTheme } from '../context/ThemeContext';

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const [login] = useLoginMutation();
  const [register] = useRegisterMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isRegister) {
        await register({ username, password }).unwrap();
        setIsRegister(false);
        setError('註冊成功，請登入');
      } else {
        const data = await login({ username, password }).unwrap();
        localStorage.setItem('token', data.access_token);
        navigate('/');
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
      <div className="bg-[var(--card-bg)] border border-[var(--border-color)] p-8 rounded-2xl shadow-2xl w-full max-w-md animate-fade-in-up">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-500/20 mb-3">
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
              className="w-full rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)',
              }}
              placeholder="帳號"
              required
            />
          </div>
          <div>
            <label className="block text-[var(--text-secondary)] text-sm mb-1">密碼</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)',
              }}
              placeholder="密碼"
              required
            />
          </div>
          {error && (
            <div className="text-[var(--error)] text-sm text-center py-2 rounded-lg" style={{ backgroundColor: 'color-mix(in srgb, var(--error) 10%, transparent)' }}>
              {error}
            </div>
          )}
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
          onClick={() => setIsRegister(!isRegister)}
        >
          {isRegister ? '已有帳號？登入' : '沒有帳號？註冊'}
        </p>
      </div>
    </div>
  );
}
