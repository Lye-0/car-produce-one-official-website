import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
const base = (process.env.PAGES_BASE_PATH || '/').replace(/\/+$/, '') + '/';
if (!base.startsWith('/') || base.startsWith('//') || /[?#]/.test(base))
  throw new Error(
    'PAGES_BASE_PATH must be an absolute URL path such as /my-repo/.',
  );
export default defineConfig({
  base,
  plugins: [react()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true },
});
