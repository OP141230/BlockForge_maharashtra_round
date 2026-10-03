"""Synthetic Seed Data Generator for BLACKBOX: AI Agent Flight Recorder.

All data is generated deterministically for reproducible benchmark demonstrations.
Label: Synthetic demo data.

Generates ~100 runs across 5 agent types, 6 fault categories, varied
destinations, budgets, and outcomes — all deterministic, no randomness.
"""
from datetime import datetime, timedelta, timezone
import json
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from backend.database import SessionLocal, init_db
from backend.models import (
    Checkpoint,
    DiagnosisResult,
    EvaluationBenchmark,
    Run,
    Step,
)
from backend.diagnosis.hybrid import HybridDiagnosisEngine
from backend.evaluation import BenchmarkRunner


# ─────────────────────────────────────────────────────────────────────────────
# DETERMINISTIC VARIATION TABLES
# No random calls anywhere in this file.
# ─────────────────────────────────────────────────────────────────────────────

TRAVEL_DESTINATIONS = [
    ("Paris", "CDG", "France"),
    ("Tokyo", "NRT", "Japan"),
    ("New York", "JFK", "USA"),
    ("London", "LHR", "UK"),
    ("Barcelona", "BCN", "Spain"),
    ("Dubai", "DXB", "UAE"),
    ("Sydney", "SYD", "Australia"),
    ("Rome", "FCO", "Italy"),
    ("Singapore", "SIN", "Singapore"),
    ("Amsterdam", "AMS", "Netherlands"),
]

TRAVEL_BUDGETS = [1800, 2000, 2200, 2500, 2800, 3000, 3200, 3500, 4000, 4500]

# (flight, hotel, activities) — correct totals for success runs
TRAVEL_COSTS = [
    (620, 780, 350),
    (750, 900, 400),
    (820, 850, 420),
    (680, 720, 380),
    (950, 1100, 500),
    (1100, 1200, 600),
    (880, 960, 480),
    (720, 840, 400),
    (1050, 1150, 550),
    (800, 880, 420),
]

SUPPORT_SCENARIOS = [
    ("Billing Dispute Resolution",   "database_query",    "Schema Drift",         "KeyError: 'customer_guid' missing from response payload."),
    ("Password Reset Loop",          "policy_lookup",     "Retry Exhaustion",     "MaxRetriesExceeded: Auth service returned 503 after 5 attempts."),
    ("Subscription Downgrade Fail",  "policy_lookup",     "Constraint Violation", "PolicyError: Downgrade blocked — active add-ons require Base tier."),
    ("Refund Processing Error",      "authorize_refund",  "Tool Failure",         "PaymentGatewayError: Transaction declined by processor."),
    ("Account Merge Conflict",       "database_query",    "State Drift",          "DuplicateKeyError: Merged account ID already exists in table."),
    ("Invoice Generation Error",     "generate_invoice",  "Missing Context",      "TemplateError: Variable 'billing_period' undefined."),
    ("Promo Code Validation Fail",   "validate_promo",    "Invalid Model Output", "ValidationError: Promo code SAVE30 expired 2025-01-01."),
    ("SLA Breach Escalation",        "route_ticket",      "Downstream Propagation","EscalationFailed: No available agents in priority queue."),
]

DEVOPS_SCENARIOS = [
    ("Microservice Container Rollout",  "deploy_service",   "Port Collision",       "BindException: Address 0.0.0.0:8080 already in use."),
    ("Database Migration Failure",      "run_migration",    "Schema Drift",         "IntegrityError: NOT NULL constraint failed: users.phone."),
    ("Config Map Sync Error",           "sync_config",      "Missing Context",      "ConfigError: Required key DATABASE_URL not found in ConfigMap."),
    ("Rolling Deployment Timeout",      "deploy_service",   "Retry Exhaustion",     "TimeoutError: Health probe failed after 120s — pod not ready."),
    ("SSL Certificate Renewal Fail",    "renew_certificate","Tool Failure",         "ACMEError: DNS challenge verification failed for domain."),
    ("Auto-scaling Policy Conflict",    "scale_pods",       "Constraint Violation", "ScalingError: Min replicas (5) exceeds max replicas (3) in policy."),
    ("Log Pipeline Overflow",           "flush_logs",       "Downstream Propagation","BufferOverflowError: Log sink queue exceeded 10,000 entries."),
    ("CI Build Cache Poisoning",        "build_image",      "Invalid Model Output", "HashMismatch: Cached layer digest does not match expected."),
]

