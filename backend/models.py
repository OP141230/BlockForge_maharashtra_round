"""SQLAlchemy ORM data models for BLACKBOX: AI Agent Flight Recorder."""
from datetime import datetime
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from backend.database import Base


class Run(Base):
    __tablename__ = "runs"

    id = Column(String(64), primary_key=True, index=True)
    agent_name = Column(String(128), nullable=False, index=True)
    scenario = Column(String(256), nullable=False)
    task_description = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="SUCCESS", index=True)  # SUCCESS, FAILED, REPLAYED
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, default=datetime.utcnow)
    total_duration_ms = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    is_synthetic = Column(Boolean, default=True)
    metadata_json = Column(Text, default="{}")
    ground_truth_suspect_step = Column(String(64), nullable=True)
    ground_truth_fault_type = Column(String(128), nullable=True)

    steps = relationship("Step", back_populates="run", cascade="all, delete-orphan", order_by="Step.step_index")
    checkpoints = relationship("Checkpoint", back_populates="run", cascade="all, delete-orphan")
    diagnosis = relationship("DiagnosisResult", back_populates="run", uselist=False, cascade="all, delete-orphan")
    replays = relationship("ReplayResult", back_populates="run", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "scenario": self.scenario,
            "task_description": self.task_description,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms,
            "error_message": self.error_message,
            "is_synthetic": self.is_synthetic,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
            "ground_truth_suspect_step": self.ground_truth_suspect_step,
            "ground_truth_fault_type": self.ground_truth_fault_type,
            "step_count": len(self.steps) if self.steps else 0,
        }


