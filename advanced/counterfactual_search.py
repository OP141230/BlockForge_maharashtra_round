import json
import os
from typing import Any, Dict, List, Optional

from diagnosis.spec_engine import evaluate_trace
from ml.features import build_step_features
from replay.engine import load_checkpoint_before_step, run_replay

from advanced.interventions import (
    build_candidate_step_names,
    propose_interventions,
)
from advanced.trace_compare import compare_traces


def _safe_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def load_ranker(model_path: str = "data/models/ranker.json") -> Dict[str, Any]:
    """
    Loads the Phase 4 ranker model.
    """
    if not os.path.exists(model_path):
        return {
            "weights": {},
            "bias": 0.0,
        }

    with open(model_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_intervention_model(model_path: str = "data/models/intervention_model.pkl"):
    """Loads the Phase 7D intervention-outcome model, if present."""
    if not os.path.exists(model_path):
        return None
    try:
        import pickle
        with open(model_path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def _intervention_features(
    trace: Dict[str, Any],
    report: Dict[str, Any],
    intervention: Dict[str, Any],
) -> Dict[str, Any]:
    """Feature vector identical to Phase 7D training schema."""
    trace = _safe_dict(trace)
    report = _safe_dict(report)
    intervention = _safe_dict(intervention)

    earliest = report.get("earliest_step_signal")
    target_id = intervention.get("target_step_id")

    return {
        "intervention_type": intervention.get("intervention_type", "unknown"),
        "target_step_name": intervention.get("target_step_name", "unknown"),
        "target_step_id": float(target_id or 0),
        "num_violations": float(len(report.get("step_violations", []) or [])),
        "earliest_violation_step_id": float(earliest or 0),
        "is_predicted_root": 1.0 if (target_id is not None and target_id == earliest) else 0.0,
    }

def score_features(
    weights: Dict[str, float],
    bias: float,
    features: Dict[str, float],
) -> float:
    score = bias

    for key, value in features.items():
        score += weights.get(key, 0.0) * float(value)

    return float(score)


def score_steps(
    trace: Dict[str, Any],
    report: Dict[str, Any],
    model: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Scores every step in the trace using the Phase 4 ranker.
    """
    trace = _safe_dict(trace)
    report = _safe_dict(report)
    model = _safe_dict(model)

    weights = _safe_dict(model.get("weights"))
    bias = float(model.get("bias", 0.0))

    steps = _safe_list(trace.get("steps"))
    max_steps = len(steps)

    scored_steps: List[Dict[str, Any]] = []

    for step in steps:
        step = _safe_dict(step)

        features = build_step_features(
            trace=trace,
            report=report,
            step=step,
            max_steps=max_steps,
        )

        score = score_features(weights, bias, features)

        scored_steps.append(
            {
                "step_id": step.get("step_id"),
                "name": step.get("name"),
                "score": score,
            }
        )

    scored_steps.sort(
        key=lambda item: (
            -item["score"],
            item["step_id"] if isinstance(item["step_id"], int) else 9999,
        )
    )

    return scored_steps


def search_fix(
    trace: Dict[str, Any],
    traces_dir: str = "data/traces",
    report: Optional[Dict[str, Any]] = None,
    model: Optional[Dict[str, Any]] = None,
    base_dir: str = "data/advanced/replays",
    max_attempts: int = 12,
    model_ordering: bool = False,
) -> Dict[str, Any]:
    """
    Attempts to find a successful counterfactual intervention for a failed trace.

    This does not use ground-truth failure labels.
    """
    trace = _safe_dict(trace)

    if report is None:
        report = evaluate_trace(trace)

    if model is None:
        model = load_ranker()

    scored_steps = score_steps(trace, report, model)

    candidate_step_names = build_candidate_step_names(
        trace=trace,
        report=report,
        scored_steps=scored_steps,
        max_candidates=10,
    )


    interventions = propose_interventions(
        trace=trace,
        candidate_step_names=candidate_step_names,
    )

    # Annotate every intervention with the Phase 7D outcome model's fix probability.
    # By default this does NOT change attempt order (model_ordering=False),
    # so proven 6/6 and 20/20 behaviour is preserved.
    intervention_model = load_intervention_model()
    if intervention_model is not None and interventions:
        try:
            import pandas as pd
            rows = [_intervention_features(trace, report, iv) for iv in interventions]
            probs = intervention_model.predict_proba(pd.DataFrame(rows))[:, 1]
            for iv, p in zip(interventions, probs):
                iv["predicted_fix_probability"] = round(float(p), 4)
            if model_ordering:
                interventions = sorted(
                    interventions,
                    key=lambda x: x.get("predicted_fix_probability", 0.0),
                    reverse=True,
                )
        except Exception:
            pass

    trace_id = trace.get("trace_id")
    trace_dir = os.path.join(traces_dir, str(trace_id))

    attempts: List[Dict[str, Any]] = []
    successful_attempt: Optional[Dict[str, Any]] = None

    for intervention in interventions:
        if len(attempts) >= max_attempts:
            break

        intervention = _safe_dict(intervention)

        target_step_name = intervention.get("target_step_name")
        target_step_id = intervention.get("target_step_id")

        attempt: Dict[str, Any] = {
            "attempt_number": len(attempts) + 1,
            "intervention": intervention,
            "fixed": False,
        }

        try:
            initial_state = load_checkpoint_before_step(
                trace_dir=trace_dir,
                step_id=int(target_step_id),
            )

            replay_trace = run_replay(
                task=trace.get("task", {}),
                initial_state=initial_state,
                start_step_name=target_step_name,
                patches=intervention.get("patch", {}),
                base_dir=base_dir,
                defects=trace.get("defects"),
            )

            replay_status = replay_trace.get("status")

            replay_final_state = _safe_dict(replay_trace.get("final_state"))
            replay_final_validation = _safe_dict(
                replay_final_state.get("final_validation")
            )

            fixed = (
                replay_status == "success"
                and bool(replay_final_validation.get("success"))
            )

            comparison = compare_traces(
                original_trace=trace,
                replay_trace=replay_trace,
                intervention=intervention,
            )

            attempt["replay_trace_id"] = replay_trace.get("trace_id")
            attempt["replay_status"] = replay_status
            attempt["fixed"] = fixed
            attempt["comparison"] = comparison

        except Exception as exc:
            attempt["error"] = str(exc)

        attempt["predicted_fix_probability"] = intervention.get("predicted_fix_probability")
        attempts.append(attempt)

        if attempt.get("fixed") and successful_attempt is None:
            successful_attempt = attempt
            break

    predicted_root = scored_steps[0] if scored_steps else None

    return {
        "trace_id": trace_id,
        "status": trace.get("status"),
        "predicted_root": predicted_root,
        "candidate_step_names": candidate_step_names,
        "attempts": attempts,
        "successful_attempt": successful_attempt,
        "fixed": successful_attempt is not None,
    }