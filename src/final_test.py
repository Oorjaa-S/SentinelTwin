from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)


def load_test_and_model():
    root = Path(__file__).resolve().parents[1]

    test = pd.read_csv(root / "data" / "splits" / "test.csv")

    payload = joblib.load(root / "models" / "attack_classifier.joblib")

    return test, payload


def main():

    print("\nSentinelTwin Held-Out Attack Classification")
    print("=" * 65)

    test, payload = load_test_and_model()

    model = payload["model"]
    features = payload["features"]
    config = payload["config"]

    X_test = test[features].copy()
    y_test = test["attack_type"].copy()

    # --------------------------------------------------
    # ONE-WAY INFERENCE
    # No fitting or tuning occurs below this point.
    # --------------------------------------------------

    predictions = model.predict(X_test)

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    present_labels = sorted(y_test.unique())

    macro_f1 = f1_score(
        y_test,
        predictions,
        labels=present_labels,
        average="macro",
        zero_division=0,
    )

    print(f"\nTest sessions: {len(test):,}")

    print(
        f"Date range: "
        f"{test['session_start'].min()} "
        f"-> {test['session_start'].max()}"
    )

    print(f"\nFrozen model configuration: {config}")

    print("\nFinal Test Performance")
    print("-" * 65)

    print(f"Accuracy: {accuracy:.3f}")
    print(f"Macro-F1: {macro_f1:.3f}")

    print("\nPer-Class Performance")
    print("-" * 65)

    print(
        classification_report(
            y_test,
            predictions,
            labels=present_labels,
            zero_division=0,
        )
    )

    # --------------------------------------------------
    # Confusion matrix
    # --------------------------------------------------

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=present_labels,
    )

    matrix_df = pd.DataFrame(
        matrix,
        index=present_labels,
        columns=present_labels,
    )

    print("\nConfusion Matrix")
    print("-" * 65)
    print(matrix_df)

    # --------------------------------------------------
    # Save individual predictions for later dashboard
    # --------------------------------------------------

    results = test.copy()

    results["predicted_attack_type"] = predictions

    probabilities = model.predict_proba(X_test)

    results["classification_confidence"] = probabilities.max(axis=1)

    results["classification_correct"] = (
        results["attack_type"] == results["predicted_attack_type"]
    ).astype(int)

    root = Path(__file__).resolve().parents[1]

    output_dir = root / "data" / "results"

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / "test_classification.csv"

    results.to_csv(
        output_path,
        index=False,
    )

    print(f"\nPredictions saved to: {output_path}")


if __name__ == "__main__":
    main()
