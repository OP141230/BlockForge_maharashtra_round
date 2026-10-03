"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Layers,
  AlertTriangle,
  Zap,
  BarChart3,
  Search,
  RotateCcw,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Clock,
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

  const failedRuns  = runs.filter((r) => r.status === "FAILED");
  const hybrid      = benchmark?.models?.blackbox_hybrid || {};

  return (
    <div className="p-8 space-y-7 max-w-6xl mx-auto w-full">

      {/* ── Page header ── */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span
              className="text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full"
              style={{ background: "#EEF2FF", color: "#3B82F6", border: "1px solid #C7D7FD" }}
            >
              Flight Control Center
            </span>
            <span className="text-xs" style={{ color: "#9BA8BF" }}>
              ● Deterministic Synthetic Traces
            </span>
          </div>
          <h1
            className="text-3xl font-black tracking-tight"
            style={{ color: "#1A2236" }}
          >
            BLACKBOX: AI Agent Flight Recorder
          </h1>
          <p className="text-sm mt-1 max-w-2xl" style={{ color: "#6B7A99" }}>
            Continuous flight recording, multi-signal hybrid fault isolation,
            counterfactual replay with side-effect blocking, and benchmark
            evaluation studio.
          </p>
        </div>

        <Link
          href="/investigation?run_id=run_travel_paris_fail"
          className="shrink-0 flex items-center gap-2 px-5 py-3 rounded-2xl font-bold text-sm text-white transition-all hover:opacity-90 active:scale-95 shadow-lg"
          style={{ background: "#3B82F6", boxShadow: "0 4px 18px rgba(59,130,246,0.35)" }}
        >
          <Search className="w-4 h-4" />
          Investigate Flagship Run
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* ── Metric cards ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: "Total Recorded Runs",
            value: loading ? "—" : runs.length,
            sub: "100% Trace Fidelity",
            icon: Layers,
            iconBg: "#EEF2FF",
            iconColor: "#3B82F6",
            valueColor: "#1A2236",
          },
          {
            label: "Flagged Failure Traces",
            value: loading ? "—" : failedRuns.length,
            sub: "Root Causes Isolated",
            icon: AlertTriangle,
            iconBg: "#FFF1F2",
            iconColor: "#EF4444",
            valueColor: "#EF4444",
          },
          {
            label: "Top-1 Diagnosis Accuracy",
            value: hybrid.top1_accuracy != null
              ? `${(hybrid.top1_accuracy * 100).toFixed(0)}%`
              : "—",
            sub: "Hybrid Ranker Model",
            icon: Zap,
            iconBg: "#F3EEFF",
            iconColor: "#7C5CFF",
            valueColor: "#7C5CFF",
          },
          {
            label: "Mean Reciprocal Rank (MRR)",
            value: hybrid.mrr != null ? hybrid.mrr.toFixed(3) : "—",
            sub: "Benchmark Baseline: 0.33",
            icon: BarChart3,
            iconBg: "#ECFDF5",
            iconColor: "#22C55E",
            valueColor: "#22C55E",
          },
        ].map((card) => (
          <div
            key={card.label}
            className="rounded-2xl p-5 flex items-center gap-4"
            style={{
              background: "#FFFFFF",
              border: "1px solid #DDE3EE",
              boxShadow: "0 2px 10px rgba(26,34,54,0.05)",
            }}
          >
            <div
              className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: card.iconBg }}
            >
              <card.icon className="w-5 h-5" style={{ color: card.iconColor }} />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium truncate" style={{ color: "#6B7A99" }}>
                {card.label}
              </p>
              <p
                className="text-2xl font-black font-mono mt-0.5 leading-none"
                style={{ color: card.valueColor }}
              >
                {card.value}
              </p>
              <p className="text-[11px] font-medium mt-1" style={{ color: "#9BA8BF" }}>
                {card.sub}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Flagship banner ── */}
      <div
        className="rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center gap-5"
        style={{
          background: "linear-gradient(135deg, #FFFBEB 0%, #FFF7E6 100%)",
          border: "1px solid #FDE68A",
          boxShadow: "0 2px 12px rgba(245,158,11,0.08)",
        }}
      >
        <div
          className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 shadow-md"
          style={{ background: "#F59E0B", boxShadow: "0 4px 14px rgba(245,158,11,0.35)" }}
        >
          <AlertTriangle className="w-6 h-6 text-white" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span
              className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
              style={{ background: "#FDE68A", color: "#92400E" }}
            >
              Flagship Demo Case
            </span>
            <span className="text-xs font-semibold" style={{ color: "#B45309" }}>
              TravelPlanner Agent
            </span>
          </div>
          <h3 className="text-base font-bold" style={{ color: "#1A2236" }}>
            Paris 7-Day Budget Failure (Arithmetic Duplication Bug)
          </h3>
          <p className="text-xs mt-1 leading-relaxed" style={{ color: "#78716C" }}>
            The agent double-added accommodation costs ($900 + $900) in{" "}
            <code
              className="px-1.5 py-0.5 rounded font-mono text-xs"
              style={{ background: "#FEF3C7", color: "#92400E" }}
            >
              budget_calculation
            </code>
            , totaling $2,950 over the $2,500 limit. BLACKBOX isolated the root
            suspect with Suspicion Score 91.2.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Link
            href="/investigation?run_id=run_travel_paris_fail"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm transition-all hover:opacity-90"
            style={{
              background: "#FFFFFF",
              border: "1px solid #E2E8F0",
              color: "#1A2236",
              boxShadow: "0 1px 4px rgba(26,34,54,0.06)",
            }}
          >
            <Search className="w-4 h-4" style={{ color: "#3B82F6" }} />
            Diagnose Trace
          </Link>
          <Link
            href="/replay?run_id=run_travel_paris_fail&step_id=step_tp_3"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm text-white transition-all hover:opacity-90"
            style={{ background: "#F59E0B", boxShadow: "0 4px 14px rgba(245,158,11,0.30)" }}
          >
            <RotateCcw className="w-4 h-4" />
            Test Counterfactual Fix
          </Link>
        </div>
      </div>

      {/* ── Runs table ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold" style={{ color: "#1A2236" }}>
              Recorded Flight Runs
            </h3>
            <p className="text-xs mt-0.5" style={{ color: "#9BA8BF" }}>
              Inspected agent executions across scenarios
            </p>
          </div>
          <Link
            href="/executions"
            className="flex items-center gap-1 text-xs font-bold hover:underline"
            style={{ color: "#3B82F6" }}
          >
            View All Runs <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div
          className="rounded-2xl overflow-hidden"
          style={{
            background: "#FFFFFF",
            border: "1px solid #DDE3EE",
            boxShadow: "0 2px 10px rgba(26,34,54,0.05)",
          }}
        >
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr style={{ background: "#F8FAFD", borderBottom: "1px solid #DDE3EE" }}>
                {["Agent & Scenario", "Status", "Steps", "Duration", "Primary Suspect", "Suspicion Score", ""].map(
                  (h) => (
                    <th
                      key={h}
                      className="py-3 px-4 font-semibold"
                      style={{ color: "#6B7A99" }}
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {runs.map((r, i) => (
                <tr
                  key={r.id}
                  className="transition-colors hover:bg-[#F8FAFD]"
                  style={{ borderBottom: i < runs.length - 1 ? "1px solid #EEF2F7" : "none" }}
                >
                  <td className="py-3.5 px-4">
                    <p className="font-semibold" style={{ color: "#1A2236" }}>
                      {r.agent_name}
                    </p>
                    <p className="text-[11px] mt-0.5 truncate max-w-[180px]" style={{ color: "#9BA8BF" }}>
                      {r.scenario}
                    </p>
                  </td>
                  <td className="py-3.5 px-4">
                    <span
                      className="inline-flex items-center gap-1.5 text-[11px] font-bold px-2.5 py-1 rounded-full uppercase"
                      style={
                        r.status === "SUCCESS"
                          ? { background: "#ECFDF5", color: "#16A34A" }
                          : { background: "#FFF1F2", color: "#DC2626" }
                      }
                    >
                      {r.status === "SUCCESS" ? (
                        <CheckCircle2 className="w-3 h-3" />
                      ) : (
                        <XCircle className="w-3 h-3" />
                      )}
                      {r.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono font-semibold" style={{ color: "#1A2236" }}>
                    {r.step_count || 6}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="flex items-center gap-1 font-mono text-xs" style={{ color: "#6B7A99" }}>
                      <Clock className="w-3 h-3" />
                      {r.total_duration_ms?.toFixed(0)}ms
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-medium" style={{ color: "#1A2236" }}>
                    {r.diagnosis_summary?.suspect_step_name ||
                      r.ground_truth_suspect_step ||
                      "—"}
                  </td>
                  <td className="py-3.5 px-4">
                    {r.diagnosis_summary?.suspicion_score ? (
                      <span
                        className="font-mono font-bold text-xs px-2.5 py-1 rounded-full"
                        style={{ background: "#FEF3C7", color: "#B45309" }}
                      >
                        {r.diagnosis_summary.suspicion_score}
                      </span>
                    ) : (
                      <span style={{ color: "#C8D0E0" }} className="font-mono">—</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <Link
                      href={`/investigation?run_id=${r.id}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all hover:opacity-90"
                      style={{
                        background: "#EEF2FF",
                        color: "#3B82F6",
                        border: "1px solid #C7D7FD",
                      }}
                    >
                      Investigate <ArrowRight className="w-3 h-3" />
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
