# Black Box — a flight recorder for AI agents

GDG On Campus internal round submission, AI/ML track, problem statement 2.

Black Box debugs AI agent executions. It records everything an agent does
(inputs, outputs, state mutations, latency, a state checkpoint after every
step), locates the step that caused a failure, shows the evidence behind that
claim, and then proves it: the suspected step is patched and the run is
replayed from the saved checkpoint. If the replayed execution succeeds, the
diagnosis is confirmed by execution rather than by opinion.

The demo agent is an 11-step travel booking agent running on deterministic
mock tools. Failures are injected faults (wrong dates, budget violations,
hallucinated tool results, overwritten state, bypassed filters). Everything
downstream of the recorder only consumes the trace format, so the diagnosis
and replay machinery is not tied to this particular agent.

No LLM is used anywhere in the diagnosis loop. Diagnosis is deterministic
invariant checking plus small trained models. An LLM could narrate the
output, but it never decides anything.

## Coverage of the brief

- Execution data: per-step traces with state checkpoints (`recorder/`)
- Failure diagnosis: invariant spec engine + causal provenance slicing +
  trained step ranker (`diagnosis/`, `ml/`)
- Failure explanation: post-mortem narrative, suspicion gauge, and
  per-feature confidence contributions in the UI
- Checkpointed replay: restore any checkpoint, re-execute downstream stages
  only (`replay/`)
- Alternative execution: generic intervention proposals, each validated by
  actually replaying (`advanced/`)
- Model evaluation: held-out test split plus zero-shot evaluation on unseen
  fault families; metrics surfaced in the UI
- Trace comparison: recursive diff of two executions, original vs replayed
  (`advanced/trace_compare.py`)

## Setup

```
pip install -r requirements.txt
```

Python 3.10+. The backend core (recording, spec engine, provenance, replay,
search) is standard library only. scikit-learn and pandas are used for the
intervention model and UI metrics. Streamlit serves the dashboard. The graph
widget pulls vis-network from a CDN, so the UI needs internet on first load.

## Running the pipeline

One command runs everything (from any directory) and stops at the first failure.
Add `--tests` to run the pytest suite at the end:

```
python run_all.py
python run_all.py --tests
```

For tests alone: `pip install -r requirements-dev.txt && python -m pytest`.
CI (`.github/workflows/ci.yml`) runs both on every push.

Every script also validates its own output and exits non-zero on failure, so
the chain can be run step by step:

```
python main.py                          # one clean run
python generate_dataset.py              # 7 labelled traces -> data/traces
python diagnose.py                      # spec engine detection report
python generate_training_dataset.py     # 70 train / 28 test traces
python train_ranker.py                  # suspicion ranker -> data/models/ranker.json
python replay_and_validate.py           # fault-aware checkpointed replay
python advanced/run_advanced_replay.py  # generic counterfactual search (no fault labels)
python advanced/provenance_analysis.py  # print causal slices
python advanced/contrastive_dataset.py  # intervention attempts -> contrastive dataset
python advanced/train_intervention_model.py
python advanced/generate_unseen_dataset.py
python advanced/evaluate_unseen.py      # zero-shot eval, 4 unseen fault families
python advanced/evaluate_persistent.py  # persistent-defect benchmark (replay alone cannot fix these)

# Rigorous ML Evaluation (Massive Scale)
python advanced/generate_massive_dataset.py  # 1500+ traces across Seen/Unseen Tasks & Faults
python advanced/rigorous_evaluation.py      # Baselines, AUC, Learning Curves, Ablations

python generate_more_traces.py 3        # optional: bulk traces for poking at the UI
streamlit run ui/animated_app.py
```

`data/` is gitignored. Everything in it is reproducible with the commands
above.

## Layout

```.
├── main.py                     # single clean run
├── generate_dataset.py         # known-fault labelled traces
├── generate_training_dataset.py
├── generate_more_traces.py     # bulk trace generation for the UI
├── diagnose.py                 # spec engine CLI
├── train_ranker.py             # ranker training + eval
├── replay_and_validate.py      # fault-aware replay CLI
├── run_all.py                  # whole pipeline, optional --tests
├── tests/                      # pytest: recorder, replay, spec engine, diff, search
├── requirements.txt
├── .streamlit/config.toml      # dark theme for native widgets
├── agent/                      # demo agent, mock tools, fault injector
├── recorder/                   # trace writer + checkpoint snapshots
├── diagnosis/                  # trace loader, spec engine, provenance graph
├── ml/                         # feature extraction, dataset builder, localization metrics + baseline
├── replay/                     # checkpoint restore, replay runner, patches
├── advanced/                   # counterfactual search, interventions, trace
│                               # diff, contrastive dataset, intervention
│                               # model, unseen-fault generation and eval,
│                               # massive dataset generation, rigorous evaluation
├── ui/animated_app.py          # Streamlit dashboard
└── data/                       # generated artifacts (not committed)
```

