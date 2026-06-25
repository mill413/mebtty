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
  },
  build: {
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('/xterm') || id.includes('xterm-addon-')) {
            return 'xterm'
          }
          if (
            id.includes('/vue') ||
            id.includes('/pinia') ||
            id.includes('/vue-router') ||
            id.includes('/vue-i18n')
          ) {
            return 'vue-vendor'
          }
          return 'vendor'
        }
      }
    }
  }
})
