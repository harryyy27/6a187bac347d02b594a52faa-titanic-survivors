# File Locking (MANDATORY)

Before creating or modifying ANY file you MUST call `acquire_file_lock` (single)
or `acquire_file_locks` (batch — preferred when you know the files upfront).

- Lock **granted** → proceed with your changes.
- Lock **denied** → do NOT touch that file. Adapt your plan.
- Never read or write `.env` files directly — use the `env_tool` MCP server.
- The worker process owns persistence and cleanup after you finish; do not run git commands.

---

# Runtime Behaviour (MANDATORY)

## Pause checks
Call `check_project_paused` at the very start of your session and every 20 turns thereafter.
If it returns `PAUSED`, stop immediately — do not modify files, do not commit, do not start
any new tasks. Exit cleanly.

## Race condition prevention
- All file writes go through `write_file` / `edit_file` MCP tools — they acquire the file lock
  atomically. Never use the built-in Write/Edit tools in dev mode.
- For Redis: use atomic operations (SETNX, INCR, WATCH/MULTI/EXEC) for shared counters or
  flags. Never do read-then-write without holding the lock across both.
- For databases: any write touching more than one document or row must use a transaction.
  Treat partial writes as corruption.
- For any check-then-act pattern (read a value, decide, write): hold the lock across the
  entire sequence. Never release the lock between the check and the act.

## Graceful failure handling
- Wrap every external call (DB, Redis, HTTP, filesystem, subprocess) in try/except.
  On error: clean up any partial writes, release locks, log with full context, then raise.
- Never leave files half-written. Write to a temp path first, then rename atomically.
- Never swallow exceptions silently. If you catch and recover, log what you caught and why.
- On unrecoverable error: exit cleanly with a clear, actionable error message.
  Do not spin in a retry loop without exponential back-off and a hard ceiling.

## Observability
- Every significant operation boundary (start, success, failure, retry) must emit a
  structured log line with consistent fields: timestamp, operation name, entity IDs, duration.
- Include project and feature context in every log line — operators must be able to grep
  a single entity ID and reconstruct what happened.
- Log timing for any operation that can be slow: DB queries, HTTP calls, test runs, LLM calls.
- Error logs must contain enough context to diagnose without re-running: input values,
  current state, the exception message and type. Never log secrets, tokens, or PII.

## Atomicity
- Database: use transactions for multi-document writes. Commit or roll back as a unit — never
  leave the DB in a state where document A is updated but document B is not.
- Redis: use MULTI/EXEC or Lua scripts for related key updates that must succeed together.
- Files: write to a temp file then rename. A file that must never be partially read must never
  be written in place.

## Production-ready code (non-negotiable)
- No TODOs, FIXMEs, placeholder comments, or `pass` left in any production code path.
- All external calls (HTTP, DB, Redis, subprocess) must have explicit timeouts. No open-ended
  blocking calls.
- Configuration via environment variables with sane defaults. Never hardcode credentials,
  hostnames, ports, or environment-specific values in source code.
- Validate all inputs at system boundaries (API endpoints, queue consumers, file parsers).
  Never trust external data — check types, ranges, and required fields before use.
- All error messages are actionable: state what failed, why it failed, and what the caller
  should do about it.

## Testing — never assume, always prove

**Code is not complete until tests pass.** Do not assume your implementation is correct
because it looks right, compiles, or follows a pattern. Assume nothing — prove everything.
The only acceptable evidence that code works is a green `run_test` result on the actual
output. Reading your own code and concluding it is correct is not a substitute for running it.

All production code you create or modify must be fully unit tested and integration tested
before it is used by runtime code, notebooks, agents, jobs, dashboards, APIs, or user-facing
flows. Do not treat code as complete, dispatchable, callable, or ready for use until the
relevant tests have passed through `run_test`.

**Unit tests** — cover every piece of logic you write. Narrow, deterministic, fast. Test
decision branches, error paths, and data transformations. Test one thing per test case.

