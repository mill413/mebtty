<script setup>
import { useThemeStore } from '../../stores/theme'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const themeStore = useThemeStore()
</script>

<template>
  <div class="theme-toggle">
    <button
      class="theme-btn"
      :class="{ active: themeStore.mode === 'system' }"
      @click="themeStore.setMode('system')"
      :title="t('toolbar.themeSystem')"
    >
      <!-- Monitor / system icon -->
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
      </svg>
    </button>

    <button
      class="theme-btn"
      :class="{ active: themeStore.mode === 'light' }"
      @click="themeStore.setMode('light')"
      :title="t('toolbar.switchToLight')"
    >
      <!-- Sun icon -->
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="5" />
        <line x1="12" y1="1" x2="12" y2="3" />
        <line x1="12" y1="21" x2="12" y2="23" />
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
        <line x1="1" y1="12" x2="3" y2="12" />
        <line x1="21" y1="12" x2="23" y2="12" />
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
      </svg>
    </button>

    <button
      class="theme-btn"
      :class="{ active: themeStore.mode === 'dark' }"
      @click="themeStore.setMode('dark')"
      :title="t('toolbar.switchToDark')"
    >
      <!-- Moon icon -->
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.theme-toggle {
  display: flex;
  align-items: center;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2px;
  gap: 1px;
}

.theme-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 22px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--overlay);
  cursor: pointer;
  transition: all var(--transition);
}

.theme-btn:hover:not(.active) {
  color: var(--subtext);
  background: var(--surface);
}

.theme-btn.active {
  background: var(--accent);
  color: white;
}
</style>
