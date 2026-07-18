"""Smoke test: confirms the test runner executes our project-owned code."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tiny_math import add  # noqa: E402

from tests.testWrapperTimeout import testWrapperTimeout  # noqa: E402


@testWrapperTimeout
def test_add_returns_sum() -> None:
    assert add(2, 3) == 5
