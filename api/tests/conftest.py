"""Shared pytest fixtures for the api test suite.

Keeps tests hermetic and fast:
  (a) an autouse fixture snapshots/restores ``os.environ`` around every
      test so no test can leak environment mutations into another;
  (b) lightweight stub modules are installed into ``sys.modules`` for the
      heavy, unused production packages so incidental import resolution
      (e.g. accidental collection of app modules) stays fast without
      those packages being installed in the test image;
  (c) no fixture performs I/O outside the working directory.
"""
from __future__ import annotations

import os
import sys
import types
from collections.abc import Iterator

import pytest

_STUB_MODULE_NAMES = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "pandas",
    "numpy",
    "sklearn",
    "xgboost",
    "joblib",
    "python_dotenv",
    "dotenv",
    "orjson",
    "starlette",
    "aiofiles",
    "requests",
    "typing_extensions",
]


def _install_stub_modules() -> None:
    for module_name in _STUB_MODULE_NAMES:
        if module_name in sys.modules:
            continue
        sys.modules[module_name] = types.ModuleType(module_name)


@pytest.fixture(autouse=True)
def _snapshot_environ() -> Iterator[None]:
    """Snapshot os.environ before each test and restore it afterward."""
    before = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(before)


@pytest.fixture(autouse=True, scope="session")
def _stub_heavy_dependencies() -> Iterator[None]:
    """Insert lightweight stand-ins for heavy production packages."""
    _install_stub_modules()
    yield
