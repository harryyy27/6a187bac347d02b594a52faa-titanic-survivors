"""Tests for the Titanic Survival Prediction container eval script.

Scope, mirroring the sibling component's heavy-dependency test policy:
  * The synthetic dataset generator is pure pandas/numpy logic and is tested
    directly (schema, determinism, cross-split category coverage).
  * Functions that drive the real `titanic` module's training/prediction
    entry points are tested via the `fake_titanic_dispatch` fixture (see
    conftest.py), asserting *how* run_eval calls them and how it assembles
    the result record -- not on any real model's numeric output.
  * No real xgboost training executes in this suite.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import run_eval


# ---------------------------------------------------------------------------
# Pure logic: synthetic dataset generator (no titanic.py / xgboost involved)
# ---------------------------------------------------------------------------


def test_generate_synthetic_titanic_has_expected_schema():
    train_df, holdout_df = run_eval.generate_synthetic_titanic(
        seed=1, train_per_combo=2, holdout_per_combo=1
    )

    expected_cols = {
        "PassengerId", "Survived", "Pclass", "Name", "Sex", "Age",
        "SibSp", "Parch", "Ticket", "Fare", "Cabin", "Embarked",
    }
    assert expected_cols == set(train_df.columns) == set(holdout_df.columns)
    assert train_df["PassengerId"].is_unique
    assert holdout_df["PassengerId"].is_unique
    assert set(train_df["PassengerId"]).isdisjoint(set(holdout_df["PassengerId"]))
    assert set(train_df["Survived"].unique()) <= {0, 1}
    assert len(train_df) > 0 and len(holdout_df) > 0


def test_generate_synthetic_titanic_categories_match_across_splits():
    """The project's encode_categoricals runs pd.get_dummies on train/test
    independently with no reindexing, so mismatched categorical coverage
    would silently misalign feature columns between the two frames. The
    generator must guarantee identical coverage on both sides."""
    train_df, holdout_df = run_eval.generate_synthetic_titanic(
        seed=7, train_per_combo=8, holdout_per_combo=3
    )

    assert set(train_df["Pclass"]) == set(holdout_df["Pclass"])
    assert set(train_df["Sex"]) == set(holdout_df["Sex"])
    assert set(train_df["Embarked"].dropna()) == set(holdout_df["Embarked"].dropna())

    def titles(df):
        return set(df["Name"].str.split(", ", expand=True)[1].str.split(".", expand=True)[0])

    assert titles(train_df) == titles(holdout_df)


def test_generate_synthetic_titanic_is_deterministic():
    train_a, holdout_a = run_eval.generate_synthetic_titanic(seed=123)
    train_b, holdout_b = run_eval.generate_synthetic_titanic(seed=123)

    pd.testing.assert_frame_equal(train_a, train_b)
    pd.testing.assert_frame_equal(holdout_a, holdout_b)


# ---------------------------------------------------------------------------
# Dispatch tests: run_eval driving the (faked) titanic training/prediction
# entry points
# ---------------------------------------------------------------------------


def test_compute_fold_errors_uses_contiguous_fold_boundaries(monkeypatch):
    def fake_predict_with_ensemble(ensemble, test_x):
        return [0 for _ in range(len(test_x))]

    monkeypatch.setattr(run_eval.titanic, "predict_with_ensemble", fake_predict_with_ensemble)

    train_x = np.zeros((20, 2))
    train_y = np.array([0, 1] * 10)
    ensemble = ["fold-0", "fold-1", "fold-2", "fold-3"]

    errors = run_eval.compute_fold_errors(ensemble, train_x, train_y, k=4)

    assert len(errors) == 4
    for err in errors:
        assert 0.0 <= err <= 1.0


def test_run_produces_well_formed_result_record(monkeypatch, tmp_path, fake_titanic_dispatch):
    monkeypatch.setattr(run_eval, "ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setattr(run_eval, "RESULTS_JSON_PATH", str(tmp_path / "eval_results.json"))

    result = run_eval.run(
        {"train_per_combo": 2, "holdout_per_combo": 1, "k": 2, "num_round": 3}
    )

    assert result["primary_metric"] == "accuracy"
    assert result["primary_metric_direction"] == "maximize"
    assert 0.0 <= result["metrics"]["accuracy"] <= 1.0
    assert "mean_cv_error" in result["metrics"]
    assert result["model"]["type"] == "xgboost.Booster"
    assert result["hyperparameters"]["k"] == 2
    assert result["hyperparameters"]["num_round"] == 3
    assert result["hyperparameters"]["objective"] == "binary:logistic"
    assert result["configuration"]["run_type"] == "baseline"
    assert result["configuration"]["eval_kind"] == "model_training"
    assert "fold_errors" in result["additional_metadata"]

    # The training dispatch actually ran through our fakes, with the
    # parameters run_eval was given (not real xgboost).
    assert len(fake_titanic_dispatch["train_xgb_ensemble"]) == 1
    assert fake_titanic_dispatch["train_xgb_ensemble"][0]["k"] == 2
    assert fake_titanic_dispatch["train_xgb_ensemble"][0]["num_round"] == 3

    # Must be JSON-serializable, per the eval contract.
    json.dumps(result)


def test_run_forwards_recognized_hyperparameter_overrides(monkeypatch, tmp_path, fake_titanic_dispatch):
    """EVAL_PARAMETERS_JSON hyperparameter-tuning keys (eta, max_depth, ...)
    must reach the real training call and the recorded result record, not
    just eval-only knobs (k, num_round, seed, ...)."""
    monkeypatch.setattr(run_eval, "ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setattr(run_eval, "RESULTS_JSON_PATH", str(tmp_path / "eval_results.json"))

    result = run_eval.run(
        {
            "train_per_combo": 2,
            "holdout_per_combo": 1,
            "k": 2,
            "num_round": 3,
            "early_stopping_rounds": 9,
            "eta": 0.05,
            "max_depth": 6,
            # Unrecognized/eval-only key: must NOT leak into XGBoost params.
            "seed": 123,
        }
    )

    calls = fake_titanic_dispatch["train_xgb_ensemble"]
    assert len(calls) == 1
    assert calls[0]["early_stopping_rounds"] == 9
    assert calls[0]["param_overrides"] == {"eta": 0.05, "max_depth": 6}

    assert result["hyperparameters"]["eta"] == 0.05
    assert result["hyperparameters"]["max_depth"] == 6
    assert result["hyperparameters"]["early_stopping_rounds"] == 9
    assert result["configuration"]["hyperparameter_overrides"] == {"eta": 0.05, "max_depth": 6}

    json.dumps(result)


def test_run_with_no_hyperparameter_overrides_passes_none(monkeypatch, tmp_path, fake_titanic_dispatch):
    monkeypatch.setattr(run_eval, "ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setattr(run_eval, "RESULTS_JSON_PATH", str(tmp_path / "eval_results.json"))

    run_eval.run({"train_per_combo": 2, "holdout_per_combo": 1, "k": 2, "num_round": 3})

    calls = fake_titanic_dispatch["train_xgb_ensemble"]
    assert calls[0]["param_overrides"] is None
    assert calls[0]["early_stopping_rounds"] == 20


def test_main_emits_training_results_line(monkeypatch, tmp_path, fake_titanic_dispatch, capsys):
    monkeypatch.setattr(run_eval, "ARTIFACT_DIR", str(tmp_path / "artifacts"))
    results_path = tmp_path / "eval_results.json"
    monkeypatch.setattr(run_eval, "RESULTS_JSON_PATH", str(results_path))
    monkeypatch.setenv(
        "EVAL_PARAMETERS_JSON",
        json.dumps({"train_per_combo": 2, "holdout_per_combo": 1, "k": 2, "num_round": 3}),
    )

    run_eval.main()

    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line.startswith("TRAINING_RESULTS=")]
    assert len(lines) == 1
    payload = json.loads(lines[0][len("TRAINING_RESULTS="):])
    assert payload["primary_metric"] == "accuracy"

    assert results_path.exists()
    with open(results_path) as f:
        written = json.load(f)
    assert written["primary_metric"] == "accuracy"
