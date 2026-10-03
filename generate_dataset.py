from copy import deepcopy

from agent.task import sampleTask
from agent.agent import TravelAgent
from recorder.recorder import TraceRecorder


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
            "root_cause_step_id": 5,
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


def run_scenario(base_task, fault_config, expected_status):
    """
    Runs one agent scenario and verifies that its final status matches expectation.
    """
    task = deepcopy(base_task)

    recorder = TraceRecorder(task=task)

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
            "notes": "Phase 2: success baseline",
        }

    agent = TravelAgent(
        task=task,
        recorder=recorder,
        fault_config=fault_config,
    )

    trace = agent.run()

    status_ok = trace["status"] == expected_status

    return trace, status_ok


def main():
    print("Black Box Phase 2 dataset generation")

    base_task = sampleTask()
    failures = []

    for scenario in SCENARIOS:
        scenario_name = scenario["name"]
        fault_config = scenario["fault_config"]
        expected_status = scenario["expected_status"]

        trace, status_ok = run_scenario(
            base_task=base_task,
            fault_config=fault_config,
            expected_status=expected_status,
        )

        result_label = "PASS" if status_ok else "FAIL"

        print(
            f"[{result_label}] {scenario_name} | "
            f"status={trace['status']} | "
            f"expected={expected_status} | "
            f"trace_id={trace['trace_id']}"
        )

        if not status_ok:
            failures.append(scenario_name)

    if failures:
        raise SystemExit(
            f"Phase 2 validation failed for scenarios: {', '.join(failures)}"
        )

    print("All Phase 2 scenarios generated successfully.")


if __name__ == "__main__":
    main()