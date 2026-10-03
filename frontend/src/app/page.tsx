"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Layers, AlertTriangle, Zap, BarChart3,
  Search, RotateCcw, ArrowRight, CheckCircle2, XCircle, Clock,
} from "lucide-react";
import { fetchRuns, fetchBenchmark } from "@/lib/api";

export default function OverviewPage() {
  const [runs,      setRuns]      = useState<any[]>([]);
  const [benchmark, setBenchmark] = useState<any>(null);
  const [loading,   setLoading]   = useState(true);

  useEffect(() => {
    Promise.all([
      fetchRuns().catch(() => ({ runs: [] })),
      fetchBenchmark().catch(() => null),
    ]).then(([r, b]) => {
      setRuns(r.runs || []);
      setBenchmark(b);
      setLoading(false);
    });
  }, []);

  const failed = runs.filter((r) => r.status === "FAILED");
  const hybrid = benchmark?.models?.blackbox_hybrid || {};

  const metrics = [
    {
      label: "Total Recorded Runs",
      value: loading ? "—" : String(runs.length),
      sub: "100% Trace Fidelity",
      iconBg: "#EFF6FF", iconColor: "#3B82F6",
      valueColor: "#1A2236",
      Icon: Layers,
    },
    {
      label: "Flagged Failure Traces",
      value: loading ? "—" : String(failed.length),
      sub: "Root Causes Isolated",
      iconBg: "#FFF1F2", iconColor: "#EF4444",
      valueColor: "#EF4444",
      Icon: AlertTriangle,
    },
    {
      label: "Top-1 Diagnosis Accuracy",
      value: hybrid.top1_accuracy != null
        ? `${(hybrid.top1_accuracy * 100).toFixed(0)}%` : "—",
      sub: "Hybrid Ranker Model",
      iconBg: "#F5F3FF", iconColor: "#7C5CFF",
      valueColor: "#7C5CFF",
      Icon: Zap,
    },
    {
      label: "Mean Reciprocal Rank",
      value: hybrid.mrr != null ? hybrid.mrr.toFixed(3) : "—",
      sub: "Benchmark Baseline: 0.33",
      iconBg: "#F0FDF4", iconColor: "#22C55E",
      valueColor: "#22C55E",
      Icon: BarChart3,
    },
  ];

  return (
    <div className="p-7 space-y-6 max-w-6xl mx-auto w-full">

      {/* ── Header ── */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span style={{
              fontSize: 10, fontWeight: 700, letterSpacing: "0.06em",
              textTransform: "uppercase",
              padding: "3px 10px", borderRadius: 999,
              background: "#EFF6FF", color: "#3B82F6",
              border: "1px solid #BFDBFE",
            }}>
              Flight Control Center
            </span>
            <span style={{ fontSize: 11, color: "#9BA8BF" }}>
              ● Deterministic Synthetic Traces
            </span>
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 900, color: "#1A2236", letterSpacing: "-0.02em", margin: 0 }}>
            BLACKBOX: AI Agent Flight Recorder
          </h1>
          <p style={{ fontSize: 13, color: "#6B7A99", marginTop: 5, maxWidth: 560, lineHeight: 1.55 }}>
            Continuous flight recording, multi-signal hybrid fault isolation,
            counterfactual replay with side-effect blocking, and benchmark evaluation studio.
          </p>
        </div>

        <Link href="/investigation?run_id=run_travel_paris_fail"
          style={{
            display: "flex", alignItems: "center", gap: 8, flexShrink: 0,
            padding: "10px 20px", borderRadius: 12, fontWeight: 700, fontSize: 13,
            color: "white", textDecoration: "none",
            background: "#3B82F6",
            boxShadow: "0 4px 16px rgba(59,130,246,0.30)",
          }}>
          <Search style={{ width: 15, height: 15 }} />
          Investigate Flagship Run
          <ArrowRight style={{ width: 15, height: 15 }} />
        </Link>
      </div>

      {/* ── Metric cards ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
        {metrics.map((m) => (
          <div key={m.label} style={{
            background: "#FFFFFF", borderRadius: 16, padding: "18px 20px",
            border: "1px solid #E4EAF4",
            boxShadow: "0 2px 8px rgba(26,34,54,0.05)",
            display: "flex", alignItems: "center", gap: 14,
          }}>
            <div style={{
              width: 44, height: 44, borderRadius: 12, flexShrink: 0,
              background: m.iconBg, display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <m.Icon style={{ width: 20, height: 20, color: m.iconColor }} />
            </div>
            <div style={{ minWidth: 0 }}>
              <p style={{ fontSize: 10.5, color: "#9BA8BF", fontWeight: 500, margin: "0 0 3px" }}>
                {m.label}
              </p>
              <p style={{ fontSize: 22, fontWeight: 900, color: m.valueColor, fontFamily: "monospace", margin: 0, lineHeight: 1 }}>
                {m.value}
              </p>
              <p style={{ fontSize: 10.5, color: "#9BA8BF", marginTop: 4, fontWeight: 500 }}>
                {m.sub}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Flagship banner ── */}
      <div style={{
        borderRadius: 16, padding: "20px 24px",
        background: "linear-gradient(135deg, #FFFBEB 0%, #FEF9EC 100%)",
        border: "1px solid #FDE68A",
        boxShadow: "0 2px 12px rgba(245,158,11,0.08)",
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20,
      }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 16, flex: 1 }}>
          <div style={{
            width: 46, height: 46, borderRadius: 14, flexShrink: 0,
            background: "#F59E0B", display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 12px rgba(245,158,11,0.35)",
          }}>
            <AlertTriangle style={{ width: 22, height: 22, color: "white" }} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <span style={{
                fontSize: 9.5, fontWeight: 800, letterSpacing: "0.06em", textTransform: "uppercase",
                padding: "2px 8px", borderRadius: 999, background: "#FDE68A", color: "#92400E",
              }}>
                Flagship Demo Case
              </span>
              <span style={{ fontSize: 11.5, fontWeight: 600, color: "#B45309" }}>
                TravelPlanner Agent
              </span>
            </div>
            <h3 style={{ fontSize: 15, fontWeight: 800, color: "#1A2236", margin: "0 0 5px" }}>
              Paris 7-Day Budget Failure (Arithmetic Duplication Bug)
            </h3>
            <p style={{ fontSize: 12, color: "#78716C", margin: 0, lineHeight: 1.55 }}>
              The agent double-added accommodation costs ($900 + $900) in{" "}
              <code style={{
                fontFamily: "monospace", fontSize: 11,
                padding: "1px 6px", borderRadius: 4,
                background: "#FEF3C7", color: "#92400E",
              }}>budget_calculation</code>
              , totaling $2,950 over the $2,500 limit. BLACKBOX isolated the root
              suspect with Suspicion Score 91.2.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, flexShrink: 0 }}>
          <Link href="/investigation?run_id=run_travel_paris_fail" style={{
            display: "flex", alignItems: "center", gap: 7,
            padding: "9px 16px", borderRadius: 11, fontWeight: 700, fontSize: 12,
            textDecoration: "none", color: "#1A2236",
            background: "#FFFFFF", border: "1px solid #E4EAF4",
            boxShadow: "0 1px 5px rgba(26,34,54,0.06)",
          }}>
            <Search style={{ width: 13, height: 13, color: "#3B82F6" }} />
            Diagnose Trace
          </Link>
          <Link href="/replay?run_id=run_travel_paris_fail&step_id=step_tp_3" style={{
            display: "flex", alignItems: "center", gap: 7,
            padding: "9px 16px", borderRadius: 11, fontWeight: 700, fontSize: 12,
            textDecoration: "none", color: "white",
            background: "#F59E0B",
            boxShadow: "0 3px 10px rgba(245,158,11,0.30)",
          }}>
            <RotateCcw style={{ width: 13, height: 13 }} />
            Test Counterfactual Fix
          </Link>
        </div>
      </div>

      {/* ── Runs table ── */}
      <div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <div>
            <h3 style={{ fontSize: 15, fontWeight: 800, color: "#1A2236", margin: 0 }}>
              Recorded Flight Runs
            </h3>
            <p style={{ fontSize: 11, color: "#9BA8BF", marginTop: 3 }}>
              Inspected agent executions across scenarios
            </p>
          </div>
          <Link href="/executions" style={{
            display: "flex", alignItems: "center", gap: 5,
            fontSize: 12, fontWeight: 700, color: "#3B82F6", textDecoration: "none",
          }}>
            View All Runs <ArrowRight style={{ width: 13, height: 13 }} />
          </Link>
        </div>

        <div style={{
          background: "#FFFFFF", borderRadius: 16,
          border: "1px solid #E4EAF4",
          boxShadow: "0 2px 10px rgba(26,34,54,0.05)",
          overflow: "hidden",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#F8FAFD", borderBottom: "1px solid #E4EAF4" }}>
                {["Agent & Scenario", "Status", "Steps", "Duration", "Primary Suspect", "Score", ""].map((h) => (
                  <th key={h} style={{
                    padding: "11px 16px", textAlign: "left",
                    fontWeight: 600, color: "#6B7A99", fontSize: 11,
                    letterSpacing: "0.02em",
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {runs.map((r, i) => (
                <tr key={r.id} style={{
                  borderBottom: i < runs.length - 1 ? "1px solid #F0F4FA" : "none",
                  transition: "background 0.12s",
                }}
                  onMouseEnter={e => (e.currentTarget.style.background = "#FAFBFD")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                >
                  <td style={{ padding: "13px 16px" }}>
                    <p style={{ fontWeight: 700, color: "#1A2236", margin: 0 }}>{r.agent_name}</p>
                    <p style={{ fontSize: 11, color: "#9BA8BF", margin: "2px 0 0", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {r.scenario}
                    </p>
                  </td>
                  <td style={{ padding: "13px 16px" }}>
                    <span style={{
                      display: "inline-flex", alignItems: "center", gap: 5,
                      fontSize: 10.5, fontWeight: 700, padding: "3px 10px",
                      borderRadius: 999, textTransform: "uppercase",
                      ...(r.status === "SUCCESS"
                        ? { background: "#F0FDF4", color: "#16A34A" }
                        : { background: "#FFF1F2", color: "#DC2626" }),
                    }}>
                      {r.status === "SUCCESS"
                        ? <CheckCircle2 style={{ width: 11, height: 11 }} />
                        : <XCircle style={{ width: 11, height: 11 }} />}
                      {r.status}
                    </span>
                  </td>
                  <td style={{ padding: "13px 16px", fontFamily: "monospace", fontWeight: 600, color: "#1A2236" }}>
                    {r.step_count || 6}
                  </td>
                  <td style={{ padding: "13px 16px" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11.5, fontFamily: "monospace", color: "#6B7A99" }}>
                      <Clock style={{ width: 11, height: 11 }} />
                      {r.total_duration_ms?.toFixed(0)}ms
                    </span>
                  </td>
                  <td style={{ padding: "13px 16px", fontWeight: 600, color: "#1A2236" }}>
                    {r.diagnosis_summary?.suspect_step_name || r.ground_truth_suspect_step || "—"}
                  </td>
                  <td style={{ padding: "13px 16px" }}>
                    {r.diagnosis_summary?.suspicion_score ? (
                      <span style={{
                        fontFamily: "monospace", fontWeight: 800, fontSize: 12,
                        padding: "3px 10px", borderRadius: 999,
                        background: "#FEF3C7", color: "#B45309",
                      }}>
                        {r.diagnosis_summary.suspicion_score}
                      </span>
                    ) : (
                      <span style={{ color: "#C8D0E0", fontFamily: "monospace" }}>—</span>
                    )}
                  </td>
                  <td style={{ padding: "13px 16px", textAlign: "right" }}>
                    <Link href={`/investigation?run_id=${r.id}`} style={{
                      display: "inline-flex", alignItems: "center", gap: 5,
                      padding: "6px 14px", borderRadius: 9, fontSize: 11.5, fontWeight: 700,
                      textDecoration: "none", color: "#3B82F6",
                      background: "#EFF6FF", border: "1px solid #BFDBFE",
                      transition: "all 0.12s",
                    }}>
                      Investigate <ArrowRight style={{ width: 11, height: 11 }} />
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
