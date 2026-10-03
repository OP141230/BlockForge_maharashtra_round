# BLACKBOX Build Plan

## Phase 1 – Foundation
- Verify branch om ✓. Scaffold backend (FastAPI+SQLite) and frontend (Next.js).
- .gitignore update, requirements.txt, package.json.

## Phase 2 – Trace System & Data Model
- SQLAlchemy models: Run, Step, Checkpoint. Seed TravelPlanner scenario.
- Deterministic synthetic data generator with budget_calculation duplication bug.
- REST API: /runs, /runs/{id}, /runs/{id}/steps, /runs/{id}/diagnosis.

## Phase 3 – Diagnosis Engine
- Rule engine (constraint violations, type mismatches, budget overflows).
- Anomaly signals (z-score on duration/output size vs historical).
- Learned ranker (sklearn logistic regression on feature vector).
- Dependency impact analysis (downstream failure propagation).
- Historical comparison (cosine similarity to known failures).
- Hybrid score combiner → Suspicion Score (heuristic, not probability).

## Phase 4 – Replay Lab
- Checkpoint creation per step. Re-execute with intervention.
- Side-effect suppression (send_email, make_payment, book_flight blocked).
- Diff view of original vs replayed outputs.

## Phase 5 – Frontend (Light Holographic UI)
- Sidebar: BLACKBOX logo + nav. Radial React Flow graph canvas.
- Floating diagnosis glassmorphism panel. Timeline view.
- Replay Lab page. Comparison page. Evaluation Studio.

## Phase 6 – Evaluation Studio
- Benchmark runner: labeled failures with ground truth root cause.
- Metrics: Top-1, Top-3, MRR for baseline vs BLACKBOX hybrid.

## Phase 7 – QA, tests, final commit.
