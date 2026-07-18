/**
 * Retrieves the Vite dev server instance stored on `globalThis` by
 * global-setup.ts and closes it.
 */
export default async function globalTeardown() {
  const server = globalThis.__VITE_SERVER__;
  if (server) {
    await server.close();
    globalThis.__VITE_SERVER__ = undefined;
  }
}
