"""Tests for Benchmark Runner and Evaluation Studio metrics."""
from backend.evaluation import BenchmarkRunner


def test_benchmark_metrics():
    report = BenchmarkRunner.run_benchmark()
    assert report["total_cases"] >= 5
    models = report["models"]
    hybrid = models["blackbox_hybrid"]
    last_step = models["baseline_last_step"]

    # Hybrid should have higher Top-1 accuracy than last-step heuristic
    assert hybrid["top1_accuracy"] >= last_step["top1_accuracy"]
    assert hybrid["top3_accuracy"] >= 0.80
    assert hybrid["mrr"] >= 0.70