CODE_SCENARIOS = [
    ("Async Deadlock in Payment Flow",   "run_tests",    "Arithmetic Duplication", "DeadlockError: Circular await detected in payment_processor.py:84."),
    ("Type Coercion Silent Failure",     "analyse_code", "Invalid Model Output",   "TypeError: Cannot add str and int — coercion silently produced 0."),
    ("Memory Leak in Session Handler",   "run_tests",    "State Drift",            "MemoryError: Session store grew to 4.2 GB — leak in cleanup path."),
    ("Race Condition in Job Queue",      "analyse_code", "Downstream Propagation", "ConcurrencyError: Job processed twice due to duplicate queue entry."),
    ("Regex DoS Vulnerability",          "run_tests",    "Constraint Violation",   "TimeoutError: Regex engine stalled on adversarial input after 30s."),
    ("Uncaught Promise Rejection",       "analyse_code", "Missing Context",        "UnhandledPromiseRejection: fetch() called with undefined URL."),
]

TRADING_SCENARIOS = [
    ("Order Routing Arbitrage Fail",     "execute_trade",    "Arithmetic Duplication", "PriceMismatchError: Calculated arbitrage spread turned negative."),
    ("Position Limit Breach",            "risk_check",       "Constraint Violation",   "RiskLimitError: Order size 50,000 exceeds max position 10,000."),
    ("Stale Price Feed",                 "fetch_market_data","Tool Failure",            "DataFeedError: Last quote is 47 seconds old — threshold is 30s."),
    ("Margin Call Miscalculation",       "budget_calculation","Arithmetic Duplication", "MarginError: Available margin $12,400 < required $15,200."),
    ("Compliance Rule Mismatch",         "compliance_check", "Constraint Violation",   "ComplianceError: Short sale restricted on TSLA pre-market hours."),
    ("Settlement Failure Cascade",       "settle_trade",     "Downstream Propagation", "SettlementError: Counterparty failed to deliver securities T+2."),
]


def _make_step(run_id, idx, name, tool, status, input_data, output_data,
               duration_ms, error_text=None, is_suspect=False,
               is_downstream=False, suspicion_score=0.0, side_effect=False):
    return {
        "id": f"s_{run_id}_{idx}",
        "run_id": run_id,
        "step_index": idx,
        "step_name": name,
        "tool_name": tool,
        "input_data_json": json.dumps(input_data),
        "output_data_json": json.dumps(output_data),
        "duration_ms": duration_ms,
        "status": status,
        "error_text": error_text,
        "side_effect_flag": side_effect,
        "is_root_suspect": is_suspect,
        "is_downstream_impact": is_downstream,
        "suspicion_score": suspicion_score,
        "dependencies_json": json.dumps([f"s_{run_id}_{idx-1}"] if idx > 0 else []),
    }


def _make_travel_steps(run_id, dest, iata, flight_cost, hotel_cost,
                       activities_cost, budget, inject_bug):
    """Generate TravelPlanner steps. inject_bug=True doubles hotel cost."""
    actual_total = flight_cost + hotel_cost + activities_cost
    buggy_total  = flight_cost + hotel_cost + hotel_cost + activities_cost

    total = buggy_total if inject_bug else actual_total
    budget_status = "OVERFLOW" if total > budget else "WITHIN_BUDGET"
    downstream_failed = inject_bug and (total > budget)

    breakdown = [
        {"category": f"Flight", "amount": flight_cost},
        {"category": f"Accommodation", "amount": hotel_cost},
    ]
    if inject_bug:
        breakdown.append({"category": "Accommodation (duplicate)", "amount": hotel_cost})
    breakdown.append({"category": "Activities & Transit", "amount": activities_cost})

    steps = [
        _make_step(run_id, 0, "Requirements Parsing", "parse_requirements", "SUCCESS",
                   {"prompt": f"Plan trip to {dest}", "budget": budget},
                   {"destination": dest, "budget_limit": budget}, 40.0),
        _make_step(run_id, 1, "Flight Discovery", "search_flights", "SUCCESS",
                   {"origin": "JFK", "destination": iata},
                   {"selected_flight": {"price": flight_cost}}, 300.0),
        _make_step(run_id, 2, "Accommodation Search", "search_accommodations", "SUCCESS",
                   {"city": dest, "nights": 6},
                   {"selected_hotel": {"price_total": hotel_cost}}, 280.0),
        _make_step(run_id, 3, "Budget Calculation & Audit", "budget_calculation",
                   "SUCCESS",
                   {"flight_cost": flight_cost, "hotel_cost": hotel_cost,
                    "activities_cost": activities_cost, "budget_limit": budget},
                   {"total_cost": total, "budget_limit": budget,
                    "calculation_status": budget_status, "breakdown": breakdown},
                   68.0,
                   is_suspect=inject_bug,
                   suspicion_score=88.0 if inject_bug else 5.0),
        _make_step(run_id, 4, "Itinerary Verification", "select_itinerary",
                   "FAILED" if downstream_failed else "SUCCESS",
                   {"total_allocated": total, "budget_limit": budget},
                   {"error": f"BudgetExceededError: ${total} > ${budget}"} if downstream_failed
                   else {"status": "CONFIRMED", "allocated": total},
                   140.0,
                   error_text=f"BudgetExceededError: ${total} exceeds ${budget}" if downstream_failed else None,
                   is_downstream=downstream_failed,
                   suspicion_score=35.0 if downstream_failed else 4.0),
        _make_step(run_id, 5, "Booking Finalization", "finalize_booking",
                   "FAILED" if downstream_failed else "SUCCESS",
                   {"itinerary_confirmed": not downstream_failed},
                   {"error": "PipelineAborted"} if downstream_failed
                   else {"booking_reference": f"BKG-{budget}", "total_charged": total},
                   90.0,
                   error_text="PipelineAborted: Upstream validation failure" if downstream_failed else None,
                   is_downstream=downstream_failed,
                   suspicion_score=22.0 if downstream_failed else 3.0,
                   side_effect=True),
        _make_step(run_id, 6, "Send Confirmation Email", "send_confirmation_email",
                   "FAILED" if downstream_failed else "SUCCESS",
                   {"status": "ABORTED" if downstream_failed else "CONFIRMED"},
                   {"status": "NOT_SENT"} if downstream_failed else {"email_sent": True},
                   15.0,
                   error_text="ExecutionSuppressed: Prior failure" if downstream_failed else None,
                   is_downstream=downstream_failed,
                   suspicion_score=12.0 if downstream_failed else 2.0,
                   side_effect=True),
    ]
    return steps


