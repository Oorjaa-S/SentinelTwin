from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.behavioral_twin import BehavioralTwin
from src.multi_horizon import MultiHorizonRisk
from src.context_engine import calculate_context_signals
from src.trust_gate import (
    TrustGate,
    QuarantineManager,
)


def load_sessions() -> pd.DataFrame:
    root = Path(__file__).resolve().parents[1]

    path = root / "data" / "processed" / "sessions.csv"

    df = pd.read_csv(
        path,
        parse_dates=["session_start", "session_end"],
    )

    return df.sort_values(
        "session_start"
    ).reset_index(drop=True)


def run_online_pipeline(
    sessions: pd.DataFrame,
) -> pd.DataFrame:

    twin = BehavioralTwin(
        window_size=30,
        min_personal_history=5,
    )

    horizon = MultiHorizonRisk()

    gate = TrustGate(
        trusted_threshold=25,
        suspicious_threshold=45,
        mature_history=15,
    )

    quarantine = QuarantineManager(
    required_consistency=3,
    max_history=5,
    )

    results = []

    for _, session in sessions.iterrows():

        # ==================================================
        # 1. SCORE AGAINST CURRENT BEHAVIORAL TWIN
        # ==================================================

        twin_scores = twin.score_session(session)

        working = session.copy()

        for key, value in twin_scores.items():
            working[key] = value

        # ==================================================
        # 2. MULTI-HORIZON HISTORY
        # ==================================================

        horizon_scores = horizon.score(
            user_id=session["user_id"],
            current_deviation=float(
                twin_scores["behavioral_deviation"]
            ),
        )

        for key, value in horizon_scores.items():
            working[key] = value

        # ==================================================
        # 3. CONTEXT ENGINE
        # ==================================================

        context_scores = calculate_context_signals(
            working
        )

        for key, value in context_scores.items():
            working[key] = value

        # ==================================================
        # 4. FINAL RISK
        # ==================================================

        final_risk = (
            0.35 * float(
                working["immediate_risk"]
            )
            + 0.35 * float(
                working["context_risk"]
            )
            + 0.30 * float(
                working["multi_horizon_risk"]
            )
        )

        working["final_risk"] = round(
            float(
                np.clip(final_risk, 0, 100)
            ),
            2,
        )

        # ==================================================
        # 5. TRUST GATE
        #
        # Notice:
        # is_attack is NOT passed into the decision.
        # ==================================================

        gate_result = gate.evaluate(working)

        for key, value in gate_result.items():
            working[key] = value

        # ==================================================
        # 6. ADAPTATION
        # ==================================================

        # ==================================================
        # 6. SAFE ADAPTATION + QUARANTINE RECOVERY
        # ==================================================

        learn_from_session = False

        if gate_result["learn_allowed"]:

            # Immediately trusted observation.
            learn_from_session = True

            working["quarantine_status"] = "NOT_REQUIRED"
            working["consistency_count"] = 0
            working["released_from_quarantine"] = False

        elif gate_result["trust_decision"] == "QUARANTINE":

            quarantine_result = quarantine.evaluate(
                working
            )

            working["quarantine_status"] = (
                quarantine_result["quarantine_status"]
            )

            working["consistency_count"] = (
                quarantine_result["consistency_count"]
            )

            working["released_from_quarantine"] = (
                quarantine_result["release_for_learning"]
            )

            if quarantine_result["release_for_learning"]:
                learn_from_session = True

        else:

            # REJECT sessions can never automatically update
            # the Behavioral Twin.
            working["quarantine_status"] = "REJECTED"
            working["consistency_count"] = 0
            working["released_from_quarantine"] = False


        if learn_from_session:
            twin.update(session)


        working["actually_learned"] = (
            learn_from_session
        )

        # Historical risk observes every session.
        horizon.update(
            user_id=session["user_id"],
            immediate_risk=float(
                working["immediate_risk"]
            ),
        )

        results.append(
            working.to_dict()
        )

    return pd.DataFrame(results)


