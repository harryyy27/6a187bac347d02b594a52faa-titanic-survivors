"""Shared fixtures for the Titanic Survival Prediction eval bundle tests.

``run_eval.py`` imports the production ``titanic`` module from the sibling
``titanic_survival_predictor/`` component for its real feature-engineering,
training, and prediction functions. This test image is intentionally
minimal (pandas/numpy/pytest only -- no xgboost, no the sibling component's
source is copied in), so a lightweight stand-in ``titanic`` module is
installed into ``sys.modules`` at collection time when the real one is not
importable. Individual tests then monkeypatch specific attributes on
``run_eval.titanic`` to control behaviour deterministically -- the same
dispatch-fixture pattern the sibling component's own suite uses to fake
``xgboost``/``keras`` (see titanic_survival_predictor/tests/conftest.py).

No real xgboost training or the real titanic_survival_predictor engine
executes in this suite.
"""
from __future__ import annotations

import sys
import types

import pytest

try:
    import titanic  # noqa: F401  (use the real module if it happens to be on sys.path)
except ImportError:
    _stub = types.ModuleType("titanic")
    _stub.RARE_TITLE_THRESHOLD = 8

    def _stub_xgb_params():
        return {
            "max_depth": 4,
            "objective": "binary:logistic",
            "eta": 0.125,
            "min_child_weight": 1,
            "gamma": 1,
            "alpha": 0.4,
            "eval_metric": "error",
            "colsample_bytree": 0.8,
        }

    def _stub_prepare_features(train, test):
        """Numeric-only passthrough standing in for the real cleaning /
        feature-engineering chain -- just enough shape/column behaviour for
        run_eval's orchestration to exercise (Survived kept in train,
        PassengerId kept in test, everything else numeric)."""
        keep = [c for c in ("PassengerId", "Survived", "Pclass", "Age", "SibSp", "Parch", "Fare") if c in train.columns]
        train_out = train[keep].fillna(0.0).copy()
        keep_test = [c for c in keep if c in test.columns]
        test_out = test[keep_test].fillna(0.0).copy()
        return train_out, test_out

    def _stub_train_xgb_ensemble(
        train_x, train_y, k=4, num_round=25, model_dir=".", early_stopping_rounds=20
    ):
        return [f"stub-fold-{i}" for i in range(k)]

    def _stub_predict_with_ensemble(ensemble, test_x):
        return [1 for _ in range(len(test_x))]

    _stub.xgb_params = _stub_xgb_params
    _stub.prepare_features = _stub_prepare_features
    _stub.train_xgb_ensemble = _stub_train_xgb_ensemble
    _stub.predict_with_ensemble = _stub_predict_with_ensemble
    sys.modules["titanic"] = _stub


@pytest.fixture
def fake_titanic_dispatch(monkeypatch):
    """Install call-recording fakes for the heavy titanic entry points.

    Lets tests assert *how* run_eval.run() drives the training/prediction
    engine (arguments passed, number of calls) without any real xgboost
    training, and without depending on which `titanic` (real or stub) ended
    up in sys.modules at collection time.
    """
    import run_eval  # sys.modules["titanic"] is guaranteed to be set by now

    calls = {"train_xgb_ensemble": [], "predict_with_ensemble": []}

    def fake_train_xgb_ensemble(
        train_x, train_y, k=4, num_round=25, model_dir=".", early_stopping_rounds=20
    ):
        calls["train_xgb_ensemble"].append(
            {
                "n_rows": len(train_x),
                "k": k,
                "num_round": num_round,
                "model_dir": model_dir,
                "early_stopping_rounds": early_stopping_rounds,
            }
        )
        return [f"fold-{i}" for i in range(k)]

    def fake_predict_with_ensemble(ensemble, test_x):
        calls["predict_with_ensemble"].append(
            {"ensemble_size": len(ensemble), "n_rows": len(test_x)}
        )
        # Alternate 0/1 deterministically so accuracy isn't trivially 0 or 1.
        return [i % 2 for i in range(len(test_x))]

    monkeypatch.setattr(run_eval.titanic, "train_xgb_ensemble", fake_train_xgb_ensemble)
    monkeypatch.setattr(run_eval.titanic, "predict_with_ensemble", fake_predict_with_ensemble)
    return calls
