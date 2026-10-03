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


def test_ranker_is_trained_not_class_mean(make_trace):
    """The ranker must have a fitted (non-zero) bias and use the causal features."""
    import train_ranker as tr
    from ml.features import FEATURE_NAMES

    traces = []
    for ft, rc in (("wrong_date", 3), ("budget_violation", 5), ("state_overwrite", 9)):
        trace, _ = make_trace(ft, rc)
        traces.append(trace)
    clean, _ = make_trace()
    traces.append(clean)

    weights, bias = tr.train_ranker(traces)
    assert bias != 0.0
    assert set(weights) == set(FEATURE_NAMES)
    assert {"feeds_earliest_violation", "undeclared_state_write"} <= set(FEATURE_NAMES)
    assert any(abs(w) > 0 for w in weights.values())
