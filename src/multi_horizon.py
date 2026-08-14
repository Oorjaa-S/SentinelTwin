from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd


class MultiHorizonRisk:
    """
    Tracks behavioral risk across multiple time horizons.

    Immediate:
        Current-session behavioral deviation.

    Short-term:
        Recent 3 sessions.

    Medium-term:
        Recent 7 sessions.

    Long-term:
        Recent 15 sessions.

    This allows gradual attacks to accumulate risk even when
    individual sessions are not extreme anomalies.
    """

    def __init__(self):
        self.history = defaultdict(
            lambda: deque(maxlen=15)
        )

    @staticmethod
    def deviation_to_risk(deviation: float) -> float:
        """
        Convert unbounded behavioral deviation into a 0-100 score.

        Smooth exponential transformation prevents extreme
        deviations from producing arbitrarily large values.
        """

        risk = 100 * (
            1 - np.exp(-max(deviation, 0) / 2.0)
        )

        return float(np.clip(risk, 0, 100))

    @staticmethod
    def weighted_recent_average(
        values: list[float],
    ) -> float:

        if not values:
            return 0.0

        # More recent observations matter more.
        weights = np.arange(
            1,
            len(values) + 1,
            dtype=float,
        )

        return float(
            np.average(values, weights=weights)
        )

    def score(
        self,
        user_id: str,
        current_deviation: float,
    ) -> dict:

        previous = list(
            self.history[user_id]
        )

        current_risk = self.deviation_to_risk(
            current_deviation
        )

        # Include current observation when assessing trajectory.
        trajectory = previous + [current_risk]

        short_values = trajectory[-3:]
        medium_values = trajectory[-7:]
        long_values = trajectory[-15:]

        short_risk = self.weighted_recent_average(
            short_values
        )

        medium_risk = self.weighted_recent_average(
            medium_values
        )

        long_risk = self.weighted_recent_average(
            long_values
        )

        # --------------------------------------------------
        # Persistent deviation
        #
        # Count how many recent sessions have meaningful risk.
        # A gradual attacker may never produce a single massive
        # anomaly, but repeated moderate anomalies matter.
        # --------------------------------------------------

        recent_7 = trajectory[-7:]

        persistent_count = sum(
            risk >= 35
            for risk in recent_7
        )

        persistence_risk = min(
            persistent_count / 5,
            1.0,
        ) * 100

        # --------------------------------------------------
        # Trend
        #
        # Positive slope means behavioral risk is increasing.
        # --------------------------------------------------

        if len(recent_7) >= 3:
            x = np.arange(len(recent_7))

            slope = np.polyfit(
                x,
                recent_7,
                1,
            )[0]

            trend_risk = float(
                np.clip(
                    max(slope, 0) * 10,
                    0,
                    100,
                )
            )

        else:
            trend_risk = 0.0

        # --------------------------------------------------
        # Multi-horizon score
        #
        # Current behavior still matters most, but historical
        # persistence can significantly raise the final score.
        # --------------------------------------------------

        multi_horizon_risk = (
            0.40 * current_risk
            + 0.20 * short_risk
            + 0.15 * medium_risk
            + 0.10 * long_risk
            + 0.10 * persistence_risk
            + 0.05 * trend_risk
        )

        multi_horizon_risk = float(
            np.clip(
                multi_horizon_risk,
                0,
                100,
            )
        )

        return {
            "immediate_risk": round(
                current_risk,
                2,
            ),
            "short_term_risk": round(
                short_risk,
                2,
            ),
            "medium_term_risk": round(
                medium_risk,
                2,
            ),
            "long_term_risk": round(
                long_risk,
                2,
            ),
            "persistence_risk": round(
                persistence_risk,
                2,
            ),
            "trend_risk": round(
                trend_risk,
                2,
            ),
            "multi_horizon_risk": round(
                multi_horizon_risk,
                2,
            ),
        }

    def update(
        self,
        user_id: str,
        immediate_risk: float,
    ):
        self.history[user_id].append(
            float(immediate_risk)
        )


def apply_multi_horizon(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    df["session_start"] = pd.to_datetime(
        df["session_start"]
    )

    df = df.sort_values(
        "session_start"
    ).reset_index(drop=True)

    engine = MultiHorizonRisk()

    rows = []

    for _, session in df.iterrows():

        scores = engine.score(
            user_id=session["user_id"],
            current_deviation=float(
                session["behavioral_deviation"]
            ),
        )

        rows.append(scores)

        # Historical risk engine observes all sessions.
        # This does NOT update the Behavioral Twin baseline.
        engine.update(
            user_id=session["user_id"],
            immediate_risk=scores[
                "immediate_risk"
            ],
        )

    risk_df = pd.DataFrame(rows)

    result = pd.concat(
        [
            df.reset_index(drop=True),
            risk_df.reset_index(drop=True),
        ],
        axis=1,
    )

    return result


def load_behavioral_sessions():
    root = Path(__file__).resolve().parents[1]

    path = (
        root
        / "data"
        / "processed"
        / "behavioral_sessions.csv"
    )

    return pd.read_csv(
        path,
        parse_dates=["session_start", "session_end"],
    )


def save_results(df):
    root = Path(__file__).resolve().parents[1]

    path = (
        root
        / "data"
        / "processed"
        / "risk_sessions.csv"
    )

    df.to_csv(path, index=False)

    return path


def print_summary(df):

    print("\nSentinelTwin Multi-Horizon Risk Engine")
    print("=" * 50)

    comparison = (
        df.groupby("is_attack")[
            [
                "immediate_risk",
                "short_term_risk",
                "medium_term_risk",
                "long_term_risk",
                "multi_horizon_risk",
            ]
        ]
        .mean()
        .round(2)
    )

    print("\nNormal vs Attack:")
    print(comparison)

    print("\nRisk by attack type:")

    attack_comparison = (
        df.groupby("attack_type")[
            [
                "immediate_risk",
                "multi_horizon_risk",
                "persistence_risk",
                "trend_risk",
            ]
        ]
        .mean()
        .round(2)
        .sort_values(
            "multi_horizon_risk",
            ascending=False,
        )
    )

    print(attack_comparison)


if __name__ == "__main__":

    df = load_behavioral_sessions()

    result = apply_multi_horizon(df)

    path = save_results(result)

    print_summary(result)

    print(f"\nSaved to: {path}")