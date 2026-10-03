"""
Run the whole Black Box pipeline from the repo root, regardless of where this
is invoked from. Stops at the first failing step.

    python run_all.py            # pipeline
    python run_all.py --tests    # pipeline + pytest
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    "main.py",
    "generate_dataset.py",
    "diagnose.py",
    "generate_training_dataset.py",
    "train_ranker.py",
    "replay_and_validate.py",
    "advanced/run_advanced_replay.py",
    "advanced/provenance_analysis.py",
    "advanced/contrastive_dataset.py",
    "advanced/train_intervention_model.py",
    "advanced/generate_unseen_dataset.py",
    "advanced/evaluate_unseen.py",
    "advanced/evaluate_persistent.py",
]


def main() -> int:
    steps = [[sys.executable, s] for s in STEPS]
    if "--tests" in sys.argv:
        steps.append([sys.executable, "-m", "pytest", "-q"])

    for cmd in steps:
        label = " ".join(cmd[1:])
        print(f"\n=== {label}", flush=True)
        t0 = time.time()
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            print(f"\nFAILED: {label} (exit {result.returncode})")
            return result.returncode
        print(f"--- ok ({time.time() - t0:.1f}s)")
    print("\nAll steps passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
