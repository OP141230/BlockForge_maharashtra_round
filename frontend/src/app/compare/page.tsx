"use client";

import React, { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { compareRuns } from "@/lib/api";

export default function ComparePage() {
  const [cmp,     setCmp]     = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    compareRuns("run_travel_paris_fail", "run_travel_paris_success")
      .then((d) => { setCmp(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const card: React.CSSProperties = {
    background: "#FFFFFF", borderRadius: 16,
    border: "1px solid #E4EAF4",
    boxShadow: "0 2px 10px rgba(26,34,54,0.05)",
  };

  return (
    <div className="p-7 space-y-6 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", padding: "3px 10px", borderRadius: 999, background: "#EFF6FF", color: "#3B82F6", border: "1px solid #BFDBFE" }}>
            Divergence Studio
          </span>
          <span style={{ fontSize: 11, color: "#9BA8BF" }}>● Causal State Alignment</span>
        </div>
        <h1 style={{ fontSize: 24, fontWeight: 900, color: "#1A2236", letterSpacing: "-0.02em", margin: 0 }}>
          Run Comparison &amp; First Divergence Analysis
        </h1>
        <p style={{ fontSize: 13, color: "#6B7A99", marginTop: 5 }}>
          Side-by-side alignment of failed vs successful executions to pinpoint exact divergence.
        </p>
      </div>

      {/* Divergence spotlight */}
      {cmp?.first_meaningful_divergence && (
        <div style={{ ...card, padding: "20px 24px", background: "linear-gradient(135deg,#FFFBEB,#FFF7E0)", border: "1px solid #FDE68A", display: "flex", alignItems: "flex-start", gap: 16 }}>
          <div style={{ width: 46, height: 46, borderRadius: 14, flexShrink: 0, background: "#F59E0B", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 12px rgba(245,158,11,0.30)" }}>
            <AlertTriangle style={{ width: 22, height: 22, color: "white" }} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
              <span style={{ fontSize: 9.5, fontWeight: 800, letterSpacing: "0.06em", textTransform: "uppercase", padding: "2px 8px", borderRadius: 999, background: "#FDE68A", color: "#92400E" }}>
                First Meaningful Divergence
              </span>
              <span style={{ fontSize: 12, fontWeight: 700, color: "#B45309" }}>
                Step {cmp.first_meaningful_divergence.step_index}: {cmp.first_meaningful_divergence.step_name}
              </span>
            </div>
            <p style={{ fontSize: 12, color: "#78716C", margin: "0 0 14px" }}>
              {cmp.first_meaningful_divergence.root_cause_diagnosis}
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {[
                { label: "Failed Run Output", data: cmp.first_meaningful_divergence.target_output, border: "#FCA5A5", color: "#DC2626" },
                { label: "Baseline Success Output", data: cmp.first_meaningful_divergence.baseline_output, border: "#86EFAC", color: "#16A34A" },
              ].map(({ label, data, border, color }) => (
                <div key={label} style={{ background: "#FFFFFF", border: `1px solid ${border}`, borderRadius: 10, padding: 12 }}>
                  <p style={{ fontSize: 9.5, fontWeight: 700, textTransform: "uppercase", color, marginBottom: 5 }}>{label}</p>
                  <pre style={{ margin: 0, fontSize: 10.5, color, fontFamily: "monospace", overflowX: "auto" }}>
                    {JSON.stringify(data, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Aligned steps */}
      <div>
        <h3 style={{ fontSize: 15, fontWeight: 800, color: "#1A2236", margin: "0 0 14px" }}>
          Aligned Execution Pipeline
        </h3>
        <div style={{ ...card, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#F8FAFD", borderBottom: "1px solid #E4EAF4" }}>
                {["#", "Step & Tool", "Failed Status", "Baseline Status", "Alignment", "Duration Δ"].map(h => (
                  <th key={h} style={{ padding: "11px 16px", textAlign: "left", fontWeight: 600, color: "#6B7A99", fontSize: 11 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cmp?.aligned_steps?.map((s: any, i: number) => (
                <tr key={i}
                  style={{ background: s.is_divergent ? "#FFFBEB" : "transparent", borderBottom: i < cmp.aligned_steps.length-1 ? "1px solid #F0F4FA" : "none" }}>
                  <td style={{ padding: "12px 16px", fontFamily: "monospace", color: "#9BA8BF" }}>{s.step_index}</td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{ fontWeight: 700, color: "#1A2236" }}>{s.step_name}</span>
                    <span style={{ fontFamily: "monospace", fontSize: 10.5, color: "#9BA8BF", marginLeft: 6 }}>({s.tool_name})</span>
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{ fontSize: 10.5, fontWeight: 700, padding: "2px 9px", borderRadius: 999, textTransform: "uppercase", ...(s.target_run_status === "SUCCESS" ? { background: "#F0FDF4", color: "#16A34A" } : { background: "#FFF1F2", color: "#DC2626" }) }}>
                      {s.target_run_status}
                    </span>
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{ fontSize: 10.5, fontWeight: 700, padding: "2px 9px", borderRadius: 999, textTransform: "uppercase", background: "#F0FDF4", color: "#16A34A" }}>
                      {s.baseline_run_status}
                    </span>
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    {s.is_divergent ? (
                      <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, fontWeight: 700, color: "#B45309" }}>
                        <AlertTriangle style={{ width: 13, height: 13 }} /> Divergent
                      </span>
                    ) : (
                      <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "#22C55E" }}>
                        <CheckCircle2 style={{ width: 13, height: 13 }} /> Aligned
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "12px 16px", fontFamily: "monospace", color: "#6B7A99", fontSize: 11 }}>
                    {s.target_duration_ms?.toFixed(0)}ms / {s.baseline_duration_ms?.toFixed(0)}ms
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