**Integration tests** — required for any code that crosses a boundary: API handler to DB,
service to queue, module to external client, one component to another. Write an integration
test that exercises the full sequence end-to-end with realistic inputs and asserts on the
actual outputs, not mocked return values. If an integration test already exists for the flow
you changed, update it and run it — do not leave it passing against a stale version of the code.

**E2E / acceptance tests** — if the workflow touches user-facing behaviour (UI flows, API
contracts consumed by a frontend, webhook sequences), write or update an E2E test that
drives the flow from the outside and asserts on the observable outcome. Never stub the
system under test in an E2E test — the point is to prove the real stack works end-to-end.

**Iterate until green.** If `run_test` fails, diagnose the root cause and fix it. Do not
move on, mark the workflow complete, or report success while any test is red. One failure is
not a reason to skip the test — it is a reason to fix the code.

Use the `run_test` MCP tool for all validation. Do not install packages or run test commands
directly in the worker workspace. Declare dependency changes in manifests and let the test
runtime build/run them.

If `run_test` cannot run because the test container is broken, the Dockerfile is wrong,
or the Dockerfile is missing, fix the root cause before proceeding:
- Inspect the component manifests, existing Dockerfiles, stack, and test command.
- Prefer correcting or creating a lightweight `Dockerfile.test` for validation. Do not delete,
  rewrite, or replace the project's production `Dockerfile` unless the task is explicitly about
  production deployment/runtime behavior.
- Include all dependencies and system packages required to install and run the tests.
- Re-run `run_test` after the Dockerfile fix.
- Do not bypass the test gate because the Dockerfile/test image was broken.

## Preview runtime fields

Preview deployment consumes these per-container fields from the project-root `docker-compose.dev.yml` or the project-root canonical compose file:
- service key/name
- container port(s) from `ports` or `expose`
- startup `command`
- optional `x-install-command` for workspace dependency linking, such as making `/deps` packages visible
- entry service implied by the browser/API-facing component and its first HTTP port

The root compose file is the preview source of truth. If you add or modify a hostable component, update the root compose `services:` map with that component. Do not rely on component-local compose files alone, and do not leave root compose as `services: {}` for a deployable project.

**Test scope — only test code you own.** Never write a test that asserts on the behaviour
of a third-party library. Third-party packages are tested by their maintainers. If a test
calls into a third-party package and asserts on that package's output rather than on your
own code's logic, rewrite it to mock the third-party call and assert on what your code does
with the result instead. If the test has no value once mocked, delete it. Apply this rule to
existing tests you encounter too — rewrite or delete any that assert on third-party behaviour.

**Dockerfile.test — stub, don't install.** Any third-party package not directly asserted
against in a test must be stubbed, not installed. Grep test imports first; install only
packages whose functions your tests actually call in assertions. "The module must be
importable" is not a reason to install it — expose it via a stub file on `PYTHONPATH` instead.
A Dockerfile.test must never use `COPY . .` — copy only source and test files explicitly.
Always add a `.dockerignore` excluding binary artefacts (`*.pkl`, `*.h5`, `*.pt`, `*.bin`,
`*.npy`, `data/`, `models/`, `outputs/`, `checkpoints/`).

When stubbing external dependencies (databases, HTTP clients, queues, external services):
- Use the test framework's built-in setup/teardown or scoping mechanism — never register
  stubs by mutating global or module-level state at test-file load time.
- Stubs registered globally at load time bleed into other test files in the same process
  and make tests order-dependent; always scope them to the test or suite that needs them.
- Load or instantiate the code under test after stubs are in place so it picks up the
  fakes at load time, not the real dependencies.

---

# Project: Titanic Survivors



**User request:** {'project_id': '6a5930d00af5ba40433b276c', 'software_name': 'Titanic Survivors Web App', 'software_idea': "We need to extend this app by giving it an interface via which the user can enter the details of a passenger (see titanic survival prediction feature), the passenger gets sent to the backend and it gets classified by the classifier in titanic survival prediction feature. And then depending on whether the classification is death or survival, we'll get a survival animation or a death animation", 'target_platforms': ['website'], 'core_functionality': ['Interface for enterring passenger details', 'Survival and death animations'], 'ui_ux_requirements': 'quaint and titanic themed'}

