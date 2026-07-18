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

| Variable        | Purpose                                               |
|-----------------|--------------------------------------------------------|
| `ENV`           | Runtime environment name (e.g. `development`)          |
| `APP_NAME`      | Human-readable service name                            |
| `LOG_LEVEL`     | Logging verbosity                                      |
| `SECRET_KEY`    | Application secret (replace in real deployments)       |
| `MODEL_PATH`    | Path to the joblib-serialized classifier artifact      |
| `ALLOWED_HOSTS` | Comma-separated list of hosts for TrustedHostMiddleware |
| `PORT`          | Port the ASGI server binds to                          |

See `.env` for local development defaults (dummy values only).

## Running (production image)

```
docker build -t titanic-api .
docker run -p 8000:8000 titanic-api
```

The container entrypoint runs `uvicorn app:app --host 0.0.0.0 --port $PORT`.
