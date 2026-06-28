<template>
  <div>
    <!-- Board summary -->
    <div style="background:var(--base-gradient);border-radius:12px;padding:20px 24px;margin-bottom:20px;color:#fff">
      <div style="font-size:20px;font-weight:700;margin-bottom:4px">龙江投资 · 股票池</div>
      <div style="font-size:13px;opacity:0.85">
        价值景气投资法 · 增量市场，稀缺卡位 · 顺势而为
        <span style="margin-left:12px">{{ todayStr }}</span>
      </div>
      <div style="display:flex;gap:20px;margin-top:12px;font-size:14px">
        <span>合理 <b>{{ countByVal('合理') + countByVal('合理/低估') }}</b></span>
        <span>低估 <b>{{ countByVal('低估') }}</b></span>
        <span>泡沫 <b>{{ countByVal('泡沫') }}</b></span>
      </div>
    </div>

    <!-- Filters -->
    <div class="pool-filters">
      <button v-for="f in filters" :key="f.value" :class="{ active: currentFilter === f.value }" @click="currentFilter = f.value">
        {{ f.label }}
      </button>
      <input
        v-model="searchKeyword"
        placeholder="搜索：名称 / 拼音首字母 / 代码"
        style="margin-left:auto;padding:6px 12px;border:1px solid var(--border);border-radius:6px;font-size:13px;width:240px;outline:none"
      />
    </div>

    <!-- Add stock + actions -->
    <div style="display:flex;gap:8px;margin-bottom:16px">
      <input
        v-model="newKeyword"
        placeholder="输入股票名称或代码"
        style="flex:1;max-width:300px;padding:8px 12px;border:1px solid var(--border);border-radius:6px;font-size:14px;outline:none"
        @keydown.enter="handleAdd"
      />
      <button class="primary-btn" style="height:38px;font-size:14px;padding:0 20px" @click="handleAdd">
        + 加入股票池
      </button>
      <button class="primary-btn" style="height:38px;font-size:14px;padding:0 20px;background:var(--text-muted)" :disabled="refreshing" @click="handleRefresh">
        {{ refreshing ? '刷新中...' : '刷新数据' }}
      </button>
    </div>

    <!-- Table -->
    <div v-if="pool.length" class="table-scroll">
      <table class="stock-table">
        <thead>
          <tr>
            <th class="first-col">公司简称</th>
            <th>2023营收(亿)</th>
            <th>2024营收(亿)</th>
            <th>2025营收(亿)</th>
            <th style="background:#ea580c">2026预测(亿)</th>
            <th>2027预测(亿)</th>
            <th>2028预测(亿)</th>
            <th>Q1毛利率(%)</th>
            <th>Q1净利率(%)</th>
            <th>Q1营收增速(%)</th>
            <th>近5年最低PS</th>
            <th style="background:#ea580c">当前市值(亿)</th>
            <th>今年涨幅(%)</th>
            <th>估值情况</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredPool" :key="item.id">
            <td class="metric-name">
              {{ item.stockName }}
              <br/><span style="font-size:11px;color:var(--text-muted)">{{ item.stockCode }}</span>
            </td>
            <td><EditableNum :value="item.revenue2023" @save="v => patchField(item.id, 'revenue2023', v)" /></td>
            <td><EditableNum :value="item.revenue2024" @save="v => patchField(item.id, 'revenue2024', v)" /></td>
            <td><EditableNum :value="item.revenue2025" @save="v => patchField(item.id, 'revenue2025', v)" /></td>
            <td style="background:#fff7ed"><EditableNum :value="item.revenueForecastY0" @save="v => patchField(item.id, 'revenueForecastY0', v)" /></td>
            <td><EditableNum :value="item.revenueForecastY1" @save="v => patchField(item.id, 'revenueForecastY1', v)" /></td>
            <td><EditableNum :value="item.revenueForecastY2" @save="v => patchField(item.id, 'revenueForecastY2', v)" /></td>
            <td><EditableNum :value="item.q1GrossMargin" @save="v => patchField(item.id, 'q1GrossMargin', v)" /></td>
            <td><EditableNum :value="item.q1NetMargin" @save="v => patchField(item.id, 'q1NetMargin', v)" /></td>
            <td :class="growthClass(item.q1RevenueGrowth)">
              <EditableNum :value="item.q1RevenueGrowth" @save="v => patchField(item.id, 'q1RevenueGrowth', v)" />
            </td>
            <td><EditableNum :value="item.minPs5y" @save="v => patchField(item.id, 'minPs5y', v)" /></td>
            <td style="background:#fff7ed">{{ fmtNum(item.currentMarketCap) }}</td>
            <td :class="colorClass(item.ytdGainPct)">{{ fmtPct(item.ytdGainPct) }}</td>
            <td>
              <span :style="valuationStyle(item.valuationRange)">{{ item.valuationRange || '--' }}</span>
            </td>
            <td>
              <button style="background:none;border:none;color:var(--base);cursor:pointer;font-size:12px;margin-right:4px" @click="showDetail(item)">详情</button>
              <button style="background:none;border:none;color:var(--accent);cursor:pointer;font-size:12px" @click="handleRemove(item.id)">移除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p style="text-align:center;font-size:12px;color:var(--text-muted);margin-top:8px">
        共 {{ pool.length }} 只，当前显示 {{ filteredPool.length }} 只
      </p>
    </div>
    <div v-else style="text-align:center;padding:40px;color:var(--text-muted)">
      股票池为空，请添加股票
    </div>

    <!-- Distribution Charts -->
    <div v-if="filteredPool.length > 0" style="margin-top:24px">
      <h3 style="font-size:16px;font-weight:700;margin-bottom:12px">Q1 营收增速分布</h3>
      <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:end;margin-bottom:24px">
        <div v-for="item in chartItems" :key="'rev-'+item.id" style="text-align:center;min-width:50px">
          <div :style="barStyle(item.q1RevenueGrowth, 'rev')" :title="fmtPct(item.q1RevenueGrowth)">
            <span style="font-size:10px">{{ item.q1RevenueGrowth != null ? Number(item.q1RevenueGrowth).toFixed(1) : '--' }}</span>
          </div>
          <div style="font-size:10px;color:var(--text-muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:60px">{{ item.stockName }}</div>
        </div>
      </div>

      <h3 style="font-size:16px;font-weight:700;margin-bottom:12px">Q1 净利率分布</h3>
      <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:end">
        <div v-for="item in chartItems" :key="'nm-'+item.id" style="text-align:center;min-width:50px">
          <div :style="barStyle(item.q1NetMargin, 'nm')" :title="fmtPct(item.q1NetMargin)">
            <span style="font-size:10px">{{ item.q1NetMargin != null ? Number(item.q1NetMargin).toFixed(1) : '--' }}</span>
          </div>
          <div style="font-size:10px;color:var(--text-muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:60px">{{ item.stockName }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { fetchStockPool, addToPool, removeFromPool, refreshPool, patchPoolField } from '@/api'
import { colorClass } from '@/utils/formatter'

const pool = ref([])
const currentFilter = ref('all')
const searchKeyword = ref('')
const newKeyword = ref('')
const refreshing = ref(false)

const todayStr = new Date().toLocaleDateString('zh-CN')

const filters = [
  { label: '全部', value: 'all' },
  { label: '合理', value: 'fair' },
  { label: '低估', value: 'low' },
  { label: '高估', value: 'bubble' },
]

const filteredPool = computed(() => {
  let items = pool.value
  if (currentFilter.value === 'fair') {
    items = items.filter(i => i.valuationRange === '合理' || i.valuationRange === '合理/低估')
  } else if (currentFilter.value === 'low') {
    items = items.filter(i => i.valuationRange === '低估')
  } else if (currentFilter.value === 'bubble') {
    items = items.filter(i => i.valuationRange === '泡沫')
  }
  const kw = searchKeyword.value.trim().toLowerCase()
  if (kw) {
    items = items.filter(i =>
      (i.stockName || '').toLowerCase().includes(kw) ||
      (i.stockCode || '').toLowerCase().includes(kw)
    )
  }
  return items
})

const chartItems = computed(() => filteredPool.value.slice(0, 16))

function countByVal(v) { return pool.value.filter(i => i.valuationRange === v).length }

async function loadPool() {
  try { pool.value = await fetchStockPool() } catch (e) { console.error(e) }
}

async function handleAdd() {
  const kw = newKeyword.value.trim()
  if (!kw) return
  try {
    await addToPool({ keyword: kw, poolType: 'tech_vc', status: 'watching' })
    newKeyword.value = ''
    await loadPool()
  } catch (e) { alert(e.response?.data?.detail || e.message || '添加失败') }
}

async function handleRemove(id) {
  if (!confirm('确认移除该股票？')) return
  try { await removeFromPool(id); await loadPool() } catch (e) { alert('移除失败') }
}

async function handleRefresh() {
  refreshing.value = true
  try {
    const result = await refreshPool()
    await loadPool()
    alert('刷新完成：' + result.refreshed + ' 只已更新' + (result.errors ? '，' + result.errors + ' 个错误' : ''))
  } catch (e) { alert('刷新失败: ' + (e.response?.data?.detail || e.message)) }
  finally { refreshing.value = false }
}

async function patchField(id, field, value) {
  try {
    await patchPoolField(id, field, value)
    await loadPool()
  } catch (e) { alert('保存失败: ' + (e.response?.data?.detail || e.message)) }
}

function showDetail(item) {
  const lines = [
    '股票: ' + item.stockName + ' (' + item.stockCode + ')',
    '类型: ' + (item.poolTypeLabel || '--'),
    '状态: ' + (item.statusLabel || item.status),
    '最新价: ' + (item.latestPrice || '--'),
    '估值: ' + (item.valuationRange || '--'),
  ]
  if (item.memo) lines.push('备注: ' + item.memo)
  alert(lines.join('\n'))
}

function growthClass(v) {
  if (v == null) return ''
  const n = Number(v)
  if (n >= 100) return 'growth-surge'
  if (n >= 30) return 'growth-strong'
  if (n >= 0) return 'growth-warm'
  return 'growth-calm'
}

function barStyle(v, type) {
  if (v == null) return { width: '50px', height: '4px', background: '#e2e8f0', borderRadius: '2px' }
  const n = Math.abs(Number(v))
  const h = Math.max(4, Math.min(80, n * 1.2))
  const color = type === 'rev'
    ? (Number(v) >= 0 ? '#2563eb' : '#dc2626')
    : (Number(v) >= 0 ? '#16a34a' : '#dc2626')
  return { width: '50px', height: h + 'px', background: color, borderRadius: '2px', display: 'flex', alignItems: 'end', justifyContent: 'center', color: '#fff', paddingBottom: '2px' }
}

function fmtPct(v) { return v == null ? '--' : Number(v).toFixed(1) + '%' }
function fmtNum(v) { return v == null ? '--' : Number(v).toFixed(2) }
function valuationStyle(v) {
  if (v === '低估') return { color: '#16a34a', fontWeight: '600' }
  if (v === '泡沫') return { color: '#dc2626', fontWeight: '600' }
  if (v === '合理' || v === '合理/低估') return { color: '#2563eb', fontWeight: '600' }
  return {}
}

// Inline EditableNum component
const EditableNum = {
  props: ['value'],
  emits: ['save'],
  setup(props, { emit }) {
    const editing = ref(false)
    const draft = ref(null)
    function startEdit() { editing.value = true; draft.value = props.value ?? '' }
    function commit() {
      editing.value = false
      const v = draft.value === '' || draft.value == null ? null : Number(draft.value)
      if (v !== props.value) emit('save', v)
    }
    function cancel() { editing.value = false }
    function onKey(e) {
      if (e.key === 'Enter') commit()
      if (e.key === 'Escape') cancel()
    }
    return () => editing.value
      ? h('input', {
          type: 'number', step: '0.01', value: draft.value,
          style: 'width:70px;padding:2px 4px;border:1px solid var(--base);border-radius:3px;font-size:13px;text-align:center;outline:none',
          onInput: e => draft.value = e.target.value,
          onBlur: commit, onKeydown: onKey,
          onVnodeMounted: vn => vn.el && vn.el.focus(),
        })
      : h('span', {
          style: 'cursor:pointer;border-bottom:1px dashed transparent',
          onClick: startEdit,
          title: '点击编辑',
        }, props.value != null ? Number(props.value).toFixed(1) : '--')
  }
}

onMounted(loadPool)
</script>

<style scoped>
.growth-surge { color: #dc2626; font-weight: 700; }
.growth-strong { color: #ea580c; font-weight: 600; }
.growth-warm { color: var(--text); }
.growth-calm { color: #16a34a; }
</style>