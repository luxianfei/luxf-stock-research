import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useSkinStore = defineStore('skin', () => {
  const STORAGE_KEY = 'gp.skin'
  const VALID_SKINS = ['tech', 'bull', 'gold']

  const saved = localStorage.getItem(STORAGE_KEY)
  const currentSkin = ref(VALID_SKINS.includes(saved) ? saved : 'tech')

  function setSkin(skin) {
    if (VALID_SKINS.includes(skin)) {
      currentSkin.value = skin
      localStorage.setItem(STORAGE_KEY, skin)
      document.dispatchEvent(new CustomEvent('skin:changed', { detail: { skin } }))
    }
  }

  function toggleSkin() {
    const idx = VALID_SKINS.indexOf(currentSkin.value)
    const next = VALID_SKINS[(idx + 1) % VALID_SKINS.length]
    setSkin(next)
  }

  return { currentSkin, setSkin, toggleSkin }
})