def _make_support_steps(run_id, scenario, tool_name, fault_category, error_msg):
    steps = [
        _make_step(run_id, 0, "Parse Ticket", "parse_requirements", "SUCCESS",
                   {"ticket": scenario}, {"ticket_id": f"TCK-{abs(hash(run_id)) % 9999}"}, 35.0),
        _make_step(run_id, 1, "Policy Lookup", tool_name, "SUCCESS",
                   {"scenario": scenario},
                   {"policy": "retrieved", "schema_version": "v3_migrated"}, 88.0,
                   is_suspect=True, suspicion_score=84.0),
        _make_step(run_id, 2, "Authorise Action", "authorize_refund", "FAILED",
                   {"policy_result": "retrieved"},
                   {"error": error_msg[:60]}, 45.0,
                   error_text=error_msg,
                   is_downstream=True, suspicion_score=30.0),
        _make_step(run_id, 3, "Send Resolution", "send_confirmation_email", "FAILED",
                   {"resolution": "pending"},
                   {"error": "PipelineAborted"}, 12.0,
                   error_text="PipelineAborted: upstream failed",
                   is_downstream=True, suspicion_score=12.0, side_effect=True),
    ]
    return steps


def _make_devops_steps(run_id, scenario, tool_name, fault_category, error_msg):
    steps = [
        _make_step(run_id, 0, "Fetch Config & Build", "parse_requirements", "SUCCESS",
                   {"task": scenario}, {"image": "service:latest"}, 120.0),
        _make_step(run_id, 1, "Pre-flight Check", "select_itinerary", "SUCCESS",
                   {"image": "service:latest"}, {"checks": "passed"}, 90.0),
        _make_step(run_id, 2, "Execute Deployment", tool_name, "FAILED",
                   {"target": "production", "image": "service:latest"},
                   {"error": error_msg[:60]}, 1180.0,
                   error_text=error_msg,
                   is_suspect=True, suspicion_score=92.0),
        _make_step(run_id, 3, "Health Probe", "select_itinerary", "FAILED",
                   {"endpoint": "/health"},
                   {"error": "ConnectionRefused"}, 150.0,
                   error_text="ConnectionRefused: service not responding",
                   is_downstream=True, suspicion_score=26.0),
    ]
    return steps


