"""Evaluation Benchmark Engine for BLACKBOX.

Measures diagnosis accuracy (Top-1, Top-3, MRR) of BLACKBOX Hybrid Ranker
against standard baselines across labeled ground-truth failure scenarios.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from backend.diagnosis.hybrid import HybridDiagnosisEngine


class BenchmarkRunner:
    """Runs evaluation benchmark suites over labeled agent failure datasets."""

    @staticmethod
    def get_benchmark_cases() -> List[Dict[str, Any]]:
        """Return canonical labeled test cases with known ground truth root causes."""
        return [
            # 1. TravelPlanner Arithmetic Duplicate
            {
                "case_id": "TC_TRAVEL_01",
                "agent": "TravelPlanner",
                "name": "Paris 7-Day Budget Duplication",
                "ground_truth_suspect": "budget_calculation",
                "fault_category": "Arithmetic Duplication",
                "steps": [
                    {"id": "s1", "step_index": 0, "step_name": "Requirements Parsing", "tool_name": "parse_requirements", "status": "SUCCESS", "input_data": {}, "output_data": {"budget": 2500}, "duration_ms": 40},
                    {"id": "s2", "step_index": 1, "step_name": "Flight Search", "tool_name": "search_flights", "status": "SUCCESS", "input_data": {}, "output_data": {"price": 750}, "duration_ms": 310},
                    {"id": "s3", "step_index": 2, "step_name": "Accommodation Search", "tool_name": "search_accommodations", "status": "SUCCESS", "input_data": {}, "output_data": {"price": 900}, "duration_ms": 290},
                    {"id": "s4", "step_index": 3, "step_name": "Budget Aggregation", "tool_name": "budget_calculation", "status": "SUCCESS", "input_data": {"budget": 2500}, "output_data": {"total_cost": 2950, "breakdown": [{"category": "hotel", "amount": 900}, {"category": "hotel", "amount": 900}, {"category": "flight", "amount": 750}, {"category": "activities", "amount": 400}]}, "duration_ms": 65},
                    {"id": "s5", "step_index": 4, "step_name": "Itinerary Selection", "tool_name": "select_itinerary", "status": "FAILED", "error_text": "BudgetExceededError: $2950 > $2500", "input_data": {}, "output_data": {}, "duration_ms": 140},
                    {"id": "s6", "step_index": 5, "step_name": "Booking Finalization", "tool_name": "finalize_booking", "status": "FAILED", "error_text": "Downstream cancelled", "input_data": {}, "output_data": {}, "duration_ms": 20},
                ],
            },
            # 2. TravelPlanner Temporal Conflict
            {
                "case_id": "TC_TRAVEL_02",
                "agent": "TravelPlanner",
                "name": "Arrival / Checkin Time Inversion",
                "ground_truth_suspect": "search_accommodations",
                "fault_category": "Constraint Inversion",
                "steps": [
                    {"id": "s1", "step_index": 0, "step_name": "Requirements Parsing", "tool_name": "parse_requirements", "status": "SUCCESS", "input_data": {}, "output_data": {"budget": 3000}, "duration_ms": 45},
                    {"id": "s2", "step_index": 1, "step_name": "Flight Search", "tool_name": "search_flights", "status": "SUCCESS", "input_data": {}, "output_data": {"arrival_time": "19:30"}, "duration_ms": 320},
                    {"id": "s3", "step_index": 2, "step_name": "Accommodation Search", "tool_name": "search_accommodations", "status": "SUCCESS", "input_data": {}, "output_data": {"checkin_time": "14:00", "arrival_time": "19:30"}, "duration_ms": 280},
                    {"id": "s4", "step_index": 3, "step_name": "Itinerary Verification", "tool_name": "select_itinerary", "status": "FAILED", "error_text": "ScheduleConflict: Hotel checkin closed before flight arrival", "input_data": {}, "output_data": {}, "duration_ms": 110},
                ],
            },
            # 3. Empty Flight Lookup
            {
                "case_id": "TC_TRAVEL_03",
                "agent": "TravelPlanner",
                "name": "Empty Flight Query Crash",
                "ground_truth_suspect": "search_flights",
                "fault_category": "Empty API Result",
                "steps": [
                    {"id": "s1", "step_index": 0, "step_name": "Requirements Parsing", "tool_name": "parse_requirements", "status": "SUCCESS", "input_data": {}, "output_data": {}, "duration_ms": 38},
                    {"id": "s2", "step_index": 1, "step_name": "Flight Search", "tool_name": "search_flights", "status": "SUCCESS", "input_data": {}, "output_data": {"flights": []}, "duration_ms": 290},
                    {"id": "s3", "step_index": 2, "step_name": "Flight Selection", "tool_name": "select_itinerary", "status": "FAILED", "error_text": "IndexError: list index out of range on flights[0]", "input_data": {}, "output_data": {}, "duration_ms": 85},
                ],
            },
            # 4. Customer Support Schema Drift
            {
                "case_id": "TC_SUPPORT_01",
                "agent": "CustomerSupport",
                "name": "Database Schema Key Mismatch",
                "ground_truth_suspect": "database_query",
                "fault_category": "Schema Drift",
                "steps": [
                    {"id": "s1", "step_index": 0, "step_name": "Receive Ticket", "tool_name": "parse_requirements", "status": "SUCCESS", "input_data": {}, "output_data": {}, "duration_ms": 35},
                    {"id": "s2", "step_index": 1, "step_name": "Query Customer DB", "tool_name": "database_query", "status": "SUCCESS", "input_data": {}, "output_data": {"user_id": 9921, "account_status": "ACTIVE"}, "duration_ms": 90},
                    {"id": "s3", "step_index": 2, "step_name": "Generate Response", "tool_name": "select_itinerary", "status": "FAILED", "error_text": "KeyError: 'customer_guid' not found in db result", "input_data": {}, "output_data": {}, "duration_ms": 60},
                ],
            },
            # 5. DevOps Deployer Port Conflict
            {
                "case_id": "TC_DEVOPS_01",
                "agent": "DevOpsDeployer",
                "name": "Service Port Binding Collision",
                "ground_truth_suspect": "deploy_service",
                "fault_category": "Infrastructure Collision",
                "steps": [
                    {"id": "s1", "step_index": 0, "step_name": "Build Container", "tool_name": "parse_requirements", "status": "SUCCESS", "input_data": {}, "output_data": {}, "duration_ms": 120},
                    {"id": "s2", "step_index": 1, "step_name": "Deploy Container Service", "tool_name": "deploy_service", "status": "FAILED", "error_text": "BindException: Address already in use 0.0.0.0:8080", "input_data": {}, "output_data": {}, "duration_ms": 1150},
                    {"id": "s3", "step_index": 2, "step_name": "Verify Healthcheck", "tool_name": "select_itinerary", "status": "FAILED", "error_text": "ConnectionRefused: Health probe timed out", "input_data": {}, "output_data": {}, "duration_ms": 500},
                ],
            },
            # 6. Trading Bot Price Slip
            {
                "case_id": "TC_TRADING_01",
                "agent": "TradingBot",
                "name": "Stale Quote Calculation Error",
                "ground_truth_suspect": "budget_calculation",
                "fault_category": "Stale Data Anomaly",
                "steps": [
                    {"id": "s1", "step_index": 0, "step_name": "Fetch Market Feed", "tool_name": "parse_requirements", "status": "SUCCESS", "input_data": {}, "output_data": {}, "duration_ms": 50},
                    {"id": "s2", "step_index": 1, "step_name": "Calculate Exposure", "tool_name": "budget_calculation", "status": "SUCCESS", "input_data": {"budget": 10000}, "output_data": {"total_cost": 15400, "breakdown": [{"category": "margin", "amount": 7700}, {"category": "margin", "amount": 7700}]}, "duration_ms": 80},
                    {"id": "s3", "step_index": 2, "step_name": "Execute Order", "tool_name": "finalize_booking", "status": "FAILED", "error_text": "MarginBreachError: Requested order exceeds collateral limit", "input_data": {}, "output_data": {}, "duration_ms": 150},
                ],
            },
        ]

    @classmethod
    def run_benchmark(cls) -> Dict[str, Any]:
        """Run all test cases across baselines and BLACKBOX hybrid engine."""
        cases = cls.get_benchmark_cases()
        engine = HybridDiagnosisEngine()

        results: List[Dict[str, Any]] = []

        hybrid_ranks: List[int] = []
        last_step_ranks: List[int] = []
        rule_only_ranks: List[int] = []
        anomaly_only_ranks: List[int] = []

        for c in cases:
            steps = c["steps"]
            gt = c["ground_truth_suspect"]

            # Run Hybrid Model
            diag = engine.diagnose_run({"id": c["case_id"], "metadata": {"budget": 2500}}, steps)
            ranked_step_tools = [s["tool_name"] for s in diag["ranked_steps"]]

            # Find rank of ground truth in hybrid
            try:
                h_rank = ranked_step_tools.index(gt) + 1
            except ValueError:
                h_rank = len(steps) + 1
            hybrid_ranks.append(h_rank)

            # Baseline 1: Last Step (blames the final failed step)
            failed_steps = [s for s in steps if s.get("status") == "FAILED"]
            last_failed_tool = failed_steps[-1]["tool_name"] if failed_steps else steps[-1]["tool_name"]
            last_step_rank = 1 if last_failed_tool == gt else len(steps)
            last_step_ranks.append(last_step_rank)

            # Baseline 2: Rule-Only Ranker
            rule_ranked = sorted(steps, key=lambda s: engine.rule_engine.evaluate_step(s, {})[0], reverse=True)
            rule_tools = [s["tool_name"] for s in rule_ranked]
            r_rank = rule_tools.index(gt) + 1 if gt in rule_tools else len(steps)
            rule_only_ranks.append(r_rank)

            # Baseline 3: Anomaly-Only Ranker
            anomaly_ranked = sorted(steps, key=lambda s: engine.anomaly_engine.evaluate_step(s)[0], reverse=True)
            anomaly_tools = [s["tool_name"] for s in anomaly_ranked]
            a_rank = anomaly_tools.index(gt) + 1 if gt in anomaly_tools else len(steps)
            anomaly_only_ranks.append(a_rank)

            results.append({
                "case_id": c["case_id"],
                "name": c["name"],
                "agent": c["agent"],
                "ground_truth": gt,
                "fault_category": c["fault_category"],
                "hybrid_top_prediction": diag["suspect_step_name"],
                "hybrid_top_tool": diag["ranked_steps"][0]["tool_name"] if diag["ranked_steps"] else "",
                "hybrid_rank": h_rank,
                "hybrid_suspicion_score": diag["suspicion_score"],
                "is_top1": h_rank == 1,
                "is_top3": h_rank <= 3,
                "reciprocal_rank": round(1.0 / h_rank, 3),
                "signals": diag["top_signals"],
            })

        # Calculate metrics
        def calc_metrics(ranks: List[int]) -> Dict[str, float]:
            top1 = sum(1 for r in ranks if r == 1) / len(ranks)
            top3 = sum(1 for r in ranks if r <= 3) / len(ranks)
            mrr = float(np.mean([1.0 / r for r in ranks]))
            return {
                "top1_accuracy": round(top1, 3),
                "top3_accuracy": round(top3, 3),
                "mrr": round(mrr, 3),
            }

        hybrid_metrics = calc_metrics(hybrid_ranks)
        last_step_metrics = calc_metrics(last_step_ranks)
        rule_only_metrics = calc_metrics(rule_only_ranks)
        anomaly_only_metrics = calc_metrics(anomaly_only_ranks)

        return {
            "benchmark_name": "BLACKBOX Autonomous Flight Recorder Benchmark v2.1",
            "total_cases": len(cases),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "models": {
                "blackbox_hybrid": {
                    "name": "BLACKBOX Hybrid Engine (Ours)",
                    **hybrid_metrics,
                },
                "baseline_last_step": {
                    "name": "Baseline: Last-Step Heuristic",
                    **last_step_metrics,
                },
                "baseline_rule_only": {
                    "name": "Baseline: Rule-Only Engine",
                    **rule_only_metrics,
                },
                "baseline_anomaly_only": {
                    "name": "Baseline: Anomaly-Only Engine",
                    **anomaly_only_metrics,
                },
            },
            "detailed_cases": results,
        }
