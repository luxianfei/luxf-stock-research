<template>
  <div :data-theme="skinStore.currentSkin">
    <AppHeader />
    <main class="container">
      <NotifBar />
      <router-view />
    </main>
    <AppFooter />
  </div>
</template>

<script setup>
import { useSkinStore } from '@/stores/skin'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import NotifBar from '@/components/layout/NotifBar.vue'

const skinStore = useSkinStore()
</script>

<style lang="scss">
.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 20px 64px;
}
</style>
