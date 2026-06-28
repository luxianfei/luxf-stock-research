/**
 * Format a number as percentage with sign.
 */
export function pctFmt(v) {
  if (v == null) return '--'
  const n = Number(v)
  return isFinite(n) ? n.toFixed(2) + '%' : '--'
}

/**
 * Format a raw value (in yuan) to 亿.
 */
export function yiFmt(v) {
  if (v == null) return '--'
  const n = Number(v)
  return isFinite(n) ? (n / 1e8).toFixed(2) + '亿' : '--'
}

/**
 * Format number to 2 decimal places.
 */
export function numFmt2(v) {
  if (v == null) return '--'
  const n = Number(v)
  return isFinite(n) ? n.toFixed(2) : '--'
}

/**
 * Get CSS class for positive/negative coloring.
 */
export function colorClass(value) {
  if (value == null) return ''
  const n = Number(value)
  if (!isFinite(n)) return ''
  return n > 0 ? 'pos' : n < 0 ? 'neg' : ''
}

/**
 * Metric configuration matching the backend METRIC_CONFIG.
 */
export const METRIC_CONFIG = [
  { key: 'revenueYoy',           label: '营收同比',    unit: '%',  format: pctFmt,  group: '增长',   color: true,  defaultOn: true,  primary: true  },
  { key: 'revenueQoq',           label: '营收环比',    unit: '%',  format: pctFmt,  group: '增长',   color: true,  defaultOn: false, primary: false },
  { key: 'deductedNetProfitYoy', label: '扣非同比',    unit: '%',  format: pctFmt,  group: '增长',   color: true,  defaultOn: true,  primary: true  },
  { key: 'netProfitQoq',         label: '净利润环比',  unit: '%',  format: pctFmt,  group: '增长',   color: true,  defaultOn: false, primary: false },
  { key: 'grossMargin',          label: '毛利率',      unit: '%',  format: pctFmt,  group: '盈利',   color: false, defaultOn: true,  primary: true  },
  { key: 'netMargin',            label: '净利率',      unit: '%',  format: pctFmt,  group: '盈利',   color: false, defaultOn: false, primary: true  },
  { key: 'roe',                  label: 'ROE',         unit: '%',  format: pctFmt,  group: '盈利',   color: true,  defaultOn: false, primary: true  },
  { key: 'roa',                  label: 'ROA',         unit: '%',  format: pctFmt,  group: '盈利',   color: true,  defaultOn: false, primary: false },
  { key: 'eps',                  label: '每股收益',    unit: '元', format: numFmt2, group: '盈利',   color: true,  defaultOn: false, primary: false },
  { key: 'revenue',              label: '营业收入',    unit: '亿', format: yiFmt,   group: '规模',   color: false, defaultOn: true,  primary: true  },
  { key: 'netProfit',            label: '净利润',      unit: '亿', format: yiFmt,   group: '规模',   color: true,  defaultOn: true,  primary: true  },
  { key: 'deductedNetProfitTtm', label: '扣非TTM',     unit: '亿', format: yiFmt,   group: '规模',   color: false, defaultOn: false, primary: false },
  { key: 'totalAssets',          label: '总资产',      unit: '亿', format: yiFmt,   group: '规模',   color: false, defaultOn: false, primary: false },
  { key: 'totalEquity',          label: '净资产',      unit: '亿', format: yiFmt,   group: '规模',   color: false, defaultOn: false, primary: false },
  { key: 'operatingCashflow',    label: '经营现金流',  unit: '亿', format: yiFmt,   group: '现金流', color: true,  defaultOn: true,  primary: true  },
  { key: 'debtRatio',            label: '资产负债率',  unit: '%',  format: pctFmt,  group: '风险',   color: false, defaultOn: false, primary: false },
  { key: 'currentRatio',         label: '流动比率',    unit: '',   format: numFmt2, group: '风险',   color: false, defaultOn: false, primary: false },
]

export const METRIC_MAP = Object.fromEntries(METRIC_CONFIG.map(m => [m.key, m]))

export const DEFAULT_KEYS = METRIC_CONFIG.filter(m => m.defaultOn).map(m => m.key)
