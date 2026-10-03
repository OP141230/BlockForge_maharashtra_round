"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  RotateCcw,
  ShieldAlert,
  Play,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Sliders,
  Code2,
  Sparkles,
} from "lucide-react";
import { fetchRun, replayRun } from "@/lib/api";
import DiffViewer from "@/components/diff-viewer";

function ReplayLabContent() {
  const searchParams = useSearchParams();
  const runIdParam = searchParams.get("run_id") || "run_travel_paris_fail";
  const stepIdParam = searchParams.get("step_id") || "step_tp_3";

  const [run, setRun] = useState<any>(null);
  const [selectedStepId, setSelectedStepId] = useState<string>(stepIdParam);
  const [deduplicate, setDeduplicate] = useState(true);
  const [budgetLimit, setBudgetLimit] = useState(2500);
  const [replayResult, setReplayResult] = useState<any>(null);
  const [isReplaying, setIsReplaying] = useState(false);

  useEffect(() => {
    fetchRun(runIdParam).then((data) => {
      setRun(data);
      if (data?.steps) {
        const suspect = data.steps.find((s: any) => s.is_root_suspect);
        if (suspect) setSelectedStepId(suspect.id);
      }
    });
  }, [runIdParam]);

  const handleExecuteReplay = async () => {
    setIsReplaying(true);
    try {
      const payload = {
        deduplicate: deduplicate,
        fixed: deduplicate,
        budget_limit: budgetLimit,
        items: deduplicate
          ? [
              {"category": "Flight (AF-104)", "amount": 750},
              {"category": "Accommodation (Hotel Le Marais)", "amount": 900},
              {"category": "Activities & Transit", "amount": 400},
            ]
          : [
              {"category": "Flight (AF-104)", "amount": 750},
              {"category": "Accommodation (Hotel Le Marais)", "amount": 900},
              {"category": "Accommodation (Hotel Le Marais)", "amount": 900},
              {"category": "Activities & Transit", "amount": 400},
            ],
      };
      const result = await replayRun(runIdParam, selectedStepId, payload);
      setReplayResult(result);
    } catch (e) {
      console.error(e);
    } finally {
      setIsReplaying(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase font-mono tracking-wider text-primary font-bold px-2 py-0.5 rounded bg-blue-50 border border-blue-200">
              Counterfactual Sandbox
            </span>
            <span className="text-xs text-text-muted">● Side-Effect Safe</span>
          </div>
          <h1 className="text-3xl font-black text-text-primary tracking-tight">
            Replay Lab & Intervention Engine
          </h1>
          <p className="text-sm text-text-muted mt-1 max-w-2xl">
            Re-execute downstream execution steps from saved checkpoints. Mutating tools (e.g. emails, payments) are strictly suppressed with mock safety notices.
          </p>
        </div>

        <div className="p-3 rounded-xl bg-purple-50 border border-purple-200 text-purple-900 text-xs flex items-center gap-2 font-medium">
          <ShieldAlert className="w-4 h-4 text-purple-600" />
          <span>Side-Effect Blocker Active</span>
        </div>
      </div>

      {/* Main Grid: Left Controls, Right Diffs */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 5 Cols: Intervention Configuration */}
        <div className="lg:col-span-5 space-y-6">
          <div className="p-6 rounded-2xl glass-card border border-panel-border space-y-5">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
              <Sliders className="w-4 h-4 text-primary" />
              <h3 className="font-bold text-sm text-text-primary">Checkpoint & Parameter Controls</h3>
            </div>

            {/* Checkpoint Step Selector */}
            <div>
              <label className="block text-xs font-semibold text-text-muted mb-1.5">
                Resume from Checkpoint Step:
              </label>
              <select
                value={selectedStepId}
                onChange={(e) => setSelectedStepId(e.target.value)}
                className="w-full p-2.5 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {run?.steps?.map((s: any) => (
                  <option key={s.id} value={s.id}>
                    Step {s.step_index}: {s.step_name} ({s.tool_name})
                    {s.is_root_suspect ? " [SUSPECT]" : ""}
                  </option>
                ))}
              </select>
            </div>

            {/* Intervention Parameter: Deduplicate Toggle */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-xs text-text-primary">Apply Arithmetic Deduplication</h4>
                  <p className="text-[11px] text-text-muted">Removes duplicate hotel line-item</p>
                </div>
                <input
                  type="checkbox"
                  checked={deduplicate}
                  onChange={(e) => setDeduplicate(e.target.checked)}
                  className="w-5 h-5 text-primary rounded focus:ring-primary"
                />
              </div>

              {/* Budget Limit Slider */}
              <div className="space-y-1.5 pt-2 border-t border-slate-200/60">
                <div className="flex justify-between text-xs">
                  <span className="text-text-muted font-medium">Budget Threshold:</span>
                  <span className="font-mono font-bold text-primary">${budgetLimit}</span>
                </div>
                <input
                  type="range"
                  min="1500"
                  max="3500"
                  step="100"
                  value={budgetLimit}
                  onChange={(e) => setBudgetLimit(Number(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>
            </div>

            {/* Safety Disclaimers */}
            <div className="text-[11px] text-text-muted bg-slate-100/80 p-3 rounded-xl space-y-1">
              <p className="font-semibold text-slate-700">Experimental Notice:</p>
              <p>Replay demonstrates experimental evidence under modified inputs, not formal proof of causality.</p>
            </div>

            {/* Run Button */}
            <button
              onClick={handleExecuteReplay}
              disabled={isReplaying}
              className="w-full py-3 px-4 rounded-xl bg-primary hover:bg-blue-600 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-primary/25 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>{isReplaying ? "Replaying Downstream..." : "Execute Counterfactual Replay"}</span>
            </button>
          </div>
        </div>

        {/* Right 7 Cols: Live Diff & Output View */}
        <div className="lg:col-span-7">
          {replayResult ? (
            <div className="p-6 rounded-2xl glass-card border border-panel-border space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-600" />
                  <h3 className="font-bold text-sm text-text-primary">Replay Outcome & Diff</h3>
                </div>
                <span
                  className={`text-xs font-bold px-2.5 py-0.5 rounded-full uppercase ${
                    replayResult.replay_status === "SUCCESS"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-rose-100 text-rose-800"
                  }`}
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
            <div className="h-full min-h-[380px] p-8 rounded-2xl glass-card border border-panel-border flex flex-col items-center justify-center text-center text-text-muted space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-blue-50 text-primary flex items-center justify-center">
                <RotateCcw className="w-6 h-6" />
              </div>
              <h4 className="font-bold text-sm text-text-primary">No Replay Executed Yet</h4>
              <p className="text-xs max-w-sm">
                Click &quot;Execute Counterfactual Replay&quot; to test your fix against the checkpointed agent state.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ReplayLabPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-text-muted">Loading Replay Lab...</div>}>
      <ReplayLabContent />
    </Suspense>
  );
}
