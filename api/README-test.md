# api tests

Notes specific to the test harness for this component.

## Timeout wrapper

Every new test function must be decorated with `testWrapperTimeout` from
`tests/testWrapperTimeout.py`, either bare (`@testWrapperTimeout`, default
10s timeout) or parameterized (`@testWrapperTimeout(timeout=5)`). The
decorator runs the test in a background thread and raises `TimeoutError`
(naming the test, its file, and its starting line) if it exceeds the
timeout, preventing a hung test from stalling the whole suite.

## Environment isolation

- `.env.test` documents safe, predictable defaults (`ENV`, `LOG_LEVEL`,
  `PORT`) for test runs. Nothing loads it automatically today (it is copied
  into the test image but not sourced as `.env`), so `app.core.config`
  falls back to its own field defaults unless the harness injects these as
  real process environment variables; `AppSettings.env`'s validator accepts
  both `dev/staging/prod` and `test/testing` for this reason.
- `tests/conftest.py` provides an autouse fixture that snapshots
  `os.environ` before each test and restores it afterward, so no test can
  leak environment mutations into another.

## Dependency isolation and stubbing scope

Test-time dependencies are restricted to exactly what `requirements-test.txt`
declares: `pytest`, plus the web framework itself (`fastapi`, `starlette`,
`pydantic`, `python-dotenv`, `orjson`, `uvicorn`) and HTTP test clients
(`httpx`, `requests`). These are installed for real because the "API
Service Foundation" tests exercise our own config/logging/error/routing
code running *on top of* that framework -- they are not asserting on
fastapi/pydantic's own behaviour, they are asserting on what our app does
with it (response schemas, CORS headers, error payloads).

Heavy, unrelated production packages used only by the pre-existing predict
feature (`pandas`, `numpy`, `scikit-learn`, `xgboost`, `joblib`,
`aiofiles`) are **not** installed here, because no test in this suite calls
their functions in an assertion. Importing `app.main` still transitively
imports them (via `app.api.routes` / `app.ml.model`), so
`tests/integration/conftest.py` provides a `stub_unused_ml_dependencies`
fixture that installs empty stand-in modules into `sys.modules` via
`monkeypatch` (auto-restored after each test). It is scoped to
`tests/integration/` only (a directory-scoped `conftest.py`, pytest's
built-in scoping mechanism) -- `tests/unit/` never needs it and never sees
it. Tests that request this fixture must import `app.main` (and anything
that transitively imports it) *inside* the test/fixture body, after the
fixture has patched `sys.modules`, not at module import time.

Do not add a production package to `requirements-test.txt` unless a test
directly imports and asserts against it -- stub it instead.
