import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/static/dist/',
  build: {
    outDir: '../main/static/dist',
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: 'src/main.jsx',
    },
  },
  server: {
    host: 'localhost',
    port: 5173,
    cors: true,
  },
})
