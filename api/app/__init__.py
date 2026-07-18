"""ASGI entrypoint package.

Re-exports the FastAPI ``app`` instance from ``app.main`` so ASGI servers
can target this package directly, e.g. ``uvicorn app:app``.
"""
from app.main import app

__all__ = ["app"]
