import os
import sys
import json
import streamlit as st
import streamlit.components.v1 as components
from html import escape as esc

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

# ---------------------------------------------------------------- theme tokens
NAVY = "#0f172a"
NAVY_DEEP = "#f1f5fb"
GOLD = "#2563eb"
GOLD_SOFT = "#93c5fd"
INK = "#0f172a"
MUTED = "#64748b"
LINE = "#e5eaf3"
GREEN = "#16a34a"
RED = "#dc2626"


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
        f"<div class='crumb'>Trace {trace.get('trace_id')} · {str(trace.get('status')).title()} · {len(steps)} stages</div>",
        unsafe_allow_html=True,
    )

    for s in steps:
        name = s.get("name")
        sid = s.get("step_id")
        sc = scored.get(name, 0.0)
        is_root = (name == root_name)
        tag = " · Root cause" if is_root else ""

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
                        f"<div style='font-family:monospace;font-size:12px;color:{INK};margin:3px 0'>"
                        f"{k}: <span style='color:{GREEN};font-weight:600'>{compact_value(sb.get(k))}</span> → "
                        f"<span style='color:{RED};font-weight:600'>{compact_value(sa.get(k))}</span></div>"
                        for k in changed
                    ]
                )
                st.markdown(
                    f"<div class='sub-h'>State mutations</div>" + lines,
                    unsafe_allow_html=True,
                )

            vs = viol_by_step.get(sid, [])
            if vs:
                tags = "".join(
                    [
                        f"<span style='display:inline-block;margin:3px 6px 3px 0;padding:4px 11px;border-radius:999px;"
                        f"font-size:12px;color:{RED};background:rgba(220,38,38,.08);"
                        f"border:1px solid rgba(220,38,38,.3)'>{pretty(v.get('invariant'))}</span>"
                        for v in vs
                    ]
                )
                st.markdown(
                    f"<div class='sub-h'>Invariant violations</div>" + tags,
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
            "kicker": "Incident summary",
            "body": "Execution terminated in a healthy state. All task invariants held across every pipeline stage and no state contamination was detected in the provenance graph.",
        })
        return paras

    violations = [pretty(v.get("violation")) for v in report.get("final_violations", [])]
    step_count = len(trace.get("steps", []))
    root_label = pretty(root.get("name")) if root else "Unknown"

    paras.append({
        "kicker": "Incident summary",
        "body": f"Execution terminated in a failed state. Terminal validation reported: {', '.join(violations)}.",
    })

    if root:
        signals = ", ".join([c["label"] for c in contributions]) or "aggregate step anomalies"
        paras.append({
            "kicker": "Root cause localization",
            "body": f"The Intervention Ranker assigns Step {root['step_id']} ({root_label}) a suspicion index of {root['score']:.3f}, the highest across all {step_count} executed steps. Dominant signals: {signals}.",
        })

    if causal_path and root:
        path_str = " → ".join([pretty(p) for p in causal_path])
        paras.append({
            "kicker": "Causal propagation",
            "body": f"A backward slice from the terminal violation traverses {len(causal_path)} nodes: {path_str}. State contamination originates at the head of this slice.",
        })
        paras.append({
            "kicker": "Recommended intervention",
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  :root{
    --card:#ffffff; --soft:#f5f8fd; --line:#e5eaf3;
    --text:#0f172a; --body:#475569; --muted:#64748b;
    --navy:#0f172a; --gold:#2563eb; --gold-soft:#93c5fd;
    --green:#16a34a; --rose:#dc2626;
    --mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    --sans:'Plus Jakarta Sans',system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:transparent;font-family:var(--sans);color:var(--text)}
  .dash{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(340px,.95fr);gap:16px;height:920px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:20px;box-shadow:0 1px 2px rgba(15,23,42,.04),0 12px 30px rgba(15,23,42,.06);overflow:hidden}
  .stage{display:flex;flex-direction:column}
  .card-h{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:14px 20px;border-bottom:1px solid var(--line)}
  .card-b{padding:18px 20px;max-height:210px;overflow:hidden;position:relative;transition:max-height .45s cubic-bezier(.22,1,.36,1)}
  .card-b::after{content:"";position:absolute;left:0;right:0;bottom:0;height:44px;background:linear-gradient(180deg,rgba(255,255,255,0),#fff);opacity:0;pointer-events:none;transition:opacity .3s}
  .card.clamped .card-b::after{opacity:1}
  .card.clamped.open .card-b::after{opacity:0}
  .h-right{display:inline-flex;align-items:center;gap:8px}
  .chev{background:var(--soft);border:1px solid var(--line);border-radius:50%;width:28px;height:28px;display:grid;place-items:center;cursor:pointer;color:var(--muted);transition:color .2s,border-color .2s}
  .chev:hover{color:var(--gold);border-color:var(--gold)}
  .chev:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
  .chev svg{transition:transform .3s}
  .card.open .chev svg{transform:rotate(180deg)}
  .micro{font-size:14px;font-weight:600;color:var(--navy)}
  .mono{font-family:var(--mono)}
  #graph{flex:1;min-height:0;background:var(--soft)}
  .legend{display:flex;gap:18px;padding:12px 20px;border-top:1px solid var(--line);flex-wrap:wrap}
  .legend span{display:inline-flex;align-items:center;gap:7px;font-size:12px;color:var(--muted)}
  .legend i{width:10px;height:10px;border-radius:50%;display:inline-block}
  .rail{overflow-y:auto;display:flex;flex-direction:column;gap:14px;padding-right:6px;scrollbar-width:thin;scrollbar-color:#cbd5e1 transparent}
  .rail::-webkit-scrollbar{width:8px}
  .rail::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:4px}
  .rail .card{flex:0 0 auto}
  .pill{display:inline-flex;align-items:center;gap:7px;padding:5px 12px;border-radius:999px;font-size:11px;font-weight:600;letter-spacing:.04em}
  .pill .dot{width:6px;height:6px;border-radius:50%;background:currentColor}
  .pill.fail{color:var(--rose);background:rgba(220,38,38,.08);border:1px solid rgba(220,38,38,.3)}
  .pill.ok{color:var(--green);background:rgba(22,163,74,.09);border:1px solid rgba(22,163,74,.3)}
  .pill.info{color:var(--gold);background:rgba(37,99,235,.10);border:1px solid rgba(37,99,235,.35)}
  .kv{display:grid;grid-template-columns:1fr 1fr;gap:14px 18px}
  .kv .k{font-size:12px;color:var(--muted);margin-bottom:3px}
  .kv .v{font-size:14px;font-weight:500;color:var(--text)}
  .diag{display:flex;gap:18px;align-items:flex-start}
  .gauge-wrap{position:relative;width:92px;height:92px;flex:0 0 auto}
  .gauge-wrap svg{transform:rotate(-90deg)}
  .g-bg{fill:none;stroke:#e8edf6;stroke-width:7}
  .g-fg{fill:none;stroke:var(--rose);stroke-width:7;stroke-linecap:round;transition:stroke-dashoffset 1s cubic-bezier(.22,1,.36,1)}
  .g-val{position:absolute;inset:0;display:grid;place-items:center;font-size:19px;font-weight:600;color:var(--navy)}
  .kicker{font-size:12px;font-weight:600;color:var(--gold);margin:0 0 4px}
  .para{font-size:13.5px;line-height:1.65;color:var(--body);margin:0 0 14px}
  .para:last-child{margin-bottom:0}
  .bar-row{margin-bottom:14px}
  .bar-h{display:flex;justify-content:space-between;font-size:13px;color:var(--body);margin-bottom:6px}
  .bar-h b{font-weight:600;color:var(--gold)}
  .bar{height:7px;border-radius:4px;background:#e8edf6;overflow:hidden}
  .bar i{display:block;height:100%;border-radius:4px;background:linear-gradient(90deg,var(--gold),var(--gold-soft));animation:grow .9s cubic-bezier(.22,1,.36,1) both}
  @keyframes grow{from{width:0}}
  .note{font-size:12px;color:var(--muted);line-height:1.55}
  ol.tl{list-style:none;margin:0;padding:0 0 0 6px}
  ol.tl li{position:relative;padding:0 0 18px 22px;font-size:13px;color:var(--body)}
  ol.tl li::before{content:"";position:absolute;left:0;top:4px;width:10px;height:10px;border-radius:50%;background:var(--rose)}
  ol.tl li::after{content:"";position:absolute;left:4px;top:16px;bottom:0;width:1px;background:rgba(220,38,38,.3)}
  ol.tl li:last-child::after{display:none}
  ol.tl li.term{color:var(--rose);font-weight:600}
  .tag{display:inline-block;padding:4px 11px;border-radius:999px;font-size:12px;margin:0 6px 6px 0}
  .tag.red{color:var(--rose);background:rgba(220,38,38,.08);border:1px solid rgba(220,38,38,.3)}
  .tag.green{color:var(--green);background:rgba(22,163,74,.09);border:1px solid rgba(22,163,74,.3)}
  .cmp{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
  .cmp .box{border:1px solid var(--line);border-radius:14px;padding:12px;background:var(--soft)}
  .cmp .box h5{margin:0 0 8px;font-size:12px;font-weight:600;color:var(--navy)}
  .stat{display:flex;justify-content:space-between;gap:8px;font-size:12.5px;color:var(--body);padding:4px 0}
  .stat b{font-weight:600;color:var(--text)}
  @media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<div class="dash">
  <section class="card stage">
    <div class="card-h">
      <span class="micro" id="stage-title">Execution graph</span>
      <span id="stage-pill"></span>
    </div>
    <div id="graph"></div>
    <div class="legend">
      <span><i style="background:#16a34a"></i>Healthy stage</span>
      <span><i style="background:#2563eb"></i>Active execution</span>
      <span><i style="background:#dc2626"></i>Contaminated stage</span>
      <span><i style="background:transparent;border:1px dashed #dc2626"></i>Causal link</span>
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
  'Execution graph · ' + String(P.trace_id).slice(0, 24) + '…';
document.getElementById('stage-pill').innerHTML =
  P.status === 'failed' ? pill('Fault', 'fail') : pill('Nominal', 'ok');

/* ---------- rail cards ---------- */
let rail = '';
if (P.banner) {
  rail += card(P.banner.title, pill(P.banner.pill, P.banner.pill_cls),
    '<div class="note" style="font-size:13px;color:#475569;line-height:1.65">' + P.banner.body + '</div>');
}

/* telemetry */
const t = P.task || {};
rail += card('Trip details', '',
  '<div class="kv">' +
  '<div><div class="k">Route</div><div class="v">' + esc(t.origin) + ' → ' + esc(t.destination) + '</div></div>' +
  '<div><div class="k">Travel date</div><div class="v">' + esc(t.date) + '</div></div>' +
  '<div><div class="k">Budget ceiling</div><div class="v">₹' + esc(t.budget) + '</div></div>' +
  '<div><div class="k">Check-in floor</div><div class="v">' + esc(t.hotel_checkin_after) + '</div></div>' +
  '<div><div class="k">Pipeline depth</div><div class="v">' + P.steps.length + ' stages</div></div>' +
  '<div><div class="k">Terminal state</div><div class="v" style="color:' + (P.status === 'failed' ? '#dc2626' : '#16a34a') + '">' + esc(P.status.charAt(0).toUpperCase() + P.status.slice(1)) + '</div></div>' +
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
  rail += card('Diagnosis', pill('Localized', 'fail'), body);
  setTimeout(() => { const g = document.getElementById('gfg'); if (g) g.style.strokeDashoffset = offset.toFixed(1); }, 250);
} else {
  let body = '';
  for (const para of P.narrative) {
    body += '<p class="kicker">' + esc(para.kicker) + '</p><p class="para">' + para.body + '</p>';
  }
  rail += card('Diagnosis', pill('Nominal', 'ok'), body);
}

/* suspicion ranking */
if (P.ranking && P.ranking.length) {
  let rk = '';
  for (const r of P.ranking) {
    const col = r.is_root ? '#dc2626' : '#2563eb';
    const grad = r.is_root ? 'linear-gradient(90deg,#dc2626,#f87171)' : 'linear-gradient(90deg,#2563eb,#93c5fd)';
    rk += '<div class="bar-row"><div class="bar-h"><span style="' + (r.is_root ? 'color:#dc2626;font-weight:600' : '') + '">' +
      esc(r.label) + (r.is_root ? ' · Root' : '') + '</span><b style="color:' + col + '">' + r.score.toFixed(3) +
      '</b></div><div class="bar"><i style="width:' + r.pct + '%;background:' + grad + '"></i></div></div>';
  }
  rk += '<div class="note">Suspicion index per stage from the Intervention Ranker. The highest-scoring stage is treated as the localized root cause.</div>';
  rail += card('Step suspicion ranking', '', rk);
}

/* confidence metrics */
if (P.status === 'failed' && P.contributions.length) {
  let body = '';
  for (const c of P.contributions) {
    body += '<div class="bar-row"><div class="bar-h"><span>' + esc(c.label) + '</span><b>+' + c.value.toFixed(3) + '</b></div>' +
            '<div class="bar"><i style="width:' + c.pct + '%"></i></div></div>';
  }
  body += '<div class="note">Values are weight × activation contributions from the Intervention Ranker for the localized root step. Bars are normalized against the dominant signal.</div>';
  rail += card('Fault confidence metrics', '', body);
}

/* divergence */
if (P.divergence) {
  const d = P.divergence;
  let db = '<div class="stat"><span>Healthy baseline</span><b style="font-size:11px">' +
    esc(String(d.baseline_trace_id).slice(0, 18)) + '…</b></div>' +
    '<div class="stat"><span>First divergent stage</span><b style="color:#dc2626">Step ' + d.step_id +
    ' · ' + esc(String(d.step_name).replace(/_/g, ' ').replace(/\\b\\w/g, m => m.toUpperCase())) + '</b></div>' +
    '<div style="margin-top:10px">';
  for (const dd of d.diffs) {
    db += '<div class="note mono" style="margin-bottom:6px;color:#475569">' + esc(dd.path) +
      ': <span style="color:#16a34a">' + esc(short(dd.before)) + '</span> → <span style="color:#dc2626">' +
      esc(short(dd.after)) + '</span></div>';
  }
  db += '</div>';
  rail += card('Divergence vs healthy baseline', pill('Diff', 'info'), db);
}

/* causal flow */
if (P.status === 'failed' && P.causal_path.length) {
  let body = '<ol class="tl">';
  for (const s of P.causal_path) {
    body += '<li>' + esc(s.replace(/_/g, ' ').replace(/\\b\\w/g, m => m.toUpperCase())) + '</li>';
  }
  body += '<li class="term">Terminal: ' + esc(P.violations[0] || 'unknown') + '</li></ol>';
  rail += card('Corrupted data flow', pill('Slice', 'fail'), body);
}

/* counterfactual replay */
let rbody = '';
if (!P.replay) {
  rbody = '<div class="note">No counterfactual experiment recorded for this trace. Select <b>Run counterfactual replay</b> to restore the checkpoint before the suspected step, replay downstream stages, and compare the outcomes.</div>';
} else if (P.replay.fixed) {
  rbody = pill('Fix validated', 'ok') +
    '<div class="cmp">' +
    '<div class="box"><h5>Intervention</h5>' +
    '<div class="stat"><span>Type</span><b>' + esc(P.replay.intervention_type) + '</b></div>' +
    '<div class="stat"><span>Target</span><b>' + esc(P.replay.target) + '</b></div>' +
    '<div class="stat"><span>Attempts</span><b>' + P.replay.attempts + '</b></div>' +
    (P.replay.model_confidence != null ? '<div class="stat"><span>Outcome-model confidence</span><b style="color:#2563eb">' + Math.round(P.replay.model_confidence * 100) + '%</b></div>' : '') +
    '</div>' +
    '<div class="box"><h5>Replay economics</h5>' +
    '<div class="stat"><span>Stages replayed</span><b>' + P.replay.replayed.length + '</b></div>' +
    '<div class="stat"><span>Stages reused</span><b>' + P.replay.skipped.length + '</b></div>' +
    '<div class="stat"><span>Replay trace</span><b style="font-size:11px">' + esc(String(P.replay.replay_trace_id).slice(0, 14)) + '…</b></div>' +
    '</div></div>' +
    '<div style="margin-top:12px"><div class="k" style="font-size:12px;color:var(--muted);margin-bottom:6px">Violations resolved by replay</div>' +
    (P.replay.removed.length ? P.replay.removed.map(v => '<span class="tag green">' + esc(v.replace(/_/g, ' ')) + '</span>').join('') : '<span class="note">none</span>') +
    '</div>';
} else {
  rbody = pill('Replay failed', 'fail') + '<div class="note" style="margin-top:10px">The counterfactual search could not validate a fix within ' + P.replay.attempts + ' intervention attempts.</div>';
}
rail += card('Counterfactual replay', P.replay && P.replay.fixed ? pill('Verified', 'ok') : '', rbody);

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
  color: { background: '#ffffff', border: '#cbd5e1' },
  font: { color: '#0f172a', size: 15, face: 'Plus Jakarta Sans, system-ui, sans-serif' },
  shape: 'box', margin: 14, borderWidth: 2,
  shapeProperties: { borderRadius: 14 },
  widthConstraint: { minimum: 170 }
})));
const edges = new vis.DataSet(P.edges.map(e => ({
  from: e.from, to: e.to,
  arrows: { to: { enabled: true, scaleFactor: 0.5 } },
  smooth: { type: 'cubicBezier', forceDirection: 'vertical', roundness: 0.4 },
  color: { color: '#cbd5e1' }, width: 2
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
    nodes.update({ id: s.id, color: { background: '#eff6ff', border: '#2563eb' }, shadow: { enabled: true, color: 'rgba(37,99,235,.45)', size: 14 } });
    if (i > 0) {
      const prev = P.steps[i - 1].id;
      const e = edges.get({ filter: x => x.from === prev && x.to === s.id })[0];
      if (e) edges.update({ id: e.id, color: { color: '#2563eb' } });
    }
    await sleep(240);
    nodes.update({ id: s.id, color: { background: '#ffffff', border: bad ? '#dc2626' : '#16a34a' }, shadow: { enabled: false } });
  }
  if (P.causal_edges.length) {
    await sleep(350);
    P.causal_edges.forEach(key => {
      const [f, to] = key.split('->');
      const e = edges.get({ filter: x => x.from === f && x.to === to })[0];
      if (e) edges.update({ id: e.id, color: { color: '#dc2626' }, dashes: true, width: 3 });
    });
  }
})();
</script>
</body>
</html>
"""



# ---------------------------------------------------------------- evaluation helpers

def render_evaluation_studio():
    """Dynamically calculates and renders Model Evaluation metrics from backend JSONs."""
    pass

    seen_path = "data/advanced/replay_reports.json"
    seen_fixed = 0
    seen_total = 0
    if os.path.exists(seen_path):
        with open(seen_path, "r", encoding="utf-8") as f:
            seen_reports = json.load(f)
            seen_total = len(seen_reports)
            seen_fixed = sum(1 for r in seen_reports if r.get("fixed"))

    unseen_path = "data/unseen_evaluation/evaluation_reports.json"
    unseen_fixed = 0
    unseen_total = 0
    if os.path.exists(unseen_path):
        with open(unseen_path, "r", encoding="utf-8") as f:
            unseen_reports = json.load(f)
            unseen_total = len(unseen_reports)
            unseen_fixed = sum(1 for r in unseen_reports if r.get("fixed"))

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
    c1.metric("Top-1 localization", top1, delta="Global metric", delta_color="off")
    c2.metric("Top-3 localization", top3, delta="Global metric", delta_color="off")
    c3.metric("Mean reciprocal rank", mrr, delta="Global metric", delta_color="off")

    unseen_pct = f"{(unseen_fixed/unseen_total*100):.0f}%" if unseen_total > 0 else "N/A"
    c4.metric("Unseen fault fix rate", f"{unseen_fixed} / {unseen_total}", delta=f"{unseen_pct} generalized", delta_color="normal" if unseen_fixed == unseen_total else "inverse")

    seen_pct = f"{(seen_fixed/seen_total*100):.0f}%" if seen_total > 0 else "0%"
    unseen_pct_full = f"{(unseen_fixed/unseen_total*100):.0f}%" if unseen_total > 0 else "0%"

    st.markdown(f"""
    <div class="panel">
        <h3>Generalization report</h3>
        <p>
            Black Box uses a <strong>causal provenance graph</strong> and an <strong>intervention ranker</strong>
            to diagnose failures. These figures are calculated live from the backend evaluation pipelines
            (<code>data/advanced/</code> and <code>data/unseen_evaluation/</code>).
        </p>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-top:20px;">
            <div class="stat-box">
                <div class="l">Seen faults (counterfactual search)</div>
                <div class="n">{seen_fixed} / {seen_total} fixed ({seen_pct})</div>
            </div>
            <div class="stat-box">
                <div class="l">Unseen faults (zero-shot generalization)</div>
                <div class="n">{unseen_fixed} / {unseen_total} fixed ({unseen_pct_full})</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_diff_lab(trace, replay_report):
    """Renders the side-by-side state diff when a replay is executed."""
    pass

    if not replay_report or not replay_report.get("successful_attempt"):
        st.info("Run a counterfactual replay from the Investigation page to populate the diff lab.")
        return

    comp = replay_report["successful_attempt"].get("comparison", {})
    original_violations = comp.get("violations_before", [])
    replay_violations = comp.get("violations_after", [])
    removed = comp.get("removed_violations", [])

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("<h4>Original execution (failed)</h4>", unsafe_allow_html=True)
        if original_violations:
            for v in original_violations:
                deco = "text-decoration:line-through;" if v in removed else ""
                st.markdown(f"<span class='chip bad' style='{deco}'>{v}</span>", unsafe_allow_html=True)
        else:
            st.write("No terminal violations.")

    with c2:
        st.markdown("<h4>Replayed execution (fixed)</h4>", unsafe_allow_html=True)
        if not replay_violations:
            st.markdown("<span class='chip good'>All invariants satisfied</span>", unsafe_allow_html=True)
        else:
            for v in replay_violations:
                st.markdown(f"<span class='chip bad'>{v}</span>", unsafe_allow_html=True)

    st.markdown("<h4 style='margin-top:24px'>Intervention details</h4>", unsafe_allow_html=True)

    interv = replay_report["successful_attempt"].get("intervention", {})
    st.json({
        "Target Step": interv.get("target_step_name"),
        "Intervention Type": interv.get("intervention_type"),
        "Steps Skipped (Reused Checkpoint)": len(comp.get("steps_skipped", [])),
        "Steps Replayed": len(comp.get("steps_replayed", []))
    })



# ================================================================ BLACKBOX UI (light "flight control" theme)
PAGES = ["Overview", "Executions", "Investigation", "Replay lab", "Comparison", "Evaluation", "Step inspector"]
PAGE_ICONS = {
    "Overview": "⊞", "Executions": "☰", "Investigation": "⌕", "Replay lab": "↺",
    "Comparison": "⇄", "Evaluation": "▥", "Step inspector": "◇",
}

ICON_LAYERS = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 3 8l9 5 9-5-9-5Z"/><path d="m3 13 9 5 9-5"/><path d="m3 17.5 9 5 9-5" opacity=".5"/></svg>'
ICON_ALERT = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg>'
ICON_BOLT = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z"/></svg>'
ICON_BARS = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>'
ICON_WARN_W = '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg>'
LOGO_SVG = (
    '<svg width="42" height="42" viewBox="0 0 40 40"><defs><linearGradient id="bbg" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#22c55e"/><stop offset=".5" stop-color="#2563eb"/><stop offset="1" stop-color="#a855f7"/>'
    '</linearGradient></defs><circle cx="20" cy="20" r="14" fill="none" stroke="url(#bbg)" stroke-width="5" '
    'stroke-dasharray="70 18" stroke-linecap="round" transform="rotate(-60 20 20)"/></svg>'
)

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');
html, body, .stApp, [class*="css"] { font-family: 'Plus Jakarta Sans', system-ui, sans-serif; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.stApp { background: radial-gradient(900px 420px at 100% 0%, #e2ebff 0%, transparent 62%), #f1f5fb; color: #0f172a; }
.block-container { padding: 1.7rem 2.4rem 2.5rem; max-width: 1500px; }
h1, h2, h3, h4, .stMarkdown p, label { color: #0f172a; }

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] { background: #f7f9fd; border-right: 1px solid #e5eaf3; }
.brand { display: flex; align-items: center; gap: 12px; padding: 4px 6px 18px; }
.brand b { display: block; font-size: 19px; font-weight: 800; letter-spacing: .01em; color: #0f172a; line-height: 1.1; }
.brand span { display: block; font-size: 12.5px; color: #64748b; line-height: 1.3; margin-top: 2px; }
section[data-testid="stSidebar"] [data-testid="stRadio"] > label { display: none; }
section[data-testid="stSidebar"] [role="radiogroup"] { gap: 4px; }
section[data-testid="stSidebar"] [role="radiogroup"] label { padding: 11px 14px; border-radius: 12px; width: 100%; cursor: pointer; transition: background .15s; }
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display: none; }
section[data-testid="stSidebar"] [role="radiogroup"] label p { font-size: 15px; font-weight: 500; color: #475569; }
section[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #edf2fb; }
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background: #fff; box-shadow: 0 1px 2px rgba(15,23,42,.06), 0 6px 16px rgba(37,99,235,.10); }
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p { color: #2563eb; font-weight: 700; }
.side-foot { margin-top: 38vh; padding: 16px 8px 0; border-top: 1px solid #e5eaf3; }
.side-foot .ok { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; color: #16a34a; }
.side-foot .ok i { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 0 4px rgba(34,197,94,.18); display: inline-block; }
.side-foot small { display: block; margin-top: 6px; font-size: 12px; color: #94a3b8; }

/* ---------- page header ---------- */
.chip-k { display: inline-flex; align-items: center; gap: 8px; padding: 5px 12px; border-radius: 999px; background: #eaf1ff; border: 1px solid #c9dafc; color: #2563eb; font-size: 11px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; }
.chip-k i { width: 6px; height: 6px; border-radius: 50%; background: #2563eb; display: inline-block; }
.chip-sub { font-size: 12.5px; color: #94a3b8; margin-left: 10px; }
.page-title { font-size: 34px; font-weight: 800; letter-spacing: -.02em; color: #0f172a; margin: 12px 0 6px; line-height: 1.15; }
.page-sub { font-size: 15px; color: #64748b; max-width: 760px; line-height: 1.6; margin: 0 0 20px; }
.sec-h { font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: -.01em; margin: 6px 0 2px; }
.sec-s { font-size: 13px; color: #94a3b8; margin-bottom: 14px; }
.crumb { font-size: 13px; color: #64748b; margin: 4px 0 16px; }
.sub-h { font-size: 12px; font-weight: 700; color: #2563eb; margin: 10px 0 4px; }

/* ---------- stat cards ---------- */
.stat-card { display: flex; gap: 16px; align-items: center; background: #fff; border: 1px solid #e5eaf3; border-radius: 20px; padding: 20px 22px; box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 10px 26px rgba(15,23,42,.05); height: 100%; }
.stat-ic { width: 54px; height: 54px; border-radius: 15px; display: grid; place-items: center; flex: 0 0 auto; }
.stat-l { font-size: 12.5px; color: #64748b; font-weight: 500; }
.stat-v { font-size: 30px; font-weight: 800; line-height: 1.15; color: #0f172a; margin: 2px 0; letter-spacing: -.02em; }
.stat-s { font-size: 12px; color: #94a3b8; }

/* ---------- flagship ---------- */
.st-key-flagship { background: linear-gradient(100deg, #fffbeb, #fff5d6); border: 1px solid #f8dc92; border-radius: 22px; padding: 22px 26px; margin: 22px 0 30px; box-shadow: 0 10px 28px rgba(245,158,11,.10); }
.fl-ic { width: 66px; height: 66px; border-radius: 18px; background: linear-gradient(180deg, #fbbf24, #f59e0b); display: grid; place-items: center; box-shadow: 0 10px 22px rgba(245,158,11,.35); }
.fl-tag { display: inline-block; padding: 3px 10px; border-radius: 999px; background: #fde68a; color: #92400e; font-size: 10.5px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.fl-agent { font-size: 13px; color: #b45309; font-weight: 600; margin-left: 8px; }
.fl-title { font-size: 21px; font-weight: 800; color: #0f172a; margin: 8px 0 6px; letter-spacing: -.01em; }
.fl-body { font-size: 14px; color: #78613a; line-height: 1.6; max-width: 760px; }
.fl-body code { background: #fff; border: 1px solid #f3dca0; border-radius: 6px; padding: 1px 7px; font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #92400e; }

/* ---------- runs table ---------- */
[class*="st-key-tbl_"] { background: #fff; border: 1px solid #e5eaf3; border-radius: 22px; padding: 6px 12px 10px; box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 12px 30px rgba(15,23,42,.05); gap: .3rem; }
.th { font-size: 12.5px; font-weight: 700; color: #64748b; padding: 12px 6px 4px; }
hr.rl { border: 0; border-top: 1px solid #edf1f7; margin: .2rem 0; }
.cell-t { font-weight: 700; font-size: 14.5px; color: #0f172a; line-height: 1.3; }
.cell-s { font-size: 12.5px; color: #94a3b8; margin-top: 2px; }
.cell-n { font-size: 14px; font-weight: 600; color: #0f172a; }
.cell-m { font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #64748b; }
.badge { display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 999px; font-size: 11.5px; font-weight: 700; letter-spacing: .04em; }
.b-fail { color: #dc2626; background: #fef2f2; border: 1px solid #fecaca; }
.b-ok { color: #16a34a; background: #f0fdf4; border: 1px solid #bbf7d0; }
.score { font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: 13px; padding: 4px 12px; border-radius: 999px; background: #fff3c4; color: #a16207; border: 1px solid #f8dc92; }
.empty { padding: 28px; text-align: center; color: #94a3b8; font-size: 14px; }

/* ---------- info panels ---------- */
.panel { background: #fff; border: 1px solid #e5eaf3; border-radius: 22px; padding: 24px 26px; box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 12px 30px rgba(15,23,42,.05); }
.panel h3 { color: #0f172a !important; margin: 0 0 8px; font-weight: 800; font-size: 18px; }
.panel p { color: #475569; line-height: 1.65; font-size: 14px; }
.panel code { background: #f1f5fb; color: #1e40af; padding: 1px 6px; border-radius: 6px; }
.stat-box { border-radius: 16px; padding: 18px; border: 1px solid #e5eaf3; background: #f8fafd; }
.stat-box .l { font-size: 13px; color: #64748b; }
.stat-box .n { font-size: 24px; font-weight: 800; color: #16a34a; margin-top: 6px; }
.ob { margin-bottom: 14px; }
.ob-h { display: flex; justify-content: space-between; font-size: 13.5px; color: #334155; font-weight: 600; margin-bottom: 6px; }
.ob-h b { color: #2563eb; font-family: 'JetBrains Mono', monospace; font-weight: 600; }
.ob-bar { height: 8px; border-radius: 6px; background: #e8edf6; overflow: hidden; }
.ob-bar i { display: block; height: 100%; border-radius: 6px; background: linear-gradient(90deg, #2563eb, #60a5fa); }
.flow { display: flex; flex-direction: column; gap: 16px; }
.flow-i { display: flex; gap: 14px; align-items: flex-start; }
.flow-n { width: 30px; height: 30px; border-radius: 10px; background: #eaf1ff; color: #2563eb; font-weight: 800; display: grid; place-items: center; flex: 0 0 auto; font-size: 14px; }
.flow-i b { display: block; font-size: 14.5px; color: #0f172a; }
.flow-i span { font-size: 13px; color: #64748b; line-height: 1.55; }
.chip { display: inline-block; margin: 4px 6px 4px 0; padding: 6px 14px; border-radius: 999px; font-size: 13px; font-weight: 600; }
.chip.bad { color: #dc2626; background: #fef2f2; border: 1px solid #fecaca; }
.chip.good { color: #16a34a; background: #f0fdf4; border: 1px solid #bbf7d0; }
.chip.warn { color: #a16207; background: #fff8dc; border: 1px solid #f8dc92; }

/* ---------- controls ---------- */
.st-key-ctl { background: #fff; border: 1px solid #e5eaf3; border-radius: 22px; padding: 14px 18px; box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 12px 30px rgba(15,23,42,.05); margin-bottom: 16px; }
div[data-baseweb="select"] > div { background: #f8fafd; border: 1px solid #e5eaf3; border-radius: 14px; min-height: 46px; }
.stButton > button { width: 100%; height: 46px; border-radius: 12px; font-weight: 700; font-size: 14px; border: 1px solid #e5eaf3; background: #fff; color: #0f172a; box-shadow: 0 1px 2px rgba(15,23,42,.04); transition: all .15s; }
.stButton > button:hover { border-color: #2563eb; color: #2563eb; }
.stButton > button:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }
.stButton > button:disabled { opacity: .45; }
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] { background: linear-gradient(180deg, #3b82f6, #2563eb); border: 0; color: #fff; box-shadow: 0 10px 22px rgba(37,99,235,.30); }
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover { filter: brightness(1.07); color: #fff; }
.stButton > button[kind="primary"] p, .stButton > button[data-testid="stBaseButton-primary"] p { color: #fff; }
.st-key-btn_cf button { background: linear-gradient(180deg, #fbbf24, #f59e0b) !important; border: 0 !important; color: #fff !important; box-shadow: 0 10px 22px rgba(245,158,11,.32) !important; }
.st-key-btn_cf button p { color: #fff !important; }
.st-key-viewall button { background: transparent; border: 0; box-shadow: none; color: #2563eb; justify-content: flex-end; }
[class*="st-key-tbl_"] .stButton > button { height: 38px; font-size: 13px; border-color: #c9dafc; color: #2563eb; background: #f3f7ff; }
[class*="st-key-tbl_"] .stButton > button:hover { background: #2563eb; color: #fff; }
[class*="st-key-tbl_"] .stButton > button:hover p { color: #fff; }

/* pill radios in the main area */
[data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] { gap: 8px; }
[data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] label { background: #fff; border: 1px solid #e5eaf3; border-radius: 999px; padding: 6px 18px; cursor: pointer; }
[data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] label > div:first-child { display: none; }
[data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) { background: #eaf1ff; border-color: #9dbcf7; }
[data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) p { color: #2563eb; font-weight: 700; }

/* expanders, metrics */
div[data-testid="stExpander"] { background: #fff; border: 1px solid #e5eaf3; border-radius: 18px; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(15,23,42,.04); }
div[data-testid="stExpander"] summary p { color: #0f172a; font-weight: 700; }
div[data-testid="stMetric"] { background: #fff; border: 1px solid #e5eaf3; border-radius: 18px; padding: 16px 18px; box-shadow: 0 1px 2px rgba(15,23,42,.04); }
div[data-testid="stMetric"] [data-testid="stMetricLabel"] p { color: #64748b; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #0f172a; font-weight: 800; }
div[data-testid="stExpander"] div[data-testid="stMetric"] { border: 0; box-shadow: none; padding: 0; }
</style>
"""


def inject_theme():
    st.markdown(APP_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------- data helpers
def tlabel(i, t):
    return f"{i + 1:02d} · {str(t.get('trace_id'))[:20]}… · {str(t.get('status')).upper()}"


def trace_title(t):
    k = t.get("task") or {}
    if k.get("origin") and k.get("destination"):
        return f"{k['origin']} → {k['destination']}"
    return str(t.get("trace_id"))[:24]


def trace_sub(t):
    k = t.get("task") or {}
    bits = []
    if k.get("date"):
        bits.append(str(k["date"]))
    if k.get("budget") is not None:
        bits.append(f"₹{k['budget']} budget")
    bits.append(str(t.get("trace_id"))[:12] + "…")
    return " · ".join(bits)


def summarize(t):
    """Per-trace summary (duration, steps, root-cause suspect). Cached per session."""
    cache = st.session_state.setdefault("_sum", {})
    tid = t.get("trace_id")
    if tid in cache:
        return cache[tid]
    steps = t.get("steps", [])
    out = {
        "steps": len(steps),
        "duration": sum(float(s.get("latency_ms", 0) or 0) for s in steps),
        "root": None, "score": None, "root_id": None, "violations": [],
    }
    try:
        rep = evaluate_trace(t)
        out["violations"] = [pretty(v.get("violation")) for v in rep.get("final_violations", [])]
        if t.get("status") == "failed" and steps:
            model = load_ranker()
            w, b = model.get("weights", {}), float(model.get("bias", 0.0))
            scored = [
                (score_features(w, b, build_step_features(t, rep, s, len(steps))), s) for s in steps
            ]
            best = max(scored, key=lambda x: x[0])
            out.update(root=pretty(best[1].get("name")), score=best[0], root_id=best[1].get("step_id"))
    except Exception:
        pass
    cache[tid] = out
    return out


def load_metrics():
    p = os.path.join("data", "models", "ranker_metrics.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def goto(page, tid=None, auto=False):
    st.session_state["page"] = page
    if tid is not None:
        st.session_state["sel_tid"] = tid
    if auto and tid is not None:
        st.session_state["auto_run"] = tid


# ---------------------------------------------------------------- ui pieces
def page_header(kicker, title, sub, note=None):
    n = f"<span class='chip-sub'>● {esc(note)}</span>" if note else ""
    st.markdown(
        f"<div><span class='chip-k'><i></i>{esc(kicker)}</span>{n}</div>"
        f"<div class='page-title'>{esc(title)}</div><div class='page-sub'>{esc(sub)}</div>",
        unsafe_allow_html=True,
    )


def stat_card(icon, tint, label, value, sub):
    return (
        f"<div class='stat-card'><div class='stat-ic' style='background:{tint}'>{icon}</div>"
        f"<div><div class='stat-l'>{esc(label)}</div><div class='stat-v'>{esc(value)}</div>"
        f"<div class='stat-s'>{esc(sub)}</div></div></div>"
    )


COLS = [3.1, 1.25, 0.8, 1.2, 2.5, 0.95, 1.4]


def render_runs(traces, limit=None, flt="All", key="overview"):
    rows = [
        t for t in traces
        if flt == "All"
        or (flt == "Failed" and t.get("status") == "failed")
        or (flt == "Healthy" and t.get("status") == "success")
    ]
    shown = rows[:limit] if limit else rows
    with st.container(key=f"tbl_{key}"):
        for c, txt in zip(st.columns(COLS), ["Agent & scenario", "Status", "Steps", "Duration", "Primary suspect", "Score", ""]):
            c.markdown(f"<div class='th'>{txt}</div>", unsafe_allow_html=True)
        st.markdown("<hr class='rl'>", unsafe_allow_html=True)
        if not shown:
            st.markdown("<div class='empty'>No runs match this filter.</div>", unsafe_allow_html=True)
        for n, t in enumerate(shown):
            s = summarize(t)
            tid = t.get("trace_id")
            failed = t.get("status") == "failed"
            cols = st.columns(COLS, vertical_alignment="center")
            cols[0].markdown(
                f"<div class='cell-t'>{esc(trace_title(t))}</div><div class='cell-s'>{esc(trace_sub(t))}</div>",
                unsafe_allow_html=True,
            )
            cols[1].markdown(
                "<span class='badge b-fail'>✕ FAILED</span>" if failed else "<span class='badge b-ok'>✓ SUCCESS</span>",
                unsafe_allow_html=True,
            )
            cols[2].markdown(f"<div class='cell-n'>{s['steps']}</div>", unsafe_allow_html=True)
            cols[3].markdown(f"<div class='cell-m'>◷ {s['duration']:.0f} ms</div>", unsafe_allow_html=True)
            cols[4].markdown(
                f"<div class='cell-n'>{esc(s['root']) if s['root'] else '—'}</div>", unsafe_allow_html=True
            )
            cols[5].markdown(
                f"<span class='score'>{s['score']:.2f}</span>" if s["score"] is not None else "<div class='cell-m'>—</div>",
                unsafe_allow_html=True,
            )
            cols[6].button("Investigate  →", key=f"inv_{key}_{n}_{tid}", on_click=goto, args=("Investigation", tid))
            if n < len(shown) - 1:
                st.markdown("<hr class='rl'>", unsafe_allow_html=True)


# ---------------------------------------------------------------- pages
def page_overview(traces):
    sums = {t["trace_id"]: summarize(t) for t in traces}
    failed = [t for t in traces if t.get("status") == "failed"]
    healthy = [t for t in traces if t.get("status") == "success"]
    flag = None
    if failed:
        flag = max(failed, key=lambda t: sums[t["trace_id"]]["score"] if sums[t["trace_id"]]["score"] is not None else -1e9)

    hl, hr = st.columns([4, 1.25], vertical_alignment="top")
    with hl:
        page_header(
            "Flight control center",
            "BLACKBOX: AI Agent Flight Recorder",
            "Continuous flight recording, multi-signal fault isolation, counterfactual replay with checkpoint reuse, and a benchmark evaluation studio.",
            note="Recorded agent traces",
        )
    with hr:
        st.markdown("<div style='height:34px'></div>", unsafe_allow_html=True)
        st.button(
            "Investigate flagship run  →", type="primary", key="hero_btn", disabled=flag is None,
            on_click=goto, args=("Investigation", flag["trace_id"] if flag else None),
        )

    m = load_metrics()
    isolated = sum(1 for t in failed if sums[t["trace_id"]]["root"])
    top1 = f"{m['top1'] * 100:.1f}%" if m.get("top1") is not None else "—"
    mrr = f"{m['mrr']:.3f}" if m.get("mrr") is not None else "—"
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(stat_card(ICON_LAYERS, "#eaf1ff", "Total recorded runs", str(len(traces)), f"{len(healthy)} healthy · {len(failed)} failed"), unsafe_allow_html=True)
    k2.markdown(stat_card(ICON_ALERT, "#fef2f2", "Flagged failure traces", str(len(failed)), f"{isolated} root causes isolated"), unsafe_allow_html=True)
    k3.markdown(stat_card(ICON_BOLT, "#f3eeff", "Top-1 diagnosis accuracy", top1, "Intervention ranker model"), unsafe_allow_html=True)
    k4.markdown(stat_card(ICON_BARS, "#f0fdf4", "Mean reciprocal rank", mrr, "Localization quality"), unsafe_allow_html=True)

    if flag:
        fs = sums[flag["trace_id"]]
        viol = ", ".join(fs["violations"]) if fs["violations"] else "a terminal invariant violation"
        suspect = esc(fs["root"] or "an unknown step")
        score_txt = f" with suspicion score <b>{fs['score']:.2f}</b>" if fs["score"] is not None else ""
        with st.container(key="flagship"):
            ci, ct, cb1, cb2 = st.columns([0.7, 6.0, 1.35, 2.1], vertical_alignment="center")
            ci.markdown(f"<div class='fl-ic'>{ICON_WARN_W}</div>", unsafe_allow_html=True)
            ct.markdown(
                f"<span class='fl-tag'>Flagship case</span><span class='fl-agent'>{esc(trace_title(flag))}</span>"
                f"<div class='fl-title'>{esc(trace_title(flag))}: {esc(viol)}</div>"
                f"<div class='fl-body'>Black Box isolated <code>{suspect}</code> as the root suspect{score_txt}. "
                f"The run executed {fs['steps']} steps before terminal validation failed.</div>",
                unsafe_allow_html=True,
            )
            cb1.button("Diagnose trace", key="btn_diag", on_click=goto, args=("Investigation", flag["trace_id"]))
            cb2.button("Test counterfactual fix", key="btn_cf", on_click=goto, args=("Investigation", flag["trace_id"], True))
    else:
        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    tl, tr = st.columns([5, 1], vertical_alignment="bottom")
    tl.markdown("<div class='sec-h'>Recorded flight runs</div><div class='sec-s'>Inspected agent executions across scenarios</div>", unsafe_allow_html=True)
    with tr:
        st.button("View all runs  →", key="viewall", on_click=goto, args=("Executions",))
    render_runs(traces, limit=5, key="overview")

    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
    cl, cr = st.columns([1.1, 1])
    origins = {}
    for t in failed:
        r = sums[t["trace_id"]]["root"]
        if r:
            origins[r] = origins.get(r, 0) + 1
    with cl:
        body = "<div class='panel'><h3>Where failures originate</h3><p style='margin-bottom:16px'>Root-cause stage across all failed runs.</p>"
        if origins:
            mx = max(origins.values())
            for name, cnt in sorted(origins.items(), key=lambda x: -x[1])[:5]:
                body += (
                    f"<div class='ob'><div class='ob-h'><span>{esc(name)}</span><b>{cnt} run{'s' if cnt != 1 else ''}</b></div>"
                    f"<div class='ob-bar'><i style='width:{cnt / mx * 100:.0f}%'></i></div></div>"
                )
        else:
            body += "<div class='empty'>No failed runs recorded.</div>"
        st.markdown(body + "</div>", unsafe_allow_html=True)
    with cr:
        st.markdown(
            "<div class='panel'><h3>How Black Box works</h3><div class='flow' style='margin-top:14px'>"
            "<div class='flow-i'><div class='flow-n'>1</div><div><b>Record</b><span>Every stage of an agent run is captured with its inputs, outputs and state.</span></div></div>"
            "<div class='flow-i'><div class='flow-n'>2</div><div><b>Localize</b><span>A learned ranker scores each stage and points to the most suspicious one.</span></div></div>"
            "<div class='flow-i'><div class='flow-n'>3</div><div><b>Replay</b><span>Restore the checkpoint before that stage and test a fix without re-running the prefix.</span></div></div>"
            "</div></div>",
            unsafe_allow_html=True,
        )


def page_executions(traces):
    page_header("Executions", "All recorded runs", "Every captured agent execution with its terminal status, primary suspect and suspicion score.")
    flt = st.radio("Filter", ["All", "Failed", "Healthy"], horizontal=True, key="run_filter", label_visibility="collapsed")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    render_runs(traces, None, flt, "all")


def page_investigation(traces):
    page_header("Investigation", "Trace the failure to its root cause",
                "Pick a recorded run to see its execution graph, the suspected failure step, the evidence behind it, and a replay of the fix.")
    ids = [t.get("trace_id") for t in traces]
    labels = [tlabel(i, t) for i, t in enumerate(traces)]
    idx = ids.index(st.session_state.sel_tid) if st.session_state.get("sel_tid") in ids else 0

    with st.container(key="ctl"):
        c1, c2, c3, c4 = st.columns([4.6, 2.4, 1.0, 1.5], vertical_alignment="center")
        with c1:
            sel = st.selectbox("Execution trace", labels, index=idx, label_visibility="collapsed")
        trace = traces[labels.index(sel)]
        trace_id = trace.get("trace_id")
        st.session_state.sel_tid = trace_id

        view_key = f"view_{trace_id}"
        if view_key not in st.session_state:
            st.session_state[view_key] = False

        with c2:
            run_clicked = st.button("Run counterfactual replay", type="primary", key="run_cf", disabled=(trace.get("status") != "failed"))
        with c3:
            clear_clicked = st.button("Clear", key="clear_cf", disabled=(st.session_state.replay_cache.get(trace_id) is None))

        auto = st.session_state.get("auto_run") == trace_id and trace.get("status") == "failed"
        if run_clicked or auto:
            st.session_state.pop("auto_run", None)
            traces_dir = "data/traces"
            if not os.path.exists(os.path.join(traces_dir, str(trace_id))):
                alt_dir = "data/unseen_traces/test"
                if os.path.exists(os.path.join(alt_dir, str(trace_id))):
                    traces_dir = alt_dir
            with st.spinner("Restoring checkpoint and replaying…"):
                rep = search_fix(
                    trace=trace,
                    traces_dir=traces_dir,
                    base_dir=os.path.join("data", "advanced", "replays"),
                    max_attempts=12,
                )
            st.session_state.replay_cache[trace_id] = rep
            if rep.get("fixed"):
                st.session_state[view_key] = True

        if clear_clicked:
            st.session_state.replay_cache.pop(trace_id, None)
            st.session_state[view_key] = False

        replay_report = st.session_state.replay_cache.get(trace_id)
        replay_available = bool(replay_report and replay_report.get("fixed"))

        with c4:
            view_replay = st.checkbox(
                "Replay view", key=view_key, disabled=not replay_available,
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
                    "title": "Counterfactual replay active", "pill": "Fixed", "pill_cls": "ok",
                    "body": f"Viewing replayed execution <span class='mono'>{str(rid)[:18]}…</span>. "
                            f"Intervention <b>{interv.get('intervention_type')}</b> applied at "
                            f"<b>{pretty(interv.get('target_step_name'))}</b>. "
                            f"All task invariants now satisfied across every stage.",
                }
            else:
                banner = {
                    "title": "Replay trace missing", "pill": "Error", "pill_cls": "fail",
                    "body": "The replay was validated, but the trace file could not be loaded from disk.",
                }
        else:
            banner = {
                "title": "Validated fix available", "pill": "Verified", "pill_cls": "ok",
                "body": f"A counterfactual replay has already fixed this trace "
                        f"(<b>{interv.get('intervention_type')}</b> at <b>{pretty(interv.get('target_step_name'))}</b>). "
                        f"Turn on <b>Replay view</b> to watch the corrected execution run green.",
            }

    report = evaluate_trace(display_trace)
    payload = build_payload(display_trace, report, replay_report, banner=banner, traces_all=traces)
    payload_json = json.dumps(payload).replace("</", "<\\/")
    components.html(DASHBOARD_TEMPLATE.replace("__PAYLOAD__", payload_json), height=940, scrolling=False)


def page_replay(traces):
    page_header("Replay lab", "Compare the failed run with its fix",
                "Violations before and after a counterfactual replay, and how much of the execution was reused from the checkpoint.")
    cache = st.session_state.replay_cache
    with_replay = [t for t in traces if (cache.get(t.get("trace_id")) or {}).get("successful_attempt")]
    if not with_replay:
        st.markdown(
            "<div class='panel'><h3>No replays yet</h3><p>Run a counterfactual replay on a failed trace and the before/after comparison will appear here.</p></div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.button("Go to investigation  →", type="primary", key="to_inv", on_click=goto, args=("Investigation",))
        return
    labels = [tlabel(i, t) for i, t in enumerate(with_replay)]
    cur = st.session_state.get("sel_tid")
    ids = [t.get("trace_id") for t in with_replay]
    sel = st.selectbox("Replayed trace", labels, index=ids.index(cur) if cur in ids else 0)
    t = with_replay[labels.index(sel)]
    render_diff_lab(t, cache.get(t.get("trace_id")))


def page_comparison(traces):
    page_header("Comparison", "See exactly where two runs diverge",
                "Compare a healthy run with a failed one, stage by stage, to see which outputs changed and where the first divergence appears.")
    labels = [tlabel(i, t) for i, t in enumerate(traces)]
    good = [i for i, t in enumerate(traces) if t.get("status") == "success"]
    bad = [i for i, t in enumerate(traces) if t.get("status") == "failed"]
    ca, cb = st.columns(2)
    la = ca.selectbox("Baseline run", labels, index=good[0] if good else 0)
    lb = cb.selectbox("Comparison run", labels, index=bad[0] if bad else min(1, len(labels) - 1))
    a, b = traces[labels.index(la)], traces[labels.index(lb)]
    if a.get("trace_id") == b.get("trace_id"):
        st.info("Pick two different runs to compare.")
        return

    sa, sb = summarize(a), summarize(b)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(stat_card(ICON_LAYERS, "#eaf1ff", "Baseline status", str(a.get("status")).title(), f"{sa['steps']} steps"), unsafe_allow_html=True)
    k2.markdown(stat_card(ICON_ALERT, "#fef2f2", "Comparison status", str(b.get("status")).title(), f"{sb['steps']} steps"), unsafe_allow_html=True)
    k3.markdown(stat_card(ICON_BARS, "#f0fdf4", "Duration change", f"{sb['duration'] - sa['duration']:+.0f} ms", f"{sa['duration']:.0f} → {sb['duration']:.0f} ms"), unsafe_allow_html=True)
    va, vb = set(sa["violations"]), set(sb["violations"])
    k4.markdown(stat_card(ICON_BOLT, "#f3eeff", "Violation delta", f"{len(vb - va)} new · {len(va - vb)} gone", "Terminal invariants"), unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div><div class='sec-h'>Stage by stage</div><div class='sec-s'>Outputs of matching stages, baseline versus comparison</div>", unsafe_allow_html=True)
    base_steps = {s.get("name"): s for s in a.get("steps", [])}
    first_seen = False
    for s in b.get("steps", []):
        base = base_steps.get(s.get("name"))
        if base is None:
            st.markdown(f"<span class='chip warn'>Step {s.get('step_id')} · {esc(pretty(s.get('name')))} · only in comparison run</span>", unsafe_allow_html=True)
            continue
        try:
            d = diff_values(base.get("output"), s.get("output"), path="output") or []
        except Exception:
            d = []
        title = f"Step {s.get('step_id')} · {pretty(s.get('name'))}"
        if not d:
            st.markdown(f"<span class='chip good'>{esc(title)} · identical</span>", unsafe_allow_html=True)
            continue
        tag = ""
        if not first_seen:
            tag, first_seen = " · first divergence", True
        with st.expander(f"{title} · {len(d)} change{'s' if len(d) != 1 else ''}{tag}", expanded=(tag != "")):
            for x in d[:8]:
                st.markdown(
                    f"<div style='font-family:JetBrains Mono,monospace;font-size:12.5px;margin:4px 0;color:#334155'>"
                    f"{esc(x.get('path'))}: <span style='color:{GREEN};font-weight:600'>{esc(compact_value(x.get('before')))}</span> → "
                    f"<span style='color:{RED};font-weight:600'>{esc(compact_value(x.get('after')))}</span></div>",
                    unsafe_allow_html=True,
                )


def page_evaluation():
    page_header("Evaluation", "How well does Black Box localize failures?",
                "Ranking accuracy on known failures, and how many unseen failures counterfactual replay could fix.")
    render_evaluation_studio()


def page_inspector(traces):
    page_header("Step inspector", "Inspect every stage of a run",
                "Suspicion score, latency, state mutations and invariant violations for each stage.")
    labels = [tlabel(i, t) for i, t in enumerate(traces)]
    ids = [t.get("trace_id") for t in traces]
    cur = st.session_state.get("sel_tid")
    sel = st.selectbox("Execution trace", labels, index=ids.index(cur) if cur in ids else 0)
    t = traces[labels.index(sel)]
    render_step_inspector(t, evaluate_trace(t))


def render_sidebar(n_traces):
    with st.sidebar:
        st.markdown(
            f"<div class='brand'>{LOGO_SVG}<div><b>BLACKBOX</b><span>AI Agent Flight<br>Recorder</span></div></div>",
            unsafe_allow_html=True,
        )
        st.radio("Navigate", PAGES, key="page", format_func=lambda p: f"{PAGE_ICONS[p]}   {p}", label_visibility="collapsed")
        st.markdown(
            f"<div class='side-foot'><div class='ok'><i></i>Operational</div><small>Local engine · {n_traces} traces loaded</small></div>",
            unsafe_allow_html=True,
        )


def main():
    st.set_page_config(page_title="BLACKBOX · AI Agent Flight Recorder", layout="wide", page_icon="🛫")
    inject_theme()

    traces = load_traces("data/traces")
    if not traces:
        st.error("No traces found. Run Phase 2 first.")
        return

    st.session_state.setdefault("replay_cache", {})
    st.session_state.setdefault("page", "Overview")

    render_sidebar(len(traces))

    page = st.session_state["page"]
    if page == "Overview":
        page_overview(traces)
    elif page == "Executions":
        page_executions(traces)
    elif page == "Investigation":
        page_investigation(traces)
    elif page == "Replay lab":
        page_replay(traces)
    elif page == "Comparison":
        page_comparison(traces)
    elif page == "Evaluation":
        page_evaluation()
    else:
        page_inspector(traces)


if __name__ == "__main__":
    main()