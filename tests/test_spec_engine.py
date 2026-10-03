from diagnosis.spec_engine import evaluate_trace


def test_clean_trace_has_no_violations(make_trace):
    trace, _ = make_trace()
    report = evaluate_trace(trace)
    assert not report["step_violations"]
    assert not report["final_violations"]
    assert report["earliest_step_signal"] is None


def test_wrong_date_is_flagged_at_search_flights(make_trace):
    trace, _ = make_trace("wrong_date", root_cause_step_id=3)
    report = evaluate_trace(trace)
    assert trace["status"] == "failed"
    assert report["earliest_step_signal"] == 3


def test_budget_violation_is_flagged_at_selection_step(make_trace):
    trace, _ = make_trace("budget_violation", root_cause_step_id=5)
    assert evaluate_trace(trace)["earliest_step_signal"] == 5


def test_state_overwrite_is_flagged_at_create_booking(make_trace):
    trace, _ = make_trace("state_overwrite", root_cause_step_id=9)
    assert evaluate_trace(trace)["earliest_step_signal"] == 9
