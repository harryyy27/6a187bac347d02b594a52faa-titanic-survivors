import { fileURLToPath } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const allowedHostSuffix = env.VITE_ALLOWED_HOST_SUFFIX || process.env.VITE_ALLOWED_HOST_SUFFIX;

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: true,
      strictPort: true,
      port: 5173,
      // Allow wildcard subdomains of the preview base domain plus the
      // in-cluster service hostname, without disabling host checking.
      allowedHosts: [
        allowedHostSuffix,
        'appbuilder-appbuilder-frontend.default.svc.cluster.local',
      ].filter((host): host is string => Boolean(host)),
      hmr: {
        protocol: 'wss',
        clientPort: 443,
      },
    },
  };
});
