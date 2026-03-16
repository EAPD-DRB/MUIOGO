import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  base: '/',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      // Proxy API requests to the Python backend during development
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      // Proxy other unknown requests to backend if needed (e.g. upload)
      '/upload': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      }
    }
  }
});