class Step(Base):
    __tablename__ = "steps"

    id = Column(String(64), primary_key=True, index=True)
    run_id = Column(String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_index = Column(Integer, nullable=False)
    step_name = Column(String(128), nullable=False)
    tool_name = Column(String(128), nullable=False)
    input_data_json = Column(Text, default="{}")
    output_data_json = Column(Text, default="{}")
    duration_ms = Column(Float, default=0.0)
    status = Column(String(32), default="SUCCESS")  # SUCCESS, FAILED, INTERCEPTED
    error_text = Column(Text, nullable=True)
    side_effect_flag = Column(Boolean, default=False)
    is_root_suspect = Column(Boolean, default=False)
    is_downstream_impact = Column(Boolean, default=False)
    suspicion_score = Column(Float, default=0.0)
    diagnosis_breakdown_json = Column(Text, default="{}")
    dependencies_json = Column(Text, default="[]")

    run = relationship("Run", back_populates="steps")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "step_index": self.step_index,
            "step_name": self.step_name,
            "tool_name": self.tool_name,
            "input_data": json.loads(self.input_data_json) if self.input_data_json else {},
            "output_data": json.loads(self.output_data_json) if self.output_data_json else {},
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_text": self.error_text,
            "side_effect_flag": self.side_effect_flag,
            "is_root_suspect": self.is_root_suspect,
            "is_downstream_impact": self.is_downstream_impact,
            "suspicion_score": self.suspicion_score,
            "diagnosis_breakdown": json.loads(self.diagnosis_breakdown_json) if self.diagnosis_breakdown_json else {},
            "dependencies": json.loads(self.dependencies_json) if self.dependencies_json else [],
        }


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id = Column(String(64), primary_key=True, index=True)
    run_id = Column(String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id = Column(String(64), nullable=False)
    step_index = Column(Integer, nullable=False)
    agent_state_json = Column(Text, default="{}")
    memory_state_json = Column(Text, default="{}")
    timestamp = Column(DateTime, default=datetime.utcnow)

    run = relationship("Run", back_populates="checkpoints")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "step_index": self.step_index,
            "agent_state": json.loads(self.agent_state_json) if self.agent_state_json else {},
            "memory_state": json.loads(self.memory_state_json) if self.memory_state_json else {},
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class DiagnosisResult(Base):
    __tablename__ = "diagnosis_results"

    id = Column(String(64), primary_key=True, index=True)
    run_id = Column(String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    suspect_step_id = Column(String(64), nullable=False)
    suspect_step_name = Column(String(128), nullable=False)
    suspicion_score = Column(Float, default=0.0)
    rule_score = Column(Float, default=0.0)
    anomaly_score = Column(Float, default=0.0)
    ranker_score = Column(Float, default=0.0)
    dependency_score = Column(Float, default=0.0)
    historical_score = Column(Float, default=0.0)
    confidence_label = Column(String(64), default="HIGH")
    explanation_text = Column(Text, nullable=False)
    evidence_items_json = Column(Text, default="[]")
    breakdown_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("Run", back_populates="diagnosis")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "suspect_step_id": self.suspect_step_id,
            "suspect_step_name": self.suspect_step_name,
            "suspicion_score": round(self.suspicion_score, 1),
            "signals": {
                "rule_match": round(self.rule_score, 2),
                "anomaly_signal": round(self.anomaly_score, 2),
                "learned_ranker": round(self.ranker_score, 2),
                "dependency_impact": round(self.dependency_score, 2),
                "historical_evidence": round(self.historical_score, 2),
            },
            "weights": {
                "rule_match": 0.30,
                "anomaly_signal": 0.20,
                "learned_ranker": 0.20,
                "dependency_impact": 0.15,
                "historical_evidence": 0.15,
            },
            "confidence_label": self.confidence_label,
            "explanation_text": self.explanation_text,
            "evidence_items": json.loads(self.evidence_items_json) if self.evidence_items_json else [],
            "breakdown": json.loads(self.breakdown_json) if self.breakdown_json else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ReplayResult(Base):
    __tablename__ = "replay_results"

    id = Column(String(64), primary_key=True, index=True)
    original_run_id = Column(String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    intervention_step_id = Column(String(64), nullable=False)
    modified_input_json = Column(Text, default="{}")
    replay_status = Column(String(32), default="SUCCESS")
    replayed_steps_json = Column(Text, default="[]")
    suppressed_side_effects_json = Column(Text, default="[]")
    diff_summary_json = Column(Text, default="{}")
    experimental_evidence_notes = Column(Text, default="Experimental evidence only - does not constitute formal proof of causality.")
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("Run", back_populates="replays")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "original_run_id": self.original_run_id,
            "intervention_step_id": self.intervention_step_id,
            "modified_input": json.loads(self.modified_input_json) if self.modified_input_json else {},
            "replay_status": self.replay_status,
            "replayed_steps": json.loads(self.replayed_steps_json) if self.replayed_steps_json else [],
            "suppressed_side_effects": json.loads(self.suppressed_side_effects_json) if self.suppressed_side_effects_json else [],
            "diff_summary": json.loads(self.diff_summary_json) if self.diff_summary_json else {},
            "experimental_evidence_notes": self.experimental_evidence_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# ITINERARY LAB MODELS
# ─────────────────────────────────────────────────────────────────────────────

class Itinerary(Base):
    """Stored travel itinerary submitted to Itinerary Lab."""
    __tablename__ = "itineraries"

    id            = Column(String(64), primary_key=True, index=True)
    name          = Column(String(256), nullable=False)
    destination   = Column(String(256), nullable=False)
    start_date    = Column(String(32), nullable=False)   # ISO date string
    end_date      = Column(String(32), nullable=False)
    travelers     = Column(Integer, default=1)
    budget        = Column(Float, default=0.0)
    currency      = Column(String(8), default="EUR")
    preferences   = Column(Text, default="[]")            # JSON list of strings
    items_json    = Column(Text, default="[]")            # JSON list of ItineraryItem dicts
    linked_run_id = Column(String(64), nullable=True)     # links to existing BLACKBOX run
    created_at    = Column(DateTime, default=datetime.utcnow)
    is_demo       = Column(Boolean, default=False)

    validation_runs = relationship(
        "ItineraryValidationRun",
        back_populates="itinerary",
        cascade="all, delete-orphan",
        order_by="ItineraryValidationRun.created_at",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "destination": self.destination,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "travelers": self.travelers,
            "budget": self.budget,
            "currency": self.currency,
            "preferences": json.loads(self.preferences) if self.preferences else [],
            "items": json.loads(self.items_json) if self.items_json else [],
            "linked_run_id": self.linked_run_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_demo": self.is_demo,
        }


class ItineraryValidationRun(Base):
    """One execution of the validation engine against an itinerary."""
    __tablename__ = "itinerary_validation_runs"

    id              = Column(String(64), primary_key=True, index=True)
    itinerary_id    = Column(String(64), ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False, index=True)
    findings_json   = Column(Text, default="[]")   # list of Finding dicts
    summary_json    = Column(Text, default="{}")   # {passed, critical, high, medium, low, optimization}
    patched_items_json = Column(Text, nullable=True)  # items after applied fixes (None = original)
    created_at      = Column(DateTime, default=datetime.utcnow)
    label           = Column(String(64), default="BEFORE")  # BEFORE | AFTER

    itinerary = relationship("Itinerary", back_populates="validation_runs")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "itinerary_id": self.itinerary_id,
            "findings": json.loads(self.findings_json) if self.findings_json else [],
            "summary": json.loads(self.summary_json) if self.summary_json else {},
            "patched_items": json.loads(self.patched_items_json) if self.patched_items_json else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "label": self.label,
        }


class EvaluationBenchmark(Base):
    __tablename__ = "evaluation_benchmarks"

    id = Column(String(64), primary_key=True, index=True)
    benchmark_name = Column(String(128), nullable=False)
    total_cases = Column(Integer, default=0)
    top1_accuracy = Column(Float, default=0.0)
    top3_accuracy = Column(Float, default=0.0)
    mrr = Column(Float, default=0.0)
    baselines_json = Column(Text, default="{}")
    detailed_results_json = Column(Text, default="[]")
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "benchmark_name": self.benchmark_name,
            "total_cases": self.total_cases,
            "top1_accuracy": round(self.top1_accuracy, 3),
            "top3_accuracy": round(self.top3_accuracy, 3),
            "mrr": round(self.mrr, 3),
            "baselines": json.loads(self.baselines_json) if self.baselines_json else {},
            "detailed_results": json.loads(self.detailed_results_json) if self.detailed_results_json else [],
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
        }
