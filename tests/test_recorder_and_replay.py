import json
import os

import pytest

from replay.engine import get_replay_config, load_checkpoint_before_step, run_replay


def test_clean_run_succeeds_and_records_every_step(make_trace):
    trace, _ = make_trace()
    assert trace["status"] == "success"
    assert len(trace["steps"]) == 11
    assert [s["step_id"] for s in trace["steps"]] == list(range(1, 12))


def test_checkpoints_are_enveloped_and_cover_initial_state(make_trace):
    trace, base = make_trace()
    ckpt_dir = os.path.join(base, trace["trace_id"], "checkpoints")
    files = sorted(os.listdir(ckpt_dir))
    assert files[0] == "step_000.json" and len(files) == 12
    with open(os.path.join(ckpt_dir, "step_003.json"), encoding="utf-8") as f:
        payload = json.load(f)
    assert set(payload) == {"trace_id", "step_id", "step_name", "state"}
    assert payload["step_name"] == "search_flights"


def test_load_checkpoint_is_strictly_before_target_step(make_trace):
    trace, base = make_trace()
    trace_dir = os.path.join(base, trace["trace_id"])
    state = load_checkpoint_before_step(trace_dir, step_id=3)
    # state after step 2 (extract_constraints): constraints exist, flights do not
    assert "constraints" in state and "flights" not in state


def test_load_checkpoint_raises_when_nothing_precedes(make_trace):
    trace, base = make_trace()
    with pytest.raises(FileNotFoundError):
        load_checkpoint_before_step(os.path.join(base, trace["trace_id"]), step_id=0)


def test_replay_reuses_prefix_and_fixes_injected_fault(make_trace, task, tmp_path):
    trace, base = make_trace("budget_violation", root_cause_step_id=5)
    assert trace["status"] == "failed"

    cfg = get_replay_config("budget_violation", task)
    state = load_checkpoint_before_step(os.path.join(base, trace["trace_id"]), 5)
    replay = run_replay(
        task=task,
        initial_state=state,
        start_step_name=cfg["start_step_name"],
        patches=cfg["patches"],
        base_dir=str(tmp_path / "replays"),
    )
    assert replay["status"] == "success"
    assert len(replay["steps"]) == 7  # steps 5..11 only; 1..4 were reused


def test_replay_config_for_wrong_date_restores_task_date(task):
    cfg = get_replay_config("wrong_date", task)
    assert cfg["start_step_name"] == "search_flights"
    assert cfg["patches"]["search_flights"]["state_override"]["constraints"]["date"] == task["date"]


def test_unknown_failure_type_replays_from_the_start(task):
    assert get_replay_config("nope", task) == {"start_step_name": "parse_request", "patches": {}}
