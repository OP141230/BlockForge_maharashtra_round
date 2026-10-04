"""Tests for Benchmark Runner and Evaluation Studio metrics.

Thresholds are set against the 10-case TEST split.  The benchmark now
deliberately includes hard cases where the root cause is NOT the first
error, NOT the slowest step, and NOT the last step — so Top-3 accuracy
below 100% is expected and honest.
"""
from backend.evaluation import BenchmarkRunner


def test_benchmark_metrics():
    report = BenchmarkRunner.run_benchmark()

    # Structural checks
    assert report["total_cases"] >= 10, "Expected at least 10 benchmark cases"
    assert "test_cases" in report
    assert "validation_cases" in report
    assert report["test_cases"] >= 10
    assert report["validation_cases"] == 4  # no-fault fixture excluded from scoring

    models = report["models"]  # TEST split metrics
    hybrid    = models["blackbox_hybrid"]
    last_step = models["baseline_last_step"]

    # Hybrid must beat the last-step heuristic on Top-1
    assert hybrid["top1_accuracy"] >= last_step["top1_accuracy"], (
        "Hybrid Top-1 should be at least as good as last-step baseline"
    )

    # Reasonable thresholds for 10 non-trivial cases
    assert hybrid["top1_accuracy"] >= 0.30, (
        f"Top-1 unexpectedly low: {hybrid['top1_accuracy']}"
    )
    assert hybrid["top3_accuracy"] >= 0.60, (
        f"Top-3 unexpectedly low: {hybrid['top3_accuracy']}"
    )
    assert hybrid["mrr"] >= 0.45, (
        f"MRR unexpectedly low: {hybrid['mrr']}"
    )

    # Split note must be present (honesty requirement)
    assert "split_note" in report
    assert "leakage" in report["split_note"].lower()
