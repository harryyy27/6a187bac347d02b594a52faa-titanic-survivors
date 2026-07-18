import { afterEach, vi } from 'vitest';

// Guarantee clean state between tests: reset mocks and modules so no
// production code path leaks state or double-registers side effects.
afterEach(() => {
  vi.clearAllMocks();
  vi.resetModules();
  vi.unstubAllGlobals?.();
});
