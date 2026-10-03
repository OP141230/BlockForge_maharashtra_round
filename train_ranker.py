import json
import os
from typing import Any, Dict, List, Tuple

from diagnosis.loader import load_traces
from diagnosis.spec_engine import evaluate_trace
from ml.features import FEATURE_NAMES, build_dataset, build_step_features, _safe_dict


def train_feature_weight_model(X: List[Dict[str, float]], y: List[int]):
    """
    Trains a lightweight linear feature-weight ranker.
    """
    positives = [features for features, label in zip(X, y) if label == 1]
    negatives = [features for features, label in zip(X, y) if label == 0]

    weights: Dict[str, float] = {}

    for feature_name in FEATURE_NAMES:
        positive_mean = 0.0
        negative_mean = 0.0

        if positives:
            positive_mean = sum(
                float(features.get(feature_name, 0.0)) for features in positives
            ) / len(positives)

        if negatives:
            negative_mean = sum(
                float(features.get(feature_name, 0.0)) for features in negatives
            ) / len(negatives)

        weights[feature_name] = positive_mean - negative_mean

    bias = 0.0
    return weights, bias


def score_features(weights: Dict[str, float], bias: float, features: Dict[str, float]) -> float:
    """
    Computes suspicion score for one step.
    """
    score = bias
    for feature_name in FEATURE_NAMES:
        score += weights.get(feature_name, 0.0) * float(features.get(feature_name, 0.0))
    return score


def evaluate_ranking(traces: List[Dict[str, Any]], weights: Dict[str, float], bias: float) -> Dict[str, Any]:
    """
    Evaluates root-cause ranking on failed traces.
    """
    failed_traces = 0
    top1_hits = 0
    top3_hits = 0
    reciprocal_rank_sum = 0.0

    for trace in traces:
        trace = _safe_dict(trace)
        if trace.get("status") != "failed":
            continue

        ground_truth = _safe_dict(trace.get("ground_truth"))
        root_cause_step_id = ground_truth.get("root_cause_step_id")
        if root_cause_step_id is None:
            continue

        failed_traces += 1
        report = evaluate_trace(trace)

        steps = trace.get("steps", [])
        if not isinstance(steps, list):
            steps = []

        max_steps = len(steps)
        scored_steps = []

        for step in steps:
            step = _safe_dict(step)
            features = build_step_features(trace=trace, report=report, step=step, max_steps=max_steps)
            score = score_features(weights, bias, features)
            scored_steps.append({
                "step_id": step.get("step_id"),
                "step_name": step.get("name"),
                "score": score,
            })

        scored_steps.sort(
            key=lambda item: (
                -item["score"],
                item["step_id"] if isinstance(item["step_id"], int) else 9999,
            )
        )

        rank = None
        for index, item in enumerate(scored_steps):
            if item["step_id"] == root_cause_step_id:
                rank = index
                break

        if rank is None:
            continue

        if rank == 0:
            top1_hits += 1
        if rank < 3:
            top3_hits += 1

        reciprocal_rank_sum += 1.0 / (rank + 1)

    if failed_traces == 0:
        return {"failed_traces": 0, "top1": 0.0, "top3": 0.0, "mrr": 0.0}

    return {
        "failed_traces": failed_traces,
        "top1": top1_hits / failed_traces,
        "top3": top3_hits / failed_traces,
        "mrr": reciprocal_rank_sum / failed_traces,
    }


def train_ranker(traces: List[Dict[str, Any]]) -> Tuple[Dict[str, float], float]:
    """
    Reusable function to train the ranker on any list of traces.
    Returns (weights, bias).
    """
    X_train, y_train, _ = build_dataset(traces)
    if not X_train:
        return {}, 0.0
    weights, bias = train_feature_weight_model(X_train, y_train)
    return weights, bias


def main():
    print("Black Box Phase 4 model training")

    train_traces = load_traces("data/training_traces/train")
    test_traces = load_traces("data/training_traces/test")

    print(f"Training traces: {len(train_traces)}")
    print(f"Test traces: {len(test_traces)}")

    weights, bias = train_ranker(train_traces)

    model = {
        "model_type": "feature_weight_ranker",
        "description": "Lightweight learned ranker for Black Box failure localization.",
        "feature_names": FEATURE_NAMES,
        "weights": weights,
        "bias": bias,
    }

    os.makedirs("data/models", exist_ok=True)
    model_path = os.path.join("data/models", "ranker.json")

    with open(model_path, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, ensure_ascii=False)

    metrics = evaluate_ranking(test_traces, weights, bias)

    print(f"Test failed traces: {metrics['failed_traces']}")
    print(f"Top-1 accuracy: {metrics['top1']:.4f}")
    print(f"Top-3 accuracy: {metrics['top3']:.4f}")
    print(f"MRR: {metrics['mrr']:.4f}")
    print(f"Saved model to: {model_path}")

    # Save metrics for UI live reading
    metrics_path = os.path.join("data", "models", "ranker_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump({
            "test_failed_traces": metrics["failed_traces"],
            "top1": metrics["top1"],
            "top3": metrics["top3"],
            "mrr": metrics["mrr"],
        }, f, indent=2)

if __name__ == "__main__":
    main()