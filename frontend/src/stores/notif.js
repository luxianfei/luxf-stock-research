import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNotifStore = defineStore('notif', () => {
  const items = ref([])
  const current = ref(0)

  async function fetchNotifications() {
    try {
      const [recap, analysis, bigyang, ai] = await Promise.allSettled([
        fetch('/api/market-recaps/badge').then(r => r.json()),
        fetch('/api/stock-analysis/list?limit=3').then(r => r.json()),
        fetch('/api/invest/big-yang/alerts').then(r => r.json()),
        fetch('/api/tech-ai/alerts').then(r => r.json()),
      ])

      const all = []

      if (recap.status === 'fulfilled' && recap.value?.latestId) {
        all.push({
          kind: 'recap',
          text: `${recap.value.latestTradeDate} 复盘已更新`,
          time: recap.value.latestTradeDate,
          href: '/market-recap',
        })
      }

      if (analysis.status === 'fulfilled' && analysis.value?.records) {
        for (const r of analysis.value.records) {
          all.push({
            kind: 'analysis',
            text: `${r.stockName} 已生成 · ${r.verdict || ''} · ${r.summaryOneLiner || ''}`,
            time: r.submittedAt,
            href: `/invest?analysis=${r.id}`,
          })
        }
      }

      if (bigyang.status === 'fulfilled' && Array.isArray(bigyang.value)) {
        for (const a of bigyang.value.slice(0, 3)) {
          all.push({
            kind: 'bigyang',
            text: `${a.stockCode} ${a.title || '大阳线告警'}`,
            time: a.triggerAt,
            href: '/invest',
          })
        }
      }

      items.value = all.sort((a, b) => new Date(b.time) - new Date(a.time)).slice(0, 8)
    } catch (e) {
      console.error('Failed to fetch notifications:', e)
    }
  }

  return { items, current, fetchNotifications }
})
