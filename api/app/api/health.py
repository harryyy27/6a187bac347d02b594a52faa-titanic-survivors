"""Foundation liveness/readiness probe: ``GET {API_V1_PREFIX}/health``."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response

from app.api.schemas import ServiceHealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ServiceHealthResponse)
async def health(request: Request, response: Response) -> ServiceHealthResponse:
    """Liveness/readiness probe.

    Always returns 200 once the process is up and this handler is reachable
    (there is no separate readiness gating in this foundation feature beyond
    the ``app.state.ready`` flag set at the end of startup, which is
    surfaced under ``dependencies`` for visibility).
    """
    response.headers["Cache-Control"] = "no-store"

    settings = request.app.state.settings
    process_start = getattr(request.app.state, "process_start", None)
    uptime_ms = (time.perf_counter() - process_start) * 1000 if process_start is not None else 0.0

    return ServiceHealthResponse(
        service=settings.app_name,
        env=settings.env,
        time=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        version=getattr(request.app.state, "version", "unknown"),
        uptime_ms=round(uptime_ms, 2),
        dependencies={
            "ready": bool(getattr(request.app.state, "ready", False)),
            "model_artifacts": "unknown",
        },
    )