**Stack:** **Proposed Architecture - brief summary**

Titanic Survivors Web App

Adds a browser UI and a thin prediction API around the existing titanic_survival_predictor training pipeline so users can enter passenger details on a website and receive a survival/death result with themed animations.

Architecture_components:

0. api (fastapi)

Programming Language:

python

Technology:

fastapi, uvicorn, pydantic, pandas, numpy, scikit-learn, xgboost, joblib, python-dotenv, orjson, starlette, aiofiles, requests, typing-extensions

Responsibilities:

Exposes an HTTP prediction API that wraps the existing titanic_survival_predictor model. On startup, attempts to load serialized artifacts produced by the existing pipeline from ./artifacts (e.g., ./artifacts/titanic_ensemble.pkl and ./artifacts/feature_pipeline.pkl). If artifacts are missing, optionally invokes the existing titanic_survival_predictor module (as a Python import or subprocess) to run its training routine to generate them, without modifying that code. For request handling, validates incoming passenger fields with Pydantic (fields like Pclass, Sex, Age, SibSp, Parch, Fare, Embarked, Cabin, Ticket, Name if required by the existing feature engineering). To ensure feature parity, first tries to import and call any feature engineering utilities from titanic_survival_predictor (e.g., titanic_survival_predictor.features.transform(df)); if unavailable, falls back to loading a serialized preprocessing pipeline saved by the training run. Applies the ensemble model to the engineered features and returns a JSON response containing: prediction (0/1), probability, and a friendly label ('survived'/'did_not_survive'). Provides endpoints: GET /health (service health), GET /model/info (artifact metadata such as model version timestamp, hash), POST /predict (single passenger), POST /predict/batch (bulk), and POST /model/reload (reload artifacts without restart). Enables CORS for the web component origin so the website can call the API directly. Uses orjson for fast JSON and returns deterministic schemas so the web form can map fields unambiguously.

Rationale:

FastAPI provides a lean, typed, and performant Python API that can co-reside in the same Python environment as titanic_survival_predictor, letting us import its feature engineering or run its training routine. Keeping the prediction adapter in Python avoids cross-language serialization issues with XGBoost/sklearn artifacts. We include both import-and-call and artifact-load paths to integrate cleanly with the existing pipeline regardless of how it currently persists models. The explicit endpoints and CORS configuration make it straightforward for a browser SPA to consume.

1. web (react)

Programming Language:

typescript

Technology:

react, react-dom, axios, zustand, react-hook-form, zod, @hookform/resolvers, lottie-web, clsx

Responsibilities:

Browser SPA that renders a quaint, Titanic-themed form for entering passenger details used by the existing model (Pclass, Sex, Age, SibSp, Parch, Fare, Embarked; optionally Cabin/Ticket if the existing feature engineering expects them). Validates inputs client-side with react-hook-form and zod before sending to the API. Calls the api POST /predict endpoint via axios and displays the prediction: plays a survival animation if predicted to survive, or a death animation otherwise, using lottie-web assets stored under public/animations (e.g., public/animations/survive.json and public/animations/not_survive.json). Provides basic UX flows: reset form, try another passenger, and shows probability/confidence. Includes environment-based configuration (e.g., VITE_API_BASE_URL) to target the api component. Sets CORS-friendly headers only on the client side (actual policy is enforced server-side by api). Ships a minimal Titanic-themed style (colors, typography) with TailwindCSS utility classes.

Rationale:

React with Vite offers a fast, lightweight SPA suitable for a single-page form-and-result workflow. TypeScript ensures typed request/response parity with the API. Lottie provides high-quality, easily swappable animations without heavy assets. Using small libraries (react-hook-form, zod) keeps the codebase simple while delivering robust validation and state management.


