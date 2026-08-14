from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def load_data() -> pd.DataFrame:
    root = Path(__file__).resolve().parents[1]

    path = (
        root
        / "data"
        / "processed"
        / "risk_sessions.csv"
    )

    return pd.read_csv(
        path,
        parse_dates=["session_start", "session_end"],
    )


def calculate_context_signals(
    row: pd.Series,
) -> dict:

    signals = {}

    # -------------------------------------------------------
    # 1. Authentication abuse
    # -------------------------------------------------------

    failed_rate = float(
        row["failed_login_rate"]
    )

    login_attempts = float(
        row["login_attempts"]
    )

    auth_abuse = min(
        100,
        failed_rate * 70
        + max(login_attempts - 3, 0) * 4,
    )

    signals["authentication_abuse"] = auth_abuse

    # -------------------------------------------------------
    # 2. Geographic inconsistency
    #
    # Multiple locations within one session are highly
    # suspicious and useful for impossible-travel detection.
    # -------------------------------------------------------

    locations = int(
        row["unique_locations"]
    )

    if locations <= 1:
        geographic_risk = 0

    elif locations == 2:
        geographic_risk = 80

    else:
        geographic_risk = 100

    signals["geographic_risk"] = geographic_risk

    # -------------------------------------------------------
    # 3. Device inconsistency
    # -------------------------------------------------------

    devices = int(
        row["unique_devices"]
    )

    if devices <= 1:
        device_risk = 0

    elif devices == 2:
        device_risk = 70

    else:
        device_risk = 100

    signals["device_risk"] = device_risk

    # -------------------------------------------------------
    # 4. Resource spread
    # -------------------------------------------------------

    resource_count = int(
        row["unique_resources"]
    )

    resource_dev = float(
        row["unique_resources_deviation"]
    )

    resource_risk = min(
        100,
        resource_dev * 15
        + max(resource_count - 4, 0) * 10,
    )

    signals["resource_spread_risk"] = resource_risk

    # -------------------------------------------------------
    # 5. Privilege escalation/context
    # -------------------------------------------------------

    privileged = int(
        row["privileged_actions"]
    )

    role = str(row["role"])

    if privileged == 0:
        privilege_risk = 0

    elif role != "admin":
        privilege_risk = min(
            100,
            65 + privileged * 10,
        )

    else:
        # Privileged operations are expected for admins,
        # although an unusually large number still matters.
        privilege_risk = min(
            60,
            privileged * 8,
        )

    signals["privilege_risk"] = privilege_risk

    # -------------------------------------------------------
    # 6. Data movement
    # -------------------------------------------------------

    data_dev = float(
        row["total_data_mb_deviation"]
    )

    data_risk = min(
        100,
        data_dev * 12,
    )

    signals["data_movement_risk"] = data_risk

    # -------------------------------------------------------
    # 7. Temporal anomaly
    # -------------------------------------------------------

    time_dev = float(
        row["start_hour_deviation"]
    )

    night = int(
        row["is_night"]
    )

    temporal_risk = min(
        100,
        time_dev * 10 + night * 20,
    )

    signals["temporal_risk"] = temporal_risk

    # -------------------------------------------------------
    # Context score
    #
    # We intentionally use the strongest few signals rather
    # than averaging everything. An impossible-travel attack
    # should not become "less suspicious" simply because it
    # did not transfer much data.
    # -------------------------------------------------------

    values = sorted(
        signals.values(),
        reverse=True,
    )

    strongest = values[0]
    second = values[1]
    third = values[2]

    context_risk = (
        0.55 * strongest
        + 0.30 * second
        + 0.15 * third
    )

    signals["context_risk"] = round(
        float(np.clip(context_risk, 0, 100)),
        2,
    )

    return {
        key: round(float(value), 2)
        for key, value in signals.items()
    }


def apply_context_engine(
    df: pd.DataFrame,
) -> pd.DataFrame:

    context_rows = []

    for _, row in df.iterrows():
        context_rows.append(
            calculate_context_signals(row)
        )

    context_df = pd.DataFrame(
        context_rows
    )

    return pd.concat(
        [
            df.reset_index(drop=True),
            context_df.reset_index(drop=True),
        ],
        axis=1,
    )


def calculate_final_risk(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    # -------------------------------------------------------
    # Risk fusion
    #
    # Behavioral Twin:
    #     Is this abnormal for this person?
    #
    # Context:
    #     Is the behavior intrinsically security-sensitive?
    #
    # Multi-horizon:
    #     Has suspicious behavior persisted over time?
    # -------------------------------------------------------

    df["final_risk"] = (
        0.35 * df["immediate_risk"]
        + 0.35 * df["context_risk"]
        + 0.30 * df["multi_horizon_risk"]
    ).clip(0, 100)

    df["final_risk"] = (
        df["final_risk"]
        .round(2)
    )

    # -------------------------------------------------------
    # Severity
    # -------------------------------------------------------

    df["severity"] = pd.cut(
        df["final_risk"],
        bins=[
            -np.inf,
            25,
            45,
            65,
            80,
            np.inf,
        ],
        labels=[
            "LOW",
            "GUARDED",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        ],
    )

    return df


def save_results(
    df: pd.DataFrame,
) -> Path:

    root = Path(__file__).resolve().parents[1]

    path = (
        root
        / "data"
        / "processed"
        / "context_sessions.csv"
    )

    df.to_csv(
        path,
        index=False,
    )

    return path


def print_summary(
    df: pd.DataFrame,
) -> None:

    print("\nSentinelTwin Context & Risk Engine")
    print("=" * 55)

    print("\nRisk: Normal vs Attack")

    print(
        df.groupby("is_attack")[
            [
                "immediate_risk",
                "context_risk",
                "multi_horizon_risk",
                "final_risk",
            ]
        ]
        .mean()
        .round(2)
    )

    print("\nFinal risk by attack type:")

    comparison = (
        df.groupby("attack_type")[
            [
                "immediate_risk",
                "context_risk",
                "multi_horizon_risk",
                "final_risk",
            ]
        ]
        .mean()
        .round(2)
        .sort_values(
            "final_risk",
            ascending=False,
        )
    )

    print(comparison)

    print("\nSeverity distribution:")

    print(
        df["severity"]
        .value_counts()
        .sort_index()
    )


if __name__ == "__main__":

    df = load_data()

    df = apply_context_engine(df)

    df = calculate_final_risk(df)

    path = save_results(df)

    print_summary(df)

    print(f"\nSaved to: {path}")