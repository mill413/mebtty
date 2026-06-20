<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '../../stores/settings'

const settingsStore = useSettingsStore()

const props = defineProps({
  tabs: { type: Array, required: true },
  activeTabId: { type: Number, default: null }
})

const emit = defineEmits(['switch', 'close', 'rename', 'icon-change', 'new-tab'])

const { t } = useI18n()

const editingTabId = ref(null)
const editingTitle = ref('')
const dragTabId = ref(null)
const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  tab: null
})
const iconPicker = ref({
  visible: false,
  x: 0,
  y: 0,
  tab: null,
  query: ''
})

const iconModules = import.meta.glob('/public/catppuccin-icons/*.svg', {
  eager: true,
  query: '?url',
  import: 'default'
})

const preferredIconNames = [
  'bash',
  'robots',
  'adobe-ai',
  'code-climate',
  'powershell',
  'vim',
  'vscode',
  'cursor',
  'git',
  'docker',
  'python',
  'javascript',
  'typescript',
  'vue',
  'go',
  'rust',
  'database',
  'config',
  'text'
]

const iconOptions = Object.entries(iconModules)
  .map(([path, src]) => {
    const name = path.split('/').pop().replace(/\.svg$/, '')
    return {
      name,
      label: formatIconLabel(name),
      src,
      searchText: name.replace(/[-_]/g, ' ')
    }
  })
  .sort((a, b) => {
    const aPreferred = preferredIconNames.indexOf(a.name)
    const bPreferred = preferredIconNames.indexOf(b.name)
    if (aPreferred !== -1 || bPreferred !== -1) {
      if (aPreferred === -1) return 1
      if (bPreferred === -1) return -1
      return aPreferred - bPreferred
    }
    return a.label.localeCompare(b.label)
  })

const processIconMap = {
  claude: 'robots',
  'claude-code': 'robots',
  claudecode: 'robots',
  anthropic: 'robots',
  codex: 'robots',
  'codex-linux-sandbox': 'robots',
  'codex-linux-san': 'robots',
  openai: 'robots',
  chatgpt: 'robots',
  bash: 'bash',
  sh: 'bash',
  dash: 'bash',
  ksh: 'bash',
  powershell: 'powershell',
  pwsh: 'powershell',
  nvim: 'vim',
  vim: 'vim',
  vi: 'vim',
  git: 'git',
  lazygit: 'git',
  python: 'python',
  python3: 'python',
  node: 'javascript',
  npm: 'npm',
  pnpm: 'pnpm',
  yarn: 'yarn',
  bun: 'bun',
  docker: 'docker',
  cargo: 'cargo',
  go: 'go',
  make: 'makefile',
  nginx: 'nginx'
}