**Services / containers:**
  - titanic_survival_predictor: 
  - api: Exposes an HTTP prediction API that wraps the existing titanic_survival_predictor model. On startup, attempts to load serialized artifacts produced by the existing pipeline from ./artifacts (e.g., ./artifacts/titanic_ensemble.pkl and ./artifacts/feature_pipeline.pkl). If artifacts are missing, optionally invokes the existing titanic_survival_predictor module (as a Python import or subprocess) to run its training routine to generate them, without modifying that code. For request handling, validates incoming passenger fields with Pydantic (fields like Pclass, Sex, Age, SibSp, Parch, Fare, Embarked, Cabin, Ticket, Name if required by the existing feature engineering). To ensure feature parity, first tries to import and call any feature engineering utilities from titanic_survival_predictor (e.g., titanic_survival_predictor.features.transform(df)); if unavailable, falls back to loading a serialized preprocessing pipeline saved by the training run. Applies the ensemble model to the engineered features and returns a JSON response containing: prediction (0/1), probability, and a friendly label ('survived'/'did_not_survive'). Provides endpoints: GET /health (service health), GET /model/info (artifact metadata such as model version timestamp, hash), POST /predict (single passenger), POST /predict/batch (bulk), and POST /model/reload (reload artifacts without restart). Enables CORS for the web component origin so the website can call the API directly. Uses orjson for fast JSON and returns deterministic schemas so the web form can map fields unambiguously.
  - web: Browser SPA that renders a quaint, Titanic-themed form for entering passenger details used by the existing model (Pclass, Sex, Age, SibSp, Parch, Fare, Embarked; optionally Cabin/Ticket if the existing feature engineering expects them). Validates inputs client-side with react-hook-form and zod before sending to the API. Calls the api POST /predict endpoint via axios and displays the prediction: plays a survival animation if predicted to survive, or a death animation otherwise, using lottie-web assets stored under public/animations (e.g., public/animations/survive.json and public/animations/not_survive.json). Provides basic UX flows: reset form, try another passenger, and shows probability/confidence. Includes environment-based configuration (e.g., VITE_API_BASE_URL) to target the api component. Sets CORS-friendly headers only on the client side (actual policy is enforced server-side by api). Ships a minimal Titanic-themed style (colors, typography) with TailwindCSS utility classes.

---

# Feature: API Service Foundation (FastAPI + CORS + Config)

Feature: API Service Foundation (FastAPI + CORS + Config)

Purpose
- Provide a production-ready FastAPI scaffold for the Titanic Survivors Web App API.
- Centralize configuration (env, dotenv), logging, JSON serialization (orjson), CORS, routing structure, and lifecycle hooks.
- Expose GET /health for uptime checks and basic service readiness verification.
- Establish consistent error handling and response schemas to be reused by subsequent API features (predict, model info, reload, etc.).

Scope and Responsibilities
- Server creation using FastAPI with orjson response class and global exception handlers.
- Configuration loading via pydantic BaseSettings with python-dotenv; layered precedence (env vars > .env file > defaults).
- CORS middleware allowing the configured web origin(s) and common HTTP methods/headers.
- Lifecycle hooks: on_startup and on_shutdown for future model-loading and resource cleanup (no-ops or pluggable in this feature).
- Health endpoint: GET /health with liveness/readiness detail.
- Structured error model and error handling for validation, HTTP exceptions, and unexpected errors.
- Logging initialization for structured logs (JSON) with request correlation, timing, and error traces.
- Basic router structure and versioned API prefix (/api/v1) to house future endpoints.
- Dependency injection scaffolding (e.g., settings provider) and standard middleware ordering.

Directory and File Layout
- api/
  - main.py (FastAPI app factory, middleware, startup/shutdown, include routers)
  - config.py (pydantic BaseSettings + loading utilities)
  - logging_config.py (logging init, JSON formatter, uvicorn log harmonization)
  - errors.py (error models and exception handlers)
  - routers/
    - __init__.py
    - health.py (GET /health)
  - middleware.py (future custom middlewares; optional request ID)
  - deps.py (FastAPI dependencies: get_settings, get_logger)
  - types.py (shared type aliases, enums)
  - __init__.py
- .env.example (document expected env vars)
- requirements.txt/pyproject.toml updates for: fastapi, uvicorn[standard], pydantic>=2, python-dotenv, orjson, typing-extensions
- tests/
  - test_health.py (pytest + httpx/fastapi TestClient for /health)

