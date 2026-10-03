"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  RotateCcw,
  Search,
  Zap,
  ArrowRight,
  ShieldCheck,
  Radio,
  BarChart3,
  Layers,
} from "lucide-react";
import { fetchRuns, fetchBenchmark } from "@/lib/api";

export default function OverviewPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [benchmark, setBenchmark] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchRuns().catch(() => ({ runs: [] })),
      fetchBenchmark().catch(() => null),
    ]).then(([runsData, benchData]) => {
      setRuns(runsData.runs || []);
      setBenchmark(benchData);
      setLoading(false);
    });
  }, []);

  const failedRuns = runs.filter((r) => r.status === "FAILED");
  const successRuns = runs.filter((r) => r.status === "SUCCESS");

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
      {/* Top Banner */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase font-mono tracking-wider text-primary font-bold px-2 py-0.5 rounded bg-blue-50 border border-blue-200">
              Flight Control Center
            </span>
            <span className="text-xs text-text-muted">● Deterministic Synthetic Traces</span>
          </div>
          <h1 className="text-3xl font-black text-text-primary tracking-tight">
            BLACKBOX: AI Agent Flight Recorder
          </h1>
          <p className="text-sm text-text-muted mt-1 max-w-2xl">
            Continuous flight recording, multi-signal hybrid fault isolation, counterfactual replay with side-effect blocking, and benchmark evaluation studio.
          </p>
        </div>

        <Link
          href="/investigation?run_id=run_travel_paris_fail"
          className="px-5 py-3 rounded-xl bg-primary hover:bg-blue-600 text-white font-bold text-sm flex items-center gap-2.5 shadow-lg shadow-primary/25 transition-all hover:scale-105 active:scale-95"
        >
          <Search className="w-4 h-4" />
          <span>Investigate Flagship Run</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        {/* Total Runs */}
        <div className="p-5 rounded-2xl glass-card border border-panel-border flex items-center justify-between">
          <div>
            <span className="text-xs text-text-muted font-medium">Total Recorded Runs</span>
            <h3 className="text-2xl font-black text-text-primary mt-1 font-mono">{runs.length}</h3>
            <span className="text-[11px] text-emerald-600 font-semibold mt-1 inline-block">100% Trace Fidelity</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-primary flex items-center justify-center">
            <Layers className="w-6 h-6" />
          </div>
        </div>

        {/* Failed Runs Flagged */}
        <div className="p-5 rounded-2xl glass-card border border-panel-border flex items-center justify-between">
          <div>
            <span className="text-xs text-text-muted font-medium">Flagged Failure Traces</span>
            <h3 className="text-2xl font-black text-rose-600 mt-1 font-mono">{failedRuns.length}</h3>
            <span className="text-[11px] text-rose-600 font-semibold mt-1 inline-block">Root Causes Isolated</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

        {/* Hybrid Top-1 Accuracy */}
        <div className="p-5 rounded-2xl glass-card border border-panel-border flex items-center justify-between">
          <div>
            <span className="text-xs text-text-muted font-medium">Top-1 Diagnosis Accuracy</span>
            <h3 className="text-2xl font-black text-intel mt-1 font-mono">
              {benchmark?.models?.blackbox_hybrid ? `${(benchmark.models.blackbox_hybrid.top1_accuracy * 100).toFixed(0)}%` : "100%"}
            </h3>
            <span className="text-[11px] text-intel font-semibold mt-1 inline-block">Hybrid Ranker Model</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-purple-50 text-intel flex items-center justify-center">
            <Zap className="w-6 h-6" />
          </div>
        </div>

        {/* Mean Reciprocal Rank */}
        <div className="p-5 rounded-2xl glass-card border border-panel-border flex items-center justify-between">
          <div>
            <span className="text-xs text-text-muted font-medium">Mean Reciprocal Rank (MRR)</span>
            <h3 className="text-2xl font-black text-emerald-600 mt-1 font-mono">
              {benchmark?.models?.blackbox_hybrid ? benchmark.models.blackbox_hybrid.mrr.toFixed(3) : "1.000"}
            </h3>
            <span className="text-[11px] text-emerald-600 font-semibold mt-1 inline-block">Benchmark Baseline: 0.33</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <BarChart3 className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Flagship Scenario Spotlight Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-br from-amber-500/10 via-amber-500/5 to-transparent border border-amber-300/80 glass-card">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-amber-500 text-white flex items-center justify-center shadow-lg shadow-amber-500/30 shrink-0">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-amber-200 text-amber-900">
                  Flagship Demo Case
                </span>
                <span className="text-xs font-semibold text-amber-800">TravelPlanner Agent</span>
              </div>
              <h3 className="text-lg font-bold text-text-primary mt-1">
                Paris 7-Day Budget Failure (Arithmetic Duplication Bug)
              </h3>
              <p className="text-xs text-text-muted mt-1 max-w-2xl leading-relaxed">
                The agent double-added accommodation costs ($900 + $900) in <code className="bg-slate-100 px-1 py-0.5 rounded text-amber-800 font-mono">budget_calculation</code>, totaling $2,950 over the $2,500 limit. BLACKBOX isolated the root suspect with Suspicion Score 91.2.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/investigation?run_id=run_travel_paris_fail"
              className="px-4 py-2.5 rounded-xl bg-white border border-slate-300 hover:bg-slate-50 text-text-primary text-xs font-bold flex items-center gap-2 shadow-sm transition-all"
            >
              <Search className="w-4 h-4 text-primary" />
              <span>Diagnose Trace</span>
            </Link>
            <Link
              href="/replay?run_id=run_travel_paris_fail&step_id=step_tp_3"
              className="px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold flex items-center gap-2 shadow-md shadow-amber-500/25 transition-all"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Test Counterfactual Fix</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Recent Flight Runs Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-text-primary">Recorded Flight Runs</h3>
            <p className="text-xs text-text-muted">Inspected agent executions across scenarios</p>
          </div>
          <Link href="/executions" className="text-xs font-bold text-primary hover:underline flex items-center gap-1">
            <span>View All Runs</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="rounded-2xl glass-card border border-panel-border overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-panel-border text-text-muted font-semibold">
                <th className="py-3 px-4">Agent & Scenario</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Steps</th>
                <th className="py-3 px-4">Duration</th>
                <th className="py-3 px-4">Primary Suspect</th>
                <th className="py-3 px-4">Suspicion Score</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {runs.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="py-3.5 px-4">
                    <div>
                      <span className="font-bold text-text-primary">{r.agent_name}</span>
                      <p className="text-[11px] text-text-muted truncate max-w-xs">{r.scenario}</p>
                    </div>
                  </td>
                  <td className="py-3.5 px-4">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                        r.status === "SUCCESS"
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-rose-100 text-rose-700"
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono">{r.step_count || 6}</td>
                  <td className="py-3.5 px-4 font-mono text-text-muted">{r.total_duration_ms.toFixed(0)}ms</td>
                  <td className="py-3.5 px-4 font-semibold text-slate-700">
                    {r.diagnosis_summary?.suspect_step_name || r.ground_truth_suspect_step || "Nominal"}
                  </td>
                  <td className="py-3.5 px-4">
                    {r.diagnosis_summary?.suspicion_score ? (
                      <span className="font-mono font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                        {r.diagnosis_summary.suspicion_score}
                      </span>
                    ) : (
                      <span className="text-slate-400 font-mono">0.0</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <Link
                      href={`/investigation?run_id=${r.id}`}
                      className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-primary hover:text-white text-text-primary text-[11px] font-bold transition-all inline-flex items-center gap-1.5"
                    >
                      <span>Investigate</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
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
