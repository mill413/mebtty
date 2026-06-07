<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTerminalStore } from '../stores/terminal'
import { useAuthStore } from '../stores/auth'
import TerminalTabs from '../components/terminal/TerminalTabs.vue'
import TerminalPane from '../components/terminal/TerminalPane.vue'
import TerminalToolbar from '../components/layout/TerminalToolbar.vue'
import StatusBar from '../components/layout/StatusBar.vue'
import FileBrowser from '../components/terminal/FileBrowser.vue'
import { useI18n } from 'vue-i18n'
import ThemeToggle from '../components/common/ThemeToggle.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const terminalStore = useTerminalStore()
const authStore = useAuthStore()

const terminalPaneRef = ref(null)
const terminalDims = ref({ cols: 80, rows: 24 })
const connectionStatus = ref('disconnected')
const showSearch = ref(false)
const showFileBrowser = ref(false)

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchUser()
  }

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

  await nextTick()
  terminalPaneRef.value?.focus()
})

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

function toggleSearch() {
  showSearch.value = !showSearch.value
  if (showSearch.value) {
    nextTick(() => {
      terminalPaneRef.value?.openSearch()
    })
  } else {
    terminalPaneRef.value?.closeSearch()
  }
}

function toggleFileBrowser() {
  showFileBrowser.value = !showFileBrowser.value
}

function closeFileBrowser() {
  showFileBrowser.value = false
}

function handleUpload() {
  if (!terminalStore.activeSession) return
  const input = document.createElement('input')
  input.type = 'file'
  input.onchange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    formData.append('session_id', terminalStore.activeSession)
    try {
      const { default: api } = await import('../services/api')
      await api.post('/api/files/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    } catch (err) {
      console.error('Upload failed:', err)
    }
  }
  input.click()
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
      <div class="header-right">
        <ThemeToggle />
        <span class="text-subtext user-label">{{ authStore.username }}</span>
        <button class="btn-icon-sm" @click="logout" :title="t('terminal.logout')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
      </div>
    </div>

    <TerminalTabs
      :tabs="terminalStore.tabs"
      :activeTabId="terminalStore.activeTabId"
      @switch="handleTabSwitch"
      @close="handleTabClose"
      @rename="handleTabRename"
      @new-tab="handleNewTerminal"
    />

    <TerminalToolbar
      @new-terminal="handleNewTerminal"
      @toggle-search="toggleSearch"
      @toggle-file-browser="toggleFileBrowser"
      :showFileBrowser="showFileBrowser"
      @upload="handleUpload"
    />

    <div class="terminal-main">
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
        v-if="showFileBrowser"
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
  align-items: center;
  justify-content: space-between;
  height: 36px;
  padding: 0 12px;
  background: var(--bg-deep);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-home {
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
}

.btn-home:hover {
  background: var(--surface);
  color: var(--text);
}

.header-brand {
  font-weight: 600;
  font-size: 13px;
  color: var(--subtext);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-label {
  font-size: 12px;
}

.btn-icon-sm {
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

.btn-icon-sm:hover {
  background: var(--surface);
  color: var(--text);
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
