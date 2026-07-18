"""FastAPI dependency-injection helpers shared across routers."""
from __future__ import annotations

import logging

from app.core.config import AppSettings, get_settings

__all__ = ["get_settings", "get_logger"]


def get_logger(name: str = "app") -> logging.Logger:
    """Return a module-scoped logger.

    A thin wrapper (rather than a bare ``logging.getLogger`` call at every
    call site) so routers can depend on it via FastAPI's ``Depends`` and so
    the log-acquisition strategy can change in one place later (e.g. to
    attach request-scoped context) without touching every router.
    """
    return logging.getLogger(name)


def settings_dependency() -> AppSettings:
    """FastAPI ``Depends``-compatible accessor for the cached settings."""
    return get_settings()
