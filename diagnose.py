import json
import os

from diagnosis.loader import load_traces
from diagnosis.spec_engine import evaluate_trace


def main():
    print("Black Box Phase 3 failure detection")

    traces = load_traces()
    reports = []

    for trace in traces:
        report = evaluate_trace(trace)
        reports.append(report)

    os.makedirs("data/diagnosis", exist_ok=True)
    output_path = os.path.join("data/diagnosis", "failure_reports.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)

    any_failure = False

    for report in reports:
        ground_truth = report.get("ground_truth")
        if not isinstance(ground_truth, dict):
            ground_truth = {}

        failure_type = ground_truth.get("failure_type") or "none"
        ground_truth_root = ground_truth.get("root_cause_step_id")

        localization_ok = True

        if report["status"] == "failed" and ground_truth_root is not None:
            localization_ok = report["earliest_step_signal"] == ground_truth_root

        result_ok = report["detection_matches_status"] and localization_ok

        if not result_ok:
            any_failure = True

        result_label = "PASS" if result_ok else "FAIL"

        print(
            f"[{result_label}] {report['trace_id']} | "
            f"status={report['status']} | "
            f"ground_truth={failure_type} | "
            f"step_violations={report['total_step_violations']} | "
            f"final_violations={report['total_final_violations']} | "
            f"earliest_step={report['earliest_step_signal']}"
        )

    print(f"Saved reports to: {output_path}")

    if any_failure:
        raise SystemExit("Phase 3 detection validation failed.")

    print("Phase 3 detection completed successfully.")


if __name__ == "__main__":
    main()