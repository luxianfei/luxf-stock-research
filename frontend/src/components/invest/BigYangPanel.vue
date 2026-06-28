<template>
  <div>
    <p style="color:var(--text-muted);margin-bottom:16px">
      股票池内标的出现连续 1-2 天涨停后进入观察池，回踩首板起涨点附近时触发买入提示。
    </p>

    <button class="primary-btn" style="height:38px;font-size:14px;padding:0 20px;margin-bottom:20px" :disabled="scanning" @click="handleScan">
      {{ scanning ? '扫描中...' : '立即扫描' }}
    </button>

    <!-- Scan result -->
    <div v-if="scanResult" class="scan-result-bar">
      扫描完成：共扫描 {{ scanResult.scanned }} 只，
      新发现信号 {{ scanResult.new_signals }} 个，
      新告警 {{ scanResult.new_alerts }} 条，
      过期 {{ scanResult.expired }} 个
      <span v-if="scanResult.errors?.length" style="color:#dc2626">（{{ scanResult.errors.length }} 个错误）</span>
    </div>

    <!-- Summary cards -->
    <div class="by-summary-row">
      <div v-for="card in summaryCards" :key="card.label" class="by-summary-card" :style="card.cardStyle">
        <div class="by-summary-label">{{ card.label }}</div>
        <div class="by-summary-value" :style="card.style">{{ card.value }}</div>
      </div>
    </div>

    <!-- Side-by-side panels -->
    <div class="by-panels">
      <!-- Left: Signal List (观察池) -->
      <div class="by-panel">
        <div class="by-panel-head">
          <h3 class="by-panel-title">观察池</h3>
          <span class="by-panel-count">{{ signals.length }}</span>
        </div>
        <!-- Status filter -->
        <div class="by-filter-row">
          <button
            v-for="f in signalFilters"
            :key="f.value"
            class="by-filter-btn"
            :class="{ active: signalFilter === f.value }"
            @click="signalFilter = f.value; loadSignals()"
          >
            {{ f.label }}
          </button>
        </div>
        <div v-if="signals.length" class="by-signal-list">
          <div v-for="sig in signals" :key="sig.id" class="by-signal-card">
            <div class="by-signal-head">
              <span class="by-signal-name">{{ sig.stockName }}</span>
              <span class="by-signal-code">{{ sig.stockCode }}</span>
              <span class="by-signal-status" :style="statusStyle(sig.status)">{{ statusLabel(sig.status) }}</span>
            </div>
            <div class="by-signal-kv">
              <div class="by-kv">
                <span class="by-kv-label">起涨价</span>
                <span class="by-kv-value">{{ sig.triggerPrice ? sig.triggerPrice.toFixed(2) : '--' }}</span>
              </div>
              <div class="by-kv">
                <span class="by-kv-label">收盘价</span>
                <span class="by-kv-value">{{ sig.basePrice ? sig.basePrice.toFixed(2) : '--' }}</span>
              </div>
              <div class="by-kv" v-if="sig.triggerPrice && sig.basePrice">
                <span class="by-kv-label">偏离</span>
                <span class="by-kv-value" :class="deviationClass(sig)">{{ deviationPct(sig) }}</span>
              </div>
            </div>
            <div class="by-signal-time">{{ formatTime(sig.createdAt) }}</div>
          </div>
        </div>
        <div v-else class="by-empty">暂无信号</div>
      </div>

      <!-- Right: Alerts (买入提示消息) -->
      <div class="by-panel">
        <div class="by-panel-head">
          <h3 class="by-panel-title">买入提示消息</h3>
          <span class="by-panel-count" v-if="unreadCount > 0" style="color:#dc2626">{{ unreadCount }}</span>
        </div>
        <div v-if="alerts.length" class="by-alert-list">
          <div
            v-for="alert in alerts"
            :key="alert.id"
            class="by-alert-card"
            :class="{ unread: !alert.read }"
          >
            <div class="by-alert-head">
              <span class="by-alert-title">
                <span v-if="!alert.read" class="by-unread-dot"></span>
                {{ alert.title }}
              </span>
              <span class="by-alert-time">{{ formatTime(alert.createdAt) }}</span>
            </div>
            <div class="by-alert-meta">
              {{ alert.stockName }} · {{ alert.stockCode }}
              <span v-if="alert.triggerPrice"> · ¥{{ alert.triggerPrice }}</span>
            </div>
            <div class="by-alert-body">{{ alert.message }}</div>
            <div class="by-alert-actions" v-if="!alert.read">
              <button class="by-read-btn" @click="handleMarkRead(alert.id)">标记已读</button>
            </div>
            <div v-else class="by-alert-read-tag">已读</div>
          </div>
        </div>
        <div v-else class="by-empty">暂无告警</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchBigYangSignals, fetchBigYangAlerts, runBigYangScan, markAlertRead } from '@/api'

