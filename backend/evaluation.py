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
        """Return 15 labeled cases (14 are scorable) with known ground-truth root causes.

        Design constraints (anti-leakage / anti-trivial-baseline):
        ──────────────────────────────────────────────────────────
        * Root cause is NOT always the first failing step.
        * Root cause is NOT always the slowest step.
        * Root cause is NOT always the last step.
        * Cases span 5 agent types and 9 fault categories.
        * None of these run IDs appear in the training corpus used by the
          Learned Ranker (ranker.py), so there is no train/test leakage.
        * Split annotation: cases 0-9 = held-out TEST, cases 10-14 = VALIDATION.
        """
        return [
            # ── TEST SPLIT (cases 0-9) ────────────────────────────────────────

            # 0. Root cause is NOT the first error — it's a silent upstream bug
            {
                "case_id": "TC_TRAVEL_01",
                "agent": "TravelPlanner", "split": "TEST",
                "name": "Paris 7-Day Budget Duplication",
                "ground_truth_suspect": "budget_calculation",
                "fault_category": "Arithmetic Duplication",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Requirements Parsing","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{"budget":2500},"duration_ms":40},
                    {"id":"s2","step_index":1,"step_name":"Flight Search","tool_name":"search_flights","status":"SUCCESS","input_data":{},"output_data":{"price":750},"duration_ms":310},
                    {"id":"s3","step_index":2,"step_name":"Accommodation Search","tool_name":"search_accommodations","status":"SUCCESS","input_data":{},"output_data":{"price":900},"duration_ms":290},
                    {"id":"s4","step_index":3,"step_name":"Budget Aggregation","tool_name":"budget_calculation","status":"SUCCESS","input_data":{"budget":2500},"output_data":{"total_cost":2950,"breakdown":[{"category":"hotel","amount":900},{"category":"hotel","amount":900},{"category":"flight","amount":750},{"category":"activities","amount":400}]},"duration_ms":65},
                    {"id":"s5","step_index":4,"step_name":"Itinerary Selection","tool_name":"select_itinerary","status":"FAILED","error_text":"BudgetExceededError: $2950 > $2500","input_data":{},"output_data":{},"duration_ms":140},
                    {"id":"s6","step_index":5,"step_name":"Booking Finalization","tool_name":"finalize_booking","status":"FAILED","error_text":"Downstream cancelled","input_data":{},"output_data":{},"duration_ms":20},
                ],
            },
            # 1. Temporal constraint — root cause is NOT the failing step
            {
                "case_id": "TC_TRAVEL_02",
                "agent": "TravelPlanner", "split": "TEST",
                "name": "Arrival / Checkin Time Inversion",
                "ground_truth_suspect": "search_accommodations",
                "fault_category": "Constraint Inversion",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Requirements Parsing","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{"budget":3000},"duration_ms":45},
                    {"id":"s2","step_index":1,"step_name":"Flight Search","tool_name":"search_flights","status":"SUCCESS","input_data":{},"output_data":{"arrival_time":"19:30"},"duration_ms":320},
                    {"id":"s3","step_index":2,"step_name":"Accommodation Search","tool_name":"search_accommodations","status":"SUCCESS","input_data":{},"output_data":{"checkin_time":"14:00","arrival_time":"19:30"},"duration_ms":280},
                    {"id":"s4","step_index":3,"step_name":"Itinerary Verification","tool_name":"select_itinerary","status":"FAILED","error_text":"ScheduleConflict: Hotel checkin closed before arrival","input_data":{},"output_data":{},"duration_ms":110},
                ],
            },
            # 2. Empty result — fast step, NOT the slowest
            {
                "case_id": "TC_TRAVEL_03",
                "agent": "TravelPlanner", "split": "TEST",
                "name": "Empty Flight Query Crash",
                "ground_truth_suspect": "search_flights",
                "fault_category": "Empty API Result",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Requirements Parsing","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{},"duration_ms":38},
                    {"id":"s2","step_index":1,"step_name":"Flight Search","tool_name":"search_flights","status":"SUCCESS","input_data":{},"output_data":{"flights":[]},"duration_ms":290},
                    {"id":"s3","step_index":2,"step_name":"Flight Selection","tool_name":"select_itinerary","status":"FAILED","error_text":"IndexError: list index out of range on flights[0]","input_data":{},"output_data":{},"duration_ms":85},
                ],
            },
            # 3. Schema drift — root cause is NOT the erroring step
            {
                "case_id": "TC_SUPPORT_01",
                "agent": "CustomerSupport", "split": "TEST",
                "name": "Database Schema Key Mismatch",
                "ground_truth_suspect": "database_query",
                "fault_category": "Schema Drift",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Receive Ticket","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{},"duration_ms":35},
                    {"id":"s2","step_index":1,"step_name":"Query Customer DB","tool_name":"database_query","status":"SUCCESS","input_data":{},"output_data":{"user_id":9921,"account_status":"ACTIVE"},"duration_ms":90},
                    {"id":"s3","step_index":2,"step_name":"Generate Response","tool_name":"select_itinerary","status":"FAILED","error_text":"KeyError: 'customer_guid' not found","input_data":{},"output_data":{},"duration_ms":60},
                ],
            },
            # 4. Port collision — slowest step AND root cause (baseline should get this)
            {
                "case_id": "TC_DEVOPS_01",
                "agent": "DevOpsDeployer", "split": "TEST",
                "name": "Service Port Binding Collision",
                "ground_truth_suspect": "deploy_service",
                "fault_category": "Infrastructure Collision",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Build Container","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{},"duration_ms":120},
                    {"id":"s2","step_index":1,"step_name":"Deploy Container Service","tool_name":"deploy_service","status":"FAILED","error_text":"BindException: Address already in use 0.0.0.0:8080","input_data":{},"output_data":{},"duration_ms":1150},
                    {"id":"s3","step_index":2,"step_name":"Verify Healthcheck","tool_name":"select_itinerary","status":"FAILED","error_text":"ConnectionRefused","input_data":{},"output_data":{},"duration_ms":500},
                ],
            },
            # 5. Stale data — root cause SUCCESS step, failure is two steps later
            {
                "case_id": "TC_TRADING_01",
                "agent": "TradingBot", "split": "TEST",
                "name": "Stale Quote Margin Calculation",
                "ground_truth_suspect": "budget_calculation",
                "fault_category": "Arithmetic Duplication",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Fetch Market Feed","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{},"duration_ms":50},
                    {"id":"s2","step_index":1,"step_name":"Calculate Exposure","tool_name":"budget_calculation","status":"SUCCESS","input_data":{"budget":10000},"output_data":{"total_cost":15400,"breakdown":[{"category":"margin","amount":7700},{"category":"margin","amount":7700}]},"duration_ms":80},
                    {"id":"s3","step_index":2,"step_name":"Execute Order","tool_name":"finalize_booking","status":"FAILED","error_text":"MarginBreachError: exceeds collateral limit","input_data":{},"output_data":{},"duration_ms":150},
                ],
            },
            # 6. Retry exhaustion — middle step, not first, not last
            {
                "case_id": "TC_SUPPORT_02",
                "agent": "CustomerSupport", "split": "TEST",
                "name": "Password Reset Auth 503 Loop",
                "ground_truth_suspect": "policy_lookup",
                "fault_category": "Retry Exhaustion",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Parse Ticket","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{"ticket":"PWD_RESET"},"duration_ms":30},
                    {"id":"s2","step_index":1,"step_name":"Lookup Auth Policy","tool_name":"policy_lookup","status":"SUCCESS","input_data":{},"output_data":{"attempts":5,"last_status":503,"max_retries":5},"duration_ms":1200},
                    {"id":"s3","step_index":2,"step_name":"Authorise Reset","tool_name":"authorize_refund","status":"FAILED","error_text":"MaxRetriesExceeded: auth service 503 after 5 attempts","input_data":{},"output_data":{},"duration_ms":45},
                    {"id":"s4","step_index":3,"step_name":"Send Resolution","tool_name":"send_confirmation_email","status":"FAILED","error_text":"PipelineAborted","input_data":{},"output_data":{},"duration_ms":12},
                ],
            },
            # 7. Config missing — root cause is step 1, errors appear at step 3
            {
                "case_id": "TC_DEVOPS_02",
                "agent": "DevOpsDeployer", "split": "TEST",
                "name": "Config Map Missing DATABASE_URL",
                "ground_truth_suspect": "sync_config",
                "fault_category": "Missing Context",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Fetch Repo","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{"image":"api:v2"},"duration_ms":90},
                    {"id":"s2","step_index":1,"step_name":"Sync Config Map","tool_name":"sync_config","status":"SUCCESS","input_data":{},"output_data":{"keys_found":3,"keys_missing":["DATABASE_URL"]},"duration_ms":110},
                    {"id":"s3","step_index":2,"step_name":"Deploy Service","tool_name":"deploy_service","status":"SUCCESS","input_data":{},"output_data":{"status":"running"},"duration_ms":820},
                    {"id":"s4","step_index":3,"step_name":"Health Probe","tool_name":"select_itinerary","status":"FAILED","error_text":"ConfigError: Required key DATABASE_URL not found","input_data":{},"output_data":{},"duration_ms":200},
                ],
            },
            # 8. Downstream propagation — blame is 3 steps back
            {
                "case_id": "TC_CODE_01",
                "agent": "CodeFixer", "split": "TEST",
                "name": "Silent Type Coercion Downstream Fail",
                "ground_truth_suspect": "analyse_code",
                "fault_category": "Invalid Model Output",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Parse Task","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{},"duration_ms":28},
                    {"id":"s2","step_index":1,"step_name":"Static Analysis","tool_name":"analyse_code","status":"SUCCESS","input_data":{},"output_data":{"type_errors":0,"coercion_warnings":1,"coerced_to":0},"duration_ms":410},
                    {"id":"s3","step_index":2,"step_name":"Code Generation","tool_name":"generate_code","status":"SUCCESS","input_data":{},"output_data":{"lines":120},"duration_ms":680},
                    {"id":"s4","step_index":3,"step_name":"Run Tests","tool_name":"run_tests","status":"FAILED","error_text":"TypeError: cannot add str and int — coercion silently produced 0","input_data":{},"output_data":{},"duration_ms":440},
                    {"id":"s5","step_index":4,"step_name":"Report","tool_name":"select_itinerary","status":"FAILED","error_text":"UpstreamFailed","input_data":{},"output_data":{},"duration_ms":18},
                ],
            },
            # 9. Constraint violation — root cause succeeds, two downstream fail
            {
                "case_id": "TC_TRADING_02",
                "agent": "TradingBot", "split": "TEST",
                "name": "Position Limit Breach",
                "ground_truth_suspect": "risk_check",
                "fault_category": "Constraint Violation",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Fetch Market Data","tool_name":"fetch_market_data","status":"SUCCESS","input_data":{},"output_data":{"price":182.3},"duration_ms":55},
                    {"id":"s2","step_index":1,"step_name":"Risk Assessment","tool_name":"risk_check","status":"SUCCESS","input_data":{},"output_data":{"order_size":50000,"max_position":10000,"breach":True},"duration_ms":180},
                    {"id":"s3","step_index":2,"step_name":"Execute Trade","tool_name":"execute_trade","status":"FAILED","error_text":"RiskLimitError: order size 50,000 exceeds max 10,000","input_data":{},"output_data":{},"duration_ms":90},
                    {"id":"s4","step_index":3,"step_name":"Compliance Log","tool_name":"send_confirmation_email","status":"FAILED","error_text":"PipelineAborted","input_data":{},"output_data":{},"duration_ms":12},
                ],
            },

            # ── VALIDATION SPLIT (cases 10-14) ───────────────────────────────

            # 10. Subscription downgrade constraint
            {
                "case_id": "TC_SUPPORT_03",
                "agent": "CustomerSupport", "split": "VALIDATION",
                "name": "Subscription Downgrade Blocked by Add-on",
                "ground_truth_suspect": "policy_lookup",
                "fault_category": "Constraint Violation",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Parse Ticket","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{},"duration_ms":30},
                    {"id":"s2","step_index":1,"step_name":"Policy Lookup","tool_name":"policy_lookup","status":"SUCCESS","input_data":{},"output_data":{"active_addons":["Premium Support"],"required_tier":"Base","current_tier":"Pro"},"duration_ms":88},
                    {"id":"s3","step_index":2,"step_name":"Process Downgrade","tool_name":"authorize_refund","status":"FAILED","error_text":"PolicyError: Downgrade blocked — active add-ons require Base tier","input_data":{},"output_data":{},"duration_ms":45},
                ],
            },
            # 11. DB migration NOT NULL constraint
            {
                "case_id": "TC_DEVOPS_03",
                "agent": "DevOpsDeployer", "split": "VALIDATION",
                "name": "Database Migration NOT NULL Violation",
                "ground_truth_suspect": "run_migration",
                "fault_category": "Schema Drift",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Checkout Schema","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{},"duration_ms":50},
                    {"id":"s2","step_index":1,"step_name":"Run Migration","tool_name":"run_migration","status":"FAILED","error_text":"IntegrityError: NOT NULL constraint failed: users.phone","input_data":{},"output_data":{},"duration_ms":340},
                    {"id":"s3","step_index":2,"step_name":"Verify Schema","tool_name":"select_itinerary","status":"FAILED","error_text":"PipelineAborted","input_data":{},"output_data":{},"duration_ms":20},
                ],
            },
            # 12. CodeFixer race condition
            {
                "case_id": "TC_CODE_02",
                "agent": "CodeFixer", "split": "VALIDATION",
                "name": "Race Condition in Job Queue",
                "ground_truth_suspect": "run_tests",
                "fault_category": "State Drift",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Parse Task","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{},"duration_ms":28},
                    {"id":"s2","step_index":1,"step_name":"Static Analysis","tool_name":"analyse_code","status":"SUCCESS","input_data":{},"output_data":{"warnings":0},"duration_ms":400},
                    {"id":"s3","step_index":2,"step_name":"Generate Code","tool_name":"generate_code","status":"SUCCESS","input_data":{},"output_data":{"lines":90},"duration_ms":650},
                    {"id":"s4","step_index":3,"step_name":"Run Tests","tool_name":"run_tests","status":"FAILED","error_text":"ConcurrencyError: job processed twice — duplicate queue entry","input_data":{},"output_data":{},"duration_ms":890},
                ],
            },
            # 13. Stale price feed trading
            {
                "case_id": "TC_TRADING_03",
                "agent": "TradingBot", "split": "VALIDATION",
                "name": "Stale Price Feed Decision",
                "ground_truth_suspect": "fetch_market_data",
                "fault_category": "Stale Data",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Fetch Market Data","tool_name":"fetch_market_data","status":"SUCCESS","input_data":{},"output_data":{"last_quote_age_sec":47,"threshold_sec":30,"stale":True},"duration_ms":55},
                    {"id":"s2","step_index":1,"step_name":"Strategy Calculation","tool_name":"budget_calculation","status":"SUCCESS","input_data":{},"output_data":{"signal":"BUY","size":2000},"duration_ms":90},
                    {"id":"s3","step_index":2,"step_name":"Execute Trade","tool_name":"execute_trade","status":"FAILED","error_text":"DataFeedError: last quote is 47s old — threshold 30s","input_data":{},"output_data":{},"duration_ms":80},
                ],
            },
            # 14. TravelPlanner Tokyo budget success path (no fault — tests specificity)
            {
                "case_id": "TC_TRAVEL_04",
                "agent": "TravelPlanner", "split": "VALIDATION",
                "name": "Tokyo Budget OK — No Fault",
                "ground_truth_suspect": "budget_calculation",   # highest suspicion even in success
                "fault_category": "No Fault (Specificity Check)",
                "steps": [
                    {"id":"s1","step_index":0,"step_name":"Requirements Parsing","tool_name":"parse_requirements","status":"SUCCESS","input_data":{},"output_data":{"budget":3500},"duration_ms":42},
                    {"id":"s2","step_index":1,"step_name":"Flight Search","tool_name":"search_flights","status":"SUCCESS","input_data":{},"output_data":{"price":950},"duration_ms":315},
                    {"id":"s3","step_index":2,"step_name":"Accommodation Search","tool_name":"search_accommodations","status":"SUCCESS","input_data":{},"output_data":{"price":1100},"duration_ms":285},
                    {"id":"s4","step_index":3,"step_name":"Budget Aggregation","tool_name":"budget_calculation","status":"SUCCESS","input_data":{"budget":3500},"output_data":{"total_cost":2450,"breakdown":[{"category":"flight","amount":950},{"category":"hotel","amount":1100},{"category":"activities","amount":400}]},"duration_ms":60},
                    {"id":"s5","step_index":4,"step_name":"Itinerary Selection","tool_name":"select_itinerary","status":"SUCCESS","input_data":{},"output_data":{"status":"CONFIRMED"},"duration_ms":130},
                ],
            },
        ]

    @classmethod
    def run_benchmark(cls) -> Dict[str, Any]:
        """Run all test cases across baselines and BLACKBOX hybrid engine.

        Split policy
        ─────────────
        TEST split       (cases 0-9)  — primary reported metrics
        VALIDATION split (cases 10-14) — secondary check for overfitting

        The Learned Ranker is trained on a synthetic corpus built at import
        time (ranker.py).  None of the benchmark case IDs appear in that
        corpus — there is no train/test leakage.
        """
        raw_cases  = cls.get_benchmark_cases()
        # A "No Fault" run has no real root cause, so it cannot be scored for
        # localization. It is excluded from ranking metrics (kept as a
        # specificity fixture) instead of being counted with a made-up label.
        all_cases  = [c for c in raw_cases if not c["fault_category"].startswith("No Fault")]
        test_cases = [c for c in all_cases if c.get("split", "TEST") == "TEST"]
        val_cases  = [c for c in all_cases if c.get("split") == "VALIDATION"]

        engine = HybridDiagnosisEngine()

        def _evaluate_cases(cases):
            hybrid_ranks = []
            last_ranks   = []
            rule_ranks   = []
            anom_ranks   = []
            results      = []

            for c in cases:
                steps = c["steps"]
                gt    = c["ground_truth_suspect"]

                diag = engine.diagnose_run({"id": c["case_id"], "metadata": {"budget": 2500}}, steps)
                ranked_tools = [s["tool_name"] for s in diag["ranked_steps"]]

                try:    h_rank = ranked_tools.index(gt) + 1
                except: h_rank = len(steps) + 1
                hybrid_ranks.append(h_rank)

                # Last-step baseline
                failed  = [s for s in steps if s.get("status") == "FAILED"]
                last_t  = failed[-1]["tool_name"] if failed else steps[-1]["tool_name"]
                last_ranks.append(1 if last_t == gt else len(steps))

                # Rule-only baseline
                rule_sorted = sorted(steps, key=lambda s: engine.rule_engine.evaluate_step(s, {})[0], reverse=True)
                rt = [s["tool_name"] for s in rule_sorted]
                rule_ranks.append(rt.index(gt) + 1 if gt in rt else len(steps))

                # Anomaly-only baseline
                anom_sorted = sorted(steps, key=lambda s: engine.anomaly_engine.evaluate_step(s)[0], reverse=True)
                at = [s["tool_name"] for s in anom_sorted]
                anom_ranks.append(at.index(gt) + 1 if gt in at else len(steps))

                results.append({
                    "case_id":               c["case_id"],
                    "name":                  c["name"],
                    "agent":                 c["agent"],
                    "split":                 c.get("split", "TEST"),
                    "ground_truth":          gt,
                    "fault_category":        c["fault_category"],
                    "hybrid_top_prediction": diag["suspect_step_name"],
                    "hybrid_top_tool":       diag["ranked_steps"][0]["tool_name"] if diag["ranked_steps"] else "",
                    "hybrid_rank":           h_rank,
                    "hybrid_suspicion_score": diag["suspicion_score"],
                    "is_top1":               h_rank == 1,
                    "is_top3":               h_rank <= 3,
                    "reciprocal_rank":       round(1.0 / h_rank, 3),
                    "signals":               diag["top_signals"],
                })

            def _metrics(ranks):
                n = len(ranks)
                return {
                    "top1_accuracy": round(sum(1 for r in ranks if r == 1) / n, 3),
                    "top3_accuracy": round(sum(1 for r in ranks if r <= 3) / n, 3),
                    "mrr":           round(float(np.mean([1.0 / r for r in ranks])), 3),
                    "n":             n,
                }

            return results, {
                "blackbox_hybrid":        {"name": "BLACKBOX Hybrid (Ours)",       **_metrics(hybrid_ranks)},
                "baseline_last_step":     {"name": "Baseline: Last-Step Heuristic", **_metrics(last_ranks)},
                "baseline_rule_only":     {"name": "Baseline: Rule-Only Engine",    **_metrics(rule_ranks)},
                "baseline_anomaly_only":  {"name": "Baseline: Anomaly-Only Engine", **_metrics(anom_ranks)},
            }

        test_results, test_models = _evaluate_cases(test_cases)
        val_results,  val_models  = _evaluate_cases(val_cases)

        return {
            "benchmark_name": "BLACKBOX Autonomous Flight Recorder Benchmark v2.1",
            "total_cases":    len(all_cases),
            "test_cases":     len(test_cases),
            "validation_cases": len(val_cases),
            "split_note":     (
                "Primary metrics are on the held-out TEST split (10 cases). "
                "VALIDATION split (4 scorable cases; the no-fault fixture is excluded) is a secondary overfitting check. "
                "Ranker training corpus is entirely separate — no leakage."
            ),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "models":         test_models,     # primary — TEST split
            "models_val":     val_models,      # secondary — VALIDATION split
            "detailed_cases": test_results + val_results,
        }
