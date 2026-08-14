from __future__ import annotations

import subprocess
import sys
import time


PIPELINE_STAGES = [
    ("Generate synthetic security events", "src.generator"),
    ("Build behavioral sessions", "src.sessions"),
    ("Create temporal train/validation/test split", "src.temporal_split"),
    ("Train and validate attack classifier", "src.attack_classifier"),
    ("Build behavioral digital twins", "src.behavioral_twin"),
    ("Calculate multi-horizon risk", "src.multi_horizon"),
    ("Apply contextual risk scoring", "src.context_engine"),
    ("Run integrated inference", "src.inference"),
    ("Apply trust-gated adaptation", "src.trust_gate"),
    ("Run online adaptive simulation", "src.online_pipeline"),
    ("Evaluate held-out system performance", "src.system_evaluation"),
    ("Generate alert explanations", "src.explainability"),
]


def run_stage(
    stage_number: int,
    total_stages: int,
    description: str,
    module: str,
) -> float:
    """
    Execute one SentinelTwin pipeline stage.

    Returns the execution time in seconds.
    Raises an error immediately if the stage fails.
    """

    print("\n" + "=" * 72)
    print(
        f"[{stage_number}/{total_stages}] "
        f"{description}"
    )
    print(f"Module: python -m {module}")
    print("=" * 72)

    start = time.perf_counter()

    result = subprocess.run(
        [sys.executable, "-m", module],
        check=False,
    )

    elapsed = time.perf_counter() - start

    if result.returncode != 0:
        raise RuntimeError(
            f"Pipeline failed during '{description}' "
            f"({module})."
        )

    print(
        f"\n✓ Stage completed in {elapsed:.2f}s"
    )

    return elapsed


def run_pipeline() -> None:
    """
    Run the complete SentinelTwin workflow from raw
    synthetic events through final evaluation and
    explainability.
    """

    print("\n")
    print("=" * 72)
    print("SentinelTwin End-to-End Security Pipeline")
    print("=" * 72)
    print(
        "Adaptive Behavioral Digital Twin "
        "for Security Risk Intelligence"
    )

    pipeline_start = time.perf_counter()

    stage_times = []

    total_stages = len(PIPELINE_STAGES)

    for index, (description, module) in enumerate(
        PIPELINE_STAGES,
        start=1,
    ):
        elapsed = run_stage(
            index,
            total_stages,
            description,
            module,
        )

        stage_times.append(
            (description, elapsed)
        )

    total_elapsed = (
        time.perf_counter() - pipeline_start
    )

    print("\n" + "=" * 72)
    print("SentinelTwin Pipeline Complete")
    print("=" * 72)

    print("\nStage execution times:")

    for description, elapsed in stage_times:
        print(
            f"{description:<48} "
            f"{elapsed:>7.2f}s"
        )

    print("-" * 72)
    print(
        f"{'Total execution time':<48} "
        f"{total_elapsed:>7.2f}s"
    )

    print("\nGenerated system components:")
    print("  ✓ Synthetic security event dataset")
    print("  ✓ Session-level behavioral features")
    print("  ✓ Chronological train/validation/test splits")
    print("  ✓ Frozen attack classification model")
    print("  ✓ Entity behavioral digital twins")
    print("  ✓ Multi-horizon behavioral risk")
    print("  ✓ Context-aware final risk scores")
    print("  ✓ Integrated attack inference")
    print("  ✓ Trust-gated twin adaptation")
    print("  ✓ Online adaptation simulation")
    print("  ✓ Held-out system evaluation")
    print("  ✓ Human-readable alert explanations")

    print(
        "\nLaunch dashboard with:"
    )
    print(
        "  streamlit run dashboard.py"
    )


if __name__ == "__main__":
    run_pipeline()