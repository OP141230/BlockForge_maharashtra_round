import os, sys, json, random
import pandas as pd
from copy import deepcopy

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path: sys.path.insert(0, project_root)

from diagnosis.loader import load_traces
from diagnosis.spec_engine import evaluate_trace
from ml.features import build_step_features
from train_ranker import train_ranker, evaluate_ranking

def load_split(path): return load_traces(path) if os.path.exists(path) else []

def main():
    print("Phase 9B: Rigorous ML Evaluation (Baselines, AUC, Ablations)...")
    
    seen_train = load_split("data/massive_traces/seen_train")
    seen_test = load_split("data/massive_traces/seen_test")
    unseen_fault = load_split("data/massive_traces/unseen_fault_test")
    unseen_task = load_split("data/massive_traces/unseen_task_test")
    
    # 1. Full Model Training & Evaluation
    print("Training full model...")
    weights, bias = train_ranker(seen_train)
    seen_metrics = evaluate_ranking(seen_test, weights, bias)
    unseen_fault_metrics = evaluate_ranking(unseen_fault, weights, bias)
    unseen_task_metrics = evaluate_ranking(unseen_task, weights, bias)
    
    # 2. Baselines
    def calc_baselines(traces):
        failed = [t for t in traces if t["status"] == "failed"]
        if not failed: return {}
        total = len(failed)
        random_hits = sum(1 for t in failed if random.randint(0, len(t["steps"])-1) == t["ground_truth"]["root_cause_step_id"])
        last_hits = sum(1 for t in failed if (len(t["steps"])-1) == t["ground_truth"]["root_cause_step_id"])
        first_hits = sum(1 for t in failed if 0 == t["ground_truth"]["root_cause_step_id"])
        return {
            "random_step": random_hits / total,
            "always_last_step": last_hits / total,
            "always_first_step": first_hits / total
        }

    # 3. Fail Detection AUC (Spec Engine)
    def calc_auc(traces):
        # Simple classifier: >0 step violations = failed
        tp = fp = tn = fn = 0
        for t in traces:
            report = evaluate_trace(t)
            predicted_failed = len(report.get("step_violations", [])) > 0
            actual_failed = t["status"] == "failed"
            if predicted_failed and actual_failed: tp += 1
            elif predicted_failed and not actual_failed: fp += 1
            elif not predicted_failed and actual_failed: fn += 1
            else: tn += 1
        # Simple AUC approximation for binary threshold
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        return (tpr + (1 - fpr)) / 2 # Approximation

    # 4. Learning Curve
    print("Generating Learning Curve...")
    learning_curve = []
    for size in [100, 300, 600, 1200, len(seen_train)]:
        subset = seen_train[:size]
        if len(subset) < 20: continue
        w, b = train_ranker(subset)
        m = evaluate_ranking(seen_test, w, b)
        learning_curve.append({"train_runs": size, "top1": m["top1"]})

    # 5. Ablation Study
    print("Running Ablation Study...")
    ablation = {}
    full_top1 = unseen_fault_metrics["top1"]
    ablation["full_model"] = full_top1
    
    # Drop specific features and retrain
    features_to_drop = ["is_earliest_violation", "violation_count", "has_error"]
    for feat in features_to_drop:
        # Monkey-patch build_step_features temporarily to zero out the feature
        original_build = build_step_features
        def patched_build(trace, report, step, max_steps):
            f = original_build(trace, report, step, max_steps)
            f[feat] = 0.0
            return f
        
        import ml.features
        ml.features.build_step_features = patched_build
        
        w, b = train_ranker(seen_train)
        m = evaluate_ranking(unseen_fault, w, b)
        ablation[f"no_{feat}"] = m["top1"]
        
        ml.features.build_step_features = original_build # Restore

    results = {
        "full_model": {
            "seen_test_top1": seen_metrics["top1"],
            "unseen_fault_top1": unseen_fault_metrics["top1"],
            "unseen_task_top1": unseen_task_metrics["top1"],
            "fail_detection_auc": calc_auc(seen_test + unseen_fault)
        },
        "baselines": calc_baselines(seen_test),
        "learning_curve": learning_curve,
        "ablation": ablation
    }
    
    os.makedirs("data/models", exist_ok=True)
    with open("data/models/rigorous_metrics.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Saved to data/models/rigorous_metrics.json")

if __name__ == "__main__":
    main()