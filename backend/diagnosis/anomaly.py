"""Statistical Anomaly Signal Engine for BLACKBOX.

Calculates standardized Z-scores and deviations for step duration,
payload size, and output parameters compared to reference baselines.
"""
import math
from typing import Any, Dict, List, Optional, Tuple


# Historical baselines for synthetic agent tools (mean, std_dev)
TOOL_HISTORICAL_BASELINES: Dict[str, Dict[str, Tuple[float, float]]] = {
    "parse_requirements": {
        "duration_ms": (42.0, 10.5),
        "payload_chars": (180.0, 40.0),
    },
    "search_flights": {
        "duration_ms": (310.0, 65.0),
        "payload_chars": (650.0, 110.0),
    },
    "search_accommodations": {
        "duration_ms": (290.0, 55.0),
        "payload_chars": (580.0, 95.0),
    },
    "budget_calculation": {
        "duration_ms": (65.0, 15.0),
        "payload_chars": (220.0, 35.0),
        "cost_multiplier": (1.0, 0.15),
    },
    "select_itinerary": {
        "duration_ms": (145.0, 30.0),
        "payload_chars": (420.0, 75.0),
    },
    "finalize_booking": {
        "duration_ms": (210.0, 45.0),
        "payload_chars": (310.0, 50.0),
    },
    "send_confirmation_email": {
        "duration_ms": (180.0, 35.0),
        "payload_chars": (260.0, 40.0),
    },
    "database_query": {
        "duration_ms": (85.0, 20.0),
        "payload_chars": (350.0, 80.0),
    },
    "deploy_service": {
        "duration_ms": (850.0, 150.0),
        "payload_chars": (480.0, 90.0),
    },
}


class AnomalyEngine:
    """Computes statistical z-score anomalies against historical operational distributions."""

    @classmethod
    def evaluate_step(
        cls,
        step_dict: Dict[str, Any],
        historical_overrides: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Evaluate statistical anomalies for a step.
        Returns: (anomaly_score: 0.0 - 1.0, anomaly_evidence: List[Dict])
        """
        tool_name = step_dict.get("tool_name", "")
        duration_ms = float(step_dict.get("duration_ms", 0.0))
        output_str = str(step_dict.get("output_data", {}))
        payload_chars = float(len(output_str))

        baselines = TOOL_HISTORICAL_BASELINES.get(tool_name, {
            "duration_ms": (150.0, 80.0),
            "payload_chars": (300.0, 150.0),
        })

        evidence: List[Dict[str, Any]] = []
        z_scores: List[float] = []

        # 1. Duration Z-Score
        dur_mean, dur_std = baselines.get("duration_ms", (150.0, 80.0))
        dur_z = abs(duration_ms - dur_mean) / max(dur_std, 1.0)
        if dur_z >= 1.75:
            severity = "HIGH" if dur_z >= 3.0 else "MEDIUM"
            evidence.append({
                "signal": "Duration Deviation",
                "metric": "duration_ms",
                "observed": round(duration_ms, 1),
                "expected_mean": dur_mean,
                "z_score": round(dur_z, 2),
                "severity": severity,
                "details": f"Execution time {duration_ms:.1f}ms is {dur_z:.2f} standard deviations from tool mean ({dur_mean:.1f}ms).",
            })
            z_scores.append(dur_z)

        # 2. Output Payload Size Z-Score
        size_mean, size_std = baselines.get("payload_chars", (300.0, 150.0))
        size_z = abs(payload_chars - size_mean) / max(size_std, 1.0)
        if size_z >= 1.75:
            severity = "HIGH" if size_z >= 3.0 else "MEDIUM"
            evidence.append({
                "signal": "Payload Size Deviation",
                "metric": "payload_length",
                "observed": payload_chars,
                "expected_mean": size_mean,
                "z_score": round(size_z, 2),
                "severity": severity,
                "details": f"Output size {payload_chars} chars deviates by {size_z:.2f}σ from baseline mean ({size_mean:.1f} chars).",
            })
            z_scores.append(size_z)

        # 3. Domain Specific Numeric Shift Anomaly
        output_data = step_dict.get("output_data", {}) or {}
        if "total_cost" in output_data or "calculated_budget" in output_data:
            cost = float(output_data.get("total_cost") or output_data.get("calculated_budget") or 0.0)
            # Typically costs around 1800 - 2400 for 7-day budget scenario
            expected_cost_mean, expected_cost_std = 2100.0, 300.0
            cost_z = abs(cost - expected_cost_mean) / expected_cost_std
            if cost_z >= 2.0:
                evidence.append({
                    "signal": "Value Distribution Outlier",
                    "metric": "total_cost",
                    "observed": cost,
                    "expected_mean": expected_cost_mean,
                    "z_score": round(cost_z, 2),
                    "severity": "HIGH",
                    "details": f"Calculated value ${cost:.2f} is an outlier ({cost_z:.2f}σ above normal historical distributions).",
                })
                z_scores.append(cost_z)

        if not z_scores:
            return 0.0, []

        # Convert max z-score into bounded [0, 1] score using a calibrated sigmoid
        max_z = max(z_scores)
        # Shifted sigmoid: z=2.0 -> 0.50, z=3.0 -> 0.73, z=4.0 -> 0.88, z=5.0 -> 0.95
        score = 1.0 / (1.0 + math.exp(-1.0 * (max_z - 2.0)))
        return round(score, 3), evidence
