"""End-to-end: the counterfactual search must tell injected faults from persistent defects."""
from advanced.counterfactual_search import search_fix


def _winner(report):
    iv = report["successful_attempt"]["intervention"]
    return iv["intervention_type"], iv["target_step_name"]


def test_injected_fault_is_fixed_by_plain_replay(make_trace, tmp_path):
    trace, base = make_trace("budget_violation", root_cause_step_id=5)
    report = search_fix(trace, traces_dir=base, base_dir=str(tmp_path / "r"))
    assert report["fixed"]
    assert _winner(report)[0] == "replay_no_patch"


def test_persistent_defect_survives_plain_replay(make_trace, tmp_path):
    trace, base = make_trace("persistent", 5, defects=["select_reads_unfiltered_list"])
    assert trace["status"] == "failed"
    assert trace["defects"] == ["select_reads_unfiltered_list"]

    report = search_fix(trace, traces_dir=base, base_dir=str(tmp_path / "r"))
    plain = [
        a for a in report["attempts"]
        if a["intervention"]["intervention_type"] == "replay_no_patch"
    ]
    assert plain and not any(a["fixed"] for a in plain)  # replaying alone never works


def test_persistent_defect_is_fixed_by_step_hotfix_at_the_right_step(make_trace, tmp_path):
    trace, base = make_trace("persistent", 5, defects=["select_reads_unfiltered_list"])
    report = search_fix(trace, traces_dir=base, base_dir=str(tmp_path / "r"))
    assert report["fixed"]
    assert _winner(report) == ("disable_step_defect", "select_cheapest_flight")


def test_inverted_hotel_filter_defect_is_fixed(make_trace, tmp_path):
    trace, base = make_trace("persistent", 7, defects=["hotel_filter_inverted"])
    assert trace["status"] == "failed"
    report = search_fix(trace, traces_dir=base, base_dir=str(tmp_path / "r"))
    assert report["fixed"]
    assert _winner(report) == ("disable_step_defect", "filter_hotels_by_checkin")
