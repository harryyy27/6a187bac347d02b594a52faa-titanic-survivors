"""Baseline container eval for the Titanic Survival Prediction feature.

This is an eval-owned script, not part of the production pipeline. It:

1. Builds a small, deterministic, Titanic-schema passenger dataset (the repo
   does not bundle the real Kaggle CSVs, and downloading them would require
   network access/credentials that are unavailable and non-deterministic in
   a container eval). The synthetic generator guarantees every categorical
   level (Pclass, Sex, Embarked, Title) appears in both the train and
   holdout splits, so the project's own ``encode_categoricals`` (independent
   ``pd.get_dummies`` calls on train/test) produces matching columns.
2. Drives the *actual* project pipeline functions from
   ``titanic_survival_predictor/titanic.py`` (``prepare_features``,
   ``train_xgb_ensemble``, ``predict_with_ensemble``) -- no reimplementation
   of feature engineering or modeling logic.
3. Computes baseline metrics (holdout accuracy, mean k-fold CV error) and
   emits a parseable run record: ``eval_results.json`` plus a
   ``TRAINING_RESULTS=<json>`` stdout line.

Run directly: ``python evals/titanic_survival_predictor/run_eval.py``
Optional overrides via the ``EVAL_PARAMETERS_JSON`` environment variable,
e.g. ``{"k": 3, "num_round": 10}``.
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
_COMPONENT_DIR = os.path.join(_PROJECT_ROOT, "titanic_survival_predictor")
if _COMPONENT_DIR not in sys.path:
    sys.path.insert(0, _COMPONENT_DIR)

import titanic  # noqa: E402  (project pipeline module, path set up above)


DEFAULT_SEED = 42
DEFAULT_TRAIN_PER_COMBO = 8
DEFAULT_HOLDOUT_PER_COMBO = 3
DEFAULT_K = 4
DEFAULT_NUM_ROUND = 25

RESULTS_JSON_PATH = os.path.join(_THIS_DIR, "eval_results.json")
ARTIFACT_DIR = os.path.join(_THIS_DIR, "artifacts")

# (sex, title_group) pairs used to build the synthetic passenger population.
# Kept to the four most common real-world titles so every level stays well
# above titanic.RARE_TITLE_THRESHOLD in both splits -- no rare-title
# collapsing, so Title_* dummy columns line up between train and holdout.
_SEX_TITLES = [("male", "Mr"), ("male", "Master"), ("female", "Mrs"), ("female", "Miss")]
_PCLASSES = [1, 2, 3]
_EMBARKED = ["S", "C", "Q"]

_FIRST_NAMES = {
    "male": ["James", "John", "William", "Charles", "Henry", "George", "Edward", "Arthur"],
    "female": ["Mary", "Anna", "Margaret", "Elizabeth", "Alice", "Florence", "Helen", "Dorothy"],
}
_LAST_NAMES = [
    "Smith", "Brown", "Taylor", "Wilson", "Davies", "Evans", "Thomas", "Roberts",
    "Johnson", "Walker", "Harris", "Clarke", "Wright", "Green", "Baker", "Hall",
]


def generate_synthetic_titanic(
    seed: int = DEFAULT_SEED,
    train_per_combo: int = DEFAULT_TRAIN_PER_COMBO,
    holdout_per_combo: int = DEFAULT_HOLDOUT_PER_COMBO,
):
    """Build a deterministic Titanic-schema train/holdout dataset.

    Every (Pclass, Sex/Title, Embarked) combination is materialized with a
    fixed row count in *both* splits, guaranteeing identical categorical
    coverage on both sides (the real project's ``encode_categoricals`` runs
    ``pd.get_dummies`` on train and test independently, with no reindexing,
    so mismatched categories would silently misalign feature columns).

    Returns ``(train_df, holdout_df)`` where both retain a ``Survived``
    column -- the caller is responsible for stripping it from the frame it
    hands to the pipeline's ``test`` side and keeping the true labels aside.
    """
    rng = np.random.default_rng(seed)
    combos = list(itertools.product(_PCLASSES, _SEX_TITLES, _EMBARKED))

    rows = []
    passenger_id = 1
    for split, n_per_combo in (("train", train_per_combo), ("holdout", holdout_per_combo)):
        for pclass, (sex, title), embarked in combos:
            for _ in range(n_per_combo):
                if title == "Master":
                    age = float(rng.integers(1, 13))
                elif sex == "female" and title == "Miss":
                    age = float(rng.integers(1, 40))
                else:
                    age = float(rng.integers(18, 70))
                # Sprinkle in a few missing ages to exercise fill_missing_values.
                if rng.random() < 0.08:
                    age = np.nan

                sibsp = int(rng.integers(0, 3))
                parch = int(rng.integers(0, 2))

                base_fare = {1: 60.0, 2: 20.0, 3: 10.0}[pclass]
                fare = float(max(0.1, rng.lognormal(mean=np.log(base_fare), sigma=0.4)))
                # Sprinkle a few zero fares to exercise fix_zero_fares.
                if rng.random() < 0.03:
                    fare = 0.0

                embarked_value = embarked
                if rng.random() < 0.02:
                    embarked_value = np.nan

                first = _FIRST_NAMES[sex][int(rng.integers(0, len(_FIRST_NAMES[sex])))]
                last = _LAST_NAMES[int(rng.integers(0, len(_LAST_NAMES)))]
                name = f"{last}, {title}. {first}"

                score = (2.2 if sex == "female" else -0.3)
                score += {1: 1.1, 2: 0.2, 3: -0.9}[pclass]
                if not np.isnan(age) and age < 13:
                    score += 1.3
                score += 0.4 * np.log1p(fare) / 5.0
                score += rng.normal(0, 1.0)
                prob = 1.0 / (1.0 + np.exp(-score))
                survived = int(rng.binomial(1, prob))

                rows.append(
                    {
                        "PassengerId": passenger_id,
                        "Survived": survived,
                        "Pclass": pclass,
                        "Name": name,
                        "Sex": sex,
                        "Age": age,
                        "SibSp": sibsp,
                        "Parch": parch,
                        "Ticket": f"TICK{passenger_id}",
                        "Fare": fare,
                        "Cabin": np.nan,
                        "Embarked": embarked_value,
                        "_split": split,
                    }
                )
                passenger_id += 1

    full = pd.DataFrame(rows)
    train_df = full[full["_split"] == "train"].drop(columns=["_split"]).reset_index(drop=True)
    holdout_df = full[full["_split"] == "holdout"].drop(columns=["_split"]).reset_index(drop=True)
    return train_df, holdout_df


def compute_fold_errors(ensemble, train_x, train_y, k: int):
    """Per-fold holdout error, using the same fold boundaries as
    ``titanic.train_xgb_ensemble`` (contiguous blocks of ``len(train_x)//k``).

    Reuses ``titanic.predict_with_ensemble`` (single-model "ensemble") so no
    prediction logic is reimplemented here.
    """
    num_samples = len(train_x) // k
    train_y_arr = np.asarray(train_y)
    errors = []
    for i, model in enumerate(ensemble):
        val_x = train_x[i * num_samples: (i + 1) * num_samples]
        val_y = train_y_arr[i * num_samples: (i + 1) * num_samples]
        preds = np.array(titanic.predict_with_ensemble([model], val_x))
        errors.append(float(np.mean(preds != val_y)))
    return errors


def _load_eval_parameters():
    raw = os.environ.get("EVAL_PARAMETERS_JSON", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def run(params: dict) -> dict:
    """Execute the baseline eval end-to-end and return the run record dict."""
    start = time.time()

    seed = int(params.get("seed", DEFAULT_SEED))
    train_per_combo = int(params.get("train_per_combo", DEFAULT_TRAIN_PER_COMBO))
    holdout_per_combo = int(params.get("holdout_per_combo", DEFAULT_HOLDOUT_PER_COMBO))
    k = int(params.get("k", DEFAULT_K))
    num_round = int(params.get("num_round", DEFAULT_NUM_ROUND))
    early_stopping_rounds = int(params.get("early_stopping_rounds", 20))

    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    train_df, holdout_df = generate_synthetic_titanic(
        seed=seed, train_per_combo=train_per_combo, holdout_per_combo=holdout_per_combo
    )
    holdout_true = holdout_df["Survived"].to_numpy()
    holdout_for_pipeline = holdout_df.drop(columns=["Survived"])

    train_proc, holdout_proc = titanic.prepare_features(train_df, holdout_for_pipeline)

    train_y = train_proc["Survived"]
    train_x = train_proc.drop(["Survived"], axis=1).to_numpy()

    ensemble = titanic.train_xgb_ensemble(
        train_x, train_y, k=k, num_round=num_round, model_dir=ARTIFACT_DIR
    )

    passenger_id = holdout_proc["PassengerId"]
    holdout_x = holdout_proc.drop(["PassengerId"], axis=1).to_numpy()
    predictions = titanic.predict_with_ensemble(ensemble, holdout_x)

    accuracy = float(np.mean(np.array(predictions) == holdout_true))
    fold_errors = compute_fold_errors(ensemble, train_x, train_y, k=k)
    mean_cv_error = float(np.mean(fold_errors)) if fold_errors else None

    submission = pd.DataFrame(
        {"PassengerId": passenger_id.to_numpy(), "Survived": predictions}
    )
    submission_path = os.path.join(ARTIFACT_DIR, "holdout_predictions.csv")
    submission.to_csv(submission_path, index=False, header=["PassengerId", "Survived"])

    duration = time.time() - start

    model_hyperparameters = dict(titanic.xgb_params())
    model_hyperparameters.update(
        {
            "k": k,
            "num_round": num_round,
            "early_stopping_rounds": early_stopping_rounds,
        }
    )

    result = {
        "metrics": {
            "accuracy": accuracy,
            "mean_cv_error": mean_cv_error,
        },
        "primary_metric": "accuracy",
        "primary_metric_direction": "maximize",
        "artifact_uri": os.path.relpath(ARTIFACT_DIR, _PROJECT_ROOT),
        "model": {
            "name": "XGBoostKFoldEnsemble",
            "type": "xgboost.Booster",
        },
        "hyperparameters": model_hyperparameters,
        "configuration": {
            "dataset": "synthetic_titanic_schema_v1",
            "dataset_seed": seed,
            "train_rows": int(len(train_df)),
            "holdout_rows": int(len(holdout_df)),
            "train_per_combo": train_per_combo,
            "holdout_per_combo": holdout_per_combo,
            "rare_title_threshold": titanic.RARE_TITLE_THRESHOLD,
            "feature_engineering": [
                "fill_missing_values",
                "drop_unused_columns",
                "add_family_features",
                "extract_title",
                "consolidate_rare_titles",
                "fix_zero_fares",
                "add_fare_per_person",
                "scale_fare",
                "scale_fare_per_person",
                "scale_age",
                "encode_categoricals",
            ],
            "split": "stratified_by_pclass_sex_title_embarked",
            "run_type": "baseline",
            "eval_kind": "model_training",
        },
        "additional_metadata": {
            "fold_errors": fold_errors,
            "duration_seconds": duration,
            "notes": (
                "Real Kaggle train.csv/test.csv are not bundled with the repo, "
                "so this eval generates a deterministic Titanic-schema synthetic "
                "dataset (fixed numpy seed) and drives the project's own "
                "titanic.py feature-engineering and k-fold XGBoost ensemble "
                "functions unmodified."
            ),
            "keras_mlp_helper": "unused by run_pipeline / this eval; not exercised",
        },
    }
    return result


def main():
    params = _load_eval_parameters()
    result = run(params)

    with open(RESULTS_JSON_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print("TRAINING_RESULTS=" + json.dumps(result))
    return result


if __name__ == "__main__":
    main()
