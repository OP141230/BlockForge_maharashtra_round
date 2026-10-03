"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Layers,
  Search,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Filter,
} from "lucide-react";
import { fetchRuns } from "@/lib/api";

export default function ExecutionsPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRuns().then((data) => {
      setRuns(data.runs || []);
      setLoading(false);
    });
  }, []);

  const filteredRuns = runs.filter((r) => {
    const matchesStatus = filterStatus === "ALL" || r.status === filterStatus;
    const matchesSearch =
      r.agent_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.scenario.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs uppercase font-mono tracking-wider text-primary font-bold px-2 py-0.5 rounded bg-blue-50 border border-blue-200">
            Execution Ledger
          </span>
          <span className="text-xs text-text-muted">● Full Trace Archive</span>
        </div>
        <h1 className="text-3xl font-black text-text-primary tracking-tight">
          Agent Flight Executions
        </h1>
        <p className="text-sm text-text-muted mt-1 max-w-2xl">
          Search and filter all recorded agent runs, examine status outcomes, duration profiles, and suspected fault points.
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Status Filters */}
        <div className="flex items-center bg-white p-1 rounded-xl border border-panel-border shadow-sm text-xs font-semibold">
          {["ALL", "FAILED", "SUCCESS"].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-3.5 py-1.5 rounded-lg transition-all ${
                filterStatus === st
                  ? "bg-primary text-white shadow-sm"
                  : "text-text-muted hover:text-text-primary"
              }`}
            >
              {st === "ALL" ? "All Runs" : st}
            </button>
          ))}
        </div>

        {/* Search input */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search agent or scenario..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-xl border border-panel-border bg-white text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-primary shadow-sm"
          />
        </div>
      </div>

      {/* Executions Table */}
      <div className="rounded-2xl glass-card border border-panel-border overflow-hidden">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-50/80 border-b border-panel-border text-text-muted font-semibold">
              <th className="py-3 px-4">Agent Name</th>
              <th className="py-3 px-4">Scenario / Objective</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Steps</th>
              <th className="py-3 px-4">Duration</th>
              <th className="py-3 px-4">Primary Suspect</th>
              <th className="py-3 px-4">Suspicion Score</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredRuns.map((r) => (
              <tr key={r.id} className="hover:bg-slate-50/50 transition-colors">
                <td className="py-3.5 px-4 font-bold text-text-primary">{r.agent_name}</td>
                <td className="py-3.5 px-4 text-text-muted">{r.scenario}</td>
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
  );
}
