"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  RotateCcw, ShieldCheck, Play, Sliders, Sparkles,
} from "lucide-react";
import { fetchRun, replayRun } from "@/lib/api";
import DiffViewer from "@/components/diff-viewer";

function ReplayLabContent() {
  const searchParams = useSearchParams();
  const runIdParam   = searchParams.get("run_id") || "run_travel_paris_fail";
  const stepIdParam  = searchParams.get("step_id") || "step_tp_3";

  const [run,            setRun]            = useState<any>(null);
  const [selectedStepId, setSelectedStepId] = useState(stepIdParam);
  const [deduplicate,    setDeduplicate]    = useState(true);
  const [budgetLimit,    setBudgetLimit]    = useState(2500);
  const [replayResult,   setReplayResult]   = useState<any>(null);
  const [isReplaying,    setIsReplaying]    = useState(false);

  useEffect(() => {
    fetchRun(runIdParam).then((d) => {
      setRun(d);
      const suspect = d?.steps?.find((s: any) => s.is_root_suspect);
      if (suspect) setSelectedStepId(suspect.id);
    });
  }, [runIdParam]);

  const handleReplay = async () => {
    setIsReplaying(true);
    try {
      const payload = {
        deduplicate,
        fixed: deduplicate,
        budget_limit: budgetLimit,
        items: deduplicate
          ? [
              { category: "Flight (AF-104)", amount: 750 },
              { category: "Accommodation (Hotel Le Marais)", amount: 900 },
              { category: "Activities & Transit", amount: 400 },
            ]
          : [
              { category: "Flight (AF-104)", amount: 750 },
              { category: "Accommodation (Hotel Le Marais)", amount: 900 },
              { category: "Accommodation (Hotel Le Marais)", amount: 900 },
              { category: "Activities & Transit", amount: 400 },
            ],
      };
      const result = await replayRun(runIdParam, selectedStepId, payload);
      setReplayResult(result);
    } catch (e) { console.error(e); }
    finally { setIsReplaying(false); }
  };

  return (
    <div className="p-8 space-y-7 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full"
              style={{ background: "#EEF2FF", color: "#3B82F6", border: "1px solid #C7D7FD" }}>
              Counterfactual Sandbox
            </span>
            <span className="text-xs" style={{ color: "#9BA8BF" }}>● Side-Effect Safe</span>
          </div>
          <h1 className="text-3xl font-black tracking-tight" style={{ color: "#1A2236" }}>
            Replay Lab &amp; Intervention Engine
          </h1>
          <p className="text-sm mt-1" style={{ color: "#6B7A99" }}>
            Re-execute downstream steps from saved checkpoints. Mutating tools are strictly suppressed.
          </p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs font-semibold shrink-0"
          style={{ background: "#F5F3FF", border: "1px solid #DDD6FE", color: "#7C5CFF" }}>
          <ShieldCheck className="w-4 h-4" />
          Side-Effect Blocker Active
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Controls */}
        <div className="lg:col-span-5 space-y-5">
          <div className="rounded-2xl p-6 space-y-5"
            style={{ background: "#FFFFFF", border: "1px solid #DDE3EE", boxShadow: "0 2px 10px rgba(26,34,54,0.05)" }}>
            <div className="flex items-center gap-2 pb-3" style={{ borderBottom: "1px solid #EEF2F7" }}>
              <Sliders className="w-4 h-4" style={{ color: "#3B82F6" }} />
              <h3 className="font-bold text-sm" style={{ color: "#1A2236" }}>Checkpoint &amp; Parameter Controls</h3>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1.5" style={{ color: "#6B7A99" }}>
                Resume from Checkpoint Step:
              </label>
              <select
                value={selectedStepId}
                onChange={(e) => setSelectedStepId(e.target.value)}
                className="w-full p-2.5 rounded-xl text-xs font-semibold outline-none"
                style={{ background: "#F8FAFD", border: "1px solid #DDE3EE", color: "#1A2236" }}
              >
                {run?.steps?.map((s: any) => (
                  <option key={s.id} value={s.id}>
                    Step {s.step_index}: {s.step_name}{s.is_root_suspect ? " [SUSPECT]" : ""}
                  </option>
                ))}
              </select>
            </div>

            <div className="rounded-xl p-4 space-y-3"
              style={{ background: "#F8FAFD", border: "1px solid #EEF2F7" }}>
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-xs" style={{ color: "#1A2236" }}>Apply Arithmetic Deduplication</h4>
                  <p className="text-[11px] mt-0.5" style={{ color: "#9BA8BF" }}>Removes duplicate hotel line-item</p>
                </div>
                <div
                  onClick={() => setDeduplicate(!deduplicate)}
                  className="w-11 h-6 rounded-full relative cursor-pointer transition-all"
                  style={{ background: deduplicate ? "#3B82F6" : "#DDE3EE" }}
                >
                  <div
                    className="absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-all"
                    style={{ left: deduplicate ? 24 : 4 }}
                  />
                </div>
              </div>

              <div className="space-y-1.5 pt-2" style={{ borderTop: "1px solid #EEF2F7" }}>
                <div className="flex justify-between text-xs">
                  <span style={{ color: "#6B7A99" }}>Budget Threshold:</span>
                  <span className="font-mono font-bold" style={{ color: "#3B82F6" }}>${budgetLimit}</span>
                </div>
                <input
                  type="range" min="1500" max="3500" step="100"
                  value={budgetLimit}
                  onChange={(e) => setBudgetLimit(Number(e.target.value))}
                  className="w-full accent-blue-500"
                />
              </div>
            </div>

            <div className="rounded-xl p-3 text-[11px]"
              style={{ background: "#F8FAFD", border: "1px solid #EEF2F7", color: "#9BA8BF" }}>
              <p className="font-semibold mb-0.5" style={{ color: "#6B7A99" }}>Experimental Notice:</p>
              Replay shows experimental evidence, not formal proof of causality.
            </div>

            <button
              onClick={handleReplay}
              disabled={isReplaying}
              className="w-full py-3 rounded-xl font-bold text-sm text-white flex items-center justify-center gap-2 transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
              style={{ background: "#3B82F6", boxShadow: "0 4px 14px rgba(59,130,246,0.30)" }}
            >
              <Play className="w-4 h-4 fill-current" />
              {isReplaying ? "Replaying Downstream…" : "Execute Counterfactual Replay"}
            </button>
          </div>
        </div>

        {/* Result */}
        <div className="lg:col-span-7">
          {replayResult ? (
            <div className="rounded-2xl p-6 space-y-4"
              style={{ background: "#FFFFFF", border: "1px solid #DDE3EE", boxShadow: "0 2px 10px rgba(26,34,54,0.05)" }}>
              <div className="flex items-center justify-between pb-3" style={{ borderBottom: "1px solid #EEF2F7" }}>
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4" style={{ color: "#22C55E" }} />
                  <h3 className="font-bold text-sm" style={{ color: "#1A2236" }}>Replay Outcome &amp; Diff</h3>
                </div>
                <span
                  className="text-xs font-bold px-3 py-1 rounded-full uppercase"
                  style={replayResult.replay_status === "SUCCESS"
                    ? { background: "#ECFDF5", color: "#16A34A" }
                    : { background: "#FFF1F2", color: "#DC2626" }}
                >
                  {replayResult.replay_status}
                </span>
              </div>
              <DiffViewer
                diffSummary={replayResult.diff_summary}
                suppressedSideEffects={replayResult.suppressed_side_effects}
                replayStatus={replayResult.replay_status}
              />
            </div>
          ) : (
            <div className="h-full min-h-[360px] rounded-2xl flex flex-col items-center justify-center text-center gap-4"
              style={{ background: "#FFFFFF", border: "1px solid #DDE3EE", boxShadow: "0 2px 10px rgba(26,34,54,0.05)" }}>
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
                style={{ background: "#EEF2FF" }}>
                <RotateCcw className="w-7 h-7" style={{ color: "#3B82F6" }} />
              </div>
              <div>
                <h4 className="font-bold text-sm" style={{ color: "#1A2236" }}>No Replay Executed Yet</h4>
                <p className="text-xs mt-1 max-w-xs" style={{ color: "#9BA8BF" }}>
                  Click &ldquo;Execute Counterfactual Replay&rdquo; to test your fix against the checkpointed agent state.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ReplayLabPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm" style={{ color: "#6B7A99" }}>Loading Replay Lab…</div>}>
      <ReplayLabContent />
    </Suspense>
  );
}
