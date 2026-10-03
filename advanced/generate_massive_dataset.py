import os
import sys
import random
import shutil
from copy import deepcopy

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path: sys.path.insert(0, project_root)

from agent.task import sampleTask
from agent.agent import TravelAgent
from recorder.recorder import TraceRecorder

# Import all fault configs from our existing unseen generator logic
from advanced.generate_unseen_dataset import UNSEEN_SCENARIOS

SEEN_SCENARIOS = [
    {"name": "success", "fault_config": None, "expected_status": "success"},
    {"name": "wrong_date", "fault_config": {"fault_type": "wrong_date", "root_cause_step_id": 3}, "expected_status": "failed"},
    {"name": "wrong_destination", "fault_config": {"fault_type": "wrong_destination", "root_cause_step_id": 3}, "expected_status": "failed"},
    {"name": "budget_violation", "fault_config": {"fault_type": "budget_violation", "root_cause_step_id": 5}, "expected_status": "failed"},
    {"name": "ignored_empty_result", "fault_config": {"fault_type": "ignored_empty_result", "root_cause_step_id": 5}, "expected_status": "failed"},
    {"name": "state_overwrite", "fault_config": {"fault_type": "state_overwrite", "root_cause_step_id": 9}, "expected_status": "failed"},
    {"name": "hotel_checkin_violation", "fault_config": {"fault_type": "hotel_checkin_violation", "root_cause_step_id": 8}, "expected_status": "failed"},
]

SEEN_ROUTES = [("Mumbai", "Delhi"), ("Bangalore", "Chennai"), ("Kolkata", "Pune")]
UNSEEN_ROUTES = [("Hyderabad", "Jaipur"), ("Ahmedabad", "Lucknow")]

def generate_task(rng, origin, dest):
    task = deepcopy(sampleTask())
    task["origin"] = origin
    task["destination"] = dest
    task["budget"] = rng.choice([5000, 6000, 7000, 8000])
    task["hotel_checkin_after"] = rng.choice(["13:00", "14:00", "15:00"])
    task["instruction"] = f"Book {origin} to {dest} under {task['budget']}."
    return task

def run_one(base_dir, task, fault_config):
    recorder = TraceRecorder(task=task, base_dir=base_dir)
    if fault_config:
        recorder.trace["ground_truth"] = {"failure_type": fault_config["fault_type"], "root_cause_step_id": fault_config["root_cause_step_id"]}
    else:
        recorder.trace["ground_truth"] = {"failure_type": None, "root_cause_step_id": None}
    agent = TravelAgent(task=task, recorder=recorder, fault_config=fault_config)
    return agent.run()

def _discard(split_dir, trace):
    """Remove a mislabelled trace (and its checkpoints) from disk."""
    tid = trace.get("trace_id")
    for name in os.listdir(split_dir):
        if tid and tid in name:
            path = os.path.join(split_dir, name)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)


def main():
    print("Phase 9A: Generating labelled trace dataset (count is printed per split)...")
    rng = random.Random(42)
    
    splits = {
        "seen_train": (SEEN_ROUTES, SEEN_SCENARIOS, 15),
        "seen_test": (SEEN_ROUTES, SEEN_SCENARIOS, 5),
        "unseen_fault_test": (SEEN_ROUTES, UNSEEN_SCENARIOS, 5),
        "unseen_task_test": (UNSEEN_ROUTES, SEEN_SCENARIOS + UNSEEN_SCENARIOS, 5)
    }
    
    base_root = "data/massive_traces"
    if os.path.exists(base_root): shutil.rmtree(base_root)
    
    for split_name, (routes, scenarios, count) in splits.items():
        split_dir = os.path.join(base_root, split_name)
        os.makedirs(split_dir, exist_ok=True)
        generated = 0
        skipped = 0
        for origin, dest in routes:
            for scenario in scenarios:
                for _ in range(count):
                    # Resample the task until the observed status matches the label,
                    # so every committed label is truthful (e.g. a 5000 budget can make
                    # a clean run fail legitimately). Give up after a few tries.
                    for _attempt in range(10):
                        task = generate_task(rng, origin, dest)
                        trace = run_one(split_dir, task, scenario.get("fault_config"))
                        if trace["status"] == scenario["expected_status"]:
                            generated += 1
                            break
                        _discard(split_dir, trace)
                        skipped += 1
        print(f"  {split_name}: {generated} traces kept, {skipped} mismatched runs discarded.")

if __name__ == "__main__":
    main()