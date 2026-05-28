import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      '/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/loans': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/repayments': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/users': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})