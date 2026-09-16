import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器：注入 Bearer token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一错误处理 + 401 跳转登录
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const msg = error.response?.data?.detail || error.response?.data?.message || error.message
    if (status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      ElMessage.error('登录已过期，请重新登录')
      router.push('/login')
    } else if (status === 403) {
      ElMessage.error('没有权限执行此操作')
    } else if (status >= 400) {
      ElMessage.error(msg || '请求失败')
    }
    return Promise.reject(error)
  }
)

// ============ 认证 API ============
export const authAPI = {
  login: (username, password) => api.post('/auth/login', { username, password }),
  register: (username, password, email) => api.post('/auth/register', { username, password, email }),
  refresh: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken }),
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
}

// ============ 市场数据 API ============
export const marketAPI = {
  getQuote: (code, provider = 'eastmoney') => api.get(`/data/market/quote/${code}`, { params: { provider } }),
  getKLine: (code, startDate, endDate, interval = '1d', provider = 'eastmoney') =>
    api.get(`/data/market/kline/${code}`, { params: { start_date: startDate, end_date: endDate, interval, provider } }),
  getStocks: (exchange = null, limit = 100) => api.get('/data/market/stocks', { params: { exchange, limit } }),
  getCalendar: (startDate, endDate) => api.get('/data/market/calendar', { params: { start_date: startDate, end_date: endDate } }),
  getBoard: (codes = '') => api.get('/data/market/board', { params: { codes } }),
  getWatchlist: () => api.get('/data/market/watchlist'),
  addToWatchlist: (code, remark = '') => api.post('/data/market/watchlist', { code, remark }),
  removeFromWatchlist: (code) => api.delete(`/data/market/watchlist/${code}`),
}

// ============ 策略 API ============
export const strategyAPI = {
  list: (page = 1, pageSize = 20, status = null) => api.get('/strategy/', { params: { page, page_size: pageSize, status } }),
  get: (id) => api.get(`/strategy/${id}`),
  create: (data) => api.post('/strategy/', data),
  update: (id, data) => api.put(`/strategy/${id}`, data),
  remove: (id) => api.delete(`/strategy/${id}`),
  run: (id) => api.post(`/strategy/${id}/run`),
  stop: (id) => api.post(`/strategy/${id}/stop`),
  getSignals: (id, limit = 100) => api.get(`/strategy/${id}/signals`, { params: { limit } }),
  analyze: (id, days = 90) => api.get(`/strategy/${id}/analysis`, { params: { days } }),
  compare: (ids) => api.get('/strategy/compare', { params: { ids: ids.join(',') } }),
}

// ============ 回测 API ============
export const backtestAPI = {
  list: (page = 1, pageSize = 20, status = null) => api.get('/backtest/', { params: { page, page_size: pageSize, status } }),
  get: (id) => api.get(`/backtest/${id}`),
  create: (data) => api.post('/backtest/', data),
  run: (id) => api.post(`/backtest/${id}/run`),
  stop: (id) => api.post(`/backtest/${id}/stop`),
  getResult: (id) => api.get(`/backtest/${id}/result`),
  getStatus: (id) => api.get(`/backtest/${id}/status`),
  getReport: (id) => api.get(`/backtest/${id}/report`),
  getExportCsv: (id, kind = 'trades') => api.get(`/backtest/${id}/export-csv`, { params: { kind }, responseType: 'blob' }),
  getExportReport: (id) => api.get(`/backtest/${id}/export-report`, { responseType: 'blob' }),
}

// ============ 交易 API ============
export const tradingAPI = {
  createOrder: (data) => api.post('/trading/order', data),
  listOrders: (code = null, direction = null, status = null, limit = 100) =>
    api.get('/trading/orders', { params: { code, direction, status, limit } }),
  getOrder: (orderId) => api.get(`/trading/order/${orderId}`),
  cancelOrder: (orderId) => api.post(`/trading/order/${orderId}/cancel`),
  listTrades: (code = null, direction = null, limit = 100) =>
    api.get('/trading/trades', { params: { code, direction, limit } }),
  getPositions: () => api.get('/trading/positions'),
  getPosition: (code) => api.get(`/trading/position/${code}`),
  getCapital: () => api.get('/trading/capital'),
  getStats: () => api.get('/trading/stats'),
  getStatus: () => api.get('/trading/status'),
}

// ============ 组合 API ============
export const portfolioAPI = {
  getPositions: (status = null) => api.get('/portfolio/positions', { params: { status } }),
  getPosition: (code) => api.get(`/portfolio/positions/${code}`),
  getSummary: (prices = null) => api.get('/portfolio/summary', { params: prices ? { prices } : {} }),
  getAccount: () => api.get('/portfolio/account'),
  getLogs: (limit = 100, type = null) => api.get('/portfolio/logs', { params: { limit, type } }),
  getAnalysis: (prices = null) => api.get('/portfolio/analysis', { params: prices ? { prices } : {} }),
  deposit: (amount, description = '现金存入') => api.post('/portfolio/deposit', null, { params: { amount, description } }),
  withdraw: (amount, description = '现金取出') => api.post('/portfolio/withdraw', null, { params: { amount, description } }),
  updatePrices: (prices) => api.post('/portfolio/update-prices', prices),
  processTrade: (trade) => api.post('/portfolio/process-trade', trade),
  rebuild: (trades) => api.post('/portfolio/rebuild', trades),
  getStats: () => api.get('/portfolio/stats'),
  getReport: () => api.get('/portfolio/report'),
}

// ============ 风控 API ============
export const riskAPI = {
  check: (data, totalCapital = 100000, currentPositions = {}) =>
    api.post('/risk/check', data, { params: { total_capital: totalCapital, current_positions: currentPositions } }),
  getLimits: (riskType = null, enabled = null) => api.get('/risk/limits', { params: { risk_type: riskType, enabled } }),
  createLimit: (data) => api.post('/risk/limits', data),
  updateLimit: (limitId, updates) => api.put(`/risk/limits/${limitId}`, updates),
  deleteLimit: (limitId) => api.delete(`/risk/limits/${limitId}`),
  getAlerts: (riskType = null, level = null, limit = 100) => api.get('/risk/alerts', { params: { risk_type: riskType, level, limit } }),
  getChecks: (riskType = null, limit = 100) => api.get('/risk/checks', { params: { risk_type: riskType, limit } }),
  calcVaR: (returns, confidence = 0.95, period = 1) => api.post('/risk/var', returns, { params: { confidence, period } }),
  getStats: () => api.get('/risk/stats'),
  getStatus: () => api.get('/risk/status'),
  getDashboard: () => api.get('/risk/dashboard'),
}

export default api
