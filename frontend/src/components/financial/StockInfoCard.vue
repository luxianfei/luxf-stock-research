<template>
  <div class="stock-info-bar">
    <div class="info-bar-line">
      <div class="info-bar-head">
        <span class="info-bar-title">{{ stockName }}&nbsp;&nbsp;{{ stockCode }}</span>
        <span class="info-badges">
          <span v-if="info.board" class="info-badge info-badge-board">{{ info.board }}</span>
          <span v-if="info.industry" class="info-badge info-badge-industry" :title="info.industry">
            {{ info.industry }}{{ info.extraIndustryCount > 0 ? '+' + info.extraIndustryCount : '' }}
          </span>
        </span>
      </div>
      <div class="info-kv-row">
        <div v-if="info.listDate" class="info-kv">
          <span class="info-kv-label">上市</span>
          <span class="info-kv-value">{{ info.listDate }} / {{ info.listYears }}年</span>
        </div>
        <InfoKv label="PE-TTM" :value="fmtDecimal(info.peTtm)" />
        <InfoKv label="PB" :value="fmtDecimal(info.pb)" />
        <InfoKv label="PS-TTM" :value="fmtDecimal(info.psTtm)" />
        <InfoKv label="当前市值" :value="fmtYi(info.currentMarketCapYi)" />
        <InfoKv v-if="info.latestNetMargin != null" label="净利率" :value="pctFmt(info.latestNetMargin)" />
        <InfoKv v-if="info.tenPsCandidate != null" label="10PS标的" :value="info.tenPsCandidate ? '是' : '否'" :tone="info.tenPsCandidate ? 'strong' : 'muted'" />
        <InfoKv v-if="info.tenPsCurrentToY1 != null" label="明年PS" :value="fmtDecimal(info.tenPsCurrentToY1) + '倍'" />
        <InfoKv v-if="info.tenPsFairMarketCapYi != null" label="合理市值" :value="fmtYi(info.tenPsFairMarketCapYi)" />
        <InfoKv v-if="info.tenPsValuationVerdict" label="估值" :value="info.tenPsValuationVerdict"
          :tone="info.tenPsValuationVerdict === '合理/低估' ? 'ok' : info.tenPsValuationVerdict === '不适用' ? 'muted' : 'warn'"
          :title="info.tenPsValuationDetail" />
      </div>
    </div>
    <div v-if="info.updatedAt" class="info-bar-foot">{{ info.updatedAt }}</div>
  </div>
</template>

<script setup>
import { pctFmt } from '@/utils/formatter'

const props = defineProps({
  info: { type: Object, required: true },
  stockName: String,
  stockCode: String,
})

function fmtDecimal(v) {
  if (v == null) return '--'
  const n = Number(v)
  return isFinite(n) ? n.toFixed(2) : '--'
}

function fmtYi(v) {
  if (v == null) return '--'
  const n = Number(v)
  return isFinite(n) ? n.toFixed(2) + '亿' : '--'
}
</script>

<script>
// Inline InfoKv component
export default {
  components: {
    InfoKv: {
      props: ['label', 'value', 'tone', 'title'],
      template: `
        <div class="info-kv">
          <span class="info-kv-label">{{ label }}</span>
          <span class="info-kv-value" :class="[value === '--' ? 'muted' : '', tone || '']" :title="title">{{ value }}</span>
        </div>
      `,
    },
  },
}
</script>
