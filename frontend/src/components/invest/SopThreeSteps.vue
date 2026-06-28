<template>
  <div>
    <!-- Step 1: Select Track -->
    <div class="sop-step">
      <div class="sop-step-title">Step 1 · 10 分钟 — 选赛道：找"增量市场"</div>
      <div style="font-size:14px;color:var(--text-mid);line-height:1.8">
        <p><b>判断要点：</b></p>
        <p>• 未来 3-5 年规模能否翻倍（增量驱动 vs 存量博弈）</p>
        <p>• 是否由技术进步推动财富增长（AI / 新能源 / 半导体 / 创新药）</p>
        <p>• 是否获得国家政策长期支持</p>
      </div>
    </div>

    <!-- Step 2: Select Company (5A Scorecard) -->
    <div class="sop-step">
      <div class="sop-step-title">Step 2 · 10 分钟 — 选公司：找"稀缺卡位"</div>
      <p style="font-size:14px;color:var(--text-mid);margin-bottom:16px">
        5A 模型评分卡：为每个维度打分（1-5），自动算出星级。
      </p>

      <div style="margin-bottom:12px">
        <input
          v-model="sopKeyword"
          placeholder="股票名称或代码"
          style="padding:8px 12px;border:1px solid var(--border);border-radius:6px;font-size:14px;width:240px;outline:none"
        />
      </div>

      <!-- 5A Dimensions -->
      <div v-for="dim in dimensions" :key="dim.key" class="sop-5a-dim">
        <div class="sop-5a-dim-head">
          <span class="sop-5a-dim-title">{{ dim.title }}</span>
          <span class="sop-5a-dim-score">{{ scores[dim.key] }}</span>
        </div>
        <div class="sop-5a-dim-hint">{{ dim.hint }}</div>
        <div class="sop-5a-dots">
          <button
            v-for="n in 5"
            :key="n"
            class="sop-5a-dot"
            :class="{ active: scores[dim.key] >= n }"
            @click="setScore(dim.key, n)"
          >
            {{ n }}
          </button>
        </div>
      </div>

      <!-- Summary -->
      <div class="sop-5a-summary">
        <div style="font-size:14px;color:var(--text-muted);margin-bottom:4px">
          当前得分：<b>{{ totalScore }}</b> / 25
        </div>
        <div class="sop-5a-stars">{{ stars }}</div>
        <div class="sop-5a-verdict" :class="verdictClass">{{ verdictText }}</div>
        <button
          class="primary-btn"
          style="height:36px;font-size:13px;padding:0 20px;margin-top:12px"
          :disabled="!sopKeyword || totalScore === 0"
          @click="saveToPool"
        >
          加入股票池
        </button>
      </div>
    </div>

    <!-- Step 3: Verify (Digital Checkup) -->
    <div class="sop-step">
      <div class="sop-step-title">Step 3 · 10 分钟 — 验真伪：看"漂亮数字"</div>
      <p style="font-size:14px;color:var(--text-mid);margin-bottom:16px">
        三条验证线：毛利率（稳定或提升）、营收 YoY（持续两位数）、扣非净利润 YoY（增速 > 营收增速）
      </p>

      <div style="display:flex;gap:8px;margin-bottom:16px">
        <input
          v-model="checkupKeyword"
          placeholder="输入股票代码"
          style="flex:1;max-width:300px;padding:8px 12px;border:1px solid var(--border);border-radius:6px;font-size:14px;outline:none"
          @keydown.enter="runCheckup"
        />
        <button class="primary-btn" style="height:38px;font-size:14px;padding:0 20px" :disabled="checking" @click="runCheckup">
          {{ checking ? '体检中...' : '立即体检' }}
        </button>
      </div>

      <!-- Checkup Result -->
      <div v-if="checkupResult">
        <div v-if="!checkupResult.matched" style="color:var(--text-muted);padding:16px;text-align:center">
          {{ checkupResult.message || '未找到该股票' }}
        </div>
        <div v-else>
          <div class="sop-checkup-header">
            <div class="sop-checkup-stock">
              {{ checkupResult.stockName }}
              <span class="sop-checkup-code">{{ checkupResult.stockCode }}</span>
            </div>
            <span class="sop-checkup-overall" :class="'sop-verdict-' + checkupResult.overallVerdict">
              {{ verdictLabel(checkupResult.overallVerdict) }} · {{ checkupResult.overallSummary }}
            </span>
          </div>
          <div class="sop-checkup-grid">
            <CheckupCard v-if="checkupResult.grossMargin" :metric="checkupResult.grossMargin" />
            <CheckupCard v-if="checkupResult.revenueYoy" :metric="checkupResult.revenueYoy" />
            <CheckupCard v-if="checkupResult.profitYoy" :metric="checkupResult.profitYoy" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { addToPool, fetchSopCheckup } from '@/api'

