import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const base = process.env.DISKTRACKER_BASE_PATH || '/';

export default defineConfig({
  base,
  plugins: [react()],
  server: {
    allowedHosts: ['code.diyhub.dev'],
    proxy: {
      [`${base}api`]: {
        target: process.env.DISKTRACKER_API_ORIGIN ?? 'http://127.0.0.1:8000',
        rewrite: path => path.slice(base.length - 1),
      },
    },
  },
});
