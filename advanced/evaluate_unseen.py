import os
import sys
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from diagnosis.loader import load_traces
from advanced.counterfactual_search import search_fix, load_ranker
from ml.localization import evaluate_localization, format_localization

def main():
    print("Black Box Phase 7E: Unseen Fault Evaluation")

    traces = load_traces("data/unseen_traces/test")

    failed_traces = [
        trace
        for trace in traces
        if trace.get("status") == "failed"
    ]

    if not failed_traces:
        raise SystemExit("No failed traces found in data/unseen_traces/test.")

    os.makedirs(os.path.join("data", "unseen_evaluation"), exist_ok=True)

    reports = []
    success_count = 0

    for trace in failed_traces:
        report = search_fix(
            trace=trace,
            traces_dir="data/unseen_traces/test",
            base_dir=os.path.join("data", "unseen_evaluation", "replays"),
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

    output_path = os.path.join("data", "unseen_evaluation", "evaluation_reports.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)

    print(f"Saved unseen evaluation reports to: {output_path}")
    print(f"Fix rate on unseen faults: {success_count}/{len(failed_traces)}")

    first_try = sum(1 for r in reports if r.get("fixed") and len(r.get("attempts", [])) == 1)
    print(f"Fixed on first attempt: {first_try}/{len(failed_traces)}")

    ranker = load_ranker()
    loc = evaluate_localization(failed_traces, ranker.get("weights", {}), ranker.get("bias", 0.0))
    print(format_localization(loc, "Zero-shot localization on unseen families"))

    summary_path = os.path.join("data", "unseen_evaluation", "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "fixed": success_count,
                "total": len(failed_traces),
                "fixed_first_attempt": first_try,
                "localization": loc,
            },
            f,
            indent=2,
        )

    if success_count != len(failed_traces):
        print("WARNING: Not all unseen faults were fixed. This is expected for truly novel failures.")
    else:
        print("Phase 7E completed successfully. All unseen faults were fixed!")

if __name__ == "__main__":
    main()