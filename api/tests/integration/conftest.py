"""Fixtures scoped to ``tests/integration`` only.

Directory-scoped ``conftest.py`` is pytest's built-in mechanism for
restricting a fixture's availability to a subset of the suite -- these
fixtures are invisible to ``tests/unit``.
"""
from __future__ import annotations

import sys
import types
from collections.abc import Iterator

import pytest

# These packages are real production dependencies of `app.ml.model` /
# `app.api.routes` (the pre-existing /predict feature), but none of the
# foundation tests in this directory call their functions or assert on
# their behaviour -- they only need `app.main` to *import* successfully.
# Per the project's test-scope rule ("stub, don't install"), they are
# stubbed here rather than added to requirements-test.txt.
_UNASSERTED_HEAVY_MODULES = (
    "pandas",
    "numpy",
    "sklearn",
    "xgboost",
    "joblib",
    "aiofiles",
)


@pytest.fixture
def stub_unused_ml_dependencies(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Install empty stand-in modules for unused heavy ML packages.

    Scoped via ``monkeypatch`` (function-scoped teardown restores the real
    ``sys.modules`` entries automatically), and only requested by the tests
    that need to import ``app.main``. Import the code under test *inside*
    the test function (after requesting this fixture) so it resolves these
    stubs at import time instead of the real -- absent -- packages.
    """
    for module_name in _UNASSERTED_HEAVY_MODULES:
        if module_name not in sys.modules:
            monkeypatch.setitem(sys.modules, module_name, types.ModuleType(module_name))
    yield
