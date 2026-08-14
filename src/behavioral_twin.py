from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd


# Features that define a user's behavioral profile.
TWIN_FEATURES = [
    "start_hour",
    "duration_minutes",
    "event_count",
    "failed_login_rate",
    "unique_locations",
    "unique_devices",
    "unique_resources",
    "total_data_mb",
    "privileged_actions",
]


class BehavioralTwin:
    """
    Maintains a rolling behavioral profile for every entity.

    Important:
    A session is scored BEFORE it is allowed to update the user's
    behavioral history. This prevents future/current information
    from leaking into the baseline used to score that session.
    """

    def __init__(
        self,
        window_size: int = 30,
        min_personal_history: int = 5,
    ):
        self.window_size = window_size
        self.min_personal_history = min_personal_history

        # user_id -> rolling history
        self.user_history = defaultdict(
            lambda: deque(maxlen=self.window_size)
        )

        # role -> rolling cohort history
        # Used for cold-start users.
        self.role_history = defaultdict(
            lambda: deque(maxlen=500)
        )

    @staticmethod
    def _robust_stats(values: list[float]) -> tuple[float, float]:
        """
        Return median and robust scale using MAD.

        MAD is preferred over ordinary standard deviation because
        security data can contain extreme outliers.
        """

        arr = np.asarray(values, dtype=float)

        if len(arr) == 0:
            return 0.0, 1.0

        median = float(np.median(arr))

        mad = float(
            np.median(
                np.abs(arr - median)
            )
        )

        # Convert MAD to a standard-deviation-like scale.
        scale = 1.4826 * mad

        # Prevent division by zero for extremely stable features.
        if scale < 1e-6:
            scale = max(
                float(np.std(arr)),
                1.0,
            )

        return median, scale

    def _get_personal_stats(
        self,
        user_id: str,
        feature: str,
    ) -> tuple[float, float] | None:

        history = self.user_history[user_id]

        if len(history) < self.min_personal_history:
            return None

        values = [
            session[feature]
            for session in history
        ]

        return self._robust_stats(values)

    def _get_role_stats(
        self,
        role: str,
        feature: str,
    ) -> tuple[float, float] | None:

        history = self.role_history[role]

        if len(history) < self.min_personal_history:
            return None

        values = [
            session[feature]
            for session in history
        ]

        return self._robust_stats(values)

    def _calculate_deviation(
        self,
        value: float,
        median: float,
        scale: float,
    ) -> float:

        return abs(value - median) / max(scale, 1e-6)

    def score_session(
        self,
        session: pd.Series,
    ) -> dict:

        user_id = session["user_id"]
        role = session["role"]

        personal_history_size = len(
            self.user_history[user_id]
        )

        # -----------------------------------------------------
        # Cold-start weighting
        #
        # Little personal history:
        #     rely heavily on role peers.
        #
        # More history:
        #     gradually rely on personal behavior.
        # -----------------------------------------------------

        personal_weight = min(
            personal_history_size
            / max(self.min_personal_history * 3, 1),
            1.0,
        )

        deviations = {}

        for feature in TWIN_FEATURES:

            value = float(session[feature])

            personal_stats = self._get_personal_stats(
                user_id,
                feature,
            )

            role_stats = self._get_role_stats(
                role,
                feature,
            )

            # ---------------------------------------------
            # Personal deviation
            # ---------------------------------------------

            if personal_stats is not None:
                personal_median, personal_scale = (
                    personal_stats
                )

                personal_dev = self._calculate_deviation(
                    value,
                    personal_median,
                    personal_scale,
                )
            else:
                personal_dev = None

            # ---------------------------------------------
            # Cohort / role deviation
            # ---------------------------------------------

            if role_stats is not None:
                role_median, role_scale = role_stats

                role_dev = self._calculate_deviation(
                    value,
                    role_median,
                    role_scale,
                )
            else:
                role_dev = None

            # ---------------------------------------------
            # Blend personal and cohort behavior.
            # ---------------------------------------------

            if (
                personal_dev is not None
                and role_dev is not None
            ):
                deviation = (
                    personal_weight * personal_dev
                    + (1 - personal_weight) * role_dev
                )

                baseline_source = "hybrid"

            elif personal_dev is not None:
                deviation = personal_dev
                baseline_source = "personal"

            elif role_dev is not None:
                deviation = role_dev
                baseline_source = "cohort"

            else:
                # No meaningful history yet.
                deviation = 0.0
                baseline_source = "insufficient_history"

            deviations[
                f"{feature}_deviation"
            ] = round(float(deviation), 4)

        # -----------------------------------------------------
        # Aggregate behavioral deviation
        #
        # We cap individual deviations so one pathological
        # feature cannot completely dominate the score.
        # -----------------------------------------------------

        deviation_values = np.array(
            list(deviations.values()),
            dtype=float,
        )

        clipped = np.clip(
            deviation_values,
            0,
            10,
        )

        behavioral_deviation = float(
            np.mean(clipped)
        )

        deviations["behavioral_deviation"] = round(
            behavioral_deviation,
            4,
        )

        deviations["personal_history_size"] = (
            personal_history_size
        )

        deviations["personal_weight"] = round(
            personal_weight,
            4,
        )

        # Overall source is mainly for explanation/dashboard.
        if personal_history_size == 0:
            source = "cold_start"

        elif personal_weight < 1:
            source = "hybrid"

        else:
            source = "personal"

        deviations["baseline_source"] = source

        return deviations

    def update(
        self,
        session: pd.Series,
    ) -> None:
        """
        Add a session to behavioral history.

        TEMPORARY Phase-3 behavior:
        only ground-truth normal sessions update the twin.

        Later the Trust Gate will replace this and decide whether
        an observation is safe enough to learn from WITHOUT using
        ground-truth attack labels.
        """

        record = {
            feature: float(session[feature])
            for feature in TWIN_FEATURES
        }

        user_id = session["user_id"]
        role = session["role"]

        self.user_history[user_id].append(record)
        self.role_history[role].append(record)


