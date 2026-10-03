import os
import sys
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from diagnosis.loader import load_traces
from diagnosis.spec_engine import evaluate_trace
from advanced.counterfactual_search import (
    load_ranker,
    score_steps,
    build_candidate_step_names,
    propose_interventions,
)
from replay.engine import load_checkpoint_before_step, run_replay

def generate_attempts_for_trace(trace, report, model, max_attempts=10):
    scored_steps = score_steps(trace, report, model)
    candidate_step_names = build_candidate_step_names(trace, report, scored_steps, max_candidates=10)
    interventions = propose_interventions(trace, candidate_step_names)
    
    trace_id = trace.get("trace_id")
    trace_dir = os.path.join("data/traces", str(trace_id))
    
    attempts = []
    
    for intervention in interventions[:max_attempts]:
        target_step_name = intervention.get("target_step_name")
        target_step_id = intervention.get("target_step_id")
        
        try:
            initial_state = load_checkpoint_before_step(trace_dir, int(target_step_id))
            replay_trace = run_replay(
                task=trace.get("task", {}),
                initial_state=initial_state,
                start_step_name=target_step_name,
                patches=intervention.get("patch", {}),
                base_dir="data/contrastive/replays"
            )
            
            replay_status = replay_trace.get("status")
            final_validation = replay_trace.get("final_state", {}).get("final_validation", {})
            fixed = replay_status == "success" and bool(final_validation.get("success"))
            
            attempts.append({
                "trace_id": trace_id,
                "intervention": intervention,
                "replay_trace_id": replay_trace.get("trace_id"),
                "fixed": fixed,
                "replay_status": replay_status
            })
            
        except Exception as e:
            attempts.append({
                "trace_id": trace_id,
                "intervention": intervention,
                "error": str(e),
                "fixed": False
            })
            
    return attempts

def main():
    print("Black Box Phase 7C: Contrastive Intervention Dataset Generation")
    
    traces = load_traces("data/traces")
    failed_traces = [t for t in traces if t.get("status") == "failed"]
    
    if not failed_traces:
        print("No failed traces found.")
        return
        
    os.makedirs("data/contrastive", exist_ok=True)
    
    model = load_ranker()
    all_attempts = []
    
    for trace in failed_traces:
        print(f"Generating attempts for {trace['trace_id']}...")
        report = evaluate_trace(trace)
        attempts = generate_attempts_for_trace(trace, report, model, max_attempts=10)
        all_attempts.extend(attempts)
        
    output_path = "data/contrastive/intervention_attempts.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_attempts, f, indent=2)
        
    print(f"Generated {len(all_attempts)} intervention attempts.")
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()