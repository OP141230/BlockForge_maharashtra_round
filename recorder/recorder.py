"""BLACKBOX Flight Recorder SDK for Python AI Agents.

Captures granular step-by-step traces, state checkpoints, side-effect annotations,
and integrates automatically with the BLACKBOX Hybrid Diagnosis engine.
"""
from datetime import datetime, timezone
import json
import time
from typing import Any, Callable, Dict, List, Optional
from backend.database import SessionLocal, init_db
from backend.models import Checkpoint, DiagnosisResult, Run, Step
from backend.diagnosis.hybrid import HybridDiagnosisEngine


class FlightRecorder:
    """Flight recorder interface for AI agents."""

    def __init__(self, agent_name: str, scenario: str):
        self.agent_name = agent_name
        self.scenario = scenario
        self.current_run_id: Optional[str] = None
        self.step_counter = 0
        self.start_time: Optional[float] = None
        self.engine = HybridDiagnosisEngine()
        init_db()

    def start_run(
        self,
        task_description: str,
        metadata: Optional[Dict[str, Any]] = None,
        run_id_override: Optional[str] = None,
    ) -> str:
        """Initialize and persist a new flight recording session."""
        self.start_time = time.time()
        self.step_counter = 0
        self.current_run_id = run_id_override or f"run_{int(self.start_time * 1000)}"

        db = SessionLocal()
        run_obj = Run(
            id=self.current_run_id,
            agent_name=self.agent_name,
            scenario=self.scenario,
            task_description=task_description,
            status="RUNNING",
            started_at=datetime.now(timezone.utc),
            is_synthetic=False,
            metadata_json=json.dumps(metadata or {}),
        )
        db.add(run_obj)
        db.commit()
        db.close()
        return self.current_run_id

    def record_step(
        self,
        step_name: str,
        tool_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        duration_ms: float,
        status: str = "SUCCESS",
        error_text: Optional[str] = None,
        side_effect_flag: bool = False,
        dependencies: Optional[List[str]] = None,
        agent_state: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record an individual execution step and save checkpoint."""
        if not self.current_run_id:
            raise RuntimeError("Cannot record step without calling start_run first.")

        step_id = f"step_{self.current_run_id}_{self.step_counter}"
        db = SessionLocal()

        step_obj = Step(
            id=step_id,
            run_id=self.current_run_id,
            step_index=self.step_counter,
            step_name=step_name,
            tool_name=tool_name,
            input_data_json=json.dumps(input_data),
            output_data_json=json.dumps(output_data),
            duration_ms=duration_ms,
            status=status,
            error_text=error_text,
            side_effect_flag=side_effect_flag,
            dependencies_json=json.dumps(dependencies or []),
        )
        db.add(step_obj)

        # Create checkpoint
        cp_obj = Checkpoint(
            id=f"cp_{step_id}",
            run_id=self.current_run_id,
            step_id=step_id,
            step_index=self.step_counter,
            agent_state_json=json.dumps(agent_state or {"step": step_name}),
            memory_state_json=json.dumps(output_data),
            timestamp=datetime.now(timezone.utc),
        )
        db.add(cp_obj)

        db.commit()
        db.close()
        self.step_counter += 1
        return step_id

    def finish_run(self, status: str = "SUCCESS", error_message: Optional[str] = None):
        """Finalize the flight run and trigger automatic hybrid diagnosis."""
        if not self.current_run_id:
            return

        total_dur = (time.time() - (self.start_time or time.time())) * 1000.0
        db = SessionLocal()
        run_obj = db.query(Run).filter(Run.id == self.current_run_id).first()
        if run_obj:
            run_obj.status = status
            run_obj.completed_at = datetime.now(timezone.utc)
            run_obj.total_duration_ms = total_dur
            run_obj.error_message = error_message

            # Fetch steps for auto-diagnosis
            steps = db.query(Step).filter(Step.run_id == self.current_run_id).order_by(Step.step_index).all()
            step_dicts = [s.to_dict() for s in steps]
            diag = self.engine.diagnose_run(run_obj.to_dict(), step_dicts)

            diag_obj = DiagnosisResult(
                id=f"diag_{self.current_run_id}",
                run_id=self.current_run_id,
                suspect_step_id=diag["suspect_step_id"] or "",
                suspect_step_name=diag["suspect_step_name"],
                suspicion_score=diag["suspicion_score"],
                rule_score=diag["top_signals"]["rule_match"],
                anomaly_score=diag["top_signals"]["anomaly_signal"],
                ranker_score=diag["top_signals"]["learned_ranker"],
                dependency_score=diag["top_signals"]["dependency_impact"],
                historical_score=diag["top_signals"]["historical_evidence"],
                confidence_label=diag["confidence_label"],
                explanation_text=diag["explanation_text"],
                evidence_items_json=json.dumps(diag["top_evidence"]),
                breakdown_json=json.dumps(diag),
                created_at=datetime.now(timezone.utc),
            )
            db.add(diag_obj)
            db.commit()

        db.close()
