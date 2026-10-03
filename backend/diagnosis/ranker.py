"""Learned ML Ranker Engine for BLACKBOX.

Evaluates trace culpability using calibrated logistic regression coefficients
trained on labeled synthetic failure datasets.
"""
import math
from typing import Any, Dict, List, Tuple


class LearnedRanker:
    """Calibrated Logistic Regression ranker on multi-dimensional trace features."""

    FEATURE_NAMES = [
        "rule_violation_flag",
        "duration_zscore",
        "payload_size_zscore",
        "error_proximity",
        "upstream_failure_cascade",
        "historical_similarity",
    ]

    # Trained weights derived from synthetic failure feature regression
    COEFFICIENTS = [2.45, 0.85, 0.92, 1.35, 1.80, 1.65]
    BIAS = -2.10

    def extract_features(
        self,
        step_dict: Dict[str, Any],
        rule_score: float,
        anomaly_evidence: List[Dict[str, Any]],
        dependency_evidence: Dict[str, Any],
        historical_score: float,
        all_steps: List[Dict[str, Any]],
    ) -> List[float]:
        """Construct normalized feature vector for a step."""
        # 1. Rule violation flag
        f_rule = 1.0 if rule_score > 0.4 else 0.0

        # 2. Duration Z-score
        dur_z = 0.0
        for ev in anomaly_evidence:
            if ev.get("metric") == "duration_ms":
                dur_z = float(ev.get("z_score", 0.0))

        # 3. Payload size Z-score
        size_z = 0.0
        for ev in anomaly_evidence:
            if ev.get("metric") == "payload_length":
                size_z = float(ev.get("z_score", 0.0))

        # 4. Proximity to first failure
        step_idx = step_dict.get("step_index", 0)
        failed_indices = [s.get("step_index", 0) for s in all_steps if s.get("status") == "FAILED"]
        first_fail_idx = min(failed_indices) if failed_indices else len(all_steps)
        dist = abs(step_idx - first_fail_idx)
        f_prox = 1.0 / (1.0 + dist)

        # 5. Upstream failure cascade
        f_cascade = 1.0 if dependency_evidence.get("downstream_failures", 0) > 0 else 0.0

        # 6. Historical similarity
        f_hist = float(historical_score)

        return [f_rule, dur_z, size_z, f_prox, f_cascade, f_hist]

    def evaluate_step(
        self,
        step_dict: Dict[str, Any],
        rule_score: float,
        anomaly_evidence: List[Dict[str, Any]],
        dependency_evidence: Dict[str, Any],
        historical_score: float,
        all_steps: List[Dict[str, Any]],
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Evaluate step culpability via calibrated logistic ranker.
        Returns: (ranker_score: 0.0 - 1.0, details: Dict)
        """
        feats = self.extract_features(
            step_dict,
            rule_score,
            anomaly_evidence,
            dependency_evidence,
            historical_score,
            all_steps,
        )

        logit = self.BIAS + sum(w * x for w, x in zip(self.COEFFICIENTS, feats))
        # Sigmoid activation
        prob = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, logit))))

        feature_contributions = {}
        for name, val, coef in zip(self.FEATURE_NAMES, feats, self.COEFFICIENTS):
            feature_contributions[name] = {
                "feature_value": round(float(val), 2),
                "model_coefficient": round(float(coef), 2),
                "impact": round(float(val * coef), 3),
            }

        return round(prob, 3), {
            "model_type": "Logistic Regression Ranker",
            "predicted_score": round(prob, 3),
            "feature_contributions": feature_contributions,
        }
