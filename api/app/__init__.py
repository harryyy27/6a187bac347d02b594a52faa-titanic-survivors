"""ASGI entrypoint package.

Lazily re-exports the FastAPI ``app`` instance from ``app.main`` so ASGI
servers can target this package directly, e.g. ``uvicorn app:app``.

This is deliberately lazy (via module ``__getattr__``, PEP 562) rather than
a top-level ``from app.main import app``: eagerly importing ``app.main`` at
package-init time would mean importing *any* ``app.*`` submodule (e.g.
``app.core.config`` from a unit test) always drags in ``app.main`` ->
``app.api.routes`` -> ``app.ml.model`` and their heavy production
dependencies (pandas, joblib, ...), even for tests that have nothing to do
with the predict endpoint. Lazy access keeps ``uvicorn app:app`` working
identically while letting unit tests import narrow ``app.*`` submodules
without needing those heavy packages installed.
"""
from __future__ import annotations

from typing import Any

__all__ = ["app"]


def __getattr__(name: str) -> Any:
    if name == "app":
        from app.main import app as _app

        return _app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
