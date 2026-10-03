"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight, RotateCcw, CheckCircle2, XCircle, AlertTriangle,
} from "lucide-react";
import { fetchRun, fetchDiagnosis, fetchBenchmark } from "@/lib/api";

/* ─── Inline radial graph for the overview canvas ─── */
function OverviewRadialGraph({
  steps, diagnosis, agentName, runStatus, selectedId, onSelectStep,
}: {
  steps: any[]; diagnosis: any; agentName: string; runStatus: string;
  selectedId: string | null; onSelectStep: (id: string) => void;
}) {
  const W = 820, H = 500;
  const cx = 410, cy = 250;
  const orbitR = 185;
  const total  = steps.length;
  const suspectId = diagnosis?.suspect_step_id;
  const trunc  = (s: string, n: number) => s.length > n ? s.slice(0, n) + "…" : s;
  const angleOf = (i: number) => (2 * Math.PI * i) / Math.max(total, 1) - Math.PI / 2;

  /* Donut */
  const dR = 42, dSW = 7, circ = 2 * Math.PI * dR;
  const segs = [
    { c: "#3B82F6", p: 0.30 }, { c: "#7C5CFF", p: 0.25 },
    { c: "#F59E0B", p: 0.25 }, { c: "#22C55E", p: 0.20 },
  ];
  let segOff = 0;

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block", userSelect: "none" }}>
      <defs>
        <pattern id="ov-mesh" width="72" height="72" patternUnits="userSpaceOnUse">
          <path d="M36 0L72 36L36 72L0 36Z" fill="none" stroke="#C8D4E8" strokeWidth="0.35" opacity="0.30" />
        </pattern>
        <radialGradient id="ov-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#7C5CFF" stopOpacity="0.06" />
          <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
        </radialGradient>
      </defs>

      <rect width={W} height={H} fill="url(#ov-mesh)" />
      <circle cx={cx} cy={cy} r={220} fill="url(#ov-glow)" />

      {/* Orbit ring */}
      <circle cx={cx} cy={cy} r={orbitR} fill="none"
        stroke="#C8D4E8" strokeWidth="1" strokeDasharray="5 6" opacity="0.50" />

      {/* Spokes */}
      {steps.map((step, i) => {
        const angle = angleOf(i);
        const nx = cx + orbitR * Math.cos(angle);
        const ny = cy + orbitR * Math.sin(angle);
        const isSuspect = step.id === suspectId || step.is_root_suspect;
        const isDown    = step.is_downstream_impact || (step.status === "FAILED" && !isSuspect);
        return (
          <line key={`sp-${i}`} x1={cx} y1={cy} x2={nx} y2={ny}
            stroke={isSuspect ? "#F59E0B" : isDown ? "#EF4444" : "#C8D4E8"}
            strokeWidth={isSuspect ? 1.8 : 1}
            strokeDasharray={isDown ? "4 3" : undefined}
            opacity={isSuspect ? 0.9 : 0.50}
          />
        );
      })}

      {/* Seq connectors */}
      {steps.map((_, i) => {
        if (i === steps.length - 1) return null;
        const a1 = angleOf(i), a2 = angleOf(i + 1);
        return (
          <line key={`sq-${i}`}
            x1={cx + orbitR * Math.cos(a1)} y1={cy + orbitR * Math.sin(a1)}
            x2={cx + orbitR * Math.cos(a2)} y2={cy + orbitR * Math.sin(a2)}
            stroke="#BCC8DA" strokeWidth="0.7" strokeDasharray="3 5" opacity="0.35"
          />
        );
      })}

      {/* Donut centre */}
      <circle cx={cx} cy={cy} r={dR + dSW / 2 + 10} fill="rgba(255,255,255,0.50)" />
      <circle cx={cx} cy={cy} r={dR + dSW / 2 + 3} fill="white"
        style={{ filter: "drop-shadow(0 2px 10px rgba(59,130,246,0.12))" }} />
      {segs.map((seg, i) => {
        const dash = seg.p * circ, gap = circ - dash;
        const el = (
          <circle key={i} cx={cx} cy={cy} r={dR} fill="none"
            stroke={seg.c} strokeWidth={dSW}
            strokeDasharray={`${dash} ${gap}`} strokeDashoffset={-segOff}
            strokeLinecap="round"
            style={{ transformOrigin: `${cx}px ${cy}px`, transform: "rotate(-90deg)" }}
          />
        );
        segOff += dash;
        return el;
      })}
      <circle cx={cx} cy={cy} r={dR - dSW / 2 - 2} fill="white" />
      <text x={cx} y={cy - 9} textAnchor="middle" fontSize="10" fontWeight="700" fill="#1A2236" fontFamily="Inter,sans-serif">
        {trunc(agentName, 14)}
      </text>
      <text x={cx} y={cy + 5} textAnchor="middle" fontSize="8.5" fill="#9BA8BF" fontFamily="Inter,sans-serif">
        {total} nodes
      </text>
      <text x={cx} y={cy + 19} textAnchor="middle" fontSize="8.5" fontWeight="700"
        fill={runStatus === "FAILED" ? "#EF4444" : "#22C55E"} fontFamily="Inter,sans-serif">
        {runStatus}
      </text>

      {/* Step nodes */}
      {steps.map((step, i) => {
        const angle    = angleOf(i);
        const nx       = cx + orbitR * Math.cos(angle);
        const ny       = cy + orbitR * Math.sin(angle);
        const isSuspect = step.id === suspectId || step.is_root_suspect;
        const isDown    = step.is_downstream_impact || (step.status === "FAILED" && !isSuspect);
        const isOk      = !isSuspect && !isDown;
        const isSelected = selectedId === step.id;
        const R = isSuspect ? 20 : 14;

        /* Label pushed outside orbit */
        const labelDist = R + 17;
        const lx = cx + (orbitR + labelDist) * Math.cos(angle);
        const ly = cy + (orbitR + labelDist) * Math.sin(angle);
        const anchor = Math.cos(angle) > 0.15 ? "start" : Math.cos(angle) < -0.15 ? "end" : "middle";

        return (
          <g key={step.id} onClick={() => onSelectStep(step.id)} style={{ cursor: "pointer" }}>
            {isSuspect && (
              <>
                <circle cx={nx} cy={ny} r={R + 17} fill="rgba(245,158,11,0.07)" />
                <circle cx={nx} cy={ny} r={R + 10} fill="rgba(245,158,11,0.14)" />
                <circle cx={nx} cy={ny} r={R + 4}  fill="rgba(245,158,11,0.23)" />
              </>
            )}
            {isDown && <circle cx={nx} cy={ny} r={R + 8} fill="rgba(239,68,68,0.09)" />}

            <circle cx={nx} cy={ny} r={R}
              fill={isSuspect ? "#FEF9EC" : isDown ? "#FEF2F2" : isSelected ? "#F0F6FF" : "#FFFFFF"}
              stroke={isSuspect ? "#F59E0B" : isDown ? "#EF4444" : isSelected ? "#3B82F6" : "#DDE3EE"}
              strokeWidth={isSuspect || isSelected ? 2 : 1.5}
              style={{
                filter: isSuspect
                  ? "drop-shadow(0 0 6px rgba(245,158,11,0.40))"
                  : isDown
                  ? "drop-shadow(0 0 5px rgba(239,68,68,0.30))"
                  : "drop-shadow(0 1px 3px rgba(26,34,54,0.07))",
              }}
            />

            {isOk && (
              <path d={`M${nx - 4.5} ${ny} l 3 3 l 5.5 -5.5`}
                fill="none" stroke="#22C55E" strokeWidth="1.8"
                strokeLinecap="round" strokeLinejoin="round"
              />
            )}
            {isDown && (
              <>
                <line x1={nx-3.5} y1={ny-3.5} x2={nx+3.5} y2={ny+3.5} stroke="#EF4444" strokeWidth="1.8" strokeLinecap="round" />
                <line x1={nx+3.5} y1={ny-3.5} x2={nx-3.5} y2={ny+3.5} stroke="#EF4444" strokeWidth="1.8" strokeLinecap="round" />
              </>
            )}
            {isSuspect && (
              <text x={nx} y={ny + 5} textAnchor="middle" fontSize="13" fontWeight="800" fill="#D97706" fontFamily="Inter,sans-serif">!</text>
            )}

            {/* Label outside orbit */}
            <text x={lx} y={ly - 4} textAnchor={anchor}
              fontSize="8.5" fontWeight={isSuspect ? "700" : "500"}
              fill={isSuspect ? "#B45309" : isDown ? "#DC2626" : "#6B7A99"}
              fontFamily="Inter,sans-serif">
              {trunc(step.step_name, 13)}
            </text>

            {isSuspect && step.suspicion_score != null && (
              <>
                <rect
                  x={lx - (anchor === "middle" ? 22 : anchor === "start" ? 0 : 44)}
                  y={ly + 2} width={44} height={13} rx={6.5} fill="#F59E0B"
                />
                <text
                  x={lx + (anchor === "middle" ? 0 : anchor === "start" ? 22 : -22)}
                  y={ly + 11.5} textAnchor="middle"
                  fontSize="7.5" fontWeight="700" fill="white" fontFamily="Inter,sans-serif">
                  Score {Math.round(step.suspicion_score)}
                </text>
              </>
            )}

            {isDown && (
              <>
                <rect
                  x={lx - (anchor === "middle" ? 17 : anchor === "start" ? 0 : 34)}
                  y={ly + 2} width={34} height={12} rx={6}
                  fill="#FFF1F2" stroke="#FCA5A5" strokeWidth="0.8"
                />
                <text
                  x={lx + (anchor === "middle" ? 0 : anchor === "start" ? 17 : -17)}
                  y={ly + 11} textAnchor="middle"
                  fontSize="7" fontWeight="600" fill="#EF4444" fontFamily="Inter,sans-serif">
                  impact
                </text>
              </>
            )}
          </g>
        );
      })}
    </svg>
  );
}

