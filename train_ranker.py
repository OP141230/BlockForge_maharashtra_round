import json
import os
from typing import Any, Dict, List, Tuple

from diagnosis.loader import load_traces
from diagnosis.spec_engine import evaluate_trace
from ml.features import FEATURE_NAMES, build_dataset, build_step_features, _safe_dict


def train_feature_weight_model(
    X: List[Dict[str, float]],
    y: List[int],
) -> Tuple[Dict[str, float], float, Dict[str, Any]]:
    """
    Trains a lightweight linear feature-weight ranker.

    For each feature, weight is:
        mean feature value in positive examples
      - mean feature value in negative examples

    This is intentionally simple and dependency-free.
    Later it can be replaced by a stronger learned ranker.
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

    stats = {
        "training_samples": len(X),
        "positive_samples": len(positives),
        "negative_samples": len(negatives),
    }

    return weights, bias, stats


def score_features(
    weights: Dict[str, float],
    bias: float,
    features: Dict[str, float],
) -> float:
    """
    Computes suspicion score for one step.
    """
    score = bias

    for feature_name in FEATURE_NAMES:
        score += weights.get(feature_name, 0.0) * float(features.get(feature_name, 0.0))

    return score


def evaluate_ranking(
    traces: List[Dict[str, Any]],
    weights: Dict[str, float],
    bias: float,
) -> Dict[str, Any]:
    """
    Evaluates root-cause ranking on failed traces.

    Metrics:
        Top-1 accuracy
        Top-3 accuracy
        Mean Reciprocal Rank
    """
    failed_traces = 0
    top1_hits = 0
    top3_hits = 0
    reciprocal_rank_sum = 0.0
    details = []

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

            features = build_step_features(
                trace=trace,
                report=report,
                step=step,
                max_steps=max_steps,
            )

            score = score_features(weights, bias, features)

            scored_steps.append(
                {
                    "step_id": step.get("step_id"),
                    "step_name": step.get("name"),
                    "score": score,
                }
            )

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
            raise SystemExit(
                f"Root cause step not found in scored steps. "
                f"trace_id={trace.get('trace_id')}, "
                f"root_cause_step_id={root_cause_step_id}"
            )

        if rank == 0:
            top1_hits += 1

        if rank < 3:
            top3_hits += 1

        reciprocal_rank_sum += 1.0 / (rank + 1)

        details.append(
            {
                "trace_id": trace.get("trace_id"),
                "failure_type": ground_truth.get("failure_type"),
                "root_cause_step_id": root_cause_step_id,
                "predicted_top1_step_id": scored_steps[0]["step_id"],
                "rank": rank + 1,
            }
        )

    if failed_traces == 0:
        return {
            "failed_traces": 0,
            "top1": 0.0,
            "top3": 0.0,
            "mrr": 0.0,
            "details": details,
        }

    return {
        "failed_traces": failed_traces,
        "top1": top1_hits / failed_traces,
        "top3": top3_hits / failed_traces,
        "mrr": reciprocal_rank_sum / failed_traces,
        "details": details,
    }


def main():
    print("Black Box Phase 4 model training")

    train_traces = load_traces("data/training_traces/train")
    test_traces = load_traces("data/training_traces/test")

    print(f"Training traces: {len(train_traces)}")
    print(f"Test traces: {len(test_traces)}")

    X_train, y_train, meta_train = build_dataset(train_traces)

    print(f"Training samples: {len(X_train)}")
    print(f"Positive samples: {sum(y_train)}")
    print(f"Negative samples: {len(y_train) - sum(y_train)}")

    weights, bias, training_stats = train_feature_weight_model(X_train, y_train)

    model = {
        "model_type": "feature_weight_ranker",
        "description": "Lightweight learned ranker for Black Box failure localization.",
        "feature_names": FEATURE_NAMES,
        "weights": weights,
        "bias": bias,
        "training_stats": training_stats,
    }

    os.makedirs("data/models", exist_ok=True)
    model_path = os.path.join("data/models", "ranker.json")

    with open(model_path, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, ensure_ascii=False)

    metrics = evaluate_ranking(test_traces, weights, bias)
    metrics_path = os.path.join("data", "models", "ranker_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "test_failed_traces": metrics["failed_traces"],
                "top1": metrics["top1"],
                "top3": metrics["top3"],
                "mrr": metrics["mrr"],
            },
            f,
            indent=2,
        )

    print(f"Test failed traces: {metrics['failed_traces']}")
    print(f"Top-1 accuracy: {metrics['top1']:.4f}")
    print(f"Top-3 accuracy: {metrics['top3']:.4f}")
    print(f"MRR: {metrics['mrr']:.4f}")
    print(f"Saved model to: {model_path}")

    if metrics["failed_traces"] == 0:
        raise SystemExit("No failed test traces found. Dataset generation failed.")

    if metrics["top1"] < 0.90:
        raise SystemExit("Phase 4 validation failed: Top-1 accuracy below 0.90.")

    if metrics["top3"] < 0.95:
        raise SystemExit("Phase 4 validation failed: Top-3 accuracy below 0.95.")

    if metrics["mrr"] < 0.90:
        raise SystemExit("Phase 4 validation failed: MRR below 0.90.")

    print("Phase 4 training completed successfully.")


if __name__ == "__main__":
    main()