def build_behavioral_features(
    sessions: pd.DataFrame,
) -> pd.DataFrame:

    sessions = sessions.copy()

    sessions["session_start"] = pd.to_datetime(
        sessions["session_start"]
    )

    sessions = sessions.sort_values(
        "session_start"
    ).reset_index(drop=True)

    twin = BehavioralTwin(
        window_size=30,
        min_personal_history=5,
    )

    behavioral_rows = []

    for _, session in sessions.iterrows():

        # Score FIRST.
        # Current session is not yet part of its own baseline.
        score = twin.score_session(session)

        behavioral_rows.append(score)

        # --------------------------------------------------
        # Phase 3 training/evaluation shortcut:
        #
        # Only known normal history updates the baseline.
        #
        # IMPORTANT:
        # This uses ground truth ONLY while developing the
        # baseline system.
        #
        # Our final online pipeline will replace this with
        # the Trust Gate.
        # --------------------------------------------------

        if int(session["is_attack"]) == 0:
            twin.update(session)

    behavioral_df = pd.DataFrame(
        behavioral_rows
    )

    result = pd.concat(
        [
            sessions.reset_index(drop=True),
            behavioral_df.reset_index(drop=True),
        ],
        axis=1,
    )

    return result


def load_sessions() -> pd.DataFrame:
    project_root = Path(__file__).resolve().parents[1]

    path = (
        project_root
        / "data"
        / "processed"
        / "sessions.csv"
    )

    df = pd.read_csv(path)

    df["session_start"] = pd.to_datetime(
        df["session_start"]
    )

    df["session_end"] = pd.to_datetime(
        df["session_end"]
    )

    return df


def save_behavioral_features(
    df: pd.DataFrame,
) -> Path:

    project_root = Path(__file__).resolve().parents[1]

    output_dir = (
        project_root
        / "data"
        / "processed"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        output_dir
        / "behavioral_sessions.csv"
    )

    df.to_csv(
        path,
        index=False,
    )

    return path


def print_summary(df: pd.DataFrame) -> None:

    print("\nSentinelTwin Behavioral Digital Twin")
    print("=" * 50)

    print(f"Sessions scored: {len(df):,}")

    print("\nBaseline source:")
    print(
        df["baseline_source"]
        .value_counts()
    )

    print("\nBehavioral deviation:")
    print(
        df.groupby("is_attack")[
            "behavioral_deviation"
        ]
        .describe()
        .round(3)
    )

    print("\nAverage deviations: Normal vs Attack")

    deviation_columns = [
        f"{feature}_deviation"
        for feature in TWIN_FEATURES
    ]

    comparison = (
        df.groupby("is_attack")[
            deviation_columns
        ]
        .mean()
        .T
    )

    comparison.columns = [
        "normal",
        "attack",
    ]

    comparison["attack_vs_normal"] = (
        comparison["attack"]
        / comparison["normal"].replace(0, np.nan)
    )

    print(
        comparison
        .round(2)
        .sort_values(
            "attack_vs_normal",
            ascending=False,
        )
    )


if __name__ == "__main__":

    sessions = load_sessions()

    behavioral = build_behavioral_features(
        sessions
    )

    path = save_behavioral_features(
        behavioral
    )

    print_summary(behavioral)

    print(f"\nSaved to: {path}")
    