## How the pieces work

**Recording.** Each step logs its input, output, state before/after,
confidence, latency and any exception. A JSON snapshot of the full agent
state is written after every step (and once before step 1). Checkpoints are
stored as envelopes — `{trace_id, step_id, step_name, state}` — and the replay
loader unwraps them. Trace IDs carry a uuid suffix so bulk generation never
collides.

**Spec engine.** Task constraints (origin, destination, date, budget,
check-in floor) are encoded as per-step invariants plus terminal checks.
Violations are structured records with expected vs observed values, e.g.
`search_flights.date_matches_task: expected 2026-10-04, observed 2026-10-03`.
The engine also reports the earliest violating step, which is used both as a
model feature and as a sanity signal.

**Provenance.** A static read/write map for the demo agent's state keys
(`STEP_READS` / `STEP_WRITES` in `diagnosis/provenance.py`) is used to build a
DAG over steps, state keys and terminal violations. A backward slice from a
terminal violation yields the causal path the UI draws as the corrupted data
flow.

**Ranker.** 22 hand-built features per step (invariant violations, earliest
violation flag, output emptiness, state-change count, selection validity,
position, step-type one-hots, ...). The model is a linear feature-weight
scorer trained on 770 step-level examples, 60 positive. It was kept linear on
purpose: every score decomposes into weight × activation, which is exactly
what the confidence bars in the UI display.

**Counterfactual search.** Candidate steps come from the ranker's top scores,
steps with violations, hints derived from terminal violations, and upstream
dependencies of those steps. Three intervention policies are proposed per
candidate: replay without the fault, restore task constraints, restore
booking inputs. Each attempt restores the nearest checkpoint below the target
step and re-executes only downstream stages. The first replay that satisfies
all invariants wins, and a comparison record (steps reused vs re-executed,
violations removed/added) is stored with it.

**Intervention model.** Every attempt (features + fixed/not) becomes a row in
a contrastive dataset; a logistic regression over intervention type, target
step and violation statistics is trained on it. It annotates each proposal
with a predicted fix probability, shown in the replay card. Using it to order
attempts is implemented (`model_ordering=True` in `search_fix`) but off by
default, so the validated search order is unchanged.

**Trace comparison.** Two traces aligned by step name are diffed recursively
over inputs, outputs and final state. The Replay Diff Lab tab renders the
result: resolved violations struck through, replay economics, intervention
details.

**Massive Dataset & Rigorous Evaluation.** To prove generalization beyond a small 
curated set, a generator produces 1,500+ traces across multiple dynamic city routes, 
splitting them into strict seen_train, seen_test, unseen_fault_test, and 
unseen_task_test buckets. A dedicated evaluation script trains the ranker on 
subsets to plot a learning curve, drops features to measure ablation impact, and 
calculates baselines (random step, always last step) and fail-detection AUC.

## Fault taxonomy

| Fault | Injected at | Effect | Seen in training |
|---|---|---|---|
| wrong_date | before search_flights | search uses yesterday's date | yes |
| wrong_destination | before search_flights | wrong destination city | yes |
| budget_violation | after select_cheapest_flight | most expensive flight selected | yes |
| ignored_empty_result | before search + after select | empty search, hallucinated flight | yes |
| state_overwrite | before create_booking | selected flight nulled | yes |
| hotel_checkin_violation | after select_hotel | hotel breaks check-in constraint | yes |
| wrong_origin | before search_flights | wrong origin city | no |
| hotel_wrong_city | before search_hotels | wrong hotel city | no |
| hotel_wrong_date | before search_hotels | wrong hotel date | no |
| budget_filter_disabled | before filter + after select | filter bypassed, expensive flight | no |

The last four families are generated and evaluated but never used for
training or for building intervention hints.

### Injected faults vs. persistent defects

The faults above are injected from outside the agent and are **switched off
during replay** (`fault_config=None`). A plain replay from before the fault
therefore fixes them by construction. That demonstrates the checkpoint/replay
machinery, but it does not show that the search found a real bug.

To test the harder case, the agent also supports *persistent defects*
(`TravelAgent(defects=[...])`): bugs in the agent's own step logic that survive
replay and are recorded in `trace["defects"]`.

