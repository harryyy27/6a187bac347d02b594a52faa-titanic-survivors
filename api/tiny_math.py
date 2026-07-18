"""Smallest possible project-owned code artifact, used by the smoke test.

Confirms the test runner is actually executing our code path (as opposed
to, say, silently collecting zero tests).
"""
from __future__ import annotations


def add(a: float, b: float) -> float:
    """Return a + b."""
    return a + b
