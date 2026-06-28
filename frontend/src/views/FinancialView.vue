<template>
  <div>
    <h1 class="page-title" style="text-align:center;font-size:32px;font-weight:700;letter-spacing:2px;margin:8px 0 28px">
      财务分析
    </h1>

    <!-- Search bar -->
    <div class="search-bar">
      <div class="search-input-wrap">
        <input
          ref="searchInput"
          v-model="keyword"
          placeholder="输入股票名称或代码，多个用逗号分隔"
          @keydown.enter="handleQuery"
        />
        <button v-if="keyword" class="clear-btn" @click="keyword = ''">×</button>
      </div>
      <button class="primary-btn" :disabled="loading || isCollecting" @click="handleQuery">
        {{ isCollecting ? '采集中...' : loading ? '查询中...' : '查询' }}
      </button>
    </div>

    <!-- Auto-collection notification -->
    <Transition name="notification">
      <div v-if="collectNotification" class="collect-notification" :class="collectNotification.type">
        <div class="notif-header">
          <span class="notif-icon">{{ collectNotification.type === 'info' ? '⟳' : collectNotification.type === 'success' ? '✓' : '✗' }}</span>
          <span class="notif-message">{{ collectNotification.message }}</span>
          <button class="notif-close" @click="collectNotification = null">×</button>
        </div>
        <div v-if="collectNotification.details?.length" class="notif-details">
          <div
            v-for="(d, i) in collectNotification.details"
            :key="i"
            class="notif-detail"
            :class="d.status"
          >
            <span class="detail-icon">{{ d.status === 'success' ? '✓' : '✗' }}</span>
            {{ d.message }}
          </div>
        </div>
        <!-- Progress bar for collecting state -->
        <div v-if="collectNotification.type === 'info'" class="notif-progress">
          <div class="notif-progress-bar"></div>
        </div>
      </div>
    </Transition>

    <!-- Metric selector -->
    <div class="metric-chips">
      <button
        v-for="m in METRIC_CONFIG"
        :key="m.key"
        class="metric-chip"
        :class="{ on: selectedKeys.has(m.key) }"
        @click="toggleMetric(m.key)"
      >
        {{ m.label }}
      </button>
      <div class="chip-actions">
        <span>已选 {{ selectedKeys.size }} 项</span>
        <button @click="resetDefault">默认</button>
        <button @click="selectAll">全选</button>
        <button @click="clearAll">清空</button>
      </div>
    </div>

    <!-- Results -->
    <div v-if="result" class="results">
      <h2 class="section-title">核心财务指标对比分析</h2>
      <p class="section-subtitle">
        输入<span class="hl">{{ result.requested }}</span>只股票，已查询到<span class="hl">{{ result.matched }}</span>只股票
        <span v-if="result.notFound?.length">（未找到: {{ result.notFound.join('、') }}）</span>
      </p>

      <!-- Tables -->
      <div class="tables-wrap">
        <div v-for="stock in result.stocks" :key="stock.stockCode">
          <!-- Info card (single stock only) -->
          <StockInfoCard v-if="result.stocks.length === 1" :info="stock.basicInfo" :stock-name="stock.stockName" :stock-code="stock.stockCode" />

          <!-- Data table -->
          <div class="table-scroll">
            <table class="stock-table">
              <thead>
                <tr>
                  <th class="first-col">{{ stock.stockName }}<br/>({{ stock.stockCode }})</th>
                  <th v-for="q in stock.quarters" :key="q.quarter">{{ q.quarter }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="m in activeMetrics" :key="m.key">
                  <td class="metric-name">{{ m.label }}</td>
                  <td
                    v-for="q in stock.quarters"
                    :key="q.quarter + m.key"
                    :class="m.color ? colorClass(q[m.key]) : ''"
                  >
                    {{ m.format(q[m.key]) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Chart -->
      <div class="chart-section">
        <div class="chart-tabs">
          <button
            v-for="m in activeMetrics"
            :key="m.key"
            class="tab"
            :class="{ active: currentChartKey === m.key }"
            @click="currentChartKey = m.key"
          >
            {{ m.label }}
          </button>
        </div>
        <div class="chart-container">
          <canvas ref="chartCanvas"></canvas>
        </div>
        <div style="text-align:center;margin-top:12px">
          <button class="primary-btn" style="height:36px;font-size:13px;padding:0 20px" @click="handleExport">
            免费下载图表 + CSV
          </button>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="searched && !result?.stocks?.length" style="text-align:center;color:var(--text-muted);margin-top:32px">
      <p>未查询到相关股票数据。请确认输入的股票名称或代码。</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { Chart, registerables } from 'chart.js'
import { fetchFinancialData, collectSingle } from '@/api'
import { METRIC_CONFIG, METRIC_MAP, DEFAULT_KEYS, colorClass } from '@/utils/formatter'
import { useSkinStore } from '@/stores/skin'
import StockInfoCard from '@/components/financial/StockInfoCard.vue'

Chart.register(...registerables)

const skinStore = useSkinStore()
const keyword = ref('')
const loading = ref(false)
const searched = ref(false)
const result = ref(null)
const chartCanvas = ref(null)
const searchInput = ref(null)
let chartInstance = null

// Auto-collection state
const isCollecting = ref(false)
const collectNotification = ref(null)
// e.g. { type: 'info'|'success'|'error', message: '...', details: [...] }

// Metric selection
const STORAGE_KEY = 'quant.selectedMetrics'
const savedKeys = (() => {
  try {
    const s = JSON.parse(localStorage.getItem(STORAGE_KEY))
    if (Array.isArray(s) && s.length > 0) return new Set(s)
  } catch (e) {}
  return new Set(DEFAULT_KEYS)
})()
const selectedKeys = ref(savedKeys)

const currentChartKey = ref(Array.from(selectedKeys.value)[0] || DEFAULT_KEYS[0])

const activeMetrics = computed(() =>
  METRIC_CONFIG.filter(m => selectedKeys.value.has(m.key))
)

function toggleMetric(key) {
  const s = new Set(selectedKeys.value)
  if (s.has(key)) s.delete(key)
  else s.add(key)
  selectedKeys.value = s
  localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(s)))
  if (!s.has(currentChartKey.value)) {
    currentChartKey.value = Array.from(s)[0] || DEFAULT_KEYS[0]
  }
}

function resetDefault() {
  selectedKeys.value = new Set(DEFAULT_KEYS)
  currentChartKey.value = DEFAULT_KEYS[0]
  localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_KEYS))
}

