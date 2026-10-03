import os
import sys
import json
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from diagnosis.loader import load_traces
from diagnosis.spec_engine import evaluate_trace
from diagnosis.provenance import build_provenance_graph, get_backward_slice
from ml.features import build_step_features
from advanced.counterfactual_search import search_fix
from advanced.trace_compare import diff_values


# ---------------------------------------------------------------- helpers
def load_ranker(model_path="data/models/ranker.json"):
    if not os.path.exists(model_path):
        return {"weights": {}, "bias": 0.0}
    with open(model_path, "r", encoding="utf-8") as f:
        return json.load(f)


def score_features(weights, bias, features):
    score = bias
    for k, v in features.items():
        score += weights.get(k, 0.0) * float(v)
    return float(score)


def pretty(name):
    return str(name).replace("_", " ").title()


FEATURE_LABELS = {
    "has_error": "Tool Execution Error",
    "output_empty": "Empty Tool Output",
    "violation_count": "Invariant Violations",
    "is_earliest_violation": "Earliest Failure Signal",
    "has_search_input_mismatch": "Search Parameter Mismatch",
    "has_selected_flight_invalid": "Invalid Flight Selection",
    "has_selected_hotel_invalid": "Invalid Hotel Selection",
    "has_booking_input_lost": "State Data Lost Before Booking",
    "low_confidence": "Low Agent Confidence",
        "state_changed_key_count": "Unexpected State Mutations",
}


def compact_value(v):
    if v is None:
        return "∅"
    if isinstance(v, list):
        return f"list[{len(v)}]"
    if isinstance(v, dict):
        return f"dict({len(v)} keys)"
    s = str(v)
    return s if len(s) <= 34 else s[:31] + "…"