const dimensions = [
  { key: 'a1', title: 'A1 · 行业地位', hint: '5分=赛道唯一龙头；3分=前三；1分=跟随者' },
  { key: 'a2', title: 'A2 · 业务唯一性', hint: '5分=不可替代/独家牌照；3分=有差异；1分=同质化' },
  { key: 'a3', title: 'A3 · 客户粘性', hint: '5分=长合同/高切换成本；3分=中等；1分=低粘性' },
  { key: 'a4', title: 'A4 · 护城河', hint: '5分=专利/工艺/品牌强壁垒；3分=部分壁垒；1分=易复制' },
  { key: 'a5', title: 'A5 · 替代难度', hint: '5分=对手追赶需3年+；3分=1-2年；1分=随时被替代' },
]

const scores = reactive({ a1: 0, a2: 0, a3: 0, a4: 0, a5: 0 })
const sopKeyword = ref('')
const checkupKeyword = ref('')
const checking = ref(false)
const checkupResult = ref(null)

const totalScore = computed(() => Object.values(scores).reduce((a, b) => a + b, 0))

const stars = computed(() => {
  const t = totalScore.value
  if (t >= 22) return '★★★★★'
  if (t >= 17) return '★★★★☆'
  if (t >= 12) return '★★★☆☆'
  if (t > 0) return '★★☆☆☆'
  return '☆☆☆☆☆'
})

const verdictText = computed(() => {
  const t = totalScore.value
  if (t >= 22) return '极为稀缺，重点跟踪'
  if (t >= 17) return '稀缺，可纳入候选'
  if (t >= 12) return '一般，需对比同行'
  if (t > 0) return '稀缺性不足，建议放弃'
  return '请先为各维度打分'
})

const verdictClass = computed(() => {
  const t = totalScore.value
  if (t >= 17) return 'pass'
  if (t >= 12) return 'warn'
  if (t > 0) return 'fail'
  return ''
})

function setScore(key, val) {
  scores[key] = val
}

