<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useThemeStore, mediaQuery } from './stores/theme'

const themeStore = useThemeStore()
themeStore.apply()

let handler = null

onMounted(() => {
  handler = () => themeStore.onSystemThemeChange()
  mediaQuery.addEventListener('change', handler)
})

onUnmounted(() => {
  if (handler) {
    mediaQuery.removeEventListener('change', handler)
  }
})
</script>

<template>
  <router-view />
</template>

<style>
/* App-level styles are in global.css */
</style>