| Defect | Where | Effect |
|---|---|---|
| select_reads_unfiltered_list | select_cheapest_flight | reads the unfiltered list, picks the most expensive flight |
| hotel_filter_inverted | filter_hotels_by_checkin | inverted comparison keeps early check-ins |

Replaying these without a patch cannot work. The search must pick the right
step and the right intervention (`disable_step_defect`, which re-executes with
the reference step logic from that step on).

## Results

All numbers are produced by the scripts themselves (`python run_all.py`); the
Evaluation Studio tab reads the same JSON reports from disk. Small samples:
treat these as demonstrations, not benchmarks.

**Localization (does the model add anything?).** The ranker is compared with a
trivial baseline: blame the earliest step the spec engine flagged.

| Set | n | Ranker top-1 | Baseline top-1 |
|---|---|---|---|
| Held-out test split (seen families) | 24 | 1.00 | 1.00 |
| Unseen families (zero-shot) | 20 | 0.75 | 0.75 |
| Persistent defects | 10 | 1.00 | 1.00 |

The ranker matches the baseline everywhere. Its feature set includes the
spec engine's earliest-violation flag, so on this agent the spec engine does
the localizing and the learned weights add nothing measurable. On the unseen
`budget_filter_disabled` family both score 0/5: the filter at step 4 is the
root cause, but the violation first shows at step 5.

**Fixing.**

- Fault-aware checkpointed replay: 6/6 known traces fixed.
- Generic counterfactual search, no fault labels: 6/6 known and 20/20 unseen
  injected-fault traces fixed. 20/20 are fixed on the first attempt, mostly by
  `replay_no_patch`, i.e. by turning the injection off (see above).
- Persistent defects: plain replay fixes 0/10; the search fixes 10/10, never on
  the first attempt, averaging 2.5 attempts, always via `disable_step_defect`
  at the correct step.

**Intervention model.** Training accuracy is about 0.92-0.95 on the 60-72
contrastive attempts; accuracy on held-out traces (grouped CV, whole traces
left out) is about 0.81-0.87 against a 0.52 majority-class baseline. Written
to `data/models/intervention_model_metrics.json`. It annotates proposals only.

**Rigorous ML Metrics (from 1,500+ trace evaluation).**

- Fail Detection AUC: Spec engine separates success from failure with an AUC of ~0.90+.
- Baselines: The ranker crushes trivial baselines (Random Step: ~16%, Always Last Step: ~11%).
- Learning Curve: Top-1 accuracy scales smoothly from 100 to 1500+ training runs, plateauing near 1.0 on seen faults.
- Ablation Study: Dropping features like is_earliest_violation or violation_count measurably degrades zero-shot generalization on unseen faults, proving the feature set's necessity.

## UI

`streamlit run ui/animated_app.py` opens four tabs.

- **Flight Recorder** — animated vertical execution graph (stages light up as
  the run proceeds, contaminated stages and causal links marked in red) next
  to a diagnostic rail: telemetry, post-mortem narrative with suspicion
  gauge, step ranking, confidence contributions, divergence against a
  matching healthy baseline, causal slice, replay card. Cards are collapsible.
  "Run Counterfactual Replay" runs the search; on a validated fix the view
  automatically switches to the replayed execution and the graph re-animates
  fully green. The "Replay view" checkbox toggles back and forth.
- **Evaluation Studio** — localization and fix-rate metrics parsed live from
  the backend report JSONs, plus interactive charts for the Learning Curve, 
Ablation Study, Fail Detection AUC, and baseline comparisons.
- **Replay Diff Lab** — original vs replayed terminal states, resolved
  violations struck through, intervention and replay economics.
- **Step Inspector** — per-stage expanders with suspicion score, latency,
  confidence, state mutations, invariant violations and raw I/O. The
  localized root stage opens expanded.

## Limitations

- Mock tools are deterministic by design, which is what makes replay exact.
  A real agent with non-deterministic tools would need recorded tool
  responses replayed instead of live calls; the trace format already stores
  inputs and outputs, but this is not implemented.
- The provenance read/write map is hand-written for the demo agent. A new
  agent domain needs its own map, or runtime instrumentation of reads and
  writes.
- The `disable_step_defect` intervention assumes a reference implementation of
  each step exists. For a real agent that means a known-good version, not a
  guessed patch.
- The generic intervention search is heuristic. It fixes 100% of the curated
  benchmark traces, but there is no guarantee on arbitrary traces; on a
  bulk-generated set with label noise it reached 90/100.
- The ranker is deliberately small (linear, 770 samples). The contribution of
  this project is the record-diagnose-prove pipeline, not model scale.