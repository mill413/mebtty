import { defineStore } from 'pinia'
import api from '../services/api'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    themeMode: localStorage.getItem('mebtty-theme') || 'system',
    accentColor: localStorage.getItem('mebtty-accent') || '#7c3aed',
    tabTitleFormat: '{user}: {cwd}',
    sidebarPosition: 'right',
    sessionTimeout: 0,
    fileAutoSave: localStorage.getItem('mebtty-file-auto-save') !== 'false',
    fileShowLineNumbers: localStorage.getItem('mebtty-file-show-line-numbers') === 'true',
    statusBarVisible: localStorage.getItem('mebtty-statusbar-visible') !== 'false',
    statusBarItems: JSON.parse(localStorage.getItem('mebtty-statusbar-items') || '[{"key":"shell","visible":false,"position":"left","order":0},{"key":"status","visible":false,"position":"left","order":1},{"key":"connection","visible":true,"position":"right","order":0}]'),
    loaded: false
  }),

  getters: {
    sidebarOnLeft: (state) => state.sidebarPosition === 'left',
    statusBarLeftItems: (state) =>
      state.statusBarItems.filter((i) => i.visible && i.position === 'left').sort((a, b) => a.order - b.order),
    statusBarRightItems: (state) =>
      state.statusBarItems.filter((i) => i.visible && i.position === 'right').sort((a, b) => a.order - b.order)
  },

  actions: {
    async fetchSettings() {
      try {
        const { data } = await api.get('/api/settings')
        this.themeMode = data.theme_mode
        this.accentColor = data.accent_color
        this.tabTitleFormat = data.tab_title_format
        this.sidebarPosition = data.sidebar_position
        this.sessionTimeout = data.session_timeout
        this.fileAutoSave = data.file_auto_save !== false
        this.fileShowLineNumbers = data.file_show_line_numbers === true
        localStorage.setItem('mebtty-file-auto-save', this.fileAutoSave)
        localStorage.setItem('mebtty-file-show-line-numbers', this.fileShowLineNumbers)
        this.loaded = true
        this.applyAccentColor()
      } catch {
        // Use defaults if fetch fails
        this.loaded = true
      }
    },

    async updateSettings(updates) {
      try {
        const { data } = await api.put('/api/settings', updates)
        this.themeMode = data.theme_mode
        this.accentColor = data.accent_color
        this.tabTitleFormat = data.tab_title_format
        this.sidebarPosition = data.sidebar_position
        this.sessionTimeout = data.session_timeout
        this.fileAutoSave = data.file_auto_save !== false
        this.fileShowLineNumbers = data.file_show_line_numbers === true
        localStorage.setItem('mebtty-file-auto-save', this.fileAutoSave)
        localStorage.setItem('mebtty-file-show-line-numbers', this.fileShowLineNumbers)
        this.applyAccentColor()
      } catch (err) {
        console.error('Failed to update settings:', err)
      }
    },

    applyAccentColor() {
      const root = document.documentElement
      root.style.setProperty('--accent', this.accentColor)
      // Generate a slightly darker hover color
      const hover = this.adjustBrightness(this.accentColor, -20)
      root.style.setProperty('--accent-hover', hover)
      localStorage.setItem('mebtty-accent', this.accentColor)
    },

    adjustBrightness(hex, amount) {
      hex = hex.replace('#', '')
      const num = parseInt(hex, 16)
      let r = Math.min(255, Math.max(0, (num >> 16) + amount))
      let g = Math.min(255, Math.max(0, ((num >> 8) & 0x00ff) + amount))
      let b = Math.min(255, Math.max(0, (num & 0x0000ff) + amount))
      return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')
    },

    toggleStatusBar(visible) {
      this.statusBarVisible = visible
      localStorage.setItem('mebtty-statusbar-visible', visible)
    },

    toggleFileAutoSave(enabled) {
      this.fileAutoSave = enabled
      localStorage.setItem('mebtty-file-auto-save', enabled)
      this.updateSettings({ file_auto_save: enabled })
    },

    toggleFileShowLineNumbers(enabled) {
      this.fileShowLineNumbers = enabled
      localStorage.setItem('mebtty-file-show-line-numbers', enabled)
      this.updateSettings({ file_show_line_numbers: enabled })
    },

    toggleStatusBarItemVisible(key, visible) {
      const item = this.statusBarItems.find((i) => i.key === key)
      if (item) {
        item.visible = visible
        this.saveStatusBarItems()
      }
    },

    updateStatusBarItemPosition(key, position) {
      const item = this.statusBarItems.find((i) => i.key === key)
      if (item) {
        item.position = position
        // Reorder: put at the end of the new position
        const itemsInPosition = this.statusBarItems
          .filter((i) => i.position === position)
          .sort((a, b) => a.order - b.order)
        item.order = itemsInPosition.length > 1 ? itemsInPosition[itemsInPosition.length - 1].order + 1 : 0
        this.saveStatusBarItems()
      }
    },

    reorderStatusBarItems(fromIndex, toIndex) {
      const [moved] = this.statusBarItems.splice(fromIndex, 1)
      this.statusBarItems.splice(toIndex, 0, moved)
      // Recalculate order within each position
      let leftOrder = 0
      let rightOrder = 0
      for (const item of this.statusBarItems) {
        if (item.position === 'left') {
          item.order = leftOrder++
        } else {
          item.order = rightOrder++
        }
      }
      this.saveStatusBarItems()
    },

    saveStatusBarItems() {
      localStorage.setItem('mebtty-statusbar-items', JSON.stringify(this.statusBarItems))
    },

    formatTabTitle(template, shell, index, title, user = '', cwd = '') {
      const shortCwd = cwd
        ? (cwd.length > 20 ? '...' + cwd.slice(-17) : cwd)
        : '~'
      return template
        .replace('{shell}', shell?.split('/').pop() || 'bash')
        .replace('{index}', index)
        .replace('{title}', title || '')
        .replace('{user}', user || 'user')
        .replace('{cwd}', shortCwd)
    }
  }
})
