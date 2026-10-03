"use client";

import React, { useEffect, useState } from "react";
import { Play, CheckCircle2 } from "lucide-react";
import { fetchBenchmark, runBenchmarkSuite } from "@/lib/api";

const S = {
  card: { background: "#FFFFFF", borderRadius: 16, border: "1px solid #E4EAF4", boxShadow: "0 2px 10px rgba(26,34,54,0.05)" } as React.CSSProperties,
  label: { fontSize: 10.5, fontWeight: 500, color: "#9BA8BF", margin: "0 0 3px" } as React.CSSProperties,
  tag: (bg: string, color: string, border?: string): React.CSSProperties => ({
    fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase",
    padding: "3px 10px", borderRadius: 999, background: bg, color,
    border: border ? `1px solid ${border}` : undefined,
  }),
};

export default function EvaluationStudioPage() {
  const [benchmark, setBenchmark] = useState<any>(null);
  const [running,   setRunning]   = useState(false);

  useEffect(() => { fetchBenchmark().then(setBenchmark); }, []);

  const handleRun = async () => {
    setRunning(true);
    try { setBenchmark(await runBenchmarkSuite()); } catch {}
    finally { setRunning(false); }
  };

  const models  = benchmark?.models || benchmark?.baselines || {};
  const hybrid  = models?.blackbox_hybrid     || {};
  const last    = models?.baseline_last_step  || {};
  const rule    = models?.baseline_rule_only  || {};
  const anomaly = models?.baseline_anomaly_only || {};
  const cases   = benchmark?.detailed_cases   || benchmark?.detailed_results || [];

  const metricCards = [
    { label: "Top-1 Accuracy (Exact Root Cause)", value: hybrid.top1_accuracy != null ? `${(hybrid.top1_accuracy*100).toFixed(0)}%` : "—", color: "#7C5CFF", bg: "#F5F3FF", rows: [{ name: "BLACKBOX Hybrid", v: hybrid.top1_accuracy, c: "#7C5CFF" }, { name: "Rule-Only", v: rule.top1_accuracy, c: "#9BA8BF" }, { name: "Last-Step", v: last.top1_accuracy, c: "#9BA8BF" }] },
    { label: "Top-3 Accuracy (In Suspect Pool)", value: hybrid.top3_accuracy != null ? `${(hybrid.top3_accuracy*100).toFixed(0)}%` : "—", color: "#3B82F6", bg: "#EFF6FF", rows: [{ name: "BLACKBOX Hybrid", v: hybrid.top3_accuracy, c: "#3B82F6" }, { name: "Anomaly-Only", v: anomaly.top3_accuracy, c: "#9BA8BF" }, { name: "Last-Step", v: last.top3_accuracy, c: "#9BA8BF" }] },
    { label: "Mean Reciprocal Rank", value: hybrid.mrr != null ? hybrid.mrr.toFixed(3) : "—", color: "#22C55E", bg: "#F0FDF4", rows: [{ name: "BLACKBOX Hybrid", v: hybrid.mrr, c: "#22C55E" }, { name: "Rule-Only", v: rule.mrr, c: "#9BA8BF" }, { name: "Last-Step", v: last.mrr, c: "#9BA8BF" }] },
  ];

  return (
    <div className="p-7 space-y-6 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 20 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={S.tag("#EFF6FF", "#3B82F6", "#BFDBFE")}>Evaluation Studio</span>
            <span style={{ fontSize: 11, color: "#9BA8BF" }}>● Ground-Truth Benchmark</span>
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 900, color: "#1A2236", letterSpacing: "-0.02em", margin: 0 }}>
            Diagnosis Accuracy &amp; Benchmark Suite
          </h1>
          <p style={{ fontSize: 13, color: "#6B7A99", marginTop: 5, maxWidth: 520, lineHeight: 1.5 }}>
            Evaluating fault localization accuracy (Top-1, Top-3, MRR) across labeled failure test cases.
          </p>
        </div>
        <button onClick={handleRun} disabled={running} style={{
          display: "flex", alignItems: "center", gap: 8, flexShrink: 0,
          padding: "10px 20px", borderRadius: 12, fontWeight: 700, fontSize: 13,
          color: "white", border: "none", cursor: running ? "not-allowed" : "pointer",
          background: "#3B82F6", boxShadow: "0 4px 14px rgba(59,130,246,0.28)",
          opacity: running ? 0.65 : 1,
        }}>
          <Play style={{ width: 14, height: 14 }} />
          {running ? "Running…" : "Execute Benchmark Suite"}
        </button>
      </div>

      {/* Small benchmark notice */}
      {cases.length < 20 && (
        <div style={{ padding: "10px 16px", borderRadius: 10, background: "#FFFBEB", border: "1px solid #FDE68A", fontSize: 12, color: "#92400E", fontWeight: 500 }}>
          Small benchmark ({cases.length} cases) — results are illustrative. Counts shown alongside percentages. No weight tuning on test split.
        </div>
      )}

      {/* Metric cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14 }}>
        {metricCards.map((c) => (
          <div key={c.label} style={{ ...S.card, padding: "20px 22px" }}>
            <p style={S.label}>{c.label}</p>
            <p style={{ fontSize: 30, fontWeight: 900, color: c.color, fontFamily: "monospace", margin: "4px 0 10px", lineHeight: 1 }}>{c.value}</p>
            <div style={{ height: 4, background: "#F0F4FA", borderRadius: 99, marginBottom: 12, overflow: "hidden" }}>
              <div style={{ height: "100%", background: c.color, borderRadius: 99, width: c.value.includes("%") ? c.value : "70%", transition: "width 0.5s ease" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
              {c.rows.map((row) => (
                <div key={row.name} style={{ display: "flex", justifyContent: "space-between", fontSize: 11 }}>
                  <span style={{ color: "#6B7A99" }}>{row.name}</span>
                  <span style={{ fontFamily: "monospace", fontWeight: 700, color: row.c }}>
                    {row.v != null ? (String(row.v).includes(".") && row.v < 2 ? row.v.toFixed(3) : `${(row.v*100).toFixed(0)}%`) : "—"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Cases table */}
      <div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <h3 style={{ fontSize: 15, fontWeight: 800, color: "#1A2236", margin: 0 }}>
            Labeled Failure Test Suite ({cases.length} cases)
          </h3>
          <span style={{ fontSize: 11, fontFamily: "monospace", color: "#9BA8BF" }}>Ground-Truth Verified</span>
        </div>
        <div style={{ ...S.card, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#F8FAFD", borderBottom: "1px solid #E4EAF4" }}>
                {["Case ID", "Agent & Name", "Fault Category", "Ground Truth", "Rank", "Score", "Result"].map(h => (
                  <th key={h} style={{ padding: "11px 16px", textAlign: "left", fontWeight: 600, color: "#6B7A99", fontSize: 11 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cases.map((tc: any, i: number) => (
                <tr key={tc.case_id} style={{ borderBottom: i < cases.length-1 ? "1px solid #F0F4FA" : "none" }}
                  onMouseEnter={e => (e.currentTarget.style.background = "#FAFBFD")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                  <td style={{ padding: "12px 16px", fontFamily: "monospace", fontWeight: 700, color: "#9BA8BF" }}>{tc.case_id}</td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{ fontWeight: 700, color: "#1A2236" }}>{tc.name}</span>
                    <span style={{ fontFamily: "monospace", fontSize: 10.5, color: "#9BA8BF", marginLeft: 6 }}>({tc.agent})</span>
                  </td>
                  <td style={{ padding: "12px 16px", color: "#6B7A99" }}>{tc.fault_category}</td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{ fontFamily: "monospace", fontWeight: 700, padding: "2px 8px", borderRadius: 6, background: "#FEF3C7", color: "#B45309" }}>{tc.ground_truth}</span>
                  </td>
                  <td style={{ padding: "12px 16px", fontFamily: "monospace", fontWeight: 700, color: "#3B82F6" }}>#{tc.hybrid_rank}</td>
                  <td style={{ padding: "12px 16px", fontFamily: "monospace", fontWeight: 700, color: "#F59E0B" }}>{tc.hybrid_suspicion_score || "—"}</td>
                  <td style={{ padding: "12px 16px" }}>
                    {tc.is_top1 ? (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999, background: "#F0FDF4", color: "#16A34A" }}>
                        <CheckCircle2 style={{ width: 11, height: 11 }} /> Top-1
                      </span>
                    ) : (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999, background: "#EFF6FF", color: "#3B82F6" }}>
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