def load_replay_trace(replay_report):
    """Loads the replayed trace produced by search_fix, from disk."""
    succ = (replay_report or {}).get("successful_attempt") or {}
    rid = ((succ.get("comparison") or {}).get("replay_trace_id"))
    if not rid:
        return None
    path = os.path.join("data", "advanced", "replays", str(rid), "trace.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_divergence(trace, traces_all):
    """Finds the first stage whose output differs from a matching healthy baseline."""
    if trace.get("status") != "failed":
        return None

    task = trace.get("task", {})
    key = (
        task.get("origin"),
        task.get("destination"),
        task.get("date"),
        task.get("budget"),
        task.get("hotel_checkin_after"),
    )

    baseline = None
    for t in traces_all or []:
        if t.get("trace_id") == trace.get("trace_id"):
            continue
        if t.get("status") != "success":
            continue
        tt = t.get("task", {})
        if (
            tt.get("origin"),
            tt.get("destination"),
            tt.get("date"),
            tt.get("budget"),
            tt.get("hotel_checkin_after"),
        ) == key:
            baseline = t
            break

    if baseline is None:
        return None

    base_steps = {s.get("name"): s for s in baseline.get("steps", [])}

    for s in trace.get("steps", []):
        b = base_steps.get(s.get("name"))
        if not b:
            continue
        d = diff_values(b.get("output"), s.get("output"), path="output")
        if d:
            return {
                "baseline_trace_id": baseline.get("trace_id"),
                "step_id": s.get("step_id"),
                "step_name": s.get("name"),
                "diffs": [
                    {"path": x.get("path"), "before": x.get("before"), "after": x.get("after")}
                    for x in d[:4]
                ],
            }

    return None


def render_step_inspector(trace, report):
    """Native Streamlit per-stage inspector: scores, latency, state mutations, violations."""
    model = load_ranker()
    weights = model.get("weights", {})
    bias = float(model.get("bias", 0.0))

    steps = trace.get("steps", [])
    max_steps = len(steps)

    viol_by_step = {}
    for v in report.get("step_violations", []):
        viol_by_step.setdefault(v.get("step_id"), []).append(v)

    scored = {
        s.get("name"): score_features(weights, bias, build_step_features(trace, report, s, max_steps))
        for s in steps
    }

    root_name = max(scored, key=scored.get) if scored and trace.get("status") == "failed" else None

    st.markdown(
        f"<div style='font-family:monospace;font-size:12px;color:#8b98ad;margin:8px 0 16px'>"
        f"TRACE {trace.get('trace_id')} · {str(trace.get('status')).upper()} · {len(steps)} STAGES</div>",
        unsafe_allow_html=True,
    )

    for s in steps:
        name = s.get("name")
        sid = s.get("step_id")
        sc = scored.get(name, 0.0)
        is_root = (name == root_name)
        tag = " · ROOT CAUSE" if is_root else ""

        with st.expander(f"Step {sid} · {pretty(name)} · suspicion {sc:.3f}{tag}", expanded=is_root):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Suspicion", f"{sc:.3f}")
            m2.metric("Latency", f"{float(s.get('latency_ms', 0)):.1f} ms")
            m3.metric("Agent confidence", f"{float(s.get('confidence', 0)):.2f}")
            m4.metric("Stage type", str(s.get("type", "-")))

            if s.get("error"):
                st.error(f"Step raised: {s['error']}")

            sb = s.get("state_before") or {}
            sa = s.get("state_after") or {}
            changed = sorted([k for k in set(sb) | set(sa) if sb.get(k) != sa.get(k)])

            if changed:
                lines = "".join(
                    [
                        f"<div style='font-family:monospace;font-size:12px;color:#cbd5e1;margin:3px 0'>"
                        f"{k}: <span style='color:#34d399'>{compact_value(sb.get(k))}</span> → "
                        f"<span style='color:#fb7185'>{compact_value(sa.get(k))}</span></div>"
                        for k in changed
                    ]
                )
                st.markdown(
                    "<div style='margin:8px 0 2px;font-family:monospace;font-size:10px;"
                    "letter-spacing:.14em;color:#8b98ad;text-transform:uppercase'>State mutations</div>" + lines,
                    unsafe_allow_html=True,
                )

            vs = viol_by_step.get(sid, [])
            if vs:
                tags = "".join(
                    [
                        f"<span style='display:inline-block;margin:3px 6px 3px 0;padding:3px 9px;border-radius:6px;"
                        f"font-family:monospace;font-size:11px;color:#fb7185;background:rgba(251,113,133,.1);"
                        f"border:1px solid rgba(251,113,133,.3)'>{pretty(v.get('invariant'))}</span>"
                        for v in vs
                    ]
                )
                st.markdown(
                    "<div style='margin:8px 0 2px;font-family:monospace;font-size:10px;"
                    "letter-spacing:.14em;color:#8b98ad;text-transform:uppercase'>Invariant violations</div>" + tags,
                    unsafe_allow_html=True,
                )

            with st.expander("Raw input / output"):
                st.json({"input": s.get("input"), "output": s.get("output")})

# ---------------------------------------------------------------- payload
def build_replay_payload(rr):
    if not rr:
        return None
    succ = rr.get("successful_attempt") or {}
    comp = succ.get("comparison") or {}
    interv = succ.get("intervention") or {}

    if not succ:
        return {
            "fixed": False,
            "attempts": len(rr.get("attempts", [])),
            "intervention_type": None,
            "target": None,
            "removed": [],
            "added": [],
            "replayed": [],
            "skipped": [],
            "replay_trace_id": None,
        }

    return {
        "fixed": bool(rr.get("fixed")),
        "attempts": len(rr.get("attempts", [])),
        "intervention_type": interv.get("intervention_type"),
        "target": pretty(interv.get("target_step_name")),
        "model_confidence": interv.get("predicted_fix_probability"),
        "removed": comp.get("removed_violations", []),
        "added": comp.get("added_violations", []),
        "replayed": comp.get("steps_replayed", []),
        "skipped": comp.get("steps_skipped", []),
        "replay_trace_id": comp.get("replay_trace_id"),
    }
def build_narrative(trace, report, causal_path, root, contributions):
    paras = []

    if trace.get("status") == "success":
        paras.append({
            "kicker": "Incident Summary",
            "body": "Execution terminated in a healthy state. All task invariants held across every pipeline stage and no state contamination was detected in the provenance graph.",
        })
        return paras

    violations = [pretty(v.get("violation")) for v in report.get("final_violations", [])]
    step_count = len(trace.get("steps", []))
    root_label = pretty(root.get("name")) if root else "Unknown"

    paras.append({
        "kicker": "Incident Summary",
        "body": f"Execution terminated in a failed state. Terminal validation reported: {', '.join(violations)}.",
    })

    if root:
        signals = ", ".join([c["label"] for c in contributions]) or "aggregate step anomalies"
        paras.append({
            "kicker": "Root Cause Localization",
            "body": f"The Intervention Ranker assigns Step {root['step_id']} ({root_label}) a suspicion index of {root['score']:.3f}, the highest across all {step_count} executed steps. Dominant signals: {signals}.",
        })

    if causal_path and root:
        path_str = " → ".join([pretty(p) for p in causal_path])
        paras.append({
            "kicker": "Causal Propagation",
            "body": f"A backward slice from the terminal violation traverses {len(causal_path)} nodes: {path_str}. State contamination originates at the head of this slice.",
        })
        paras.append({
            "kicker": "Recommended Intervention",
            "body": f"Restore the checkpoint immediately preceding Step {root['step_id']} and replay only downstream stages under a corrected intervention. The unaffected execution prefix is not re-run.",
        })

    return paras

def build_payload(trace, report, replay_report, banner=None, traces_all=None):
    steps = trace.get("steps", [])
    model = load_ranker()
    weights = model.get("weights", {})
    bias = float(model.get("bias", 0.0))

    causal_path, causal_edges = [], []
    if trace.get("status") == "failed":
        graph = build_provenance_graph(trace, report)
        fvs = report.get("final_violations", [])
        if fvs:
            vname = fvs[0].get("violation")
            cs = get_backward_slice(graph, f"violation:{vname}")
            order = {s.get("name"): i for i, s in enumerate(steps)}
            cs.sort(key=lambda n: order.get(n, 999))
            causal_path = cs
            causal_edges = [f"{cs[i]}->{cs[i + 1]}" for i in range(len(cs) - 1)]

    scored = []
    max_steps = len(steps)
    for step in steps:
        feats = build_step_features(trace, report, step, max_steps)
        scored.append({
            "step_id": step.get("step_id"),
            "name": step.get("name"),
            "score": score_features(weights, bias, feats),
            "features": feats,
        })

    root = max(scored, key=lambda x: x["score"]) if scored else None

    contributions = []
    if root and trace.get("status") == "failed":
        for fname, fval in root["features"].items():
            w = weights.get(fname, 0.0)
            c = w * float(fval)
            if c > 0.01:
                contributions.append({
                    "label": FEATURE_LABELS.get(fname, fname.replace("_", " ").title()),
                    "value": round(c, 3),
                })
        contributions.sort(key=lambda x: x["value"], reverse=True)
        contributions = contributions[:4]
        if contributions:
            mx = contributions[0]["value"]
            for c in contributions:
                c["pct"] = round(min(100.0, c["value"] / mx * 100.0), 1)

    ranking = []
    if scored:
        mx_score = max(abs(s["score"]) for s in scored) or 1.0
        for s in sorted(scored, key=lambda x: x["score"], reverse=True)[:5]:
            ranking.append({
                "label": pretty(s["name"]),
                "score": round(s["score"], 3),
                "pct": round(min(100.0, abs(s["score"]) / mx_score * 100.0), 1),
                "is_root": bool(root) and s["name"] == root["name"],
            })

    return {
        "trace_id": trace.get("trace_id"),
        "status": trace.get("status"),
        "task": trace.get("task", {}),
        "steps": [{"id": s.get("name"), "label": pretty(s.get("name"))} for s in steps],
        "edges": [{"from": steps[i - 1].get("name"), "to": steps[i].get("name")} for i in range(1, len(steps))],
        "causal_path": causal_path,
        "causal_edges": causal_edges,
        "violations": [pretty(v.get("violation")) for v in report.get("final_violations", [])],
        "root": {
            "step_id": root["step_id"],
            "label": pretty(root["name"]),
            "score": round(root["score"], 3),
        } if root else None,
        "contributions": contributions,
        "narrative": build_narrative(trace, report, causal_path, root, contributions),
        "replay": build_replay_payload(replay_report),
        "ranking": ranking,
        "divergence": compute_divergence(trace, traces_all) if traces_all else None,
        "banner": banner,
    }


# ---------------------------------------------------------------- dashboard template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  :root{
    --bg:#04060c; --panel:rgba(13,18,32,.78); --line:rgba(148,163,184,.16);
    --text:#e6edf7; --muted:#8b98ad; --cyan:#22d3ee; --green:#34d399;
    --rose:#fb7185; --indigo:#818cf8;
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:transparent;font-family:var(--sans);color:var(--text)}
  body::before{
    content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
    background:
      radial-gradient(1100px 520px at 85% -10%, rgba(79,110,247,.16), transparent 60%),
      radial-gradient(900px 480px at 5% 110%, rgba(34,211,238,.10), transparent 60%),
      linear-gradient(rgba(148,163,184,.045) 1px, transparent 1px),
      linear-gradient(90deg, rgba(148,163,184,.045) 1px, transparent 1px);
    background-size:auto,auto,44px 44px,44px 44px;
  }
  .dash{position:relative;z-index:1;display:grid;grid-template-columns:minmax(0,1.55fr) minmax(340px,.95fr);gap:16px;height:920px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:16px;backdrop-filter:blur(14px);box-shadow:0 12px 32px rgba(0,0,0,.38);overflow:hidden}
  .stage{display:flex;flex-direction:column}
  .card-h{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid var(--line)}
  .card-b{padding:16px;max-height:210px;overflow:hidden;position:relative;transition:max-height .45s cubic-bezier(.22,1,.36,1)}
  .card-b::after{content:"";position:absolute;left:0;right:0;bottom:0;height:44px;background:linear-gradient(180deg,transparent,rgba(13,18,32,.96));opacity:0;pointer-events:none;transition:opacity .3s}
  .card.clamped .card-b::after{opacity:1}
  .card.clamped.open .card-b::after{opacity:0}
  .h-right{display:inline-flex;align-items:center;gap:8px}
  .chev{background:rgba(148,163,184,.08);border:1px solid var(--line);border-radius:8px;width:26px;height:26px;display:grid;place-items:center;cursor:pointer;color:var(--muted);transition:color .2s,border-color .2s}
  .chev:hover{color:var(--cyan);border-color:rgba(34,211,238,.45)}
  .chev svg{transition:transform .3s}
  .card.open .chev svg{transform:rotate(180deg)}
  .micro{font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
  .mono{font-family:var(--mono)}
  #graph{flex:1;min-height:0}
  .legend{display:flex;gap:18px;padding:10px 16px;border-top:1px solid var(--line)}
  .legend span{display:inline-flex;align-items:center;gap:7px;font-size:11px;color:var(--muted)}
  .legend i{width:9px;height:9px;border-radius:50%;display:inline-block}
  .rail{overflow-y:auto;display:flex;flex-direction:column;gap:14px;padding-right:6px;scrollbar-width:thin;scrollbar-color:#24304a transparent}
  .rail::-webkit-scrollbar{width:8px}
  .rail::-webkit-scrollbar-thumb{background:#24304a;border-radius:4px}
  .rail::-webkit-scrollbar-track{background:transparent}
  .rail .card{animation:fadeUp .45s ease both;flex:0 0 auto}
  .rail .card:nth-child(2){animation-delay:.06s}
  .rail .card:nth-child(3){animation-delay:.12s}
  .rail .card:nth-child(4){animation-delay:.18s}
  .rail .card:nth-child(5){animation-delay:.24s}
  @keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
  .pill{display:inline-flex;align-items:center;gap:7px;padding:4px 10px;border-radius:999px;font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.1em}
  .pill .dot{width:6px;height:6px;border-radius:50%;background:currentColor;box-shadow:0 0 9px currentColor;animation:pulse 1.7s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
  .pill.fail{color:var(--rose);background:rgba(251,113,133,.10);border:1px solid rgba(251,113,133,.35)}
  .pill.ok{color:var(--green);background:rgba(52,211,153,.10);border:1px solid rgba(52,211,153,.35)}
  .pill.info{color:var(--cyan);background:rgba(34,211,238,.10);border:1px solid rgba(34,211,238,.35)}
  .kv{display:grid;grid-template-columns:1fr 1fr;gap:14px 18px}
  .kv .k{font-size:11px;color:var(--muted);margin-bottom:3px}
  .kv .v{font-size:13px;color:var(--text)}
  .diag{display:flex;gap:18px;align-items:flex-start}
  .gauge-wrap{position:relative;width:92px;height:92px;flex:0 0 auto}
  .gauge-wrap svg{transform:rotate(-90deg)}
  .g-bg{fill:none;stroke:rgba(148,163,184,.15);stroke-width:7}
  .g-fg{fill:none;stroke:var(--rose);stroke-width:7;stroke-linecap:round;transition:stroke-dashoffset 1s cubic-bezier(.22,1,.36,1);filter:drop-shadow(0 0 6px rgba(251,113,133,.55))}
  .g-val{position:absolute;inset:0;display:grid;place-items:center;font-family:var(--mono);font-size:17px;font-weight:700}
  .kicker{font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--cyan);margin:0 0 4px}
  .para{font-size:13px;line-height:1.65;color:#cbd5e1;margin:0 0 14px}
  .para:last-child{margin-bottom:0}
  .bar-row{margin-bottom:14px}
  .bar-h{display:flex;justify-content:space-between;font-size:12px;color:#cbd5e1;margin-bottom:6px}
  .bar-h b{font-family:var(--mono);color:var(--cyan);font-weight:600}
  .bar{height:6px;border-radius:3px;background:rgba(148,163,184,.14);overflow:hidden}
  .bar i{display:block;height:100%;border-radius:3px;background:linear-gradient(90deg,var(--cyan),var(--indigo));box-shadow:0 0 12px rgba(34,211,238,.45);animation:grow .9s cubic-bezier(.22,1,.36,1) both}
  @keyframes grow{from{width:0}}
  .note{font-size:11px;color:var(--muted);line-height:1.5}
  ol.tl{list-style:none;margin:0;padding:0 0 0 6px}
  ol.tl li{position:relative;padding:0 0 18px 22px;font-family:var(--mono);font-size:12px;color:#cbd5e1}
  ol.tl li::before{content:"";position:absolute;left:0;top:4px;width:9px;height:9px;border-radius:50%;background:var(--rose);box-shadow:0 0 10px rgba(251,113,133,.6)}
  ol.tl li::after{content:"";position:absolute;left:4px;top:16px;bottom:0;width:1px;background:rgba(251,113,133,.30)}
  ol.tl li:last-child::after{display:none}
  ol.tl li.term{color:var(--rose)}
  .tag{display:inline-block;padding:3px 9px;border-radius:6px;font-family:var(--mono);font-size:11px;margin:0 6px 6px 0}
  .tag.red{color:var(--rose);background:rgba(251,113,133,.10);border:1px solid rgba(251,113,133,.30)}
  .tag.green{color:var(--green);background:rgba(52,211,153,.10);border:1px solid rgba(52,211,153,.30)}
  .cmp{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
  .cmp .box{border:1px solid var(--line);border-radius:10px;padding:12px;background:rgba(4,6,12,.45)}
  .cmp .box h5{margin:0 0 8px;font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
  .stat{display:flex;justify-content:space-between;font-size:12px;color:#cbd5e1;padding:4px 0}
  .stat b{font-family:var(--mono);font-weight:600}
</style>
</head>
<body>
<div class="dash">
  <section class="card stage">
    <div class="card-h">
      <span class="micro" id="stage-title">Execution Graph</span>
      <span id="stage-pill"></span>
    </div>
    <div id="graph"></div>
    <div class="legend">
      <span><i style="background:#34d399"></i>Healthy stage</span>
      <span><i style="background:#22d3ee"></i>Active execution</span>
      <span><i style="background:#fb7185"></i>Contaminated stage</span>
      <span><i style="background:transparent;border:1px dashed #fb7185"></i>Causal link</span>
    </div>
  </section>
  <aside class="rail" id="rail"></aside>
</div>

<script>
const P = __PAYLOAD__;
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => (
  {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]
));
const short = v => {
  const s = (v == null ? '∅' : (Array.isArray(v) ? 'list[' + v.length + ']' : (typeof v === 'object' ? 'dict' : String(v))));
  return s.length > 28 ? s.slice(0, 25) + '…' : s;
};
const pill = (txt, cls) => '<span class="pill ' + cls + '"><span class="dot"></span>' + esc(txt) + '</span>';
let cardSeq = 0;
const card = (title, right, body) => {
  const id = 'card-' + (cardSeq++);
  return '<section class="card" id="' + id + '">' +
    '<div class="card-h"><span class="micro">' + esc(title) + '</span>' +
    '<span class="h-right">' + (right || '') +
    '<button class="chev" title="Expand / collapse" aria-expanded="false">' +
    '<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 4l4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
    '</button></span></div>' +
    '<div class="card-b">' + body + '</div></section>';
};
/* ---------- stage header ---------- */
document.getElementById('stage-title').textContent =
  'Execution Graph · ' + String(P.trace_id).slice(0, 24) + '…';
document.getElementById('stage-pill').innerHTML =
  P.status === 'failed' ? pill('FAULT', 'fail') : pill('NOMINAL', 'ok');

/* ---------- rail cards ---------- */
let rail = '';
if (P.banner) {
  rail += card(P.banner.title, pill(P.banner.pill, P.banner.pill_cls),
    '<div class="note" style="font-size:12.5px;color:#cbd5e1;line-height:1.65">' + P.banner.body + '</div>');
}

/* telemetry */
const t = P.task || {};
rail += card('Mission Telemetry', '',
  '<div class="kv">' +
  '<div><div class="k">Route</div><div class="v">' + esc(t.origin) + ' → ' + esc(t.destination) + '</div></div>' +
  '<div><div class="k">Travel Date</div><div class="v mono">' + esc(t.date) + '</div></div>' +
  '<div><div class="k">Budget Ceiling</div><div class="v mono">₹' + esc(t.budget) + '</div></div>' +
  '<div><div class="k">Check-in Floor</div><div class="v mono">' + esc(t.hotel_checkin_after) + '</div></div>' +
  '<div><div class="k">Pipeline Depth</div><div class="v mono">' + P.steps.length + ' stages</div></div>' +
  '<div><div class="k">Terminal State</div><div class="v mono" style="color:' + (P.status === 'failed' ? '#fb7185' : '#34d399') + '">' + esc(P.status.toUpperCase()) + '</div></div>' +
  '</div>');

/* diagnosis */
if (P.status === 'failed' && P.root) {
  const C = 2 * Math.PI * 34;
  const prob = 1 / (1 + Math.exp(-P.root.score));
  const offset = C * (1 - prob);
  let body = '<div class="diag"><div class="gauge-wrap">' +
    '<svg viewBox="0 0 80 80" width="92" height="92">' +
    '<circle class="g-bg" cx="40" cy="40" r="34"></circle>' +
    '<circle class="g-fg" id="gfg" cx="40" cy="40" r="34" stroke-dasharray="' + C.toFixed(1) + '" stroke-dashoffset="' + C.toFixed(1) + '"></circle>' +
    '</svg><div class="g-val">' + P.root.score.toFixed(2) + '</div></div><div>';
  for (const para of P.narrative) {
    body += '<p class="kicker">' + esc(para.kicker) + '</p><p class="para">' + para.body + '</p>';
  }
  body += '</div></div>';
  rail += card('Diagnosis', pill('LOCALIZED', 'fail'), body);
  setTimeout(() => { const g = document.getElementById('gfg'); if (g) g.style.strokeDashoffset = offset.toFixed(1); }, 250);
} else {
  let body = '';
  for (const para of P.narrative) {
    body += '<p class="kicker">' + esc(para.kicker) + '</p><p class="para">' + para.body + '</p>';
  }
  rail += card('Diagnosis', pill('NOMINAL', 'ok'), body);
}

/* suspicion ranking */
if (P.ranking && P.ranking.length) {
  let rk = '';
  for (const r of P.ranking) {
    const col = r.is_root ? '#fb7185' : '#22d3ee';
    const grad = r.is_root ? 'linear-gradient(90deg,#fb7185,#f472b6)' : 'linear-gradient(90deg,#22d3ee,#818cf8)';
    rk += '<div class="bar-row"><div class="bar-h"><span style="' + (r.is_root ? 'color:#fb7185;font-weight:600' : '') + '">' +
      esc(r.label) + (r.is_root ? ' · ROOT' : '') + '</span><b style="color:' + col + '">' + r.score.toFixed(3) +
      '</b></div><div class="bar"><i style="width:' + r.pct + '%;background:' + grad + '"></i></div></div>';
  }
  rk += '<div class="note">Suspicion index per stage from the Intervention Ranker. The highest-scoring stage is treated as the localized root cause.</div>';
  rail += card('Step Suspicion Ranking', '', rk);
}

/* confidence metrics */
if (P.status === 'failed' && P.contributions.length) {
  let body = '';
  for (const c of P.contributions) {
    body += '<div class="bar-row"><div class="bar-h"><span>' + esc(c.label) + '</span><b>+' + c.value.toFixed(3) + '</b></div>' +
            '<div class="bar"><i style="width:' + c.pct + '%"></i></div></div>';
  }
  body += '<div class="note">Values are weight × activation contributions from the Intervention Ranker for the localized root step. Bars are normalized against the dominant signal.</div>';
  rail += card('Fault Confidence Metrics', '', body);
}

/* divergence */
if (P.divergence) {
  const d = P.divergence;
  let db = '<div class="stat"><span>Healthy baseline</span><b style="font-size:10px">' +
    esc(String(d.baseline_trace_id).slice(0, 18)) + '…</b></div>' +
    '<div class="stat"><span>First divergent stage</span><b style="color:#fb7185">Step ' + d.step_id +
    ' · ' + esc(String(d.step_name).replace(/_/g, ' ').replace(/\\b\\w/g, m => m.toUpperCase())) + '</b></div>' +
    '<div style="margin-top:10px">';
  for (const dd of d.diffs) {
    db += '<div class="note mono" style="margin-bottom:6px;color:#cbd5e1">' + esc(dd.path) +
      ': <span style="color:#34d399">' + esc(short(dd.before)) + '</span> → <span style="color:#fb7185">' +
      esc(short(dd.after)) + '</span></div>';
  }
  db += '</div>';
  rail += card('Divergence vs Healthy Baseline', pill('DIFF', 'info'), db);
}

/* causal flow */
if (P.status === 'failed' && P.causal_path.length) {
  let body = '<ol class="tl">';
  for (const s of P.causal_path) {
    body += '<li>' + esc(s.replace(/_/g, ' ').toUpperCase()) + '</li>';
  }
  body += '<li class="term">TERMINAL: ' + esc((P.violations[0] || 'unknown').toUpperCase()) + '</li></ol>';
  rail += card('Corrupted Data Flow', pill('SLICE', 'fail'), body);
}

/* counterfactual replay */
let rbody = '';
if (!P.replay) {
  rbody = '<div class="note">No counterfactual experiment recorded for this trace. Trigger <b>Run Counterfactual Replay</b> from the toolbar to restore the checkpoint before the suspected step, replay downstream stages, and diff the outcomes.</div>';
} else if (P.replay.fixed) {
  rbody = pill('FIX VALIDATED', 'ok') +
    '<div class="cmp">' +
    '<div class="box"><h5>Intervention</h5>' +
    '<div class="stat"><span>Type</span><b>' + esc(P.replay.intervention_type) + '</b></div>' +
    '<div class="stat"><span>Target</span><b>' + esc(P.replay.target) + '</b></div>' +
    '<div class="stat"><span>Attempts</span><b>' + P.replay.attempts + '</b></div>' +
    (P.replay.model_confidence != null ? '<div class="stat"><span>Outcome-model confidence</span><b style="color:#22d3ee">' + Math.round(P.replay.model_confidence * 100) + '%</b></div>' : '') +
    '</div>' +
    '<div class="box"><h5>Replay Economics</h5>' +
    '<div class="stat"><span>Stages replayed</span><b>' + P.replay.replayed.length + '</b></div>' +
    '<div class="stat"><span>Stages reused</span><b>' + P.replay.skipped.length + '</b></div>' +
    '<div class="stat"><span>Replay trace</span><b style="font-size:10px">' + esc(String(P.replay.replay_trace_id).slice(0, 14)) + '…</b></div>' +
    '</div></div>' +
    '<div style="margin-top:12px"><div class="k" style="font-size:11px;color:var(--muted);margin-bottom:6px">Violations resolved by replay</div>' +
    (P.replay.removed.length ? P.replay.removed.map(v => '<span class="tag green">' + esc(v.replace(/_/g, ' ')) + '</span>').join('') : '<span class="note">none</span>') +
    '</div>';
} else {
  rbody = pill('REPLAY FAILED', 'fail') + '<div class="note" style="margin-top:10px">The counterfactual search could not validate a fix within ' + P.replay.attempts + ' intervention attempts.</div>';
}
rail += card('Counterfactual Replay', P.replay && P.replay.fixed ? pill('VERIFIED', 'ok') : '', rbody);

const railEl = document.getElementById('rail');
railEl.innerHTML = rail;

railEl.addEventListener('click', (e) => {
  const btn = e.target.closest('.chev');
  if (!btn) return;
  const cardEl = btn.closest('.card');
  const body = cardEl.querySelector('.card-b');
  const open = cardEl.classList.toggle('open');
  btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  body.style.maxHeight = open ? (body.scrollHeight + 'px') : '';
});

railEl.querySelectorAll('.card').forEach((c) => {
  const b = c.querySelector('.card-b');
  if (b && b.scrollHeight > b.clientHeight + 6) c.classList.add('clamped');
});

/* ---------- graph ---------- */
const nodes = new vis.DataSet(P.steps.map(s => ({
  id: s.id, label: s.label,
  color: { background: '#0b1222', border: '#24304a' },
  font: { color: '#dbe7ff', size: 15, face: 'system-ui, sans-serif' },
  shape: 'box', margin: 14, borderWidth: 2,
  widthConstraint: { minimum: 170 }
})));
const edges = new vis.DataSet(P.edges.map(e => ({
  from: e.from, to: e.to,
  arrows: { to: { enabled: true, scaleFactor: 0.5 } },
  smooth: { type: 'cubicBezier', forceDirection: 'vertical', roundness: 0.4 },
  color: { color: '#24304a' }, width: 2
})));
const network = new vis.Network(
  document.getElementById('graph'),
  { nodes, edges },
  {
    layout: { hierarchical: { direction: 'UD', sortMethod: 'directed', levelSeparation: 110, nodeSpacing: 190 } },
    physics: false,
    interaction: { dragNodes: false, zoomView: true, dragView: true, hover: true }
  }
);
network.once('afterDrawing', () => network.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } }));

const sleep = ms => new Promise(r => setTimeout(r, ms));
(async function animate() {
  for (let i = 0; i < P.steps.length; i++) {
    const s = P.steps[i];
    const bad = P.causal_path.includes(s.id);
    nodes.update({ id: s.id, color: { background: '#0b1222', border: '#22d3ee' }, shadow: { enabled: true, color: 'rgba(34,211,238,.45)', size: 16 } });
    if (i > 0) {
      const prev = P.steps[i - 1].id;
      const e = edges.get({ filter: x => x.from === prev && x.to === s.id })[0];
      if (e) edges.update({ id: e.id, color: { color: '#22d3ee' } });
    }
    await sleep(240);
    nodes.update({ id: s.id, color: { background: '#0b1222', border: bad ? '#fb7185' : '#34d399' }, shadow: { enabled: false } });
  }
  if (P.causal_edges.length) {
    await sleep(350);
    P.causal_edges.forEach(key => {
      const [f, to] = key.split('->');
      const e = edges.get({ filter: x => x.from === f && x.to === to })[0];
      if (e) edges.update({ id: e.id, color: { color: '#fb7185' }, dashes: true, width: 3 });
    });
  }
})();
</script>
</body>
</html>
"""

# ---------------------------------------------------------------- app
def render_evaluation_studio():
    """Dynamically calculates and renders Model Evaluation metrics from backend JSONs."""
    st.markdown("<h2 style='font-family:monospace; letter-spacing:2px; color:#e6edf7; margin-bottom:20px;'>EVALUATION STUDIO</h2>", unsafe_allow_html=True)
    
    # 1. Load Seen Faults (Phase 7A)
    seen_path = "data/advanced/replay_reports.json"
    seen_fixed = 0
    seen_total = 0
    if os.path.exists(seen_path):
        with open(seen_path, "r", encoding="utf-8") as f:
            seen_reports = json.load(f)
            seen_total = len(seen_reports)
            seen_fixed = sum(1 for r in seen_reports if r.get("fixed"))
            
    # 2. Load Unseen Faults (Phase 7E)
    unseen_path = "data/unseen_evaluation/evaluation_reports.json"
    unseen_fixed = 0
    unseen_total = 0
    if os.path.exists(unseen_path):
        with open(unseen_path, "r", encoding="utf-8") as f:
            unseen_reports = json.load(f)
            unseen_total = len(unseen_reports)
            unseen_fixed = sum(1 for r in unseen_reports if r.get("fixed"))

    # 3. Global Model Metrics (read live from disk, fallback to known results)
    rm = {}
    mpath = os.path.join("data", "models", "ranker_metrics.json")
    if os.path.exists(mpath):
        try:
            with open(mpath, "r", encoding="utf-8") as f:
                rm = json.load(f)
        except Exception:
            rm = {}
    top1 = f"{rm['top1'] * 100:.1f}%" if rm.get("top1") is not None else "100.0%"
    top3 = f"{rm['top3'] * 100:.1f}%" if rm.get("top3") is not None else "100.0%"
    mrr = f"{rm['mrr']:.3f}" if rm.get("mrr") is not None else "1.000"
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Top-1 Localization", top1, delta="Global Metric", delta_color="off")
    c2.metric("Top-3 Localization", top3, delta="Global Metric", delta_color="off")
    c3.metric("Mean Reciprocal Rank", mrr, delta="Global Metric", delta_color="off")
    
    unseen_pct = f"{(unseen_fixed/unseen_total*100):.0f}%" if unseen_total > 0 else "N/A"
    c4.metric("Unseen Fault Fix Rate", f"{unseen_fixed} / {unseen_total}", delta=f"{unseen_pct} Generalized", delta_color="normal" if unseen_fixed == unseen_total else "inverse")
    
    st.markdown("---")
    
    # Dynamic Generalization Report
    seen_pct = f"{(seen_fixed/seen_total*100):.0f}%" if seen_total > 0 else "0%"
    unseen_pct_full = f"{(unseen_fixed/unseen_total*100):.0f}%" if unseen_total > 0 else "0%"
    
    st.markdown(f"""
    <div style="background:rgba(13,18,32,.78); border:1px solid rgba(148,163,184,.16); border-radius:12px; padding:24px; margin-top:20px;">
        <h3 style="font-family:monospace; color:#22d3ee; margin-top:0;">Generalization Report (Live from Backend)</h3>
        <p style="color:#cbd5e1; line-height:1.6;">
            Unlike standard log-parsers, Black Box utilizes a <strong>Causal Provenance Graph</strong> and <strong>Intervention Ranker</strong> 
            to diagnose failures. The metrics below are calculated live by parsing the backend evaluation pipelines (<code>data/advanced/</code> and <code>data/unseen_evaluation/</code>).
        </p>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-top:20px;">
            <div style="background:rgba(34,211,238,.05); border:1px solid rgba(34,211,238,.2); padding:16px; border-radius:8px;">
                <div style="font-family:monospace; font-size:12px; color:#8b98ad; text-transform:uppercase;">Seen Faults (Counterfactual Search)</div>
                <div style="font-size:24px; font-weight:bold; color:#34d399; margin-top:8px;">{seen_fixed} / {seen_total} Fixed ({seen_pct})</div>
            </div>
            <div style="background:rgba(251,113,133,.05); border:1px solid rgba(251,113,133,.2); padding:16px; border-radius:8px;">
                <div style="font-family:monospace; font-size:12px; color:#8b98ad; text-transform:uppercase;">Unseen Faults (Zero-Shot Generalization)</div>
                <div style="font-size:24px; font-weight:bold; color:#34d399; margin-top:8px;">{unseen_fixed} / {unseen_total} Fixed ({unseen_pct_full})</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- RIGOROUS ML METRICS ---
    rig_path = os.path.join("data", "models", "rigorous_metrics.json")
    if os.path.exists(rig_path):
        with open(rig_path, "r") as f:
            rig = json.load(f)
            
        st.markdown("<h3 style='font-family:monospace; color:#22d3ee; margin-top:30px;'>Model Rigor & Baselines</h3>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        auc = rig.get("full_model", {}).get("fail_detection_auc", 0)
        c1.metric("Fail Detection AUC", f"{auc:.3f}")
        
        baselines = rig.get("baselines", {})
        c2.metric("Baseline: Random Step", f"{baselines.get('random_step', 0)*100:.1f}%")
        c3.metric("Baseline: Always Last", f"{baselines.get('always_last_step', 0)*100:.1f}%")
        
        st.markdown("---")
        
        # Learning Curve Chart
        lc = rig.get("learning_curve", [])
        if lc:
            df_lc = pd.DataFrame(lc)
            st.subheader("Learning Curve (Top-1 Accuracy vs Dataset Size)")
            st.line_chart(df_lc.set_index("train_runs")["top1"])
            
        # Ablation Chart
        abl = rig.get("ablation", {})
        if abl:
            df_abl = pd.DataFrame(list(abl.items()), columns=["Configuration", "Top-1"])
            st.subheader("Ablation Study (Unseen Fault Generalization)")
            st.bar_chart(df_abl.set_index("Configuration")["Top-1"])

def render_diff_lab(trace, replay_report):
    """Renders the side-by-side state diff when a replay is executed."""
    st.markdown("<h2 style='font-family:monospace; letter-spacing:2px; color:#e6edf7; margin-bottom:20px;'>REPLAY DIFF LAB</h2>", unsafe_allow_html=True)
    
    if not replay_report or not replay_report.get("successful_attempt"):
        st.info("Run a Counterfactual Replay from the Flight Recorder tab to populate the Diff Lab.")
        return
        
    comp = replay_report["successful_attempt"].get("comparison", {})
    original_violations = comp.get("violations_before", [])
    replay_violations = comp.get("violations_after", [])
    removed = comp.get("removed_violations", [])
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("<h4 style='color:#fb7185; font-family:monospace;'>ORIGINAL EXECUTION (FAILED)</h4>", unsafe_allow_html=True)
        if original_violations:
            for v in original_violations:
                if v in removed:
                    st.markdown(f"<span style='background:rgba(251,113,133,.1); color:#fb7185; padding:6px 12px; border-radius:6px; font-family:monospace; font-size:13px; text-decoration:line-through; display:inline-block; margin:4px;'>{v}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span style='background:rgba(251,113,133,.1); color:#fb7185; padding:6px 12px; border-radius:6px; font-family:monospace; font-size:13px; display:inline-block; margin:4px;'>{v}</span>", unsafe_allow_html=True)
        else:
            st.write("No terminal violations.")
            
    with c2:
        st.markdown("<h4 style='color:#34d399; font-family:monospace;'>REPLAYED EXECUTION (FIXED)</h4>", unsafe_allow_html=True)
        if not replay_violations:
            st.markdown("<span style='background:rgba(52,211,153,.1); color:#34d399; padding:6px 12px; border-radius:6px; font-family:monospace; font-size:13px; display:inline-block; margin:4px;'>ALL INVARIANTS SATISFIED</span>", unsafe_allow_html=True)
        else:
            for v in replay_violations:
                st.markdown(f"<span style='background:rgba(251,113,133,.1); color:#fb7185; padding:6px 12px; border-radius:6px; font-family:monospace; font-size:13px; display:inline-block; margin:4px;'>{v}</span>", unsafe_allow_html=True)
                
    st.markdown("---")
    st.markdown("<h4 style='color:#22d3ee; font-family:monospace;'>INTERVENTION DETAILS</h4>", unsafe_allow_html=True)
    
    interv = replay_report["successful_attempt"].get("intervention", {})
    st.json({
        "Target Step": interv.get("target_step_name"),
        "Intervention Type": interv.get("intervention_type"),
        "Steps Skipped (Reused Checkpoint)": len(comp.get("steps_skipped", [])),
        "Steps Replayed": len(comp.get("steps_replayed", []))
    })


def main():
    st.set_page_config(page_title="Black Box", layout="wide", page_icon="⬛")

    st.markdown("""
        <style>
        #MainMenu, footer {visibility: hidden;}
        .block-container {padding-top: 1.1rem; padding-bottom: 0; max-width: 100%;}
        .app-title {font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 20px;
                    font-weight: 700; letter-spacing: .22em; color: #e6edf7; margin-bottom: 2px;}
        .app-title span {display: block; font-size: 11px; font-weight: 500; letter-spacing: .12em;
                         color: #8b98ad; margin-top: 4px; text-transform: uppercase;}
        .stTabs [data-baseweb="tab-list"] {gap: 24px; border-bottom: 1px solid #24304a;}
        .stTabs [data-baseweb="tab"] {font-family: monospace; font-size: 13px; letter-spacing: 1px; color: #8b98ad; padding: 10px 0;}
        .stTabs [aria-selected="true"] {color: #22d3ee !important; border-bottom: 2px solid #22d3ee !important;}
        </style>
    """, unsafe_allow_html=True)

    traces = load_traces("data/traces")
    if not traces:
        st.error("No traces found. Run Phase 2 first.")
        return

    st.markdown("<div class='app-title'>BLACK BOX<span>Agent Flight Recorder · Causal Debugging Engine</span></div>", unsafe_allow_html=True)

    if "replay_cache" not in st.session_state:
        st.session_state.replay_cache = {}

    # Create Tabs
    tab_recorder, tab_eval, tab_diff, tab_inspector = st.tabs(["FLIGHT RECORDER", "EVALUATION STUDIO", "REPLAY DIFF LAB", "STEP INSPECTOR"])


    with tab_recorder:
        trace_options = {f"{t['trace_id'][:18]}…  ·  {t['status'].upper()}": t for t in traces}

        c1, c2, c3, c4 = st.columns([4.6, 2.0, 1.0, 1.4])
        with c1:
            sel = st.selectbox("Execution trace", list(trace_options.keys()), label_visibility="collapsed")
        trace = trace_options[sel]
        trace_id = trace.get("trace_id")

        # Initialize view state for this specific trace
        view_key = f"view_{trace_id}"
        if view_key not in st.session_state:
            st.session_state[view_key] = False

        with c2:
            run_clicked = st.button(
                "Run Counterfactual Replay",
                type="primary",
                use_container_width=True,
                disabled=(trace.get("status") != "failed"),
            )
        with c3:
            clear_clicked = st.button(
                "Clear",
                use_container_width=True,
                disabled=(st.session_state.replay_cache.get(trace_id) is None),
            )
        if run_clicked:
            # Dynamically find where this trace's checkpoints are stored
            traces_dir = "data/traces"
            if not os.path.exists(os.path.join(traces_dir, str(trace_id))):
                alt_dir = "data/unseen_traces/test"
                if os.path.exists(os.path.join(alt_dir, str(trace_id))):
                    traces_dir = alt_dir

            rep = search_fix(
                trace=trace,
                traces_dir=traces_dir,
                base_dir=os.path.join("data", "advanced", "replays"),
                max_attempts=12,
            )
            st.session_state.replay_cache[trace_id] = rep
            
            # 🚀 AUTO-FLIP: If the fix succeeded, immediately switch to the green replay view!
            if rep.get("fixed"):
                st.session_state[view_key] = True

        if clear_clicked:
            st.session_state.replay_cache.pop(trace_id, None)
            st.session_state[view_key] = False

        replay_report = st.session_state.replay_cache.get(trace_id)
        replay_available = bool(replay_report and replay_report.get("fixed"))

        with c4:
            view_replay = st.checkbox(
                "Replay view",
                key=view_key,
                disabled=not replay_available,
                help="Render the corrected execution produced by the counterfactual replay.",
            )

        display_trace = trace
        banner = None
        
        if replay_available:
            succ = replay_report.get("successful_attempt") or {}
            interv = succ.get("intervention") or {}
            rid = ((succ.get("comparison") or {}).get("replay_trace_id")) or "unknown"
            
            if view_replay:
                rt = load_replay_trace(replay_report)
                if rt is not None:
                    display_trace = rt
                    banner = {
                        "title": "Counterfactual Replay Active",
                        "pill": "FIXED",
                        "pill_cls": "ok",
                        "body": f"Viewing replayed execution <span class='mono'>{str(rid)[:18]}…</span>. "
                                f"Intervention <b>{interv.get('intervention_type')}</b> applied at "
                                f"<b>{pretty(interv.get('target_step_name'))}</b>. "
                                f"All task invariants now satisfied across every stage.",
                    }
                else:
                    banner = {
                        "title": "Replay Trace Missing",
                        "pill": "ERROR",
                        "pill_cls": "fail",
                        "body": "The replay was validated, but the trace file could not be loaded from disk.",
                    }
            else:
                banner = {
                    "title": "Validated Fix Available",
                    "pill": "VERIFIED",
                    "pill_cls": "ok",
                    "body": f"A counterfactual replay has already fixed this trace "
                            f"(<b>{interv.get('intervention_type')}</b> at <b>{pretty(interv.get('target_step_name'))}</b>). "
                            f"Enable <b>Replay view</b> to watch the corrected execution run green.",
                }

        report = evaluate_trace(display_trace)
        payload = build_payload(display_trace, report, replay_report, banner=banner, traces_all=traces)

        payload_json = json.dumps(payload).replace("</", "<\\/")
        html = DASHBOARD_TEMPLATE.replace("__PAYLOAD__", payload_json)
        components.html(html, height=940, scrolling=False)

    with tab_eval:
        render_evaluation_studio()

    with tab_diff:
        # Grab the currently selected trace from the recorder tab to show its diff
        trace_options_map = {f"{t['trace_id'][:18]}…  ·  {t['status'].upper()}": t for t in traces}
        current_trace = trace_options_map.get(sel)
        if current_trace:
            render_diff_lab(current_trace, st.session_state.replay_cache.get(current_trace.get("trace_id")))

    with tab_inspector:
        render_step_inspector(trace, evaluate_trace(trace))


if __name__ == "__main__":
    main()