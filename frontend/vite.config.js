import fs from 'node:fs/promises'
import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

function publishDistPermissions() {
  async function chmodRecursive(targetPath) {
    const stats = await fs.stat(targetPath)
    await fs.chmod(targetPath, stats.isDirectory() ? 0o755 : 0o644)
    if (!stats.isDirectory()) return
    const entries = await fs.readdir(targetPath)
    await Promise.all(entries.map((entry) => chmodRecursive(path.join(targetPath, entry))))
  }

  return {
    name: 'publish-dist-permissions',
    apply: 'build',
    async closeBundle() {
      const distPath = path.resolve(process.cwd(), 'dist')
      await chmodRecursive(distPath)
    },
  }
}

export default defineConfig({
  plugins: [react(), publishDistPermissions()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('recharts')) return 'vendor-charts'
          if (id.includes('lucide-react')) return 'vendor-icons'
          return 'vendor'
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: true,
    proxy: {
      '/api': {
        rewrite: (path) => path.replace(/^\/api/, ''),
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
