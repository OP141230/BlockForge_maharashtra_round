"""Synthetic Seed Data Generator for BLACKBOX: AI Agent Flight Recorder.

All data is generated deterministically for reproducible benchmark demonstrations.
Label: Synthetic demo data.
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


def seed_database():
    """Seed synthetic trace runs and benchmark evaluation data."""
    init_db()
    db: Session = SessionLocal()

    # Clear existing data to ensure idempotent deterministic seed
    db.query(DiagnosisResult).delete()
    db.query(Checkpoint).delete()
    db.query(Step).delete()
    db.query(Run).delete()
    db.query(EvaluationBenchmark).delete()
    db.commit()

    engine = HybridDiagnosisEngine()
    now = datetime.now(timezone.utc)

    # =========================================================================
    # 1. FLAGSHIP RUN: TravelPlanner Paris Budget Failure
    # =========================================================================
    run_flagship = Run(
        id="run_travel_paris_fail",
        agent_name="TravelPlanner Agent v2",
        scenario="Paris 7-Day Budget Itinerary",
        task_description="Plan a 7-day budget trip to Paris for 1 traveler under $2,500 with central hotel and booked flights.",
        status="FAILED",
        started_at=now - timedelta(minutes=15),
        completed_at=now - timedelta(minutes=14, seconds=42),
        total_duration_ms=1045.0,
        error_message="BudgetExceededError: Calculated total trip expenditure $2,950.00 exceeds configured budget limit of $2,500.00.",
        is_synthetic=True,
        metadata_json=json.dumps({
            "destination": "Paris, France",
            "duration_days": 7,
            "budget": 2500,
            "flight_class": "Economy",
            "hotel_rating": "3-Star Central",
            "environment": "Production-Agent-V2",
        }),
        ground_truth_suspect_step="budget_calculation",
        ground_truth_fault_type="Arithmetic Duplication",
    )
    db.add(run_flagship)

    steps_flagship_data = [
        {
            "id": "step_tp_0",
            "run_id": "run_travel_paris_fail",
            "step_index": 0,
            "step_name": "Requirements Parsing",
            "tool_name": "parse_requirements",
            "input_data_json": json.dumps({"prompt": "Plan a 7-day budget trip to Paris under $2500"}),
            "output_data_json": json.dumps({
                "destination": "Paris",
                "duration_days": 7,
                "budget_limit": 2500,
                "constraints": ["central", "wifi"],
            }),
            "duration_ms": 42.0,
            "status": "SUCCESS",
            "side_effect_flag": False,
            "is_root_suspect": False,
            "is_downstream_impact": False,
            "dependencies_json": json.dumps([]),
        },
        {
            "id": "step_tp_1",
            "run_id": "run_travel_paris_fail",
            "step_index": 1,
            "step_name": "Flight Discovery",
            "tool_name": "search_flights",
            "input_data_json": json.dumps({"origin": "JFK", "destination": "CDG", "date": "2026-10-10"}),
            "output_data_json": json.dumps({
                "flights": [
                    {"flight_id": "AF-104", "origin": "JFK", "destination": "CDG", "price": 750, "arrival_time": "14:30"},
                    {"flight_id": "DL-202", "origin": "JFK", "destination": "CDG", "price": 880, "arrival_time": "17:15"},
                ],
                "selected_flight": {"flight_id": "AF-104", "price": 750, "arrival_time": "14:30"},
            }),
            "duration_ms": 312.0,
            "status": "SUCCESS",
            "side_effect_flag": False,
            "is_root_suspect": False,
            "is_downstream_impact": False,
            "dependencies_json": json.dumps(["step_tp_0"]),
        },
        {
            "id": "step_tp_2",
            "run_id": "run_travel_paris_fail",
            "step_index": 2,
            "step_name": "Accommodation Search",
            "tool_name": "search_accommodations",
            "input_data_json": json.dumps({"city": "Paris", "nights": 6, "max_nightly": 160}),
            "output_data_json": json.dumps({
                "accommodations": [
                    {"hotel_id": "HTL-PAR-01", "name": "Hotel Le Marais", "price_total": 900, "checkin_time": "15:00"},
                    {"hotel_id": "HTL-PAR-02", "name": "Boutique Seine", "price_total": 1150, "checkin_time": "14:00"},
                ],
                "selected_hotel": {"hotel_id": "HTL-PAR-01", "name": "Hotel Le Marais", "price_total": 900, "checkin_time": "15:00"},
            }),
            "duration_ms": 288.0,
            "status": "SUCCESS",
            "side_effect_flag": False,
            "is_root_suspect": False,
            "is_downstream_impact": False,
            "dependencies_json": json.dumps(["step_tp_0"]),
        },
        {
            "id": "step_tp_3",
            "run_id": "run_travel_paris_fail",
            "step_index": 3,
            "step_name": "Budget Calculation & Audit",
            "tool_name": "budget_calculation",
            "input_data_json": json.dumps({
                "flight_cost": 750,
                "hotel_cost": 900,
                "activities_cost": 400,
                "budget_limit": 2500,
            }),
            # BUG: Hotel cost duplicated twice in breakdown list ($750 + $900 + $900 + $400 = $2950)
            "output_data_json": json.dumps({
                "total_cost": 2950,
                "budget_limit": 2500,
                "calculation_status": "OVERFLOW",
                "breakdown": [
                    {"category": "Flight (AF-104)", "amount": 750},
                    {"category": "Accommodation (Hotel Le Marais)", "amount": 900},
                    {"category": "Accommodation (Hotel Le Marais)", "amount": 900},
                    {"category": "Activities & Transit", "amount": 400},
                ],
            }),
            "duration_ms": 68.0,
            "status": "SUCCESS",  # Returned normally but contained fatal logic flaw
            "side_effect_flag": False,
            "is_root_suspect": True,
            "is_downstream_impact": False,
            "suspicion_score": 91.2,
            "dependencies_json": json.dumps(["step_tp_1", "step_tp_2"]),
        },
        {
            "id": "step_tp_4",
            "run_id": "run_travel_paris_fail",
            "step_index": 4,
            "step_name": "Itinerary Verification",
            "tool_name": "select_itinerary",
            "input_data_json": json.dumps({"total_allocated": 2950, "budget_limit": 2500}),
            "output_data_json": json.dumps({"error": "BudgetExceededError: $2950 exceeds max threshold $2500"}),
            "duration_ms": 142.0,
            "status": "FAILED",
            "error_text": "BudgetExceededError: $2950 exceeds max threshold $2500",
            "side_effect_flag": False,
            "is_root_suspect": False,
            "is_downstream_impact": True,
            "suspicion_score": 38.0,
            "dependencies_json": json.dumps(["step_tp_3"]),
        },
        {
            "id": "step_tp_5",
            "run_id": "run_travel_paris_fail",
            "step_index": 5,
            "step_name": "Booking Finalization",
            "tool_name": "finalize_booking",
            "input_data_json": json.dumps({"itinerary_confirmed": False}),
            "output_data_json": json.dumps({"error": "PipelineAborted: Upstream validation failure"}),
            "duration_ms": 22.0,
            "status": "FAILED",
            "error_text": "PipelineAborted: Upstream validation failure",
            "side_effect_flag": True,
            "is_root_suspect": False,
            "is_downstream_impact": True,
            "suspicion_score": 25.0,
            "dependencies_json": json.dumps(["step_tp_4"]),
        },
        {
            "id": "step_tp_6",
            "run_id": "run_travel_paris_fail",
            "step_index": 6,
            "step_name": "Send Confirmation Email",
            "tool_name": "send_confirmation_email",
            "input_data_json": json.dumps({"recipient": "traveler@example.com", "status": "ABORTED"}),
            "output_data_json": json.dumps({"status": "NOT_SENT"}),
            "duration_ms": 15.0,
            "status": "FAILED",
            "error_text": "ExecutionSuppressed: Prior failure",
            "side_effect_flag": True,
            "is_root_suspect": False,
            "is_downstream_impact": True,
            "suspicion_score": 14.0,
            "dependencies_json": json.dumps(["step_tp_5"]),
        },
    ]

    for sd in steps_flagship_data:
        step_obj = Step(**sd)
        db.add(step_obj)

    # Checkpoints for flagship run
    for s in steps_flagship_data:
        cp = Checkpoint(
            id=f"cp_{s['id']}",
            run_id="run_travel_paris_fail",
            step_id=s["id"],
            step_index=s["step_index"],
            agent_state_json=json.dumps({"current_step": s["step_name"], "status": s["status"]}),
            memory_state_json=json.dumps({"budget_limit": 2500, "accumulated_cost": 2950 if s["step_index"] >= 3 else 750}),
            timestamp=now - timedelta(minutes=15 - s["step_index"]),
        )
        db.add(cp)

    # Flagship Run Hybrid Diagnosis
    flagship_run_dict = run_flagship.to_dict()
    diag_res = engine.diagnose_run(flagship_run_dict, [
        {
            "id": s["id"],
            "step_index": s["step_index"],
            "step_name": s["step_name"],
            "tool_name": s["tool_name"],
            "status": s["status"],
            "input_data": json.loads(s["input_data_json"]),
            "output_data": json.loads(s["output_data_json"]),
            "duration_ms": s["duration_ms"],
            "error_text": s.get("error_text"),
            "dependencies": json.loads(s["dependencies_json"]),
            "is_root_suspect": s["is_root_suspect"],
        }
        for s in steps_flagship_data
    ])

    diagnosis_entry = DiagnosisResult(
        id="diag_run_travel_paris_fail",
        run_id="run_travel_paris_fail",
        suspect_step_id=diag_res["suspect_step_id"],
        suspect_step_name=diag_res["suspect_step_name"],
        suspicion_score=diag_res["suspicion_score"],
        rule_score=diag_res["top_signals"]["rule_match"],
        anomaly_score=diag_res["top_signals"]["anomaly_signal"],
        ranker_score=diag_res["top_signals"]["learned_ranker"],
        dependency_score=diag_res["top_signals"]["dependency_impact"],
        historical_score=diag_res["top_signals"]["historical_evidence"],
        confidence_label=diag_res["confidence_label"],
        explanation_text=diag_res["explanation_text"],
        evidence_items_json=json.dumps(diag_res["top_evidence"]),
        breakdown_json=json.dumps(diag_res),
        created_at=now - timedelta(minutes=14),
    )
    db.add(diagnosis_entry)

    # =========================================================================
    # 2. BASELINE SUCCESS RUN: Reference Run for Divergence Comparison
    # =========================================================================
    run_success = Run(
        id="run_travel_paris_success",
        agent_name="TravelPlanner Agent v2",
        scenario="Paris 7-Day Budget Itinerary (Baseline Success)",
        task_description="Plan a 7-day budget trip to Paris for 1 traveler under $2,500 with central hotel and booked flights.",
        status="SUCCESS",
        started_at=now - timedelta(hours=2),
        completed_at=now - timedelta(hours=2, minutes=-1),
        total_duration_ms=980.0,
        error_message=None,
        is_synthetic=True,
        metadata_json=json.dumps({
            "destination": "Paris, France",
            "duration_days": 7,
            "budget": 2500,
            "flight_class": "Economy",
            "hotel_rating": "3-Star Central",
        }),
    )
    db.add(run_success)

    steps_success_data = [
        {
            "id": "step_tps_0",
            "run_id": "run_travel_paris_success",
            "step_index": 0,
            "step_name": "Requirements Parsing",
            "tool_name": "parse_requirements",
            "input_data_json": json.dumps({"prompt": "Plan a 7-day budget trip to Paris under $2500"}),
            "output_data_json": json.dumps({
                "destination": "Paris",
                "duration_days": 7,
                "budget_limit": 2500,
                "constraints": ["central", "wifi"],
            }),
            "duration_ms": 40.0,
            "status": "SUCCESS",
        },
        {
            "id": "step_tps_1",
            "run_id": "run_travel_paris_success",
            "step_index": 1,
            "step_name": "Flight Discovery",
            "tool_name": "search_flights",
            "input_data_json": json.dumps({"origin": "JFK", "destination": "CDG", "date": "2026-10-10"}),
            "output_data_json": json.dumps({
                "flights": [
                    {"flight_id": "AF-104", "origin": "JFK", "destination": "CDG", "price": 750, "arrival_time": "14:30"},
                    {"flight_id": "DL-202", "origin": "JFK", "destination": "CDG", "price": 880, "arrival_time": "17:15"},
                ],
                "selected_flight": {"flight_id": "AF-104", "price": 750, "arrival_time": "14:30"},
            }),
            "duration_ms": 305.0,
            "status": "SUCCESS",
        },
        {
            "id": "step_tps_2",
            "run_id": "run_travel_paris_success",
            "step_index": 2,
            "step_name": "Accommodation Search",
            "tool_name": "search_accommodations",
            "input_data_json": json.dumps({"city": "Paris", "nights": 6, "max_nightly": 160}),
            "output_data_json": json.dumps({
                "accommodations": [
                    {"hotel_id": "HTL-PAR-01", "name": "Hotel Le Marais", "price_total": 900, "checkin_time": "15:00"},
                    {"hotel_id": "HTL-PAR-02", "name": "Boutique Seine", "price_total": 1150, "checkin_time": "14:00"},
                ],
                "selected_hotel": {"hotel_id": "HTL-PAR-01", "name": "Hotel Le Marais", "price_total": 900, "checkin_time": "15:00"},
            }),
            "duration_ms": 280.0,
            "status": "SUCCESS",
        },
        {
            "id": "step_tps_3",
            "run_id": "run_travel_paris_success",
            "step_index": 3,
            "step_name": "Budget Calculation & Audit",
            "tool_name": "budget_calculation",
            "input_data_json": json.dumps({
                "flight_cost": 750,
                "hotel_cost": 900,
                "activities_cost": 400,
                "budget_limit": 2500,
            }),
            "output_data_json": json.dumps({
                "total_cost": 2050,
                "budget_limit": 2500,
                "calculation_status": "WITHIN_BUDGET",
                "breakdown": [
                    {"category": "Flight (AF-104)", "amount": 750},
                    {"category": "Accommodation (Hotel Le Marais)", "amount": 900},
                    {"category": "Activities & Transit", "amount": 400},
                ],
            }),
            "duration_ms": 62.0,
            "status": "SUCCESS",
        },
        {
            "id": "step_tps_4",
            "run_id": "run_travel_paris_success",
            "step_index": 4,
            "step_name": "Itinerary Verification",
            "tool_name": "select_itinerary",
            "input_data_json": json.dumps({"total_allocated": 2050, "budget_limit": 2500}),
            "output_data_json": json.dumps({
                "itinerary_id": "ITIN-PARIS-OPTIMAL",
                "status": "CONFIRMED",
                "days_count": 7,
                "allocated_budget": 2050,
            }),
            "duration_ms": 138.0,
            "status": "SUCCESS",
        },
        {
            "id": "step_tps_5",
            "run_id": "run_travel_paris_success",
            "step_index": 5,
            "step_name": "Booking Finalization",
            "tool_name": "finalize_booking",
            "input_data_json": json.dumps({"itinerary_confirmed": True}),
            "output_data_json": json.dumps({
                "booking_reference": "BKG-774912",
                "booking_status": "COMPLETED",
                "total_charged": 2050,
            }),
            "duration_ms": 195.0,
            "status": "SUCCESS",
        },
        {
            "id": "step_tps_6",
            "run_id": "run_travel_paris_success",
            "step_index": 6,
            "step_name": "Send Confirmation Email",
            "tool_name": "send_confirmation_email",
            "input_data_json": json.dumps({"booking_ref": "BKG-774912"}),
            "output_data_json": json.dumps({"email_sent": True, "message_id": "MSG-88412"}),
            "duration_ms": 160.0,
            "status": "SUCCESS",
            "side_effect_flag": True,
        },
    ]
    for s in steps_success_data:
        db.add(Step(**s))

    # =========================================================================
    # 3. MORE DIVERSE REALISTIC RUNS
    # =========================================================================
    additional_runs = [
        {
            "id": "run_support_schema_drift",
            "agent_name": "CustomerSupport Agent",
            "scenario": "Billing Dispute Resolution",
            "task_description": "Lookup customer subscription state and process refund for erroneous charge.",
            "status": "FAILED",
            "total_duration_ms": 620.0,
            "error_message": "KeyError: 'customer_guid' missing from response payload.",
            "ground_truth_suspect_step": "database_query",
            "ground_truth_fault_type": "Schema Drift",
            "steps": [
                {"id": "s_cs_0", "step_index": 0, "step_name": "Parse Ticket", "tool_name": "parse_requirements", "status": "SUCCESS", "output_data": {"ticket_id": "TCK-881"}, "duration_ms": 35.0},
                {"id": "s_cs_1", "step_index": 1, "step_name": "Query Database", "tool_name": "database_query", "status": "SUCCESS", "output_data": {"user_id": 991, "migrated_schema": True}, "duration_ms": 88.0, "is_root_suspect": True, "suspicion_score": 86.4},
                {"id": "s_cs_2", "step_index": 2, "step_name": "Authorize Refund", "tool_name": "finalize_booking", "status": "FAILED", "error_text": "KeyError: 'customer_guid'", "output_data": {"error": "KeyError"}, "duration_ms": 45.0, "is_downstream_impact": True, "suspicion_score": 32.0},
            ],
        },
        {
            "id": "run_devops_port_conflict",
            "agent_name": "DevOpsDeployer Agent",
            "scenario": "Microservice Container Rollout",
            "task_description": "Build and spin up auth-service container on internal port 8080.",
            "status": "FAILED",
            "total_duration_ms": 1450.0,
            "error_message": "BindException: Address already in use 0.0.0.0:8080.",
            "ground_truth_suspect_step": "deploy_service",
            "ground_truth_fault_type": "Port Collision",
            "steps": [
                {"id": "s_do_0", "step_index": 0, "step_name": "Fetch Repo & Build", "tool_name": "parse_requirements", "status": "SUCCESS", "output_data": {"image": "auth:v1.4"}, "duration_ms": 120.0},
                {"id": "s_do_1", "step_index": 1, "step_name": "Deploy Container", "tool_name": "deploy_service", "status": "FAILED", "error_text": "BindException: Address 0.0.0.0:8080 already in use", "output_data": {"error": "PortConflict"}, "duration_ms": 1180.0, "is_root_suspect": True, "suspicion_score": 94.5},
                {"id": "s_do_2", "step_index": 2, "step_name": "Probe Health Check", "tool_name": "select_itinerary", "status": "FAILED", "error_text": "ConnectionRefused: probe failed", "output_data": {}, "duration_ms": 150.0, "is_downstream_impact": True, "suspicion_score": 28.0},
            ],
        },
    ]

    for ar in additional_runs:
        r_obj = Run(
            id=ar["id"],
            agent_name=ar["agent_name"],
            scenario=ar["scenario"],
            task_description=ar["task_description"],
            status=ar["status"],
            started_at=now - timedelta(hours=1),
            completed_at=now - timedelta(hours=1, minutes=-1),
            total_duration_ms=ar["total_duration_ms"],
            error_message=ar["error_message"],
            is_synthetic=True,
            ground_truth_suspect_step=ar["ground_truth_suspect_step"],
            ground_truth_fault_type=ar["ground_truth_fault_type"],
        )
        db.add(r_obj)

        step_dicts = []
        for s in ar["steps"]:
            st_obj = Step(
                id=s["id"],
                run_id=ar["id"],
                step_index=s["step_index"],
                step_name=s["step_name"],
                tool_name=s["tool_name"],
                input_data_json=json.dumps(s.get("input_data", {})),
                output_data_json=json.dumps(s.get("output_data", {})),
                duration_ms=s.get("duration_ms", 50.0),
                status=s.get("status", "SUCCESS"),
                error_text=s.get("error_text"),
                is_root_suspect=s.get("is_root_suspect", False),
                is_downstream_impact=s.get("is_downstream_impact", False),
                suspicion_score=s.get("suspicion_score", 0.0),
            )
            db.add(st_obj)
            step_dicts.append({
                "id": s["id"],
                "step_index": s["step_index"],
                "step_name": s["step_name"],
                "tool_name": s["tool_name"],
                "status": s.get("status", "SUCCESS"),
                "input_data": s.get("input_data", {}),
                "output_data": s.get("output_data", {}),
                "duration_ms": s.get("duration_ms", 50.0),
                "error_text": s.get("error_text"),
                "is_root_suspect": s.get("is_root_suspect", False),
            })

        # Run diagnosis for additional run
        ar_diag = engine.diagnose_run(r_obj.to_dict(), step_dicts)
        diag_rec = DiagnosisResult(
            id=f"diag_{ar['id']}",
            run_id=ar["id"],
            suspect_step_id=ar_diag["suspect_step_id"] or s["id"],
            suspect_step_name=ar_diag["suspect_step_name"],
            suspicion_score=ar_diag["suspicion_score"],
            rule_score=ar_diag["top_signals"]["rule_match"],
            anomaly_score=ar_diag["top_signals"]["anomaly_signal"],
            ranker_score=ar_diag["top_signals"]["learned_ranker"],
            dependency_score=ar_diag["top_signals"]["dependency_impact"],
            historical_score=ar_diag["top_signals"]["historical_evidence"],
            confidence_label=ar_diag["confidence_label"],
            explanation_text=ar_diag["explanation_text"],
            evidence_items_json=json.dumps(ar_diag["top_evidence"]),
            breakdown_json=json.dumps(ar_diag),
            created_at=now - timedelta(hours=1),
        )
        db.add(diag_rec)

    # =========================================================================
    # 4. BENCHMARK EVALUATION INITIALIZATION
    # =========================================================================
    benchmark_data = BenchmarkRunner.run_benchmark()
    b_obj = EvaluationBenchmark(
        id="bench_v2_1_official",
        benchmark_name=benchmark_data["benchmark_name"],
        total_cases=benchmark_data["total_cases"],
        top1_accuracy=benchmark_data["models"]["blackbox_hybrid"]["top1_accuracy"],
        top3_accuracy=benchmark_data["models"]["blackbox_hybrid"]["top3_accuracy"],
        mrr=benchmark_data["models"]["blackbox_hybrid"]["mrr"],
        baselines_json=json.dumps(benchmark_data["models"]),
        detailed_results_json=json.dumps(benchmark_data["detailed_cases"]),
        evaluated_at=now,
    )
    db.add(b_obj)

    db.commit()
    db.close()
    print("BLACKBOX synthetic dataset successfully initialized in SQLite.")


if __name__ == "__main__":
    seed_database()
