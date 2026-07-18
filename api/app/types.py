"""Shared type aliases and enums used across the API foundation."""
from __future__ import annotations

from typing import Literal

Environment = Literal["dev", "staging", "prod", "test", "testing"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
