from copy import deepcopy
from typing import Any, Dict, List, Optional


CONSTRAINT_SENSITIVE_STEPS = {
    "extract_constraints",
    "search_flights",
    "filter_flights_by_budget",
    "search_hotels",
    "filter_hotels_by_checkin",
}

UPSTREAM_MAP = {
    "filter_flights_by_budget": [
        "search_flights",
    ],
    "select_cheapest_flight": [
        "filter_flights_by_budget",
        "search_flights",
    ],
    "filter_hotels_by_checkin": [
        "search_hotels",
    ],
    "select_hotel": [
        "filter_hotels_by_checkin",
        "search_hotels",
    ],
    "create_booking": [
        "select_cheapest_flight",
        "select_hotel",
    ],
    "validate_final_result": [
        "create_booking",
    ],
    "send_confirmation": [
        "validate_final_result",
    ],
}

FINAL_VIOLATION_HINTS = {
    "booking_missing": [
        "create_booking",
        "select_cheapest_flight",
        "select_hotel",
        "search_flights",
        "search_hotels",
    ],
    "flight_origin_mismatch": [
        "search_flights",
        "select_cheapest_flight",
    ],
    "flight_destination_mismatch": [
        "search_flights",
        "select_cheapest_flight",
    ],
    "flight_date_mismatch": [
        "search_flights",
        "select_cheapest_flight",
    ],
    "flight_budget_violation": [
        "select_cheapest_flight",
        "filter_flights_by_budget",
        "search_flights",
    ],
    "hotel_city_mismatch": [
        "search_hotels",
        "select_hotel",
    ],
    "hotel_date_mismatch": [
        "search_hotels",
        "select_hotel",
    ],
    "hotel_checkin_time_violation": [
        "select_hotel",
        "filter_hotels_by_checkin",
        "search_hotels",
    ],
}


