<script setup>
import { onMounted, onUnmounted, watch } from 'vue'
import { useThemeStore, mediaQuery } from './stores/theme'
import { useSettingsStore } from './stores/settings'
import { bindVisualViewport } from './utils/visual-viewport'

const themeStore = useThemeStore()
themeStore.apply()

const settingsStore = useSettingsStore()

watch(
  () => themeStore.resolved,
  () => settingsStore.applyThemeColors()
)

let handler = null
let unbindVisualViewport = null

onMounted(async () => {
  unbindVisualViewport = bindVisualViewport()
  handler = () => themeStore.onSystemThemeChange()
  mediaQuery.addEventListener('change', handler)
  await settingsStore.fetchSettings()
  themeStore.setMode(settingsStore.themeMode)
  settingsStore.applyThemeColors()
})

onUnmounted(() => {
  unbindVisualViewport?.()
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