Runtime Dependencies and Versions
- Python 3.10+
- fastapi >= 0.112
- pydantic >= 2.5
- python-dotenv >= 1.0
- orjson >= 3.9
- uvicorn[standard] >= 0.30

Configuration Model (pydantic BaseSettings)
- AppSettings
  - ENV: str = "dev" (dev|staging|prod)
  - APP_NAME: str = "titanic-api"
  - API_V1_PREFIX: str = "/api/v1"
  - HOST: str = "0.0.0.0"
  - PORT: int = 8000
  - LOG_LEVEL: str = "INFO" (DEBUG|INFO|WARNING|ERROR)
  - LOG_JSON: bool = True (JSON logs for production)
  - CORS_ALLOW_ORIGINS: list[str] = ["http://localhost:5173"] (web SPA origin)
  - CORS_ALLOW_CREDENTIALS: bool = False (can be True if cookies used later)
  - CORS_ALLOW_METHODS: list[str] = ["GET","POST","OPTIONS"]
  - CORS_ALLOW_HEADERS: list[str] = ["*"]
  - REQUEST_MAX_BODY_SIZE: int = 2_000_000 (bytes) for safety
  - TIMEOUT_STARTUP_MS: int = 15000 (used by readiness checks/timeouts)
  - INCLUDE_SERVER_TIMING: bool = True (adds Server-Timing header for debugging)
  - TRUSTED_PROXIES: list[str] = [] (if behind proxy; affects client IP logging)
  - SENTRY_DSN: str | None = None (placeholder; not wired in this feature)
- Loading precedence: environment variables override .env values; .env loaded via python-dotenv early in process startup (uvicorn or main).
- Validation: pydantic enforces types; invalid CORS origins log warnings and are ignored.

App Factory and Initialization
- Use a create_app(settings: AppSettings | None = None) -> FastAPI function to build the app for testability.
- FastAPI(app) configuration
  - default_response_class = ORJSONResponse (from fastapi.responses)
  - title = APP_NAME; version set to package/version string if available.
  - docs: enabled in non-prod; in prod, optionally served but can be disabled via setting later.
- Middleware installation order
  - CORS (starlette.middleware.cors) with configured allow_* values.
  - Optional request ID middleware (future) before logging to correlate logs.
  - Custom body size limiting middleware if needed (drop with 413 on exceed); initially, rely on server/proxy limits.
  - Server-Timing simple middleware (optional) to measure handler execution time when INCLUDE_SERVER_TIMING.
- Routers
  - Include routers.health under API_V1_PREFIX.
- Exception handlers
  - RequestValidationError -> 422 structured error payload.
  - HTTPException -> pass-through status + structured error payload.
  - Generic Exception -> 500 structured error payload, no internals leaked.
- Startup/shutdown events (on_event or lifespan context)
  - Startup: log environment, settings summary (non-sensitive), and readiness gate set to true after init steps complete.
  - Shutdown: log flush completion.

Routing: Health Endpoint
- Path: GET {API_V1_PREFIX}/health
- Purpose: liveness and basic readiness probe; designed for k8s/containers/load balancers.
- Response 200 JSON
  - status: "ok"
  - service: APP_NAME
  - env: ENV
  - time: ISO8601 UTC timestamp
  - version: semantic version string or git SHA if available (fallback "unknown")
  - uptime_ms: milliseconds since process start (tracked via app.state.process_start)
  - dependencies: { "model_artifacts": "unknown" } in this foundation; later features can update readiness flags.
- Headers
  - Cache-Control: no-store
- Failure cases: in this foundation always returns 200 once app started; if future readiness gating is added, return 503 when not ready.

Error Handling and Response Model
- Standard error schema (ErrorResponse)
  - error: { code: str, message: str }
  - details: optional dict | list for validation errors
  - request_id: optional str (if request ID middleware exists)
- Mapping
  - HTTPException: code = http_{status_code}, message = detail (string), details = None.
  - RequestValidationError: code = "validation_error", message = "Request validation failed", details = list of field errors {loc,msg,type}.
  - Exception: code = "internal_error", message = "Internal server error".
- Ensure all handlers return ORJSONResponse with appropriate status codes.

