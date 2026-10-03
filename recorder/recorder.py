import json
import os
from datetime import datetime
from typing import Any, Dict, Optional
import uuid


class TraceRecorder:

    def __init__(self, task: Dict[str, Any], base_dir: str = "data/traces") -> None:

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.trace_id = f"trace_{timestamp}_{uuid.uuid4().hex[:8]}"
        self.trace_dir = os.path.join(base_dir, self.trace_id)
        self.checkpoint_dir = os.path.join(self.trace_dir, "checkpoints")

        os.makedirs(self.checkpoint_dir, exist_ok=True)

        self.trace: Dict[str, Any] = {
            "trace_id": self.trace_id,
            "task": task,
            "status": "running",
            "steps": [],
            "final_state": None,
            "ground_truth": {
                "failure_type": None,
                "root_cause_step_id": None,
                "notes": "Phase 1: no injected fault",
            },
        }

    def save_checkpoint(self, state: Dict[str, Any], step_id: int, name: str) -> str:
        
        payload = {
            "trace_id": self.trace_id,
            "step_id": step_id,
            "step_name": name,
            "state": state,
        }

        filename = f"step_{step_id:03d}.json"
        path = os.path.join(self.checkpoint_dir, filename)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        return path

    def record_step(
        self,
        step_id: int,
        name: str,
        step_type: str,
        input_payload: Dict[str, Any],
        output: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        confidence: float,
        latency_ms: float,
        error: Optional[str] = None,
    ) -> None:
        event = {
            "step_id": step_id,
            "name": name,
            "type": step_type,
            "input": input_payload,
            "output": output,
            "state_before": state_before,
            "state_after": state_after,
            "confidence": confidence,
            "latency_ms": latency_ms,
            "error": error,
        }

        self.trace["steps"].append(event)

        self.save_checkpoint(
            state=state_after,
            step_id=step_id,
            name=name,
        )

    def finish(self, final_state: Dict[str, Any], status: str) -> Dict[str, Any]:
        self.trace["final_state"] = final_state
        self.trace["status"] = status

        trace_path = os.path.join(self.trace_dir, "trace.json")

        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(self.trace, f, indent=2, ensure_ascii=False)

        return self.trace