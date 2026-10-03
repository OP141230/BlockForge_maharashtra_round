import os
import sys

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from diagnosis.loader import load_traces
from diagnosis.spec_engine import evaluate_trace
from diagnosis.provenance import build_provenance_graph, get_backward_slice

def main():
    print("Black Box Phase 7B: Provenance & Causal Slicing\n")
    
    traces = load_traces("data/traces")
    failed_traces = [t for t in traces if t.get("status") == "failed"]
    
    if not failed_traces:
        print("No failed traces found.")
        return

    for trace in failed_traces:
        report = evaluate_trace(trace)
        graph = build_provenance_graph(trace, report)
        
        print(f"--- Trace: {trace['trace_id']} ---")
        print(f"Graph Size: {len(graph['nodes'])} Nodes | {len(graph['edges'])} Edges")
        
        final_violations = report.get("final_violations", [])
        if not final_violations:
            print("No final violations detected.\n")
            continue
            
        for v in final_violations:
            v_name = v.get("violation")
            target_id = f"violation:{v_name}"
            
            # Get the causal steps
            causal_steps = get_backward_slice(graph, target_id)
            
            # Sort them chronologically based on their actual step_id in the trace
            step_order = {s['name']: s['step_id'] for s in trace.get('steps', [])}
            causal_steps.sort(key=lambda n: step_order.get(n, 999))
            
            print(f"🚨 Violation: {v_name}")
            print(f"   <- Causal Path: {' ➔ '.join(causal_steps)}\n")

if __name__ == "__main__":
    main()