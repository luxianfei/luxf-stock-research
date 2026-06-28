<template>
  <div class="skin-switch" ref="rootEl">
    <button class="skin-toggle" @click="menuOpen = !menuOpen">
      <span class="dot" :style="{ background: currentDotColor }"></span>
      <span class="label">{{ currentLabel }}</span>
    </button>
    <ul v-show="menuOpen" class="skin-menu">
      <li
        v-for="s in skins"
        :key="s.key"
        :class="{ active: skinStore.currentSkin === s.key }"
        @click="setSkin(s.key)"
      >
        <span class="dot" :style="{ background: s.color }"></span>
        {{ s.label }}
        <span v-if="skinStore.currentSkin === s.key" class="check">✓</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSkinStore } from '@/stores/skin'

const skinStore = useSkinStore()
const menuOpen = ref(false)
const rootEl = ref(null)

const skins = [
  { key: 'tech', label: '科技蓝', color: '#2563eb' },
  { key: 'bull', label: '牛市红', color: '#dc2626' },
  { key: 'gold', label: '土豪金', color: '#b8860b' },
]

const currentSkinObj = computed(() => skins.find(s => s.key === skinStore.currentSkin) || skins[0])
const currentLabel = computed(() => currentSkinObj.value.label)
const currentDotColor = computed(() => currentSkinObj.value.color)

function setSkin(skin) {
  skinStore.setSkin(skin)
  menuOpen.value = false
}

function onClickOutside(e) {
  if (rootEl.value && !rootEl.value.contains(e.target)) {
    menuOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>
