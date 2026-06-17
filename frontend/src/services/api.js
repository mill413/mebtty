import axios from 'axios'
import router from '../router'

const api = axios.create({
  baseURL: '',
  timeout: 15000
})

let refreshPromise = null

function getAccessToken() {
  return localStorage.getItem('access_token')
}

function getRefreshToken() {
  return localStorage.getItem('refresh_token')
}

function storeTokens(data) {
  localStorage.setItem('access_token', data.access_token)
  if (data.refresh_token) {
    localStorage.setItem('refresh_token', data.refresh_token)
  }
}

function clearAuthAndRedirect() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  if (router.currentRoute.value.name !== 'Login') {
    router.push('/login')
  }
}

function shouldSkipRefresh(config) {
  const url = config?.url || ''
  return url.includes('/api/auth/login') ||
    url.includes('/api/auth/register') ||
    url.includes('/api/auth/refresh')
}

async function refreshAccessToken() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) throw new Error('Missing refresh token')

  if (!refreshPromise) {
    refreshPromise = axios.post('/api/auth/refresh', {
      refresh_token: refreshToken
    }, {
      timeout: 15000
    }).then((response) => {
      storeTokens(response.data)
      return response.data.access_token
    }).finally(() => {
      refreshPromise = null
    })
  }

  return refreshPromise
}

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !shouldSkipRefresh(originalRequest)) {
      originalRequest._retry = true

      try {
        const accessToken = await refreshAccessToken()
        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers.Authorization = `Bearer ${accessToken}`
        return api(originalRequest)
      } catch {
        clearAuthAndRedirect()
      }
    } else if (error.response?.status === 401 && !shouldSkipRefresh(originalRequest)) {
      clearAuthAndRedirect()
    }

    return Promise.reject(error)
  }
)

export default api
