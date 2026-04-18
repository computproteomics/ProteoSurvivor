import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

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
