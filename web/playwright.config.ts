import { defineConfig } from '@playwright/test';

/**
 * Playwright E2E config. The dev server is started programmatically in
 * e2e/global-setup.ts (Vite's JS API) rather than via Playwright's
 * `webServer` option, so no webServer block is configured here.
 */
export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  globalTeardown: './e2e/global-teardown.ts',
  use: {
    baseURL: 'http://localhost:5173',
  },
});
