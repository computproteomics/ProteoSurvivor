import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// VITE_BASE_PATH sets the public base URL for the built assets.
// Use this when the app is served under a sub-path behind a reverse proxy,
// e.g. VITE_BASE_PATH=/ProteoSurviver/ when nginx proxies /ProteoSurviver/ to
// the container.  Defaults to / for local development and direct container use.
const base = process.env.VITE_BASE_PATH || '/';

const proxyConfig = {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
  '/admin': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
};

export default defineConfig({
  base,
  plugins: [react()],
  server: {
    port: 3000,
    allowedHosts: ['computproteomics.bmb.sdu.dk'],
    proxy: proxyConfig,
  },
  preview: {
    port: 3000,
    allowedHosts: ['computproteomics.bmb.sdu.dk'],
    proxy: proxyConfig,
  },
});
