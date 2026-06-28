import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// ---- Stock / Financial ----

export async function fetchFinancialData(keywords, quarters = 16, localOnly = false) {
  const params = { keywords, quarters }
  if (localOnly) params.local_only = true
  const { data } = await api.get('/stock/financial', { params })
  return data
}

// ---- Invest Pool ----

export async function fetchStockPool() {
  const { data } = await api.get('/invest/pool')
  return data
}

export async function addToPool(item) {
  const { data } = await api.post('/invest/pool', item)
  return data
}

export async function updatePoolItem(id, updates) {
  const { data } = await api.put(`/invest/pool/${id}`, updates)
  return data
}

export async function removeFromPool(id) {
  await api.delete(`/invest/pool/${id}`)
}

export async function refreshPool() {
  const { data } = await api.post('/invest/pool/refresh')
  return data
}

export async function patchPoolField(id, field, value) {
  const { data } = await api.patch(`/invest/pool/${id}/${field}`, { field, value })
  return data
}

// ---- Big Yang ----

export async function fetchBigYangSummary() {
  const { data } = await api.get('/invest/big-yang/summary')
  return data
}

export async function fetchBigYangSignals(status) {
  const { data } = await api.get('/invest/big-yang/signals', {
    params: status ? { status } : {},
  })
  return data
}

export async function fetchBigYangAlerts() {
  const { data } = await api.get('/invest/big-yang/alerts')
  return data
}

export async function runBigYangScan() {
  const { data } = await api.post('/invest/big-yang/run')
  return data
}

export async function markAlertRead(id) {
  await api.post(`/invest/big-yang/alerts/${id}/read`)
}

// ---- SOP Checkup ----

export async function fetchSopCheckup(keyword) {
  const { data } = await api.get('/invest/sop/checkup', {
    params: { keyword },
  })
  return data
}

// ---- Practical Select ----

export async function runPracticalSelect(keyword) {
  const { data } = await api.post('/practical-select', { keyword })
  return data
}

export async function fetchSelectHistory(page = 0, size = 20, kw = '') {
  const { data } = await api.get('/practical-select/history', {
    params: { page, size, kw },
  })
  return data  // { records, total, page, size, totalPages }
}

export async function deleteSelectRecord(id) {
  await api.delete(`/practical-select/history/${id}`)
}

// ---- Notifications ----

export async function fetchRecapBadge() {
  const { data } = await api.get('/market-recaps/badge')
  return data
}

export async function fetchAnalysisList(limit = 3) {
  const { data } = await api.get('/stock-analysis/list', {
    params: { limit, size: limit },
  })
  return data
}

// ---- Data Collection ----

export async function collectSingle(keyword) {
  const { data } = await api.post('/collect/single', null, {
    params: { keyword },
    timeout: 120000,
  })
  return data
}

export async function getStockStatus(keyword) {
  const { data } = await api.get(`/collect/stock-status/${keyword}`)
  return data
}

export async function startBatchCollect(keywords, incremental = true) {
  const { data } = await api.post('/collect/batch', keywords, {
    params: { incremental },
  })
  return data
}

export async function uploadBatchCSV(file, incremental = true) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('incremental', incremental)
  const { data } = await api.post('/collect/batch/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function getCollectProgress(taskId) {
  const { data } = await api.get(`/collect/batch/${taskId}`)
  return data
}

export async function getMarkets() {
  const { data } = await api.get('/collect/markets')
  return data
}

export async function startMarketCollect(market, incremental = true) {
  const { data } = await api.post('/collect/market', null, {
    params: { market, incremental },
  })
  return data
}
