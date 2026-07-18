"""Model loading and inference helpers.

The classifier is loaded lazily (on first use) from ``MODEL_PATH`` via
``joblib``. A thread-safe double-checked-locking singleton avoids loading
the artifact more than once, and avoids paying the load cost at import
time (useful for fast test collection / app startup).
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.core.config import get_settings

_model_lock = threading.Lock()
_model: Any | None = None


class ModelLoadError(RuntimeError):
    """Raised when the classifier artifact cannot be loaded."""


def _load_model_from_disk() -> Any:
    settings = get_settings()
    model_path = Path(settings.model_path)
    if not model_path.exists():
        raise ModelLoadError(
            f"Model artifact not found at '{model_path}'. Expected a joblib-serialized "
            "scikit-learn/xgboost-compatible estimator exposing predict/predict_proba. "
            "Set MODEL_PATH to a valid artifact or run the training pipeline first."
        )
    try:
        return joblib.load(model_path)
    except Exception as exc:  # noqa: BLE001
        raise ModelLoadError(
            f"Failed to load model artifact at '{model_path}': {exc}"
        ) from exc


def get_model() -> Any:
    """Return the process-wide model singleton, loading it if necessary."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = _load_model_from_disk()
    return _model


def reload_model() -> Any:
    """Force a reload of the model artifact from disk."""
    global _model
    with _model_lock:
        _model = _load_model_from_disk()
    return _model


def predict_proba_and_label(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    """Run inference on an already feature-engineered dataframe.

    Returns a list of dicts (one per row) with ``prediction``, ``probability``
    and ``label`` keys.
    """
    model = get_model()
    predictions = model.predict(dataframe)
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(dataframe)[:, 1]
    else:
        probabilities = predictions.astype(float)

    results: list[dict[str, Any]] = []
    for pred, proba in zip(predictions, probabilities, strict=True):
        label = "survived" if int(pred) == 1 else "did_not_survive"
        results.append(
            {"prediction": int(pred), "probability": float(proba), "label": label}
        )
    return results
