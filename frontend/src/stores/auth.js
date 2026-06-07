import { defineStore } from 'pinia'
import api from '../services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('access_token') || null,
    refreshToken: localStorage.getItem('refresh_token') || null
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.user?.is_admin === true,
    username: (state) => state.user?.username || '',
    avatar: (state) => state.user?.avatar ? `/api/auth/avatar/${state.user.avatar}` : null
  },

  actions: {
    async login(username, password) {
      const { data } = await api.post('/api/auth/login', { username, password })
      this.token = data.access_token
      this.refreshToken = data.refresh_token
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      await this.fetchUser()
    },

    async register(username, password) {
      const { data } = await api.post('/api/auth/register', { username, password })
      this.token = data.access_token
      this.refreshToken = data.refresh_token
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      await this.fetchUser()
    },

    async fetchUser() {
      try {
        const { data } = await api.get('/api/auth/me')
        this.user = data
      } catch {
        this.logout()
      }
    },

    async refreshAuthToken() {
      if (!this.refreshToken) return
      try {
        const { data } = await api.post('/api/auth/refresh', {
          refresh_token: this.refreshToken
        })
        this.token = data.access_token
        localStorage.setItem('access_token', data.access_token)
        if (data.refresh_token) {
          this.refreshToken = data.refresh_token
          localStorage.setItem('refresh_token', data.refresh_token)
        }
      } catch {
        this.logout()
      }
    },

    logout() {
      this.user = null
      this.token = null
      this.refreshToken = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  }
})
