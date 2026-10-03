"""Tests for Hybrid Diagnosis Engine, Rule Engine, Anomaly Engine, and Ranker."""
from backend.diagnosis.rules import RuleEngine
from backend.diagnosis.anomaly import AnomalyEngine
from backend.diagnosis.dependencies import DependencyEngine
from backend.diagnosis.historical import HistoricalEngine
from backend.diagnosis.ranker import LearnedRanker
from backend.diagnosis.hybrid import HybridDiagnosisEngine


def test_rule_engine_arithmetic_duplication():
    step = {
        "step_name": "Budget Calculation",
        "tool_name": "budget_calculation",
        "input_data": {"budget_limit": 2500},
        "output_data": {
            "total_cost": 2950,
            "breakdown": [
                {"category": "hotel", "amount": 900},
                {"category": "hotel", "amount": 900},
                {"category": "flight", "amount": 750},
            ],
        },
        "status": "SUCCESS",
    }
    score, rules = RuleEngine.evaluate_step(step, {"budget": 2500})
    assert score >= 0.90
    assert any(r["rule_id"] == "RULE_ARITHMETIC_DUPLICATION" for r in rules)
    assert any(r["rule_id"] == "RULE_BUDGET_OVERFLOW" for r in rules)


def test_anomaly_engine_deviation():
    step = {
        "tool_name": "search_flights",
        "duration_ms": 950.0,  # Mean is ~310ms, std is 65ms -> Z > 9.0
        "output_data": {"status": "ok"},
    }
    score, evidence = AnomalyEngine.evaluate_step(step)
    assert score > 0.60
    assert len(evidence) > 0
    assert any(e["metric"] == "duration_ms" for e in evidence)


def test_dependency_engine_cascade():
    steps = [
        {"id": "s0", "step_index": 0, "step_name": "Start", "tool_name": "init", "status": "SUCCESS"},
        {"id": "s1", "step_index": 1, "step_name": "Faulty", "tool_name": "budget_calculation", "status": "SUCCESS", "is_root_suspect": True},
        {"id": "s2", "step_index": 2, "step_name": "Crash", "tool_name": "select_itinerary", "status": "FAILED", "dependencies": ["s1"]},
    ]
    score, ev = DependencyEngine.evaluate_step(steps[1], steps)
    assert score >= 0.70
    assert ev["downstream_failures"] == 1


def test_historical_pattern_matching():
    engine = HistoricalEngine()
    step = {
        "step_name": "Budget Calculation",
        "tool_name": "budget_calculation",
        "output_data": {"total": 2950, "breakdown": "duplicate hotel accommodation cost overflow"},
    }
    score, matches = engine.evaluate_step(step)
    assert score > 0.30
    assert len(matches) > 0
    assert matches[0]["pattern_id"] == "PAT_ARITHMETIC_DUPLICATION"


def test_hybrid_diagnosis_top_suspect():
    engine = HybridDiagnosisEngine()
    run_dict = {"id": "test_run", "metadata": {"budget": 2500}}
    steps = [
        {"id": "s0", "step_index": 0, "step_name": "Requirements", "tool_name": "parse_requirements", "status": "SUCCESS", "input_data": {}, "output_data": {}, "duration_ms": 40},
        {"id": "s1", "step_index": 1, "step_name": "Flight Search", "tool_name": "search_flights", "status": "SUCCESS", "input_data": {}, "output_data": {"price": 750}, "duration_ms": 310},
        {"id": "s2", "step_index": 2, "step_name": "Hotel Search", "tool_name": "search_accommodations", "status": "SUCCESS", "input_data": {}, "output_data": {"price": 900}, "duration_ms": 290},
        {
            "id": "s3",
            "step_index": 3,
            "step_name": "Budget Calculation",
            "tool_name": "budget_calculation",
            "status": "SUCCESS",
            "input_data": {"budget": 2500},
            "output_data": {
                "total_cost": 2950,
                "breakdown": [{"category": "hotel", "amount": 900}, {"category": "hotel", "amount": 900}],
            },
            "duration_ms": 70,
        },
        {"id": "s4", "step_index": 4, "step_name": "Itinerary Select", "tool_name": "select_itinerary", "status": "FAILED", "error_text": "BudgetExceededError", "input_data": {}, "output_data": {}, "duration_ms": 120},
    ]

    result = engine.diagnose_run(run_dict, steps)
    assert result["suspect_step_id"] == "s3"
    assert result["suspect_step_name"] == "Budget Calculation"
    assert result["suspicion_score"] >= 80.0
    assert result["confidence_label"] == "CRITICAL"
