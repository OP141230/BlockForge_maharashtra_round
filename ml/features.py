from typing import Any, Dict, List, Tuple

from diagnosis.spec_engine import evaluate_trace


FEATURE_NAMES = [
    "confidence",
    "low_confidence",
    "latency_ms",
    "output_empty",
    "state_changed_key_count",
    "is_earliest_violation",
    "has_search_input_mismatch",
    "has_selected_flight_invalid",
    "has_selected_hotel_invalid",
    "has_booking_input_lost",
    "has_filter_violation",
    "final_violation_count",
    "feeds_earliest_violation",
    "is_ancestor_of_earliest",
    "ancestor_hops_norm",
    "undeclared_state_write",
]


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, (list, dict, str)) and len(value) == 0:
        return True

    return False


def _output_empty(output: Any) -> float:
    if output is None:
        return 1.0

    if not isinstance(output, dict):
        return 0.0

    if len(output) == 0:
        return 1.0

    if all(_is_empty_value(value) for value in output.values()):
        return 1.0

    return 0.0


def _state_changed_key_count(state_before: Any, state_after: Any) -> float:
    state_before = _safe_dict(state_before)
    state_after = _safe_dict(state_after)

    keys = set(state_before.keys()) | set(state_after.keys())
    changed = 0

    for key in keys:
        if state_before.get(key) != state_after.get(key):
            changed += 1

    return float(changed)


def _undeclared_write(step_name: Any, state_before: Any, state_after: Any) -> float:
    """1.0 if the step changed a state key that is not in its declared write set.

    Healthy steps only touch the keys the agent's data-flow map says they write.
    A change anywhere else (a corrupted input, an injected flag) is a generic,
    label-free sign that something other than the step's own logic altered state.
    """
    from diagnosis.provenance import STEP_WRITES

    declared = set(STEP_WRITES.get(step_name, []))
    before = _safe_dict(state_before)
    after = _safe_dict(state_after)
    for key in set(before) | set(after):
        if key not in declared and before.get(key) != after.get(key):
            return 1.0
    return 0.0


def _step_violations_for_step(report: Dict[str, Any], step_id: Any) -> List[Dict[str, Any]]:
    violations = report.get("step_violations", [])
    if not isinstance(violations, list):
        return []

    return [
        violation
        for violation in violations
        if violation.get("step_id") == step_id
    ]


def _has_invariant_prefix(violations: List[Dict[str, Any]], prefixes: Tuple[str, ...]) -> float:
    for violation in violations:
        invariant = violation.get("invariant", "")

        if invariant.startswith(prefixes):
            return 1.0

    return 0.0


def _ancestor_hops(earliest_name: str) -> Dict[str, int]:
    """Steps upstream of `earliest_name` in the agent's data-flow graph.

    Returns {step_name: hops}, where 1 means the step directly writes a state key
    that `earliest_name` reads. Uses the static read/write map from provenance,
    so it needs no ground truth and no fault labels.
    """
    from diagnosis.provenance import STEP_READS, STEP_WRITES

    writers: Dict[str, List[str]] = {}
    for name, keys in STEP_WRITES.items():
        for key in keys:
            writers.setdefault(key, []).append(name)

    hops: Dict[str, int] = {}
    frontier = [earliest_name]
    depth = 0
    while frontier:
        depth += 1
        nxt: List[str] = []
        for name in frontier:
            for key in STEP_READS.get(name, []):
                for parent in writers.get(key, []):
                    if parent != earliest_name and parent not in hops:
                        hops[parent] = depth
                        nxt.append(parent)
        frontier = nxt
    return hops


