import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The browser calls /api/... on the SAME origin as the page (no CORS issues,
    // the HttpOnly refresh cookie just works). Vite forwards it to FastAPI.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        xfwd: true, // send X-Forwarded-For so the backend sees the real client IP
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
