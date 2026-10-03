"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { RotateCcw, ShieldCheck, Play, Sliders, Sparkles } from "lucide-react";
import { fetchRun, replayRun } from "@/lib/api";
import DiffViewer from "@/components/diff-viewer";

const card: React.CSSProperties = {
  background: "#FFFFFF", borderRadius: 16,
  border: "1px solid #E4EAF4",
  boxShadow: "0 2px 10px rgba(26,34,54,0.05)",
};

function ReplayLabContent() {
  const searchParams  = useSearchParams();
  const runId         = searchParams.get("run_id") || "run_travel_paris_fail";
  const defaultStepId = searchParams.get("step_id") || "step_tp_3";

  const [run,        setRun]        = useState<any>(null);
  const [stepId,     setStepId]     = useState(defaultStepId);
  const [dedup,      setDedup]      = useState(true);
  const [budget,     setBudget]     = useState(2500);
  const [result,     setResult]     = useState<any>(null);
  const [replaying,  setReplaying]  = useState(false);

  useEffect(() => {
    fetchRun(runId).then((d) => {
      setRun(d);
      const s = d?.steps?.find((s: any) => s.is_root_suspect);
      if (s) setStepId(s.id);
    });
  }, [runId]);

  const handleReplay = async () => {
    setReplaying(true);
    try {
      const r = await replayRun(runId, stepId, {
        deduplicate: dedup, fixed: dedup, budget_limit: budget,
        items: dedup
          ? [{ category: "Flight (AF-104)", amount: 750 }, { category: "Accommodation (Hotel Le Marais)", amount: 900 }, { category: "Activities & Transit", amount: 400 }]
          : [{ category: "Flight (AF-104)", amount: 750 }, { category: "Accommodation (Hotel Le Marais)", amount: 900 }, { category: "Accommodation (Hotel Le Marais)", amount: 900 }, { category: "Activities & Transit", amount: 400 }],
      });
      setResult(r);
    } catch {}
    finally { setReplaying(false); }
  };

  return (
    <div className="p-7 space-y-6 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", padding: "3px 10px", borderRadius: 999, background: "#EFF6FF", color: "#3B82F6", border: "1px solid #BFDBFE" }}>
              Counterfactual Sandbox
            </span>
            <span style={{ fontSize: 11, color: "#9BA8BF" }}>● Side-Effect Safe</span>
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 900, color: "#1A2236", letterSpacing: "-0.02em", margin: 0 }}>
            Replay Lab &amp; Intervention Engine
          </h1>
          <p style={{ fontSize: 13, color: "#6B7A99", marginTop: 5 }}>
            Re-execute downstream steps from checkpoints. Mutating tools are strictly suppressed.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 7, padding: "9px 16px", borderRadius: 12, background: "#F5F3FF", border: "1px solid #DDD6FE", flexShrink: 0 }}>
          <ShieldCheck style={{ width: 15, height: 15, color: "#7C5CFF" }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: "#7C5CFF" }}>Side-Effect Blocker Active</span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "5fr 7fr", gap: 16, alignItems: "start" }}>
        {/* Controls */}
        <div style={{ ...card, padding: "22px 22px", display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, paddingBottom: 14, borderBottom: "1px solid #EEF2F8" }}>
            <Sliders style={{ width: 15, height: 15, color: "#3B82F6" }} />
            <h3 style={{ fontSize: 13, fontWeight: 800, color: "#1A2236", margin: 0 }}>Checkpoint &amp; Parameter Controls</h3>
          </div>

          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: "#6B7A99", display: "block", marginBottom: 6 }}>
              Resume from Checkpoint:
            </label>
            <select value={stepId} onChange={(e) => setStepId(e.target.value)} style={{ width: "100%", padding: "9px 12px", borderRadius: 10, border: "1px solid #E4EAF4", background: "#F8FAFD", fontSize: 12, fontWeight: 600, color: "#1A2236", outline: "none" }}>
              {run?.steps?.map((s: any) => (
                <option key={s.id} value={s.id}>
                  Step {s.step_index}: {s.step_name}{s.is_root_suspect ? " [SUSPECT]" : ""}
                </option>
              ))}
            </select>
          </div>

          <div style={{ padding: "14px 16px", borderRadius: 12, background: "#F8FAFD", border: "1px solid #EEF2F8", display: "flex", flexDirection: "column", gap: 14 }}>
            {/* Toggle */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <p style={{ fontSize: 12, fontWeight: 700, color: "#1A2236", margin: "0 0 2px" }}>Apply Arithmetic Deduplication</p>
                <p style={{ fontSize: 11, color: "#9BA8BF", margin: 0 }}>Removes duplicate hotel line-item</p>
              </div>
              <div onClick={() => setDedup(!dedup)} style={{ width: 44, height: 24, borderRadius: 99, background: dedup ? "#3B82F6" : "#E4EAF4", position: "relative", cursor: "pointer", transition: "background 0.2s", flexShrink: 0 }}>
                <div style={{ position: "absolute", top: 3, left: dedup ? 22 : 3, width: 18, height: 18, borderRadius: "50%", background: "white", boxShadow: "0 1px 4px rgba(0,0,0,0.15)", transition: "left 0.2s" }} />
              </div>
            </div>

            {/* Slider */}
            <div style={{ borderTop: "1px solid #EEF2F8", paddingTop: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: "#6B7A99", fontWeight: 500 }}>Budget Threshold</span>
                <span style={{ fontSize: 12, fontFamily: "monospace", fontWeight: 800, color: "#3B82F6" }}>${budget}</span>
              </div>
              <input type="range" min="1500" max="3500" step="100" value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                style={{ width: "100%", accentColor: "#3B82F6" }}
              />
            </div>
          </div>

          <div style={{ padding: "10px 12px", borderRadius: 9, background: "#F8FAFD", border: "1px solid #EEF2F8", fontSize: 11, color: "#9BA8BF", lineHeight: 1.55 }}>
            <strong style={{ color: "#6B7A99" }}>Experimental Notice:</strong>{" "}
            Replay shows experimental evidence under modified inputs, not formal proof of causality.
          </div>

          <button onClick={handleReplay} disabled={replaying} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, padding: "11px 16px", borderRadius: 12, border: "none", fontWeight: 700, fontSize: 13, color: "white", cursor: replaying ? "not-allowed" : "pointer", background: "#3B82F6", boxShadow: "0 4px 14px rgba(59,130,246,0.28)", opacity: replaying ? 0.65 : 1, transition: "opacity 0.15s" }}>
            <Play style={{ width: 14, height: 14 }} />
            {replaying ? "Replaying Downstream…" : "Execute Counterfactual Replay"}
          </button>
        </div>

        {/* Result */}
        {result ? (
          <div style={{ ...card, padding: "22px 22px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: 14, marginBottom: 14, borderBottom: "1px solid #EEF2F8" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Sparkles style={{ width: 16, height: 16, color: "#22C55E" }} />
                <h3 style={{ fontSize: 13, fontWeight: 800, color: "#1A2236", margin: 0 }}>Replay Outcome &amp; Diff</h3>
              </div>
              <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 12px", borderRadius: 999, textTransform: "uppercase", ...(result.replay_status === "SUCCESS" ? { background: "#F0FDF4", color: "#16A34A" } : { background: "#FFF1F2", color: "#DC2626" }) }}>
                {result.replay_status}
              </span>
            </div>
            <DiffViewer diffSummary={result.diff_summary} suppressedSideEffects={result.suppressed_side_effects} replayStatus={result.replay_status} />
          </div>
        ) : (
          <div style={{ ...card, padding: "48px 24px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", gap: 14, minHeight: 320 }}>
            <div style={{ width: 52, height: 52, borderRadius: 16, background: "#EFF6FF", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <RotateCcw style={{ width: 24, height: 24, color: "#3B82F6" }} />
            </div>
            <div>
              <h4 style={{ fontSize: 14, fontWeight: 800, color: "#1A2236", margin: "0 0 6px" }}>No Replay Executed Yet</h4>
              <p style={{ fontSize: 12, color: "#9BA8BF", maxWidth: 260, lineHeight: 1.55, margin: 0 }}>
                Click "Execute Counterfactual Replay" to test your fix against the checkpointed agent state.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ReplayLabPage() {
  return (
    <Suspense fallback={<div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "#6B7A99" }}>Loading Replay Lab…</div>}>
      <ReplayLabContent />
    </Suspense>
  );
}