def build_step_features(
    trace: Dict[str, Any],
    report: Dict[str, Any],
    step: Dict[str, Any],
    max_steps: int,
) -> Dict[str, float]:
    """
    Builds numeric features for one step in one trace.
    """
    step = _safe_dict(step)
    trace = _safe_dict(trace)
    report = _safe_dict(report)

    step_id = step.get("step_id")
    step_type = step.get("type")

    features: Dict[str, float] = {name: 0.0 for name in FEATURE_NAMES}

    # Position features
    if max_steps > 1 and isinstance(step_id, int):
        position = (step_id - 1) / (max_steps - 1)
    else:
        position = 0.0

    features["step_position"] = float(position)
    features["distance_from_end"] = float(1.0 - position)

    # Step type features
    if step_type == "planner":
        features["is_planner"] = 1.0
    elif step_type == "tool_call":
        features["is_tool_call"] = 1.0
    elif step_type == "transform":
        features["is_transform"] = 1.0
    elif step_type == "decision":
        features["is_decision"] = 1.0
    elif step_type == "validator":
        features["is_validator"] = 1.0
    elif step_type == "output":
        features["is_output"] = 1.0

    # Execution features

    confidence = _to_float(step.get("confidence"), default=0.0)
    features["confidence"] = confidence
    features["low_confidence"] = 1.0 if confidence < 0.94 else 0.0

    features["latency_ms"] = _to_float(step.get("latency_ms"), default=0.0)

    # Output/state features
    features["output_empty"] = _output_empty(step.get("output"))
    features["state_changed_key_count"] = _state_changed_key_count(
        step.get("state_before"),
        step.get("state_after"),
    )

    features["undeclared_state_write"] = _undeclared_write(
        step.get("name"), step.get("state_before"), step.get("state_after")
    )

    # Spec violation features
    step_violations = _step_violations_for_step(report, step_id)


    earliest_step_signal = report.get("earliest_step_signal")
    if step_id is not None and step_id == earliest_step_signal:
        features["is_earliest_violation"] = 1.0

    features["has_search_input_mismatch"] = _has_invariant_prefix(
        step_violations,
        ("search_flights.", "search_hotels."),
    )

    features["has_selected_flight_invalid"] = _has_invariant_prefix(
        step_violations,
        ("select_cheapest_flight.",),
    )

    features["has_selected_hotel_invalid"] = _has_invariant_prefix(
        step_violations,
        ("select_hotel.",),
    )

    features["has_booking_input_lost"] = _has_invariant_prefix(
        step_violations,
        ("create_booking.",),
    )

    features["has_filter_violation"] = _has_invariant_prefix(
        step_violations,
        ("filter_flights_by_budget.", "filter_hotels_by_checkin."),
    )

    features["final_violation_count"] = _to_float(
        report.get("total_final_violations"),
        default=0.0,
    )

    # Causal-position features: where is this step relative to the first symptom?
    # A fault can first *show* downstream of the step that caused it (e.g. a bypassed
    # filter shows up when the selector reads its output), so we expose data-flow
    # distance to the earliest violation instead of relying on "earliest" alone.
    if earliest_step_signal is not None:
        earliest_name = None
        for other in _safe_list(trace.get("steps")):
            if _safe_dict(other).get("step_id") == earliest_step_signal:
                earliest_name = _safe_dict(other).get("name")
                break
        hops = _ancestor_hops(earliest_name) if earliest_name else {}
        h = hops.get(step.get("name"))
        if h is not None:
            features["is_ancestor_of_earliest"] = 1.0
            features["feeds_earliest_violation"] = 1.0 if h == 1 else 0.0
            features["ancestor_hops_norm"] = 1.0 / h

    return features


def build_dataset(
    traces: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, float]], List[int], List[Dict[str, Any]]]:
    """
    Converts traces into step-level training examples.

    Label:
        1 if this step is the ground-truth root cause step in a failed trace.
        0 otherwise.
    """
    X: List[Dict[str, float]] = []
    y: List[int] = []
    meta: List[Dict[str, Any]] = []

    for trace in traces:
        trace = _safe_dict(trace)
        report = evaluate_trace(trace)

        status = trace.get("status")
        ground_truth = _safe_dict(trace.get("ground_truth"))
        root_cause_step_id = ground_truth.get("root_cause_step_id")
        failure_type = ground_truth.get("failure_type")

        steps = trace.get("steps", [])
        if not isinstance(steps, list):
            steps = []

        max_steps = len(steps)

        for step in steps:
            step = _safe_dict(step)

            features = build_step_features(
                trace=trace,
                report=report,
                step=step,
                max_steps=max_steps,
            )

            label = 0

            if (
                status == "failed"
                and root_cause_step_id is not None
                and step.get("step_id") == root_cause_step_id
            ):
                label = 1

            X.append(features)
            y.append(label)

            meta.append(
                {
                    "trace_id": trace.get("trace_id"),
                    "step_id": step.get("step_id"),
                    "step_name": step.get("name"),
                    "status": status,
                    "failure_type": failure_type,
                    "root_cause_step_id": root_cause_step_id,
                    "label": label,
                }
            )

    return X, y, meta