"""Shared pytest fixtures for the api test suite.

Keeps tests hermetic and fast: an autouse fixture snapshots/restores
``os.environ`` around every test so no test can leak environment mutations
into another.

Stubbing of heavy, unused third-party packages (pandas, numpy, sklearn,
xgboost, joblib, aiofiles) is intentionally *not* done here. A global,
session-scoped, autouse stub would bleed into every test file in this
process regardless of whether it needs the stub, which is exactly the
anti-pattern the project's testing rules warn against. Instead, only the
test files that actually need to import the full ``app.main`` graph (and
therefore transitively import those unused heavy packages) install scoped
stubs via ``monkeypatch`` -- see ``tests/integration/conftest.py``.
"""
from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _snapshot_environ() -> Iterator[None]:
    """Snapshot os.environ before each test and restore it afterward."""
    before = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(before)
