from __future__ import annotations

from pathlib import Path

import pandas as pd


DEVIATION_FEATURES = {
    "failed_login_rate_deviation": "Failed-login behaviour",
    "unique_locations_deviation": "Location usage",
    "unique_devices_deviation": "Device usage",
    "unique_resources_deviation": "Resource access",
    "total_data_mb_deviation": "Data transfer",
    "start_hour_deviation": "Login time",
    "event_count_deviation": "Session activity",
    "duration_minutes_deviation": "Session duration",
    "privileged_actions_deviation": "Privileged activity",
}


class AlertExplainer:
    """
    Converts SentinelTwin's numerical risk and behavioral
    deviation signals into analyst-readable explanations.

    Explanations are derived from model inputs and behavioral
    baselines rather than from ground-truth attack labels.
    """

    def _deviation_reasons(
        self,
        session: pd.Series,
        max_reasons: int = 4,
    ) -> list[str]:

        deviations = []

        for column, label in DEVIATION_FEATURES.items():

            if column not in session.index:
                continue

            value = session[column]

            if pd.isna(value):
                continue

            deviations.append(
                (
                    float(value),
                    label,
                )
            )

        deviations.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        reasons = []

        for value, label in deviations[:max_reasons]:

            if value < 1.0:
                continue

            if value >= 3.0:
                strength = "strongly"
            elif value >= 2.0:
                strength = "significantly"
            else:
                strength = "moderately"

            reasons.append(
                f"{label} {strength} deviates "
                f"from the user's behavioral baseline "
                f"(deviation score {value:.2f})."
            )

        return reasons

    def _temporal_reason(
        self,
        session: pd.Series,
    ) -> str | None:

        if (
            "multi_horizon_risk"
            not in session.index
        ):
            return None

        multi = float(
            session["multi_horizon_risk"]
        )

        immediate = float(
            session.get(
                "immediate_risk",
                0,
            )
        )

        persistence = float(
            session.get(
                "persistence_risk",
                0,
            )
        )

        if persistence >= 60:
            return (
                "Abnormal behaviour persists across "
                "multiple recent sessions, indicating "
                "a sustained behavioral shift."
            )

        if (
            multi >= 50
            and immediate < 60
        ):
            return (
                "Risk becomes more significant when "
                "behaviour is evaluated across multiple "
                "time horizons rather than as an "
                "isolated session."
            )

        return None

    def _context_reason(
        self,
        session: pd.Series,
    ) -> str | None:

        context = float(
            session.get(
                "context_risk",
                0,
            )
        )

        immediate = float(
            session.get(
                "immediate_risk",
                0,
            )
        )

        if (
            context >= 70
            and context > immediate
        ):
            return (
                "Contextual indicators increase the "
                "severity beyond what the session's "
                "raw behavioral anomaly alone suggests."
            )

        return None

    def explain(
        self,
        session: pd.Series,
    ) -> dict:

        reasons = self._deviation_reasons(
            session
        )

        temporal = self._temporal_reason(
            session
        )

        context = self._context_reason(
            session
        )

        if temporal:
            reasons.append(temporal)

        if context:
            reasons.append(context)

        if not reasons:
            reasons.append(
                "The combined behavioral, contextual, "
                "and temporal risk exceeded the alert "
                "threshold."
            )

        return {
            "severity": session.get(
                "severity",
                "UNKNOWN",
            ),
            "final_risk": float(
                session.get(
                    "final_risk",
                    0,
                )
            ),
            "predicted_attack_type": (
                session.get(
                    "predicted_attack_type",
                    "unknown",
                )
            ),
            "classification_confidence": float(
                session.get(
                    "classification_confidence",
                    0,
                )
            ),
            "reasons": reasons,
        }


def main():

    root = Path(__file__).resolve().parents[1]

    path = (
        root
        / "data"
        / "processed"
        / "classified_sessions.csv"
    )

    sessions = pd.read_csv(path)

    alerts = sessions[
        sessions["final_risk"] >= 45
    ].copy()

    alerts = alerts.sort_values(
        "final_risk",
        ascending=False,
    )

    explainer = AlertExplainer()

    print("\nSentinelTwin Explainability Engine")
    print("=" * 60)

    print(
        f"Alerts available: {len(alerts):,}"
    )

    print("\nTop 5 Alert Explanations")
    print("=" * 60)

    for _, session in alerts.head(5).iterrows():

        explanation = explainer.explain(
            session
        )

        print(
            f"\nUser: {session['user_id']}"
        )

        print(
            f"Risk: "
            f"{explanation['final_risk']:.1f}"
        )

        print(
            f"Severity: "
            f"{explanation['severity']}"
        )

        print(
            "Predicted attack: "
            f"{explanation['predicted_attack_type']}"
        )

        print(
            "Classifier confidence: "
            f"{explanation['classification_confidence']:.1%}"
        )

        print("Why this alert:")

        for reason in explanation["reasons"]:
            print(f"  - {reason}")

        print("-" * 60)


if __name__ == "__main__":
    main()