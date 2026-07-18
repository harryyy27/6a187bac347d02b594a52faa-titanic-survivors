# api

FastAPI service for Titanic Survivors. Wraps the existing
`titanic_survival_predictor` training pipeline behind an HTTP prediction
API so the `web` component can request survival predictions for a
passenger.

## Dependency management

Dependencies are managed exclusively with [Poetry](https://python-poetry.org/).
The manifest is `pyproject.toml`; the resolved, reproducible lockfile is
`poetry.lock`. Do not use pip/requirements.txt directly for this component.

- Runtime dependencies: `[tool.poetry.dependencies]`
- Dev-only dependencies (lint/type-check): `[tool.poetry.group.dev.dependencies]`

### Generating the lockfile

`poetry.lock` is produced reproducibly by building `Dockerfile.installer`,
which resolves dependencies from `pyproject.toml` only (no packages are
installed, lock resolution only):

```
docker build -f Dockerfile.installer -t titanic-api-installer .
docker run --rm titanic-api-installer > poetry.lock
```

## Linting

The recorded lint command (see `[tool.ruff]` in `pyproject.toml`) is:

```
poetry run ruff check --fix .
```

Type checking is configured via `[tool.mypy]` in the same file.

## Environment variables

| Variable                   | Purpose                                                        |
|----------------------------|------------------------------------------------------------------|
| `ENV`                      | Runtime environment: `dev`\|`staging`\|`prod` (`test`/`testing` also accepted) |
| `APP_NAME`                 | Human-readable service name                                     |
| `API_V1_PREFIX`            | Prefix routers are mounted under (default `/api/v1`)             |
| `HOST`                     | Interface uvicorn binds to                                       |
| `PORT`                     | Port the ASGI server binds to                                    |
| `LOG_LEVEL`                | Logging verbosity: `DEBUG`\|`INFO`\|`WARNING`\|`ERROR`            |
| `LOG_JSON`                 | `true` for structured JSON logs, `false` for console-friendly    |
| `CORS_ALLOW_ORIGINS`       | Comma-separated browser origins allowed to call this API (invalid entries are dropped with a warning) |
| `CORS_ALLOW_CREDENTIALS`   | Allow credentialed CORS requests (forced `false` if origins include `*`) |
| `CORS_ALLOW_METHODS`       | Comma-separated allowed HTTP methods                              |
| `CORS_ALLOW_HEADERS`       | Comma-separated allowed request headers                           |
| `REQUEST_MAX_BODY_SIZE`    | Reserved for future request-size limiting (bytes)                 |
| `TIMEOUT_STARTUP_MS`       | Reserved startup-readiness timeout budget (ms)                    |
| `INCLUDE_SERVER_TIMING`    | Emit a `Server-Timing` response header with handler duration      |
| `TRUSTED_PROXIES`          | Reserved for future proxy-aware client IP logging                 |
| `SENTRY_DSN`               | Placeholder; not wired up by this feature                         |
| `SECRET_KEY`               | Application secret (replace in real deployments)                  |
| `MODEL_PATH`               | Path to the joblib-serialized classifier artifact                 |
| `ALLOWED_HOSTS`            | Comma-separated list of hosts for TrustedHostMiddleware            |

See `.env.example` for a documented starting point and `.env` for local
development defaults (dummy values only). `GET {API_V1_PREFIX}/health`
reports the resolved `env`, service name, uptime, and readiness.

## Running (production image)

```
docker build -t titanic-api .
docker run -p 8000:8000 titanic-api
```

The container entrypoint runs `uvicorn app:app --host 0.0.0.0 --port $PORT`.
