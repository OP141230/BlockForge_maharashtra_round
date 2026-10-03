"use client";

import React, { useEffect, useState } from "react";
import { GitCompare, AlertTriangle, CheckCircle2, ArrowRight } from "lucide-react";
import { compareRuns } from "@/lib/api";

export default function ComparePage() {
  const [comparison, setComparison] = useState<any>(null);
  const [loading, setLoading]       = useState(true);

  useEffect(() => {
    compareRuns("run_travel_paris_fail", "run_travel_paris_success")
      .then((d) => { setComparison(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 space-y-7 max-w-6xl mx-auto w-full">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full"
            style={{ background: "#EEF2FF", color: "#3B82F6", border: "1px solid #C7D7FD" }}>
            Divergence Studio
          </span>
        </div>
        <h1 className="text-3xl font-black tracking-tight" style={{ color: "#1A2236" }}>
          Run Comparison &amp; First Divergence Analysis
        </h1>
        <p className="text-sm mt-1" style={{ color: "#6B7A99" }}>
          Side-by-side alignment of failed vs successful executions to pinpoint exact divergence.
        </p>
      </div>

      {/* First divergence spotlight */}
      {comparison?.first_meaningful_divergence && (
        <div className="rounded-2xl p-6 flex items-start gap-5"
          style={{ background: "linear-gradient(135deg,#FFFBEB,#FFF7E6)", border: "1px solid #FDE68A" }}>
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 shadow-md"
            style={{ background: "#F59E0B", boxShadow: "0 4px 14px rgba(245,158,11,0.35)" }}>
            <AlertTriangle className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                style={{ background: "#FDE68A", color: "#92400E" }}>
                First Meaningful Divergence
              </span>
              <span className="text-xs font-bold" style={{ color: "#B45309" }}>
                Step {comparison.first_meaningful_divergence.step_index}: {comparison.first_meaningful_divergence.step_name}
              </span>
            </div>
            <p className="text-xs" style={{ color: "#78716C" }}>
              {comparison.first_meaningful_divergence.root_cause_diagnosis}
            </p>
            <div className="grid grid-cols-2 gap-4 mt-4 font-mono text-xs">
              <div className="p-3 rounded-xl"
                style={{ background: "#FFFFFF", border: "1px solid #FCA5A5" }}>
                <p className="text-[10px] font-bold uppercase mb-1" style={{ color: "#DC2626" }}>Failed Run Output</p>
                <pre className="text-[11px] overflow-x-auto" style={{ color: "#EF4444" }}>
                  {JSON.stringify(comparison.first_meaningful_divergence.target_output, null, 2)}
                </pre>
              </div>
              <div className="p-3 rounded-xl"
                style={{ background: "#FFFFFF", border: "1px solid #86EFAC" }}>
                <p className="text-[10px] font-bold uppercase mb-1" style={{ color: "#16A34A" }}>Baseline Success Output</p>
                <pre className="text-[11px] overflow-x-auto" style={{ color: "#22C55E" }}>
                  {JSON.stringify(comparison.first_meaningful_divergence.baseline_output, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Aligned steps */}
      <div>
        <h3 className="text-base font-bold mb-4" style={{ color: "#1A2236" }}>Aligned Execution Pipeline</h3>
        <div className="rounded-2xl overflow-hidden"
          style={{ background: "#FFFFFF", border: "1px solid #DDE3EE", boxShadow: "0 2px 10px rgba(26,34,54,0.05)" }}>
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr style={{ background: "#F8FAFD", borderBottom: "1px solid #DDE3EE" }}>
                {["#", "Step & Tool", "Failed Status", "Baseline Status", "Alignment", "Duration Δ"].map(h => (
                  <th key={h} className="py-3 px-4 font-semibold" style={{ color: "#6B7A99" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparison?.aligned_steps?.map((s: any, i: number) => (
                <tr key={i}
                  className="transition-colors"
                  style={{
                    background: s.is_divergent ? "#FFFBEB" : "transparent",
                    borderBottom: i < (comparison.aligned_steps.length-1) ? "1px solid #EEF2F7" : "none",
                  }}>
                  <td className="py-3.5 px-4 font-mono" style={{ color: "#9BA8BF" }}>{s.step_index}</td>
                  <td className="py-3.5 px-4">
                    <span className="font-semibold" style={{ color: "#1A2236" }}>{s.step_name}</span>
                    <span className="font-mono ml-1 text-[11px]" style={{ color: "#9BA8BF" }}>({s.tool_name})</span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase"
                      style={s.target_run_status === "SUCCESS"
                        ? { background: "#ECFDF5", color: "#16A34A" }
                        : { background: "#FFF1F2", color: "#DC2626" }}>
                      {s.target_run_status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase"
                      style={{ background: "#ECFDF5", color: "#16A34A" }}>
                      {s.baseline_run_status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    {s.is_divergent ? (
                      <span className="flex items-center gap-1 text-xs font-bold"
                        style={{ color: "#B45309" }}>
                        <AlertTriangle className="w-3 h-3" /> Divergent
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs" style={{ color: "#22C55E" }}>
                        <CheckCircle2 className="w-3 h-3" /> Aligned
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 font-mono" style={{ color: "#6B7A99" }}>
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
