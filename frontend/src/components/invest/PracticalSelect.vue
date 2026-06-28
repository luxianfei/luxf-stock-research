<template>
  <div class="practical-select">
    <!-- Title Card -->
    <div class="title-card">
      <h3 class="title">🎯 实战选股 · 一键综合分析</h3>
      <p class="desc">
        输入股票代码或名称，自动产出四大维度：完美走势 + 漂亮数字 + 稀缺性/成长动力星级 + 10 倍 PS 估值。
      </p>

      <div class="input-row">
        <input
          v-model="keyword"
          class="kw-input"
          placeholder="输入股票名称或代码"
          @keydown.enter="handleAnalyze"
        />
        <button class="primary-btn analyze-btn" :disabled="analyzing" @click="handleAnalyze">
          {{ analyzing ? '分析中...' : '立即分析' }}
        </button>
      </div>

      <div class="example-links">
        <span class="example-label">试试：</span>
        <a v-for="ex in examples" :key="ex.kw" class="example-link" @click="tryExample(ex.kw)">
          {{ ex.label }}
        </a>
      </div>
    </div>

    <!-- Loading Animation -->
    <div v-if="analyzing" class="loading-card">
      <p class="loading-title">正在分析 {{ keyword }}...</p>
      <div v-for="(step, idx) in analysisSteps" :key="idx" class="step-row">
        <span class="step-icon" :class="{ done: idx < currentStep, active: idx === currentStep }">
          {{ idx < currentStep ? '✓' : idx === currentStep ? '⏳' : '○' }}
        </span>
        <span class="step-text" :class="{ done: idx < currentStep, active: idx === currentStep }">
          {{ step }}
        </span>
      </div>
    </div>

    <!-- Result Area: 4 Cards -->
    <div v-if="result && result.status === 'SUCCESS'" class="result-area">
      <!-- Action Bar -->
      <div class="action-bar">
        <div class="action-info">
          <span class="result-name">{{ result.stockName }}</span>
          <span class="result-code">{{ result.stockCode }}</span>
          <span class="verdict-tag" :class="verdictClass(result.verdict)">{{ result.verdict || '--' }}</span>
        </div>
        <div class="action-btns">
          <button class="action-btn" @click="handleAnalyze">🔄 重新分析</button>
          <button class="action-btn danger" @click="handleDeleteResult">🗑 删除</button>
        </div>
      </div>

      <!-- Card 1: Perfect Trend -->
      <div class="analysis-card">
        <div class="card-header">
          <span class="card-num">①</span>
          <span class="card-title">完美的走势</span>
          <span class="card-score">{{ result.trendScore?.toFixed(1) || '--' }} <small>/ 100</small></span>
        </div>
        <div class="card-body">
          <p class="card-summary">{{ trendSummary }}</p>
          <div class="kpi-row">
            <div class="kpi-item">
              <div class="kpi-label">走势评分</div>
              <div class="kpi-value" :class="scoreClass(result.trendScore)">{{ result.trendScore?.toFixed(1) || '--' }}</div>
            </div>
            <div class="kpi-item" v-if="aj">
              <div class="kpi-label">最新价</div>
              <div class="kpi-value">{{ aj.latest_price?.toFixed(2) || '--' }}</div>
            </div>
            <div class="kpi-item" v-if="aj">
              <div class="kpi-label">今年涨幅</div>
              <div class="kpi-value" :class="pctClass(aj.ytd_gain)">{{ aj.ytd_gain != null ? (aj.ytd_gain > 0 ? '+' : '') + aj.ytd_gain.toFixed(1) + '%' : '--' }}</div>
            </div>
            <div class="kpi-item" v-if="aj">
              <div class="kpi-label">K线数据</div>
              <div class="kpi-value">{{ aj.klines_count || 0 }}月</div>
            </div>
          </div>
          <div class="trend-bar" v-if="result.trendScore != null">
            <div class="trend-bar-fill" :style="{ width: result.trendScore + '%' }" :class="scoreBarClass(result.trendScore)"></div>
          </div>
        </div>
      </div>

      <!-- Card 2: Beautiful Numbers -->
      <div class="analysis-card">
        <div class="card-header">
          <span class="card-num">②</span>
          <span class="card-title">漂亮的数字 · {{ aj?.quarters_count || 16 }} 季度财务</span>
          <span class="card-score">{{ result.financialScore?.toFixed(1) || '--' }} <small>/ 100</small></span>
        </div>
        <div class="card-body">
          <p class="card-summary">{{ result.summaryOneLiner || '数据不足' }}</p>
          <div class="kpi-row" v-if="aj">
            <div class="kpi-item">
              <div class="kpi-label">毛利率</div>
              <div class="kpi-value" :class="marginClass(aj.latest_gross_margin)">{{ aj.latest_gross_margin != null ? aj.latest_gross_margin.toFixed(1) + '%' : '--' }}</div>
            </div>
            <div class="kpi-item">
              <div class="kpi-label">营收同比</div>
              <div class="kpi-value" :class="pctClass(aj.latest_revenue_yoy)">{{ aj.latest_revenue_yoy != null ? aj.latest_revenue_yoy.toFixed(1) + '%' : '--' }}</div>
            </div>
            <div class="kpi-item">
              <div class="kpi-label">扣非同比</div>
              <div class="kpi-value" :class="pctClass(aj.latest_profit_yoy)">{{ aj.latest_profit_yoy != null ? aj.latest_profit_yoy.toFixed(1) + '%' : '--' }}</div>
            </div>
            <div class="kpi-item">
              <div class="kpi-label">净利率</div>
              <div class="kpi-value">{{ aj.latest_net_margin != null ? aj.latest_net_margin.toFixed(1) + '%' : '--' }}</div>
            </div>
            <div class="kpi-item">
              <div class="kpi-label">EPS</div>
              <div class="kpi-value">{{ aj.latest_eps != null ? aj.latest_eps.toFixed(2) : '--' }}</div>
            </div>
            <div class="kpi-item">
              <div class="kpi-label">ROE</div>
              <div class="kpi-value">{{ aj.latest_roe != null ? aj.latest_roe.toFixed(1) + '%' : '--' }}</div>
            </div>
          </div>
          <div class="trend-bar" v-if="result.financialScore != null">
            <div class="trend-bar-fill" :style="{ width: result.financialScore + '%' }" :class="scoreBarClass(result.financialScore)"></div>
          </div>
        </div>
      </div>

      <!-- Card 3: Scarcity + Growth Rating -->
      <div class="analysis-card">
        <div class="card-header">
          <span class="card-num">③</span>
          <span class="card-title">稀缺性 + 成长动力 星级评级</span>
          <span class="ai-badge">{{ result.aiModel === 'local' ? '⚙️ 本地启发式' : '🤖 AI 生成' }}</span>
        </div>
        <div class="card-body">
          <div class="rating-row">
            <div class="rating-block">
              <div class="rating-label">稀缺性</div>
              <div class="stars-row">
                <span v-for="i in 5" :key="i" class="star" :class="{ filled: i <= (result.scarcityStars || 0) }">★</span>
                <span class="star-score">{{ result.scarcityStars || 0 }}.0 / 5.0</span>
              </div>
              <div class="rating-bar">
                <div class="rating-bar-fill star-bar" :style="{ width: ((result.scarcityStars || 0) / 5 * 100) + '%' }"></div>
              </div>
              <p class="rating-desc">{{ scarcityDesc }}</p>
            </div>
            <div class="rating-block">
              <div class="rating-label">成长动力</div>
              <div class="stars-row">
                <span v-for="i in 5" :key="i" class="star" :class="{ filled: i <= (result.growthStars || 0) }">★</span>
                <span class="star-score">{{ result.growthStars || 0 }}.0 / 5.0</span>
              </div>
              <div class="rating-bar">
                <div class="rating-bar-fill growth-bar" :style="{ width: ((result.growthStars || 0) / 5 * 100) + '%' }"></div>
              </div>
              <p class="rating-desc">{{ growthDesc }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Card 4: 10x PS Valuation -->
      <div class="analysis-card">
        <div class="card-header">
          <span class="card-num">④</span>
          <span class="card-title">10 倍 PS 估值</span>
          <span class="verdict-tag" :class="verdictClass(result.tenPsVerdict || result.verdict)">{{ result.tenPsVerdict || result.verdict || '--' }}</span>
        </div>
        <div class="card-body">
          <div v-if="aj && aj.fair_cap_y1" class="ps-table">
            <div class="ps-row">
              <span class="ps-label">最新季度营收</span>
              <span class="ps-value">{{ aj.latest_revenue ? (aj.latest_revenue / 1e8).toFixed(2) + ' 亿' : '--' }}</span>
            </div>
            <div class="ps-row">
              <span class="ps-label">明年预测营收 (Y1)</span>
              <span class="ps-value highlight">{{ aj.forecast_revenue_y1 }} 亿</span>
            </div>
            <div class="ps-row">
              <span class="ps-label">后年预测营收 (Y2)</span>
              <span class="ps-value">{{ aj.forecast_revenue_y2 }} 亿</span>
            </div>
            <div class="ps-row">
              <span class="ps-label">合理市值 (Y1×10)</span>
              <span class="ps-value highlight">{{ aj.fair_cap_y1 }} 亿</span>
            </div>
            <div class="ps-row">
              <span class="ps-label">合理市值 (Y2×10)</span>
              <span class="ps-value">{{ aj.fair_cap_y2 }} 亿</span>
            </div>
          </div>
          <p v-else class="card-summary">数据不足，无法完成 10PS 估值。</p>
          <p class="valuation-note" v-if="aj && aj.fair_cap_y1">
            合理市值 = 预测营收 × 10（适用于净利率接近 25% 的高科技公司）。
            当前市值对应明年 10 倍 PS，或被低估；对应 2-3 年后 10 倍 PS，或存泡沫，需警惕。
          </p>
        </div>
      </div>

      <!-- Elapsed info -->
      <div class="elapsed-info" v-if="elapsedMs">
        分析耗时 {{ (elapsedMs / 1000).toFixed(1) }} 秒
      </div>
    </div>

    <!-- Failed result -->
    <div v-if="result && result.status === 'FAILED'" class="fail-card">
      <p>{{ result.summaryOneLiner || '分析失败' }}</p>
    </div>

    <!-- History Section -->
    <div class="history-section">
      <div class="history-header">
        <h3 class="history-title">📚 历史分析记录</h3>
        <div class="history-controls">
          <input
            v-model="historyKw"
            class="history-search"
            placeholder="搜索股票名称或代码..."
            @input="onHistorySearch"
          />
        </div>
      </div>

      <div v-if="historyRecords.length" class="history-list">
        <div v-for="h in historyRecords" :key="h.id" class="history-item">
          <div class="history-info">
            <span class="history-name">{{ h.stockName }}</span>
            <span class="history-code">{{ h.stockCode }}</span>
            <span class="verdict-tag sm" :class="verdictClass(h.verdict)">{{ h.verdict || '--' }}</span>
          </div>
          <div class="history-meta">
            <span class="history-summary">{{ h.summaryOneLiner || '' }}</span>
            <span class="history-time">{{ formatTime(h.submittedAt) }}</span>
          </div>
          <div class="history-actions">
            <button class="history-del-btn" @click="handleDeleteHistory(h.id)" title="删除">🗑</button>
          </div>
        </div>
      </div>
      <div v-else class="history-empty">
        {{ historyLoading ? '加载中...' : '暂无记录' }}
      </div>

      <!-- Pagination -->
      <div v-if="historyTotal > historySize" class="history-pagination">
        <button class="page-btn" :disabled="historyPage <= 0" @click="goHistoryPage(historyPage - 1)">‹ 上一页</button>
        <span class="page-info">{{ historyPage + 1 }} / {{ historyTotalPages }}</span>
        <button class="page-btn" :disabled="historyPage >= historyTotalPages - 1" @click="goHistoryPage(historyPage + 1)">下一页 ›</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { runPracticalSelect, fetchSelectHistory, deleteSelectRecord } from '@/api'

// ---- State ----
const keyword = ref('')
const analyzing = ref(false)
const result = ref(null)
const currentStep = ref(0)
const elapsedMs = ref(0)

const historyRecords = ref([])
const historyPage = ref(0)
const historySize = 20
const historyTotal = ref(0)
const historyTotalPages = ref(1)
const historyKw = ref('')
const historyLoading = ref(false)

const examples = [
  { label: '赛腾股份', kw: '赛腾股份' },
  { label: '000001', kw: '000001' },
  { label: '300750', kw: '300750' },
  { label: '600519', kw: '600519' },
]

const analysisSteps = [
  '① 解析月线走势',
  '② 调取 16 季度财务',
  '③ 估算 PS 估值',
  '④ AI 评级稀缺性 + 成长动力',
]

let stepTimer = null
let searchTimer = null

// ---- Computed ----
const aj = computed(() => result.value?.analysisJson || null)

const trendSummary = computed(() => {
  if (!result.value) return ''
  const score = result.value.trendScore
  if (score == null) return '走势数据不足'
  if (score >= 70) return '月线走势稳健，长期趋势向上。'
  if (score >= 40) return '月线走势震荡，方向不明确。'
  return '月线走势偏弱，下行趋势明显。'
})

const scarcityDesc = computed(() => {
  const s = result.value?.scarcityStars || 0
  if (s >= 4) return '毛利率高且稳定，行业壁垒强，具有稀缺性。'
  if (s >= 3) return '毛利率中等偏上，具备一定竞争优势。'
  return '毛利率偏低或波动较大，行业竞争激烈。'
})

const growthDesc = computed(() => {
  const g = result.value?.growthStars || 0
  if (g >= 4) return '营收和利润高速增长，成长动力充足。'
  if (g >= 3) return '营收稳健增长，具备一定成长潜力。'
  return '增速放缓或出现下滑，成长动力不足。'
})

// ---- Methods ----
function tryExample(kw) {
  keyword.value = kw
  handleAnalyze()
}

async function handleAnalyze() {
  const kw = keyword.value.trim()
  if (!kw) return
  analyzing.value = true
  result.value = null
  currentStep.value = 0
  elapsedMs.value = 0

  const t0 = Date.now()
  stepTimer = setInterval(() => {
    if (currentStep.value < analysisSteps.length - 1) {
      currentStep.value++
    }
  }, 3000)

  try {
    result.value = await runPracticalSelect(kw)
    elapsedMs.value = Date.now() - t0
    await loadHistory()
  } catch (e) {
    alert(e.response?.data?.detail || '分析失败')
  } finally {
    analyzing.value = false
    if (stepTimer) clearInterval(stepTimer)
  }
}

async function handleDeleteResult() {
  if (!result.value?.id) return
  if (!confirm('确定删除此分析记录？')) return
  try {
    await deleteSelectRecord(result.value.id)
    result.value = null
    await loadHistory()
  } catch (e) {
    alert('删除失败')
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await fetchSelectHistory(historyPage.value, historySize, historyKw.value)
    historyRecords.value = res.records || []
    historyTotal.value = res.total || 0
    historyTotalPages.value = res.totalPages || 1
  } catch (e) {
    console.error('History load error:', e)
  } finally {
    historyLoading.value = false
  }
}

function onHistorySearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    historyPage.value = 0
    loadHistory()
  }, 300)
}

