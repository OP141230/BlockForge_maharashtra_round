"""Tests for Replay Engine and Side-Effect Suppression."""
from backend.replay import ReplayEngine, SIDE_EFFECT_TOOLS


def test_side_effect_suppression():
    for tool in ["send_confirmation_email", "make_payment", "book_flight"]:
        out, suppressed, notice = ReplayEngine.execute_mock_tool(tool, {}, {})
        assert suppressed is True
        assert "SIDE EFFECT SUPPRESSED" in notice
        assert out.get("suppressed") is True


def test_replay_counterfactual_fix():
    original_run = {"id": "run_test_01"}
    original_steps = [
        {"id": "s0", "step_index": 0, "step_name": "Req", "tool_name": "parse_requirements", "status": "SUCCESS", "input_data": {}, "output_data": {}},
        {"id": "s1", "step_index": 1, "step_name": "Calc", "tool_name": "budget_calculation", "status": "SUCCESS", "input_data": {}, "output_data": {"total_cost": 2950}},
        {"id": "s2", "step_index": 2, "step_name": "Itin", "tool_name": "select_itinerary", "status": "FAILED", "input_data": {}, "output_data": {}},
        {"id": "s3", "step_index": 3, "step_name": "Email", "tool_name": "send_confirmation_email", "status": "FAILED", "input_data": {}, "output_data": {}},
    ]

    # Intervene by deduplicating input
    modified_input = {
        "deduplicate": True,
        "items": [
            {"category": "Flight", "amount": 750},
            {"category": "Hotel", "amount": 900},
            {"category": "Activities", "amount": 400},
        ],
        "budget_limit": 2500,
    }

    replay_result = ReplayEngine.run_replay(
        original_run,
        original_steps,
        intervention_step_id="s1",
        modified_input=modified_input,
    )

    assert replay_result["replay_status"] == "SUCCESS"
    assert len(replay_result["replayed_steps"]) == 4
    # Check that side-effect tool s3 was suppressed
    assert len(replay_result["suppressed_side_effects"]) > 0
    assert any(s["tool_name"] == "send_confirmation_email" for s in replay_result["suppressed_side_effects"])
    # Check diff summary
    diff_s1 = replay_result["diff_summary"]["s1"]
    assert diff_s1["replayed_output"]["total_cost"] == 2050
