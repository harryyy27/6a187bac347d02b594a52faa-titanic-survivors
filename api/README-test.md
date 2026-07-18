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

- `.env.test` supplies safe, predictable defaults for test runs (`ENV`,
  `LOG_LEVEL`, `PORT`) so tests never depend on a developer's local
  environment.
- `tests/conftest.py` provides an autouse fixture that snapshots
  `os.environ` before each test and restores it afterward, so no test can
  leak environment mutations into another.
- The same `conftest.py` also installs lightweight stub modules for heavy
  production packages (fastapi, pandas, xgboost, ...) into `sys.modules`
  so incidental import resolution stays fast without those packages being
  installed in the test image.

## Dependency isolation

Test-time dependencies are restricted to exactly what is declared in
`requirements-test.txt` (currently just `pytest`) to keep the test image
minimal. Do not add a production package to this file unless a test
directly imports and asserts against it -- stub it instead.
