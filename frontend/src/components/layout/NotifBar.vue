<template>
  <section class="notif-bar" v-if="notifStore.items.length > 0" @mouseenter="paused = true" @mouseleave="paused = false">
    <span class="notif-bar-label">通知</span>
    <div class="notif-bar-viewport">
      <ul class="notif-bar-list">
        <li
          v-for="(item, idx) in notifStore.items"
          :key="idx"
          class="notif-item"
          :class="{ active: idx === notifStore.current }"
        >
          <span class="notif-tag" :class="'tag-' + item.kind">{{ tagLabel(item.kind) }}</span>
          <span class="notif-text" v-html="linkify(item.text)"></span>
          <span class="notif-time">{{ formatTime(item.time) }}</span>
        </li>
      </ul>
    </div>
    <div class="notif-dots" v-if="notifStore.items.length > 1">
      <button
        v-for="(_, idx) in notifStore.items"
        :key="idx"
        class="notif-dot"
        :class="{ active: idx === notifStore.current }"
        @click="notifStore.current = idx"
      />
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useNotifStore } from '@/stores/notif'

const notifStore = useNotifStore()
const paused = ref(false)

let timer = null

function tagLabel(kind) {
  const map = { recap: '每日复盘', analysis: '个股分析', bigyang: '大阳线', ai: 'AI监控' }
  return map[kind] || '通知'
}

/** Auto-linkify URLs in notification text */
function linkify(text) {
  if (!text) return ''
  return text.replace(
    /(https?:\/\/[^\s<]+)/g,
    '<a href="$1" target="_blank" rel="noopener" style="color:var(--base);text-decoration:underline">$1</a>'
  )
}

/** Format timestamp to relative time: 刚刚 / X分钟前 / HH:MM / MM-DD */
function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diffMs = now - d
  if (isNaN(d.getTime())) return ts

  if (diffMs < 60000) return '刚刚'
  if (diffMs < 3600000) return Math.floor(diffMs / 60000) + ' 分钟前'
  if (diffMs < 86400000) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

onMounted(async () => {
  await notifStore.fetchNotifications()
  timer = setInterval(() => {
    if (!paused.value && notifStore.items.length > 1) {
      notifStore.current = (notifStore.current + 1) % notifStore.items.length
    }
  }, 4000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
