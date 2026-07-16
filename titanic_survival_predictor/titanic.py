"""Titanic survival predictor pipeline.

Refactored from the original exploratory script into importable, testable
functions. Pure data-wrangling/feature-engineering functions have no
dependency on heavy ML engines and can be unit tested in isolation. The
training/inference functions depend on xgboost and keras but only at the
point they are called (not at import time), so the module can be imported
safely without those engines running.

Running this file directly (``python titanic.py``) executes the full
production pipeline: load -> clean -> engineer features -> scale -> encode
-> train an ensemble -> predict -> write results.csv.
"""
from __future__ import annotations

import pickle
from collections import Counter

import numpy as np
import pandas as pd


DATA_DIR = "./titanic"
RARE_TITLE_THRESHOLD = 8


def load_data(data_dir: str = DATA_DIR):
    """Load the raw train/test passenger data from CSV."""
    train = pd.read_csv(f"{data_dir}/train.csv", delimiter=",")
    test = pd.read_csv(f"{data_dir}/test.csv", delimiter=",")
    return train, test


def fill_missing_values(train, test):
    """Impute Age (median) and Embarked (mode) null values."""
    train = train.copy()
    test = test.copy()
    age_median = train["Age"].median()
    embarked_mode = train["Embarked"].mode()[0]
    train["Age"] = train["Age"].fillna(age_median)
    test["Age"] = test["Age"].fillna(age_median)
    train["Embarked"] = train["Embarked"].fillna(embarked_mode)
    test["Embarked"] = test["Embarked"].fillna(embarked_mode)
    return train, test


def drop_unused_columns(train, test):
    """Drop identifier / high-missingness columns that carry no signal."""
    train = train.drop(columns=["PassengerId", "Cabin", "Ticket"])
    test = test.drop(columns=["Cabin", "Ticket"])
    return train, test


def add_family_features(df):
    """Add Family_Size (SibSp + Parch) and Loner (no family aboard) columns."""
    df = df.copy()
    df["Family_Size"] = df["SibSp"] + df["Parch"]
    df["Loner"] = 1
    df.loc[df["Family_Size"] > 0, "Loner"] = 0
    return df


def extract_title(df):
    """Derive a Title column from the passenger Name and drop Name."""
    df = df.copy()
    df["Title"] = df["Name"].str.split(", ", expand=True)[1].str.split(".", expand=True)[0]
    df = df.drop(columns=["Name"])
    return df


def consolidate_rare_titles(df, threshold: int = RARE_TITLE_THRESHOLD):
    """Collapse titles occurring fewer than ``threshold`` times into 'Other'."""
    df = df.copy()
    title_counts = df["Title"].value_counts()
    rare = title_counts < threshold
    df["Title"] = df["Title"].apply(lambda x: "Other" if rare.loc[x] else x)
    return df


def fix_zero_fares(train, test):
    """Replace zero-value fares with the per-class median fare."""
    train = train.copy()
    test = test.copy()
    filter_columns = train[["Pclass", "Fare"]]
    filter_free_tickets = filter_columns[filter_columns["Fare"] > 0]
    class_groups = filter_free_tickets.groupby("Pclass")
    class_groups_median = class_groups.median()

    def col_change(x, y):
        if x == 0:
            return class_groups_median.iloc[int(y) - 1]["Fare"]
        return x

    train["Fare"] = train.apply(lambda row: col_change(row["Fare"], row["Pclass"]), axis=1)
    test["Fare"] = test.apply(lambda row: col_change(row["Fare"], row["Pclass"]), axis=1)
    return train, test


def scale_fare(train, test):
    """Log-transform and standardize the Fare column using train statistics."""
    train = train.copy()
    test = test.copy()
    train["Fare"] = train["Fare"].apply(lambda x: np.log(x))
    fare_mean = train["Fare"].mean()
    fare_std = train["Fare"].std()
    test["Fare"] = test["Fare"].apply(lambda x: np.log(x))
    test["Fare"] -= fare_mean
    test["Fare"] /= fare_std
    train["Fare"] -= fare_mean
    train["Fare"] /= fare_std
    return train, test


