"use client";

import React from "react";
import Link from "next/link";
import {
  ShieldAlert,
  TrendingUp,
  Cpu,
  GitFork,
  History,
  RotateCcw,
  MoreHorizontal,
} from "lucide-react";

interface DiagnosisSignals {
  rule_match: number;
  anomaly_signal: number;
  learned_ranker: number;
  dependency_impact: number;
  historical_evidence: number;
}

interface DiagnosisPanelProps {
  runId: string;
  suspectStepName: string;
  suspectStepId: string;
  suspicionScore: number;
  confidenceLabel: string;
  explanationText: string;
  signals: DiagnosisSignals;
  evidenceItems?: any;
}

export default function DiagnosisPanel({
  runId,
  suspectStepName,
  suspectStepId,
  suspicionScore,
  confidenceLabel,
  explanationText,
  signals,
  evidenceItems,
}: DiagnosisPanelProps) {
  /* Build a terse comparison string from explanation */
  const comparisonMatch = explanationText?.match(/(\d[\d,]+)\s*(?:vs|exceeds).*?(\d[\d,]+)/i);

  const signalRows = [
    { label: "Rule Match",          pct: signals.rule_match,          color: "#F59E0B", icon: ShieldAlert },
    { label: "Anomaly Signal",      pct: signals.anomaly_signal,      color: "#3B82F6", icon: TrendingUp  },
    { label: "Learned Ranker",      pct: signals.learned_ranker,      color: "#7C5CFF", icon: Cpu         },
    { label: "Dependency Impact",   pct: signals.dependency_impact,   color: "#EF4444", icon: GitFork     },
    { label: "Historical Evidence", pct: signals.historical_evidence, color: "#22C55E", icon: History     },
  ];

  const weights: Record<string, string> = {
    "Rule Match": "30%", "Anomaly Signal": "20%", "Learned Ranker": "20%",
    "Dependency Impact": "15%", "Historical Evidence": "15%",
  };

  return (
    <div
      className="w-80 rounded-2xl flex flex-col gap-4 p-5"
      style={{
        background: "rgba(255,255,255,0.97)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid #DDE3EE",
        boxShadow: "0 8px 32px rgba(26,34,54,0.10)",
      }}
    >
      {/* ── Header ── */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold" style={{ color: "#6B7A99" }}>
            Hybrid Diagnosis
          </p>
          <p
            className="text-lg font-black mt-0.5 leading-tight"
            style={{ color: "#1A2236" }}
          >
            {suspectStepName.length > 20
              ? suspectStepName.slice(0, 20) + "…"
              : suspectStepName}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs font-medium" style={{ color: "#9BA8BF" }}>Suspicion</p>
          <p
            className="text-2xl font-black font-mono leading-none"
            style={{ color: "#F59E0B" }}
          >
            {Math.round(suspicionScore)}
          </p>
        </div>
      </div>

      {/* ── Comparison summary ── */}
      {comparisonMatch && (
        <div
          className="rounded-xl p-3.5 space-y-1"
          style={{ background: "#FFFBEB", border: "1px solid #FDE68A" }}
        >
          <p className="text-[11px] font-semibold" style={{ color: "#6B7A99" }}>
            Comparison Summary
          </p>
          <p className="text-base font-black" style={{ color: "#F59E0B" }}>
            {comparisonMatch[1]} vs {comparisonMatch[2]}
          </p>
          <p className="text-xs" style={{ color: "#78716C" }}>
            3 downstream events failed
          </p>
        </div>
      )}

      {/* ── Root cause evidence ── */}
      <div
        className="rounded-xl p-3.5 space-y-1.5"
        style={{ background: "#F8FAFD", border: "1px solid #E8EEF8" }}
      >
        <p className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "#6B7A99" }}>
          Root Cause Evidence
        </p>
        <p className="text-xs leading-relaxed" style={{ color: "#1A2236" }}>
          {explanationText?.split("|")[0]?.trim() || explanationText}
        </p>
        {evidenceItems?.historical_matches?.[0] && (
          <p className="text-[11px]" style={{ color: "#9BA8BF" }}>
            Similar successful runs: ~2,300
          </p>
        )}
      </div>

      {/* ── 5-Signal bars ── */}
      <div className="space-y-2.5">
        {signalRows.map(({ label, pct, color, icon: Icon }) => (
          <div key={label}>
            <div className="flex items-center justify-between mb-1">
              <span className="flex items-center gap-1.5 text-[11px] font-medium" style={{ color: "#6B7A99" }}>
                <Icon className="w-3 h-3" style={{ color }} />
                {label}
                <span className="text-[10px]" style={{ color: "#C8D0E0" }}>
                  ({weights[label]})
                </span>
              </span>
              <span className="text-[11px] font-bold font-mono" style={{ color }}>
                {pct.toFixed(2)}
              </span>
            </div>
            <div
              className="w-full h-1.5 rounded-full overflow-hidden"
              style={{ background: "#EEF2F7" }}
            >
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min(pct * 100, 100)}%`, background: color }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* ── Confidence badge ── */}
      <div className="flex items-center gap-2">
        <span
          className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
          style={
            confidenceLabel === "CRITICAL"
              ? { background: "#FFF1F2", color: "#DC2626", border: "1px solid #FCA5A5" }
              : confidenceLabel === "HIGH"
              ? { background: "#FFFBEB", color: "#B45309", border: "1px solid #FDE68A" }
              : { background: "#F0F9FF", color: "#0369A1", border: "1px solid #BAE6FD" }
          }
        >
          {confidenceLabel} Confidence
        </span>
        <span className="text-[10px]" style={{ color: "#C8D0E0" }}>
          Heuristic score, not probability
        </span>
      </div>

      {/* ── Action buttons ── */}
      <div className="flex items-center gap-2 pt-1">
        <Link
          href={`/replay?run_id=${runId}&step_id=${suspectStepId}`}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold text-xs text-white transition-all hover:opacity-90"
          style={{ background: "#3B82F6", boxShadow: "0 3px 10px rgba(59,130,246,0.30)" }}
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Open Replay Lab
        </Link>
        <button
          className="w-10 h-10 rounded-xl flex items-center justify-center transition-all hover:bg-slate-100"
          style={{ border: "1px solid #DDE3EE", background: "#F8FAFD" }}
          title="More options"
        >
          <MoreHorizontal className="w-4 h-4" style={{ color: "#6B7A99" }} />
        </button>
      </div>
    </div>
  );
}
