from __future__ import annotations

from pathlib import Path

import pandas as pd

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

from src.inference import SentinelTwinInference


RISK_THRESHOLD = 45.0


def load_data():
    root = Path(__file__).resolve().parents[1]

    test = pd.read_csv(
        root / "data" / "splits" / "test.csv",
        parse_dates=["session_start"],
    )

    scored = pd.read_csv(
        root
        / "data"
        / "processed"
        / "context_sessions.csv",
        parse_dates=["session_start"],
    )

    return test, scored


def get_test_scored_sessions(
    test: pd.DataFrame,
    scored: pd.DataFrame,
) -> pd.DataFrame:
    """
    Select from the scored dataset only sessions belonging
    to the chronologically held-out test split.

    session_id provides an exact join key.
    """

    test_ids = set(test["session_id"])

    result = scored[
        scored["session_id"].isin(test_ids)
    ].copy()

    return (
        result.sort_values("session_start")
        .reset_index(drop=True)
    )


def evaluate_detection(
    df: pd.DataFrame,
):
    """
    Evaluate SentinelTwin's binary question:

        malicious or not malicious?

    based only on final risk.
    """

    y_true = df["is_attack"].astype(int)

    y_pred = (
        df["final_risk"] >= RISK_THRESHOLD
    ).astype(int)

    precision = precision_score(
        y_true,
        y_pred,
        zero_division=0,
    )

    recall = recall_score(
        y_true,
        y_pred,
        zero_division=0,
    )

    f1 = f1_score(
        y_true,
        y_pred,
        zero_division=0,
    )

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1],
    ).ravel()

    print("\nHELD-OUT BINARY DETECTION")
    print("-" * 65)

    print(f"Risk threshold: {RISK_THRESHOLD:.1f}")
    print(f"Precision:      {precision:.3f}")
    print(f"Recall:         {recall:.3f}")
    print(f"F1:             {f1:.3f}")

    print("\nConfusion Matrix")
    print(f"TN: {tn}")
    print(f"FP: {fp}")
    print(f"FN: {fn}")
    print(f"TP: {tp}")

    print(
        f"\nFalse-positive rate: "
        f"{fp / (fp + tn):.3%}"
    )

    return y_pred


def evaluate_attack_recall(
    df: pd.DataFrame,
):
    print("\nATTACK-WISE DETECTION")
    print("-" * 65)

    attacks = df[
        df["is_attack"] == 1
    ].copy()

    attacks["detected"] = (
        attacks["final_risk"]
        >= RISK_THRESHOLD
    ).astype(int)

    report = (
        attacks
        .groupby("attack_type")
        .agg(
            sessions=("session_id", "count"),
            detected=("detected", "sum"),
            avg_risk=("final_risk", "mean"),
        )
    )

    report["recall"] = (
        report["detected"]
        / report["sessions"]
    )

    print(
        report.round(3)
    )


def evaluate_end_to_end_classification(
    df: pd.DataFrame,
):
    """
    Full system evaluation:

    Risk engine first decides whether an alert exists.

    Only flagged sessions are passed to the frozen
    attack classifier.

    Unflagged sessions become 'normal'.
    """

    engine = SentinelTwinInference()

    classified = engine.classify_alerts(
        df,
        risk_column="final_risk",
        threshold=RISK_THRESHOLD,
    )

    y_true = classified["attack_type"]

    y_pred = classified[
        "predicted_attack_type"
    ]

    labels = sorted(
        y_true.unique()
    )

    macro_f1 = f1_score(
        y_true,
        y_pred,
        labels=labels,
        average="macro",
        zero_division=0,
    )

    print("\nEND-TO-END ATTACK IDENTIFICATION")
    print("-" * 65)

    print(
        f"Macro-F1: {macro_f1:.3f}"
    )

    print()

    print(
        classification_report(
            y_true,
            y_pred,
            labels=labels,
            zero_division=0,
        )
    )

    return classified


def save_results(
    df: pd.DataFrame,
):
    root = Path(__file__).resolve().parents[1]

    output_dir = (
        root
        / "data"
        / "results"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        output_dir
        / "system_test_results.csv"
    )

    df.to_csv(
        path,
        index=False,
    )

    return path


def main():

    print(
        "\nSentinelTwin Final System Evaluation"
    )
    print("=" * 65)

    test, scored = load_data()

    test_scored = get_test_scored_sessions(
        test,
        scored,
    )

    print(
        f"\nExpected test sessions: "
        f"{len(test):,}"
    )

    print(
        f"Matched scored sessions: "
        f"{len(test_scored):,}"
    )

    if len(test_scored) != len(test):
        raise RuntimeError(
            "Test/scored session mismatch. "
            "Evaluation aborted."
        )

    print(
        f"Attack sessions: "
        f"{test_scored['is_attack'].sum():,}"
    )

    evaluate_detection(
        test_scored
    )

    evaluate_attack_recall(
        test_scored
    )

    classified = (
        evaluate_end_to_end_classification(
            test_scored
        )
    )

    path = save_results(
        classified
    )

    print(
        f"\nFinal test results saved to: "
        f"{path}"
    )


if __name__ == "__main__":
    main()