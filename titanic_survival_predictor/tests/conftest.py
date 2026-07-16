"""Shared fixtures for the titanic_survival_predictor test suite.

The production pipeline lazily imports two heavy third-party engines --
xgboost (gradient boosting) and keras (neural network training) -- inside
individual functions rather than at module scope. Neither engine (nor any
GPU/accelerator backend it might pull in) is installed in the test image.

These fixtures install lightweight fake modules into ``sys.modules`` before
a test calls into pipeline code that performs the lazy import, so the
import succeeds and the project's dispatch/wiring logic can be exercised
without pulling in or executing the real training/inference engines.
"""
from __future__ import annotations

import sys
import types

import numpy as np
import pytest


class _FakeBooster:
    """Stand-in for an xgboost.Booster: records calls, returns canned scores."""

    def __init__(self, predict_scores=None):
        self.trained_with = None
        self._predict_scores = predict_scores

    def predict(self, dmatrix, ntree_limit=None):
        if self._predict_scores is not None:
            return np.asarray(self._predict_scores[: dmatrix.n_rows])
        # Default: alternate 0/1-ish scores so majority-vote logic is exercised.
        return np.array([0.9 if i % 2 == 0 else 0.1 for i in range(dmatrix.n_rows)])


class _FakeDMatrix:
    def __init__(self, data, label=None):
        self.data = data
        self.label = label
        self.n_rows = len(data)


@pytest.fixture
def fake_xgboost(monkeypatch):
    """Install a fake ``xgboost`` module that never trains a real model."""
    calls = {"train": []}

    fake_module = types.ModuleType("xgboost")
    fake_module.DMatrix = _FakeDMatrix

    def fake_train(params, dtrain, num_round, eval_list, early_stopping_rounds=None):
        calls["train"].append(
            {
                "params": params,
                "num_round": num_round,
                "early_stopping_rounds": early_stopping_rounds,
            }
        )
        booster = _FakeBooster()
        booster.best_ntree_limit = num_round
        return booster

    fake_module.train = fake_train
    fake_module._calls = calls

    monkeypatch.setitem(sys.modules, "xgboost", fake_module)
    return fake_module


@pytest.fixture
def fake_keras(monkeypatch):
    """Install a fake ``keras`` module that records configuration only."""

    class _FakeLayer:
        def __init__(self, kind, **kwargs):
            self.kind = kind
            self.kwargs = kwargs

    class _FakeSequential:
        def __init__(self):
            self.added_layers = []
            self.compile_kwargs = None

        def add(self, layer):
            self.added_layers.append(layer)

        def compile(self, **kwargs):
            self.compile_kwargs = kwargs

    layers_module = types.ModuleType("keras.layers")
    layers_module.Dense = lambda units, activation=None, input_shape=None: _FakeLayer(
        "Dense", units=units, activation=activation, input_shape=input_shape
    )

    models_module = types.ModuleType("keras.models")
    models_module.Sequential = _FakeSequential

    keras_module = types.ModuleType("keras")
    keras_module.layers = layers_module
    keras_module.models = models_module

    monkeypatch.setitem(sys.modules, "keras", keras_module)
    monkeypatch.setitem(sys.modules, "keras.layers", layers_module)
    monkeypatch.setitem(sys.modules, "keras.models", models_module)
    return keras_module
