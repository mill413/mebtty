import { defineStore } from 'pinia'
import api from '../services/api'

const DEFAULT_CUSTOM_THEME = {
  dark: {
    bg: '#1e1e2e',
    bgDeep: '#181825',
    surface: '#313244',
    surfaceHover: '#3b3d52',
    overlay: '#45475a',
    text: '#cdd6f4',
    subtext: '#a6adc8',
    border: '#585b70',
    accent: '#7c3aed'
  },
  light: {
    bg: '#eff1f5',
    bgDeep: '#e6e9ef',
    surface: '#ccd0da',
    surfaceHover: '#bcc0cc',
    overlay: '#acb0be',
    text: '#4c4f69',
    subtext: '#6c6f85',
    border: '#9ca0b0',
    accent: '#7c3aed'
  }
}

const CUSTOM_THEME_VARS = {
  bg: '--bg',
  bgDeep: '--bg-deep',
  surface: '--surface',
  surfaceHover: '--surface-hover',
  overlay: '--overlay',
  text: '--text',
  subtext: '--subtext',
  border: '--border',
  accent: '--accent'
}

function parseCustomTheme(raw) {
  if (!raw) return cloneDefaultCustomTheme()

  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!parsed || typeof parsed !== 'object') return cloneDefaultCustomTheme()

    if (parsed.dark || parsed.light) {
      return {
        dark: { ...DEFAULT_CUSTOM_THEME.dark, ...(parsed.dark || {}) },
        light: { ...DEFAULT_CUSTOM_THEME.light, ...(parsed.light || {}) }
      }
    }

    return {
      dark: { ...DEFAULT_CUSTOM_THEME.dark, ...parsed },
      light: { ...DEFAULT_CUSTOM_THEME.light }
    }
  } catch {
    return cloneDefaultCustomTheme()
  }
}

function cloneDefaultCustomTheme() {
  return {
    dark: { ...DEFAULT_CUSTOM_THEME.dark },
    light: { ...DEFAULT_CUSTOM_THEME.light }
  }
}

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    themeMode: localStorage.getItem('mebtty-theme') || 'system',
    accentColor: localStorage.getItem('mebtty-accent') || '#7c3aed',
    customThemeEnabled: localStorage.getItem('mebtty-custom-theme-enabled') === 'true',
    customTheme: parseCustomTheme(localStorage.getItem('mebtty-custom-theme')),
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
        this.customThemeEnabled = data.custom_theme_enabled === true
        this.customTheme = parseCustomTheme(data.custom_theme)
        this.tabTitleFormat = data.tab_title_format
        this.sidebarPosition = data.sidebar_position
        this.sessionTimeout = data.session_timeout
        this.fileAutoSave = data.file_auto_save !== false
        this.fileShowLineNumbers = data.file_show_line_numbers === true
        localStorage.setItem('mebtty-file-auto-save', this.fileAutoSave)
        localStorage.setItem('mebtty-file-show-line-numbers', this.fileShowLineNumbers)
        this.loaded = true
        this.applyThemeColors()
      } catch {
        // Use defaults if fetch fails
        this.loaded = true
        this.applyThemeColors()
      }
    },

    async updateSettings(updates) {
      try {
        const { data } = await api.put('/api/settings', updates)
        this.themeMode = data.theme_mode
        this.accentColor = data.accent_color
        this.customThemeEnabled = data.custom_theme_enabled === true
        this.customTheme = parseCustomTheme(data.custom_theme)
        this.tabTitleFormat = data.tab_title_format
        this.sidebarPosition = data.sidebar_position
        this.sessionTimeout = data.session_timeout
        this.fileAutoSave = data.file_auto_save !== false
        this.fileShowLineNumbers = data.file_show_line_numbers === true
        localStorage.setItem('mebtty-file-auto-save', this.fileAutoSave)
        localStorage.setItem('mebtty-file-show-line-numbers', this.fileShowLineNumbers)
        this.applyThemeColors()
      } catch (err) {
        console.error('Failed to update settings:', err)
      }
    },

    applyAccentColor() {
      this.applyThemeColors()
    },

    applyThemeColors() {
      const root = document.documentElement
      for (const variable of Object.values(CUSTOM_THEME_VARS)) {
        root.style.removeProperty(variable)
      }
      root.style.removeProperty('--accent-hover')

      if (this.customThemeEnabled) {
        const mode = this.currentResolvedThemeMode()
        const palette = this.customTheme[mode] || DEFAULT_CUSTOM_THEME[mode]
        for (const [key, variable] of Object.entries(CUSTOM_THEME_VARS)) {
          root.style.setProperty(variable, palette[key] || DEFAULT_CUSTOM_THEME[mode][key])
        }
      } else {
        root.style.setProperty('--accent', this.accentColor)
      }

      const mode = this.currentResolvedThemeMode()
      const accent = this.customThemeEnabled ? this.customTheme[mode]?.accent : this.accentColor
      const hover = this.adjustBrightness(accent, -20)
      root.style.setProperty('--accent-hover', hover)
      localStorage.setItem('mebtty-accent', this.accentColor)
      localStorage.setItem('mebtty-custom-theme-enabled', this.customThemeEnabled)
      localStorage.setItem('mebtty-custom-theme', JSON.stringify(this.customTheme))
    },

    adjustBrightness(hex, amount) {
      hex = hex.replace('#', '')
      const num = parseInt(hex, 16)
      let r = Math.min(255, Math.max(0, (num >> 16) + amount))
      let g = Math.min(255, Math.max(0, ((num >> 8) & 0x00ff) + amount))
      let b = Math.min(255, Math.max(0, (num & 0x0000ff) + amount))
      return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')
    },

    currentResolvedThemeMode() {
      return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'
    },

    toggleCustomTheme(enabled) {
      this.customThemeEnabled = enabled
      this.applyThemeColors()
      this.updateSettings({ custom_theme_enabled: enabled })
    },

    updateCustomThemeColor(mode, key, color) {
      if (!Object.hasOwn(DEFAULT_CUSTOM_THEME, mode)) return
      if (!Object.hasOwn(CUSTOM_THEME_VARS, key)) return
      this.customTheme = {
        ...this.customTheme,
        [mode]: { ...this.customTheme[mode], [key]: color }
      }
      if (key === 'accent' && mode === this.currentResolvedThemeMode()) this.accentColor = color
      this.applyThemeColors()
      this.updateSettings({
        custom_theme: JSON.stringify(this.customTheme),
        accent_color: this.accentColor
      })
    },

    resetCustomTheme() {
      this.customTheme = cloneDefaultCustomTheme()
      this.accentColor = DEFAULT_CUSTOM_THEME[this.currentResolvedThemeMode()].accent
      this.applyThemeColors()
      this.updateSettings({
        custom_theme: JSON.stringify(this.customTheme),
        accent_color: this.accentColor
      })
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
      const displayCwd = this.formatCwd(cwd, user)
      return template
        .replace('{shell}', shell?.split('/').pop() || 'bash')
        .replace('{index}', index)
        .replace('{title}', title || '')
        .replace('{user}', user || 'user')
        .replace('{cwd}', displayCwd)
    },

    formatCwd(cwd = '', user = '') {
      const normalized = cwd.trim().replace(/\/+$/, '') || '~'
      const homeCandidates = ['~', '/root']
      if (user) homeCandidates.push(`/home/${user}`)

      if (homeCandidates.includes(normalized)) return '~'

      const parts = normalized.split('/').filter(Boolean)
      return parts.at(-1) || '~'
    }
  }
})
