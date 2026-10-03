import os
import sys
import random
from copy import deepcopy

from agent.task import sampleTask
from agent.agent import TravelAgent
from recorder.recorder import TraceRecorder
from diagnosis.loader import load_traces


# Usage:
#   python generate_more_traces.py        -> adds 3 traces per scenario (33 traces)
#   python generate_more_traces.py 5      -> adds 5 traces per scenario (55 traces)
PER_CLASS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
SEED = 777

BUDGETS = [5000, 5500, 6000, 6500, 7000]
CHECKIN_TIMES = ["13:30", "14:00", "15:00"]

SCENARIOS = [
    {"name": "success", "fault_config": None, "expected_status": "success", "root": None},
    {"name": "wrong_date", "root": 3, "expected_status": "failed",
     "fault_config": {"fault_type": "wrong_date", "root_cause_step_id": 3,
                      "description": "Flight search uses the current date instead of the requested future date."}},
    {"name": "wrong_destination", "root": 3, "expected_status": "failed",
     "fault_config": {"fault_type": "wrong_destination", "root_cause_step_id": 3,
                      "description": "Flight search uses the wrong destination city."}},
    {"name": "budget_violation", "root": 5, "expected_status": "failed",
     "fault_config": {"fault_type": "budget_violation", "root_cause_step_id": 5,
                      "description": "Agent selects a flight above the user's budget."}},
    {"name": "ignored_empty_result", "root": 3, "expected_status": "failed",
     "fault_config": {"fault_type": "ignored_empty_result", "root_cause_step_id": 3,
                      "description": "Flight search returns empty results, but the agent continues with a hallucinated flight."}},
    {"name": "state_overwrite", "root": 9, "expected_status": "failed",
     "fault_config": {"fault_type": "state_overwrite", "root_cause_step_id": 9,
                      "description": "The selected flight is overwritten before booking creation."}},
    {"name": "hotel_checkin_violation", "root": 8, "expected_status": "failed",
     "fault_config": {"fault_type": "hotel_checkin_violation", "root_cause_step_id": 8,
                      "description": "Agent selects a hotel whose check-in time violates the user constraint."}},
    {"name": "wrong_origin", "root": 3, "expected_status": "failed",
     "fault_config": {"fault_type": "wrong_origin", "root_cause_step_id": 3,
                      "description": "Flight search uses the wrong origin city."}},
    {"name": "hotel_wrong_city", "root": 6, "expected_status": "failed",
     "fault_config": {"fault_type": "hotel_wrong_city", "root_cause_step_id": 6,
                      "description": "Hotel search uses the wrong city."}},
    {"name": "hotel_wrong_date", "root": 6, "expected_status": "failed",
     "fault_config": {"fault_type": "hotel_wrong_date", "root_cause_step_id": 6,
                      "description": "Hotel search uses the wrong date."}},
    {"name": "budget_filter_disabled", "root": 4, "expected_status": "failed",
     "fault_config": {"fault_type": "budget_filter_disabled", "root_cause_step_id": 4,
                      "description": "The budget filter is disabled, allowing expensive flights to be selected."}},
]


def create_varied_task(rng: random.Random):
    task = deepcopy(sampleTask())
    task["budget"] = rng.choice(BUDGETS)
    task["hotel_checkin_after"] = rng.choice(CHECKIN_TIMES)
    task["instruction"] = (
        f"Book the cheapest flight from Mumbai to Delhi tomorrow under "
        f"{task['budget']} and book a hotel with check-in after "
        f"{task['hotel_checkin_after']}."
    )
    return task


def run_one(task, fault_config):
    """Runs one scenario and writes the trace into data/traces (append-only)."""
    recorder = TraceRecorder(task=task)  # default base_dir = data/traces

    if fault_config:
        recorder.trace["ground_truth"] = {
            "failure_type": fault_config["fault_type"],
            "root_cause_step_id": fault_config["root_cause_step_id"],
            "notes": fault_config["description"],
        }
    else:
        recorder.trace["ground_truth"] = {
            "failure_type": None,
            "root_cause_step_id": None,
            "notes": "Success baseline",
        }

    agent = TravelAgent(task=task, recorder=recorder, fault_config=fault_config)
    return agent.run()


def main():
    print(f"Black Box: appending {PER_CLASS} trace(s) per scenario to data/traces")

    rng = random.Random(SEED)
    counts = {}
    added = 0

    for i in range(PER_CLASS):
        # One varied task per round, shared by ALL scenarios in that round.
        # This guarantees every failed trace has a matching healthy baseline
        # with identical task parameters (used by the Divergence card).
        task = create_varied_task(rng)

        for scenario in SCENARIOS:
            fault_config = deepcopy(scenario["fault_config"])

            trace = run_one(task=deepcopy(task), fault_config=fault_config)

            if trace["status"] != scenario["expected_status"]:
                raise SystemExit(
                    f"Unexpected status for scenario={scenario['name']}: "
                    f"expected={scenario['expected_status']}, actual={trace['status']}"
                )

            counts[scenario["name"]] = counts.get(scenario["name"], 0) + 1
            added += 1

    total_now = len(load_traces("data/traces"))

    print("Added per scenario:")
    for scenario in SCENARIOS:
        print(f"  {scenario['name']}: {counts.get(scenario['name'], 0)}")

    print(f"Total traces added: {added}")
    print(f"Total traces now in data/traces: {total_now}")
    print("Existing traces were preserved. Reload the Streamlit app to see them.")


if __name__ == "__main__":
    main()