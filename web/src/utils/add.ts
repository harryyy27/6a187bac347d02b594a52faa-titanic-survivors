/**
 * Minimal, deterministic, project-owned function used to exercise the
 * test runner end-to-end (import resolution, TS transpilation, timeout
 * wrapper) without depending on any third-party package.
 */
export function add(a: number, b: number) {
  return a + b;
}
