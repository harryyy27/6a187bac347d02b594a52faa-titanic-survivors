"""FastAPI application entrypoint / ASGI application factory."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import router as api_router
from app.core.config import get_settings

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """Application factory used by ASGI servers (e.g. ``uvicorn app:app``)."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        default_response_class=ORJSONResponse,
    )

    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    application.include_router(api_router, prefix="/api")

    return application


app = create_app()