Logging
- Initialize logging on import or in app factory via logging_config.py.
- JSON log formatter fields
  - timestamp (UTC ISO8601), level, logger, message, env, app, version, request_id (if available), method, path, status_code, duration_ms, client_ip, user_agent.
- Uvicorn/uvicorn.access harmonization to same JSON format.
- Log at startup: environment summary, CORS origins, API prefix.
- Per-request logs using middleware that measures route execution time; log at INFO with fields above on completion; WARN on 4xx (>=400) and ERROR on 5xx.

Serialization (orjson)
- Use ORJSONResponse globally. Ensure return values are built-in types or pydantic models with model_config = {"ser_json_timedelta": "float"} if needed later.
- orjson options
  - OPT_UTC_Z: append Z to UTC datetimes
  - OPT_NAIVE_UTC: treat naive datetime as UTC (avoid; better to ensure tz-aware)
  - OPT_NON_STR_KEYS: allow non-str dict keys if needed (avoid for API contracts)
- Deterministic keys: Keep explicit field order using pydantic models; do not rely on dict ordering.

State Management and DI
- app.state
  - process_start: float monotonic_ns() or perf_counter_ns() captured at startup
  - settings: AppSettings (immutable at runtime)
  - readiness: bool (true after startup)
  - logger: optional shared logger object (or use logging.getLogger per module)
- deps.py
  - get_settings() -> AppSettings (reads from app.state)
  - get_logger() -> logging.LoggerAdapter with request_id context if available

Security and CORS
- CORS_ALLOW_ORIGINS from config; supports multiple origins.
- If wildcard "*" is configured, set allow_credentials = False (Starlette restriction) and document this.
- Allowed headers default to *; restrict if needed later.
- Methods: GET, POST, OPTIONS by default.
- If behind proxies, document need to configure TRUSTED_PROXIES and potentially use ProxyHeadersMiddleware later.

Operational Notes
- Running locally
  - uvicorn api.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
- Health check endpoints for orchestration
  - Liveness: GET /api/v1/health
  - Readiness: same endpoint; return 200 when app.state.readiness true; else 503.
- Metrics and tracing: not in scope; hooks prepared to integrate later (e.g., Prometheus, OpenTelemetry).

Edge Cases and Considerations
- Misconfigured CORS origins (e.g., spaces, missing scheme): log warning, skip invalid entries; ensure at least one valid origin in non-prod.
- orjson serialization of Decimal/UUID/datetime: convert or use pydantic models to ensure compatibility.
- Large request bodies: while foundation does not accept payloads yet, set server/proxy size limits and prepare 413 handler if added later.
- Thread safety: app.state used for read-only settings; future mutable state (model artifacts) must be guarded if hot-reloaded concurrently.
- Exception leakage: never return internal exception messages in prod; include request_id for correlation.
- Time zone: always use UTC for logs and timestamps.

Testing
- Unit tests: test_health returns 200 and schema keys exist; validate content-types and ORJSON behavior.
- Integration: start uvicorn in test container and assert CORS preflight responses for configured origins.

Example Interfaces (pseudocode-level)
- config.py
  - class AppSettings(BaseSettings): fields above; model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)
- logging_config.py
  - def init_logging(settings: AppSettings) -> None: setup root/uvicorn loggers with JSON formatter
- errors.py
  - ErrorResponse(BaseModel): error: ErrorDetail, details: Any | None = None, request_id: str | None = None
  - register_exception_handlers(app: FastAPI)
- routers/health.py
  - router = APIRouter(tags=["health"]) -> GET /health handler building payload from app.state
- main.py
  - def create_app(settings: AppSettings | None = None) -> FastAPI: load settings (from env if None), init logging, create FastAPI, add middleware, include routers, set lifecycle events, return app

Deliverables
- Working FastAPI app that boots, logs in JSON, serves GET /api/v1/health, enforces CORS, and returns ORJSON responses.
- Configuration via .env with sensible defaults; documented in .env.example.
- Tests for health endpoint and CORS preflight behavior.

