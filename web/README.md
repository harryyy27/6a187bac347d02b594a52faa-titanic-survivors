# web

Browser SPA for Titanic Survivors — a Vite + React + TypeScript single-page
app that renders a Titanic-themed passenger form, calls the `api` component's
prediction endpoint, and plays a survive/not-survive Lottie animation based
on the result.

## Structure

```
web/
  src/
    assets/
      animations/   Lottie JSON animation files (survive.json, not_survive.json, ...)
      react.svg
    components/     Shared UI components (e.g. LottiePlayer)
    lib/             Cross-cutting utilities (e.g. react-hook-form + zod wiring)
    pages/           Routed pages, if/when routing is introduced
    services/        API/data access (Axios instance, endpoint calls)
    store/           Zustand stores
    styles/          Global stylesheet(s)
    utils/           Small, deterministic, project-owned helpers
  tests/
    unit/            Vitest unit tests
    setup.ts         Global test setup/cleanup
    testWrapperTimeout.ts  Shared per-test timeout wrapper
  e2e/               Playwright end-to-end tests + global setup/teardown
  public/            Static assets served as-is
```

## Environment variables

All configuration is read via `import.meta.env`, so every variable consumed
by the app **must** be prefixed with `VITE_` (Vite only exposes prefixed
variables to client code). Variables are centralized in `.env` (local/dev
defaults) and `.env.test` (test-only overrides):

- `VITE_APP_NAME` — display name shown in the UI.
- `VITE_API_BASE_URL` — base URL of the `api` component the SPA calls.
- `VITE_ENABLE_MOCKS` — toggles client-side mock responses.
- `VITE_ALLOWED_HOST_SUFFIX` — wildcard host suffix allowed by the Vite dev
  server in preview environments.

## npm scripts

- `dev` — start the Vite dev server.
- `build` — type-check and build a production bundle.
- `preview` — serve the production build locally.
- `lint` — run ESLint over `.ts`/`.tsx` sources.
- `format` — run Prettier (write mode) over source and test files.
- `typecheck` — run the TypeScript compiler in `--noEmit` mode.
- `test` — run the Vitest unit test suite (non-watch, CI mode).
- `test:e2e` — run the Playwright end-to-end suite.
