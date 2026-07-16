"""Unit and integration tests for the titanic_survival_predictor pipeline.

Scope, per the project's heavy-dependency test policy:
  * Pure data-wrangling / feature-engineering functions are tested directly
    against small in-memory DataFrames (project-owned logic, no third-party
    training engines involved).
  * Functions that call into xgboost or keras are tested against fake
    modules (see conftest.py) that satisfy the import and let us assert on
    *how* the project code drives those engines (dispatch: number of folds
    trained, hyperparameters passed, majority-vote aggregation) rather than
    on any real trained model output.
  * No real local training, inference, or accelerator-backed computation
    runs in this suite.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import titanic


def _sample_train_df():
    return pd.DataFrame(
        {
            "PassengerId": [1, 2, 3, 4],
            "Survived": [0, 1, 1, 0],
            "Pclass": [3, 1, 3, 2],
            "Name": [
                "Braund, Mr. Owen",
                "Cumings, Mrs. John",
                "Heikkinen, Miss. Laina",
                "Allen, Mr. William",
            ],
            "Sex": ["male", "female", "female", "male"],
            "Age": [22.0, 38.0, np.nan, 35.0],
            "SibSp": [1, 1, 0, 0],
            "Parch": [0, 0, 0, 0],
            "Ticket": ["A/5", "PC", "STON/O2", "373450"],
            "Fare": [7.25, 71.28, 7.925, 0.0],
            "Cabin": [np.nan, "C85", np.nan, np.nan],
            "Embarked": ["S", "C", np.nan, "S"],
        }
    )


def _sample_test_df():
    return pd.DataFrame(
        {
            "PassengerId": [5, 6],
            "Pclass": [3, 1],
            "Name": ["Moran, Mr. James", "McCarthy, Mr. Timothy"],
            "Sex": ["male", "male"],
            "Age": [np.nan, 54.0],
            "SibSp": [0, 0],
            "Parch": [0, 0],
            "Ticket": ["330877", "17463"],
            "Fare": [8.4583, 51.8625],
            "Cabin": [np.nan, "E46"],
            "Embarked": ["Q", "S"],
        }
    )


# ---------------------------------------------------------------------------
# Pure data-wrangling / feature-engineering functions
# ---------------------------------------------------------------------------


def test_fill_missing_values_imputes_age_and_embarked():
    train, test = _sample_train_df(), _sample_test_df()
    train, test = titanic.fill_missing_values(train, test)

    assert train["Age"].isnull().sum() == 0
    assert test["Age"].isnull().sum() == 0
    assert train["Embarked"].isnull().sum() == 0
    # test's missing Age is filled from *train's* median, per project logic.
    assert test.loc[0, "Age"] == train["Age"].median()


def test_drop_unused_columns_removes_low_signal_fields():
    train, test = _sample_train_df(), _sample_test_df()
    train, test = titanic.drop_unused_columns(train, test)

    for col in ("PassengerId", "Cabin", "Ticket"):
        assert col not in train.columns
    for col in ("Cabin", "Ticket"):
        assert col not in test.columns
    assert "PassengerId" in test.columns  # kept for the submission file


def test_add_family_features_computes_size_and_loner_flag():
    df = _sample_train_df()
    df = titanic.add_family_features(df)

    assert list(df["Family_Size"]) == [1, 1, 0, 0]
    assert list(df["Loner"]) == [0, 0, 1, 1]


def test_extract_title_parses_name_and_drops_it():
    df = _sample_train_df()
    df = titanic.extract_title(df)

    assert "Name" not in df.columns
    assert list(df["Title"]) == ["Mr", "Mrs", "Miss", "Mr"]


def test_consolidate_rare_titles_collapses_below_threshold():
    df = pd.DataFrame({"Title": ["Mr"] * 5 + ["Countess"] * 1})
    df = titanic.consolidate_rare_titles(df, threshold=2)

    assert set(df["Title"]) == {"Mr", "Other"}
    assert (df["Title"] == "Other").sum() == 1


def test_fix_zero_fares_uses_class_median():
    # All three classes need >=1 non-zero fare, matching the real dataset's
    # shape: the project's fare-lookup indexes by Pclass position, which
    # assumes classes 1-3 are all represented in the non-zero-fare groups.
    train = pd.DataFrame(
        {"Pclass": [1, 1, 2, 3, 3], "Fare": [100.0, 200.0, 50.0, 20.0, 0.0]}
    )
    test = pd.DataFrame({"Pclass": [1], "Fare": [0.0]})

    train_out, test_out = titanic.fix_zero_fares(train, test)

    # Class 1 median is 150.0 and is used for the zero-fare row in `test`.
    assert test_out.loc[0, "Fare"] == 150.0
    # Class 3's own zero fare is replaced with class 3's median (20.0).
    assert train_out.loc[4, "Fare"] == 20.0
    assert (train_out["Fare"] > 0).all()


def test_scale_fare_standardizes_using_train_statistics():
    train = pd.DataFrame({"Fare": [np.e, np.e**2, np.e**3]})
    test = pd.DataFrame({"Fare": [np.e**2]})

    train_out, test_out = titanic.scale_fare(train, test)

    assert train_out["Fare"].mean() == pytest.approx(0.0, abs=1e-9)
    assert train_out["Fare"].std() == pytest.approx(1.0, abs=1e-9)


def test_scale_age_standardizes_using_train_statistics():
    train = pd.DataFrame({"Age": [20.0, 30.0, 40.0]})
    test = pd.DataFrame({"Age": [30.0]})

    train_out, test_out = titanic.scale_age(train, test)

    assert train_out["Age"].mean() == pytest.approx(0.0, abs=1e-9)
    assert test_out.loc[0, "Age"] == pytest.approx(0.0, abs=1e-9)


def test_encode_categoricals_one_hot_encodes_pclass_and_sex():
    train = pd.DataFrame({"Pclass": [1, 2, 3], "Sex": ["male", "female", "male"]})
    test = pd.DataFrame({"Pclass": [1, 2], "Sex": ["female", "male"]})

    train_out, test_out = titanic.encode_categoricals(train, test)

    assert {"Pclass_1", "Pclass_2", "Pclass_3"}.issubset(train_out.columns)
    assert {"Sex_male", "Sex_female"}.issubset(train_out.columns)


def test_xgb_params_returns_expected_hyperparameter_keys():
    params = titanic.xgb_params()

    assert params["objective"] == "binary:logistic"
    assert params["max_depth"] == 4


# ---------------------------------------------------------------------------
# Dispatch tests: project code driving stubbed heavy engines
# ---------------------------------------------------------------------------


def test_train_xgb_ensemble_trains_k_folds_without_real_xgboost(fake_xgboost, tmp_path):
    train_x = np.arange(40).reshape(20, 2).astype(float)
    train_y = np.array([0, 1] * 10)

    ensemble = titanic.train_xgb_ensemble(
        train_x, train_y, k=4, num_round=3, model_dir=str(tmp_path)
    )

    assert len(ensemble) == 4
    assert len(fake_xgboost._calls["train"]) == 4
    for call in fake_xgboost._calls["train"]:
        assert call["num_round"] == 3
        assert call["params"]["objective"] == "binary:logistic"
    # Each fold's model artifact must be handed off to disk and reloaded.
    for i in range(4):
        assert (tmp_path / f"xgb{i}.pickle.dat").exists()


def test_predict_with_ensemble_majority_votes_across_models(fake_xgboost):
    class _AllOnes:
        def predict(self, dmatrix, ntree_limit=None):
            return np.array([0.9])

    class _AllZeros:
        def predict(self, dmatrix, ntree_limit=None):
            return np.array([0.1])

    # 2 vs 1 majority should win for each of two test rows.
    ensemble = [_AllOnes(), _AllOnes(), _AllZeros()]
    predictions = titanic.predict_with_ensemble(ensemble, np.zeros((2, 3)))

    assert predictions == [1, 1]


def test_build_keras_model_configures_layers_without_real_keras(fake_keras):
    model = titanic.build_keras_model(input_dim=10)

    assert len(model.added_layers) == 2
    assert model.added_layers[0].kwargs["units"] == 32
    assert model.added_layers[1].kwargs["units"] == 2
    assert model.compile_kwargs["optimizer"] == "adam"


# ---------------------------------------------------------------------------
# Integration test: project-owned data flow through the full pipeline
# ---------------------------------------------------------------------------


def test_run_pipeline_data_flow_shapes_and_schema(monkeypatch, fake_xgboost, tmp_path):
    """End-to-end wiring check: schema/shape/artifact handoff only.

    No real training or inference engine executes -- xgboost is stubbed via
    the fake_xgboost fixture -- so this validates the project's own data
    flow (load -> feature engineering -> ensemble dispatch -> submission
    artifact), not model quality.
    """
    monkeypatch.setattr(titanic, "load_data", lambda data_dir=None: (_sample_train_df(), _sample_test_df()))

    output_path = tmp_path / "results.csv"
    submission = titanic.run_pipeline(
        data_dir="unused", output_path=str(output_path), model_dir=str(tmp_path)
    )

    assert list(submission.columns) == ["PassengerId", "Survived"]
    assert len(submission) == 2  # matches the 2-row sample test set
    assert output_path.exists()
    written = pd.read_csv(output_path)
    assert list(written.columns) == ["PassengerId", "Survived"]
    assert len(written) == 2
