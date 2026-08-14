from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def load_events() -> pd.DataFrame:
    project_root = Path(__file__).resolve().parents[1]
    path = project_root / "data" / "raw" / "security_events.csv"

    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df.sort_values("timestamp").reset_index(drop=True)


def build_sessions(events: pd.DataFrame) -> pd.DataFrame:
    """
    Convert event-level security logs into session-level behavioral records.

    IMPORTANT:
    attack_type and is_attack are retained only as ground truth for evaluation.
    They must never be used as detector input features.
    """

    events = events.copy()

    # Useful event-level fields before aggregation
    events["failed_login"] = (
        (events["command"] == "login")
        & (events["success"] == 0)
    ).astype(int)

    events["is_login"] = (
        events["command"] == "login"
    ).astype(int)

    events["is_download"] = (
        events["command"] == "download"
    ).astype(int)

    events["is_upload"] = (
        events["command"] == "upload"
    ).astype(int)

    # ---------------------------------------------------------
    # Aggregate behavioral information for each session
    # ---------------------------------------------------------

    sessions = (
        events.groupby("session_id")
        .agg(
            user_id=("user_id", "first"),
            role=("role", "first"),

            session_start=("timestamp", "min"),
            session_end=("timestamp", "max"),

            event_count=("event_id", "count"),

            login_attempts=("is_login", "sum"),
            failed_logins=("failed_login", "sum"),

            unique_ips=("ip_address", "nunique"),
            unique_locations=("location", "nunique"),
            unique_devices=("device_id", "nunique"),
            unique_resources=("resource", "nunique"),

            download_events=("is_download", "sum"),
            upload_events=("is_upload", "sum"),

            total_data_mb=("data_mb", "sum"),
            max_single_transfer_mb=("data_mb", "max"),

            privileged_actions=("privileged", "sum"),

            # Evaluation labels ONLY
            is_attack=("is_attack", "max"),
        )
        .reset_index()
    )

    # ---------------------------------------------------------
    # Session duration
    # ---------------------------------------------------------

    sessions["duration_minutes"] = (
        sessions["session_end"] - sessions["session_start"]
    ).dt.total_seconds() / 60

    # ---------------------------------------------------------
    # Time-based features
    # ---------------------------------------------------------

    sessions["start_hour"] = (
        sessions["session_start"].dt.hour
        + sessions["session_start"].dt.minute / 60
    )

    sessions["day_of_week"] = (
        sessions["session_start"].dt.dayofweek
    )

    sessions["is_weekend"] = (
        sessions["day_of_week"] >= 5
    ).astype(int)

    sessions["is_night"] = (
        (sessions["start_hour"] < 6)
        | (sessions["start_hour"] >= 22)
    ).astype(int)

    # ---------------------------------------------------------
    # Authentication features
    # ---------------------------------------------------------

    sessions["failed_login_rate"] = np.where(
        sessions["login_attempts"] > 0,
        sessions["failed_logins"]
        / sessions["login_attempts"],
        0.0,
    )

    # ---------------------------------------------------------
    # Data-transfer intensity
    # ---------------------------------------------------------

    sessions["data_per_event_mb"] = (
        sessions["total_data_mb"]
        / sessions["event_count"].clip(lower=1)
    )

    # ---------------------------------------------------------
    # Obtain session ground-truth attack type.
    #
    # A session could theoretically contain multiple labels.
    # We select the non-normal attack label if one exists.
    # ---------------------------------------------------------

    def get_attack_type(group: pd.DataFrame) -> str:
        attacks = group.loc[
            group["attack_type"] != "normal",
            "attack_type",
        ]

        if attacks.empty:
            return "normal"

        return attacks.mode().iloc[0]

    attack_labels = (
        events.groupby("session_id")
        .apply(
            get_attack_type,
            include_groups=False,
        )
        .rename("attack_type")
        .reset_index()
    )

    sessions = sessions.merge(
        attack_labels,
        on="session_id",
        how="left",
    )

    # Sort chronologically.
    # This becomes important when we construct behavioral histories.
    sessions = sessions.sort_values(
        "session_start"
    ).reset_index(drop=True)

    return sessions


def save_sessions(sessions: pd.DataFrame) -> Path:
    project_root = Path(__file__).resolve().parents[1]

    output_dir = project_root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / "sessions.csv"

    sessions.to_csv(path, index=False)

    return path


def print_summary(sessions: pd.DataFrame) -> None:
    print("\nSentinelTwin Session Dataset")
    print("=" * 45)

    print(f"Sessions: {len(sessions):,}")
    print(f"Users: {sessions['user_id'].nunique()}")

    print(
        f"Attack sessions: "
        f"{sessions['is_attack'].sum():,}"
    )

    print(
        f"Attack-session rate: "
        f"{sessions['is_attack'].mean() * 100:.2f}%"
    )

    print("\nAttack session distribution:")
    print(sessions["attack_type"].value_counts())

    print("\nSession feature summary:")

    columns = [
        "event_count",
        "duration_minutes",
        "failed_login_rate",
        "unique_locations",
        "unique_devices",
        "unique_resources",
        "total_data_mb",
        "privileged_actions",
    ]

    print(
        sessions[columns]
        .describe()
        .round(2)
    )


if __name__ == "__main__":
    events = load_events()

    sessions = build_sessions(events)

    path = save_sessions(sessions)

    print_summary(sessions)

    print(f"\nSaved to: {path}")