function selectAll() {
  selectedKeys.value = new Set(METRIC_CONFIG.map(m => m.key))
  localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(selectedKeys.value)))
}

function clearAll() {
  selectedKeys.value = new Set()
  localStorage.setItem(STORAGE_KEY, JSON.stringify([]))
}

// Query
async function handleQuery() {
  const kw = keyword.value.trim()
  if (!kw) return
  loading.value = true
  searched.value = true
  collectNotification.value = null

  try {
    // Step 1: Check local DB first (no baostock fetch)
    const localRes = await fetchFinancialData(kw, 16, true)
    const missing = localRes.notFound || []

    if (missing.length > 0) {
      // Some stocks not in local DB — show tip and auto-collect
      isCollecting.value = true

      // Show already-found results while collecting missing ones
      if (localRes.stocks?.length > 0) {
        result.value = localRes
        await nextTick()
        renderChart()
      }

      collectNotification.value = {
        type: 'info',
        message: `发现 ${missing.length} 只股票本地暂无数据：${missing.join('、')}，正在自动采集...`,
        details: [],
      }

      let collected = 0
      let failed = 0
      for (const stock of missing) {
        try {
          const collectResult = await collectSingle(stock)
          if (collectResult.success) {
            collected++
            collectNotification.value.details.push({
              stock,
              status: 'success',
              message: `${collectResult.stockName || stock} 采集完成（${collectResult.quartersCollected} 个季度）`,
            })
          } else {
            failed++
            collectNotification.value.details.push({
              stock,
              status: 'error',
              message: `${stock}: ${collectResult.error || '采集失败'}`,
            })
          }
        } catch (e) {
          failed++
          collectNotification.value.details.push({
            stock,
            status: 'error',
            message: `${stock}: 采集异常`,
          })
        }
        // Update progress
        collectNotification.value.message =
          `正在采集 ${missing.length} 只股票（${collected + failed}/${missing.length}）...`
      }

      // Update notification
      collectNotification.value = {
        type: collected > 0 ? 'success' : 'error',
        message: collected > 0
          ? `采集完成：成功 ${collected} 只${failed > 0 ? `，失败 ${failed} 只` : ''}，正在刷新数据...`
          : `采集失败：${failed} 只股票未能获取数据`,
        details: collectNotification.value.details,
      }

      isCollecting.value = false

      // Re-query with full fetch to get all stocks (including newly collected)
      if (collected > 0) {
        try {
          const updated = await fetchFinancialData(kw)
          result.value = updated
          await nextTick()
          renderChart()
        } catch (e) {
          console.error('Re-query failed:', e)
        }
      }
    } else {
      // All stocks found in local DB — use local result directly
      result.value = localRes
      await nextTick()
      renderChart()
    }
  } catch (e) {
    console.error(e)
    result.value = null
  } finally {
    loading.value = false
  }
}

// Chart
function renderChart() {
  if (!chartInstance && chartCanvas.value) {
    // Will create on watch
  }
  rebuildChart()
}

