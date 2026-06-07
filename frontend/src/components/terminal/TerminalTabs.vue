<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

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
  // Reorder is handled by the parent if needed
  dragTabId.value = null
}

function handleDragEnd() {
  dragTabId.value = null
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
        :class="{ active: tab.id === activeTabId }"
        draggable="true"
        @click="handleClick(tab.id)"
        @dblclick="handleDblClick(tab.id, tab.title)"
        @dragstart="handleDragStart(tab.id, $event)"
        @dragover="handleDragOver"
        @drop="handleDrop(tab.id, $event)"
        @dragend="handleDragEnd"
      >
        <span class="tab-icon">{{ getShellIcon(tab.shell) }}</span>

        <input
          v-if="editingTabId === tab.id"
          v-model="editingTitle"
          class="tab-rename-input"
          @blur="finishRename(tab.id)"
          @keydown="handleRenameKey(tab.id, $event)"
          @click.stop
          autofocus
        />
        <span v-else class="tab-title truncate">{{ tab.title }}</span>

        <button class="tab-close" @click="handleClose(tab.id, $event)" title="Close">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>

    <button class="tab-new" @click="$emit('new-tab', '/bin/bash')" :title="t('tabs.newTerminal')">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="5" x2="12" y2="19" />
        <line x1="5" y1="12" x2="19" y2="12" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.tab-bar {
  display: flex;
  align-items: stretch;
  height: 36px;
  background: var(--bg-deep);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  overflow: hidden;
}

.tabs-scroll {
  display: flex;
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
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
  height: 100%;
  background: transparent;
  border-right: 1px solid var(--border);
  color: var(--subtext);
  font-size: 12px;
  cursor: pointer;
  transition: background var(--transition);
  user-select: none;
  position: relative;
}

.tab:hover {
  background: var(--surface);
}

.tab.active {
  background: var(--bg);
  color: var(--text);
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--accent);
}

.tab-icon {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--accent);
  flex-shrink: 0;
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
  background: rgba(243, 139, 168, 0.2);
  color: var(--error);
}

.tab-new {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  min-width: 36px;
  height: 100%;
  background: transparent;
  border: none;
  color: var(--subtext);
  transition: all var(--transition);
}

.tab-new:hover {
  background: var(--surface);
  color: var(--text);
}
</style>
