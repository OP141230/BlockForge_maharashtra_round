"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Layers, Search, CheckCircle2, XCircle, Clock, ArrowRight, SlidersHorizontal,
} from "lucide-react";
import { fetchRuns } from "@/lib/api";

export default function ExecutionsPage() {
  const [runs, setRuns]               = useState<any[]>([]);
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [searchQuery, setSearchQuery]  = useState("");
  const [loading, setLoading]          = useState(true);

  useEffect(() => {
    fetchRuns().then((d) => { setRuns(d.runs || []); setLoading(false); });
  }, []);

  const filtered = runs.filter((r) => {
    const matchStatus = filterStatus === "ALL" || r.status === filterStatus;
    const matchSearch =
      r.agent_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.scenario.toLowerCase().includes(searchQuery.toLowerCase());
    return matchStatus && matchSearch;
  });

  return (
    <div className="p-8 space-y-7 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span
            className="text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full"
            style={{ background: "#EEF2FF", color: "#3B82F6", border: "1px solid #C7D7FD" }}
          >
            Execution Ledger
          </span>
          <span className="text-xs" style={{ color: "#9BA8BF" }}>● Full Trace Archive</span>
        </div>
        <h1 className="text-3xl font-black tracking-tight" style={{ color: "#1A2236" }}>
          Agent Flight Executions
        </h1>
        <p className="text-sm mt-1" style={{ color: "#6B7A99" }}>
          Search and filter all recorded agent runs, examine outcomes and suspected fault points.
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center justify-between gap-4">
        <div
          className="flex items-center p-1 gap-1 rounded-xl"
          style={{ background: "#FFFFFF", border: "1px solid #DDE3EE" }}
        >
          {["ALL", "FAILED", "SUCCESS"].map((s) => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={
                filterStatus === s
                  ? { background: "#3B82F6", color: "#FFFFFF", boxShadow: "0 2px 8px rgba(59,130,246,0.30)" }
                  : { color: "#6B7A99" }
              }
            >
              {s === "ALL" ? "All Runs" : s}
            </button>
          ))}
        </div>
        <div className="relative w-72">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: "#9BA8BF" }} />
          <input
            type="text"
            placeholder="Search agent or scenario…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl text-xs outline-none"
            style={{
              background: "#FFFFFF",
              border: "1px solid #DDE3EE",
              color: "#1A2236",
              boxShadow: "0 1px 4px rgba(26,34,54,0.05)",
            }}
          />
        </div>
      </div>

      {/* Table */}
      <div
        className="rounded-2xl overflow-hidden"
        style={{ background: "#FFFFFF", border: "1px solid #DDE3EE", boxShadow: "0 2px 10px rgba(26,34,54,0.05)" }}
      >
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr style={{ background: "#F8FAFD", borderBottom: "1px solid #DDE3EE" }}>
              {["Agent Name", "Scenario / Objective", "Status", "Steps", "Duration", "Primary Suspect", "Score", ""].map((h) => (
                <th key={h} className="py-3 px-4 font-semibold" style={{ color: "#6B7A99" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((r, i) => (
              <tr
                key={r.id}
                className="transition-colors hover:bg-[#F8FAFD]"
                style={{ borderBottom: i < filtered.length - 1 ? "1px solid #EEF2F7" : "none" }}
              >
                <td className="py-3.5 px-4 font-semibold" style={{ color: "#1A2236" }}>{r.agent_name}</td>
                <td className="py-3.5 px-4 max-w-[200px] truncate" style={{ color: "#6B7A99" }}>{r.scenario}</td>
                <td className="py-3.5 px-4">
                  <span
                    className="inline-flex items-center gap-1.5 text-[10px] font-bold px-2.5 py-1 rounded-full uppercase"
                    style={r.status === "SUCCESS"
                      ? { background: "#ECFDF5", color: "#16A34A" }
                      : { background: "#FFF1F2", color: "#DC2626" }}
                  >
                    {r.status === "SUCCESS" ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                    {r.status}
                  </span>
                </td>
                <td className="py-3.5 px-4 font-mono font-semibold" style={{ color: "#1A2236" }}>{r.step_count || 6}</td>
                <td className="py-3.5 px-4">
                  <span className="flex items-center gap-1 font-mono text-xs" style={{ color: "#6B7A99" }}>
                    <Clock className="w-3 h-3" />{r.total_duration_ms?.toFixed(0)}ms
                  </span>
                </td>
                <td className="py-3.5 px-4 font-medium" style={{ color: "#1A2236" }}>
                  {r.diagnosis_summary?.suspect_step_name || r.ground_truth_suspect_step || "—"}
                </td>
                <td className="py-3.5 px-4">
                  {r.diagnosis_summary?.suspicion_score ? (
                    <span className="font-mono font-bold text-xs px-2.5 py-1 rounded-full"
                      style={{ background: "#FEF3C7", color: "#B45309" }}>
                      {r.diagnosis_summary.suspicion_score}
                    </span>
                  ) : <span style={{ color: "#C8D0E0" }} className="font-mono">—</span>}
                </td>
                <td className="py-3.5 px-4 text-right">
                  <Link href={`/investigation?run_id=${r.id}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all hover:opacity-90"
                    style={{ background: "#EEF2FF", color: "#3B82F6", border: "1px solid #C7D7FD" }}>
                    Investigate <ArrowRight className="w-3 h-3" />
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