def _make_code_steps(run_id, scenario, tool_name, fault_category, error_msg):
    steps = [
        _make_step(run_id, 0, "Parse Task", "parse_requirements", "SUCCESS",
                   {"task": scenario}, {"parsed": True}, 30.0),
        _make_step(run_id, 1, "Static Analysis", "analyse_code", "SUCCESS",
                   {"task": scenario}, {"warnings": 2, "errors": 0}, 410.0),
        _make_step(run_id, 2, "Code Generation", "generate_code", "SUCCESS",
                   {"spec": scenario}, {"lines": 120, "functions": 8}, 680.0),
        _make_step(run_id, 3, "Run Tests", tool_name, "FAILED",
                   {"test_suite": "unit"},
                   {"passed": 12, "failed": 3, "error": error_msg[:60]}, 890.0,
                   error_text=error_msg,
                   is_suspect=True, suspicion_score=79.0),
        _make_step(run_id, 4, "Generate Report", "select_itinerary", "FAILED",
                   {"test_result": "FAILED"},
                   {"error": "UpstreamFailed"}, 25.0,
                   error_text="UpstreamFailed: test run did not complete",
                   is_downstream=True, suspicion_score=18.0),
    ]
    return steps


def _make_trading_steps(run_id, scenario, tool_name, fault_category, error_msg):
    steps = [
        _make_step(run_id, 0, "Fetch Market Data", "fetch_market_data", "SUCCESS",
                   {"symbols": ["AAPL", "GOOG"]}, {"prices": {"AAPL": 182.3}}, 55.0),
        _make_step(run_id, 1, "Risk Assessment", "risk_check", "SUCCESS",
                   {"portfolio": "P-881"}, {"risk_score": 0.42}, 180.0),
        _make_step(run_id, 2, "Strategy Calculation", "budget_calculation",
                   "SUCCESS" if fault_category != "Arithmetic Duplication" else "SUCCESS",
                   {"strategy": scenario},
                   {"signal": "BUY", "size": 5000, "note": "duplication" if "Arithmetic" in fault_category else "ok"},
                   220.0,
                   is_suspect=fault_category == "Arithmetic Duplication",
                   suspicion_score=85.0 if fault_category == "Arithmetic Duplication" else 5.0),
        _make_step(run_id, 3, "Execute Trade", tool_name, "FAILED",
                   {"signal": "BUY", "size": 5000},
                   {"error": error_msg[:60]}, 140.0,
                   error_text=error_msg,
                   is_suspect=fault_category != "Arithmetic Duplication",
                   is_downstream=fault_category == "Arithmetic Duplication",
                   suspicion_score=91.0 if fault_category != "Arithmetic Duplication" else 33.0),
        _make_step(run_id, 4, "Compliance Log", "send_confirmation_email", "FAILED",
                   {"trade": "failed"},
                   {"error": "PipelineAborted"}, 20.0,
                   error_text="PipelineAborted: upstream trade failed",
                   is_downstream=True, suspicion_score=10.0, side_effect=True),
    ]
    return steps


def _add_run_with_steps(db, engine, run_obj, steps_data, now_offset):
    db.add(run_obj)
    step_dicts = []
    for s in steps_data:
        # Build clean Step object
        step = Step(
            id=s["id"],
            run_id=s["run_id"],
            step_index=s["step_index"],
            step_name=s["step_name"],
            tool_name=s["tool_name"],
            input_data_json=s["input_data_json"],
            output_data_json=s["output_data_json"],
            duration_ms=s["duration_ms"],
            status=s["status"],
            error_text=s.get("error_text"),
            side_effect_flag=s.get("side_effect_flag", False),
            is_root_suspect=s.get("is_root_suspect", False),
            is_downstream_impact=s.get("is_downstream_impact", False),
            suspicion_score=s.get("suspicion_score", 0.0),
            dependencies_json=s.get("dependencies_json", "[]"),
        )
        db.add(step)
        step_dicts.append({
            "id": s["id"],
            "step_index": s["step_index"],
            "step_name": s["step_name"],
            "tool_name": s["tool_name"],
            "status": s["status"],
            "input_data": json.loads(s["input_data_json"]),
            "output_data": json.loads(s["output_data_json"]),
            "duration_ms": s["duration_ms"],
            "error_text": s.get("error_text"),
            "dependencies": json.loads(s.get("dependencies_json", "[]")),
            "is_root_suspect": s.get("is_root_suspect", False),
        })

    # Run hybrid diagnosis
    diag = engine.diagnose_run(run_obj.to_dict(), step_dicts)
    db.add(DiagnosisResult(
        id=f"diag_{run_obj.id}",
        run_id=run_obj.id,
        suspect_step_id=diag["suspect_step_id"] or step_dicts[0]["id"],
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
        created_at=now_offset,
    ))


