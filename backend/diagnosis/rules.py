"""Deterministic Rule Match Engine for BLACKBOX.

Evaluates concrete constraints, arithmetic integrity, schema validations,
and error indicators without probabilistic ambiguity.
"""
from typing import Any, Dict, List, Tuple


class RuleEngine:
    """Evaluates deterministic rule matches against trace steps."""

    @staticmethod
    def evaluate_step(step_dict: Dict[str, Any], run_context: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Evaluate deterministic rules on a single step.
        Returns: (rule_score: 0.0 - 1.0, matched_rules: List[Dict])
        """
        matched_rules: List[Dict[str, Any]] = []
        tool_name = step_dict.get("tool_name", "")
        step_name = step_dict.get("step_name", "")
        input_data = step_dict.get("input_data", {}) or {}
        output_data = step_dict.get("output_data", {}) or {}
        error_text = step_dict.get("error_text") or ""
        status = step_dict.get("status", "SUCCESS")

        # 1. Direct Step Failure / Exception Rule
        if status == "FAILED" or error_text:
            matched_rules.append({
                "rule_id": "RULE_EXPLICIT_FAILURE",
                "name": "Explicit Step Error/Exception",
                "type": "Deterministic Rule",
                "severity": "HIGH",
                "weight": 0.85,
                "evidence": f"Step terminated with status '{status}' and error: {error_text or 'Unhandled failure'}",
            })

        # 2. Arithmetic Duplication & Budget Inconsistency Rule
        if "budget" in step_name.lower() or "calc" in step_name.lower() or "budget" in tool_name.lower():
            # Check for duplicate items in cost breakdown
            items = output_data.get("breakdown", []) or output_data.get("items", [])
            total = output_data.get("total_cost") or output_data.get("total") or output_data.get("calculated_budget")
            budget_limit = run_context.get("budget") or input_data.get("budget_limit") or input_data.get("budget")

            # Check if same cost item appears twice or total != sum
            if isinstance(items, list) and len(items) > 1:
                item_names = [item.get("category") or item.get("name") for item in items if isinstance(item, dict)]
                if len(item_names) != len(set(item_names)):
                    matched_rules.append({
                        "rule_id": "RULE_ARITHMETIC_DUPLICATION",
                        "name": "Duplicate Item in Cost Accumulation",
                        "type": "Deterministic Rule",
                        "severity": "CRITICAL",
                        "weight": 0.95,
                        "evidence": f"Identified duplicate category entries in item list: {item_names}. Double-counted accommodation/expense detected.",
                    })

            # Check if total exceeds budget
            if total is not None and budget_limit is not None:
                try:
                    if float(total) > float(budget_limit):
                        matched_rules.append({
                            "rule_id": "RULE_BUDGET_OVERFLOW",
                            "name": "Budget Constraint Exceeded",
                            "type": "Deterministic Rule",
                            "severity": "CRITICAL",
                            "weight": 0.92,
                            "evidence": f"Calculated total {total} exceeds configured task budget limit {budget_limit}.",
                        })
                except (ValueError, TypeError):
                    pass

        # 3. Schema & Type Integrity Violations
        if isinstance(output_data, dict):
            # Missing critical fields or type errors
            for k, v in output_data.items():
                if k in ("price", "cost", "total", "amount") and isinstance(v, str):
                    try:
                        float(v)
                    except ValueError:
                        matched_rules.append({
                            "rule_id": "RULE_TYPE_MISMATCH",
                            "name": "Invalid Numeric Schema Type",
                            "type": "Deterministic Rule",
                            "severity": "MEDIUM",
                            "weight": 0.70,
                            "evidence": f"Field '{k}' contains non-numeric string value: '{v}'",
                        })

        # 4. Empty Result / Null Payload on Essential Lookup
        if "search" in tool_name.lower() or "lookup" in tool_name.lower():
            results = output_data.get("results") or output_data.get("flights") or output_data.get("hotels")
            if results == [] or output_data == {}:
                matched_rules.append({
                    "rule_id": "RULE_EMPTY_LOOKUP_RESULT",
                    "name": "Empty Result on Required Lookup",
                    "type": "Deterministic Rule",
                    "severity": "MEDIUM",
                    "weight": 0.60,
                    "evidence": f"Tool '{tool_name}' returned an empty result set, risking downstream null reference.",
                })

        # 5. Temporal / Chronological Logic Violation
        checkin = output_data.get("checkin_time") or input_data.get("checkin_time")
        arrival = run_context.get("flight_arrival_time") or output_data.get("arrival_time")
        if checkin and arrival:
            try:
                # Compare HH:MM format
                if arrival > checkin and "hotel" in tool_name.lower():
                    matched_rules.append({
                        "rule_id": "RULE_CHRONO_INCONSISTENCY",
                        "name": "Temporal Constraint Conflict",
                        "type": "Deterministic Rule",
                        "severity": "MEDIUM",
                        "weight": 0.65,
                        "evidence": f"Arrival time ({arrival}) is scheduled after hotel check-in deadline ({checkin}).",
                    })
            except Exception:
                pass

        if not matched_rules:
            return 0.0, []

        # Aggregate rule score based on highest severity rule and count
        max_weight = max(r["weight"] for r in matched_rules)
        bonus = min(0.15, (len(matched_rules) - 1) * 0.05)
        final_score = min(1.0, max_weight + bonus)

        return round(final_score, 3), matched_rules
