import os
import re
import json
from typing import Any, Dict, Iterable, Optional

from agent.agent import TravelAgent
from recorder.recorder import TraceRecorder


def _unwrap_checkpoint(payload: Any) -> Dict[str, Any]:
    """
    Checkpoint files are stored as:
    {
        "trace_id": ...,
        "step_id": ...,
        "step_name": ...,
        "state": { ... actual agent state ... }
    }

    This function extracts the actual agent state.
    """
    if isinstance(payload, dict) and "state" in payload:
        state = payload.get("state")
        if isinstance(state, dict):
            return state
        return {}

    if isinstance(payload, dict):
        return payload

    return {}


def load_checkpoint_before_step(trace_dir: str, step_id: int) -> Dict[str, Any]:
    """
    Loads the latest checkpoint whose step_id is strictly less than the target step_id.
    """
    checkpoint_dir = os.path.join(trace_dir, "checkpoints")

    if not os.path.isdir(checkpoint_dir):
        raise FileNotFoundError(
            f"Checkpoint directory not found: {checkpoint_dir}"
        )

    candidates = []

    for filename in os.listdir(checkpoint_dir):
        if not filename.lower().endswith(".json"):
            continue

        match = re.search(r"step_(\d+)", filename)
        if not match:
            continue

        checkpoint_step_id = int(match.group(1))

        if checkpoint_step_id < int(step_id):
            candidates.append(
                (
                    checkpoint_step_id,
                    os.path.join(checkpoint_dir, filename),
                )
            )

    if not candidates:
        existing_files = sorted(os.listdir(checkpoint_dir))
        raise FileNotFoundError(
            f"No checkpoint found before step {step_id} in {trace_dir}. "
            f"Existing checkpoint files: {existing_files}"
        )

    candidates.sort(key=lambda item: item[0])
    selected_path = candidates[-1][1]

    with open(selected_path, "r", encoding="utf-8") as f:
        checkpoint_payload = json.load(f)

    return _unwrap_checkpoint(checkpoint_payload)


# Fault type -> (step to restart from, whether to restore the task value of a
# constraint key before that step). Unknown fault types fall back to a full
# replay from parse_request.
_REPLAY_CONFIGS: Dict[str, Dict[str, Any]] = {
    "wrong_date": {"start": "search_flights", "restore_key": "date"},
    "wrong_destination": {"start": "search_flights", "restore_key": "destination"},
    "budget_violation": {"start": "select_cheapest_flight"},
    "ignored_empty_result": {"start": "search_flights"},
    "state_overwrite": {"start": "create_booking"},
    "hotel_checkin_violation": {"start": "select_hotel"},
}


def get_replay_config(failure_type: str, task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Defines the intervention required to fix each known failure type.
    """
    spec = _REPLAY_CONFIGS.get(failure_type)
    if spec is None:
        return {"start_step_name": "parse_request", "patches": {}}

    patches: Dict[str, Any] = {}
    restore_key = spec.get("restore_key")
    if restore_key:
        patches[spec["start"]] = {
            "state_override": {"constraints": {restore_key: task[restore_key]}}
        }

    return {"start_step_name": spec["start"], "patches": patches}


def run_replay(
    task: Dict[str, Any],
    initial_state: Dict[str, Any],
    start_step_name: str,
    patches: Dict[str, Any],
    base_dir: str = "data/replays",
    defects: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Executes a counterfactual replay of the agent from a checkpoint.

    Injected faults are NOT re-applied (fault_config=None). Persistent defects
    in the agent's own logic are passed through via `defects`, so they survive
    replay unless a patch disables them.
    """
    recorder = TraceRecorder(task=task, base_dir=base_dir)

    agent = TravelAgent(
        task=task,
        recorder=recorder,
        fault_config=None,
        initial_state=initial_state,
        start_step_name=start_step_name,
        patches=patches,
        defects=defects,
    )

    trace = agent.run()
    return trace