async function saveToPool() {
  const kw = sopKeyword.value.trim()
  if (!kw || totalScore.value === 0) return
  const memo = `5A 稀缺度评分：${totalScore.value}/25\n` +
    dimensions.map(d => `${d.title}：${scores[d.key]}/5`).join('\n')
  try {
    await addToPool({
      keyword: kw,
      poolType: totalScore.value >= 17 ? 'tech_vc' : 'quality',
      status: 'watching',
      memo,
    })
    alert(`已加入股票池：${kw}（${totalScore.value}/25）`)
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

async function runCheckup() {
  const kw = checkupKeyword.value.trim()
  if (!kw) return
  checking.value = true
  checkupResult.value = null
  try {
    checkupResult.value = await fetchSopCheckup(kw)
  } catch (e) {
    checkupResult.value = { matched: false, message: '请求失败: ' + (e.message || '') }
  } finally {
    checking.value = false
  }
}

function verdictLabel(v) {
  if (v === 'pass') return '✓ PASS'
  if (v === 'warn') return '⚠ WARN'
  if (v === 'fail') return '✗ FAIL'
  return '—'
}
</script>

<script>
export default {
  components: {
    CheckupCard: {
      props: ['metric'],
      computed: {
        /** Build SVG sparkline data from metric.series (reversed so oldest is left) */
        sparkData() {
          const raw = this.metric.series || []
          // series comes newest-first; reverse for chronological display
          const items = raw.filter(s => s.value != null).slice().reverse()
          if (!items.length) return null

          const W = 220, H = 64, padL = 4, padR = 4, padT = 6, padB = 18
          const plotW = W - padL - padR
          const plotH = H - padT - padB
          const n = items.length

          const vals = items.map(s => s.value)
          const minV = Math.min(0, ...vals)
          const maxV = Math.max(0, ...vals)
          const range = maxV - minV || 1

          const barW = Math.min(18, (plotW / n) * 0.6)
          const gap = (plotW - barW * n) / (n + 1)

          const bars = []
          const points = []
          const zeroY = padT + plotH * (maxV / range)

          items.forEach((item, i) => {
            const x = padL + gap + i * (barW + gap)
            const v = item.value
            const normY = padT + plotH * ((maxV - v) / range)
            const bx = x
            const by = v >= 0 ? normY : zeroY
            const bh = Math.abs(normY - zeroY) || 1

            // Bar color
            let fill = '#94a3b8'
            if (v >= 30) fill = '#16a34a'
            else if (v >= 15) fill = '#22c55e'
            else if (v >= 5) fill = '#86efac'
            else if (v >= 0) fill = '#bbf7d0'
            else if (v >= -5) fill = '#fca5a5'
            else fill = '#dc2626'

            bars.push({ x: bx, y: by, w: barW, h: bh, fill })
            points.push({ x: bx + barW / 2, y: normY })
          })

          // Line path
          let pathD = ''
          points.forEach((p, i) => {
            pathD += (i === 0 ? 'M' : 'L') + p.x.toFixed(1) + ',' + p.y.toFixed(1)
          })

          // Quarter labels (show first, middle, last)
          const labels = []
          if (n >= 1) labels.push({ x: bars[0].x + barW / 2, text: items[0].quarter })
          if (n >= 3) {
            const mid = Math.floor(n / 2)
            labels.push({ x: bars[mid].x + barW / 2, text: items[mid].quarter })
          }
          if (n >= 2) labels.push({ x: bars[n - 1].x + barW / 2, text: items[n - 1].quarter })

          return {
            W, H, bars, pathD, labels,
            zeroY: (minV < 0 && maxV > 0) ? zeroY : null,
            padB,
          }
        },
      },
      template: `
        <div class="sop-checkup-card">
          <div class="sop-checkup-card-head">
            <span class="sop-checkup-label">{{ metric.label }}</span>
            <span class="sop-checkup-verdict" :class="'sop-verdict-' + metric.verdict">
              {{ metric.verdict === 'pass' ? '✓ PASS' : metric.verdict === 'warn' ? '⚠ WARN' : '✗ FAIL' }}
            </span>
          </div>
          <div class="sop-checkup-latest">
            最新：<b>{{ metric.latest != null ? (metric.latest >= 0 ? '+' : '') + Number(metric.latest).toFixed(1) + metric.unit : '—' }}</b>
          </div>

          <!-- SVG Sparkline -->
          <svg v-if="sparkData" :viewBox="'0 0 ' + sparkData.W + ' ' + sparkData.H" class="spark-svg" preserveAspectRatio="xMidYMid meet">
            <!-- Zero line -->
            <line v-if="sparkData.zeroY" :x1="0" :y1="sparkData.zeroY" :x2="sparkData.W" :y2="sparkData.zeroY" stroke="#cbd5e1" stroke-width="0.5" stroke-dasharray="3,2" />
            <!-- Bars -->
            <rect v-for="(b, i) in sparkData.bars" :key="'b'+i" :x="b.x" :y="b.y" :width="b.w" :height="b.h" :fill="b.fill" rx="2" />
            <!-- Connecting line -->
            <path :d="sparkData.pathD" fill="none" stroke="#3b82f6" stroke-width="1.5" stroke-linejoin="round" />
            <!-- Quarter labels -->
            <text v-for="(l, i) in sparkData.labels" :key="'l'+i" :x="l.x" :y="sparkData.H - 2" text-anchor="middle" class="spark-label">{{ l.text }}</text>
          </svg>

          <div class="sop-checkup-tip">{{ metric.tip }}</div>
        </div>
      `,
    },
  },
}
</script>
