from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
)


FEATURES = [
    "event_count",
    "duration_minutes",
    "failed_login_rate",
    "unique_locations",
    "unique_devices",
    "unique_resources",
    "total_data_mb",
    "privileged_actions",
    "start_hour",
]


def load_splits():
    """
    Load only TRAIN and VALIDATION.

    The test set is intentionally not loaded here so that
    model-development decisions cannot accidentally use it.
    """

    root = Path(__file__).resolve().parents[1]

    split_dir = root / "data" / "splits"

    train = pd.read_csv(
        split_dir / "train.csv"
    )

    validation = pd.read_csv(
        split_dir / "validation.csv"
    )

    return train, validation


def prepare_xy(df: pd.DataFrame):
    """
    Build the feature matrix and attack-type target.

    Ground-truth labels are targets only and never appear
    inside X.
    """

    X = df[FEATURES].copy()
    y = df["attack_type"].copy()

    return X, y

def macro_f1_present_classes(
    y_true: pd.Series,
    y_pred,
) -> float:
    """
    Compute macro-F1 only across classes that actually
    occur in the evaluated split.

    This prevents absent validation classes from being
    incorrectly counted as zero-F1 classes.
    """

    present_labels = sorted(
        y_true.unique()
    )

    return f1_score(
        y_true,
        y_pred,
        labels=present_labels,
        average="macro",
        zero_division=0,
    )


def train_candidate_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
):
    """
    Train several Random Forest configurations.

    Model selection is based on validation macro-F1 rather
    than accuracy because attack classes are imbalanced.
    """

    candidates = [
        {
            "n_estimators": 150,
            "max_depth": 8,
            "min_samples_leaf": 2,
        },
        {
            "n_estimators": 250,
            "max_depth": 12,
            "min_samples_leaf": 2,
        },
        {
            "n_estimators": 300,
            "max_depth": None,
            "min_samples_leaf": 1,
        },
    ]

    best_model = None
    best_config = None
    best_score = -1.0

    print("\nCandidate Models")
    print("-" * 60)

    for config in candidates:

        model = RandomForestClassifier(
            n_estimators=config["n_estimators"],
            max_depth=config["max_depth"],
            min_samples_leaf=config[
                "min_samples_leaf"
            ],
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

        model.fit(
            X_train,
            y_train,
        )

        predictions = model.predict(
            X_val
        )

        macro_f1 = macro_f1_present_classes(
            y_val,
            predictions,
        )

        print(
            f"{config} -> "
            f"validation macro-F1: "
            f"{macro_f1:.3f}"
        )

        if macro_f1 > best_score:
            best_score = macro_f1
            best_model = model
            best_config = config

    return (
        best_model,
        best_config,
        best_score,
    )


def evaluate_validation(
    model,
    X_val,
    y_val,
):
    predictions = model.predict(
        X_val
    )

    accuracy = accuracy_score(
        y_val,
        predictions,
    )

    macro_f1 = macro_f1_present_classes(
        y_val,
        predictions,
    )

    print("\nValidation Performance")
    print("-" * 60)

    print(
        f"Accuracy: {accuracy:.3f}"
    )

    print(
        f"Macro-F1: {macro_f1:.3f}"
    )

    print("\nClassification Report")

    present_labels = sorted(
        y_val.unique()
    )

    print(
        classification_report(
            y_val,
            predictions,
            labels=present_labels,
            zero_division=0,
        )
    )

def print_feature_importance(
    model,
):
    importance = pd.Series(
        model.feature_importances_,
        index=FEATURES,
    ).sort_values(
        ascending=False
    )

    print("\nFeature Importance")
    print("-" * 60)

    print(
        importance.round(4)
    )


def save_model(
    model,
    config,
):
    root = Path(__file__).resolve().parents[1]

    model_dir = root / "models"

    model_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    model_path = (
        model_dir
        / "attack_classifier.joblib"
    )

    payload = {
        "model": model,
        "features": FEATURES,
        "config": config,
    }

    joblib.dump(
        payload,
        model_path,
    )

    return model_path


def main():

    print(
        "\nSentinelTwin Attack Classifier"
    )
    print("=" * 60)

    train, validation = load_splits()

    print(
        f"Training sessions: "
        f"{len(train):,}"
    )

    print(
        f"Validation sessions: "
        f"{len(validation):,}"
    )

    X_train, y_train = prepare_xy(
        train
    )

    X_val, y_val = prepare_xy(
        validation
    )

    (
        best_model,
        best_config,
        best_score,
    ) = train_candidate_models(
        X_train,
        y_train,
        X_val,
        y_val,
    )

    print("\nSelected Model")
    print("-" * 60)

    print(
        f"Configuration: {best_config}"
    )

    print(
        f"Validation macro-F1: "
        f"{best_score:.3f}"
    )

    evaluate_validation(
        best_model,
        X_val,
        y_val,
    )

    print_feature_importance(
        best_model
    )

    path = save_model(
        best_model,
        best_config,
    )

    print(
        f"\nModel saved to: {path}"
    )


if __name__ == "__main__":
    main()