const BASE = '/api'

// Frontend logger - mirrors backend logging pattern with Hermes color scheme
const logger = {
  info: (...args) => console.log('%c[INFO]', 'color: #3B82F6', ...args),
  warn: (...args) => console.warn('%c[WARN]', 'color: #F59E0B', ...args),
  error: (...args) => console.error('%c[ERROR]', 'color: #EF4444', ...args),
  debug: (...args) => console.debug('%c[DEBUG]', 'color: #9CA3AF', ...args),
}

// Global fetch error interceptor
window.addEventListener('unhandledrejection', (event) => {
  logger.error('Unhandled promise rejection:', event.reason)
})

async function request(path, options = {}) {
  const token = localStorage.getItem('token')
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const url = `${BASE}${path}`
  logger.info(`→ ${options.method || 'GET'} ${url}`)

  const startTime = performance.now()
  try {
    const res = await fetch(url, { ...options, headers })
    const duration = (performance.now() - startTime).toFixed(1)

    if (res.status === 401) {
      logger.warn('← 401 Unauthorized - redirecting to login')
      localStorage.removeItem('token')
      window.location.href = '/login'
      throw new Error('Unauthorized')
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      logger.error(`← ${res.status} ${url} | ${duration}ms | ${err.detail || res.statusText}`)
      throw new Error(err.detail || 'Request failed')
    }

    const data = await res.json()
    logger.info(`← ${res.status} ${url} | ${duration}ms`)
    return data

  } catch (err) {
    if (err.name !== 'TypeError') { // TypeError = network error, already logged
      logger.error(`✗ ${options.method || 'GET'} ${url} | ${err.message}`)
    }
    throw err
  }
}

// Global error handler for console errors
window.onerror = (msg, src, lineno, colno, err) => {
  logger.error(`Console error at ${src}:${lineno}:${colno}`, err)
}

export const api = {
  login: (username, password) =>
    request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }).toString(),
    }),

  register: (username, password) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ username, password }) }),

  updateTransaction: (id, data) =>
    request(`/transactions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  deleteTransaction: (id) =>
    request(`/transactions/${id}`, { method: 'DELETE' }),

  getAccounts: () => request('/accounts'),

  createAccount: (data) =>
    request('/accounts', { method: 'POST', body: JSON.stringify(data) }),

  getHoldings: () => request('/holdings'),

  getComputedHoldings: () => request('/holdings/computed'),

  createHolding: (data) =>
    request('/holdings', { method: 'POST', body: JSON.stringify(data) }),

  updateHolding: (id, data) =>
    request(`/holdings/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  deleteHolding: (id) =>
    request(`/holdings/${id}`, { method: 'DELETE' }),

  getTransactions: () => request('/transactions'),

  createTransaction: (data) =>
    request('/transactions', { method: 'POST', body: JSON.stringify(data) }),

  getPortfolioSummary: () => request('/portfolio/summary'),

  getHistory: () => request('/portfolio/history'),

  createSnapshot: (data) =>
    request('/portfolio/snapshot', { method: 'POST', body: JSON.stringify(data) }),

  getStatus: () => request('/admin/status'),
  getVersion: () => request('/admin/version'),
}

// Export logger for use in components
export { logger }