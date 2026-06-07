import { defineStore } from 'pinia'

const STORAGE_KEY = 'webtty-theme'
const MODES = ['system', 'dark', 'light']

const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

function getSystemTheme() {
  return mediaQuery.matches ? 'dark' : 'light'
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    // mode is what the user chose: 'system' | 'dark' | 'light'
    mode: localStorage.getItem(STORAGE_KEY) || 'system',
    // resolved is the actual effective theme: 'dark' | 'light'
    resolved: 'dark'
  }),

  getters: {
    isDark: (state) => state.resolved === 'dark',
    isSystem: (state) => state.mode === 'system'
  },

  actions: {
    toggle() {
      const idx = MODES.indexOf(this.mode)
      this.mode = MODES[(idx + 1) % MODES.length]
      this.apply()
    },

    setMode(mode) {
      if (!MODES.includes(mode)) return
      this.mode = mode
      this.apply()
    },

    apply() {
      localStorage.setItem(STORAGE_KEY, this.mode)
      this.resolved = this.mode === 'system' ? getSystemTheme() : this.mode
      document.documentElement.setAttribute('data-theme', this.resolved)
    },

    onSystemThemeChange() {
      if (this.mode === 'system') {
        this.apply()
      }
    }
  }
})

export { mediaQuery }
