import os
import sys

# Make project root importable when running:
# python advanced/run_advanced_replay.py
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json

from diagnosis.loader import load_traces
from advanced.counterfactual_search import search_fix


def main():
    print("Black Box Phase 7A: Generic Counterfactual Search")

    traces = load_traces("data/traces")

    failed_traces = [
        trace
        for trace in traces
        if trace.get("status") == "failed"
    ]

    if not failed_traces:
        raise SystemExit("No failed traces found in data/traces.")

    os.makedirs(os.path.join("data", "advanced"), exist_ok=True)

    reports = []
    success_count = 0

    for trace in failed_traces:
        report = search_fix(
            trace=trace,
            traces_dir="data/traces",
            base_dir=os.path.join("data", "advanced", "replays"),
            max_attempts=12,
        )

        reports.append(report)

        if report.get("fixed"):
            success_count += 1

        predicted_root = report.get("predicted_root") or {}
        successful_attempt = report.get("successful_attempt") or {}
        successful_intervention = successful_attempt.get("intervention") or {}

        print(
            f"Trace: {report.get('trace_id')} | "
            f"Fixed: {report.get('fixed')} | "
            f"Attempts: {len(report.get('attempts', []))} | "
            f"Predicted Root: {predicted_root.get('name')} | "
            f"Fix: {successful_intervention.get('intervention_type')} @ "
            f"{successful_intervention.get('target_step_name')}"
        )

    output_path = os.path.join("data", "advanced", "replay_reports.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)

    print(f"Saved advanced replay reports to: {output_path}")
    print(f"Fix rate: {success_count}/{len(failed_traces)}")

    if success_count != len(failed_traces):
        raise SystemExit("Phase 7A validation failed: not all failed traces were fixed.")

    print("Phase 7A completed successfully.")


if __name__ == "__main__":
    main()