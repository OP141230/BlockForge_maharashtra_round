"""Hybrid Diagnosis Engine for BLACKBOX.

Combines Rule Engine, Anomaly Signals, Learned Ranker, Dependency Graph,
and Historical Evidence into a unified, transparent Suspicion Score.
"""
from typing import Any, Dict, List, Optional
from backend.diagnosis.rules import RuleEngine
from backend.diagnosis.anomaly import AnomalyEngine
from backend.diagnosis.dependencies import DependencyEngine
from backend.diagnosis.historical import HistoricalEngine
from backend.diagnosis.ranker import LearnedRanker


class HybridDiagnosisEngine:
    """Ensemble orchestrator for multi-modal fault isolation in AI agent flight traces."""

    WEIGHT_RULE = 0.30
    WEIGHT_ANOMALY = 0.20
    WEIGHT_RANKER = 0.20
    WEIGHT_DEPENDENCY = 0.15
    WEIGHT_HISTORICAL = 0.15

    def __init__(self):
        self.rule_engine = RuleEngine()
        self.anomaly_engine = AnomalyEngine()
        self.dependency_engine = DependencyEngine()
        self.historical_engine = HistoricalEngine()
        self.ranker = LearnedRanker()

    def diagnose_run(self, run_dict: Dict[str, Any], steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run complete hybrid diagnosis across all steps in an execution trace.
        """
        if not steps:
            return {
                "suspect_step_id": None,
                "suspect_step_name": "None",
                "suspicion_score": 0.0,
                "step_diagnoses": [],
                "explanation_text": "No steps recorded in execution run.",
            }

        run_context = run_dict.get("metadata", {}) or {}
        step_diagnoses: List[Dict[str, Any]] = []

        for step in steps:
            # 1. Rule Match
            rule_score, rule_evidence = self.rule_engine.evaluate_step(step, run_context)

            # 2. Anomaly Signal
            anomaly_score, anomaly_evidence = self.anomaly_engine.evaluate_step(step)

            # 3. Historical Evidence
            historical_score, historical_evidence = self.historical_engine.evaluate_step(step)

            # 4. Dependency Impact
            dep_score, dep_evidence = self.dependency_engine.evaluate_step(step, steps)

            # 5. Learned Ranker
            ranker_score, ranker_evidence = self.ranker.evaluate_step(
                step,
                rule_score,
                anomaly_evidence,
                dep_evidence,
                historical_score,
                steps,
            )

            # Calculate composite Suspicion Score (0.0 to 100.0)
            composite_0_1 = (
                self.WEIGHT_RULE * rule_score
                + self.WEIGHT_ANOMALY * anomaly_score
                + self.WEIGHT_RANKER * ranker_score
                + self.WEIGHT_DEPENDENCY * dep_score
                + self.WEIGHT_HISTORICAL * historical_score
            )
            suspicion_score = round(composite_0_1 * 100.0, 1)

            step_diagnoses.append({
                "step_id": step["id"],
                "step_index": step["step_index"],
                "step_name": step["step_name"],
                "tool_name": step["tool_name"],
                "suspicion_score": suspicion_score,
                "signals": {
                    "rule_match": round(rule_score, 3),
                    "anomaly_signal": round(anomaly_score, 3),
                    "learned_ranker": round(ranker_score, 3),
                    "dependency_impact": round(dep_score, 3),
                    "historical_evidence": round(historical_score, 3),
                },
                "evidence": {
                    "rules": rule_evidence,
                    "anomalies": anomaly_evidence,
                    "dependencies": dep_evidence,
                    "historical_matches": historical_evidence,
                    "ranker_breakdown": ranker_evidence,
                },
            })

        # Rank steps by Suspicion Score descending
        ranked = sorted(step_diagnoses, key=lambda x: x["suspicion_score"], reverse=True)
        top_suspect = ranked[0]

        # Classify root cause vs downstream impact
        suspect_step_id = top_suspect["step_id"]
        suspect_step_name = top_suspect["step_name"]
        max_score = top_suspect["suspicion_score"]

        # Build explainability summary
        rule_items = top_suspect["evidence"]["rules"]
        hist_items = top_suspect["evidence"]["historical_matches"]
        dep_info = top_suspect["evidence"]["dependencies"]

        explanation_parts = []
        if rule_items:
            explanation_parts.append(f"Deterministic rule violation: {rule_items[0].get('name')} ({rule_items[0].get('evidence')})")
        if hist_items:
            explanation_parts.append(f"Historical pattern match: {hist_items[0].get('title')} with {hist_items[0].get('similarity') * 100:.0f}% similarity")
        if dep_info.get("downstream_failures", 0) > 0:
            explanation_parts.append(f"Graph cascade: Caused {dep_info.get('downstream_failures')} downstream failure(s) in cascade path: {' -> '.join(dep_info.get('cascade_path', []))}")

        if not explanation_parts:
            explanation_text = f"Step '{suspect_step_name}' flagged with elevated suspicion score {max_score:.1f} based on anomaly signals."
        else:
            explanation_text = " | ".join(explanation_parts)

        confidence = "CRITICAL" if max_score >= 80 else "HIGH" if max_score >= 60 else "MEDIUM"

        return {
            "suspect_step_id": suspect_step_id,
            "suspect_step_name": suspect_step_name,
            "suspicion_score": max_score,
            "confidence_label": confidence,
            "explanation_text": explanation_text,
            "weights": {
                "rule_match": self.WEIGHT_RULE,
                "anomaly_signal": self.WEIGHT_ANOMALY,
                "learned_ranker": self.WEIGHT_RANKER,
                "dependency_impact": self.WEIGHT_DEPENDENCY,
                "historical_evidence": self.WEIGHT_HISTORICAL,
            },
            "top_signals": top_suspect["signals"],
            "top_evidence": top_suspect["evidence"],
            "ranked_steps": ranked,
        }
