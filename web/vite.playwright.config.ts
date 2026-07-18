import { defineConfig, mergeConfig, type ConfigEnv, type UserConfig } from 'vite';

import baseConfig from './vite.config';

/**
 * Test-only Vite config for Playwright E2E runs. Extends the base config
 * (vite.config.ts is left untouched) and only opens up the allowed-hosts
 * restriction so Playwright's Chromium, running inside this sandbox, can
 * reach the dev server started programmatically from e2e/global-setup.ts.
 */
export default defineConfig(async (env: ConfigEnv) => {
  const resolvedBase = typeof baseConfig === 'function' ? await baseConfig(env) : baseConfig;

  return mergeConfig(resolvedBase as UserConfig, {
    server: {
      strictPort: false,
      allowedHosts: true,
    },
  });
});
