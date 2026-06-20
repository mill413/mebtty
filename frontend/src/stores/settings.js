import { defineStore } from 'pinia'
import api from '../services/api'

export const DEFAULT_CUSTOM_THEME = {
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

export const CUSTOM_THEME_FIELDS = [
  { key: 'bg', label: 'settings.themeBg' },
  { key: 'bgDeep', label: 'settings.themeBgDeep' },
  { key: 'surface', label: 'settings.themeSurface' },
  { key: 'surfaceHover', label: 'settings.themeSurfaceHover' },
  { key: 'overlay', label: 'settings.themeOverlay' },
  { key: 'text', label: 'settings.themeText' },
  { key: 'subtext', label: 'settings.themeSubtext' },
  { key: 'border', label: 'settings.themeBorder' },
  { key: 'accent', label: 'settings.themeAccent' }
]

export const CUSTOM_THEME_MODES = ['dark', 'light']

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

const HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/

function normalizeHexColor(color, fallback) {
  return typeof color === 'string' && HEX_COLOR_RE.test(color) ? color.toLowerCase() : fallback
}

function normalizeCustomTheme(rawTheme) {
  const theme = rawTheme && typeof rawTheme === 'object' ? rawTheme : {}
  return CUSTOM_THEME_MODES.reduce((next, mode) => {
    const source = theme[mode] && typeof theme[mode] === 'object' ? theme[mode] : {}
    next[mode] = CUSTOM_THEME_FIELDS.reduce((palette, field) => {
      const fallback = DEFAULT_CUSTOM_THEME[mode][field.key]
      palette[field.key] = normalizeHexColor(source[field.key], fallback)
      return palette
    }, {})
    return next
  }, {})
}

function parseCustomTheme(raw) {
  if (!raw) return cloneDefaultCustomTheme()

  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!parsed || typeof parsed !== 'object') return cloneDefaultCustomTheme()

    if (parsed.dark || parsed.light) {
      return normalizeCustomTheme(parsed)
    }

    return normalizeCustomTheme({
      dark: { ...DEFAULT_CUSTOM_THEME.dark, ...parsed },
      light: { ...DEFAULT_CUSTOM_THEME.light }
    })
  } catch {
    return cloneDefaultCustomTheme()
  }
}

function parsePluginSettings(raw) {
  if (!raw) return {}

  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
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
    pluginSettings: parsePluginSettings(localStorage.getItem('mebtty-plugin-settings')),
    statusBarVisible: localStorage.getItem('mebtty-statusbar-visible') !== 'false',
    statusBarItems: JSON.parse(localStorage.getItem('mebtty-statusbar-items') || '[{"key":"shell","visible":false,"position":"left","order":0},{"key":"status","visible":false,"position":"left","order":1},{"key":"connection","visible":true,"position":"right","order":0}]'),
    loaded: false
  }),

  getters: {
    sidebarOnLeft: (state) => state.sidebarPosition === 'left',
    resolvedThemeAccent: (state) => {
      const mode = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'
      return state.customThemeEnabled ? state.customTheme[mode]?.accent : state.accentColor
    },
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
        this.pluginSettings = parsePluginSettings(data.plugin_settings)
        this.saveLocalSettings()
        this.loaded = true
        this.applyThemeColors()
      } catch (err) {
        // Unauthenticated startup can happen on the login page; fetch again after login.
        this.loaded = err?.response?.status !== 401
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
        this.pluginSettings = parsePluginSettings(data.plugin_settings)
        this.saveLocalSettings()
        this.applyThemeColors()
      } catch (err) {
        console.error('Failed to update settings:', err)
      }
    },

    saveLocalSettings() {
      localStorage.setItem('mebtty-theme', this.themeMode)
      localStorage.setItem('mebtty-accent', this.accentColor)
      localStorage.setItem('mebtty-custom-theme-enabled', this.customThemeEnabled)
      localStorage.setItem('mebtty-custom-theme', JSON.stringify(this.customTheme))
      localStorage.setItem('mebtty-file-auto-save', this.fileAutoSave)
      localStorage.setItem('mebtty-file-show-line-numbers', this.fileShowLineNumbers)
      localStorage.setItem('mebtty-plugin-settings', JSON.stringify(this.pluginSettings))
    },

    applyAccentColor() {
      this.applyThemeColors()
    },

    applyThemeColors() {
      const root = document.documentElement
      for (const variable of Object.values(CUSTOM_THEME_VARS)) {
        root.style.removeProperty(variable)
      }
      root.style.removeProperty('--fg')
      root.style.removeProperty('--accent-hover')

      if (this.customThemeEnabled) {
        const mode = this.currentResolvedThemeMode()
        const palette = this.customTheme[mode] || DEFAULT_CUSTOM_THEME[mode]
        for (const [key, variable] of Object.entries(CUSTOM_THEME_VARS)) {
          root.style.setProperty(variable, palette[key] || DEFAULT_CUSTOM_THEME[mode][key])
        }
        root.style.setProperty('--fg', palette.text || DEFAULT_CUSTOM_THEME[mode].text)
      } else {
        root.style.setProperty('--accent', this.accentColor)
      }

      const mode = this.currentResolvedThemeMode()
      const accent = this.customThemeEnabled ? this.customTheme[mode]?.accent : this.accentColor
      const hover = this.adjustBrightness(accent, -20)
      root.style.setProperty('--accent-hover', hover)
      this.saveLocalSettings()
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

    previewAccentColor(color) {
      const normalized = normalizeHexColor(color, null)
      if (!normalized) return

      if (this.customThemeEnabled) {
        this.previewCustomThemeColor(this.currentResolvedThemeMode(), 'accent', normalized)
      } else {
        this.accentColor = normalized
        this.applyThemeColors()
      }
    },

    saveAccentColor(color) {
      const normalized = normalizeHexColor(color, null)
      if (!normalized) return

      if (this.customThemeEnabled) {
        this.saveCustomThemeColor(this.currentResolvedThemeMode(), 'accent', normalized)
      } else {
        this.accentColor = normalized
        this.applyThemeColors()
        this.updateSettings({ accent_color: normalized })
      }
    },

    previewCustomThemeColor(mode, key, color) {
      if (!Object.hasOwn(DEFAULT_CUSTOM_THEME, mode)) return
      if (!Object.hasOwn(CUSTOM_THEME_VARS, key)) return
      const normalized = normalizeHexColor(color, null)
      if (!normalized) return

      this.customTheme = {
        ...this.customTheme,
        [mode]: { ...this.customTheme[mode], [key]: normalized }
      }
      this.applyThemeColors()
    },

    saveCustomThemeColor(mode, key, color) {
      this.previewCustomThemeColor(mode, key, color)
      this.updateSettings({
        custom_theme: JSON.stringify(this.customTheme)
      })
    },

    resetCustomTheme() {
      this.customTheme = cloneDefaultCustomTheme()
      this.accentColor = DEFAULT_CUSTOM_THEME.dark.accent
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

    updatePluginSettings(settings) {
      this.pluginSettings = settings && typeof settings === 'object' ? settings : {}
      this.saveLocalSettings()
      this.updateSettings({ plugin_settings: JSON.stringify(this.pluginSettings) })
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
