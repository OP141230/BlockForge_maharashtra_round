"""Tests for TravelPlannerAgent execution and live FlightRecorder hooks."""
from agent.agent import TravelPlannerAgent
from agent.task import sampleTask
from recorder.recorder import FlightRecorder
from backend.database import SessionLocal
from backend.models import Run, Step


def test_travel_planner_agent_buggy_run():
    task = sampleTask()
    recorder = FlightRecorder("TravelPlanner_Test", "Buggy Execution Test")
    agent = TravelPlannerAgent(recorder=recorder)

    result = agent.run_task(task, inject_bug=True)
    assert result["status"] == "FAILED"
    assert "BudgetExceededError" in result["error"]

    db = SessionLocal()
    run = db.query(Run).filter(Run.id == result["run_id"]).first()
    assert run is not None
    assert run.status == "FAILED"
    assert len(run.steps) >= 4
    db.close()


def test_travel_planner_agent_fixed_run():
    task = sampleTask()
    recorder = FlightRecorder("TravelPlanner_Test_Fixed", "Fixed Execution Test")
    agent = TravelPlannerAgent(recorder=recorder)

    result = agent.run_task(task, inject_bug=False)
    assert result["status"] == "SUCCESS"
    assert result["booking"]["status"] == "CONFIRMED"

    db = SessionLocal()
    run = db.query(Run).filter(Run.id == result["run_id"]).first()
    assert run is not None
    assert run.status == "SUCCESS"
    db.close()
