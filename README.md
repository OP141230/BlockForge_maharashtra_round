# BLACKBOX — AI Agent Flight Recorder

> **Continuous flight recording, multi-signal hybrid fault isolation, counterfactual replay with side-effect blocking, and benchmark evaluation studio for autonomous AI agents.**

> ⚠️ All demo data is synthetic, generated entirely by deterministic code and labelled "Synthetic demo data" throughout the UI. No real bookings, payments or personal data are used.

---

## 📎 Presentation & Demo

<!-- Add your hackathon PPT PDF below -->
**Slide Deck (PDF):**
`[Attach PDF here]`

<!-- Add your demo video link below -->
**Demo Video:**
`[Attach demo video link here]`

---

## The Problem

Modern AI agents — travel planners, code fixers, customer support bots — operate as black boxes. When they fail, engineers have no systematic way to answer:

- **What exactly happened** at each step of the execution?
- **Which specific decision** caused the downstream failure?
- **What would have happened** if we had changed that one step?
- **How often does our diagnosis actually find the right root cause?**

---

## The Solution

BLACKBOX is a flight recorder + investigation system for AI agents. It captures every execution step, then provides a structured investigation workflow:

```
WHAT HAPPENED  →  WHERE DID IT DIVERGE  →  WHY IS THAT STEP SUSPICIOUS
      ↓                                              ↓
WHAT EVIDENCE SUPPORTS IT  ←─────────────  HYBRID DIAGNOSIS ENGINE
      ↓
WHAT IF WE CHANGE IT  →  DID THE CHANGE FIX IT  →  HOW ACCURATE IS BLACKBOX
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     BLACKBOX Frontend                         │
│         Next.js 14 · TypeScript · Tailwind CSS               │
│   Overview · Executions · Investigation · Replay Lab          │
│   Comparison · Evaluation Studio · Failure Patterns          │
├──────────────────────────────────────────────────────────────┤
│                    FastAPI REST API                           │
│              /runs  /diagnose  /replay  /compare             │
│              /evaluation  /patterns  /health                 │
├────────────┬─────────────┬────────────┬──────────────────────┤
│   Trace    │  Diagnosis  │   Replay   │     Evaluation       │
│   Engine   │   Engine    │   Engine   │      Studio          │
│            │  5 signals  │ checkpoint │  benchmarks +        │
│  ingestion │  weighted   │ + side-fx  │  baselines +         │
│  storage   │  ensemble   │ blocking   │  MRR / Top-K         │
├────────────┴─────────────┴────────────┴──────────────────────┤
│              SQLite  ·  SQLAlchemy 2  ·  Pydantic v2         │
└──────────────────────────────────────────────────────────────┘
```

---

## Diagnosis Engine — `blackbox-hybrid-v1`

The core of BLACKBOX. Five independent signals are combined into a single **Suspicion Score** (0–100 heuristic rank — not a probability):

| Signal | Weight | Type | What it detects |
|---|---|---|---|
| Rule Match | 30% | Deterministic | Constraint violations, type mismatches, arithmetic duplication, budget overflows |
| Anomaly Signal | 20% | Statistical (z-score) | Duration outliers, payload size spikes, domain cost anomalies |
| Learned Ranker | 20% | Logistic Regression — sklearn, trained at startup | Trained on a programmatically generated labeled corpus (see `ranker.py`) |
| Dependency Impact | 15% | DAG graph traversal | Steps with the most failed downstream descendants rank higher |
| Historical Evidence | 15% | TF-IDF cosine similarity | Match against 8 general-language failure pattern signatures |

Weights are hand-set defaults, stored in `hybrid.py`, and documented in the UI tooltip. The Suspicion Score is a heuristic rank, not a probability — the UI says so explicitly.

### Learned Ranker — honest description

`backend/diagnosis/ranker.py` builds a labeled training corpus **programmatically** from 5 failure templates (~255 events), then trains `sklearn.LogisticRegression` (C=1.0, seed=42). Coefficients come from sklearn — **none are hand-typed constants**. Every API response includes `is_trained`, `train_size`, and `feature_names` so the result is fully inspectable. If training data is too small the ranker disables itself with an explicit notice and the hybrid redistributes its weight.

### Historical Evidence — honest description

Pattern signatures use **general domain language only** — no step or tool names that appear verbatim in the benchmark test cases, preventing trivial keyword leakage. The `observed_in_dataset` count is derived from the live seeded data, not a fabricated constant. If no count is available the field is omitted rather than invented.

---

## Replay Engine — Mode and Limitations

Replay operates in **fixture-propagation / deterministic-registry mode**:

| Step position | What happens | Label surfaced |
|---|---|---|
| Before checkpoint | Original output reused verbatim | `REUSED` |
| Intervention step | Re-executed with modified input | `MODIFIED` |
| After intervention | Re-executed via deterministic registry | `REPLAYED` |
| Side-effect tool | Suppressed, safe mock returned | `BLOCKED` |

This is **not** a live agent restart. The API response includes `replay_mode` and `replay_mode_note` that say exactly this. The experimental evidence note also clarifies: "This replay shows what would have happened under the intervention; it does not constitute formal proof of causality."

Side-effect tools that are always BLOCKED:

| Operation | Replay behaviour |
|---|---|
| `send_email`, `send_confirmation_email` | `BLOCKED — Side effect suppressed` |
| `make_payment`, `book_flight` | `BLOCKED — Side effect suppressed` |
| `deploy_service`, `post_webhook` | `BLOCKED — Side effect suppressed` |

---

## Flagship Demo — TravelPlanner Paris Budget Failure

The demo traces a family trip planner agent booking Paris for 7 days, €2,500 budget.

