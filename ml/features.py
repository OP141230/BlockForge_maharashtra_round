from typing import Any, Dict, List, Tuple

from diagnosis.spec_engine import evaluate_trace


FEATURE_NAMES = [
    "step_position",
    "distance_from_end",
    "is_planner",
    "is_tool_call",
    "is_transform",
    "is_decision",
    "is_validator",
    "is_output",
    "has_error",
    "confidence",
    "low_confidence",
    "latency_ms",
    "output_empty",
    "state_changed_key_count",
    "violation_count",
    "is_earliest_violation",
    "has_search_input_mismatch",
    "has_selected_flight_invalid",
    "has_selected_hotel_invalid",
    "has_booking_input_lost",
    "has_filter_violation",
    "final_violation_count",
]


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
    features["has_error"] = 1.0 if step.get("error") else 0.0

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

    # Spec violation features
    step_violations = _step_violations_for_step(report, step_id)

    features["violation_count"] = float(len(step_violations))

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