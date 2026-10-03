"""
Root-cause localization metrics, with an honest baseline.

The ranker uses the spec engine's `is_earliest_violation` signal as a feature,
so a perfect score only means something relative to the trivial strategy of
"blame the earliest step the spec engine flagged". `evaluate_localization`
reports both, per fault family, so the model's added value (or lack of it)
is visible.
"""
from typing import Any, Dict, List

from diagnosis.spec_engine import evaluate_trace
from ml.features import FEATURE_NAMES, build_step_features


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _ranker_order(trace: Dict[str, Any], report: Dict[str, Any],
                  weights: Dict[str, float], bias: float) -> List[int]:
    steps = trace.get("steps", []) or []
    scored = []
    for step in steps:
        feats = build_step_features(trace=trace, report=report, step=step, max_steps=len(steps))
        score = bias + sum(weights.get(n, 0.0) * float(feats.get(n, 0.0)) for n in FEATURE_NAMES)
        scored.append((-score, step.get("step_id", 9999), step.get("step_id")))
    scored.sort()
    return [item[2] for item in scored]


def _baseline_order(trace: Dict[str, Any], report: Dict[str, Any]) -> List[int]:
    """Earliest flagged step first, then the remaining steps in execution order."""
    ids = [s.get("step_id") for s in trace.get("steps", []) or []]
    earliest = report.get("earliest_step_signal")
    if earliest in ids:
        return [earliest] + [i for i in ids if i != earliest]
    return ids


def _summarise(ranks: List[int]) -> Dict[str, float]:
    n = len(ranks)
    if n == 0:
        return {"top1": 0.0, "top3": 0.0, "mrr": 0.0}
    return {
        "top1": sum(r == 1 for r in ranks) / n,
        "top3": sum(r <= 3 for r in ranks) / n,
        "mrr": sum(1.0 / r for r in ranks) / n,
    }


def evaluate_localization(traces: List[Dict[str, Any]], weights: Dict[str, float],
                          bias: float = 0.0) -> Dict[str, Any]:
    ranker_ranks: List[int] = []
    baseline_ranks: List[int] = []
    by_family: Dict[str, Dict[str, List[int]]] = {}

    for trace in traces:
        trace = _safe_dict(trace)
        if trace.get("status") != "failed":
            continue
        truth = _safe_dict(trace.get("ground_truth"))
        root = truth.get("root_cause_step_id")
        if root is None:
            continue

        report = evaluate_trace(trace)
        r_order = _ranker_order(trace, report, weights, bias)
        b_order = _baseline_order(trace, report)
        if root not in r_order:
            continue

        r_rank = r_order.index(root) + 1
        b_rank = b_order.index(root) + 1
        ranker_ranks.append(r_rank)
        baseline_ranks.append(b_rank)

        fam = by_family.setdefault(str(truth.get("failure_type")), {"ranker": [], "baseline": []})
        fam["ranker"].append(r_rank)
        fam["baseline"].append(b_rank)

    return {
        "failed_traces": len(ranker_ranks),
        "ranker": _summarise(ranker_ranks),
        "baseline_earliest_violation": _summarise(baseline_ranks),
        "per_family": {
            name: {
                "n": len(v["ranker"]),
                "ranker_top1": _summarise(v["ranker"])["top1"],
                "baseline_top1": _summarise(v["baseline"])["top1"],
            }
            for name, v in sorted(by_family.items())
        },
    }


def format_localization(result: Dict[str, Any], title: str) -> str:
    r, b = result["ranker"], result["baseline_earliest_violation"]
    lines = [
        f"{title} (n={result['failed_traces']} failed traces)",
        f"  ranker    : top1={r['top1']:.3f} top3={r['top3']:.3f} mrr={r['mrr']:.3f}",
        f"  baseline  : top1={b['top1']:.3f} top3={b['top3']:.3f} mrr={b['mrr']:.3f}  (earliest spec violation only)",
    ]
    for name, fam in result["per_family"].items():
        lines.append(f"    {name:<26} n={fam['n']:<3} ranker_top1={fam['ranker_top1']:.2f} baseline_top1={fam['baseline_top1']:.2f}")
    return "\n".join(lines)
