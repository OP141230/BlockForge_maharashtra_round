import os
import random
import shutil
from copy import deepcopy

from agent.task import sampleTask
from agent.agent import TravelAgent
from recorder.recorder import TraceRecorder


SEED = 42
TRAIN_PER_CLASS = 10
TEST_PER_CLASS = 4

BUDGETS = [5000, 5500, 6000, 6500, 7000]
CHECKIN_TIMES = ["13:30", "14:00", "15:00"]

SCENARIOS = [
    {
        "name": "success",
        "fault_config": None,
        "expected_status": "success",
    },
    {
        "name": "wrong_date",
        "fault_config": {
            "fault_type": "wrong_date",
            "root_cause_step_id": 3,
            "description": "Flight search uses the current date instead of the requested future date.",
        },
        "expected_status": "failed",
    },
    {
        "name": "wrong_destination",
        "fault_config": {
            "fault_type": "wrong_destination",
            "root_cause_step_id": 3,
            "description": "Flight search uses the wrong destination city.",
        },
        "expected_status": "failed",
    },
    {
        "name": "budget_violation",
        "fault_config": {
            "fault_type": "budget_violation",
            "root_cause_step_id": 5,
            "description": "Agent selects a flight above the user's budget.",
        },
        "expected_status": "failed",
    },
    {
        "name": "ignored_empty_result",
        "fault_config": {
            "fault_type": "ignored_empty_result",
            "root_cause_step_id": 3,
            "description": "Flight search returns empty results, but the agent continues with a hallucinated flight.",
        },
        "expected_status": "failed",
    },
    {
        "name": "state_overwrite",
        "fault_config": {
            "fault_type": "state_overwrite",
            "root_cause_step_id": 9,
            "description": "The selected flight is overwritten before booking creation.",
        },
        "expected_status": "failed",
    },
    {
        "name": "hotel_checkin_violation",
        "fault_config": {
            "fault_type": "hotel_checkin_violation",
            "root_cause_step_id": 8,
            "description": "Agent selects a hotel whose check-in time violates the user constraint.",
        },
        "expected_status": "failed",
    },
]


def create_varied_task(rng: random.Random):
    """
    Creates a task with small controlled variations.

    The route and date remain fixed because the deterministic mock tools
    are defined for Mumbai -> Delhi on 2026-10-04.
    """
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
    """
    Runs one agent scenario and stores its trace.
    """
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
    """
    Generates one dataset split: train or test.
    """
    rng = random.Random(seed)
    base_dir = os.path.join("data", "training_traces", split_name)
    os.makedirs(base_dir, exist_ok=True)

    counts = {}

    for scenario in SCENARIOS:
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
    print("Black Box Phase 4 training dataset generation")

    training_root = os.path.join("data", "training_traces")

    if os.path.exists(training_root):
        shutil.rmtree(training_root)

    train_counts = generate_split(
        split_name="train",
        per_class=TRAIN_PER_CLASS,
        seed=SEED,
    )

    test_counts = generate_split(
        split_name="test",
        per_class=TEST_PER_CLASS,
        seed=SEED + 1,
    )

    total_train = sum(train_counts.values())
    total_test = sum(test_counts.values())

    print("Training split generated:")
    for scenario in SCENARIOS:
        name = scenario["name"]
        print(f"  {name}: {train_counts.get(name, 0)}")

    print("Test split generated:")
    for scenario in SCENARIOS:
        name = scenario["name"]
        print(f"  {name}: {test_counts.get(name, 0)}")

    print(f"Total train traces: {total_train}")
    print(f"Total test traces: {total_test}")
    print("Phase 4 dataset generation completed successfully.")


if __name__ == "__main__":
    main()