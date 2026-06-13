<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '../../stores/settings'

const settingsStore = useSettingsStore()

const props = defineProps({
  tabs: { type: Array, required: true },
  activeTabId: { type: Number, default: null }
})

const emit = defineEmits(['switch', 'close', 'rename', 'new-tab'])

const { t } = useI18n()

const editingTabId = ref(null)
const editingTitle = ref('')
const dragTabId = ref(null)

function handleClick(tabId) {
  if (editingTabId.value !== null) return
  emit('switch', tabId)
}

function handleClose(tabId, event) {
  event.stopPropagation()
  emit('close', tabId)
}

function handleDblClick(tabId, currentTitle) {
  editingTabId.value = tabId
  editingTitle.value = currentTitle
}

function finishRename(tabId) {
  if (editingTitle.value.trim()) {
    emit('rename', tabId, editingTitle.value.trim())
  }
  editingTabId.value = null
}

function handleRenameKey(tabId, event) {
  if (event.key === 'Enter') {
    finishRename(tabId)
  } else if (event.key === 'Escape') {
    editingTabId.value = null
  }
}

function handleDragStart(tabId, event) {
  dragTabId.value = tabId
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(tabId))
}

function handleDragOver(event) {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}

function handleDrop(targetTabId, event) {
  event.preventDefault()
  dragTabId.value = null
}

function handleDragEnd() {
  dragTabId.value = null
}

function isSettingsTab(tab) {
  return tab.type === 'settings'
}

function getTabDisplayTitle(tab) {
  if (tab.type === 'settings') return t('settings.title')
  const index = props.tabs.indexOf(tab) + 1
  return settingsStore.formatTabTitle(
    settingsStore.tabTitleFormat,
    tab.shell,
    index,
    tab.title,
    tab.username,
    tab.cwd
  )
}

function getShellIcon(shell) {
    if (!shell) return '>'
    const s = shell.toLowerCase()
  if (s.includes('zsh')) return '%'
  if (s.includes('fish')) return '>'
  if (s.includes('bash')) return '$'
  return '>'
}
</script>

<template>
  <div class="tab-bar">
    <div class="tabs-scroll">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        class="tab"
        :class="{ active: tab.id === activeTabId, 'is-settings': isSettingsTab(tab) }"
        :draggable="!isSettingsTab(tab)"
        @click="handleClick(tab.id)"
        @dblclick="!isSettingsTab(tab) && handleDblClick(tab.id, tab.title)"
        @dragstart="!isSettingsTab(tab) && handleDragStart(tab.id, $event)"
        @dragover="handleDragOver"
        @drop="handleDrop(tab.id, $event)"
        @dragend="handleDragEnd"
      >
        <!-- Settings tab icon -->
        <span v-if="isSettingsTab(tab)" class="tab-icon tab-icon-settings">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.32 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
          </svg>
        </span>
        <!-- Shell tab icon -->
        <span v-else class="tab-icon">{{ getShellIcon(tab.shell) }}</span>

        <input
          v-if="editingTabId === tab.id && !isSettingsTab(tab)"
          v-model="editingTitle"
          class="tab-rename-input"
          @blur="finishRename(tab.id)"
          @keydown="handleRenameKey(tab.id, $event)"
          @click.stop
          autofocus
        />
        <span v-else class="tab-title truncate">{{ getTabDisplayTitle(tab) }}</span>

        <button class="tab-close" @click="handleClose(tab.id, $event)" :title="t('tabs.close')">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div class="tab-new-wrapper">
        <button class="tab-new" @click="emit('new-tab')" :title="t('tabs.newTerminal')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tab-bar {
  display: flex;
  align-items: flex-end;
  height: 100%;
  background: var(--bg-deep);
  overflow: visible;
  position: relative;
}

.tabs-scroll {
  display: flex;
  flex: 1;
  gap: 3px;
  padding: 0 4px 0 16px;
  overflow-x: auto;
  scrollbar-width: none;
}

.tabs-scroll::-webkit-scrollbar {
  display: none;
}

.tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  min-width: 120px;
  max-width: 200px;
  height: 28px;
  background: transparent;
  border: none;
  border-radius: 16px 16px 0 0;
  color: var(--subtext);
  font-size: 12px;
  cursor: pointer;
  transition: background var(--transition);
  user-select: none;
  position: relative;
  flex-shrink: 0;
}

.tab:hover {
  background: var(--surface);
}

.tab.active {
  background: var(--bg);
  color: var(--text);
  box-shadow: inset 0 -3px 0 0 var(--accent);
  z-index: 1;
}

.tab.active::before,
.tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  width: 20px;
  height: 20px;
  border-radius: 100%;
  box-shadow: 0 0 0 40px var(--bg);
  z-index: -1;
  pointer-events: none;
}

.tab.active::before {
  left: -20px;
  clip-path: inset(50% -10px 0 50%);
}

.tab.active::after {
  right: -20px;
  clip-path: inset(50% 50% 0 -10px);
}

.tab-icon {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--accent);
  flex-shrink: 0;
}

.tab-icon-settings {
  display: flex;
  align-items: center;
  justify-content: center;
}

.tab-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-rename-input {
  flex: 1;
  min-width: 0;
  padding: 1px 4px;
  background: var(--bg);
  border: 1px solid var(--accent);
  border-radius: 3px;
  color: var(--text);
  font-size: 12px;
  outline: none;
}

.tab-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  background: transparent;
  border: none;
  border-radius: 3px;
  color: var(--subtext);
  flex-shrink: 0;
  opacity: 0;
  transition: all var(--transition);
}

.tab:hover .tab-close,
.tab.active .tab-close {
  opacity: 1;
}

.tab-close:hover {
  background: rgba(243, 139, 168, 0.15);
  color: var(--error);
}

.tab-new-wrapper {
  position: relative;
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.tab-new {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  border-radius: 50%;
  color: var(--subtext);
  transition: all var(--transition);
  cursor: pointer;
}

.tab-new:hover {
  background: var(--surface);
  color: var(--text);
}

</style>

<style>
.shell-dropdown {
  position: fixed;
  min-width: 120px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 4px;
  z-index: 9999;
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
  transition: background 0.15s;
}

.shell-dropdown-item:hover {
  background: var(--overlay);
}
</style>
