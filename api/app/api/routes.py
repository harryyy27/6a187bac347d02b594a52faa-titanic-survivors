"""Primary API router: health, readiness, and prediction endpoints."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.api.schemas import HealthResponse, PredictRequest, PredictResponse, ReadyResponse
from app.ml.model import ModelLoadError, predict_proba_and_label

router = APIRouter()


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Liveness probe: process is up and serving requests."""
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=ReadyResponse)
async def readyz() -> ReadyResponse:
    """Readiness probe: process is ready to accept traffic."""
    return ReadyResponse(status="ready")


@router.post("/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest) -> PredictResponse:
    """Predict survival for a single passenger."""
    dataframe = pd.DataFrame([payload.model_dump()])
    try:
        results = predict_proba_and_label(dataframe)
    except ModelLoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    result = results[0]
    return PredictResponse(**result)
