import { defineStore } from 'pinia'
import api from '../services/api'
import router from '../router'

let tabIdCounter = 0

export const useTerminalStore = defineStore('terminal', {
  state: () => ({
    tabs: [],
    sessions: [],
    activeTabId: null
  }),

  getters: {
    activeTab: (state) => state.tabs.find((t) => t.id === state.activeTabId) || null,
    activeSession: (state) => {
      const tab = state.tabs.find((t) => t.id === state.activeTabId)
      return tab ? tab.sessionId : null
    },
    settingsTab: (state) => state.tabs.find((t) => t.type === 'settings') || null
  },

  actions: {
    async createSession(shell = '/bin/bash', title = '', cwd = '', localUser = '', localPassword = '') {
      const { data } = await api.post('/api/sessions', {
        title: title || `${shell.split('/').pop()} session`,
        shell,
        cwd,
        local_user: localUser,
        local_password: localPassword
      })
      const tabId = ++tabIdCounter
      this.tabs.push({
        id: tabId,
        title: title || `${shell.split('/').pop()} #${this.tabs.length + 1}`,
        sessionId: data.id,
        shell: shell,
        cwd: cwd || data.cwd || '',
        username: data.username || '',
        processName: data.process || '',
        iconOverride: null,
        status: 'running'
      })
      this.activeTabId = tabId
      router.push(`/terminal/${data.id}`)
      return data
    },

    openSettingsTab() {
      const existing = this.tabs.find((t) => t.type === 'settings')
      if (existing) {
        this.activeTabId = existing.id
        router.push('/terminal')
        return
      }
      const tabId = ++tabIdCounter
      this.tabs.push({
        id: tabId,
        title: 'Settings',
        sessionId: '__settings__',
        shell: '',
        status: '',
        type: 'settings'
      })
      this.activeTabId = tabId
      router.push('/terminal')
    },

    closeTab(tabId) {
      const idx = this.tabs.findIndex((t) => t.id === tabId)
      if (idx === -1) return

      const closedTab = this.tabs[idx]

      // Delete the session on backend for terminal tabs (not settings)
      if (closedTab.type !== 'settings') {
        api.delete(`/api/sessions/${closedTab.sessionId}`).catch(() => {})
        this.sessions = this.sessions.filter((s) => s.id !== closedTab.sessionId)
      }

      this.tabs.splice(idx, 1)

      if (this.activeTabId === tabId) {
        if (this.tabs.length > 0) {
          const newIdx = Math.min(idx, this.tabs.length - 1)
          this.activeTabId = this.tabs[newIdx].id
          const nextTab = this.tabs[newIdx]
          if (nextTab.type === 'settings') {
            router.push('/terminal')
          } else {
            router.push(`/terminal/${nextTab.sessionId}`)
          }
        } else {
          this.activeTabId = null
          router.push('/terminal')
        }
      }
    },

    switchTab(tabId) {
      const tab = this.tabs.find((t) => t.id === tabId)
      if (tab) {
        this.activeTabId = tabId
        if (tab.type === 'settings') {
          router.push('/terminal')
        } else {
          router.push(`/terminal/${tab.sessionId}`)
        }
      }
    },

    renameTab(tabId, newTitle) {
      const tab = this.tabs.find((t) => t.id === tabId)
      if (tab) {
        tab.title = newTitle
      }
    },

    reorderTabs(fromIndex, toIndex) {
      const [moved] = this.tabs.splice(fromIndex, 1)
      this.tabs.splice(toIndex, 0, moved)
    },

    addTabForSession(sessionId, title, shell, cwd = '', username = '') {
      const existing = this.tabs.find((t) => t.sessionId === sessionId)
      if (existing) {
        this.activeTabId = existing.id
        return existing
      }
      const tabId = ++tabIdCounter
      this.tabs.push({
        id: tabId,
        title: title || `Session ${sessionId}`,
        sessionId,
        shell: shell || '/bin/bash',
        cwd,
        username,
        processName: '',
        iconOverride: null,
        status: 'running'
      })
      this.activeTabId = tabId
      return this.tabs[this.tabs.length - 1]
    },

    updateTabStatus(sessionId, status) {
      const tab = this.tabs.find((t) => t.sessionId === sessionId)
      if (tab) tab.status = status
    },

    updateTabCwd(sessionId, cwd) {
      const tab = this.tabs.find((t) => t.sessionId === sessionId)
      if (tab) tab.cwd = cwd

      const session = this.sessions.find((s) => s.id === sessionId)
      if (session) session.cwd = cwd
    },

    updateTabRuntimeStatus(sessionId, status = {}) {
      const tab = this.tabs.find((t) => t.sessionId === sessionId)
      if (tab) {
        if (typeof status.cwd === 'string' && status.cwd) tab.cwd = status.cwd
        if (typeof status.username === 'string' && status.username) tab.username = status.username
        if (typeof status.process === 'string') tab.processName = status.process
      }

      const session = this.sessions.find((s) => s.id === sessionId)
      if (session) {
        if (typeof status.cwd === 'string' && status.cwd) session.cwd = status.cwd
        if (typeof status.username === 'string' && status.username) session.username = status.username
      }
    },

    setTabIcon(tabId, icon) {
      const tab = this.tabs.find((t) => t.id === tabId)
      if (tab) tab.iconOverride = icon || null
    },

    async fetchSessions() {
      try {
        const { data } = await api.get('/api/sessions')
        this.sessions = data
      } catch {
        this.sessions = []
      }
    },

    async reconnectSession(sessionId) {
      const { data } = await api.post(`/api/sessions/${sessionId}/reconnect`)
      this.addTabForSession(data.id, data.title, data.shell, data.cwd || '', data.username || '')
      router.push(`/terminal/${data.id}`)
      return data
    },

    async deleteSession(sessionId) {
      await api.delete(`/api/sessions/${sessionId}`)
      // Remove tab without navigating (closeTab triggers router.push)
      const tab = this.tabs.find((t) => t.sessionId === sessionId)
      if (tab) {
        const idx = this.tabs.findIndex((t) => t.id === tab.id)
        this.tabs.splice(idx, 1)
        if (this.activeTabId === tab.id) {
          if (this.tabs.length > 0) {
            const newIdx = Math.min(idx, this.tabs.length - 1)
            this.activeTabId = this.tabs[newIdx].id
          } else {
            this.activeTabId = null
          }
        }
      }
      this.sessions = this.sessions.filter((s) => s.id !== sessionId)
    }
  }
})
