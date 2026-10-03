"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Search, CheckCircle2, XCircle, Clock, ArrowRight } from "lucide-react";
import { fetchRuns } from "@/lib/api";

export default function ExecutionsPage() {
  const [runs,   setRuns]   = useState<any[]>([]);
  const [status, setStatus] = useState("ALL");
  const [query,  setQuery]  = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRuns().then((d) => { setRuns(d.runs || []); setLoading(false); });
  }, []);

  const filtered = runs.filter((r) => {
    const ms = status === "ALL" || r.status === status;
    const mq = r.agent_name.toLowerCase().includes(query.toLowerCase()) ||
               r.scenario.toLowerCase().includes(query.toLowerCase());
    return ms && mq;
  });

  return (
    <div className="p-7 space-y-6 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", padding: "3px 10px", borderRadius: 999, background: "#EFF6FF", color: "#3B82F6", border: "1px solid #BFDBFE" }}>
            Execution Ledger
          </span>
          <span style={{ fontSize: 11, color: "#9BA8BF" }}>● Full Trace Archive</span>
        </div>
        <h1 style={{ fontSize: 24, fontWeight: 900, color: "#1A2236", letterSpacing: "-0.02em", margin: 0 }}>
          Agent Flight Executions
        </h1>
        <p style={{ fontSize: 13, color: "#6B7A99", marginTop: 5 }}>
          Search and filter all recorded agent runs, examine outcomes and suspected fault points.
        </p>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 4, padding: 4, background: "#FFFFFF", border: "1px solid #E4EAF4", borderRadius: 12 }}>
          {["ALL", "FAILED", "SUCCESS"].map((s) => (
            <button key={s} onClick={() => setStatus(s)} style={{
              padding: "6px 16px", borderRadius: 9, border: "none", cursor: "pointer",
              fontSize: 12, fontWeight: 600, transition: "all 0.12s",
              ...(status === s
                ? { background: "#3B82F6", color: "#FFFFFF", boxShadow: "0 2px 8px rgba(59,130,246,0.25)" }
                : { background: "transparent", color: "#6B7A99" }),
            }}>
              {s === "ALL" ? "All Runs" : s}
            </button>
          ))}
        </div>
        <div style={{ position: "relative", width: 280 }}>
          <Search style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", width: 14, height: 14, color: "#9BA8BF" }} />
          <input type="text" placeholder="Search agent or scenario…" value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              width: "100%", paddingLeft: 36, paddingRight: 14, paddingTop: 9, paddingBottom: 9,
              borderRadius: 11, border: "1px solid #E4EAF4", background: "#FFFFFF",
              fontSize: 12, color: "#1A2236", outline: "none",
              boxShadow: "0 1px 5px rgba(26,34,54,0.04)",
            }}
          />
        </div>
      </div>

      {/* Table */}
      <div style={{ background: "#FFFFFF", borderRadius: 16, border: "1px solid #E4EAF4", boxShadow: "0 2px 10px rgba(26,34,54,0.05)", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ background: "#F8FAFD", borderBottom: "1px solid #E4EAF4" }}>
              {["Agent Name", "Scenario", "Status", "Steps", "Duration", "Primary Suspect", "Score", ""].map((h) => (
                <th key={h} style={{ padding: "11px 16px", textAlign: "left", fontWeight: 600, color: "#6B7A99", fontSize: 11 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((r, i) => (
              <tr key={r.id} style={{ borderBottom: i < filtered.length - 1 ? "1px solid #F0F4FA" : "none" }}
                onMouseEnter={e => (e.currentTarget.style.background = "#FAFBFD")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                <td style={{ padding: "13px 16px", fontWeight: 700, color: "#1A2236" }}>{r.agent_name}</td>
                <td style={{ padding: "13px 16px", color: "#6B7A99", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.scenario}</td>
                <td style={{ padding: "13px 16px" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 10.5, fontWeight: 700, padding: "3px 10px", borderRadius: 999, textTransform: "uppercase", ...(r.status === "SUCCESS" ? { background: "#F0FDF4", color: "#16A34A" } : { background: "#FFF1F2", color: "#DC2626" }) }}>
                    {r.status === "SUCCESS" ? <CheckCircle2 style={{ width: 11, height: 11 }} /> : <XCircle style={{ width: 11, height: 11 }} />}
                    {r.status}
                  </span>
                </td>
                <td style={{ padding: "13px 16px", fontFamily: "monospace", fontWeight: 600, color: "#1A2236" }}>{r.step_count || 6}</td>
                <td style={{ padding: "13px 16px" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11.5, fontFamily: "monospace", color: "#6B7A99" }}>
                    <Clock style={{ width: 11, height: 11 }} />{r.total_duration_ms?.toFixed(0)}ms
                  </span>
                </td>
                <td style={{ padding: "13px 16px", fontWeight: 600, color: "#1A2236" }}>{r.diagnosis_summary?.suspect_step_name || r.ground_truth_suspect_step || "—"}</td>
                <td style={{ padding: "13px 16px" }}>
                  {r.diagnosis_summary?.suspicion_score ? (
                    <span style={{ fontFamily: "monospace", fontWeight: 800, fontSize: 12, padding: "3px 10px", borderRadius: 999, background: "#FEF3C7", color: "#B45309" }}>{r.diagnosis_summary.suspicion_score}</span>
                  ) : <span style={{ color: "#C8D0E0", fontFamily: "monospace" }}>—</span>}
                </td>
                <td style={{ padding: "13px 16px", textAlign: "right" }}>
                  <Link href={`/investigation?run_id=${r.id}`} style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "6px 14px", borderRadius: 9, fontSize: 11.5, fontWeight: 700, textDecoration: "none", color: "#3B82F6", background: "#EFF6FF", border: "1px solid #BFDBFE" }}>
                    Investigate <ArrowRight style={{ width: 11, height: 11 }} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
