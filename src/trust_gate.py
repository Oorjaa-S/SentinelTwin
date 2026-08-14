from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd


class TrustGate:
    """
    Determines whether an observed session is safe enough
    for the Behavioral Twin to learn from.

    IMPORTANT:
    Decisions are based only on observable risk signals.
    Ground-truth attack labels are NEVER used by the gate.
    """

    def __init__(
        self,
        trusted_threshold: float = 25.0,
        suspicious_threshold: float = 45.0,
        mature_history: int = 15,
    ):
        self.trusted_threshold = trusted_threshold
        self.suspicious_threshold = suspicious_threshold
        self.mature_history = mature_history

    def evaluate(
        self,
        row: pd.Series,
    ) -> dict:

        final_risk = float(
            row["final_risk"]
        )

        history_size = int(
            row["personal_history_size"]
        )

        # ---------------------------------------------
        # Baseline confidence
        # ---------------------------------------------

        baseline_confidence = min(
            history_size / self.mature_history,
            1.0,
        )

        # ---------------------------------------------
        # Evidence disagreement
        #
        # A session is less trustworthy when the
        # different engines strongly disagree.
        # ---------------------------------------------

        evidence = np.array(
            [
                float(row["immediate_risk"]),
                float(row["context_risk"]),
                float(row["multi_horizon_risk"]),
            ]
        )

        disagreement = float(
            np.std(evidence)
        )

        # ---------------------------------------------
        # Gate decision
        # ---------------------------------------------

        if final_risk >= self.suspicious_threshold:

            decision = "REJECT"
            learn = False

        elif final_risk >= self.trusted_threshold:

            decision = "QUARANTINE"
            learn = False

        else:

            # Even low-risk sessions from a very immature
            # profile are learned cautiously.
            if (
                baseline_confidence < 0.20
                and disagreement > 15
            ):
                decision = "QUARANTINE"
                learn = False

            else:
                decision = "TRUST"
                learn = True

        return {
            "trust_decision": decision,
            "learn_allowed": learn,
            "baseline_confidence": round(
                baseline_confidence,
                3,
            ),
            "evidence_disagreement": round(
                disagreement,
                2,
            ),
        }

class QuarantineManager:
    """
    Holds uncertain observations temporarily.

    Repeated, consistent, non-critical behavior may later be
    considered legitimate behavioral drift and released for
    learning.

    This allows the Digital Twin to adapt without immediately
    trusting every unusual observation.
    """

    def __init__(
        self,
        required_consistency: int = 3,
        max_history: int = 5,
    ):
        self.required_consistency = required_consistency

        self.quarantine = defaultdict(
            lambda: deque(maxlen=max_history)
        )

    @staticmethod
    def _is_security_critical(
        row: pd.Series,
    ) -> bool:
        """
        Behaviors with strong direct security indicators should
        never be auto-released simply because they repeat.
        """

        critical_signals = [
            float(row.get("authentication_abuse", 0)),
            float(row.get("geographic_risk", 0)),
            float(row.get("device_risk", 0)),
            float(row.get("privilege_risk", 0)),
        ]

        return max(critical_signals) >= 70

    @staticmethod
    def _behavior_vector(
        row: pd.Series,
    ) -> np.ndarray:

        return np.array(
            [
                float(row["start_hour"]),
                float(row["duration_minutes"]) / 60,
                float(row["event_count"]) / 10,
                float(row["unique_resources"]),
                float(row["total_data_mb"]) / 25,
            ],
            dtype=float,
        )

    def evaluate(
        self,
        row: pd.Series,
    ) -> dict:

        user_id = row["user_id"]

        if self._is_security_critical(row):
            return {
                "quarantine_status": "HELD_CRITICAL",
                "release_for_learning": False,
                "consistency_count": 0,
            }

        current = self._behavior_vector(row)

        history = list(
            self.quarantine[user_id]
        )

        similar = 0

        for previous in history:

            distance = np.linalg.norm(
                current - previous
            )

            if distance <= 2.5:
                similar += 1

        consistency_count = similar + 1

        self.quarantine[user_id].append(
            current
        )

        if (
            consistency_count
            >= self.required_consistency
        ):
            return {
                "quarantine_status": "RELEASED",
                "release_for_learning": True,
                "consistency_count": consistency_count,
            }

        return {
            "quarantine_status": "OBSERVING",
            "release_for_learning": False,
            "consistency_count": consistency_count,
        }

def load_data():

    root = Path(__file__).resolve().parents[1]

    path = (
        root
        / "data"
        / "processed"
        / "context_sessions.csv"
    )

    return pd.read_csv(path)


def apply_trust_gate(
    df: pd.DataFrame,
) -> pd.DataFrame:

    gate = TrustGate()

    decisions = []

    for _, row in df.iterrows():
        decisions.append(
            gate.evaluate(row)
        )

    decision_df = pd.DataFrame(
        decisions
    )

    return pd.concat(
        [
            df.reset_index(drop=True),
            decision_df,
        ],
        axis=1,
    )


def evaluate_gate(
    df: pd.DataFrame,
):

    print(
        "\nSentinelTwin Trust-Gated Adaptation"
    )
    print("=" * 55)

    print("\nGate decisions:")

    print(
        df["trust_decision"]
        .value_counts()
    )

    print(
        "\nDecision composition:"
    )

    composition = pd.crosstab(
        df["trust_decision"],
        df["is_attack"],
    )

    composition.columns = [
        "normal",
        "attack",
    ]

    print(composition)

    # ---------------------------------------------
    # How safe is adaptation?
    # ---------------------------------------------

    learned = df[
        df["learn_allowed"] == True
    ]

    malicious_learned = int(
        learned["is_attack"].sum()
    )

    total_learned = len(learned)

    contamination_rate = (
        malicious_learned / total_learned
        if total_learned
        else 0
    )

    print("\nAdaptation safety:")

    print(
        f"Sessions allowed to update twin: "
        f"{total_learned}"
    )

    print(
        f"Attack sessions accidentally learned: "
        f"{malicious_learned}"
    )

    print(
        f"Baseline contamination rate: "
        f"{contamination_rate * 100:.3f}%"
    )

    # ---------------------------------------------
    # What happened to legitimate anomalies?
    # ---------------------------------------------

    normal = df[
        df["is_attack"] == 0
    ]

    normal_trusted = (
        normal["trust_decision"]
        == "TRUST"
    ).sum()

    normal_quarantined = (
        normal["trust_decision"]
        == "QUARANTINE"
    ).sum()

    normal_rejected = (
        normal["trust_decision"]
        == "REJECT"
    ).sum()

    print("\nNormal-session handling:")

    print(
        f"Trusted:     {normal_trusted}"
    )

    print(
        f"Quarantined: {normal_quarantined}"
    )

    print(
        f"Rejected:    {normal_rejected}"
    )

    # ---------------------------------------------
    # Attack handling
    # ---------------------------------------------

    attacks = df[
        df["is_attack"] == 1
    ]

    print("\nAttack gate decisions:")

    attack_table = pd.crosstab(
        attacks["attack_type"],
        attacks["trust_decision"],
    )

    print(attack_table)


def save_results(
    df: pd.DataFrame,
):

    root = Path(__file__).resolve().parents[1]

    path = (
        root
        / "data"
        / "processed"
        / "trusted_sessions.csv"
    )

    df.to_csv(
        path,
        index=False,
    )

    return path


if __name__ == "__main__":

    df = load_data()

    result = apply_trust_gate(df)

    evaluate_gate(result)

    path = save_results(result)

    print(
        f"\nSaved to: {path}"
    )