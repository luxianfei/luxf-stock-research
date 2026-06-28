<template>
  <header class="top-nav">
    <div class="nav-inner">
      <router-link to="/" class="brand">
        <span class="brand-mark">↗</span>
        <span class="brand-name">投资助手</span>
      </router-link>
      <nav class="nav-links">
        <router-link to="/" class="nav-link">财务分析</router-link>
        <router-link to="/invest" class="nav-link">智者投资</router-link>
        <router-link to="/collect" class="nav-link">数据采集</router-link>
      </nav>
      <SkinSwitch />
    </div>
  </header>
</template>

<script setup>
import SkinSwitch from './SkinSwitch.vue'
</script>