function formatIconLabel(name) {
  return name
    .replace(/^_/, '')
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

const filteredIconOptions = computed(() => {
  const query = iconPicker.value.query.trim().toLowerCase()
  if (!query) return iconOptions
  return iconOptions.filter((icon) => {
    const searchable = [
      icon.name,
      icon.label,
      icon.searchText
    ].join(' ').toLowerCase()
    return searchable.includes(query)
  })
})

function handleClick(tabId) {
  if (editingTabId.value !== null) return
  emit('switch', tabId)
}

function handleClose(tabId, event) {
  event.stopPropagation()
  emit('close', tabId)
}

function handleDblClick(tabId, currentTitle) {
  startRename(tabId, currentTitle)
}

function startRename(tabId, currentTitle) {
  editingTabId.value = tabId
  editingTitle.value = currentTitle
  nextTick(() => {
    document.querySelector('.tab-rename-input')?.focus()
  })
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

function handleContextMenu(event, tab) {
  if (isSettingsTab(tab)) return
  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    tab
  }
}

function closeContextMenu() {
  contextMenu.value.visible = false
  contextMenu.value.tab = null
}

function closeIconPicker() {
  iconPicker.value.visible = false
  iconPicker.value.tab = null
  iconPicker.value.query = ''
}

function renameFromContextMenu() {
  const tab = contextMenu.value.tab
  if (!tab) return
  startRename(tab.id, tab.title)
  closeContextMenu()
}

function openIconPickerFromContextMenu() {
  const tab = contextMenu.value.tab
  if (!tab) return
  iconPicker.value = {
    visible: true,
    x: contextMenu.value.x,
    y: contextMenu.value.y,
    tab,
    query: ''
  }
  closeContextMenu()
  nextTick(() => {
    document.querySelector('.tab-icon-search')?.focus()
  })
}

function chooseIcon(icon) {
  const tab = iconPicker.value.tab
  if (!tab) return
  emit('icon-change', tab.id, icon.name)
  closeIconPicker()
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

function getProcessIconName(processName) {
  if (!processName) return ''
  const normalized = processName.toLowerCase()
  if (processIconMap[normalized]) return processIconMap[normalized]
  for (const [name, icon] of Object.entries(processIconMap)) {
    if (normalized.includes(name)) return icon
  }
  return ''
}

function getShellIconName(shell) {
  if (!shell) return ''
  const s = shell.toLowerCase()
  if (s.includes('bash')) return 'bash'
  if (s.includes('powershell') || s.includes('pwsh')) return 'powershell'
  return ''
}

function getFallbackGlyph(tab) {
  const shell = (tab.shell || '').toLowerCase()
  if (shell.includes('zsh')) return '%'
  if (shell.includes('fish') || shell.includes('nu')) return '>'
  return '$'
}

function getIconSource(iconName) {
  if (!iconName) return ''
  const option = iconOptions.find((icon) => icon.name === iconName)
  return option?.src || `/catppuccin-icons/${iconName}.svg`
}

function getTabIcon(tab) {
  const iconName = tab.iconOverride || getProcessIconName(tab.processName) || getShellIconName(tab.shell)
  if (iconName) {
    return {
      type: 'image',
      src: getIconSource(iconName),
      label: iconName
    }
  }
  return {
    type: 'glyph',
    glyph: getFallbackGlyph(tab),
    label: tab.shell || 'terminal'
  }
}

function handleGlobalClick() {
  closeContextMenu()
  closeIconPicker()
}

function handleGlobalKeydown(event) {
  if (event.key === 'Escape') {
    closeContextMenu()
    closeIconPicker()
  }
}

onMounted(() => {
  window.addEventListener('click', handleGlobalClick)
  window.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('click', handleGlobalClick)
  window.removeEventListener('keydown', handleGlobalKeydown)
})
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
        @contextmenu.prevent="handleContextMenu($event, tab)"
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
        <span v-else class="tab-icon">
          <img
            v-if="getTabIcon(tab).type === 'image'"
            class="tab-icon-img"
            :src="getTabIcon(tab).src"
            :alt="getTabIcon(tab).label"
          />
          <span v-else>{{ getTabIcon(tab).glyph }}</span>
        </span>

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

    <Teleport to="body">
      <div
        v-if="contextMenu.visible"
        class="tab-context-menu"
        :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
        @click.stop
        @contextmenu.prevent
      >
        <button class="tab-context-item" @click="renameFromContextMenu">
          <span class="tab-context-icon">T</span>
          <span>{{ t('tabs.rename') }}</span>
        </button>
        <button class="tab-context-item" @click="openIconPickerFromContextMenu">
          <span class="tab-context-icon">
            <img class="tab-context-icon-img" src="/catppuccin-icons/vscode.svg" alt="" />
          </span>
          <span>{{ t('tabs.changeIcon') }}</span>
        </button>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="iconPicker.visible"
        class="tab-icon-picker"
        :style="{ left: `${iconPicker.x}px`, top: `${iconPicker.y}px` }"
        @click.stop
        @contextmenu.prevent
      >
        <div class="tab-icon-picker-header">
          <input
            v-model="iconPicker.query"
            class="tab-icon-search"
            type="text"
            :placeholder="t('tabs.searchIcon')"
          />
        </div>
        <div class="tab-icon-grid">
          <button
            v-for="icon in filteredIconOptions"
            :key="icon.name"
            class="tab-icon-option"
            :class="{ active: iconPicker.tab?.iconOverride === icon.name }"
            @click="chooseIcon(icon)"
            :title="icon.label"
          >
            <img class="tab-icon-option-img" :src="getIconSource(icon.name)" :alt="icon.label" />
            <span>{{ icon.label }}</span>
          </button>
          <div v-if="filteredIconOptions.length === 0" class="tab-icon-empty">
            {{ t('tabs.noIcons') }}
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.tab-bar {
  display: flex;
  align-items: flex-end;
  height: 100%;
  background: var(--bg-deep);
  overflow: hidden;
  position: relative;
}

.tabs-scroll {
  display: flex;
  flex: 1;
  gap: 3px;
  padding: 0 4px 0 16px;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: thin;
  scrollbar-color: var(--overlay) transparent;
}

.tabs-scroll::-webkit-scrollbar {
  height: 4px;
}

.tabs-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.tabs-scroll::-webkit-scrollbar-thumb {
  background: var(--overlay);
  border-radius: 999px;
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
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 11px;
}

.tab-icon-img {
  width: 16px;
  height: 16px;
  object-fit: contain;
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

.tab-context-menu {
  position: fixed;
  min-width: 176px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 5px;
  z-index: 9999;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
}

.tab-context-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 9px;
  background: transparent;
  border: none;
  border-radius: 5px;
  color: var(--text);
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  transition: background var(--transition), color var(--transition);
}

.tab-context-item:hover,
.tab-context-item.active {
  background: var(--overlay);
}

.tab-context-item.active {
  color: var(--accent);
}

.tab-context-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  width: 18px;
  height: 18px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--accent);
  text-align: center;
}

.tab-context-icon-img {
  width: 16px;
  height: 16px;
  object-fit: contain;
}

.tab-context-divider {
  height: 1px;
  margin: 4px 2px;
  background: var(--border);
}

.tab-context-label {
  padding: 4px 9px 3px;
  color: var(--subtext);
  font-size: 10px;
  text-transform: uppercase;
}

.tab-icon-picker {
  position: fixed;
  width: min(360px, calc(100vw - 24px));
  max-height: min(440px, calc(100vh - 24px));
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px;
  z-index: 10000;
  box-shadow: 0 12px 34px rgba(0, 0, 0, 0.3);
}

.tab-icon-picker-header {
  margin-bottom: 8px;
}

.tab-icon-search {
  width: 100%;
  height: 30px;
  padding: 0 10px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 5px;
  color: var(--text);
  font-size: 12px;
  outline: none;
}

.tab-icon-search:focus {
  border-color: var(--accent);
}

.tab-icon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(76px, 1fr));
  gap: 4px;
  overflow-y: auto;
  padding-right: 2px;
}

.tab-icon-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  min-width: 0;
  height: 68px;
  padding: 8px 5px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  color: var(--text);
  cursor: pointer;
  transition: background var(--transition), border-color var(--transition);
}

.tab-icon-option:hover,
.tab-icon-option.active {
  background: var(--overlay);
  border-color: var(--border);
}

.tab-icon-option.active {
  border-color: var(--accent);
}

.tab-icon-option-img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.tab-icon-option span {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 10px;
  color: var(--subtext);
}

.tab-icon-empty {
  grid-column: 1 / -1;
  padding: 18px 8px;
  color: var(--subtext);
  font-size: 12px;
  text-align: center;
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
