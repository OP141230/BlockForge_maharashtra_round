"""
Persistent-defect benchmark.

Unlike the injected faults (which are switched off during replay, so a plain
replay "fixes" them), a persistent defect lives in the agent's own step logic
and survives replay. A plain replay therefore fails, and the search has to find
the right step AND the right intervention.

Reports localization (ranker vs. earliest-violation baseline), overall fix rate,
fix rate on the first attempt, and average attempts.
"""
import json
import os
import random
import shutil
import sys
from copy import deepcopy

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agent.agent import TravelAgent
from agent.task import sampleTask
from advanced.counterfactual_search import load_ranker, search_fix
from diagnosis.loader import load_traces
from ml.localization import evaluate_localization, format_localization
from recorder.recorder import TraceRecorder

SEED = 7
PER_DEFECT = 5
BUDGETS = [5000, 5500, 6000, 6500, 7000]
CHECKIN_TIMES = ["13:30", "14:00", "15:00"]
BASE = os.path.join("data", "persistent_traces", "test")

DEFECTS = [
    {"defect": "select_reads_unfiltered_list", "root_cause_step_id": 5,
     "description": "select_cheapest_flight has a logic bug: it reads the unfiltered flight list and picks the most expensive one."},
    {"defect": "hotel_filter_inverted", "root_cause_step_id": 7,
     "description": "filter_hotels_by_checkin has an inverted comparison and keeps early check-ins."},
    {"defect": "search_swaps_route", "root_cause_step_id": 3,
     "description": "search_flights passes origin and destination the wrong way round."},
    {"defect": "hotel_search_stale_date", "root_cause_step_id": 6,
     "description": "search_hotels queries the day before the trip."},
    {"defect": "budget_filter_inverted", "root_cause_step_id": 4,
     "description": "filter_flights_by_budget keeps flights at or above the budget."},
]


def _task(rng):
    task = deepcopy(sampleTask())
    task["budget"] = rng.choice(BUDGETS)
    task["hotel_checkin_after"] = rng.choice(CHECKIN_TIMES)
    task["instruction"] = (
        f"Book the cheapest flight from Mumbai to Delhi tomorrow under {task['budget']} "
        f"and book a hotel with check-in after {task['hotel_checkin_after']}."
    )
    return task


def generate():
    if os.path.exists(BASE):
        shutil.rmtree(BASE)
    os.makedirs(BASE)
    rng = random.Random(SEED)
    for spec in DEFECTS:
        for _ in range(PER_DEFECT):
            # A defect only counts if it really breaks the run for this task, so
            # resample the task until it does (e.g. a budget no flight exceeds).
            for _attempt in range(20):
                task = _task(rng)
                recorder = TraceRecorder(task=task, base_dir=BASE)
                recorder.trace["ground_truth"] = {
                    "failure_type": spec["defect"],
                    "root_cause_step_id": spec["root_cause_step_id"],
                    "notes": spec["description"],
                }
                trace = TravelAgent(task=task, recorder=recorder, defects=[spec["defect"]]).run()
                if trace["status"] == "failed":
                    break
                shutil.rmtree(os.path.join(BASE, trace["trace_id"]), ignore_errors=True)
            else:
                raise SystemExit(f"Defect {spec['defect']} never caused a failure in 20 tries")


def main():
    print("Black Box: persistent-defect benchmark")
    generate()
    traces = [t for t in load_traces(BASE) if t.get("status") == "failed"]
    ranker = load_ranker()

    loc = evaluate_localization(traces, ranker.get("weights", {}), ranker.get("bias", 0.0))
    print(format_localization(loc, "Localization on persistent defects"))

    reports, plain_replay_fixed = [], 0
    for trace in traces:
        report = search_fix(
            trace=trace,
            traces_dir=BASE,
            base_dir=os.path.join("data", "persistent_evaluation", "replays"),
            max_attempts=20,
        )
        reports.append(report)
        for attempt in report.get("attempts", []):
            iv = attempt.get("intervention", {})
            if iv.get("intervention_type") == "replay_no_patch" and attempt.get("fixed"):
                plain_replay_fixed += 1

    fixed = sum(1 for r in reports if r.get("fixed"))
    first = sum(1 for r in reports if r.get("fixed") and len(r["attempts"]) == 1)
    avg_attempts = sum(len(r["attempts"]) for r in reports) / max(len(reports), 1)
    winners = {}
    for r in reports:
        iv = (r.get("successful_attempt") or {}).get("intervention", {})
        key = f"{iv.get('intervention_type')}@{iv.get('target_step_name')}"
        winners[key] = winners.get(key, 0) + 1

    print(f"Fixed by search: {fixed}/{len(reports)}")
    print(f"Fixed on first attempt: {first}/{len(reports)}")
    print(f"Fixed by plain replay (replay_no_patch): {plain_replay_fixed}/{len(reports)}")
    print(f"Average attempts: {avg_attempts:.2f}")

    # Does ordering proposals by the intervention model actually save attempts?
    ordered = [
        search_fix(
            trace=t,
            traces_dir=BASE,
            base_dir=os.path.join("data", "persistent_evaluation", "replays_ordered"),
            max_attempts=20,
            model_ordering=True,
        )
        for t in traces
    ]
    o_fixed = sum(1 for r in ordered if r.get("fixed"))
    o_avg = sum(len(r["attempts"]) for r in ordered) / max(len(ordered), 1)
    print(f"With model_ordering=True: fixed {o_fixed}/{len(ordered)}, average attempts {o_avg:.2f} (default {avg_attempts:.2f})")
    print(f"Winning interventions: {winners}")

    out = os.path.join("data", "persistent_evaluation")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"fixed": fixed, "total": len(reports), "fixed_first_attempt": first,
                   "fixed_by_plain_replay": plain_replay_fixed, "avg_attempts": avg_attempts,
                   "winning_interventions": winners, "localization": loc}, f, indent=2)
    with open(os.path.join(out, "reports.json"), "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2)


if __name__ == "__main__":
    main()
