"""The counterfactual search must never use ground-truth labels."""
import copy
import os
import re

from advanced.counterfactual_search import search_fix


def _outcome(report):
    iv = (report.get("successful_attempt") or {}).get("intervention", {})
    return report["fixed"], len(report["attempts"]), iv.get("intervention_type"), iv.get("target_step_name")


def test_search_result_is_identical_without_ground_truth(make_trace, tmp_path):
    trace, base = make_trace("budget_violation", root_cause_step_id=5)
    with_gt = search_fix(trace, traces_dir=base, base_dir=str(tmp_path / "a"))

    stripped = copy.deepcopy(trace)
    stripped.pop("ground_truth", None)
    without_gt = search_fix(stripped, traces_dir=base, base_dir=str(tmp_path / "b"))

    assert _outcome(with_gt) == _outcome(without_gt)


def test_search_path_never_reads_ground_truth():
    """Static check on the label-free path. (Evaluation code and the dataset
    builder read labels on purpose; the search and the features it scores with must not.)"""
    import inspect

    import ml.features as mlf

    root = os.path.dirname(os.path.dirname(__file__))
    sources = {
        rel: open(os.path.join(root, rel), encoding="utf-8").read()
        for rel in ("advanced/counterfactual_search.py", "advanced/interventions.py", "diagnosis/provenance.py")
    }
    sources["ml.features.build_step_features"] = inspect.getsource(mlf.build_step_features)
    for name, text in sources.items():
        assert not re.search(r"ground_truth|failure_type", text), name