**The bug:** `budget_calculation` adds accommodation cost twice (€900 + €900), producing a total of €3,300 — €800 over budget — causing `budget_validation`, `itinerary_generation` and `final_response` to fail.

**BLACKBOX isolates `budget_calculation` as the root cause with Suspicion Score 91**, ahead of the first error step and the slowest step, demonstrating that the hybrid engine genuinely outperforms simple heuristics.

---

## Evaluation Studio

Benchmarks run against **15 labeled test cases** (10 TEST + 5 VALIDATION split) with known ground-truth root causes. Design constraints that prevent trivial baselines from winning:

- Root cause is **not** always the first failing step
- Root cause is **not** always the slowest step  
- Root cause is **not** always the last step
- Cases 10–14 are a held-out VALIDATION split — reported separately to check for overfitting
- Learned Ranker training corpus is built from separate templates — **no leakage into test cases**

Actual results on the TEST split (10 cases) after the changes in this commit:

| Model | Top-1 | Top-3 | MRR |
|---|---|---|---|
| **BLACKBOX Hybrid** | run `POST /api/evaluation/run` to see live numbers | — | — |
| Rule-Only | — | — | — |
| Last-Step Heuristic | — | — | — |
| Anomaly-Only | — | — | — |

> Numbers are computed live by the engine — see Evaluation Studio in the UI or `POST /api/evaluation/run`. They are not pre-baked into the README to avoid stale figures.

> **Small benchmark caveat:** 15 cases is modest. Results are illustrative of the approach. Counts are shown alongside percentages throughout the UI.

---

## Pages

| Page | What it does |
|---|---|
| **Overview** | Metric cards (runs, failures, Top-1, MRR), flagship banner, run table |
| **Executions** | Filterable, searchable table of all agent runs |
| **Investigation** | Radial graph + timeline, floating Hybrid Diagnosis panel, event inspector |
| **Replay Lab** | Checkpoint selector, parameter controls, diff viewer, side-effect suppression notices |
| **Comparison** | First meaningful divergence highlighted, aligned step-by-step table |
| **Evaluation Studio** | Benchmark suite, per-model metrics, labelled test cases |
| **Failure Patterns** | TF-IDF pattern catalog with remediation suggestions |

---

## Tech Stack

**Frontend**
- Next.js 14 (App Router), React, TypeScript
- Tailwind CSS, Lucide icons
- Custom SVG radial graph (no external graph library)

**Backend**
- Python 3.11+, FastAPI, Pydantic v2
- SQLAlchemy 2, SQLite (PostgreSQL-ready)
- NumPy, pandas, scikit-learn

---

## Running Locally

### 1. Backend

```bash
# Run from the repo root (BlockForge_maharashtra_round/)
cd BlockForge_maharashtra_round

# Install dependencies  — requirements.txt is in the repo root
python -m pip install -r requirements.txt

# Start the API (seeds the database automatically on first run)
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

> **Why `python -m uvicorn backend.main:app`?**  
> The backend package uses relative imports (`from backend.xxx import …`), so the
> server must be launched from the **repo root** with the module path `backend.main:app`.
> Running `python main.py` from inside the `backend/` folder will raise
> `ModuleNotFoundError: No module named 'backend'`.

API docs → `http://localhost:8000/docs`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

UI → `http://localhost:3000`

### 3. Seed database manually (if needed)

```bash
python -c "from backend.seed import seed_database; seed_database()"
```

This is **idempotent** — safe to run multiple times, no duplicates created.

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `BLACKBOX_DB_PATH` | `backend/blackbox.db` | SQLite database path |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000/api` | Backend API base URL |

No API keys required. BLACKBOX runs fully offline.

---

## Running Tests

```bash
# All 17 backend tests
python -m pytest backend/tests/ -v
```

Test coverage includes: trace validation, all 5 diagnosis rules, anomaly fallback, dependency analysis, historical comparison, replay safety (side-effect suppression), experiment immutability, evaluation metrics, seed idempotency.

---

## Project Structure

```
BlockForge_maharashtra_round/
├── backend/
│   ├── main.py                   # FastAPI app entrypoint
│   ├── api.py                    # All REST routes
│   ├── models.py                 # SQLAlchemy ORM models
│   ├── database.py               # DB session + init
│   ├── seed.py                   # Deterministic demo data
│   ├── replay.py                 # Replay + side-effect engine
│   ├── evaluation.py             # Benchmark runner
│   ├── diagnosis/
│   │   ├── hybrid.py             # 5-signal weighted ensemble
│   │   ├── rules.py              # Deterministic rule engine
│   │   ├── anomaly.py            # Z-score anomaly signals
│   │   ├── dependencies.py       # DAG dependency scoring
│   │   ├── historical.py         # TF-IDF pattern matching
│   │   └── ranker.py             # Logistic regression ranker
│   └── tests/                    # 17 pytest tests
├── frontend/
│   └── src/
│       ├── app/                  # Next.js App Router pages
│       ├── components/           # Sidebar, radial graph, panels
│       └── lib/api.ts            # Typed API client
├── agent/                        # TravelPlanner demo agent
├── recorder/                     # FlightRecorder SDK
└── docs/PLAN.md
```

---

## Known Limitations

- Benchmark has 15 labeled cases (10 test, 5 validation) — results are illustrative, not production-grade
- Anomaly engine uses z-score fallback; Isolation Forest requires ≥30 events per operation key — not reached by the current seed data
- Learned Ranker is trained on a **programmatically generated** synthetic corpus, not real agent production traces. The training and test distributions are similar by construction — real-world accuracy would differ
- Replay operates in fixture-propagation mode (deterministic registry), not live agent restart — clearly documented in the API response and README
- Historical pattern frequency counts reflect the seeded synthetic dataset only

---

*Built for Bit N Build Hackathon — Maharashtra Round*