Future Integration Points (outside this feature but enabled by it)
- Model artifact loading in startup hook and readiness gating.
- Routers for /model/info, /predict, /predict/batch, /model/reload under /api/v1.
- Request/response models for prediction endpoints using pydantic and consistent error responses.
- Request ID middleware and correlation with frontend via headers.


**Workflows in this feature:**
  0. Run API Locally (App Factory Boot + Lifespan) — Developer starts the FastAPI service using the app factory; settings load, logging initializes, middleware/routers/handlers attach, and readiness flips to true.
  1. Health Check (Liveness/Readiness) — A user or monitoring system retrieves health status to verify service availability and basic readiness.
  2. CORS Preflight (OPTIONS) for Browser Calls — Browser issues a CORS preflight to check permissions before cross-origin requests from the SPA.
  3. Structured Error Handling (HTTPException/404) — Unknown route access demonstrates standardized error schema and logging.
  4. Per-Request Logging and Server-Timing — Each handled request is measured and logged with structured fields; optional Server-Timing header is emitted.
  5. Configuration Change and Reload (Cold Start) — Operator updates .env to change CORS or logging and restarts the API; settings precedence and validation apply.
  6. Graceful Shutdown — Service handles termination signals, runs shutdown hooks, and flushes logs.
  7. Automated Tests: Health and CORS — CI or developer runs pytest; tests validate health endpoint and CORS behavior using TestClient.

## Feature Progress Context
The following has already been built or decided in this feature.
Treat this as the authoritative handoff from earlier workflow iterations; reuse these contracts and do not duplicate them.

**Latest feature branch state:**
  - Branch: `feature/6a5930d00af5ba40433b276c/6a5bed2cf575302e212edd17`
  - Commit: `fd68f1f7daab2b977a7df1af34c3b0af513e8a57`
**Completed workflows:**
  - Workflow 1 (Health Check (Liveness/Readiness)): Verified and confirmed the Health Check (Liveness/Readiness) workflow via GET /api/v1/health was already fully implemented with proper headers, payload, logging, and tests passing; no code changes were required.
  - Workflow 2 (CORS Preflight (OPTIONS) for Browser Calls): Validated and completed the CORS preflight workflow via expanded and corrected integration tests (no production code changes), ensuring OPTIONS handling, allowed headers/methods, and actual request behavior align with settings and browser expectations; all tests pass.
  - Workflow 3 (Structured Error Handling (HTTPException/404)): Added integration and unit tests to verify the structured 404 error handling workflow, ensuring unknown routes return a JSON ErrorResponse with 404 and that per-request logging records 4xx responses at WARNING level with route details and duration.

**Files already created:**
  - api/tests/integration/test_app_factory.py
  - api/tests/unit/test_middleware.py

**Files already modified:**
  - .claude/CLAUDE.md

**APIs already defined:**
  - GET /api/v1/health

**Functions / classes already defined:**
  - test_access_log_level_is_warning_for_4xx()
  - test_cors_actual_get_request_echoes_allow_origin_header()
  - test_cors_actual_request_from_disallowed_origin_has_no_allow_header()
  - test_cors_preflight_allows_configured_origin()
  - test_cors_preflight_allows_post_predict_json_request()
  - test_cors_preflight_echoes_requested_headers_when_wildcard()
  - test_cors_preflight_rejects_unconfigured_origin()
  - test_unknown_route_logs_warning_with_route_details_and_duration()

**Tests already run:**
  - integration tests: passed — No changes were made since the last run, so no package rebuild is needed. Re-running to confirm the integration suite is still green.