/* ─── Floating diagnosis panel (overview variant) ─── */
function FloatingDiagnosisPanel({
  diagnosis, runId,
}: { diagnosis: any; runId: string }) {
  if (!diagnosis) return null;
  const score = Math.round(diagnosis.suspicion_score);

  return (
    <div
      style={{
        position: "absolute", top: 16, right: 16,
        width: 272,
        background: "rgba(255,255,255,0.97)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid #E4EAF4",
        borderRadius: 16,
        boxShadow: "0 8px 36px rgba(26,34,54,0.11), inset 0 1px 0 rgba(255,255,255,0.9)",
        overflow: "hidden",
      }}
    >
      {/* Comparison summary */}
      <div style={{ padding: "14px 16px 12px", borderBottom: "1px solid #EEF2F8" }}>
        <p style={{ fontSize: 10, fontWeight: 600, color: "#9BA8BF", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>
          Comparison Summary
        </p>
        <p style={{ fontSize: 22, fontWeight: 900, lineHeight: 1, marginBottom: 4, fontFamily: "monospace" }}>
          <span style={{ color: "#F59E0B" }}>3,300</span>
          <span style={{ fontSize: 14, color: "#1A2236", fontWeight: 700 }}> vs 2,300</span>
        </p>
        <p style={{ fontSize: 11, color: "#9BA8BF" }}>3 downstream events failed</p>
        <p style={{ fontSize: 11, color: "#C8D0E0" }}>2,300</p>
      </div>

      {/* Root cause */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid #EEF2F8" }}>
        <p style={{ fontSize: 10, fontWeight: 700, color: "#1A2236", marginBottom: 5 }}>
          Root Cause Evidence
        </p>
        <p style={{ fontSize: 11, color: "#6B7A99", lineHeight: 1.5 }}>
          Similar successful runs: ~2,300
        </p>
        {/* Suspect chip */}
        <div style={{
          marginTop: 9, padding: "9px 11px",
          background: "linear-gradient(135deg,#FFFBEB,#FFF7E0)",
          border: "1px solid #FDE68A", borderRadius: 9,
        }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: "#1A2236", marginBottom: 1 }}>
            {diagnosis.suspect_step_name}
          </p>
          <p style={{ fontSize: 13, fontWeight: 900, color: "#F59E0B", fontFamily: "monospace" }}>
            Suspicion Score {score}
          </p>
          <p style={{ fontSize: 9, color: "#C8B97A", marginTop: 2 }}>
            Heuristic score · not a probability
          </p>
        </div>
      </div>

      {/* Actions */}
      <div style={{ padding: "10px 12px", display: "flex", gap: 8 }}>
        <Link
          href={`/investigation?run_id=${runId}`}
          style={{
            flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
            padding: "9px 12px", borderRadius: 9, fontWeight: 700, fontSize: 12,
            color: "white", textDecoration: "none",
            background: "#3B82F6",
            boxShadow: "0 3px 10px rgba(59,130,246,0.28)",
          }}
        >
          <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          Open
        </Link>
        <button style={{
          width: 36, height: 36, borderRadius: 9,
          border: "1px solid #E4EAF4", background: "#F8FAFD",
          cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <span style={{ fontSize: 16, color: "#9BA8BF", lineHeight: 1, letterSpacing: "-1px" }}>···</span>
        </button>
      </div>
    </div>
  );
}

/* ─── Spectrum bar ─── */
function SpectrumStrip() {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "center", gap: 12,
      padding: "10px 24px",
      background: "rgba(255,255,255,0.88)",
      backdropFilter: "blur(12px)",
      borderTop: "1px solid #E4EAF4",
      flexShrink: 0,
    }}>
      <span style={{ fontSize: 11, color: "#9BA8BF" }}>base</span>
      <div style={{
        width: 200, height: 9, borderRadius: 99,
        background: "linear-gradient(to right,#94A3B8 0%,#3B82F6 30%,#7C5CFF 55%,#F59E0B 75%,#EF4444 100%)",
        boxShadow: "0 1px 4px rgba(26,34,54,0.08)",
      }} />
      <span style={{ fontSize: 11, color: "#9BA8BF" }}>Intelligence</span>
      <div style={{
        width: 72, height: 9, borderRadius: 99,
        background: "linear-gradient(to right,#F59E0B,#EF4444)",
      }} />
      <span style={{ fontSize: 11, fontWeight: 700, color: "#EF4444" }}>Failure</span>
    </div>
  );
}

/* ─── OVERVIEW PAGE ─── */
const FLAGSHIP = "run_travel_paris_fail";

export default function OverviewPage() {
  const [run,       setRun]       = useState<any>(null);
  const [diagnosis, setDiagnosis] = useState<any>(null);
  const [benchmark, setBenchmark] = useState<any>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading,   setLoading]   = useState(true);

  useEffect(() => {
    Promise.all([
      fetchRun(FLAGSHIP).catch(() => null),
      fetchDiagnosis(FLAGSHIP).catch(() => null),
      fetchBenchmark().catch(() => null),
    ]).then(([r, d, b]) => {
      setRun(r); setDiagnosis(d); setBenchmark(b);
      const suspect = r?.steps?.find((s: any) => s.is_root_suspect);
      setSelectedId(suspect?.id ?? r?.steps?.[0]?.id ?? null);
      setLoading(false);
    });
  }, []);

  const hybrid  = benchmark?.models?.blackbox_hybrid || {};
  const steps   = run?.steps || [];
  const selStep = steps.find((s: any) => s.id === selectedId);

  if (loading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: "#EEF2F7", gap: 12 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: "#EEF2FF", display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <svg className="animate-spin" width="18" height="18" fill="none" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke="#3B82F6" strokeWidth="3" opacity="0.25" />
            <path fill="#3B82F6" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
        <span style={{ fontSize: 13, color: "#6B7A99" }}>Loading flight traces…</span>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden", background: "#EEF2F7" }}>

      {/* ── Top bar ── */}
      <div style={{
        flexShrink: 0,
        padding: "12px 24px",
        background: "#FFFFFF",
        borderBottom: "1px solid #E4EAF4",
        boxShadow: "0 1px 6px rgba(26,34,54,0.05)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        {/* Left: title */}
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 900, color: "#1A2236", margin: 0 }}>
            Flight Control Center
          </h2>
          <p style={{ fontSize: 11, color: "#9BA8BF", marginTop: 2 }}>
            Flagship Demo — TravelPlanner Paris Budget Failure
          </p>
        </div>

        {/* Right: metric chips + CTA */}
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          {[
            { label: "Top-1 Accuracy", value: hybrid.top1_accuracy != null ? `${(hybrid.top1_accuracy*100).toFixed(0)}%` : "—", color: "#7C5CFF" },
            { label: "MRR",            value: hybrid.mrr != null ? hybrid.mrr.toFixed(3) : "—",                               color: "#22C55E" },
            { label: "Runs Recorded",  value: String(steps.length || "—"),                                                    color: "#3B82F6" },
          ].map(s => (
            <div key={s.label} style={{ textAlign: "right" }}>
              <p style={{ fontSize: 9.5, color: "#9BA8BF", margin: 0, fontWeight: 500 }}>{s.label}</p>
              <p style={{ fontSize: 17, fontWeight: 900, color: s.color, fontFamily: "monospace", margin: 0, lineHeight: 1.1 }}>
                {s.value}
              </p>
            </div>
          ))}

          <Link
            href="/investigation?run_id=run_travel_paris_fail"
            style={{
              display: "flex", alignItems: "center", gap: 7,
              padding: "9px 18px", borderRadius: 11, fontWeight: 700, fontSize: 12.5,
              color: "white", textDecoration: "none", marginLeft: 4,
              background: "#3B82F6",
              boxShadow: "0 3px 14px rgba(59,130,246,0.28)",
            }}
          >
            Investigate
            <ArrowRight style={{ width: 14, height: 14 }} />
          </Link>
        </div>
      </div>

      {/* ── Graph canvas ── */}
      <div style={{ flex: 1, position: "relative", overflow: "hidden", background: "#F2F5FB" }}>

        {/* Canvas label */}
        <div style={{
          position: "absolute", top: 14, left: 14, zIndex: 10,
          display: "flex", alignItems: "center", gap: 7,
          padding: "6px 12px", borderRadius: 10,
          background: "rgba(255,255,255,0.78)",
          backdropFilter: "blur(8px)",
          border: "1px solid rgba(228,234,244,0.9)",
          fontSize: 11, color: "#6B7A99",
        }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#22C55E", boxShadow: "0 0 5px #22C55E", display: "inline-block" }} />
          Radial Graph Canvas
          <span style={{ color: "#DDE3EE", margin: "0 2px" }}>|</span>
          <span style={{ color: "#9BA8BF" }}>TravelPlanner Paris</span>
        </div>

        {run && (
          <OverviewRadialGraph
            steps={steps}
            diagnosis={diagnosis}
            agentName={run.agent_name}
            runStatus={run.status}
            selectedId={selectedId}
            onSelectStep={setSelectedId}
          />
        )}

        {/* Floating panel */}
        {diagnosis && <FloatingDiagnosisPanel diagnosis={diagnosis} runId={FLAGSHIP} />}

        {/* Selected step tooltip — bottom left */}
        {selStep && (
          <div style={{
            position: "absolute", bottom: 16, left: 16,
            display: "flex", alignItems: "center", gap: 10,
            padding: "10px 14px",
            background: "rgba(255,255,255,0.96)",
            backdropFilter: "blur(16px)",
            border: "1px solid #E4EAF4",
            borderRadius: 13,
            boxShadow: "0 4px 20px rgba(26,34,54,0.09)",
            maxWidth: 340,
          }}>
            <div style={{
              width: 30, height: 30, borderRadius: 8, flexShrink: 0,
              background: selStep.is_root_suspect ? "#FEF3C7" : selStep.status === "FAILED" ? "#FFF1F2" : "#ECFDF5",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              {selStep.is_root_suspect
                ? <AlertTriangle style={{ width: 14, height: 14, color: "#F59E0B" }} />
                : selStep.status === "FAILED"
                ? <XCircle style={{ width: 14, height: 14, color: "#EF4444" }} />
                : <CheckCircle2 style={{ width: 14, height: 14, color: "#22C55E" }} />}
            </div>
            <div style={{ minWidth: 0 }}>
              <p style={{ fontSize: 11.5, fontWeight: 700, color: "#1A2236", margin: 0 }}>
                Step {selStep.step_index}: {selStep.step_name}
              </p>
              <p style={{ fontSize: 10, fontFamily: "monospace", color: "#9BA8BF", margin: "2px 0 0" }}>
                {selStep.tool_name} · {selStep.duration_ms?.toFixed(0)}ms
              </p>
            </div>
            {selStep.is_root_suspect && (
              <span style={{ fontFamily: "monospace", fontWeight: 900, fontSize: 15, color: "#F59E0B", flexShrink: 0 }}>
                {selStep.suspicion_score?.toFixed(0)}
              </span>
            )}
          </div>
        )}

        {/* Bottom-right action buttons */}
        <div style={{ position: "absolute", bottom: 16, right: 16, display: "flex", gap: 8 }}>
          <Link
            href="/replay?run_id=run_travel_paris_fail&step_id=step_tp_3"
            style={{
              display: "flex", alignItems: "center", gap: 7,
              padding: "9px 16px", borderRadius: 11, fontWeight: 700, fontSize: 12,
              color: "white", textDecoration: "none",
              background: "#F59E0B",
              boxShadow: "0 3px 12px rgba(245,158,11,0.28)",
            }}
          >
            <RotateCcw style={{ width: 13, height: 13 }} />
            Test Fix in Replay Lab
          </Link>
          <Link
            href="/executions"
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "9px 16px", borderRadius: 11, fontWeight: 700, fontSize: 12,
              color: "#1A2236", textDecoration: "none",
              background: "rgba(255,255,255,0.95)",
              border: "1px solid #E4EAF4",
              boxShadow: "0 1px 6px rgba(26,34,54,0.06)",
            }}
          >
            All Runs
            <ArrowRight style={{ width: 13, height: 13 }} />
          </Link>
        </div>
      </div>

      {/* ── Spectrum bar ── */}
      <SpectrumStrip />
    </div>
  );
}
