from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.metrics import (
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)


THRESHOLD = 45


def load_data() -> pd.DataFrame:
    root = Path(__file__).resolve().parents[1]

    path = (
        root
        / "data"
        / "processed"
        / "context_sessions.csv"
    )

    return pd.read_csv(path)


def evaluate_binary_detection(
    df: pd.DataFrame,
) -> None:

    y_true = df["is_attack"].astype(int)
    scores = df["final_risk"] / 100

    y_pred = (
        df["final_risk"] >= THRESHOLD
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

    pr_auc = average_precision_score(
        y_true,
        scores,
    )

    roc_auc = roc_auc_score(
        y_true,
        scores,
    )

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred,
    ).ravel()

    false_positive_rate = (
        fp / (fp + tn)
        if (fp + tn) > 0
        else 0
    )

    print("\nBinary Detection")
    print("-" * 50)

    print(f"Threshold:        {THRESHOLD}")
    print(f"Precision:        {precision:.3f}")
    print(f"Recall:           {recall:.3f}")
    print(f"F1:               {f1:.3f}")
    print(f"PR-AUC:           {pr_auc:.3f}")
    print(f"ROC-AUC:          {roc_auc:.3f}")
    print(
        f"False Pos Rate:   "
        f"{false_positive_rate:.3f}"
    )

    print("\nConfusion Matrix")
    print(f"TN: {tn}")
    print(f"FP: {fp}")
    print(f"FN: {fn}")
    print(f"TP: {tp}")


def evaluate_attack_types(
    df: pd.DataFrame,
) -> None:

    rows = []

    attacks = sorted(
        df.loc[
            df["attack_type"] != "normal",
            "attack_type",
        ].unique()
    )

    for attack in attacks:

        subset = df[
            df["attack_type"] == attack
        ]

        detected = (
            subset["final_risk"]
            >= THRESHOLD
        )

        rows.append(
            {
                "attack_type": attack,
                "sessions": len(subset),
                "detected": int(
                    detected.sum()
                ),
                "missed": int(
                    (~detected).sum()
                ),
                "recall": round(
                    detected.mean(),
                    3,
                ),
                "avg_risk": round(
                    subset["final_risk"].mean(),
                    2,
                ),
                "min_risk": round(
                    subset["final_risk"].min(),
                    2,
                ),
                "max_risk": round(
                    subset["final_risk"].max(),
                    2,
                ),
            }
        )

    result = pd.DataFrame(rows)

    print("\nAttack-wise Detection")
    print("-" * 80)

    print(
        result.to_string(
            index=False
        )
    )


def evaluate_alert_budget(
    df: pd.DataFrame,
) -> None:
    """
    Simulate a SOC analyst who can only investigate
    the highest-risk fraction of all sessions.

    This is particularly useful for imbalanced
    cybersecurity datasets.
    """

    print("\nAnalyst Alert Budget")
    print("-" * 65)

    total_attacks = int(
        df["is_attack"].sum()
    )

    for budget_pct in [
        1,
        2,
        5,
        10,
    ]:

        n_alerts = max(
            1,
            int(
                len(df)
                * budget_pct
                / 100
            ),
        )

        alerts = (
            df.nlargest(
                n_alerts,
                "final_risk",
            )
        )

        attacks_found = int(
            alerts["is_attack"].sum()
        )

        alert_precision = (
            attacks_found / n_alerts
        )

        attack_coverage = (
            attacks_found
            / total_attacks
            if total_attacks
            else 0
        )

        print(
            f"Top {budget_pct:>2}% "
            f"({n_alerts:>3} alerts): "
            f"precision={alert_precision:.3f}, "
            f"attack coverage={attack_coverage:.3f}"
        )


def find_best_threshold(
    df: pd.DataFrame,
) -> None:

    y_true = df["is_attack"].astype(int)
    scores = df["final_risk"] / 100

    precision, recall, thresholds = (
        precision_recall_curve(
            y_true,
            scores,
        )
    )

    # Last precision/recall pair has no corresponding threshold.
    precision = precision[:-1]
    recall = recall[:-1]

    f1 = (
        2
        * precision
        * recall
        / (
            precision
            + recall
            + 1e-10
        )
    )

    best_index = int(
        np.argmax(f1)
    )

    best_threshold = (
        thresholds[best_index]
        * 100
    )

    print("\nThreshold Analysis")
    print("-" * 50)

    print(
        f"Best F1 threshold: "
        f"{best_threshold:.2f}"
    )

    print(
        f"Precision: "
        f"{precision[best_index]:.3f}"
    )

    print(
        f"Recall: "
        f"{recall[best_index]:.3f}"
    )

    print(
        f"F1: "
        f"{f1[best_index]:.3f}"
    )


def main():

    df = load_data()

    print(
        "\nSentinelTwin Detection Evaluation"
    )
    print("=" * 55)

    print(
        f"Sessions: {len(df):,}"
    )

    print(
        f"Attack sessions: "
        f"{df['is_attack'].sum():,}"
    )

    print(
        f"Attack prevalence: "
        f"{df['is_attack'].mean() * 100:.2f}%"
    )

    evaluate_binary_detection(df)

    evaluate_attack_types(df)

    evaluate_alert_budget(df)

    find_best_threshold(df)


if __name__ == "__main__":
    main()