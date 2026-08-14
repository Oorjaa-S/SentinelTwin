from __future__ import annotations

from pathlib import Path

import pandas as pd


TRAIN_RATIO = 0.70
VAL_RATIO = 0.10


def load_sessions() -> pd.DataFrame:
    """
    Load session-level data and guarantee chronological order.
    """

    root = Path(__file__).resolve().parents[1]

    path = (
        root
        / "data"
        / "processed"
        / "sessions.csv"
    )

    df = pd.read_csv(
        path,
        parse_dates=[
            "session_start",
            "session_end",
        ],
    )

    return (
        df.sort_values("session_start")
        .reset_index(drop=True)
    )


def temporal_split(
    df: pd.DataFrame,
):
    """
    Chronological 70/10/20 split based on elapsed time.

    First 70% of timeline -> training
    Next 10%              -> validation
    Final 20%             -> testing

    No random shuffling.
    """

    start = df["session_start"].min()
    end = df["session_start"].max()

    total_duration = end - start

    train_cutoff = (
        start
        + total_duration * 0.70
    )

    val_cutoff = (
        start
        + total_duration * 0.80
    )

    train = df[
        df["session_start"] < train_cutoff
    ].copy()

    val = df[
        (
            df["session_start"]
            >= train_cutoff
        )
        &
        (
            df["session_start"]
            < val_cutoff
        )
    ].copy()

    test = df[
        df["session_start"] >= val_cutoff
    ].copy()

    return (
        train.reset_index(drop=True),
        val.reset_index(drop=True),
        test.reset_index(drop=True),
    )


def print_split_summary(
    name: str,
    df: pd.DataFrame,
):
    print(f"\n{name}")
    print("-" * 55)

    print(
        f"Sessions: {len(df):,}"
    )

    print(
        f"Date range: "
        f"{df['session_start'].min()} "
        f"-> "
        f"{df['session_start'].max()}"
    )

    attacks = int(
        df["is_attack"].sum()
    )

    print(
        f"Normal sessions: "
        f"{len(df) - attacks:,}"
    )

    print(
        f"Attack sessions: "
        f"{attacks:,}"
    )

    print(
        f"Attack rate: "
        f"{df['is_attack'].mean() * 100:.2f}%"
    )

    print("\nAttack distribution:")

    attack_distribution = (
        df.loc[
            df["attack_type"] != "normal",
            "attack_type",
        ]
        .value_counts()
    )

    if len(attack_distribution) == 0:
        print("No attacks")
    else:
        print(attack_distribution)


def save_splits(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
):
    root = Path(__file__).resolve().parents[1]

    output_dir = (
        root
        / "data"
        / "splits"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    train.to_csv(
        output_dir / "train.csv",
        index=False,
    )

    val.to_csv(
        output_dir / "validation.csv",
        index=False,
    )

    test.to_csv(
        output_dir / "test.csv",
        index=False,
    )

    return output_dir


def main():

    df = load_sessions()

    train, val, test = temporal_split(df)

    print(
        "\nSentinelTwin Temporal Dataset Split"
    )
    print("=" * 55)

    print(
        "\nSplit strategy: "
        "70% Train / 10% Validation / 20% Test"
    )

    print(
        "Ordering: chronological "
        "(NO random shuffling)"
    )

    print_split_summary(
        "TRAIN",
        train,
    )

    print_split_summary(
        "VALIDATION",
        val,
    )

    print_split_summary(
        "TEST",
        test,
    )

    output_dir = save_splits(
        train,
        val,
        test,
    )

    print(
        f"\nSplits saved to: "
        f"{output_dir}"
    )


if __name__ == "__main__":
    main()