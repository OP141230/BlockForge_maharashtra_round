"use client";

import React, { useEffect, useState } from "react";
import {
  GitCompare,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Sparkles,
  Layers,
} from "lucide-react";
import { compareRuns } from "@/lib/api";

export default function ComparePage() {
  const [targetRunId] = useState("run_travel_paris_fail");
  const [baselineRunId] = useState("run_travel_paris_success");
  const [comparison, setComparison] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    compareRuns(targetRunId, baselineRunId)
      .then((data) => {
        setComparison(data);
        setLoading(false);
      })
      .catch((e) => {
        console.error(e);
        setLoading(false);
      });
  }, [targetRunId, baselineRunId]);

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs uppercase font-mono tracking-wider text-primary font-bold px-2 py-0.5 rounded bg-blue-50 border border-blue-200">
            Divergence Studio
          </span>
          <span className="text-xs text-text-muted">● Causal State Alignment</span>
        </div>
        <h1 className="text-3xl font-black text-text-primary tracking-tight">
          Run Comparison & First Divergence Analysis
        </h1>
        <p className="text-sm text-text-muted mt-1 max-w-2xl">
          Side-by-side alignment of failed vs successful executions to pinpoint the exact step where behavior first diverged from nominal behavior.
        </p>
      </div>

      {/* First Meaningful Divergence Spotlight */}
      {comparison?.first_meaningful_divergence && (
        <div className="p-6 rounded-2xl bg-amber-500/10 border border-amber-300/80 glass-card flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-500 text-white flex items-center justify-center shrink-0 shadow-md">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-amber-200 text-amber-900">
                First Meaningful Divergence Found
              </span>
              <span className="text-xs font-bold text-amber-800">
                Step {comparison.first_meaningful_divergence.step_index}: {comparison.first_meaningful_divergence.step_name}
              </span>
            </div>
            <p className="text-xs text-text-primary font-bold mt-1">
              Tool: <code className="bg-slate-100 px-1.5 py-0.5 rounded font-mono text-amber-800">{comparison.first_meaningful_divergence.tool_name}</code>
            </p>
            <p className="text-xs text-text-muted mt-1">
              {comparison.first_meaningful_divergence.root_cause_diagnosis}
            </p>

            {/* Side-by-side state diff */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 font-mono text-xs">
              <div className="p-3 rounded-xl bg-white border border-rose-200">
                <span className="text-[10px] uppercase font-bold text-rose-700">Failed Run Output:</span>
                <pre className="mt-1 text-[11px] text-rose-800 overflow-x-auto">
                  {JSON.stringify(comparison.first_meaningful_divergence.target_output, null, 2)}
                </pre>
              </div>
              <div className="p-3 rounded-xl bg-white border border-emerald-200">
                <span className="text-[10px] uppercase font-bold text-emerald-700">Baseline Success Output:</span>
                <pre className="mt-1 text-[11px] text-emerald-800 overflow-x-auto">
                  {JSON.stringify(comparison.first_meaningful_divergence.baseline_output, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Step Alignment Table */}
      <div className="space-y-4">
        <h3 className="text-base font-bold text-text-primary">Aligned Execution Pipeline Steps</h3>
        <div className="rounded-2xl glass-card border border-panel-border overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-panel-border text-text-muted font-semibold">
                <th className="py-3 px-4">Index</th>
                <th className="py-3 px-4">Step & Tool Name</th>
                <th className="py-3 px-4">Failed Run Status</th>
                <th className="py-3 px-4">Baseline Run Status</th>
                <th className="py-3 px-4">State Alignment</th>
                <th className="py-3 px-4 text-right">Target / Baseline Duration</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {comparison?.aligned_steps?.map((s: any) => (
                <tr
                  key={s.step_index}
                  className={`transition-colors ${
                    s.is_divergent ? "bg-amber-50/60 font-semibold" : "hover:bg-slate-50/50"
                  }`}
                >
                  <td className="py-3.5 px-4">{s.step_index}</td>
                  <td className="py-3.5 px-4 font-sans font-bold text-text-primary">
                    {s.step_name} <span className="font-mono text-text-muted text-[11px]">({s.tool_name})</span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                        s.target_run_status === "SUCCESS"
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-rose-100 text-rose-700"
                      }`}
                    >
                      {s.target_run_status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded uppercase bg-emerald-100 text-emerald-700">
                      {s.baseline_run_status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-sans">
                    {s.is_divergent ? (
                      <span className="text-xs font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full flex items-center gap-1 w-fit">
                        <AlertTriangle className="w-3 h-3" />
                        Divergent
                      </span>
                    ) : (
                      <span className="text-xs text-emerald-700 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        Aligned
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-right text-text-muted">
                    {s.target_duration_ms.toFixed(0)}ms / {s.baseline_duration_ms.toFixed(0)}ms
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
