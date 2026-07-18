"""FastAPI application entrypoint / ASGI application factory."""
from __future__ import annotations

import logging
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.health import router as health_router
from app.api.routes import router as api_router
from app.core.config import AppSettings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging_config import init_logging
from app.middleware import RequestContextMiddleware

STATIC_DIR = Path(__file__).parent / "static"

logger = logging.getLogger("app.main")


def _resolve_version() -> str:
    """Best-effort service version for /health and log context.

    Falls back through an explicit env var, then a git SHA baked in at
    build time, to the literal "unknown" -- never raises.
    """
    return os.environ.get("APP_VERSION") or os.environ.get("GIT_SHA") or "unknown"


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings: AppSettings = application.state.settings
    application.state.process_start = time.perf_counter()
    application.state.ready = False

    logger.info(
        "startup.begin",
        extra={
            "env": settings.env,
            "app_name": settings.app_name,
        },
    )
    logger.info(
        "startup.config_summary env=%s api_prefix=%s cors_origins=%s log_json=%s",
        settings.env,
        settings.api_v1_prefix,
        settings.cors_allow_origins,
        settings.log_json,
    )

    application.state.ready = True
    logger.info("startup.complete", extra={"env": settings.env})

    try:
        yield
    finally:
        logger.info("shutdown.begin", extra={"env": settings.env})
        application.state.ready = False
        logging.shutdown()
        # `logging.shutdown()` flushes/closes handlers; nothing further to
        # release here (no DB pools / background tasks owned by this
        # foundation feature yet).


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Application factory used by ASGI servers (e.g. ``uvicorn app:app``).

    Accepts an optional pre-built ``settings`` so tests can construct an app
    against arbitrary configuration without mutating process environment
    variables / the global settings cache.
    """
    resolved_settings = settings if settings is not None else get_settings()
    version = _resolve_version()

    init_logging(resolved_settings, version=version)

    docs_enabled = not resolved_settings.is_prod

    application = FastAPI(
        title=resolved_settings.app_name,
        version=version,
        default_response_class=ORJSONResponse,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=_lifespan,
    )

    application.state.settings = resolved_settings
    application.state.version = version
    application.state.ready = False
    application.state.process_start = time.perf_counter()

    # --- middleware --------------------------------------------------------
    # Starlette treats the *last* `add_middleware` call as the *outermost*
    # layer (it wraps everything added before it). We want CORS to be the
    # true outermost layer -- so it can short-circuit preflight OPTIONS
    # requests before they reach anything else, and so it can attach
    # Access-Control-* headers even to responses/errors produced by other
    # middleware -- so it is added *last*, even though conceptually it is
    # "(a)" in the spec's request-facing order: (a) CORS, (b) request id,
    # (c) Server-Timing.
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=resolved_settings.allowed_hosts,
    )
    # (b)/(c) request id + Server-Timing + structured access logging.
    application.add_middleware(RequestContextMiddleware, settings=resolved_settings)
    # (a) CORS -- added last so it is the outermost middleware.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_allow_origins,
        allow_credentials=resolved_settings.cors_allow_credentials,
        allow_methods=resolved_settings.cors_allow_methods,
        allow_headers=resolved_settings.cors_allow_headers,
    )

    register_exception_handlers(application)

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    application.include_router(health_router, prefix=resolved_settings.api_v1_prefix)
    application.include_router(api_router, prefix="/api")

    return application


app = create_app()
