import { defineConfig } from 'vite';
export default defineConfig({ server: { proxy: { '/api/health': {
  target: process.env.APITEST_BACKEND_URL || 'http://127.0.0.1:8111', rewrite: () => '/health'
} } } });
