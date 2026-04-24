import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { copyFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

// Copies dist/index.html -> dist/404.html after the build so static hosts
// (Replit Static, GitHub Pages, etc.) serve the SPA shell for unknown paths.
// React Router then takes over and renders the correct route on a hard
// navigation or page refresh, instead of the host returning 404.
function spaFallback404() {
  return {
    name: 'spa-fallback-404',
    apply: 'build' as const,
    closeBundle() {
      const outDir = resolve(__dirname, '../dist')
      const indexPath = resolve(outDir, 'index.html')
      const fallbackPath = resolve(outDir, '404.html')
      if (existsSync(indexPath)) {
        copyFileSync(indexPath, fallbackPath)
      }
    },
  }
}

export default defineConfig({
  plugins: [react(), tailwindcss(), spaFallback404()],
  server: {
    host: '0.0.0.0',
    port: 5000,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 800,
  },
})
