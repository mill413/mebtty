import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backendPort = process.env.MEBTTY_PORT || '18888'
const backendUrl = process.env.MEBTTY_BACKEND_URL || `http://localhost:${backendPort}`
const frontendPort = Number(process.env.MEBTTY_DEV_FRONTEND_PORT || 3000)

export default defineConfig({
  plugins: [vue()],
  server: {
    port: frontendPort,
    proxy: {
      '/api': {
        target: backendUrl,
        ws: true,
        changeOrigin: true
      }
    }
  }
})
