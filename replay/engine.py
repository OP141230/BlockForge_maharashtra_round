import os
import re
import json
from typing import Any, Dict

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


def get_replay_config(failure_type: str, task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Defines the intervention required to fix each known failure type.
    """
    if failure_type == "wrong_date":
        return {
            "start_step_name": "search_flights",
            "patches": {
                "search_flights": {
                    "state_override": {
                        "constraints": {
                            "date": task["date"]
                        }
                    }
                }
            },
        }

    elif failure_type == "wrong_destination":
        return {
            "start_step_name": "search_flights",
            "patches": {
                "search_flights": {
                    "state_override": {
                        "constraints": {
                            "destination": task["destination"]
                        }
                    }
                }
            },
        }

    elif failure_type == "budget_violation":
        return {
            "start_step_name": "select_cheapest_flight",
            "patches": {},
        }

    elif failure_type == "ignored_empty_result":
        return {
            "start_step_name": "search_flights",
            "patches": {},
        }

    elif failure_type == "state_overwrite":
        return {
            "start_step_name": "create_booking",
            "patches": {},
        }

    elif failure_type == "hotel_checkin_violation":
        return {
            "start_step_name": "select_hotel",
            "patches": {},
        }

    else:
        return {
            "start_step_name": "parse_request",
            "patches": {},
        }


def run_replay(
    task: Dict[str, Any],
    initial_state: Dict[str, Any],
    start_step_name: str,
    patches: Dict[str, Any],
    base_dir: str = "data/replays",
) -> Dict[str, Any]:
    """
    Executes a counterfactual replay of the agent from a checkpoint.
    """
    recorder = TraceRecorder(task=task, base_dir=base_dir)

    agent = TravelAgent(
        task=task,
        recorder=recorder,
        fault_config=None,
        initial_state=initial_state,
        start_step_name=start_step_name,
        patches=patches,
    )

    trace = agent.run()
    return trace