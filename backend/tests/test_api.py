"""Tests for REST API endpoints using FastAPI TestClient."""
from fastapi.testclient import TestClient
from backend.main import app
from backend.seed import seed_database

client = TestClient(app)


def setup_module():
    seed_database()


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "BLACKBOX"
    assert data["status"] == "healthy"


def test_list_runs():
    response = client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert len(data["runs"]) >= 2


def test_get_run_detail():
    response = client.get("/api/runs/run_travel_paris_fail")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "run_travel_paris_fail"
    assert "steps" in data
    assert "diagnosis" in data


def test_get_graph_layout():
    response = client.get("/api/runs/run_travel_paris_fail/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    # Root agent + 7 steps = 8 nodes
    assert len(data["nodes"]) >= 7


def test_replay_endpoint():
    payload = {
        "step_id": "step_tp_3",
        "modified_input": {
            "deduplicate": True,
            "budget_limit": 2500,
            "items": [
                {"category": "Flight", "amount": 750},
                {"category": "Accommodation", "amount": 900},
                {"category": "Activities", "amount": 400},
            ],
        },
    }
    response = client.post("/api/runs/run_travel_paris_fail/replay", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["replay_status"] == "SUCCESS"
    assert len(data["suppressed_side_effects"]) > 0


def test_compare_endpoint():
    response = client.get("/api/runs/run_travel_paris_fail/compare/run_travel_paris_success")
    assert response.status_code == 200
    data = response.json()
    assert data["divergence_found"] is True
    assert data["first_meaningful_divergence"]["step_name"] == "Budget Calculation & Audit"


def test_evaluation_benchmark_endpoint():
    response = client.get("/api/evaluation/benchmark")
    assert response.status_code == 200
    data = response.json()
    assert "top1_accuracy" in data or "models" in data