const props = defineProps({ summary: Object })
const emit = defineEmits(['refresh'])

const signals = ref([])
const alerts = ref([])
const scanning = ref(false)
const scanResult = ref(null)
const signalFilter = ref('')

const signalFilters = [
  { label: '全部', value: '' },
  { label: '观察中', value: 'watching' },
  { label: '已触发', value: 'triggered' },
  { label: '已过期', value: 'expired' },
]

const summaryCards = computed(() => {
  const s = props.summary || {}
  return [
    { label: '未读提示', value: s.unreadAlertCount || 0, style: (s.unreadAlertCount || 0) > 0 ? { color: '#dc2626' } : {}, cardStyle: (s.unreadAlertCount || 0) > 0 ? { background: '#fff1f2' } : {} },
    { label: '观察中', value: s.watchingCount || 0, style: {}, cardStyle: {} },
    { label: '今日新入池', value: s.todayNewWatchingCount || 0, style: {}, cardStyle: {} },
    { label: '今日触发', value: s.todayTriggeredCount || 0, style: (s.todayTriggeredCount || 0) > 0 ? { color: '#16a34a' } : {}, cardStyle: (s.todayTriggeredCount || 0) > 0 ? { background: '#f0fdf4' } : {} },
    { label: '已失效', value: s.expiredCount || 0, style: { color: '#94a3b8' }, cardStyle: {} },
  ]
})

const unreadCount = computed(() => alerts.value.filter(a => !a.read).length)

async function loadSignals() {
  try {
    signals.value = await fetchBigYangSignals(signalFilter.value || undefined)
  } catch (e) { console.error(e) }
}

async function loadAlerts() {
  try {
    alerts.value = await fetchBigYangAlerts()
  } catch (e) { console.error(e) }
}

async function loadAll() {
  await Promise.all([loadSignals(), loadAlerts()])
}

async function handleScan() {
  scanning.value = true
  scanResult.value = null
  try {
    scanResult.value = await runBigYangScan()
    await loadAll()
    emit('refresh')
  } catch (e) {
    alert(e.response?.data?.detail || '扫描失败')
  } finally {
    scanning.value = false
  }
}

async function handleMarkRead(id) {
  try {
    await markAlertRead(id)
    const a = alerts.value.find(x => x.id === id)
    if (a) a.read = true
    emit('refresh')
  } catch (e) { console.error(e) }
}

function statusLabel(s) {
  if (s === 'watching') return '观察中'
  if (s === 'triggered') return '已触发'
  if (s === 'expired') return '已过期'
  return s
}

function statusStyle(s) {
  if (s === 'watching') return { color: '#2563eb', background: '#eff6ff' }
  if (s === 'triggered') return { color: '#16a34a', background: '#dcfce7' }
  if (s === 'expired') return { color: '#94a3b8', background: '#f1f5f9' }
  return {}
}