def scale_age(train, test):
    """Standardize the Age column using train statistics."""
    train = train.copy()
    test = test.copy()
    age_mean = train["Age"].mean()
    age_std = train["Age"].std()
    train["Age"] -= age_mean
    train["Age"] /= age_std
    test["Age"] -= age_mean
    test["Age"] /= age_std
    return train, test


def encode_categoricals(train, test):
    """One-hot encode categorical columns, including Pclass."""
    train = pd.get_dummies(train)
    train = pd.get_dummies(train, columns=["Pclass"])
    test = pd.get_dummies(test)
    test = pd.get_dummies(test, columns=["Pclass"])
    return train, test


def prepare_features(train, test):
    """Run the full cleaning / feature-engineering chain on raw data."""
    train, test = fill_missing_values(train, test)
    train, test = drop_unused_columns(train, test)
    train = add_family_features(train)
    test = add_family_features(test)
    train = extract_title(train)
    test = extract_title(test)
    train = consolidate_rare_titles(train)
    test = consolidate_rare_titles(test)
    train, test = fix_zero_fares(train, test)
    train, test = scale_fare(train, test)
    train, test = scale_age(train, test)
    train, test = encode_categoricals(train, test)
    return train, test


def build_keras_model(input_dim: int):
    """Build the small feed-forward Keras classifier used in the ensemble."""
    from keras import layers, models

    model = models.Sequential()
    model.add(layers.Dense(32, activation="relu", input_shape=(input_dim,)))
    model.add(layers.Dense(2, activation="softmax"))
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def xgb_params():
    """Hyperparameters for the XGBoost ensemble members."""
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


def train_xgb_ensemble(train_x, train_y, k: int = 4, num_round: int = 25, model_dir: str = "."):
    """Train a k-fold XGBoost ensemble and persist each fold's model to disk."""
    import xgboost as xgb

    num_samples = len(train_x) // k
    ensemble = []
    for i in range(k):
        val_data = train_x[i * num_samples: (i + 1) * num_samples]
        val_targets = train_y[i * num_samples: (i + 1) * num_samples]
        partial_train_data = np.concatenate(
            [train_x[: i * num_samples], train_x[(i + 1) * num_samples:]], axis=0
        )
        partial_train_targets = np.concatenate(
            [train_y[: i * num_samples], train_y[(i + 1) * num_samples:]], axis=0
        )
        dtrain = xgb.DMatrix(partial_train_data, partial_train_targets)
        dval = xgb.DMatrix(val_data, val_targets)
        eval_list = [(dval, "eval"), (dtrain, "train")]
        bst = xgb.train(xgb_params(), dtrain, num_round, eval_list, early_stopping_rounds=20)
        model_path = f"{model_dir}/xgb{i}.pickle.dat"
        pickle.dump(bst, open(model_path, "wb"))
        loaded_model = pickle.load(open(model_path, "rb"))
        ensemble.append(loaded_model)
    return ensemble


def predict_with_ensemble(ensemble, test_x):
    """Majority-vote predictions across all ensemble members for each row."""
    import xgboost as xgb

    final_predictions = []
    for i in range(len(test_x)):
        votes = []
        for model in ensemble:
            dtest = xgb.DMatrix([test_x[i]])
            prediction = model.predict(dtest)[0]
            votes.append(0 if prediction <= 0.5 else 1)
        most_common_vote, _ = Counter(votes).most_common(1)[0]
        final_predictions.append(most_common_vote)
    return final_predictions


def run_pipeline(data_dir: str = DATA_DIR, output_path: str = "results.csv", model_dir: str = "."):
    """Execute the full production pipeline end-to-end."""
    train, test = load_data(data_dir)
    train, test = prepare_features(train, test)

    train_y = train["Survived"]
    train = train.drop(["Survived"], axis=1).to_numpy()

    ensemble = train_xgb_ensemble(train, train_y, model_dir=model_dir)

    passenger_id = test["PassengerId"]
    test = test.drop(["PassengerId"], axis=1).to_numpy()

    predictions = predict_with_ensemble(ensemble, test)
    submission = pd.DataFrame(
        data=np.array(list(zip(passenger_id, predictions))),
        columns=["PassengerId", "Survived"],
    )
    submission.to_csv(output_path, index=False, header=["PassengerId", "Survived"])
    return submission


if __name__ == "__main__":
    run_pipeline()
