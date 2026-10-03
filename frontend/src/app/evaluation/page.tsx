"use client";

import React, { useEffect, useState } from "react";
import { BarChart3, Play, CheckCircle2, Zap } from "lucide-react";
import { fetchBenchmark, runBenchmarkSuite } from "@/lib/api";

export default function EvaluationStudioPage() {
  const [benchmark, setBenchmark] = useState<any>(null);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => { fetchBenchmark().then(setBenchmark); }, []);

  const handleRun = async () => {
    setIsRunning(true);
    try { setBenchmark(await runBenchmarkSuite()); }
    catch (e) { console.error(e); }
    finally { setIsRunning(false); }
  };

  const models  = benchmark?.models || benchmark?.baselines || {};
  const hybrid  = models?.blackbox_hybrid   || {};
  const last    = models?.baseline_last_step || {};
  const rule    = models?.baseline_rule_only || {};
  const anomaly = models?.baseline_anomaly_only || {};
  const cases   = benchmark?.detailed_cases || benchmark?.detailed_results || [];

  const metricCards = [
    { label: "Top-1 Accuracy", value: hybrid.top1_accuracy != null ? `${(hybrid.top1_accuracy*100).toFixed(0)}%` : "—",
      sub: `vs Last-Step: ${last.top1_accuracy != null ? (last.top1_accuracy*100).toFixed(0)+"%" : "—"}`,
      color: "#7C5CFF", bg: "#F3EEFF" },
    { label: "Top-3 Accuracy", value: hybrid.top3_accuracy != null ? `${(hybrid.top3_accuracy*100).toFixed(0)}%` : "—",
      sub: "Reliable Isolation", color: "#3B82F6", bg: "#EEF2FF" },
    { label: "Mean Reciprocal Rank", value: hybrid.mrr != null ? hybrid.mrr.toFixed(3) : "—",
      sub: `Rule-Only: ${rule.mrr?.toFixed(3) || "—"}`, color: "#22C55E", bg: "#ECFDF5" },
  ];

  return (
    <div className="p-8 space-y-7 max-w-6xl mx-auto w-full">
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full"
              style={{ background: "#EEF2FF", color: "#3B82F6", border: "1px solid #C7D7FD" }}>
              Evaluation Studio
            </span>
          </div>
          <h1 className="text-3xl font-black tracking-tight" style={{ color: "#1A2236" }}>
            Diagnosis Accuracy &amp; Benchmark Suite
          </h1>
          <p className="text-sm mt-1" style={{ color: "#6B7A99" }}>
            Empirically evaluating fault localization accuracy (Top-1, Top-3, MRR) across labeled failure test cases.
          </p>
        </div>
        <button onClick={handleRun} disabled={isRunning}
          className="shrink-0 flex items-center gap-2 px-5 py-3 rounded-2xl font-bold text-sm text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
          style={{ background: "#3B82F6", boxShadow: "0 4px 18px rgba(59,130,246,0.30)" }}>
          <Play className="w-4 h-4 fill-current" />
          {isRunning ? "Running…" : "Execute Benchmark Suite"}
        </button>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-3 gap-5">
        {metricCards.map((c) => (
          <div key={c.label} className="rounded-2xl p-6 space-y-2"
            style={{ background: "#FFFFFF", border: "1px solid #DDE3EE", boxShadow: "0 2px 10px rgba(26,34,54,0.05)" }}>
            <p className="text-xs font-medium" style={{ color: "#6B7A99" }}>{c.label}</p>
            <p className="text-3xl font-black font-mono" style={{ color: c.color }}>{c.value}</p>
            <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: "#EEF2F7" }}>
              <div className="h-full rounded-full" style={{
                background: c.color,
                width: c.value.includes("%") ? c.value : "70%",
              }} />
            </div>
            <p className="text-[11px]" style={{ color: "#9BA8BF" }}>{c.sub}</p>
          </div>
        ))}
      </div>

      {/* Small benchmark notice */}
      {cases.length < 20 && (
        <div className="rounded-xl px-4 py-3 text-xs font-medium"
          style={{ background: "#FFFBEB", border: "1px solid #FDE68A", color: "#92400E" }}>
          Small benchmark ({cases.length} cases): results are illustrative.
          Report counts alongside percentages — no weight tuning on test split.
        </div>
      )}

      {/* Cases table */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-bold" style={{ color: "#1A2236" }}>
            Labeled Failure Test Suite ({cases.length} cases)
          </h3>
          <span className="text-xs font-mono" style={{ color: "#9BA8BF" }}>Ground-Truth Verified</span>
        </div>
        <div className="rounded-2xl overflow-hidden"
          style={{ background: "#FFFFFF", border: "1px solid #DDE3EE", boxShadow: "0 2px 10px rgba(26,34,54,0.05)" }}>
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr style={{ background: "#F8FAFD", borderBottom: "1px solid #DDE3EE" }}>
                {["Case ID", "Agent & Name", "Fault Category", "Ground Truth", "Rank", "Score", "Result"].map((h) => (
                  <th key={h} className="py-3 px-4 font-semibold" style={{ color: "#6B7A99" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cases.map((tc: any, i: number) => (
                <tr key={tc.case_id}
                  className="transition-colors hover:bg-[#F8FAFD]"
                  style={{ borderBottom: i < cases.length-1 ? "1px solid #EEF2F7" : "none" }}>
                  <td className="py-3.5 px-4 font-mono font-bold" style={{ color: "#9BA8BF" }}>{tc.case_id}</td>
                  <td className="py-3.5 px-4">
                    <span className="font-semibold" style={{ color: "#1A2236" }}>{tc.name}</span>
                    <span className="font-mono ml-1 text-[11px]" style={{ color: "#9BA8BF" }}>({tc.agent})</span>
                  </td>
                  <td className="py-3.5 px-4" style={{ color: "#6B7A99" }}>{tc.fault_category}</td>
                  <td className="py-3.5 px-4">
                    <span className="font-mono font-bold px-2 py-0.5 rounded"
                      style={{ background: "#FEF3C7", color: "#B45309" }}>{tc.ground_truth}</span>
                  </td>
                  <td className="py-3.5 px-4 font-mono font-bold" style={{ color: "#3B82F6" }}>#{tc.hybrid_rank}</td>
                  <td className="py-3.5 px-4 font-mono font-bold" style={{ color: "#F59E0B" }}>
                    {tc.hybrid_suspicion_score || "—"}
                  </td>
                  <td className="py-3.5 px-4">
                    {tc.is_top1 ? (
                      <span className="inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full"
                        style={{ background: "#ECFDF5", color: "#16A34A" }}>
                        <CheckCircle2 className="w-3 h-3" /> Top-1
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full"
                        style={{ background: "#EEF2FF", color: "#3B82F6" }}>
                        Top-3 (#{tc.hybrid_rank})
                      </span>
                    )}
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
