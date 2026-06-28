<template>
  <div>
    <h1 class="page-title" style="text-align:center;font-size:32px;font-weight:700;letter-spacing:2px;margin:8px 0 28px">
      数据采集
    </h1>

    <!-- Tabs -->
    <div class="invest-tabs" style="justify-content:center">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="invest-tab"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Tab 1: Single Stock -->
    <div v-show="activeTab === 'single'" class="invest-panel active">
      <div class="collect-single-form">
        <div class="search-bar">
          <div class="search-input-wrap">
            <input
              v-model="singleKeyword"
              placeholder="输入股票名称或代码"
              @keydown.enter="handleSingleCollect"
            />
            <button v-if="singleKeyword" class="clear-btn" @click="singleKeyword = ''">×</button>
          </div>
          <button class="primary-btn" :disabled="singleLoading" @click="handleSingleCollect">
            {{ singleLoading ? '采集中...' : '采集' }}
          </button>
        </div>

        <!-- Stock DB Status -->
        <div v-if="stockStatus" class="collect-result-card" style="margin-top:12px">
          <div class="result-title">数据库状态</div>
          <template v-if="stockStatus.inDb">
            <div class="result-kv">
              <div class="kv-item">
                <span class="kv-label">股票名称</span>
                <span class="kv-value">{{ stockStatus.stockName || '-' }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">股票代码</span>
                <span class="kv-value">{{ stockStatus.stockCode || '-' }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">已采集季度</span>
                <span class="kv-value">{{ stockStatus.quartersInDb ?? '-' }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">最早季度</span>
                <span class="kv-value">{{ stockStatus.earliestQuarter || '-' }}</span>
              </div>
              <div class="kv-item">
                <span class="kv-label">最新季度</span>
                <span class="kv-value">{{ stockStatus.latestQuarter || '-' }}</span>
              </div>
            </div>
          </template>
          <div v-else style="color:var(--text-muted);font-size:14px">
            该股票尚未采集数据
          </div>
        </div>

        <!-- Single Collect Result -->
        <div v-if="singleResult" class="collect-result-card">
          <div class="result-title">采集结果</div>
          <div class="result-kv">
            <div class="kv-item">
              <span class="kv-label">股票名称</span>
              <span class="kv-value">{{ singleResult.stockName || '-' }}</span>
            </div>
            <div class="kv-item">
              <span class="kv-label">股票代码</span>
              <span class="kv-value">{{ singleResult.stockCode || '-' }}</span>
            </div>
            <div class="kv-item">
              <span class="kv-label">采集季度数</span>
              <span class="kv-value">{{ singleResult.quartersCollected ?? '-' }}</span>
            </div>
            <div class="kv-item">
              <span class="kv-label">最早季度</span>
              <span class="kv-value">{{ singleResult.earliestQuarter || '-' }}</span>
            </div>
            <div class="kv-item">
              <span class="kv-label">最新季度</span>
              <span class="kv-value">{{ singleResult.latestQuarter || '-' }}</span>
            </div>
          </div>
        </div>

        <div v-if="singleError" style="text-align:center;color:var(--up);margin-top:12px;font-size:14px">
          {{ singleError }}
        </div>
      </div>
    </div>

    <!-- Tab 2: Batch Collection -->
    <div v-show="activeTab === 'batch'" class="invest-panel active">
      <div class="collect-batch-input">
        <!-- Mode toggle -->
        <div class="collect-mode-toggle">
          <button :class="{ active: batchMode === 'text' }" @click="batchMode = 'text'">文本输入</button>
          <button :class="{ active: batchMode === 'csv' }" @click="batchMode = 'csv'">CSV 上传</button>
        </div>

        <!-- Text mode -->
        <div v-if="batchMode === 'text'">
          <textarea
            v-model="batchText"
            placeholder="输入股票代码，每行一个或用逗号分隔&#10;例如：600519,000858,300750"
          ></textarea>
        </div>

        <!-- CSV mode -->
        <div v-if="batchMode === 'csv'">
          <label class="file-upload-area" @click="triggerFileInput">
            <input ref="fileInput" type="file" accept=".csv" @change="handleFileSelect" />
            <div v-if="!csvFile" style="font-size:14px">
              点击选择 CSV 文件
            </div>
            <div v-else style="font-size:14px;color:var(--text)">
              已选择：{{ csvFile.name }}
            </div>
          </label>
        </div>

        <!-- Incremental checkbox -->
        <label class="collect-checkbox">
          <input type="checkbox" v-model="batchIncremental" />
          增量采集
        </label>

        <!-- Start button -->
        <div style="text-align:center;margin-top:16px">
          <button class="primary-btn" :disabled="batchLoading || batchRunning" @click="handleBatchCollect">
            {{ batchLoading ? '提交中...' : batchRunning ? '采集中...' : '开始采集' }}
          </button>
        </div>
      </div>

      <!-- Batch progress -->
      <div v-if="batchTaskId" class="collect-progress">
        <div class="progress-bar-wrap">
          <div class="progress-bar-fill" :style="{ width: batchProgressPercent + '%' }"></div>
        </div>
        <div class="progress-text">
          <span>{{ batchCompleted }} / {{ batchTotal }}</span>
          <span>{{ batchProgressPercent }}%</span>
        </div>
        <div v-if="batchCurrentStock" class="current-stock">
          正在处理：{{ batchCurrentStock }}
        </div>
        <div v-if="batchStatus === 'complete'" class="current-stock" style="color:var(--down)">
          采集完成
        </div>
        <div v-if="batchStatus === 'failed'" class="current-stock" style="color:var(--up)">
          采集失败
        </div>
      </div>

      <!-- Batch error list -->
      <div v-if="batchErrors.length" class="collect-error-list">
        <div style="font-size:14px;font-weight:600;margin-bottom:8px;color:var(--text)">失败项目</div>
        <div v-for="(err, i) in batchErrors" :key="i" class="error-item">
          {{ err.keyword || err }}: {{ err.error || '' }}
        </div>
      </div>

      <div v-if="batchError" style="text-align:center;color:var(--up);margin-top:12px;font-size:14px">
        {{ batchError }}
      </div>
    </div>

    <!-- Tab 3: By Market -->
    <div v-show="activeTab === 'market'" class="invest-panel active">
      <!-- Shared incremental checkbox -->
      <label class="collect-checkbox" style="margin-bottom:20px">
        <input type="checkbox" v-model="marketIncremental" />
        增量采集
      </label>

      <div class="collect-market-grid">
        <div v-for="m in marketList" :key="m.code" class="collect-market-card">
          <div class="market-name">{{ m.name }}</div>
          <div class="market-prefix">代码前缀：{{ m.prefix }}</div>
          <button
            class="primary-btn"
            style="width:100%;padding:0;height:40px;font-size:14px"
            :disabled="marketRunning[m.code]"
            @click="handleMarketCollect(m)"
          >
            {{ marketRunning[m.code] ? '采集中...' : '采集' }}
          </button>
        </div>
      </div>

      <!-- Market progress -->
      <div v-if="marketTaskId" class="collect-progress">
        <div class="progress-bar-wrap">
          <div class="progress-bar-fill" :style="{ width: marketProgressPercent + '%' }"></div>
        </div>
        <div class="progress-text">
          <span>{{ marketCompleted }} / {{ marketTotal }}</span>
          <span>{{ marketProgressPercent }}%</span>
        </div>
        <div v-if="marketCurrentStock" class="current-stock">
          正在处理：{{ marketCurrentStock }}
        </div>
        <div v-if="marketStatus === 'complete'" class="current-stock" style="color:var(--down)">
          采集完成
        </div>
        <div v-if="marketStatus === 'failed'" class="current-stock" style="color:var(--up)">
          采集失败
        </div>
      </div>

      <!-- Market error list -->
      <div v-if="marketErrors.length" class="collect-error-list">
        <div style="font-size:14px;font-weight:600;margin-bottom:8px;color:var(--text)">失败项目</div>
        <div v-for="(err, i) in marketErrors" :key="i" class="error-item">
          {{ err.keyword || err }}: {{ err.error || '' }}
        </div>
      </div>

      <div v-if="marketError" style="text-align:center;color:var(--up);margin-top:12px;font-size:14px">
        {{ marketError }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import {
  collectSingle,
  getStockStatus,
  startBatchCollect,
  uploadBatchCSV,
  getCollectProgress,
  getMarkets,
  startMarketCollect,
} from '@/api'

// ── Tab state ──
const tabs = [
  { id: 'single', label: '单股采集' },
  { id: 'batch', label: '批量采集' },
  { id: 'market', label: '按市场采集' },
]
const activeTab = ref('single')

// ── Tab 1: Single Stock ──
const singleKeyword = ref('')
const singleLoading = ref(false)
const singleResult = ref(null)
const singleError = ref('')
const stockStatus = ref(null)

let statusTimer = null
watch(singleKeyword, (val) => {
  stockStatus.value = null
  clearTimeout(statusTimer)
  if (val && val.trim().length >= 2) {
    statusTimer = setTimeout(async () => {
      try {
        const res = await getStockStatus(val.trim())
        stockStatus.value = res
      } catch {
        stockStatus.value = null
      }
    }, 500)
  }
})

async function handleSingleCollect() {
  const kw = singleKeyword.value.trim()
  if (!kw) return
  singleLoading.value = true
  singleError.value = ''
  singleResult.value = null
  try {
    const res = await collectSingle(kw)
    singleResult.value = res
    // refresh status after collect
    try {
      stockStatus.value = await getStockStatus(kw)
    } catch { /* ignore */ }
  } catch (e) {
    singleError.value = e.response?.data?.message || e.message || '采集失败'
  } finally {
    singleLoading.value = false
  }
}

// ── Tab 2: Batch Collection ──
const batchMode = ref('text')
const batchText = ref('')
const csvFile = ref(null)
const fileInput = ref(null)
const batchIncremental = ref(true)
const batchLoading = ref(false)
const batchRunning = ref(false)
const batchTaskId = ref('')
const batchCompleted = ref(0)
const batchTotal = ref(0)
const batchCurrentStock = ref('')
const batchStatus = ref('')
const batchErrors = ref([])
const batchError = ref('')

let batchPollTimer = null

const batchProgressPercent = computed(() => {
  if (!batchTotal.value) return 0
  return Math.round((batchCompleted.value / batchTotal.value) * 100)
})

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileSelect(e) {
  const file = e.target.files?.[0]
  if (file) {
    csvFile.value = file
  }
}

function parseKeywords(text) {
  return text
    .split(/[\n,，;；\s]+/)
    .map(s => s.trim())
    .filter(Boolean)
}

async function handleBatchCollect() {
  batchError.value = ''
  batchErrors.value = []
  batchTaskId.value = ''
  batchCompleted.value = 0
  batchTotal.value = 0
  batchCurrentStock.value = ''
  batchStatus.value = ''

  batchLoading.value = true
  try {
    let res
    if (batchMode.value === 'csv' && csvFile.value) {
      res = await uploadBatchCSV(csvFile.value, batchIncremental.value)
    } else {
      const keywords = parseKeywords(batchText.value)
      if (!keywords.length) {
        batchError.value = '请输入至少一个股票代码'
        batchLoading.value = false
        return
      }
      res = await startBatchCollect(keywords, batchIncremental.value)
    }
    batchTaskId.value = res.taskId || res.id || ''
    batchTotal.value = res.total || 0
    batchRunning.value = true
    startBatchPolling()
  } catch (e) {
    batchError.value = e.response?.data?.message || e.message || '提交失败'
  } finally {
    batchLoading.value = false
  }
}

function startBatchPolling() {
  clearBatchPolling()
  batchPollTimer = setInterval(async () => {
    if (!batchTaskId.value) return
    try {
      const res = await getCollectProgress(batchTaskId.value)
      batchCompleted.value = res.completed ?? res.processed ?? 0
      batchTotal.value = res.total ?? batchTotal.value
      batchCurrentStock.value = res.currentStock || ''
      batchStatus.value = res.status || ''
      if (res.errors) {
        batchErrors.value = res.errors
      }
      if (res.status === 'complete' || res.status === 'failed') {
        clearBatchPolling()
        batchRunning.value = false
        batchCurrentStock.value = ''
      }
    } catch {
      // keep polling on transient errors
    }
  }, 2000)
}

function clearBatchPolling() {
  if (batchPollTimer) {
    clearInterval(batchPollTimer)
    batchPollTimer = null
  }
}

// ── Tab 3: By Market ──
const DEFAULT_MARKETS = [
  { code: 'all', name: '全市场', prefix: '全部' },
  { code: 'gem', name: '创业板', prefix: '30' },
  { code: 'star', name: '科创板', prefix: '68' },
  { code: 'sh_main', name: '上海主板', prefix: '60' },
  { code: 'sz_main', name: '深圳主板', prefix: '00' },
]

const marketList = ref([])
const marketIncremental = ref(true)
const marketRunning = ref({})
const marketTaskId = ref('')
const marketCompleted = ref(0)
const marketTotal = ref(0)
const marketCurrentStock = ref('')
const marketStatus = ref('')
const marketErrors = ref([])
const marketError = ref('')

let marketPollTimer = null

const marketProgressPercent = computed(() => {
  if (!marketTotal.value) return 0
  return Math.round((marketCompleted.value / marketTotal.value) * 100)
})

onMounted(async () => {
  try {
    const res = await getMarkets()
    const markets = Array.isArray(res) ? res : (res.markets || [])
    if (markets.length) {
      marketList.value = markets.map(m => ({
        code: m.id || m.code,
        name: m.name,
        prefix: m.codePrefix || m.prefix,
      }))
    } else {
      marketList.value = DEFAULT_MARKETS
    }
  } catch {
    marketList.value = DEFAULT_MARKETS
  }
})

async function handleMarketCollect(market) {
  marketError.value = ''
  marketErrors.value = []
  marketTaskId.value = ''
  marketCompleted.value = 0
  marketTotal.value = 0
  marketCurrentStock.value = ''
  marketStatus.value = ''

  marketRunning.value = { ...marketRunning.value, [market.code]: true }

  try {
    const res = await startMarketCollect(market.code, marketIncremental.value)
    marketTaskId.value = res.taskId || res.id || ''
    marketTotal.value = res.total || 0
    startMarketPolling()
  } catch (e) {
    marketError.value = e.response?.data?.message || e.message || '采集失败'
    marketRunning.value = { ...marketRunning.value, [market.code]: false }
  }
}

function startMarketPolling() {
  clearMarketPolling()
  marketPollTimer = setInterval(async () => {
    if (!marketTaskId.value) return
    try {
      const res = await getCollectProgress(marketTaskId.value)
      marketCompleted.value = res.completed ?? res.processed ?? 0
      marketTotal.value = res.total ?? marketTotal.value
      marketCurrentStock.value = res.currentStock || ''
      marketStatus.value = res.status || ''
      if (res.errors) {
        marketErrors.value = res.errors
      }
      if (res.status === 'complete' || res.status === 'failed') {
        clearMarketPolling()
        marketRunning.value = {}
        marketCurrentStock.value = ''
      }
    } catch {
      // keep polling on transient errors
    }
  }, 2000)
}

function clearMarketPolling() {
  if (marketPollTimer) {
    clearInterval(marketPollTimer)
    marketPollTimer = null
  }
}

// ── Cleanup ──
onBeforeUnmount(() => {
  clearBatchPolling()
  clearMarketPolling()
  clearTimeout(statusTimer)
})
</script>

<style scoped>
.invest-panel {
  display: block;
}
</style>
