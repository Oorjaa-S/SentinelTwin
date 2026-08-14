from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

RISK_THRESHOLD = 45.0


class SentinelTwinInference:
    """
    Loads the frozen attack classifier and provides
    attack classification for SentinelTwin alerts.

    The classifier is only used after the risk engine
    determines that a session is suspicious.
    """

    def __init__(
        self,
        model_path: Path | None = None,
    ):
        root = Path(__file__).resolve().parents[1]

        if model_path is None:
            model_path = root / "models" / "attack_classifier.joblib"

        payload = joblib.load(model_path)

        self.model = payload["model"]
        self.features = payload["features"]
        self.config = payload["config"]

    def classify_session(
        self,
        session: pd.Series,
    ) -> dict:
        """
        Classify one suspicious session.

        Returns predicted attack type and classifier
        confidence.
        """

        X = pd.DataFrame([{feature: session[feature] for feature in self.features}])

        predicted_type = self.model.predict(X)[0]

        probabilities = self.model.predict_proba(X)[0]

        confidence = float(probabilities.max())

        return {
            "predicted_attack_type": predicted_type,
            "classification_confidence": confidence,
        }

    def classify_alerts(
        self,
        sessions: pd.DataFrame,
        risk_column: str = "final_risk",
        threshold: float = RISK_THRESHOLD,
    ) -> pd.DataFrame:
        """
        Run attack classification only on sessions that
        SentinelTwin has already flagged as suspicious.
        """

        result = sessions.copy()

        result["predicted_attack_type"] = "normal"
        result["classification_confidence"] = 0.0

        suspicious_mask = result[risk_column] >= threshold

        suspicious = result.loc[
            suspicious_mask,
            self.features,
        ]

        if suspicious.empty:
            return result

        predictions = self.model.predict(suspicious)

        probabilities = self.model.predict_proba(suspicious)

        confidence = probabilities.max(axis=1)

        result.loc[
            suspicious_mask,
            "predicted_attack_type",
        ] = predictions

        result.loc[
            suspicious_mask,
            "classification_confidence",
        ] = confidence

        return result


def main():
    root = Path(__file__).resolve().parents[1]

    input_path = root / "data" / "processed" / "context_sessions.csv"

    sessions = pd.read_csv(input_path)

    engine = SentinelTwinInference()

    results = engine.classify_alerts(
        sessions,
        risk_column="final_risk",
        threshold=RISK_THRESHOLD,
    )

    flagged = results["final_risk"] >= RISK_THRESHOLD

    print("\nSentinelTwin Integrated Inference")
    print("=" * 55)

    print(f"Sessions processed: {len(results):,}")

    print(f"Sessions flagged: {flagged.sum():,}")

    print("\nPredicted alert types:")

    print(
        results.loc[
            flagged,
            "predicted_attack_type",
        ].value_counts()
    )

    if "attack_type" in results.columns:
        flagged_results = results.loc[flagged]

        correct = (
            flagged_results["predicted_attack_type"] == flagged_results["attack_type"]
        )

        print(
            "\nClassification accuracy "
            "among flagged sessions: "
            f"{correct.mean():.3f}"
        )

    output_path = root / "data" / "processed" / "classified_sessions.csv"

    results.to_csv(
        output_path,
        index=False,
    )

    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
