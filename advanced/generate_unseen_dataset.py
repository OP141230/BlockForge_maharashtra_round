import os
import sys
import random
import shutil
from copy import deepcopy

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agent.task import sampleTask
from agent.agent import TravelAgent
from recorder.recorder import TraceRecorder

SEED = 123
UNSEEN_PER_CLASS = 5

BUDGETS = [5000, 5500, 6000, 6500, 7000]
CHECKIN_TIMES = ["13:30", "14:00", "15:00"]

UNSEEN_SCENARIOS = [
    {
        "name": "wrong_origin",
        "fault_config": {
            "fault_type": "wrong_origin",
            "root_cause_step_id": 3,
            "description": "Flight search uses the wrong origin city.",
        },
        "expected_status": "failed",
    },
    {
        "name": "hotel_wrong_city",
        "fault_config": {
            "fault_type": "hotel_wrong_city",
            "root_cause_step_id": 6,
            "description": "Hotel search uses the wrong city.",
        },
        "expected_status": "failed",
    },
    {
        "name": "hotel_wrong_date",
        "fault_config": {
            "fault_type": "hotel_wrong_date",
            "root_cause_step_id": 6,
            "description": "Hotel search uses the wrong date.",
        },
        "expected_status": "failed",
    },
    {
        "name": "budget_filter_disabled",
        "fault_config": {
            "fault_type": "budget_filter_disabled",
            "root_cause_step_id": 4,
            "description": "The budget filter is disabled, allowing expensive flights to be selected.",
        },
        "expected_status": "failed",
    },
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

def run_scenario(base_dir, task, fault_config):
    recorder = TraceRecorder(task=task, base_dir=base_dir)

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

    agent = TravelAgent(
        task=task,
        recorder=recorder,
        fault_config=fault_config,
    )

    trace = agent.run()
    return trace

def generate_split(split_name, per_class, seed):
    rng = random.Random(seed)
    base_dir = os.path.join("data", "unseen_traces", split_name)
    os.makedirs(base_dir, exist_ok=True)

    counts = {}

    for scenario in UNSEEN_SCENARIOS:
        scenario_name = scenario["name"]
        expected_status = scenario["expected_status"]

        for i in range(per_class):
            task = create_varied_task(rng)

            fault_config = None
            if scenario["fault_config"] is not None:
                fault_config = deepcopy(scenario["fault_config"])

            trace = run_scenario(
                base_dir=base_dir,
                task=task,
                fault_config=fault_config,
            )

            if trace["status"] != expected_status:
                raise SystemExit(
                    f"Generated trace had unexpected status. "
                    f"scenario={scenario_name}, "
                    f"expected={expected_status}, "
                    f"actual={trace['status']}, "
                    f"trace_id={trace['trace_id']}"
                )

            counts[scenario_name] = counts.get(scenario_name, 0) + 1

    return counts

def main():
    print("Black Box Phase 7E: Unseen Fault Dataset Generation")

    training_root = os.path.join("data", "unseen_traces")

    if os.path.exists(training_root):
        shutil.rmtree(training_root)

    unseen_counts = generate_split(
        split_name="test",
        per_class=UNSEEN_PER_CLASS,
        seed=SEED,
    )

    total_unseen = sum(unseen_counts.values())

    print("Unseen test split generated:")
    for scenario in UNSEEN_SCENARIOS:
        name = scenario["name"]
        print(f"  {name}: {unseen_counts.get(name, 0)}")

    print(f"Total unseen test traces: {total_unseen}")
    print("Phase 7E dataset generation completed successfully.")

if __name__ == "__main__":
    main()