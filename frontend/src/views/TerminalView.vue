<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTerminalStore } from '../stores/terminal'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import TerminalTabs from '../components/terminal/TerminalTabs.vue'
import TerminalPane from '../components/terminal/TerminalPane.vue'
import StatusBar from '../components/layout/StatusBar.vue'
import FileBrowser from '../components/terminal/FileBrowser.vue'
import { useI18n } from 'vue-i18n'
import ThemeToggle from '../components/common/ThemeToggle.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const terminalStore = useTerminalStore()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()

const terminalPaneRef = ref(null)
const terminalDims = ref({ cols: 80, rows: 24 })
const connectionStatus = ref('disconnected')
const showFileBrowser = ref(false)
const showUserMenu = ref(false)

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchUser()
  }

  if (!settingsStore.loaded) {
    await settingsStore.fetchSettings()
  }

  // Close user menu on outside click
  document.addEventListener('click', () => {
    showUserMenu.value = false
  })

  // If route has a sessionId, ensure there's a tab for it
  if (route.params.sessionId) {
    const sessionId = route.params.sessionId
    const existing = terminalStore.tabs.find((t) => t.sessionId === sessionId)
    if (!existing) {
      terminalStore.addTabForSession(sessionId, `Session ${sessionId}`)
    } else {
      terminalStore.activeTabId = existing.id
    }
  }

  // Auto-open file browser if query param is set
  if (route.query.files === '1') {
    showFileBrowser.value = true
  }

  await nextTick()
  terminalPaneRef.value?.focus()
})

watch(() => terminalStore.activeTab, (tab) => {
  if (tab) {
    const title = settingsStore.formatTabTitle(
      settingsStore.tabTitleFormat,
      tab.shell,
      terminalStore.tabs.indexOf(tab) + 1,
      tab.title
    )
    document.title = `WebTTY - ${title}`
  } else {
    document.title = 'WebTTY'
  }
}, { immediate: true })

watch(() => route.params.sessionId, (newId) => {
  if (newId) {
    const existing = terminalStore.tabs.find((t) => t.sessionId === newId)
    if (existing) {
      terminalStore.activeTabId = existing.id
    } else {
      terminalStore.addTabForSession(newId, `Session ${newId}`)
    }
  }
})

function handleNewTerminal(shell) {
  terminalStore.createSession(shell)
}

function handleTabSwitch(tabId) {
  terminalStore.switchTab(tabId)
}

function handleTabClose(tabId) {
  terminalStore.closeTab(tabId)
}

function handleTabRename(tabId, title) {
  terminalStore.renameTab(tabId, title)
}

function handleResize(dims) {
  terminalDims.value = dims
}

function handleConnectionChange(status) {
  connectionStatus.value = status
}

function toggleFileBrowser() {
  showFileBrowser.value = !showFileBrowser.value
}

function closeFileBrowser() {
  showFileBrowser.value = false
}

function goHome() {
  router.push('/')
}

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="terminal-page">
    <div class="terminal-header">
      <div class="header-left">
        <button class="btn-home" @click="goHome" :title="t('terminal.home')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="4 17 10 11 4 5" />
            <line x1="12" y1="19" x2="20" y2="19" />
          </svg>
        </button>
        <span class="header-brand">WebTTY</span>
      </div>
      <div class="header-tabs">
        <TerminalTabs
          :tabs="terminalStore.tabs"
          :activeTabId="terminalStore.activeTabId"
          @switch="handleTabSwitch"
          @close="handleTabClose"
          @rename="handleTabRename"
          @new-tab="handleNewTerminal"
        />
      </div>
      <div class="header-right">
        <ThemeToggle />
        <button
          class="toolbar-btn"
          :class="{ active: showFileBrowser }"
          @click="toggleFileBrowser"
          :title="t('toolbar.fileBrowser')"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
          </svg>
        </button>
        <div class="user-menu-wrapper" @click.stop>
          <button class="user-label" @click="showUserMenu = !showUserMenu">
            {{ authStore.username }}
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          <div v-if="showUserMenu" class="user-dropdown">
            <button class="dropdown-item" @click="router.push('/settings')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.32 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
              </svg>
              {{ t('toolbar.settings') }}
            </button>
            <button class="dropdown-item" @click="logout">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              {{ t('terminal.logout') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="terminal-main">
      <FileBrowser
        v-if="showFileBrowser && settingsStore.sidebarOnLeft"
        :position="settingsStore.sidebarPosition"
        @close="closeFileBrowser"
      />
      <div class="terminal-body">
        <TerminalPane
          v-if="terminalStore.activeTab"
          ref="terminalPaneRef"
          :sessionId="terminalStore.activeTab.sessionId"
          :key="terminalStore.activeTab.sessionId"
          @resize="handleResize"
          @connection-change="handleConnectionChange"
        />
        <div v-else class="empty-terminal">
          <div class="empty-content">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="empty-icon">
              <polyline points="4 17 10 11 4 5" />
              <line x1="12" y1="19" x2="20" y2="19" />
            </svg>
            <h3>{{ t('terminal.noActive') }}</h3>
            <p class="text-subtext">{{ t('terminal.noActiveDesc') }}</p>
            <button class="btn-create" @click="handleNewTerminal('/bin/bash')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              {{ t('terminal.newTerminal') }}
            </button>
          </div>
        </div>
      </div>
      <FileBrowser
        v-if="showFileBrowser && !settingsStore.sidebarOnLeft"
        :position="settingsStore.sidebarPosition"
        @close="closeFileBrowser"
      />
    </div>

    <StatusBar
      :shell="terminalStore.activeTab?.shell || ''"
      :status="terminalStore.activeTab?.status || ''"
      :connectionStatus="connectionStatus"
      :cols="terminalDims.cols"
      :rows="terminalDims.rows"
    />
  </div>
</template>

<style scoped>
.terminal-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}

.terminal-header {
  display: flex;
  align-items: stretch;
  height: 36px;
  background: var(--bg-deep);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  flex-shrink: 0;
}

.btn-home {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--subtext);
  transition: all var(--transition);
}

.btn-home:hover {
  background: var(--surface);
  color: var(--text);
}

.header-brand {
  font-weight: 600;
  font-size: 13px;
  color: var(--subtext);
  white-space: nowrap;
}

.header-tabs {
  flex: 1;
  min-width: 0;
  height: 36px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  flex-shrink: 0;
}

.toolbar-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--subtext);
  transition: all var(--transition);
  cursor: pointer;
}

.toolbar-btn:hover {
  background: var(--surface);
  color: var(--text);
}

.toolbar-btn.active {
  background: var(--surface);
  color: var(--accent);
}

.user-menu-wrapper {
  position: relative;
}

.user-label {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--subtext);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--transition);
}

.user-label:hover {
  background: var(--surface);
  color: var(--text);
}

.user-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 140px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 4px;
  z-index: 9999;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--text);
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  transition: background var(--transition);
}

.dropdown-item:hover {
  background: var(--overlay);
}

.terminal-body {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.terminal-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.empty-terminal {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-content {
  text-align: center;
}

.empty-icon {
  color: var(--overlay);
  margin-bottom: 16px;
}

.empty-content h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 6px;
}

.empty-content p {
  margin-bottom: 20px;
  font-size: 14px;
}

.btn-create {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 500;
  transition: background var(--transition);
}

.btn-create:hover {
  background: var(--accent-hover);
}
</style>
