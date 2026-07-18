/**
 * Reusable test wrapper that enforces a default 10-second limit per test
 * and throws a detailed error (including the test name and callsite) if
 * the wrapped function does not settle in time.
 */
export function testWrapperTimeout(fn: () => unknown | Promise<unknown>, timeoutMs = 10000) {
  return async function wrapped(this: unknown, ...args: unknown[]) {
    const testName = (wrapped as { testName?: string }).testName || '(unnamed test)';
    const fileHint =
      new Error().stack?.split('\n').find((l) => l.includes('tests/')) || '(file: unknown)';
    let timer: ReturnType<typeof setTimeout>;
    try {
      await Promise.race([
        Promise.resolve(fn.apply(this, args)),
        new Promise((_, reject) => {
          timer = setTimeout(() => {
            const message = `Test timed out after ${timeoutMs}ms: ${testName} at ${fileHint}`;
            reject(new Error(message));
          }, timeoutMs);
        }),
      ]);
    } finally {
      if (timer!) clearTimeout(timer);
    }
  };
}
