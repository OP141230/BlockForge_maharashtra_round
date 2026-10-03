"""Generalisation checks for the step ranker.

Three tests, each against the baseline "blame the earliest step the spec engine flagged":

1. Held-out splits (seen / unseen faults / unseen routes), trained on seen_train only.
2. Leave-one-fault-family-out over all 10 families: train on 9, test on the 10th.
3. Held-out step position: train with one step never being the root cause, test on it.
   (The check that exposed Repo 1's 14% on step 3 under the same protocol.)
"""
import json
import os
import sys
from collections import defaultdict

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import train_ranker as tr
from diagnosis.loader import load_traces
from diagnosis.spec_engine import evaluate_trace

SPLITS = ("seen_train", "seen_test", "unseen_fault_test", "unseen_task_test")


def load_all():
    out = {}
    for s in SPLITS:
        p = f"data/massive_traces/{s}"
        out[s] = load_traces(p) if os.path.exists(p) else []
    return out


def failed(traces):
    return [t for t in traces if t["status"] == "failed"]


def baseline_top1(traces):
    f = failed(traces)
    if not f:
        return None
    hits = sum(evaluate_trace(t).get("earliest_step_signal") == t["ground_truth"]["root_cause_step_id"] for t in f)
    return hits / len(f)


def ranker_top1(train, test):
    w, b = tr.train_ranker(train)
    m = tr.evaluate_ranking(test, w, b)
    return m["top1"] if m["failed_traces"] else None


def pct(x):
    return None if x is None else round(x, 3)


def main():
    d = load_all()
    train = d["seen_train"]
    out = {"held_out_splits": {}, "leave_one_family_out": {}, "held_out_step": {}}

    for name in SPLITS[1:]:
        out["held_out_splits"][name] = {
            "n_failed": len(failed(d[name])),
            "ranker_top1": pct(ranker_top1(train, d[name])),
            "earliest_violation_baseline_top1": pct(baseline_top1(d[name])),
        }

    pool = [t for s in SPLITS for t in d[s]]
    fams = sorted({t["ground_truth"]["failure_type"] for t in failed(pool)})
    for fam in fams:
        test = [t for t in pool if t["ground_truth"]["failure_type"] == fam]
        rest = [t for t in pool if t["ground_truth"]["failure_type"] != fam]
        out["leave_one_family_out"][fam] = {
            "n_failed": len(failed(test)),
            "ranker_top1": pct(ranker_top1(rest, test)),
            "earliest_violation_baseline_top1": pct(baseline_top1(test)),
        }

    roots = sorted({t["ground_truth"]["root_cause_step_id"] for t in failed(pool)})
    for step in roots:
        is_root = lambda t: t["status"] == "failed" and t["ground_truth"]["root_cause_step_id"] == step
        test = [t for t in pool if is_root(t)]
        rest = [t for t in pool if not is_root(t)]
        out["held_out_step"][str(step)] = {
            "n_failed": len(test),
            "ranker_top1": pct(ranker_top1(rest, test)),
            "earliest_violation_baseline_top1": pct(baseline_top1(test)),
        }

    def avg(group, key):
        rows = [v for v in out[group].values() if v[key] is not None]
        tot = sum(v["n_failed"] for v in rows)
        return sum(v[key] * v["n_failed"] for v in rows) / tot if tot else None

    out["summary"] = {
        g: {"ranker": pct(avg(g, "ranker_top1")), "baseline": pct(avg(g, "earliest_violation_baseline_top1"))}
        for g in ("leave_one_family_out", "held_out_step")
    }
    os.makedirs("data/models", exist_ok=True)
    with open("data/models/ranker_generalization.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