function goHistoryPage(p) {
  if (p < 0 || p >= historyTotalPages.value) return
  historyPage.value = p
  loadHistory()
}

async function handleDeleteHistory(id) {
  if (!confirm('确定删除此记录？')) return
  try {
    await deleteSelectRecord(id)
    await loadHistory()
  } catch (e) {
    alert('删除失败')
  }
}

function verdictClass(v) {
  if (!v) return ''
  if (v === '买入' || v === '低估') return 'verdict-good'
  if (v === '回避' || v === '高估' || v === '泡沫') return 'verdict-bad'
  return 'verdict-neutral'
}

function scoreClass(score) {
  if (score == null) return ''
  if (score >= 70) return 'score-good'
  if (score >= 40) return 'score-warn'
  return 'score-bad'
}

function scoreBarClass(score) {
  if (score >= 70) return 'bar-good'
  if (score >= 40) return 'bar-warn'
  return 'bar-bad'
}

function pctClass(v) {
  if (v == null) return ''
  return v >= 0 ? 'val-pos' : 'val-neg'
}

function marginClass(v) {
  if (v == null) return ''
  if (v >= 40) return 'val-pos'
  if (v >= 20) return ''
  return 'val-neg'
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diffMs = now - d
  if (diffMs < 60000) return '刚刚'
  if (diffMs < 3600000) return Math.floor(diffMs / 60000) + ' 分钟前'
  if (diffMs < 86400000) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

onMounted(loadHistory)
onBeforeUnmount(() => {
  if (stepTimer) clearInterval(stepTimer)
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<style scoped>
.practical-select {
  padding: 0;
}

/* Title Card */
.title-card {
  background: linear-gradient(135deg, var(--base, #1a56db) 0%, #3b82f6 100%);
  color: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}
.title {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 8px;
}
.desc {
  font-size: 13px;
  opacity: 0.85;
  margin: 0 0 16px;
  line-height: 1.5;
}
.input-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.kw-input {
  flex: 1;
  max-width: 320px;
  padding: 10px 14px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  background: rgba(255,255,255,0.95);
  color: #333;
}
.analyze-btn {
  height: 40px;
  font-size: 14px;
  padding: 0 24px;
  border-radius: 8px;
  background: #fff;
  color: var(--base, #1a56db);
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: opacity 0.2s;
}
.analyze-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.analyze-btn:hover:not(:disabled) {
  opacity: 0.9;
}

/* Example links */
.example-links {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
.example-label {
  font-size: 12px;
  opacity: 0.7;
}
.example-link {
  font-size: 12px;
  color: #fff;
  cursor: pointer;
  text-decoration: underline;
  opacity: 0.8;
  padding: 2px 4px;
}
.example-link:hover {
  opacity: 1;
}
.example-link + .example-link::before {
  content: '·';
  opacity: 0.5;
  margin-right: 4px;
  text-decoration: none;
}

/* Loading */
.loading-card {
  background: #f8fafc;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
}
.loading-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--base, #1a56db);
  margin: 0 0 12px;
}
.step-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.step-icon {
  font-size: 14px;
  color: #94a3b8;
  width: 20px;
  text-align: center;
}
.step-icon.done { color: #16a34a; }
.step-icon.active { color: var(--base, #1a56db); }
.step-text {
  font-size: 13px;
  color: #94a3b8;
}
.step-text.done { color: var(--text, #1e293b); }
.step-text.active { color: var(--base, #1a56db); font-weight: 600; }

/* Result Area */
.result-area {
  margin-bottom: 24px;
}

/* Action Bar */
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 10px;
  padding: 12px 20px;
  margin-bottom: 16px;
}
.action-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.result-name {
  font-size: 18px;
  font-weight: 700;
}
.result-code {
  font-size: 13px;
  color: var(--text-muted, #94a3b8);
}
.action-btns {
  display: flex;
  gap: 8px;
}
.action-btn {
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid var(--border, #e2e8f0);
  background: var(--card-bg, #fff);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}
.action-btn:hover {
  background: #f1f5f9;
}
.action-btn.danger:hover {
  background: #fee2e2;
  color: #dc2626;
}

/* Analysis Cards */
.analysis-card {
  background: var(--card-bg, #fff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 10px;
  margin-bottom: 12px;
  overflow: hidden;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border, #e2e8f0);
  background: #f8fafc;
}
.card-num {
  font-size: 18px;
  font-weight: 700;
  color: var(--base, #1a56db);
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  flex: 1;
}
.card-score {
  font-size: 22px;
  font-weight: 700;
  color: var(--base, #1a56db);
}
.card-score small {
  font-size: 12px;
  color: var(--text-muted, #94a3b8);
  font-weight: 400;
}
.ai-badge {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 12px;
  background: #eef2ff;
  color: #4338ca;
}
.card-body {
  padding: 16px 20px;
}
.card-summary {
  font-size: 13px;
  color: var(--text-mid, #64748b);
  margin: 0 0 12px;
  line-height: 1.5;
}

/* KPI Row */
.kpi-row {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.kpi-item {
  min-width: 70px;
}
.kpi-label {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  margin-bottom: 2px;
}
.kpi-value {
  font-size: 18px;
  font-weight: 700;
}

/* Score colors */
.score-good { color: #16a34a; }
.score-warn { color: #d97706; }
.score-bad { color: #dc2626; }

/* Value colors */
.val-pos { color: #dc2626; }
.val-neg { color: #16a34a; }

/* Progress bars */
.trend-bar {
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
}
.trend-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}
.bar-good { background: #16a34a; }
.bar-warn { background: #d97706; }
.bar-bad { background: #dc2626; }

/* Rating section */
.rating-row {
  display: flex;
  gap: 32px;
}
.rating-block {
  flex: 1;
}
.rating-label {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}
.stars-row {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-bottom: 6px;
}
.star {
  font-size: 22px;
  color: #d1d5db;
}
.star.filled {
  color: #f59e0b;
}
.star-score {
  font-size: 13px;
  color: var(--text-muted, #94a3b8);
  margin-left: 8px;
}
.rating-bar {
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}
.rating-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}
.star-bar { background: #f59e0b; }
.growth-bar { background: #10b981; }
.rating-desc {
  font-size: 12px;
  color: var(--text-muted, #94a3b8);
  margin: 0;
  line-height: 1.5;
}

/* PS Table */
.ps-table {
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
}
.ps-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border, #e2e8f0);
  font-size: 13px;
}
.ps-row:last-child {
  border-bottom: none;
}
.ps-label {
  color: var(--text-muted, #94a3b8);
}
.ps-value {
  font-weight: 600;
}
.ps-value.highlight {
  color: var(--base, #1a56db);
}
.valuation-note {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  margin: 0;
  line-height: 1.6;
}

/* Verdict tags */
.verdict-tag {
  font-size: 13px;
  font-weight: 600;
  padding: 3px 12px;
  border-radius: 6px;
}
.verdict-tag.sm {
  font-size: 11px;
  padding: 2px 8px;
}
.verdict-good {
  background: #dcfce7;
  color: #16a34a;
}
.verdict-bad {
  background: #fee2e2;
  color: #dc2626;
}
.verdict-neutral {
  background: #fef3c7;
  color: #92400e;
}

/* Elapsed */
.elapsed-info {
  text-align: center;
  font-size: 12px;
  color: var(--text-muted, #94a3b8);
  padding: 8px 0;
}

/* Failed */
.fail-card {
  background: #fee2e2;
  border: 1px solid #fca5a5;
  border-radius: 10px;
  padding: 20px;
  text-align: center;
  margin-bottom: 20px;
  color: #dc2626;
}

/* History Section */
.history-section {
  margin-top: 24px;
}
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.history-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0;
}
.history-search {
  padding: 6px 12px;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  font-size: 13px;
  width: 200px;
  outline: none;
}
.history-search:focus {
  border-color: var(--base, #1a56db);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.history-item {
  display: flex;
  align-items: center;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 8px;
  padding: 10px 16px;
  gap: 12px;
  transition: background 0.15s;
}
.history-item:hover {
  background: #f8fafc;
}
.history-info {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 180px;
}
.history-name {
  font-weight: 600;
  font-size: 14px;
}
.history-code {
  font-size: 12px;
  color: var(--text-muted, #94a3b8);
}
.history-meta {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.history-summary {
  font-size: 12px;
  color: var(--text-mid, #64748b);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.history-time {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  white-space: nowrap;
}
.history-actions {
  flex-shrink: 0;
}
.history-del-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  opacity: 0.5;
  transition: opacity 0.2s;
  padding: 4px;
}
.history-del-btn:hover {
  opacity: 1;
}

.history-empty {
  text-align: center;
  padding: 24px;
  color: var(--text-muted, #94a3b8);
  font-size: 13px;
}

/* Pagination */
.history-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
}
.page-btn {
  padding: 6px 14px;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 6px;
  background: var(--card-bg, #fff);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}
.page-btn:hover:not(:disabled) {
  background: #f1f5f9;
}
.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.page-info {
  font-size: 13px;
  color: var(--text-muted, #94a3b8);
}
</style>
