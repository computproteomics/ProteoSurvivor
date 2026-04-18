import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// VITE_BASE_PATH sets the public base URL for the built assets.
// Use this when the app is served under a sub-path behind a reverse proxy,
// e.g. VITE_BASE_PATH=/ProteoSurviver/ when nginx proxies /ProteoSurviver/ to
// the container.  Defaults to / for local development and direct container use.
const base = process.env.VITE_BASE_PATH || '/';

// Strip trailing slash: '' for '/', '/ProteoSurviver' for '/ProteoSurviver/'.
// The proxy keys must include the base prefix so that nginx can forward
// requests without stripping the prefix (proxy_pass without trailing slash).
const baseStripped = base.replace(/\/$/, '');

// Rewrite function that removes the base prefix from the request path so
// Django only sees /api/... or /admin/... regardless of the sub-path.
const rewrite = baseStripped
  ? (path) => path.slice(baseStripped.length)
  : undefined;

const proxyEntry = (opts) => ({ target: 'http://localhost:8000', changeOrigin: true, rewrite, ...opts });

const proxyConfig = {
  [`${baseStripped}/api`]: proxyEntry(),
  [`${baseStripped}/admin`]: proxyEntry(),
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
