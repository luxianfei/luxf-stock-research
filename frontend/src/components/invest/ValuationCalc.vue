<template>
  <div>
    <!-- PE Matching Method -->
    <div class="valuation-calc">
      <h3>质量优选 · PE 匹配法</h3>
      <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">
        合理PE ≈ 预期年化复合增长率 × 2（如增长率15% → 合理PE 30倍）
      </p>
      <div class="valuation-inputs">
        <label>
          当前 PE（倍）
          <input v-model.number="pe" type="number" step="0.1" placeholder="当前PE" />
        </label>
        <label>
          预期未来10年年化复合增长率（%）
          <input v-model.number="growthRate" type="number" step="0.1" placeholder="增长率%" />
        </label>
        <button class="primary-btn" style="height:38px;font-size:14px;padding:0 20px" @click="calcPe">计算</button>
      </div>
      <div v-if="peResult" class="valuation-result">
        <p>合理 PE：<b>{{ fairPe }}</b> 倍 | 当前 PE：<b>{{ pe }}</b> 倍</p>
        <p :style="{ color: peResult.color }">{{ peResult.text }}</p>
      </div>
    </div>

    <!-- 10PS Method -->
    <div class="valuation-calc">
      <h3>科技风投 · 10倍 PS 法</h3>
      <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">
        合理市值 = 预测营收 × 10（适用于净利率接近25%的高科技公司）
      </p>
      <div class="valuation-inputs">
        <label>
          当前市值（亿元）
          <input v-model.number="marketCap" type="number" step="0.1" placeholder="当前市值" />
        </label>
        <label>
          今年预测营收（亿元）
          <input v-model.number="revenueY0" type="number" step="0.1" placeholder="今年营收" />
        </label>
        <label>
          明年预测营收（亿元，选填）
          <input v-model.number="revenueY1" type="number" step="0.1" placeholder="明年营收" />
        </label>
        <label>
          后年预测营收（亿元，选填）
          <input v-model.number="revenueY2" type="number" step="0.1" placeholder="后年营收" />
        </label>
        <button class="primary-btn" style="height:38px;font-size:14px;padding:0 20px" @click="calcPs">计算</button>
      </div>
      <div v-if="psResult" class="valuation-result">
        <p v-if="fairCapY0">今年 10PS 合理市值：<b>{{ fairCapY0 }}</b> 亿</p>
        <p v-if="fairCapY1">明年 10PS 合理市值：<b>{{ fairCapY1 }}</b> 亿</p>
        <p v-if="fairCapY2">后年 10PS 合理市值：<b>{{ fairCapY2 }}</b> 亿</p>
        <p :style="{ color: psResult.color }">{{ psResult.text }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// PE method
const pe = ref(null)
const growthRate = ref(null)
const peResult = ref(null)

const fairPe = computed(() => growthRate.value ? (growthRate.value * 2).toFixed(1) : '--')

function calcPe() {
  if (!pe.value || !growthRate.value) {
    peResult.value = { text: '请输入 PE 和增长率', color: '#92400e' }
    return
  }
  const fair = growthRate.value * 2
  const ratio = pe.value / fair
  if (ratio <= 0.8) {
    peResult.value = { text: `当前 PE ${pe.value} 低于合理 PE ${fair.toFixed(1)}，可能被低估`, color: '#16a34a' }
  } else if (ratio <= 1.2) {
    peResult.value = { text: `当前 PE ${pe.value} 接近合理 PE ${fair.toFixed(1)}，估值合理`, color: '#2563eb' }
  } else {
    peResult.value = { text: `当前 PE ${pe.value} 高于合理 PE ${fair.toFixed(1)}，可能被高估`, color: '#dc2626' }
  }
}

// PS method
const marketCap = ref(null)
const revenueY0 = ref(null)
const revenueY1 = ref(null)
const revenueY2 = ref(null)
const psResult = ref(null)
const fairCapY0 = ref(null)
const fairCapY1 = ref(null)
const fairCapY2 = ref(null)

function calcPs() {
  fairCapY0.value = revenueY0.value ? (revenueY0.value * 10).toFixed(1) : null
  fairCapY1.value = revenueY1.value ? (revenueY1.value * 10).toFixed(1) : null
  fairCapY2.value = revenueY2.value ? (revenueY2.value * 10).toFixed(1) : null

  if (!marketCap.value) {
    psResult.value = { text: '请输入当前市值', color: '#92400e' }
    return
  }

  // Reference site logic: cap < Y1*10 => 低估; cap > Y2*10 => 泡沫; else => 合理
  const y1Fair = revenueY1.value ? revenueY1.value * 10 : (revenueY0.value ? revenueY0.value * 10 : null)
  const y2Fair = revenueY2.value ? revenueY2.value * 10 : null

  if (!y1Fair) {
    psResult.value = { text: '请至少输入今年或明年预测营收', color: '#92400e' }
    return
  }

  const ratio = marketCap.value / y1Fair
  if (y2Fair && marketCap.value > y2Fair) {
    const overRatio = (marketCap.value / y2Fair * 100).toFixed(0)
    psResult.value = { text: `当前市值 ${marketCap.value}亿 超过后年 10PS 合理市值 ${fairCapY2.value}亿 的 ${overRatio}%，需警惕泡沫`, color: '#dc2626' }
  } else if (marketCap.value < y1Fair) {
    psResult.value = { text: `当前市值 ${marketCap.value}亿 低于明年 10PS 合理市值 ${fairCapY1.value || fairCapY0.value}亿，可能被低估`, color: '#16a34a' }
  } else {
    psResult.value = { text: `当前市值 ${marketCap.value}亿 处于合理区间（明年10PS ${fairCapY1.value || fairCapY0.value}亿）`, color: '#2563eb' }
  }
}
</script>
