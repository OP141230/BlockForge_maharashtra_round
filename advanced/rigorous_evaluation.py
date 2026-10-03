"""Held-out evaluation: baselines, failure-detection AUC, learning curve, ablations.

Everything here is computed from the traces in data/massive_traces/. Nothing is
hard-coded, and the sample sizes are written next to every metric so the numbers
can be judged honestly.
"""
import json
import os
import random
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import ml.features as mlf
import train_ranker as tr
from diagnosis.loader import load_traces
from diagnosis.spec_engine import evaluate_trace

SEED = 0


def load_split(path):
    return load_traces(path) if os.path.exists(path) else []


def failed_only(traces):
    return [t for t in traces if t["status"] == "failed"]


def baselines(traces, n_random=200):
    """Expected top-1 of step-position baselines on failed traces (random is averaged)."""
    failed = failed_only(traces)
    if not failed:
        return {}
    rng = random.Random(SEED)
    root = lambda t: t["ground_truth"]["root_cause_step_id"]
    n = len(failed)
    rand = sum(
        sum(rng.randrange(len(t["steps"])) == root(t) for t in failed) / n
        for _ in range(n_random)
    ) / n_random
    return {
        "n_failed": n,
        "random_step": rand,
        "always_first_step": sum(root(t) == 0 for t in failed) / n,
        "always_last_step": sum(root(t) == len(t["steps"]) - 1 for t in failed) / n,
    }


def auc(scores, labels):
    """Rank-based ROC AUC (Mann-Whitney U), ties count half."""
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return None
    wins = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return wins / (len(pos) * len(neg))


def fail_detection(traces):
    """AUC of the spec engine's violation count as a failed-run detector."""
    scores = [len(evaluate_trace(t).get("step_violations", [])) for t in traces]
    labels = [t["status"] == "failed" for t in traces]
    return {"n": len(traces), "auc": auc(scores, labels)}


def with_feature_zeroed(feature, fn):
    """Run fn() with `feature` zeroed everywhere the ranker builds features."""
    original = mlf.build_step_features

    def patched(*a, **k):
        f = original(*a, **k)
        f[feature] = 0.0
        return f

    # ml.features (used by build_dataset) and train_ranker (used by evaluate_ranking)
    # each hold their own reference; patch both or the ablation is a silent no-op.
    mlf.build_step_features = patched
    tr.build_step_features = patched
    try:
        return fn()
    finally:
        mlf.build_step_features = original
        tr.build_step_features = original


def main():
    print("Held-out evaluation (baselines, AUC, learning curve, ablations)...")
    train = load_split("data/massive_traces/seen_train")
    splits = {
        "seen_test": load_split("data/massive_traces/seen_test"),
        "unseen_fault": load_split("data/massive_traces/unseen_fault_test"),
        "unseen_task": load_split("data/massive_traces/unseen_task_test"),
    }
    if not train:
        raise SystemExit("No traces found. Run advanced/generate_massive_dataset.py first.")

    w, b = tr.train_ranker(train)
    full = {}
    for name, traces in splits.items():
        m = tr.evaluate_ranking(traces, w, b)
        full[name] = {"top1": m["top1"], "n_failed": len(failed_only(traces))}

    # Learning curve: only sizes that really exist, shuffled with a fixed seed.
    rng = random.Random(SEED)
    shuffled = train[:]
    rng.shuffle(shuffled)
    curve = []
    for size in sorted({s for s in (30, 60, 120, 240, len(train)) if s <= len(train)}):
        wi, bi = tr.train_ranker(shuffled[:size])
        curve.append({
            "train_runs": size,
            "seen_test_top1": tr.evaluate_ranking(splits["seen_test"], wi, bi)["top1"],
            "unseen_fault_top1": tr.evaluate_ranking(splits["unseen_fault"], wi, bi)["top1"],
        })

    # Ablations, scored on every held-out split (not just one).
    ablation = {"full_model": {k: v["top1"] for k, v in full.items()}}
    for feat in ("is_earliest_violation", "undeclared_state_write", "feeds_earliest_violation", "is_ancestor_of_earliest"):
        def run(feat=feat):
            wa, ba = tr.train_ranker(train)
            return {k: tr.evaluate_ranking(t, wa, ba)["top1"] for k, t in splits.items()}
        ablation[f"no_{feat}"] = with_feature_zeroed(feat, run)

    results = {
        "n_train_traces": len(train),
        "full_model": full,
        "baselines": {k: baselines(t) for k, t in splits.items()},
        "fail_detection": {k: fail_detection(t) for k, t in splits.items()},
        "learning_curve": curve,
        "ablation": ablation,
    }
    os.makedirs("data/models", exist_ok=True)
    with open("data/models/rigorous_metrics.json", "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
