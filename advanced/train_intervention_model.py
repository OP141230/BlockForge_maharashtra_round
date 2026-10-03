import os
import sys
import json
import pickle

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from diagnosis.loader import load_traces
from diagnosis.spec_engine import evaluate_trace


def load_attempts(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_features(attempts, traces_map):
    X = []
    y = []

    for attempt in attempts:
        trace_id = attempt.get("trace_id")
        trace = traces_map.get(trace_id)
        if not trace:
            continue

        intervention = attempt.get("intervention", {})
        report = evaluate_trace(trace)

        intervention_type = intervention.get("intervention_type", "unknown")
        target_step_name = intervention.get("target_step_name", "unknown")
        target_step_id = intervention.get("target_step_id", 0)

        num_violations = len(report.get("step_violations", []))
        earliest_violation_step_id = report.get("earliest_step_signal", 0)
        predicted_root_step_id = earliest_violation_step_id
        is_predicted_root = 1 if target_step_id == predicted_root_step_id else 0

        features = {
            "intervention_type": intervention_type,
            "target_step_name": target_step_name,
            "target_step_id": float(target_step_id),
            "num_violations": float(num_violations),
            "earliest_violation_step_id": float(earliest_violation_step_id),
            "is_predicted_root": float(is_predicted_root),
        }

        X.append(features)
        y.append(1 if attempt.get("fixed") else 0)

    return X, y


def main():
    print("Black Box Phase 7D: Intervention Model Training")

    attempts_path = "data/contrastive/intervention_attempts.json"
    if not os.path.exists(attempts_path):
        print(f"Error: {attempts_path} not found. Please run Phase 7C first.")
        return

    attempts = load_attempts(attempts_path)
    if not attempts:
        print("No attempts found in the dataset.")
        return

    traces = load_traces("data/traces")
    traces_map = {t.get("trace_id"): t for t in traces}

    X, y = build_features(attempts, traces_map)

    if not X:
        print("No valid features could be extracted.")
        return

    # Convert list of dictionaries into a proper 2D pandas DataFrame.
    df_X = pd.DataFrame(X)

    print(f"Training on {len(df_X)} samples. Positive class (fixed): {sum(y)}")
    print(f"Features: {list(df_X.columns)}")

    categorical_features = ["intervention_type", "target_step_name"]
    numerical_features = [
        "target_step_id",
        "num_violations",
        "earliest_violation_step_id",
        "is_predicted_root",
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("num", StandardScaler(), numerical_features),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                ),
            ),
        ]
    )

    model.fit(df_X, y)

    train_accuracy = model.score(df_X, y)

    os.makedirs("data/models", exist_ok=True)
    model_path = "data/models/intervention_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print(f"Training accuracy: {train_accuracy:.4f}")
    print(f"Model saved to {model_path}")
    print("Phase 7D completed successfully.")


if __name__ == "__main__":
    main()