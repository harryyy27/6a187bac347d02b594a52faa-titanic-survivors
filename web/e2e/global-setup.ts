import { fileURLToPath } from 'node:url';

import { createServer, type ViteDevServer } from 'vite';

declare global {
  // eslint-disable-next-line no-var
  var __VITE_SERVER__: ViteDevServer | undefined;
}

/**
 * Starts the Vite dev server programmatically (via Vite's JS API) using the
 * Playwright-only config, and stores the running instance on `globalThis`
 * so global-teardown.ts can close it. Starting the server in-process (rather
 * than as a webServer subprocess) puts Chromium and the dev server in the
 * same process group, which this sandbox requires for the browser to reach
 * the server at all.
 */
export default async function globalSetup() {
  const server = await createServer({
    configFile: fileURLToPath(new URL('../vite.playwright.config.ts', import.meta.url)),
    mode: 'test',
  });

  await server.listen();
  globalThis.__VITE_SERVER__ = server;
}
