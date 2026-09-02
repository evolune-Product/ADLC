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
    // Improve chunk splitting for better caching and parallel loading
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Vendor chunks - split large dependencies for better caching
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
              return 'react-vendor'
            }
            if (id.includes('@tanstack/react-query')) {
              return 'query-vendor'
            }
            if (id.includes('lucide-react') || id.includes('sonner')) {
              return 'ui-vendor'
            }
            if (id.includes('react-hook-form') || id.includes('zod')) {
              return 'form-vendor'
            }
            if (id.includes('@uiw/react-md-editor') || id.includes('rehype')) {
              return 'markdown-vendor'
            }
            // Three.js is already lazy-loaded, but group it separately
            if (id.includes('three')) {
              return 'three-vendor'
            }
            // Other node_modules go into a general vendor chunk
            return 'vendor'
          }
        },
        // Better asset naming for cache busting
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
    // Increase chunk size warning limit (we know three.js is large)
    chunkSizeWarningLimit: 1000,
    // Enable minification
    minify: 'esbuild',
    // Target modern browsers for smaller output
    target: 'esnext',
  },
})