def _safe_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def get_task_constraint_patch(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Builds the correct task constraint state from the original task.
    """
    task = _safe_dict(task)

    return {
        "origin": task.get("origin"),
        "destination": task.get("destination"),
        "date": task.get("date"),
        "flight_price_max": task.get("budget"),
        "hotel_checkin_after": task.get("hotel_checkin_after"),
    }


def get_step_names(trace: Dict[str, Any]) -> List[Any]:
    trace = _safe_dict(trace)
    steps = _safe_list(trace.get("steps"))

    names = []

    for step in steps:
        step = _safe_dict(step)
        name = step.get("name")

        if name is not None:
            names.append(name)

    return names


def get_step_by_name(trace: Dict[str, Any], step_name: str) -> Optional[Dict[str, Any]]:
    trace = _safe_dict(trace)
    steps = _safe_list(trace.get("steps"))

    for step in steps:
        step = _safe_dict(step)

        if step.get("name") == step_name:
            return step

    return None


def build_candidate_step_names(
    trace: Dict[str, Any],
    report: Dict[str, Any],
    scored_steps: List[Dict[str, Any]],
    max_candidates: int = 10,
) -> List[str]:
    """
    Builds an ordered list of candidate steps to attempt interventions on.

    This does not use ground-truth failure labels.
    It uses:
        - ML suspicion scores
        - spec engine violations
        - final violation hints
        - upstream dependencies
    """
    trace = _safe_dict(trace)
    report = _safe_dict(report)

    step_names = get_step_names(trace)
    candidates: List[str] = []

    def add_candidate(name: Optional[str]) -> None:
        if name and name in step_names and name not in candidates:
            candidates.append(name)

    # 1. Add top ML-ranked steps.
    for item in scored_steps[:3]:
        item = _safe_dict(item)
        add_candidate(item.get("name"))

    # 2. Add earliest violation step.
    earliest_step_id = report.get("earliest_step_signal")

    if earliest_step_id is not None:
        steps = _safe_list(trace.get("steps"))

        for step in steps:
            step = _safe_dict(step)

            if step.get("step_id") == earliest_step_id:
                add_candidate(step.get("name"))
                break

    # 3. Add all steps that have spec violations.
    step_violations = _safe_list(report.get("step_violations"))
    violation_step_ids = set()

    for violation in step_violations:
        violation = _safe_dict(violation)
        step_id = violation.get("step_id")

        if step_id is not None:
            violation_step_ids.add(step_id)

    steps = _safe_list(trace.get("steps"))

    for step_id in sorted(violation_step_ids):
        for step in steps:
            step = _safe_dict(step)

            if step.get("step_id") == step_id:
                add_candidate(step.get("name"))
                break

    # 4. Add steps suggested by final violations.
    final_violations = _safe_list(report.get("final_violations"))

    for final_violation in final_violations:
        final_violation = _safe_dict(final_violation)
        violation_name = final_violation.get("violation")

        for hint_name in FINAL_VIOLATION_HINTS.get(violation_name, []):
            add_candidate(hint_name)

    # 5. Expand upstream dependencies.
    for name in list(candidates):
        for upstream_name in UPSTREAM_MAP.get(name, []):
            add_candidate(upstream_name)

    # 6. Fallback: if nothing was selected, use the latest steps.
    if not candidates:
        for name in reversed(step_names):
            add_candidate(name)

    return candidates[:max_candidates]


def propose_interventions(
    trace: Dict[str, Any],
    candidate_step_names: List[str],
) -> List[Dict[str, Any]]:
    """
    Proposes interventions for candidate steps.

    Each intervention contains:
        - intervention_id
        - intervention_type
        - target_step_name
        - target_step_id
        - patch
        - rationale
    """
    trace = _safe_dict(trace)
    task = _safe_dict(trace.get("task"))

    constraint_patch = get_task_constraint_patch(task)
    interventions: List[Dict[str, Any]] = []
    seen_keys = set()

    def add_intervention(intervention: Dict[str, Any]) -> None:
        key = (
            intervention.get("target_step_name"),
            intervention.get("intervention_type"),
        )

        if key not in seen_keys:
            seen_keys.add(key)
            interventions.append(intervention)

    for step_name in candidate_step_names:
        step = get_step_by_name(trace, step_name)

        if step is None:
            continue

        step_id = step.get("step_id")

        # Intervention 1: replay from this step without fault injection.
        add_intervention(
            {
                "intervention_id": f"{step_name}_replay_no_patch",
                "intervention_type": "replay_no_patch",
                "target_step_name": step_name,
                "target_step_id": step_id,
                "patch": {},
                "rationale": "Replay from this step without applying the original fault.",
            }
        )

        # Intervention 2: restore task constraints for constraint-sensitive steps.
        if step_name in CONSTRAINT_SENSITIVE_STEPS:
            add_intervention(
                {
                    "intervention_id": f"{step_name}_restore_task_constraints",
                    "intervention_type": "restore_task_constraints",
                    "target_step_name": step_name,
                    "target_step_id": step_id,
                    "patch": {
                        step_name: {
                            "state_override": {
                                "constraints": deepcopy(constraint_patch),
                            }
                        }
                    },
                    "rationale": "Restore the original task constraints before replaying this step.",
                }
            )

        # Intervention 3: restore booking inputs for create_booking.
        if step_name == "create_booking":
            state_before = _safe_dict(step.get("state_before"))

            patch_state: Dict[str, Any] = {}

            if state_before.get("selected_flight") is not None:
                patch_state["selected_flight"] = deepcopy(
                    state_before.get("selected_flight")
                )

            if state_before.get("selected_hotel") is not None:
                patch_state["selected_hotel"] = deepcopy(
                    state_before.get("selected_hotel")
                )

            if patch_state:
                add_intervention(
                    {
                        "intervention_id": f"{step_name}_restore_booking_inputs",
                        "intervention_type": "restore_booking_inputs",
                        "target_step_name": step_name,
                        "target_step_id": step_id,
                        "patch": {
                            step_name: {
                                "state_override": patch_state,
                            }
                        },
                        "rationale": "Restore previously selected flight and hotel before creating the booking.",
                    }
                )

        # Intervention 4: hotfix the step's own logic. Needed when the bug lives
        # in the agent (a persistent defect) and so survives a plain replay.
        add_intervention(
            {
                "intervention_id": f"{step_name}_disable_step_defect",
                "intervention_type": "disable_step_defect",
                "target_step_name": step_name,
                "target_step_id": step_id,
                "patch": {step_name: {"disable_defects": True}},
                "rationale": "Re-execute this step and the rest of the run with the reference (defect-free) step logic.",
            }
        )

    return interventions