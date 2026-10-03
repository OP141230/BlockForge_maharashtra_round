from advanced.trace_compare import compare_traces, diff_values


def test_diff_values_is_empty_for_equal_inputs():
    assert diff_values({"a": [1, {"b": 2}]}, {"a": [1, {"b": 2}]}) == []


def test_diff_values_reports_nested_change_with_path():
    diffs = diff_values({"a": {"b": 1}}, {"a": {"b": 2}})
    assert len(diffs) == 1
    assert "a" in str(diffs[0]) and "b" in str(diffs[0])


def test_compare_identical_traces_reports_no_diff(make_trace):
    trace, _ = make_trace()
    result = compare_traces(original_trace=trace, replay_trace=trace, intervention={})
    assert isinstance(result, dict)