function rebuildChart() {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
  if (!chartCanvas.value || !result.value?.stocks?.length) return

  const cfg = METRIC_MAP[currentChartKey.value]
  if (!cfg) return

  const isYi = cfg.unit === '亿'
  const allDates = new Map()
  result.value.stocks.forEach(s => {
    s.quarters.forEach(q => allDates.set(q.reportDate, q.quarter))
  })
  const axis = Array.from(allDates.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))

  const labels = axis.map(([, q]) => q)
  const palette = ['#2563eb', '#0891b2', '#16a34a', '#7c3aed', '#ea580c', '#db2777']

  const datasets = result.value.stocks.map((s, idx) => {
    const byDate = Object.fromEntries(s.quarters.map(q => [q.reportDate, q]))
    return {
      label: s.stockName,
      data: axis.map(([date]) => {
        const q = byDate[date]
        if (!q || q[currentChartKey.value] == null) return null
        const v = Number(q[currentChartKey.value])
        return isYi ? v / 1e8 : v
      }),
      borderColor: palette[idx % palette.length],
      backgroundColor: palette[idx % palette.length] + '33',
      tension: 0.3,
      spanGaps: true,
      pointRadius: 3,
      pointHoverRadius: 5,
      borderWidth: 2,
    }
  })

  chartInstance = new Chart(chartCanvas.value.getContext('2d'), {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top', labels: { usePointStyle: true } },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const v = ctx.parsed.y
              if (v == null) return ctx.dataset.label + ': --'
              return ctx.dataset.label + ': ' + v.toFixed(2) + (cfg.unit || '')
            }
          }
        }
      },
      scales: {
        y: { ticks: { callback: (val) => val + (cfg.unit || '') }, grid: { color: '#eef1f5' } },
        x: { grid: { display: false } }
      }
    }
  })
}

watch(currentChartKey, () => {
  nextTick(rebuildChart)
})

watch(() => result.value?.stocks, () => {
  nextTick(rebuildChart)
})

// Export
function handleExport() {
  if (!result.value?.stocks?.length) return

  // CSV
  const keys = activeMetrics.value
  const allDates = new Map()
  result.value.stocks.forEach(s => {
    s.quarters.forEach(q => allDates.set(q.reportDate, q.quarter))
  })
  const axis = Array.from(allDates.entries()).sort((a, b) => b[0].localeCompare(a[0]))

  const rows = [['股票名称', '股票代码', '指标', ...axis.map(([, q]) => q)]]
  result.value.stocks.forEach(s => {
    const byDate = Object.fromEntries(s.quarters.map(q => [q.reportDate, q]))
    keys.forEach(m => {
      rows.push([
        s.stockName,
        s.stockCode,
        m.label,
        ...axis.map(([date]) => {
          const q = byDate[date]
          if (!q || q[m.key] == null) return ''
          const v = Number(q[m.key])
          return m.unit === '亿' ? (v / 1e8).toFixed(4) : v.toFixed(4)
        })
      ])
    })
  })

  const csv = '\ufeff' + rows.map(r => r.map(c => /[",\n]/.test(c) ? `"${c.replace(/"/g, '""')}"` : c).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${result.value.stocks.map(s => s.stockName).join('_')}_财务数据.csv`
  a.click()
  URL.revokeObjectURL(url)

  // PNG from chart
  if (chartInstance) {
    const imgUrl = chartInstance.toBase64Image('image/png', 1)
    const imgA = document.createElement('a')
    imgA.href = imgUrl
    imgA.download = `${result.value.stocks.map(s => s.stockName).join('_')}_图表.png`
    imgA.click()
  }
}

onMounted(() => {
  searchInput.value?.focus()
})
</script>

<style scoped>
.page-title {
  text-align: center;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 2px;
  margin: 8px 0 28px;
}

/* Collect notification */
.collect-notification {
  max-width: 720px;
  margin: 0 auto 16px;
  border-radius: 10px;
  padding: 14px 18px;
  font-size: 14px;
  line-height: 1.6;
  position: relative;
  overflow: hidden;
}

.collect-notification.info {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
}

.collect-notification.success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.collect-notification.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.notif-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.notif-icon {
  font-size: 18px;
  font-weight: 700;
  flex-shrink: 0;
  width: 22px;
  text-align: center;
}

.info .notif-icon {
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.notif-message {
  flex: 1;
  font-weight: 500;
}

.notif-close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  opacity: 0.5;
  padding: 0 4px;
  color: inherit;
  line-height: 1;
}

.notif-close:hover {
  opacity: 1;
}

.notif-details {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.notif-detail {
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.notif-detail.success {
  color: #166534;
}

.notif-detail.error {
  color: #991b1b;
}

.detail-icon {
  font-weight: 700;
  font-size: 12px;
  width: 16px;
  text-align: center;
  flex-shrink: 0;
}

.notif-progress {
  margin-top: 10px;
  height: 3px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 2px;
  overflow: hidden;
}

.notif-progress-bar {
  height: 100%;
  width: 30%;
  background: #3b82f6;
  border-radius: 2px;
  animation: progress-indeterminate 1.5s ease-in-out infinite;
}

@keyframes progress-indeterminate {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}

/* Transition */
.notification-enter-active {
  transition: all 0.3s ease-out;
}

.notification-leave-active {
  transition: all 0.2s ease-in;
}

.notification-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.notification-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
