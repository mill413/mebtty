<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
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
const showShellMenu = ref(false)
const newBtnRef = ref(null)
const menuPos = ref({ top: 0, left: 0 })
const tabBarRef = ref(null)

const shells = [
  { value: '/bin/bash', label: 'Bash' },
  { value: '/bin/zsh', label: 'Zsh' },
  { value: '/usr/bin/fish', label: 'Fish' },
  { value: '/bin/sh', label: 'SH' }
]

function closeShellMenu() {
  showShellMenu.value = false
}

function onClickOutside(e) {
  if (showShellMenu.value) {
    closeShellMenu()
  }
}

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

function toggleShellMenu(e) {
  e.stopPropagation()
  if (showShellMenu.value) {
    showShellMenu.value = false
    return
  }
  const btn = newBtnRef.value
  if (btn) {
    const rect = btn.getBoundingClientRect()
    menuPos.value = { top: rect.bottom + 4, left: rect.left }
  }
  showShellMenu.value = true
}

function selectShell(shell) {
  emit('new-tab', shell)
  showShellMenu.value = false
}

function getShellIcon(shell) {
    if (!shell) return '>'
    const s = shell.toLowerCase()
  if (s.includes('zsh')) return '%'
  if (s.includes('fish')) return '>'
  if (s.includes('bash')) return '$'
  return '>'
}

onMounted(() => {
  document.addEventListener('click', onClickOutside, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside, true)
})
</script>

<template>
  <div ref="tabBarRef" class="tab-bar" @click="showShellMenu = false">
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

        <button class="tab-close" @click="handleClose(tab.id, $event)" :title="t('tabs.close')">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div class="tab-new-wrapper">
        <button ref="newBtnRef" class="tab-new" @click="toggleShellMenu" :title="t('tabs.newTerminal')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showShellMenu" class="shell-dropdown" :style="{ top: menuPos.top + 'px', left: menuPos.left + 'px' }" @click.stop>
        <button
          v-for="shell in shells"
          :key="shell.value"
          class="shell-dropdown-item"
          @click="selectShell(shell.value)"
        >
          {{ shell.label }}
        </button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.tab-bar {
  display: flex;
  align-items: stretch;
  height: 100%;
  background: var(--bg-deep);
  overflow: visible;
  position: relative;
}

.tabs-scroll {
  display: flex;
  flex: 1;
  gap: 3px;
  padding: 0 4px;
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
  height: 100%;
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
