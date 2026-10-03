import json
import os
from typing import Any, Dict

from diagnosis.loader import load_traces
from diagnosis.spec_engine import evaluate_trace
from ml.features import build_step_features, _safe_dict
from replay.engine import load_checkpoint_before_step, run_replay, get_replay_config


def load_ranker(model_path: str = "data/models/ranker.json") -> Dict[str, Any]:
    with open(model_path, "r", encoding="utf-8") as f:
        return json.load(f)

def score_step(weights: Dict[str, float], bias: float, features: Dict[str, float]) -> float:
    score = bias
    for k, v in features.items():
        score += weights.get(k, 0.0) * float(v)
    return score

def main():
    print("Black Box Phase 5: Checkpointed Replay and Counterfactual Validation\n")
    
    # Load original failed traces from Phase 2
    traces = load_traces("data/traces")
    failed_traces = [t for t in traces if t.get("status") == "failed"]
    
    if not failed_traces:
        print("No failed traces found in data/traces.")
        return

    model = load_ranker()
    weights = model["weights"]
    bias = model["bias"]
    
    os.makedirs("data/replays", exist_ok=True)
    
    success_count = 0
    
    for trace in failed_traces:
        trace_id = trace["trace_id"]
        ground_truth = _safe_dict(trace.get("ground_truth"))
        failure_type = ground_truth.get("failure_type")
        root_step_id = ground_truth.get("root_cause_step_id")
        
        print(f"--- Trace: {trace_id} | Failure: {failure_type} | True Root Step: {root_step_id} ---")
        
        # 1. Diagnose using the ML ranker
        report = evaluate_trace(trace)
        steps = trace.get("steps", [])
        max_steps = len(steps)
        
        scored_steps = []
        for step in steps:
            step = _safe_dict(step)
            features = build_step_features(trace, report, step, max_steps)
            score = score_step(weights, bias, features)
            scored_steps.append({
                "step_id": step.get("step_id"),
                "name": step.get("name"),
                "score": score
            })
            
        scored_steps.sort(key=lambda x: -x["score"])
        predicted_step_id = scored_steps[0]["step_id"]
        predicted_step_name = scored_steps[0]["name"]
        
        print(f"ML Ranker predicted root cause: Step {predicted_step_id} ({predicted_step_name})")
        
        if predicted_step_id != root_step_id:
            print(f"WARNING: ML prediction mismatch. Skipping replay.\n")
            continue
            
        # 2. Get replay config
        replay_config = get_replay_config(failure_type, trace["task"])
        start_step_name = replay_config["start_step_name"]
        patches = replay_config["patches"]
        
        # Find the step_id for start_step_name to load the correct checkpoint
        start_step_id = None
        for s in steps:
            if s.get("name") == start_step_name:
                start_step_id = s.get("step_id")
                break
                
        # 3. Load checkpoint BEFORE the start step
        trace_dir = os.path.join("data/traces", trace_id)
        try:
            initial_state = load_checkpoint_before_step(trace_dir, start_step_id)
        except FileNotFoundError as e:
            print(f"ERROR: {e}\n")
            continue
            
        print(f"Replaying from Step {start_step_id} ({start_step_name}) with patches...")
        
        # 4. Run replay
        replay_trace = run_replay(
            task=trace["task"],
            initial_state=initial_state,
            start_step_name=start_step_name,
            patches=patches,
            base_dir="data/replays"
        )
        
        # 5. Validate
        replay_status = replay_trace.get("status")
        final_validation = replay_trace.get("final_state", {}).get("final_validation", {})
        
        if replay_status == "success" and final_validation.get("success"):
            print(f"SUCCESS: Counterfactual replay fixed the failure!\n")
            success_count += 1
        else:
            print(f"FAILED: Replay did not fix the issue. Status: {replay_status}, Violations: {final_validation.get('violations')}\n")
            
    print(f"--- Phase 5 Summary ---")
    print(f"Total failed traces tested: {len(failed_traces)}")
    print(f"Successfully fixed via replay: {success_count}")
    print(f"Fix validation rate: {success_count / len(failed_traces):.2%}")

if __name__ == "__main__":
    main()