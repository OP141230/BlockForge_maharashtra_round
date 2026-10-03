from typing import Any, Dict, List, Optional


def _safe_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def diff_values(before: Any, after: Any, path: str = "") -> List[Dict[str, Any]]:
    """
    Recursively compares two JSON-like values.

    Returns a list of differences:
        {
            "path": "constraints.date",
            "before": "2026-10-03",
            "after": "2026-10-04"
        }
    """
    diffs: List[Dict[str, Any]] = []

    if isinstance(before, dict) and isinstance(after, dict):
        keys = set(before.keys()) | set(after.keys())

        for key in sorted(keys):
            next_path = f"{path}.{key}" if path else key
            diffs.extend(
                diff_values(
                    before.get(key),
                    after.get(key),
                    next_path,
                )
            )

        return diffs

    if isinstance(before, list) and isinstance(after, list):
        if before != after:
            diffs.append(
                {
                    "path": path or "list",
                    "before": before,
                    "after": after,
                }
            )

        return diffs

    if before != after:
        diffs.append(
            {
                "path": path or "value",
                "before": before,
                "after": after,
            }
        )

    return diffs


def _final_violations(trace: Dict[str, Any]) -> List[Any]:
    trace = _safe_dict(trace)
    final_state = _safe_dict(trace.get("final_state"))
    final_validation = _safe_dict(final_state.get("final_validation"))
    violations = final_validation.get("violations")

    return _safe_list(violations)


def compare_traces(
    original_trace: Dict[str, Any],
    replay_trace: Dict[str, Any],
    intervention: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compares an original failed trace with a replayed trace.

    This is the backend contract for the future Trace Comparison Dashboard.
    """
    original_trace = _safe_dict(original_trace)
    replay_trace = _safe_dict(replay_trace)

    original_steps = _safe_list(original_trace.get("steps"))
    replay_steps = _safe_list(replay_trace.get("steps"))

    replay_steps_by_name: Dict[str, Dict[str, Any]] = {}

    for step in replay_steps:
        step = _safe_dict(step)
        name = step.get("name")

        if name is not None:
            replay_steps_by_name[name] = step

    steps_skipped: List[Any] = []
    steps_replayed: List[Any] = []
    step_diffs: List[Dict[str, Any]] = []

    for original_step in original_steps:
        original_step = _safe_dict(original_step)
        step_name = original_step.get("name")

        replay_step = replay_steps_by_name.get(step_name)

        if replay_step is None:
            steps_skipped.append(step_name)
            continue

        steps_replayed.append(step_name)

        input_diff = diff_values(
            original_step.get("input"),
            replay_step.get("input"),
            path="input",
        )

        output_diff = diff_values(
            original_step.get("output"),
            replay_step.get("output"),
            path="output",
        )

        if input_diff or output_diff:
            step_diffs.append(
                {
                    "step_name": step_name,
                    "original_step_id": original_step.get("step_id"),
                    "replay_step_id": replay_step.get("step_id"),
                    "input_diff": input_diff,
                    "output_diff": output_diff,
                }
            )

    state_diff = diff_values(
        original_trace.get("final_state"),
        replay_trace.get("final_state"),
        path="final_state",
    )

    violations_before = _final_violations(original_trace)
    violations_after = _final_violations(replay_trace)

    removed_violations = [
        violation
        for violation in violations_before
        if violation not in violations_after
    ]

    added_violations = [
        violation
        for violation in violations_after
        if violation not in violations_before
    ]

    original_status = original_trace.get("status")
    replay_status = replay_trace.get("status")

    replay_final_state = _safe_dict(replay_trace.get("final_state"))
    replay_final_validation = _safe_dict(replay_final_state.get("final_validation"))

    fixed = (
        original_status != "success"
        and replay_status == "success"
        and bool(replay_final_validation.get("success"))
    )

    return {
        "original_trace_id": original_trace.get("trace_id"),
        "replay_trace_id": replay_trace.get("trace_id"),
        "original_status": original_status,
        "replay_status": replay_status,
        "fixed": fixed,
        "intervention": intervention,
        "steps_skipped": steps_skipped,
        "steps_replayed": steps_replayed,
        "violations_before": violations_before,
        "violations_after": violations_after,
        "removed_violations": removed_violations,
        "added_violations": added_violations,
        "step_diffs": step_diffs,
        "state_diff": state_diff,
    }