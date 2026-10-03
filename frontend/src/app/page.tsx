"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  RotateCcw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import { fetchRun, fetchDiagnosis, fetchBenchmark } from "@/lib/api";

/* ─────────────────────────────────────────────
   Mini inline radial graph (self-contained SVG)
   so the overview has zero extra imports
───────────────────────────────────────────── */
function OverviewGraph({
  steps,
  diagnosis,
  agentName,
  runStatus,
  onSelectStep,
  selectedId,
}: {
  steps: any[];
  diagnosis: any;
  agentName: string;
  runStatus: string;
  onSelectStep: (id: string) => void;
  selectedId: string | null;
}) {
  const W = 760, H = 500;
  const cx = 340, cy = 250;
  const orbitR = 185;
  const total = steps.length;
  const suspectId = diagnosis?.suspect_step_id;

  const angleOf = (i: number) =>
    (2 * Math.PI * i) / Math.max(total, 1) - Math.PI / 2;

  /* donut segments */
  const r = 44, sw = 8;
  const circ = 2 * Math.PI * r;
  const segs = [
    { c: "#3B82F6", p: 0.30 },
    { c: "#7C5CFF", p: 0.25 },
    { c: "#F59E0B", p: 0.25 },
    { c: "#22C55E", p: 0.20 },
  ];
  let off = 0;

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${W} ${H}`}
      style={{ display: "block", userSelect: "none" }}
    >
      <defs>
        <pattern id="mesh2" width="80" height="80" patternUnits="userSpaceOnUse">
          <path d="M40 0L80 40L40 80L0 40Z" fill="none" stroke="#C8D4E8" strokeWidth="0.5" opacity="0.45" />
          <path d="M40 12L68 40L40 68L12 40Z" fill="none" stroke="#C8D4E8" strokeWidth="0.35" opacity="0.3" />
        </pattern>
        <radialGradient id="glow2" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.07" />
          <stop offset="100%" stopColor="#7C5CFF" stopOpacity="0" />
        </radialGradient>
        {/* amber glow filter */}
        <filter id="amberGlow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="6" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      {/* mesh bg */}
      <rect width={W} height={H} fill="url(#mesh2)" />
      <circle cx={cx} cy={cy} r={210} fill="url(#glow2)" />

      {/* orbit ring */}
      <circle cx={cx} cy={cy} r={orbitR} fill="none"
        stroke="#C8D4E8" strokeWidth="1" strokeDasharray="6 5" opacity="0.6" />

      {/* spokes */}
      {steps.map((step, i) => {
        const angle = angleOf(i);
        const nx = cx + orbitR * Math.cos(angle);
        const ny = cy + orbitR * Math.sin(angle);
        const isSuspect = step.id === suspectId || step.is_root_suspect;
        const isDown = step.is_downstream_impact || (step.status === "FAILED" && !isSuspect);
        return (
          <line key={`sp-${i}`}
            x1={cx} y1={cy} x2={nx} y2={ny}
            stroke={isSuspect ? "#F59E0B" : isDown ? "#EF4444" : "#C8D4E8"}
            strokeWidth={isSuspect ? 2 : 1}
            strokeDasharray={isDown ? "4 3" : "none"}
            opacity={isSuspect ? 1 : 0.65}
          />
        );
      })}

      {/* seq lines between nodes */}
      {steps.map((_, i) => {
        if (i === steps.length - 1) return null;
        const a1 = angleOf(i), a2 = angleOf(i + 1);
        return (
          <line key={`seq-${i}`}
            x1={cx + orbitR * Math.cos(a1)} y1={cy + orbitR * Math.sin(a1)}
            x2={cx + orbitR * Math.cos(a2)} y2={cy + orbitR * Math.sin(a2)}
            stroke="#B8C4D8" strokeWidth="0.8" strokeDasharray="3 4" opacity="0.4"
          />
        );
      })}

      {/* ── DONUT CENTRE ── */}
      <circle cx={cx} cy={cy} r={r + sw / 2 + 3} fill="white"
        style={{ filter: "drop-shadow(0 2px 12px rgba(59,130,246,0.15))" }} />
      {segs.map((seg, i) => {
        const dash = seg.p * circ;
        const gap = circ - dash;
        const el = (
          <circle key={i} cx={cx} cy={cy} r={r} fill="none"
            stroke={seg.c} strokeWidth={sw}
            strokeDasharray={`${dash} ${gap}`}
            strokeDashoffset={-off}
            style={{ transform: `rotate(-90deg)`, transformOrigin: `${cx}px ${cy}px` }}
          />
        );
        off += dash;
        return el;
      })}
      <circle cx={cx} cy={cy} r={r - sw / 2 - 1} fill="white" />
      <text x={cx} y={cy - 8} textAnchor="middle" fontSize="10" fontWeight="700"
        fill="#1A2236" fontFamily="Inter,sans-serif">
        {agentName.length > 13 ? agentName.slice(0, 13) + "…" : agentName}
      </text>
      <text x={cx} y={cy + 6} textAnchor="middle" fontSize="8.5" fill="#6B7A99"
        fontFamily="Inter,sans-serif">
        {total} nodes
      </text>
      <text x={cx} y={cy + 20} textAnchor="middle" fontSize="8.5" fontWeight="700"
        fill={runStatus === "FAILED" ? "#EF4444" : "#22C55E"}
        fontFamily="Inter,sans-serif">
        {runStatus}
      </text>

      {/* ── STEP NODES ── */}
      {steps.map((step, i) => {
        const angle = angleOf(i);
        const nx = cx + orbitR * Math.cos(angle);
        const ny = cy + orbitR * Math.sin(angle);
        const isSuspect = step.id === suspectId || step.is_root_suspect;
        const isDown = step.is_downstream_impact || (step.status === "FAILED" && !isSuspect);
        const isOk = !isSuspect && !isDown;
        const isSelected = selectedId === step.id;
        const R = isSuspect ? 22 : 16;

        return (
          <g key={step.id} onClick={() => onSelectStep(step.id)}
            style={{ cursor: "pointer" }}>
            {/* amber glow rings */}
            {isSuspect && (
              <>
                <circle cx={nx} cy={ny} r={R + 16} fill="rgba(245,158,11,0.10)" />
                <circle cx={nx} cy={ny} r={R + 10} fill="rgba(245,158,11,0.16)" />
                <circle cx={nx} cy={ny} r={R + 5}  fill="rgba(245,158,11,0.24)" />
              </>
            )}
            {isDown && (
              <circle cx={nx} cy={ny} r={R + 7} fill="rgba(239,68,68,0.12)" />
            )}

            <circle cx={nx} cy={ny} r={R}
              fill={isSuspect ? "#FEF3C7" : isDown ? "#FFF1F2" : "#FFFFFF"}
              stroke={isSuspect ? "#F59E0B" : isDown ? "#EF4444" : isSelected ? "#3B82F6" : "#DDE3EE"}
              strokeWidth={isSuspect ? 2.5 : isSelected ? 2 : 1.5}
              style={isSuspect
                ? { filter: "drop-shadow(0 0 8px rgba(245,158,11,0.55))" }
                : isDown
                ? { filter: "drop-shadow(0 0 6px rgba(239,68,68,0.40))" }
                : {}}
            />

            {/* icon inside */}
            {isOk && (
              <path d={`M ${nx-5} ${ny} l 3.5 3.5 l 6 -6`}
                fill="none" stroke="#22C55E" strokeWidth="2"
                strokeLinecap="round" strokeLinejoin="round" />
            )}
            {isDown && (
              <>
                <line x1={nx-4} y1={ny-4} x2={nx+4} y2={ny+4} stroke="#EF4444" strokeWidth="2" strokeLinecap="round" />
                <line x1={nx+4} y1={ny-4} x2={nx-4} y2={ny+4} stroke="#EF4444" strokeWidth="2" strokeLinecap="round" />
              </>
            )}
            {isSuspect && (
              <text x={nx} y={ny + 5} textAnchor="middle" fontSize="14" fontWeight="800" fill="#D97706">!</text>
            )}

            {/* step label */}
            <text x={nx} y={ny + R + 13} textAnchor="middle" fontSize="8.5"
              fontWeight={isSuspect ? "700" : "500"}
              fill={isSuspect ? "#B45309" : isDown ? "#DC2626" : "#6B7A99"}
              fontFamily="Inter,sans-serif">
              {step.step_name.length > 12 ? step.step_name.slice(0, 12) + "…" : step.step_name}
            </text>

            {/* suspect score chip */}
            {isSuspect && step.suspicion_score != null && (
              <>
                <rect x={nx - 24} y={ny + R + 16} width={48} height={14} rx={7} fill="#F59E0B" />
                <text x={nx} y={ny + R + 26} textAnchor="middle" fontSize="7.5"
                  fontWeight="700" fill="white" fontFamily="Inter,sans-serif">
                  Score {Math.round(step.suspicion_score)}
                </text>
              </>
            )}

            {/* downstream label */}
            {isDown && (
              <>
                <rect x={nx - 18} y={ny + R + 16} width={36} height={13} rx={6}
                  fill="#FFF1F2" stroke="#FCA5A5" strokeWidth="0.8" />
                <text x={nx} y={ny + R + 25} textAnchor="middle" fontSize="7"
                  fontWeight="600" fill="#EF4444" fontFamily="Inter,sans-serif">
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

/* ─────────────────────────────────────────────
   Floating diagnosis / comparison panel
───────────────────────────────────────────── */
function FloatingPanel({ diagnosis, runId }: { diagnosis: any; runId: string }) {
  if (!diagnosis) return null;
  return (
    <div
      className="absolute top-5 right-5 w-72 rounded-2xl p-5 flex flex-col gap-3"
      style={{
        background: "rgba(255,255,255,0.97)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid #DDE3EE",
        boxShadow: "0 8px 32px rgba(26,34,54,0.12)",
      }}
    >
      {/* Comparison summary */}
      <div>
        <p className="text-xs font-semibold mb-1" style={{ color: "#6B7A99" }}>
          Comparison Summary
        </p>
        <p className="text-2xl font-black leading-none" style={{ color: "#F59E0B" }}>
          3,300{" "}
          <span className="text-base font-bold" style={{ color: "#1A2236" }}>
            vs 2,300
          </span>
        </p>
        <p className="text-xs mt-1.5" style={{ color: "#6B7A99" }}>
          3 downstream events failed
        </p>
        <p className="text-xs" style={{ color: "#9BA8BF" }}>
          2,300
        </p>
      </div>

      <div style={{ borderTop: "1px solid #EEF2F7" }} className="pt-3">
        <p className="text-xs font-bold mb-1" style={{ color: "#1A2236" }}>
          Root Cause Evidence
        </p>
        <p className="text-xs" style={{ color: "#6B7A99" }}>
          Similar successful runs: ~2,300
        </p>
      </div>

      {/* Suspect chip */}
      <div
        className="rounded-xl px-3 py-2.5"
        style={{ background: "#FFFBEB", border: "1px solid #FDE68A" }}
      >
        <p className="text-xs font-bold" style={{ color: "#1A2236" }}>
          {diagnosis.suspect_step_name}
        </p>
        <p className="text-sm font-black" style={{ color: "#F59E0B" }}>
          Suspicion Score {Math.round(diagnosis.suspicion_score)}
        </p>
        <p className="text-[10px] mt-0.5" style={{ color: "#9BA8BF" }}>
          Heuristic score · not a probability
        </p>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        <Link
          href={`/investigation?run_id=${runId}`}
          className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl font-bold text-xs text-white transition-all hover:opacity-90"
          style={{ background: "#3B82F6", boxShadow: "0 3px 10px rgba(59,130,246,0.30)" }}
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          Open
        </Link>
        <button
          className="w-9 h-9 rounded-xl flex items-center justify-center transition-all hover:bg-slate-50"
          style={{ border: "1px solid #DDE3EE" }}
        >
          <span className="text-base font-bold" style={{ color: "#6B7A99" }}>···</span>
        </button>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Spectrum bar
───────────────────────────────────────────── */
function MiniSpectrumBar() {
  return (
    <div
      className="flex items-center justify-center gap-4 py-3"
      style={{
        background: "rgba(255,255,255,0.88)",
        backdropFilter: "blur(12px)",
        borderTop: "1px solid #DDE3EE",
      }}
    >
      <span className="text-xs" style={{ color: "#9BA8BF" }}>base</span>
      <div
        className="w-56 h-2.5 rounded-full"
        style={{
          background:
            "linear-gradient(to right,#94A3B8 0%,#3B82F6 30%,#7C5CFF 55%,#F59E0B 75%,#EF4444 100%)",
        }}
      />
      <span className="text-xs" style={{ color: "#9BA8BF" }}>Intelligence</span>
      <div
        className="w-20 h-2.5 rounded-full"
        style={{ background: "linear-gradient(to right,#F59E0B,#EF4444)" }}
      />
      <span className="text-xs font-semibold" style={{ color: "#EF4444" }}>Failure</span>
    </div>
  );
}

/* ─────────────────────────────────────────────
   OVERVIEW PAGE
───────────────────────────────────────────── */
export default function OverviewPage() {
  const FLAGSHIP_RUN = "run_travel_paris_fail";

  const [run,       setRun]       = useState<any>(null);
  const [diagnosis, setDiagnosis] = useState<any>(null);
  const [benchmark, setBenchmark] = useState<any>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading,   setLoading]   = useState(true);

  useEffect(() => {
    Promise.all([
      fetchRun(FLAGSHIP_RUN).catch(() => null),
      fetchDiagnosis(FLAGSHIP_RUN).catch(() => null),
      fetchBenchmark().catch(() => null),
    ]).then(([r, d, b]) => {
      setRun(r);
      setDiagnosis(d);
      setBenchmark(b);
      const suspect = r?.steps?.find((s: any) => s.is_root_suspect);
      if (suspect) setSelectedId(suspect.id);
      else if (r?.steps?.length) setSelectedId(r.steps[0].id);
      setLoading(false);
    });
  }, []);

  const hybrid  = benchmark?.models?.blackbox_hybrid || {};
  const steps   = run?.steps || [];

  /* Selected step info */
  const selectedStep = steps.find((s: any) => s.id === selectedId);

  if (loading) {
    return (
      <div
        className="flex-1 flex flex-col h-full items-center justify-center gap-3"
        style={{ background: "#EEF2F7" }}
      >
        <div
          className="w-10 h-10 rounded-2xl flex items-center justify-center"
          style={{ background: "#EEF2FF" }}
        >
          <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="#3B82F6" strokeWidth="3" />
            <path className="opacity-75" fill="#3B82F6"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
        <p className="text-sm" style={{ color: "#6B7A99" }}>Loading flight traces…</p>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col h-full overflow-hidden"
      style={{ background: "#EEF2F7" }}
    >
      {/* ── Top bar ── */}
      <div
        className="shrink-0 px-7 py-3.5 flex items-center justify-between"
        style={{
          background: "#FFFFFF",
          borderBottom: "1px solid #DDE3EE",
          boxShadow: "0 1px 6px rgba(26,34,54,0.05)",
        }}
      >
        <div className="flex items-center gap-3">
          <div>
            <h2 className="text-base font-black" style={{ color: "#1A2236" }}>
              Flight Control Center
            </h2>
            <p className="text-xs mt-0.5" style={{ color: "#9BA8BF" }}>
              Flagship Demo — TravelPlanner Paris Budget Failure
            </p>
          </div>
        </div>

        {/* Quick stats */}
        <div className="flex items-center gap-5">
          {[
            { label: "Top-1 Accuracy", value: hybrid.top1_accuracy != null ? `${(hybrid.top1_accuracy * 100).toFixed(0)}%` : "—", color: "#7C5CFF" },
            { label: "MRR", value: hybrid.mrr != null ? hybrid.mrr.toFixed(3) : "—", color: "#22C55E" },
            { label: "Runs Recorded", value: benchmark ? String(benchmark.total_cases || 6) : "—", color: "#3B82F6" },
          ].map((s) => (
            <div key={s.label} className="text-right">
              <p className="text-[10px] font-medium" style={{ color: "#9BA8BF" }}>{s.label}</p>
              <p className="text-lg font-black font-mono leading-none" style={{ color: s.color }}>{s.value}</p>
            </div>
          ))}

          <Link
            href="/investigation?run_id=run_travel_paris_fail"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm text-white ml-4 transition-all hover:opacity-90"
            style={{ background: "#3B82F6", boxShadow: "0 3px 12px rgba(59,130,246,0.30)" }}
          >
            Investigate
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* ── Canvas — graph + floating panel ── */}
      <div className="flex-1 relative overflow-hidden" style={{ background: "#F0F4FA" }}>
        {run && (
          <OverviewGraph
            steps={steps}
            diagnosis={diagnosis}
            agentName={run.agent_name}
            runStatus={run.status}
            onSelectStep={setSelectedId}
            selectedId={selectedId}
          />
        )}

        {/* Floating diagnosis panel — top right */}
        {diagnosis && <FloatingPanel diagnosis={diagnosis} runId={FLAGSHIP_RUN} />}

        {/* Selected step tooltip — bottom left */}
        {selectedStep && (
          <div
            className="absolute bottom-5 left-5 rounded-2xl px-4 py-3 flex items-center gap-3"
            style={{
              background: "rgba(255,255,255,0.95)",
              backdropFilter: "blur(16px)",
              border: "1px solid #DDE3EE",
              boxShadow: "0 4px 20px rgba(26,34,54,0.09)",
              maxWidth: 360,
            }}
          >
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
              style={{
                background: selectedStep.is_root_suspect
                  ? "#FEF3C7"
                  : selectedStep.status === "FAILED"
                  ? "#FFF1F2"
                  : "#ECFDF5",
              }}
            >
              {selectedStep.is_root_suspect ? (
                <AlertTriangle className="w-4 h-4" style={{ color: "#F59E0B" }} />
              ) : selectedStep.status === "FAILED" ? (
                <XCircle className="w-4 h-4" style={{ color: "#EF4444" }} />
              ) : (
                <CheckCircle2 className="w-4 h-4" style={{ color: "#22C55E" }} />
              )}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold truncate" style={{ color: "#1A2236" }}>
                Step {selectedStep.step_index}: {selectedStep.step_name}
              </p>
              <p className="text-[11px] font-mono truncate" style={{ color: "#9BA8BF" }}>
                {selectedStep.tool_name} · {selectedStep.duration_ms?.toFixed(0)}ms
              </p>
            </div>
            {selectedStep.is_root_suspect && (
              <span
                className="font-mono font-black text-sm shrink-0"
                style={{ color: "#F59E0B" }}
              >
                91
              </span>
            )}
          </div>
        )}

        {/* Bottom actions strip */}
        <div
          className="absolute bottom-5 right-5 flex items-center gap-2"
        >
          <Link
            href="/replay?run_id=run_travel_paris_fail&step_id=step_tp_3"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs text-white transition-all hover:opacity-90"
            style={{ background: "#F59E0B", boxShadow: "0 3px 12px rgba(245,158,11,0.30)" }}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Test Fix in Replay Lab
          </Link>
          <Link
            href="/executions"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs transition-all hover:opacity-90"
            style={{
              background: "rgba(255,255,255,0.95)",
              border: "1px solid #DDE3EE",
              color: "#1A2236",
            }}
          >
            All Runs
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* ── Spectrum bar ── */}
      <MiniSpectrumBar />
    </div>
  );
}
