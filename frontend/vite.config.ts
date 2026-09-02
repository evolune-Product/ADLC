import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  optimizeDeps: {
    include: ['@uiw/react-md-editor', 'rehype-sanitize'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Split three.js into its own chunk (it's large and already
          // lazy-loaded separately from the rest of the app) — leave
          // everything else to Rollup's own dependency-graph-aware default
          // chunking. A broad id.includes('react') check here previously
          // swallowed @tanstack/react-query, lucide-react and
          // react-hook-form too (their paths all contain "react"), which
          // produced a React error #130 (element type undefined) on
          // /marketplace in production.
          if (id.includes('node_modules') && id.includes('three')) {
            return 'three-vendor'
          }
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
})
