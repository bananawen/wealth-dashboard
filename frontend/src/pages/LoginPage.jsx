import { useState } from 'react'
import { api } from '../utils/api'
import { useTheme } from '../context/ThemeContext'

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { theme } = useTheme()

  const bgClass = theme === 'dark' ? 'bg-[#07070d]' : 'bg-[#F8F9FC]'
  const surfaceClass = theme === 'dark' ? 'bg-[#0f0f18]' : 'bg-white'
  const borderClass = theme === 'dark' ? 'border-blue-500/20' : 'border-blue-200'
  const textClass = theme === 'dark' ? 'text-slate-100' : 'text-slate-900'
  const textMutedClass = theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
  const inputClass = theme === 'dark'
    ? 'bg-[#07070d] border-blue-500/20 text-slate-100 placeholder-slate-500'
    : 'bg-slate-50 border-blue-200 text-slate-900 placeholder-slate-400'
  const linkClass = theme === 'dark' ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-700'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = isRegister
        ? await api.register(username, password)
        : await api.login(username, password)
      if (!isRegister) {
        localStorage.setItem('token', data.access_token)
        window.location.href = '/'
      } else {
        setIsRegister(false)
        setError('註冊成功，請登入')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`min-h-screen ${bgClass} flex items-center justify-center p-4`}>
      <div className={`${surfaceClass} border ${borderClass} p-8 rounded-2xl shadow-2xl w-full max-w-md animate-fade-in-up`}>
        {/* Logo */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-500/20 mb-3">
            <span className="text-2xl">📈</span>
          </div>
          <h1 className="text-2xl font-semibold text-slate-100">個人財富管理</h1>
          <p className={`text-sm ${textMutedClass} mt-1`}>輸入帳號密碼存取您的投資組合</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={`block ${textMutedClass} text-sm mb-1`}>帳號</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className={`${inputClass} w-full rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50`}
              required
            />
          </div>
          <div>
            <label className={`block ${textMutedClass} text-sm mb-1`}>密碼</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className={`${inputClass} w-full rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50`}
              required
            />
          </div>
          {error && (
            <div className="text-red-400 text-sm text-center bg-red-500/10 py-2 rounded-lg">{error}</div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2.5 rounded-lg transition-all duration-150 disabled:opacity-50 flex items-center justify-center gap-2"
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
          className={`${linkClass} text-sm text-center mt-4 cursor-pointer hover:underline`}
          onClick={() => setIsRegister(!isRegister)}
        >
          {isRegister ? '已有帳號？登入' : '沒有帳號？註冊'}
        </p>
      </div>
    </div>
  )
}