def evaluate_online(
    df: pd.DataFrame,
) -> None:

    print(
        "\nSentinelTwin TRUE Online Adaptive Pipeline"
    )
    print("=" * 60)

    print(f"Sessions processed: {len(df):,}")

    print("\nGate decisions:")
    print(
        df["trust_decision"]
        .value_counts()
    )

    print("\nDecision composition:")

    composition = pd.crosstab(
        df["trust_decision"],
        df["is_attack"],
    )

    composition = composition.rename(
        columns={
            0: "normal",
            1: "attack",
        }
    )

    print(composition)

    # ==================================================
    # BASELINE CONTAMINATION
    # ==================================================

    learned = df[
        df["actually_learned"] == True
    ]
    released = df[
        df["released_from_quarantine"] == True
    ]

    print("\nQuarantine recovery:")

    print(
        f"Sessions released from quarantine: "
        f"{len(released)}"
    )

    print(
        f"Normal sessions released: "
        f"{(released['is_attack'] == 0).sum()}"
    )

    print(
        f"Attack sessions released: "
        f"{(released['is_attack'] == 1).sum()}"
    )

    attacks_learned = int(
        learned["is_attack"].sum()
    )

    contamination = (
        attacks_learned / len(learned)
        if len(learned)
        else 0
    )

    print("\nAdaptation safety:")

    print(
        f"Sessions learned: "
        f"{len(learned)}"
    )

    print(
        f"Attack sessions learned: "
        f"{attacks_learned}"
    )

    print(
        f"Baseline contamination: "
        f"{contamination * 100:.3f}%"
    )

    # ==================================================
    # DETECTION PERFORMANCE
    # ==================================================

    predicted_attack = (
        df["final_risk"] >= 45
    )

    actual_attack = (
        df["is_attack"] == 1
    )

    tp = int(
        (predicted_attack & actual_attack).sum()
    )

    fp = int(
        (predicted_attack & ~actual_attack).sum()
    )

    fn = int(
        (~predicted_attack & actual_attack).sum()
    )

    tn = int(
        (~predicted_attack & ~actual_attack).sum()
    )

    precision = (
        tp / (tp + fp)
        if tp + fp
        else 0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn
        else 0
    )

    f1 = (
        2 * precision * recall
        / (precision + recall)
        if precision + recall
        else 0
    )

    print("\nOnline Detection:")

    print(f"TP: {tp}")
    print(f"FP: {fp}")
    print(f"FN: {fn}")
    print(f"TN: {tn}")

    print(
        f"Precision: {precision:.3f}"
    )

    print(
        f"Recall:    {recall:.3f}"
    )

    print(
        f"F1:        {f1:.3f}"
    )

    # ==================================================
    # ATTACK-WISE RESULTS
    # ==================================================

    attacks = df[
        df["attack_type"] != "normal"
    ].copy()

    attacks["detected"] = (
        attacks["final_risk"] >= 45
    )

    attack_results = (
        attacks.groupby("attack_type")
        .agg(
            sessions=("session_id", "count"),
            detected=("detected", "sum"),
            avg_risk=("final_risk", "mean"),
        )
    )

    attack_results["recall"] = (
        attack_results["detected"]
        / attack_results["sessions"]
    )

    print("\nAttack-wise online detection:")

    print(
        attack_results.round(3)
    )


def save_results(
    df: pd.DataFrame,
) -> Path:

    root = Path(__file__).resolve().parents[1]

    path = (
        root
        / "data"
        / "processed"
        / "online_sessions.csv"
    )

    df.to_csv(
        path,
        index=False,
    )

    return path


if __name__ == "__main__":

    sessions = load_sessions()

    result = run_online_pipeline(
        sessions
    )

    evaluate_online(result)

    path = save_results(result)

    print(
        f"\nSaved to: {path}"
    )