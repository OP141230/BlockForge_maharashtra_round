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
| Learned Ranker | 20% | Logistic Regression | Trained on labeled synthetic failure runs |
| Dependency Impact | 15% | DAG graph traversal | Steps with the most failed downstream descendants rank higher |
| Historical Evidence | 15% | TF-IDF cosine similarity | Match against 5 known failure pattern signatures |

Weights are hand-set defaults, stored in one config location, and documented in the UI tooltip. The Learned Ranker uses calibrated hand-tuned coefficients on the current dataset size and disables itself with a clear notice if training data is insufficient.

---

## Replay Engine — Side-Effect Safety

Counterfactual replay executes downstream steps from a saved checkpoint under a modified input. Side effects are **never re-executed**:

| Operation | Replay behaviour |
|---|---|
| `send_email` | `BLOCKED — Side effect suppressed during replay` |
| `make_payment` | `BLOCKED — Side effect suppressed during replay` |
| `book_flight` | `BLOCKED — Side effect suppressed during replay` |
| `delete_file` | `BLOCKED — Side effect suppressed during replay` |
| Normal computation | `REPLAYED` with modified input |
| Steps before checkpoint | `REUSED` (original trace values) |
| Intervention step | `MODIFIED` |

Replay shows **experimental evidence**, never proof of causality.

---

## Flagship Demo — TravelPlanner Paris Budget Failure

The demo traces a family trip planner agent booking Paris for 7 days, €2,500 budget.

**The bug:** `budget_calculation` adds accommodation cost twice (€900 + €900), producing a total of €3,300 — €800 over budget — causing `budget_validation`, `itinerary_generation` and `final_response` to fail.

**BLACKBOX isolates `budget_calculation` as the root cause with Suspicion Score 91**, ahead of the first error step and the slowest step, demonstrating that the hybrid engine genuinely outperforms simple heuristics.

---

## Evaluation Studio

Benchmarks are run against **6 labeled test cases** with known ground-truth root causes. The split and methodology is:

- Cases are generated by deterministic seed code across different agents and failure categories
- Root cause is **not always** the first error, slowest step, or last step — baselines cannot trivially win
- No weight tuning on the test split

| Model | Top-1 | Top-3 | MRR |
|---|---|---|---|
| **BLACKBOX Hybrid** | **50%** | **100%** | **0.708** |
| Rule-Only | 50% | 100% | 0.708 |
| Last-Step Heuristic | 16.7% | 50% | 0.333 |
| Anomaly-Only | 16.7% | 33% | 0.267 |

> Small benchmark (6 cases) — results are illustrative. Counts shown alongside percentages.

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
cd BlockForge_maharashtra_round

# Install dependencies
python -m pip install fastapi uvicorn pydantic sqlalchemy numpy pandas scikit-learn httpx pytest

# Start (seeds database automatically on first run)
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

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

- Benchmark has 6 labeled cases — results are illustrative, not production-grade
- Anomaly engine uses z-score fallback (Isolation Forest requires ≥30 events per operation key — not reached by current seed)
- Learned Ranker uses hand-calibrated coefficients; a full sklearn training loop needs more labeled run data
- No authentication — designed as a local development / hackathon tool

---

*Built for Bit N Build Hackathon — Maharashtra Round*