def seed_database():
    """Seed ~100 synthetic trace runs and benchmark evaluation data."""
    init_db()
    db: Session = SessionLocal()

    # Idempotent: clear existing data
    db.query(DiagnosisResult).delete()
    db.query(Checkpoint).delete()
    db.query(Step).delete()
    db.query(Run).delete()
    db.query(EvaluationBenchmark).delete()
    db.commit()

    engine_diag = HybridDiagnosisEngine()
    now = datetime.now(timezone.utc)

    # =========================================================================
    # 1. FLAGSHIP RUNS — Paris (kept identical so Investigation demo works)
    # =========================================================================

    # 1a. Flagship FAILED run
    run_flagship = Run(
        id="run_travel_paris_fail",
        agent_name="TravelPlanner Agent v2",
        scenario="Paris 7-Day Budget Itinerary",
        task_description="Plan a 7-day budget trip to Paris for 1 traveler under $2,500.",
        status="FAILED",
        started_at=now - timedelta(minutes=15),
        completed_at=now - timedelta(minutes=14, seconds=42),
        total_duration_ms=1045.0,
        error_message="BudgetExceededError: Calculated total $2,950 exceeds budget $2,500.",
        is_synthetic=True,
        metadata_json=json.dumps({"destination": "Paris, France", "budget": 2500}),
        ground_truth_suspect_step="budget_calculation",
        ground_truth_fault_type="Arithmetic Duplication",
    )
    flagship_steps = _make_travel_steps(
        "run_travel_paris_fail", "Paris", "CDG", 750, 900, 400, 2500, inject_bug=True
    )
    # Restore original IDs so Replay/Checkpoint links work
    id_map = {
        0: "step_tp_0", 1: "step_tp_1", 2: "step_tp_2",
        3: "step_tp_3", 4: "step_tp_4", 5: "step_tp_5", 6: "step_tp_6",
    }
    for s in flagship_steps:
        s["id"] = id_map[s["step_index"]]
        s["dependencies_json"] = json.dumps(
            [id_map[s["step_index"] - 1]] if s["step_index"] > 0 else []
        )
    _add_run_with_steps(db, engine_diag, run_flagship, flagship_steps,
                        now - timedelta(minutes=14))

    # Checkpoints for flagship
    for s in flagship_steps:
        db.add(Checkpoint(
            id=f"cp_{s['id']}",
            run_id="run_travel_paris_fail",
            step_id=s["id"],
            step_index=s["step_index"],
            agent_state_json=json.dumps({"current_step": s["step_name"]}),
            memory_state_json=json.dumps({"budget_limit": 2500}),
            timestamp=now - timedelta(minutes=15 - s["step_index"]),
        ))

    # 1b. Flagship SUCCESS baseline
    run_success = Run(
        id="run_travel_paris_success",
        agent_name="TravelPlanner Agent v2",
        scenario="Paris 7-Day Budget Itinerary (Baseline Success)",
        task_description="Plan a 7-day budget trip to Paris for 1 traveler under $2,500.",
        status="SUCCESS",
        started_at=now - timedelta(hours=2),
        completed_at=now - timedelta(hours=2, minutes=-1),
        total_duration_ms=980.0,
        is_synthetic=True,
        metadata_json=json.dumps({"destination": "Paris, France", "budget": 2500}),
    )
    success_steps = _make_travel_steps(
        "run_travel_paris_success", "Paris", "CDG", 750, 900, 400, 2500, inject_bug=False
    )
    success_id_map = {
        0: "step_tps_0", 1: "step_tps_1", 2: "step_tps_2",
        3: "step_tps_3", 4: "step_tps_4", 5: "step_tps_5", 6: "step_tps_6",
    }
    for s in success_steps:
        s["id"] = success_id_map[s["step_index"]]
        s["dependencies_json"] = json.dumps(
            [success_id_map[s["step_index"] - 1]] if s["step_index"] > 0 else []
        )
    _add_run_with_steps(db, engine_diag, run_success, success_steps,
                        now - timedelta(hours=2))

    # =========================================================================
    # 2. TRAVEL PLANNER — varied destinations × success/fail
    # Indices 0-9 → destinations, 0-9 → budgets/costs
    # Even index = SUCCESS, Odd index = FAILED (inject_bug)
    # =========================================================================
    for i in range(len(TRAVEL_DESTINATIONS)):
        dest, iata, country = TRAVEL_DESTINATIONS[i]
        budget = TRAVEL_BUDGETS[i]
        fc, hc, ac = TRAVEL_COSTS[i]
        inject = (i % 2 == 1)  # odd = bug injected

        for variant in range(4):  # 4 variants per destination = 40 travel runs
            run_id = f"run_tp_{dest.lower().replace(' ','_')}_{variant}"
            if run_id in ("run_travel_paris_fail", "run_travel_paris_success"):
                continue  # already seeded above

            # Slight variation: add variant offset to costs to make runs distinct
            fv = fc + variant * 20
            hv = hc + variant * 15
            av = ac + variant * 10
            bv = budget + variant * 50
            bug = inject and (variant % 2 == 0)
            total = fv + hv + av
            buggy = fv + hv + hv + av
            actual_total = buggy if bug else total
            run_status = "FAILED" if (bug and actual_total > bv) else "SUCCESS"

            r = Run(
                id=run_id,
                agent_name="TravelPlanner Agent v2",
                scenario=f"{dest} {6 + variant}-Day Trip",
                task_description=f"Plan a trip to {dest}, {country} within ${bv} budget.",
                status=run_status,
                started_at=now - timedelta(hours=3 + i + variant),
                completed_at=now - timedelta(hours=3 + i + variant, minutes=-1),
                total_duration_ms=900.0 + i * 20 + variant * 10,
                error_message=f"BudgetExceededError: ${actual_total} > ${bv}" if run_status == "FAILED" else None,
                is_synthetic=True,
                metadata_json=json.dumps({"destination": f"{dest}, {country}", "budget": bv}),
                ground_truth_suspect_step="budget_calculation" if bug else None,
                ground_truth_fault_type="Arithmetic Duplication" if bug else None,
            )
            steps = _make_travel_steps(run_id, dest, iata, fv, hv, av, bv, bug)
            _add_run_with_steps(db, engine_diag, r, steps,
                                now - timedelta(hours=3 + i + variant))

    # =========================================================================
    # 3. CUSTOMER SUPPORT AGENT — 8 scenarios × 2 variants each = 16 runs
    # =========================================================================
    for i, (scenario, tool, fault, error) in enumerate(SUPPORT_SCENARIOS):
        for variant in range(2):
            run_id = f"run_support_{i}_{variant}"
            r = Run(
                id=run_id,
                agent_name="CustomerSupport Agent",
                scenario=scenario,
                task_description=f"Resolve customer issue: {scenario}.",
                status="FAILED",
                started_at=now - timedelta(hours=4 + i + variant),
                completed_at=now - timedelta(hours=4 + i + variant, minutes=-1),
                total_duration_ms=500.0 + i * 30 + variant * 15,
                error_message=error,
                is_synthetic=True,
                metadata_json=json.dumps({"ticket_variant": variant}),
                ground_truth_suspect_step=tool,
                ground_truth_fault_type=fault,
            )
            steps = _make_support_steps(run_id, scenario, tool, fault, error)
            _add_run_with_steps(db, engine_diag, r, steps,
                                now - timedelta(hours=4 + i + variant))

        # One success variant per scenario
        run_id_ok = f"run_support_{i}_ok"
        r_ok = Run(
            id=run_id_ok,
            agent_name="CustomerSupport Agent",
            scenario=f"{scenario} (Resolved)",
            task_description=f"Resolve customer issue: {scenario}.",
            status="SUCCESS",
            started_at=now - timedelta(hours=10 + i),
            completed_at=now - timedelta(hours=10 + i, minutes=-1),
            total_duration_ms=420.0 + i * 20,
            is_synthetic=True,
            metadata_json=json.dumps({"resolved": True}),
        )
        # Success steps — all pass
        ok_steps = [
            _make_step(run_id_ok, 0, "Parse Ticket", "parse_requirements", "SUCCESS",
                       {"ticket": scenario}, {"ticket_id": f"TCK-{1000+i}"}, 35.0),
            _make_step(run_id_ok, 1, "Policy Lookup", tool, "SUCCESS",
                       {"scenario": scenario}, {"policy": "found", "action": "approved"}, 88.0),
            _make_step(run_id_ok, 2, "Authorise Action", "authorize_refund", "SUCCESS",
                       {"policy": "approved"}, {"status": "AUTHORISED"}, 45.0),
            _make_step(run_id_ok, 3, "Send Resolution", "send_confirmation_email", "SUCCESS",
                       {"resolution": "resolved"}, {"sent": True}, 12.0, side_effect=True),
        ]
        _add_run_with_steps(db, engine_diag, r_ok, ok_steps,
                            now - timedelta(hours=10 + i))

    # =========================================================================
    # 4. DEVOPS DEPLOYER AGENT — 8 scenarios × 2 variants = 16 + 8 success = 24
    # =========================================================================
    for i, (scenario, tool, fault, error) in enumerate(DEVOPS_SCENARIOS):
        for variant in range(2):
            run_id = f"run_devops_{i}_{variant}"
            r = Run(
                id=run_id,
                agent_name="DevOpsDeployer Agent",
                scenario=scenario,
                task_description=f"Execute DevOps task: {scenario}.",
                status="FAILED",
                started_at=now - timedelta(hours=5 + i + variant),
                completed_at=now - timedelta(hours=5 + i + variant, minutes=-1),
                total_duration_ms=1200.0 + i * 50 + variant * 25,
                error_message=error,
                is_synthetic=True,
                metadata_json=json.dumps({"environment": "production", "variant": variant}),
                ground_truth_suspect_step=tool,
                ground_truth_fault_type=fault,
            )
            steps = _make_devops_steps(run_id, scenario, tool, fault, error)
            _add_run_with_steps(db, engine_diag, r, steps,
                                now - timedelta(hours=5 + i + variant))

        run_id_ok = f"run_devops_{i}_ok"
        r_ok = Run(
            id=run_id_ok,
            agent_name="DevOpsDeployer Agent",
            scenario=f"{scenario} (Success)",
            task_description=f"Execute DevOps task: {scenario}.",
            status="SUCCESS",
            started_at=now - timedelta(hours=12 + i),
            completed_at=now - timedelta(hours=12 + i, minutes=-1),
            total_duration_ms=950.0 + i * 30,
            is_synthetic=True,
            metadata_json=json.dumps({"environment": "staging"}),
        )
        ok_steps = [
            _make_step(run_id_ok, 0, "Fetch Config & Build", "parse_requirements", "SUCCESS",
                       {"task": scenario}, {"image": "service:latest"}, 120.0),
            _make_step(run_id_ok, 1, "Pre-flight Check", "select_itinerary", "SUCCESS",
                       {"image": "service:latest"}, {"checks": "passed"}, 90.0),
            _make_step(run_id_ok, 2, "Execute Deployment", tool, "SUCCESS",
                       {"target": "staging"}, {"status": "deployed", "pods": 3}, 680.0),
            _make_step(run_id_ok, 3, "Health Probe", "select_itinerary", "SUCCESS",
                       {"endpoint": "/health"}, {"status": "200 OK"}, 60.0),
        ]
        _add_run_with_steps(db, engine_diag, r_ok, ok_steps,
                            now - timedelta(hours=12 + i))

    # =========================================================================
    # 5. CODE FIXER AGENT — 6 scenarios × 2 variants = 12 + 6 success = 18
    # =========================================================================
    for i, (scenario, tool, fault, error) in enumerate(CODE_SCENARIOS):
        for variant in range(2):
            run_id = f"run_code_{i}_{variant}"
            r = Run(
                id=run_id,
                agent_name="CodeFixer Agent",
                scenario=scenario,
                task_description=f"Detect and fix: {scenario}.",
                status="FAILED",
                started_at=now - timedelta(hours=6 + i + variant),
                completed_at=now - timedelta(hours=6 + i + variant, minutes=-1),
                total_duration_ms=1800.0 + i * 80 + variant * 40,
                error_message=error,
                is_synthetic=True,
                metadata_json=json.dumps({"language": "Python", "variant": variant}),
                ground_truth_suspect_step=tool,
                ground_truth_fault_type=fault,
            )
            steps = _make_code_steps(run_id, scenario, tool, fault, error)
            _add_run_with_steps(db, engine_diag, r, steps,
                                now - timedelta(hours=6 + i + variant))

        run_id_ok = f"run_code_{i}_ok"
        r_ok = Run(
            id=run_id_ok,
            agent_name="CodeFixer Agent",
            scenario=f"{scenario} (Fixed)",
            task_description=f"Detect and fix: {scenario}.",
            status="SUCCESS",
            started_at=now - timedelta(hours=14 + i),
            completed_at=now - timedelta(hours=14 + i, minutes=-1),
            total_duration_ms=1600.0 + i * 60,
            is_synthetic=True,
            metadata_json=json.dumps({"language": "Python", "fixed": True}),
        )
        ok_steps = [
            _make_step(run_id_ok, 0, "Parse Task", "parse_requirements", "SUCCESS",
                       {"task": scenario}, {"parsed": True}, 30.0),
            _make_step(run_id_ok, 1, "Static Analysis", "analyse_code", "SUCCESS",
                       {"task": scenario}, {"warnings": 0, "errors": 0}, 410.0),
            _make_step(run_id_ok, 2, "Code Generation", "generate_code", "SUCCESS",
                       {"spec": scenario}, {"lines": 120, "functions": 8}, 680.0),
            _make_step(run_id_ok, 3, "Run Tests", tool, "SUCCESS",
                       {"test_suite": "unit"}, {"passed": 15, "failed": 0}, 440.0),
            _make_step(run_id_ok, 4, "Generate Report", "select_itinerary", "SUCCESS",
                       {"test_result": "PASSED"}, {"report": "generated"}, 40.0),
        ]
        _add_run_with_steps(db, engine_diag, r_ok, ok_steps,
                            now - timedelta(hours=14 + i))

    # =========================================================================
    # 6. TRADING AGENT — 6 scenarios × 2 variants = 12 + 6 success = 18
    # =========================================================================
    for i, (scenario, tool, fault, error) in enumerate(TRADING_SCENARIOS):
        for variant in range(2):
            run_id = f"run_trading_{i}_{variant}"
            r = Run(
                id=run_id,
                agent_name="TradingAgent v1",
                scenario=scenario,
                task_description=f"Execute algorithmic trading task: {scenario}.",
                status="FAILED",
                started_at=now - timedelta(hours=7 + i + variant),
                completed_at=now - timedelta(hours=7 + i + variant, minutes=-1),
                total_duration_ms=600.0 + i * 40 + variant * 20,
                error_message=error,
                is_synthetic=True,
                metadata_json=json.dumps({"market": "NYSE", "variant": variant}),
                ground_truth_suspect_step=tool,
                ground_truth_fault_type=fault,
            )
            steps = _make_trading_steps(run_id, scenario, tool, fault, error)
            _add_run_with_steps(db, engine_diag, r, steps,
                                now - timedelta(hours=7 + i + variant))

        run_id_ok = f"run_trading_{i}_ok"
        r_ok = Run(
            id=run_id_ok,
            agent_name="TradingAgent v1",
            scenario=f"{scenario} (Executed)",
            task_description=f"Execute algorithmic trading task: {scenario}.",
            status="SUCCESS",
            started_at=now - timedelta(hours=16 + i),
            completed_at=now - timedelta(hours=16 + i, minutes=-1),
            total_duration_ms=480.0 + i * 30,
            is_synthetic=True,
            metadata_json=json.dumps({"market": "NYSE", "executed": True}),
        )
        ok_steps = [
            _make_step(run_id_ok, 0, "Fetch Market Data", "fetch_market_data", "SUCCESS",
                       {"symbols": ["AAPL"]}, {"prices": {"AAPL": 182.3}}, 55.0),
            _make_step(run_id_ok, 1, "Risk Assessment", "risk_check", "SUCCESS",
                       {"portfolio": "P-881"}, {"risk_score": 0.35}, 180.0),
            _make_step(run_id_ok, 2, "Strategy Calculation", "budget_calculation", "SUCCESS",
                       {"strategy": scenario}, {"signal": "BUY", "size": 1000}, 90.0),
            _make_step(run_id_ok, 3, "Execute Trade", tool, "SUCCESS",
                       {"signal": "BUY", "size": 1000}, {"trade_id": f"TRD-{1000+i}", "status": "FILLED"}, 80.0),
            _make_step(run_id_ok, 4, "Compliance Log", "send_confirmation_email", "SUCCESS",
                       {"trade": "complete"}, {"logged": True}, 20.0, side_effect=True),
        ]
        _add_run_with_steps(db, engine_diag, r_ok, ok_steps,
                            now - timedelta(hours=16 + i))

    # =========================================================================
    # 7. BENCHMARK EVALUATION
    # =========================================================================
    db.commit()

    benchmark_data = BenchmarkRunner.run_benchmark()
    db.add(EvaluationBenchmark(
        id="bench_v2_1_official",
        benchmark_name=benchmark_data["benchmark_name"],
        total_cases=benchmark_data["total_cases"],
        top1_accuracy=benchmark_data["models"]["blackbox_hybrid"]["top1_accuracy"],
        top3_accuracy=benchmark_data["models"]["blackbox_hybrid"]["top3_accuracy"],
        mrr=benchmark_data["models"]["blackbox_hybrid"]["mrr"],
        baselines_json=json.dumps(benchmark_data["models"]),
        detailed_results_json=json.dumps(benchmark_data["detailed_cases"]),
        evaluated_at=now,
    ))

    db.commit()
    db.close()

    # Count final rows
    db2 = SessionLocal()
    run_count = db2.query(Run).count()
    db2.close()
    print(f"BLACKBOX synthetic dataset successfully initialized in SQLite.")
    print(f"  Runs seeded  : {run_count}")
    print(f"  Agents       : TravelPlanner, CustomerSupport, DevOpsDeployer, CodeFixer, TradingAgent")
    print(f"  Fault types  : Arithmetic Duplication, Schema Drift, Tool Failure,")
    print(f"                 Constraint Violation, State Drift, Retry Exhaustion,")
    print(f"                 Missing Context, Downstream Propagation, Invalid Model Output")


if __name__ == "__main__":
    seed_database()