Confirmed: the `api` component test suite ran again against the reused test image (no `packages_installed` change needed since no code changed) — **53 passed, 0 failed**, covering the full Health Check workflow (route visibility, response schema, Cache-Control/ORJSON, Server-Timing, structured access logging, and a real end-to-end uvicorn boot test hitting `/api/v
  - integration tests: passed — Tool reconnected. Only the `api` component changed (test file edits in `api/tests/integration/test_app_factory.py`), so re-running its test suite to confirm the final state.
Confirmed: the `api` component test suite (57 tests, including the 5 new/updated CORS preflight tests) passes cleanly against the synced remote branch HEAD (`0a156af`). Only `api/tests/integration/test_app_factory.py` changed in this workflow — no other component required a test run.

INTEGRATION TESTS: ALL PASSED
  - integration tests: passed — Confirmed: the only files changed for this workflow (`api/tests/unit/test_middleware.py` and `api/tests/integration/test_app_factory.py`) belong to the `api` component, and `run_test` against `api` re-ran clean: **59 passed, 0 failed**, including the two new tests covering WARN-level access logging with route details and duration_ms for 404s, alongside all pre-existing structured-error-handling tests (404 body shape, 422 validation, 500 leak-safety, CORS, health, etc.). No production code change

**Read these files first:**
  - .claude/CLAUDE.md
  - api/tests/integration/test_app_factory.py
  - api/tests/unit/test_middleware.py

---

# Workflow: Per-Request Logging and Server-Timing

Each handled request is measured and logged with structured fields; optional Server-Timing header is emitted.

**Implementation steps:**
  1. 1) Operator opens browser and hits GET /api/v1/health to generate a request for observing logs; feature visible via health page access [Container: operator browser] Deps: []
  2. 2) Logging/timing middleware records start time and collects request context (method, path, client_ip, user_agent, request_id?) [Container: backend/api process] Deps: [1]
  3. 3) Request processed by route; response generated (200 or error) [Container: backend/api process] Deps: [2]
  4. 4) Middleware computes duration_ms, sets Server-Timing header if enabled, emits structured log at INFO for 2xx/3xx, WARN for 4xx, ERROR for 5xx with fields: timestamp, level, app, env, version, method, path, status_code, duration_ms, client_ip, user_agent, request_id [Container: backend/api process] Deps: [3]
  5. 5) Operator views JSON logs in terminal or log sink and confirms presence of expected fields [Container: developer shell] Deps: [4]
**Edge cases:**
  - If request handler raises Exception, handler returns 500; log level escalates to ERROR and stack trace is included in logs but not leaked to client
  - If INCLUDE_SERVER_TIMING=False, header is omitted while logs still record duration_ms
  - If behind proxy without ProxyHeadersMiddleware, client_ip may be proxy IP; document TRUSTED_PROXIES need
**Test notes:** Functional: assert Server-Timing header exists when enabled; capture logs and verify JSON fields and level per status code.

---

# Task Planning Journal (MANDATORY)

Before editing files or running implementation commands, write a task plan to:

`/tmp/claude_task_plan_6a5930d00af5ba40433b276c_6a5bed2cf575302e212edd17_workflow_4.md`

Keep this file updated as the task progresses. It is for operator debugging and
post-mortem inspection; do not commit it and do not copy secrets into it.

The plan must include:
- User request link: how this task serves the user's requested outcome.
- Feature/workflow link: which feature and workflow this task belongs to.
- Related steps: prerequisite steps, dependent steps, and any sibling workflow work that may constrain this task.
- Implementation steps: concise checklist with status (`pending`, `in_progress`, `done`, or `blocked`).
- Rationale per step: a short, concrete reason for why the step is needed, based on evidence from the codebase or prompt. Do not write private chain-of-thought; write actionable engineering rationale.
- Expected files/components: likely files to inspect or change, and why.
- Validation plan: tests, `run_test` calls, notebook/evaluation checks, and acceptance criteria.
- Decisions and blockers: any assumptions, tradeoffs, missing inputs, or user/HITL dependencies.

Update the plan whenever you complete a step, change approach, discover a blocker,
or hand off to a tool such as `run_test`, `request_human_input`, or another task-specific tool.

---

# Your Task

Implement the full **Per-Request Logging and Server-Timing** as described above.
Cover every item in the implementation steps. The order is yours to decide based on
dependencies you discover in the codebase — sequence work so each piece can be tested
before the next depends on it.

Before declaring the workflow complete:
- All new logic must have unit tests and integration tests.
- All tests must pass via `run_test`.
- No TODO, placeholder, or debug code left in production paths.
- Every external call (HTTP, DB, Redis, subprocess) has an explicit timeout.
- Structured log lines emitted at every significant operation boundary.