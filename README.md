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

Every script validates its own output and exits non-zero on failure, so the
whole chain can be run top to bottom:

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
python generate_more_traces.py 3        # optional: bulk traces for poking at the UI
streamlit run ui/animated_app.py
```

`data/` is gitignored. Everything in it is reproducible with the commands
above.

## Layout

```
.
├── main.py                     # single clean run
├── generate_dataset.py         # known-fault labelled traces
├── generate_training_dataset.py
├── generate_more_traces.py     # bulk trace generation for the UI
├── diagnose.py                 # spec engine CLI
├── train_ranker.py             # ranker training + eval
├── replay_and_validate.py      # fault-aware replay CLI
├── requirements.txt
├── .streamlit/config.toml      # dark theme for native widgets
├── agent/                      # demo agent, mock tools, fault injector
├── recorder/                   # trace writer + checkpoint snapshots
├── diagnosis/                  # trace loader, spec engine, provenance graph
├── ml/                         # feature extraction, dataset builder
├── replay/                     # checkpoint restore, replay runner, patches
├── advanced/                   # counterfactual search, interventions, trace
│                               # diff, contrastive dataset, intervention
│                               # model, unseen-fault generation and eval
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

## Results

All numbers are produced by the scripts themselves; the Evaluation Studio tab
reads the same JSON reports from disk.

- Ranker localization on the held-out test split (24 failed traces):
  Top-1 1.00, Top-3 1.00, MRR 1.00.
- Spec engine earliest-violation signal matches the injected root step on
  every curated trace.
- Fault-aware checkpointed replay: 6/6 known traces fixed.
- Generic counterfactual search, no fault labels used anywhere: 6/6 known
  traces and 20/20 unseen-family traces fixed (zero-shot).
- Intervention model: 0.95 training accuracy on 60 contrastive attempts;
  used for annotation only.

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
  the backend report JSONs.
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
- The generic intervention search is heuristic. It fixes 100% of the curated
  benchmark traces, but there is no guarantee on arbitrary traces; on a
  bulk-generated set with label noise it reached 90/100.
- The ranker is deliberately small (linear, 770 samples). The contribution of
  this project is the record-diagnose-prove pipeline, not model scale.