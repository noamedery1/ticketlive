import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, proxy the API so the app is same-origin (no CORS) like production.
const api = { target: process.env.API_TARGET || 'http://localhost:8000', changeOrigin: true }

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/teams': api, '/health': api } },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
  },
  base: '/',
})