function deviationPct(sig) {
  if (!sig.triggerPrice || !sig.basePrice) return '--'
  const pct = ((sig.basePrice - sig.triggerPrice) / sig.triggerPrice * 100)
  return (pct >= 0 ? '+' : '') + pct.toFixed(1) + '%'
}

function deviationClass(sig) {
  if (!sig.triggerPrice || !sig.basePrice) return ''
  const pct = (sig.basePrice - sig.triggerPrice) / sig.triggerPrice * 100
  return pct > 0 ? 'val-pos' : pct < 0 ? 'val-neg' : ''
}

function formatTime(iso) {
  if (!iso) return '--'
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now - d
  if (diffMs < 60000) return '刚刚'
  if (diffMs < 3600000) return Math.floor(diffMs / 60000) + ' 分钟前'
  if (diffMs < 86400000) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('zh-CN')
}

onMounted(loadAll)
</script>

<style scoped>
.scan-result-bar {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 20px;
  font-size: 13px;
}

.by-summary-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}
.by-summary-card {
  background: var(--card-bg, #fff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 8px;
  padding: 16px 20px;
  min-width: 110px;
  text-align: center;
  transition: background 0.15s;
}
.by-summary-label {
  font-size: 12px;
  color: var(--text-muted, #94a3b8);
}
.by-summary-value {
  font-size: 24px;
  font-weight: 700;
  margin-top: 4px;
}

.by-panels {
  display: flex;
  gap: 20px;
}
@media (max-width: 800px) {
  .by-panels { flex-direction: column; }
}

.by-panel {
  flex: 1;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 10px;
  padding: 16px;
  min-width: 0;
}
.by-panel-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.by-panel-title {
  font-size: 15px;
  font-weight: 700;
  margin: 0;
}
.by-panel-count {
  font-size: 12px;
  font-weight: 600;
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 10px;
}

.by-filter-row {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}
.by-filter-btn {
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid var(--border, #e2e8f0);
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.15s;
}
.by-filter-btn.active {
  background: var(--base, #1a56db);
  color: #fff;
  border-color: var(--base, #1a56db);
}

.by-signal-list, .by-alert-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.by-signal-card {
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 8px;
  padding: 12px;
  transition: background 0.15s;
}
.by-signal-card:hover {
  background: #f8fafc;
}
.by-signal-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.by-signal-name {
  font-weight: 600;
  font-size: 14px;
}
.by-signal-code {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}
.by-signal-status {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.by-signal-kv {
  display: flex;
  gap: 16px;
  margin-bottom: 6px;
}
.by-kv {
  display: flex;
  flex-direction: column;
}
.by-kv-label {
  font-size: 10px;
  color: var(--text-muted, #94a3b8);
}
.by-kv-value {
  font-size: 14px;
  font-weight: 600;
}
.by-signal-time {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}

.val-pos { color: #dc2626; }
.val-neg { color: #16a34a; }

.by-alert-card {
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 8px;
  padding: 12px;
  transition: background 0.15s;
}
.by-alert-card.unread {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.by-alert-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 4px;
}
.by-alert-title {
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.by-unread-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #dc2626;
  flex-shrink: 0;
}
.by-alert-time {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  white-space: nowrap;
}
.by-alert-meta {
  font-size: 12px;
  color: var(--text-mid, #64748b);
  margin-bottom: 4px;
}
.by-alert-body {
  font-size: 13px;
  color: var(--text, #1e293b);
  line-height: 1.5;
  margin-bottom: 8px;
}
.by-alert-actions {
  display: flex;
  gap: 8px;
}
.by-read-btn {
  padding: 4px 10px;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 4px;
  background: transparent;
  font-size: 11px;
  cursor: pointer;
  transition: background 0.15s;
}
.by-read-btn:hover {
  background: #f1f5f9;
}
.by-alert-read-tag {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}

.by-empty {
  text-align: center;
  padding: 24px;
  color: var(--text-muted, #94a3b8);
  font-size: 13px;
}
</style>
