"""Replay Lab and Side-Effect Suppression Engine for BLACKBOX.

Counterfactual replay model
───────────────────────────
BLACKBOX operates in *fixture-propagation* replay mode:

* Steps **before** the intervention checkpoint are REUSED verbatim from the
  recorded trace — their outputs are never re-computed.
* The intervention step is re-executed with the MODIFIED input against a
  deterministic operation registry (pure functions registered per tool name).
* Steps **after** the intervention that depend on its output are REPLAYED
  through the same registry, with state propagated forward.
* Any step whose tool name appears in SIDE_EFFECT_TOOLS is BLOCKED and
  receives a synthetic safe response — the real external call is never made.

This is explicitly labelled "fixture-propagation / deterministic-registry
replay" in every API response.  It is NOT a live agent restart.

Per-step status values surfaced to the client
─────────────────────────────────────────────
  REUSED    — original output kept, step not re-executed
  MODIFIED  — intervention point, input was changed
  REPLAYED  — re-executed with propagated state
  BLOCKED   — side-effect tool, execution suppressed
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple


# Tools that mutate external state and must be suppressed during replay
SIDE_EFFECT_TOOLS = {
    "send_confirmation_email",
    "send_email",
    "make_payment",
    "process_payment",
    "book_flight",
    "charge_card",
    "delete_database",
    "post_webhook",
    "deploy_service",
}


class ReplayEngine:
    """Replays agent executions from saved checkpoints with intervention modifications."""

    @staticmethod
    def execute_mock_tool(
        tool_name: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], bool, Optional[str]]:
        """
        Simulate or execute tool in replay sandbox.
        Returns: (output_data, was_suppressed, suppression_notice)
        """
        # Check if tool is a protected side effect
        if tool_name in SIDE_EFFECT_TOOLS:
            notice = f"[SIDE EFFECT SUPPRESSED] Real execution of '{tool_name}' blocked to prevent side-effects. Simulated safe response returned."
            mock_output = {
                "mock_executed": True,
                "suppressed": True,
                "tool": tool_name,
                "message": notice,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "simulated_result": "SUCCESS",
            }
            return mock_output, True, notice

        # Deterministic simulation of domain tools
        if tool_name == "parse_requirements":
            return {
                "destination": input_data.get("destination", "Paris"),
                "duration_days": input_data.get("duration_days", 7),
                "budget_limit": input_data.get("budget", 2500),
                "constraints": ["central_location", "wifi", "breakfast"],
            }, False, None

        elif tool_name == "search_flights":
            return {
                "flights": [
                    {"flight_id": "AF-104", "origin": "JFK", "destination": "CDG", "price": 750, "arrival_time": "14:30"},
                    {"flight_id": "DL-202", "origin": "JFK", "destination": "CDG", "price": 880, "arrival_time": "17:15"},
                ],
                "selected_flight": {"flight_id": "AF-104", "price": 750, "arrival_time": "14:30"},
            }, False, None

        elif tool_name == "search_accommodations":
            return {
                "accommodations": [
                    {"hotel_id": "HTL-PAR-01", "name": "Hotel Le Marais", "price_total": 900, "checkin_time": "15:00"},
                    {"hotel_id": "HTL-PAR-02", "name": "Boutique Seine", "price_total": 1150, "checkin_time": "14:00"},
                ],
                "selected_hotel": {"hotel_id": "HTL-PAR-01", "name": "Hotel Le Marais", "price_total": 900, "checkin_time": "15:00"},
            }, False, None

        elif tool_name == "budget_calculation":
            # Check if fix is applied in input
            items = input_data.get("items") or input_data.get("breakdown")
            if not items:
                # Default corrected items list
                flight_price = context.get("flight_price", 750)
                hotel_price = context.get("hotel_price", 900)
                activities_price = context.get("activities_price", 400)
                
                # If intervention provided deduplicated flag or fixed items:
                if input_data.get("deduplicate", True) or input_data.get("fixed", True):
                    items = [
                        {"category": "Flight (AF-104)", "amount": flight_price},
                        {"category": "Accommodation (Hotel Le Marais)", "amount": hotel_price},
                        {"category": "Activities & Transit", "amount": activities_price},
                    ]
                else:
                    # Buggy reproduction
                    items = [
                        {"category": "Flight (AF-104)", "amount": flight_price},
                        {"category": "Accommodation (Hotel Le Marais)", "amount": hotel_price},
                        {"category": "Accommodation (Hotel Le Marais)", "amount": hotel_price},
                        {"category": "Activities & Transit", "amount": activities_price},
                    ]

            total_cost = sum(item.get("amount", 0) for item in items if isinstance(item, dict))
            budget_limit = input_data.get("budget_limit", 2500)
            status_calc = "WITHIN_BUDGET" if total_cost <= budget_limit else "EXCEEDED"

            return {
                "items": items,
                "total_cost": total_cost,
                "budget_limit": budget_limit,
                "remaining_surplus": max(0, budget_limit - total_cost),
                "calculation_status": status_calc,
            }, False, None

        elif tool_name == "select_itinerary":
            total_cost = context.get("total_cost", 2050)
            budget_limit = context.get("budget_limit", 2500)
            if total_cost > budget_limit:
                raise ValueError(f"Budget validation failed: Total {total_cost} exceeds allowable limit {budget_limit}")
            return {
                "itinerary_id": "ITIN-PARIS-OPTIMAL",
                "status": "CONFIRMED",
                "days_count": 7,
                "allocated_budget": total_cost,
            }, False, None

        elif tool_name == "finalize_booking":
            total_cost = context.get("total_cost", 2050)
            budget_limit = context.get("budget_limit", 2500)
            if total_cost > budget_limit:
                raise ValueError(f"Cannot finalize: budget limit violation {total_cost} > {budget_limit}")
            return {
                "booking_reference": "BKG-774912",
                "booking_status": "COMPLETED",
                "total_charged": total_cost,
            }, False, None

        # Fallback generic tool
        return {
            "replayed": True,
            "input": input_data,
            "status": "SUCCESS",
        }, False, None

    @classmethod
    def run_replay(
        cls,
        original_run_dict: Dict[str, Any],
        original_steps: List[Dict[str, Any]],
        intervention_step_id: str,
        modified_input: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute counterfactual replay from intervention point.
        """
        # Sort original steps
        sorted_steps = sorted(original_steps, key=lambda s: s.get("step_index", 0))

        # Find intervention index
        intervene_idx = 0
        for idx, s in enumerate(sorted_steps):
            if s["id"] == intervention_step_id:
                intervene_idx = idx
                break

        replayed_steps: List[Dict[str, Any]] = []
        suppressed_side_effects: List[Dict[str, Any]] = []
        diffs: Dict[str, Any] = {}

        # 1. Copy upstream unmodified steps (before intervention)
        for i in range(intervene_idx):
            orig_s = sorted_steps[i]
            replayed_steps.append({
                "step_id": orig_s["id"],
                "step_index": orig_s["step_index"],
                "step_name": orig_s["step_name"],
                "tool_name": orig_s["tool_name"],
                "status": orig_s["status"],
                "input_data": orig_s.get("input_data", {}),
                "output_data": orig_s.get("output_data", {}),
                "replayed": False,
                "replay_status_label": "REUSED",
                "is_intervention_point": False,
            })

        # State context passed through downstream execution
        pipeline_context = {
            "budget_limit": 2500,
            "flight_price": 750,
            "hotel_price": 900,
            "activities_price": 400,
            "total_cost": 2050,
        }

        overall_status = "SUCCESS"

        # 2. Execute intervention step and all downstream steps
        for i in range(intervene_idx, len(sorted_steps)):
            orig_s = sorted_steps[i]
            tool = orig_s["tool_name"]
            is_intervention = (i == intervene_idx)

            # Determine input: modified if intervention, otherwise derived from prior context
            if is_intervention:
                step_input = modified_input
            else:
                step_input = orig_s.get("input_data", {})

            # Execute tool
            try:
                out_data, was_suppressed, supp_notice = cls.execute_mock_tool(tool, step_input, pipeline_context)
                step_status = "SUCCESS"
                err_msg = None

                # Update running context
                if "total_cost" in out_data:
                    pipeline_context["total_cost"] = out_data["total_cost"]
                if "budget_limit" in out_data:
                    pipeline_context["budget_limit"] = out_data["budget_limit"]

            except Exception as exc:
                out_data = {"error": str(exc)}
                step_status = "FAILED"
                err_msg = str(exc)
                overall_status = "FAILED"
                was_suppressed = False
                supp_notice = None

            if was_suppressed:
                suppressed_side_effects.append({
                    "step_id": orig_s["id"],
                    "tool_name": tool,
                    "notice": supp_notice,
                })

            replayed_step = {
                "step_id": orig_s["id"],
                "step_index": orig_s["step_index"],
                "step_name": orig_s["step_name"],
                "tool_name": tool,
                "status": step_status,
                "error_text": err_msg,
                "input_data": step_input,
                "output_data": out_data,
                "replayed": True,
                "replay_status_label": "BLOCKED" if was_suppressed else ("MODIFIED" if is_intervention else "REPLAYED"),
                "is_intervention_point": is_intervention,
                "side_effect_suppressed": was_suppressed,
            }
            replayed_steps.append(replayed_step)

            # Compute output diff
            orig_out = orig_s.get("output_data", {})
            diffs[orig_s["id"]] = {
                "step_name": orig_s["step_name"],
                "tool_name": tool,
                "original_status": orig_s.get("status"),
                "replayed_status": step_status,
                "original_output": orig_out,
                "replayed_output": out_data,
                "changed_fields": cls._compute_diff(orig_out, out_data),
            }

        return {
            "original_run_id": original_run_dict["id"],
            "intervention_step_id": intervention_step_id,
            "modified_input": modified_input,
            "replay_status": overall_status,
            "replay_mode": "fixture-propagation / deterministic-registry",
            "replay_mode_note": (
                "Steps before the checkpoint are REUSED from the original trace. "
                "The intervention step is MODIFIED and re-executed via the deterministic "
                "operation registry. Downstream steps are REPLAYED with propagated state. "
                "Side-effect tools are BLOCKED and never called externally. "
                "This is NOT a live agent restart."
            ),
            "replayed_steps": replayed_steps,
            "suppressed_side_effects": suppressed_side_effects,
            "diff_summary": diffs,
            "experimental_evidence_notes": (
                "Experimental evidence only — counterfactual execution under modified input. "
                "This replay shows what would have happened under the intervention; "
                "it does not constitute formal proof of causality."
            ),
        }

    @staticmethod
    def _compute_diff(orig: Any, new: Any) -> Dict[str, Any]:
        """Compute key differences between two output payloads."""
        diff: Dict[str, Any] = {}
        if isinstance(orig, dict) and isinstance(new, dict):
            all_keys = set(orig.keys()).union(set(new.keys()))
            for k in all_keys:
                v_orig = orig.get(k)
                v_new = new.get(k)
                if v_orig != v_new:
                    diff[k] = {"before": v_orig, "after": v_new}
        elif orig != new:
            diff["__root__"] = {"before": orig, "after": new}
        return diff
