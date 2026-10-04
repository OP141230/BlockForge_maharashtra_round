"use client";

import React from "react";
import Link from "next/link";
import {
  ShieldAlert, TrendingUp, Cpu, GitFork, History,
  RotateCcw, MoreHorizontal, Zap,
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

const SIGNAL_ROWS = [
  { key: "rule_match",          label: "Rule Match",          weight: "30%", Icon: ShieldAlert, color: "#F59E0B", bg: "#FFFBEB" },
  { key: "anomaly_signal",      label: "Anomaly Signal",      weight: "20%", Icon: TrendingUp,  color: "#3B82F6", bg: "#EFF6FF" },
  { key: "learned_ranker",      label: "Learned Ranker",      weight: "20%", Icon: Cpu,         color: "#7C5CFF", bg: "#F5F3FF" },
  { key: "dependency_impact",   label: "Dependency Impact",   weight: "15%", Icon: GitFork,     color: "#EF4444", bg: "#FFF1F2" },
  { key: "historical_evidence", label: "Historical Evidence", weight: "15%", Icon: History,     color: "#22C55E", bg: "#F0FDF4" },
] as const;

export default function DiagnosisPanel({
  runId, suspectStepName, suspectStepId,
  suspicionScore, confidenceLabel, explanationText,
  signals, evidenceItems,
}: DiagnosisPanelProps) {
  const score = Math.round(suspicionScore);

  return (
    <div
      style={{
        width: 288,
        background: "rgba(255,255,255,0.98)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid #E4EAF4",
        borderRadius: 18,
        boxShadow: "0 8px 40px rgba(26,34,54,0.11), 0 1px 0 rgba(255,255,255,0.9) inset",
        overflow: "hidden",
      }}
    >
      {/* ── Header band ── */}
      <div
        style={{
          padding: "14px 16px 12px",
          borderBottom: "1px solid #EEF2F8",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <div>
          <p style={{ fontSize: 10, fontWeight: 600, color: "#9BA8BF", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 3 }}>
            Comparison Summary
          </p>
          <p style={{ fontSize: 20, fontWeight: 900, lineHeight: 1, color: "#F59E0B", fontFamily: "monospace" }}>
            2,950{" "}
            <span style={{ fontSize: 15, color: "#1A2236" }}>vs 2,050 (corrected)</span>
          </p>
          <p style={{ fontSize: 11, color: "#9BA8BF", marginTop: 4 }}>3 downstream events failed</p>
        </div>

        {/* Score bubble */}
        <div
          style={{
            flexShrink: 0,
            width: 48, height: 48,
            borderRadius: "50%",
            background: "linear-gradient(135deg,#FEF3C7,#FDE68A)",
            border: "2px solid #F59E0B",
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            boxShadow: "0 2px 8px rgba(245,158,11,0.25)",
          }}
        >
          <span style={{ fontSize: 15, fontWeight: 900, color: "#B45309", lineHeight: 1, fontFamily: "monospace" }}>
            {score}
          </span>
          <span style={{ fontSize: 7, color: "#B45309", fontWeight: 700, letterSpacing: "0.02em" }}>
            SCORE
          </span>
        </div>
      </div>

      {/* ── Root cause evidence ── */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid #EEF2F8" }}>
        <p style={{ fontSize: 10, fontWeight: 700, color: "#9BA8BF", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 6 }}>
          Root Cause Evidence
        </p>
        <p style={{ fontSize: 11, color: "#6B7A99", lineHeight: 1.55 }}>
          Corrected replay total: 2,050 (budget 2,500)
        </p>

        {/* Suspect chip */}
        <div
          style={{
            marginTop: 10,
            padding: "10px 12px",
            background: "linear-gradient(135deg,#FFFBEB,#FFF7E0)",
            border: "1px solid #FDE68A",
            borderRadius: 10,
          }}
        >
          <p style={{ fontSize: 11, fontWeight: 700, color: "#1A2236", marginBottom: 2 }}>
            {suspectStepName}
          </p>
          <p style={{ fontSize: 13, fontWeight: 900, color: "#F59E0B", fontFamily: "monospace" }}>
            Suspicion Score {score}
          </p>
          <p style={{ fontSize: 9.5, color: "#C8B97A", marginTop: 2 }}>
            Heuristic score · not a probability
          </p>
        </div>
      </div>

      {/* ── 5-Signal bars ── */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid #EEF2F8" }}>
        <p style={{ fontSize: 10, fontWeight: 700, color: "#9BA8BF", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 8 }}>
          Signal Breakdown
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
          {SIGNAL_ROWS.map(({ key, label, weight, Icon, color, bg }) => {
            const val = signals[key as keyof DiagnosisSignals];
            const pct = Math.min(val * 100, 100);
            return (
              <div key={key}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 3 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <div style={{ width: 18, height: 18, borderRadius: 5, background: bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <Icon style={{ width: 10, height: 10, color }} />
                    </div>
                    <span style={{ fontSize: 10.5, color: "#4B5A75", fontWeight: 500 }}>{label}</span>
                    <span style={{ fontSize: 9, color: "#C8D0E0" }}>({weight})</span>
                  </div>
                  <span style={{ fontSize: 10, fontWeight: 700, color, fontFamily: "monospace" }}>
                    {val.toFixed(2)}
                  </span>
                </div>
                <div style={{ height: 4, background: "#F0F3F9", borderRadius: 9999, overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%", borderRadius: 9999,
                      width: `${pct}%`,
                      background: color,
                      transition: "width 0.4s ease",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Confidence + actions ── */}
      <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            style={{
              fontSize: 9.5, fontWeight: 700, textTransform: "uppercase",
              letterSpacing: "0.04em", padding: "3px 8px", borderRadius: 999,
              ...(confidenceLabel === "CRITICAL"
                ? { background: "#FFF1F2", color: "#DC2626", border: "1px solid #FCA5A5" }
                : confidenceLabel === "HIGH"
                ? { background: "#FFFBEB", color: "#B45309", border: "1px solid #FDE68A" }
                : { background: "#EFF6FF", color: "#1D4ED8", border: "1px solid #BFDBFE" }),
            }}
          >
            {confidenceLabel}
          </span>
          <Zap style={{ width: 11, height: 11, color: "#C8D0E0" }} />
          <span style={{ fontSize: 9.5, color: "#C8D0E0" }}>Hybrid Engine v1</span>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <Link
            href={`/replay?run_id=${runId}&step_id=${suspectStepId}`}
            style={{
              flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              padding: "9px 12px", borderRadius: 10, fontWeight: 700, fontSize: 11.5,
              color: "white", textDecoration: "none",
              background: "#3B82F6",
              boxShadow: "0 3px 12px rgba(59,130,246,0.28)",
              transition: "opacity 0.15s",
            }}
          >
            <RotateCcw style={{ width: 13, height: 13 }} />
            Open Replay Lab
          </Link>
          <button
            style={{
              width: 36, height: 36, borderRadius: 9, border: "1px solid #E4EAF4",
              background: "#F8FAFD", cursor: "pointer", display: "flex",
              alignItems: "center", justifyContent: "center",
            }}
            title="More options"
          >
            <MoreHorizontal style={{ width: 15, height: 15, color: "#9BA8BF" }} />
          </button>
        </div>
      </div>
    </div>
  );
}
