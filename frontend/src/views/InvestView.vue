<template>
  <div>
    <h1 class="page-title" style="text-align:center;font-size:32px;font-weight:700;letter-spacing:2px;margin:8px 0 28px">
      龙江投资
    </h1>
    <p style="text-align:center;color:var(--text-muted);margin-bottom:24px">
      价值景气投资法 · 增量市场，稀缺卡位 · 顺势而为
    </p>

    <!-- Tabs -->
    <div class="invest-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="invest-tab"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
        <span v-if="tab.id === 'big-yang' && bigYangSummary.unreadAlertCount > 0"
              style="background:var(--accent);color:#fff;border-radius:10px;padding:1px 6px;font-size:11px;margin-left:4px">
          {{ bigYangSummary.unreadAlertCount }}
        </span>
      </button>
    </div>

    <!-- Panel: Stock Pool -->
    <div v-show="activeTab === 'pool'" class="invest-panel active">
      <StockPool />
    </div>

    <!-- Panel: Big Yang -->
    <div v-show="activeTab === 'big-yang'" class="invest-panel active">
      <BigYangPanel :summary="bigYangSummary" @refresh="loadBigYang" />
    </div>

    <!-- Panel: Valuation Calculator -->
    <div v-show="activeTab === 'valuation'" class="invest-panel active">
      <ValuationCalc />
    </div>

    <!-- Panel: Practical Select -->
    <div v-show="activeTab === 'practical'" class="invest-panel active">
      <PracticalSelect />
    </div>

    <!-- Panel: SOP -->
    <div v-show="activeTab === 'sop'" class="invest-panel active">
      <SopThreeSteps />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchBigYangSummary } from '@/api'
import StockPool from '@/components/invest/StockPool.vue'
import BigYangPanel from '@/components/invest/BigYangPanel.vue'
import ValuationCalc from '@/components/invest/ValuationCalc.vue'
import PracticalSelect from '@/components/invest/PracticalSelect.vue'
import SopThreeSteps from '@/components/invest/SopThreeSteps.vue'

const tabs = [
  { id: 'pool', label: '股票池' },
  { id: 'big-yang', label: '大阳线战法' },
  { id: 'valuation', label: '估值计算器' },
  { id: 'practical', label: '🎯 实战选股' },
  { id: 'sop', label: '实战选股SOP' },
]

const activeTab = ref('pool')
const bigYangSummary = ref({
  unreadAlertCount: 0,
  watchingCount: 0,
  triggeredCount: 0,
  expiredCount: 0,
  todayNewWatchingCount: 0,
  todayTriggeredCount: 0,
})

async function loadBigYang() {
  try {
    bigYangSummary.value = await fetchBigYangSummary()
  } catch (e) {
    console.error(e)
  }
}

onMounted(loadBigYang)
</script>
