import { useState, useEffect, useRef } from 'react'
import { api } from '../utils/api'
import { Search, Calendar, X, Plus } from 'lucide-react'

const STOCK_SUGGESTIONS = [
  // US Tech
  'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'INTC', 'CSCO',
  // US ETFs
  'SPY', 'QQQ', 'VOO', 'VTI', 'IWM', 'VEA', 'VWO', 'BND', 'AGG', 'GLD', 'TLT', 'LQD',
  // Taiwan ETFs
  '0050', '0056', '006208', '00878', '00713',
  // Taiwan Stocks
  '2330', '2317', '2303', '2454', '2308', '2377', '2382',
  // US Financial
  'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS',
  // US Industrial
  'CAT', 'DE', 'BA', 'HON', 'UNP', 'RTX',
]

export default function AddTransactionForm({ onSuccess, onCancel }) {
  const [form, setForm] = useState({
    symbol: '',
    type: 'buy',
    shares: '',
    price: '',
    date: new Date().toISOString().split('T')[0],
  })
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [showCalendar, setShowCalendar] = useState(false)
  const inputRef = useRef(null)
  const calendarRef = useRef(null)

  useEffect(() => {
    if (form.symbol.length >= 1) {
      const filtered = STOCK_SUGGESTIONS.filter(s =>
        s.toLowerCase().includes(form.symbol.toUpperCase())
      ).slice(0, 8)
      setSuggestions(filtered)
      setShowSuggestions(filtered.length > 0)
    } else {
      setSuggestions([])
      setShowSuggestions(false)
    }
  }, [form.symbol])

  useEffect(() => {
    function handleClickOutside(e) {
      if (calendarRef.current && !calendarRef.current.contains(e.target)) {
        setShowCalendar(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const selectSuggestion = (sym) => {
    setForm(f => ({ ...f, symbol: sym }))
    setShowSuggestions(false)
    inputRef.current?.focus()
  }

  const handleDateChange = (days) => {
    const d = new Date()
    d.setDate(d.getDate() + days)
    setForm(f => ({ ...f, date: d.toISOString().split('T')[0] }))
    setShowCalendar(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      await api.createTransaction({
        symbol: form.symbol.toUpperCase(),
        type: form.type,
        shares: Number(form.shares),
        price: Number(form.price),
        date: form.date,
      })
      onSuccess?.()
      setForm({
        symbol: '',
        type: 'buy',
        shares: '',
        price: '',
        date: new Date().toISOString().split('T')[0],
      })
    } catch (err) {
      alert(err.message)
    }
  }

  const quickDates = [
    { label: '今天', days: 0 },
    { label: '昨天', days: -1 },
    { label: '3天前', days: -3 },
    { label: '1週前', days: -7 },
    { label: '1月前', days: -30 },
  ]

  return (
    <div className="card p-6 max-w-lg animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Plus className="w-5 h-5 text-[var(--accent)]" />新增交易
        </h2>
        {onCancel && (
          <button onClick={onCancel} className="p-1 hover:bg-[var(--bg-secondary)] rounded">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Symbol with autocomplete */}
        <div className="relative">
          <label className="block text-sm opacity-60 mb-1">股票代號</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 opacity-40" />
            <input
              ref={inputRef}
              value={form.symbol}
              onChange={e => setForm(f => ({ ...f, symbol: e.target.value.toUpperCase() }))}
              onFocus={() => form.symbol.length >= 1 && setShowSuggestions(true)}
              placeholder="輸入代碼，如 0050、AAPL"
              className="input-field pl-10"
              autoComplete="off"
              required
            />
            {form.symbol && (
              <button
                type="button"
                onClick={() => setForm(f => ({ ...f, symbol: '' }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-[var(--bg-secondary)] rounded"
              >
                <X className="w-3 h-3 opacity-40" />
              </button>
            )}
          </div>

          {/* Suggestions dropdown */}
          {showSuggestions && (
            <div className="absolute z-10 w-full mt-1 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg shadow-lg overflow-hidden">
              {suggestions.map(sym => (
                <button
                  key={sym}
                  type="button"
                  onClick={() => selectSuggestion(sym)}
                  className="w-full px-4 py-2 text-left hover:bg-[var(--bg-secondary)] font-mono text-sm"
                >
                  {sym}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Transaction type */}
        <div>
          <label className="block text-sm opacity-60 mb-1">交易類型</label>
          <div className="flex gap-2">
            {['buy', 'sell'].map(t => (
              <button
                key={t}
                type="button"
                onClick={() => setForm(f => ({ ...f, type: t }))}
                className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                  form.type === t
                    ? t === 'buy' ? 'bg-[var(--profit)] text-white' : 'bg-[var(--loss)] text-white'
                    : 'bg-[var(--bg-secondary)]'
                }`}
              >
                {t === 'buy' ? '買入' : '賣出'}
              </button>
            ))}
          </div>
        </div>

        {/* Shares and Price */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm opacity-60 mb-1">股數</label>
            <input
              type="number"
              step="0.0001"
              value={form.shares}
              onChange={e => setForm(f => ({ ...f, shares: e.target.value }))}
              className="input-field"
              required
            />
          </div>
          <div>
            <label className="block text-sm opacity-60 mb-1">價格</label>
            <input
              type="number"
              step="0.01"
              value={form.price}
              onChange={e => setForm(f => ({ ...f, price: e.target.value }))}
              className="input-field"
              required
            />
          </div>
        </div>

        {/* Date with calendar */}
        <div ref={calendarRef} className="relative">
          <label className="block text-sm opacity-60 mb-1">交易日期</label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setShowCalendar(!showCalendar)}
              className="input-field flex items-center gap-2"
            >
              <Calendar className="w-4 h-4 opacity-60" />
              {form.date}
            </button>
          </div>

          {/* Quick select */}
          <div className="flex flex-wrap gap-1 mt-2">
            {quickDates.map(qd => (
              <button
                key={qd.label}
                type="button"
                onClick={() => handleDateChange(qd.days)}
                className="px-2 py-1 text-xs rounded border border-[var(--border-color)] hover:border-[var(--accent)] transition-colors"
              >
                {qd.label}
              </button>
            ))}
          </div>

          {/* Calendar popup */}
          {showCalendar && (
            <div className="absolute z-10 mt-1 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg shadow-lg p-3">
              <input
                type="date"
                value={form.date}
                onChange={e => setForm(f => ({ ...f, date: e.target.value }))}
                className="input-field"
              />
            </div>
          )}
        </div>

        {/* Total preview */}
        {form.shares && form.price && (
          <div className="text-sm opacity-60 text-right">
            總金額：${(Number(form.shares) * Number(form.price)).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        )}

        <button type="submit" className="btn-primary w-full">
          送出交易
        </button>
      </form>
    </div>
  )
}
