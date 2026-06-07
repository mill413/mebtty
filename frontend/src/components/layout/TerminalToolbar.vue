<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const emit = defineEmits(['new-terminal', 'toggle-search', 'toggle-file-browser', 'upload'])

const props = defineProps({
  showFileBrowser: {
    type: Boolean,
    default: false
  }
})

const showShellMenu = ref(false)
const shells = [
  { value: '/bin/bash', label: 'Bash' },
  { value: '/bin/zsh', label: 'Zsh' },
  { value: '/usr/bin/fish', label: 'Fish' },
  { value: '/bin/sh', label: 'SH' }
]

function selectShell(shell) {
  emit('new-terminal', shell)
  showShellMenu.value = false
}

function toggleShellMenu() {
  showShellMenu.value = !showShellMenu.value
}
</script>

<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <div class="shell-selector" @click.stop>
        <button class="toolbar-btn primary-btn" @click="toggleShellMenu">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          {{ t('toolbar.new') }}
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        <div v-if="showShellMenu" class="shell-dropdown">
          <button
            v-for="shell in shells"
            :key="shell.value"
            class="shell-dropdown-item"
            @click="selectShell(shell.value)"
          >
            {{ shell.label }}
          </button>
        </div>
      </div>

      <div class="toolbar-divider"></div>

      <button class="toolbar-btn" @click="$emit('toggle-search')" :title="t('toolbar.search') + ' (Ctrl+Shift+F)'">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      </button>

      <button
        class="toolbar-btn"
        :class="{ active: showFileBrowser }"
        @click="$emit('toggle-file-browser')"
        :title="t('toolbar.fileBrowser')"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
        </svg>
      </button>

      <button class="toolbar-btn" @click="$emit('upload')" :title="t('toolbar.uploadFile')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      </button>
    </div>

    <div class="toolbar-right">
      <button class="toolbar-btn" :title="t('toolbar.settings')" disabled>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 32px;
  padding: 0 8px;
  background: var(--bg-deep);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 2px;
}

.toolbar-divider {
  width: 1px;
  height: 16px;
  background: var(--border);
  margin: 0 6px;
}

.toolbar-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  height: 24px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--subtext);
  font-size: 12px;
  transition: all var(--transition);
  white-space: nowrap;
}

.toolbar-btn:hover:not(:disabled) {
  background: var(--surface);
  color: var(--text);
}

.toolbar-btn.active {
  background: var(--surface);
  color: var(--accent);
}

.toolbar-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.primary-btn {
  color: var(--accent);
}

.primary-btn:hover {
  background: rgba(124, 58, 237, 0.1);
  color: var(--accent) !important;
}

.shell-selector {
  position: relative;
}

.shell-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 120px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 4px;
  z-index: 100;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.shell-dropdown-item {
  display: block;
  width: 100%;
  padding: 6px 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--text);
  font-size: 12px;
  text-align: left;
  transition: background var(--transition);
}

.shell-dropdown-item:hover {
  background: var(--overlay);
}
</style>
