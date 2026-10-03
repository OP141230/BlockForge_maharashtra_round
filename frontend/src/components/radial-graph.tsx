"use client";

import React, { useState } from "react";

interface StepNode {
  id: string;
  step_index: number;
  step_name: string;
  tool_name: string;
  status: string;
  duration_ms: number;
  suspicion_score?: number;
  is_root_suspect?: boolean;
  is_downstream_impact?: boolean;
  side_effect_flag?: boolean;
  error_text?: string;
}

interface RadialGraphProps {
  agentName: string;
  scenario: string;
  status: string;
  durationMs: number;
  steps: StepNode[];
  selectedStepId: string | null;
  onSelectStep: (id: string) => void;
}

/* ── Donut centre node ── */
function DonutCenter({
  cx, cy, agentName, status, total,
}: {
  cx: number; cy: number; agentName: string; status: string; total: number;
}) {
  const r = 46;
  const strokeW = 8;
  const segments = [
    { color: "#3B82F6", pct: 0.30 },
    { color: "#7C5CFF", pct: 0.25 },
    { color: "#F59E0B", pct: 0.25 },
    { color: "#22C55E", pct: 0.20 },
  ];
  const circ = 2 * Math.PI * r;
  let offset = 0;

  return (
    <g>
      {/* Outer glow ring */}
      <circle cx={cx} cy={cy} r={r + 16} fill="rgba(59,130,246,0.06)" />
      <circle cx={cx} cy={cy} r={r + 10} fill="rgba(59,130,246,0.08)" />
      {/* White background disc */}
      <circle cx={cx} cy={cy} r={r + strokeW / 2 + 2} fill="white" />

      {/* Donut segments */}
      {segments.map((seg, i) => {
        const dash = seg.pct * circ;
        const gap  = circ - dash;
        const el = (
          <circle
            key={i}
            cx={cx} cy={cy} r={r}
            fill="none"
            stroke={seg.color}
            strokeWidth={strokeW}
            strokeDasharray={`${dash} ${gap}`}
            strokeDashoffset={-offset}
            style={{ transform: `rotate(-90deg)`, transformOrigin: `${cx}px ${cy}px` }}
          />
        );
        offset += dash;
        return el;
      })}

      {/* Inner white hole */}
      <circle cx={cx} cy={cy} r={r - strokeW / 2 - 1} fill="white" />

      {/* Labels inside */}
      <text x={cx} y={cy - 10} textAnchor="middle" fontSize="11" fontWeight="700"
        fill="#1A2236" fontFamily="Inter,sans-serif">
        {agentName.length > 14 ? agentName.slice(0, 14) + "…" : agentName}
      </text>
      <text x={cx} y={cy + 6} textAnchor="middle" fontSize="9" fill="#6B7A99"
        fontFamily="Inter,sans-serif">
        {total} nodes
      </text>
      <text x={cx} y={cy + 20} textAnchor="middle" fontSize="9" fontWeight="700"
        fill={status === "FAILED" ? "#EF4444" : "#22C55E"}
        fontFamily="Inter,sans-serif">
        {status}
      </text>
    </g>
  );
}

/* ── Individual step circle node ── */
function StepCircle({
  x, y, step, isSelected, onClick,
}: {
  x: number; y: number; step: StepNode;
  isSelected: boolean; onClick: () => void;
}) {
  const isSuspect    = step.is_root_suspect || (step.suspicion_score != null && step.suspicion_score > 75);
  const isDownstream = step.is_downstream_impact || (step.status === "FAILED" && !isSuspect);
  const isOk         = !isSuspect && !isDownstream;

  const R = isSuspect ? 24 : 18;

  const fill    = isSuspect ? "#FEF3C7" : isDownstream ? "#FFF1F2" : "#FFFFFF";
  const stroke  = isSuspect ? "#F59E0B" : isDownstream ? "#EF4444" : isSelected ? "#3B82F6" : "#DDE3EE";
  const strokeW = isSuspect || isSelected ? 2.5 : 1.5;

  /* Checkmark path (scaled to circle) */
  const tick = `M ${x - 5} ${y} l 3.5 3.5 l 6 -6`;

  return (
    <g onClick={onClick} style={{ cursor: "pointer" }}>
      {/* Amber glow ring for suspect */}
      {isSuspect && (
        <>
          <circle cx={x} cy={y} r={R + 12} fill="rgba(245,158,11,0.12)" />
          <circle cx={x} cy={y} r={R + 7}  fill="rgba(245,158,11,0.18)" />
        </>
      )}
      {/* Red glow for downstream */}
      {isDownstream && (
        <circle cx={x} cy={y} r={R + 8} fill="rgba(239,68,68,0.10)" />
      )}

      <circle
        cx={x} cy={y} r={R}
        fill={fill}
        stroke={stroke}
        strokeWidth={strokeW}
        style={{ filter: isSuspect ? "drop-shadow(0 0 8px rgba(245,158,11,0.5))" : isDownstream ? "drop-shadow(0 0 6px rgba(239,68,68,0.35))" : "none" }}
      />

      {/* Icon inside node */}
      {isOk && (
        <path d={tick} fill="none" stroke="#22C55E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      )}
      {isDownstream && (
        <>
          <line x1={x - 4} y1={y - 4} x2={x + 4} y2={y + 4} stroke="#EF4444" strokeWidth="2" strokeLinecap="round" />
          <line x1={x + 4} y1={y - 4} x2={x - 4} y2={y + 4} stroke="#EF4444" strokeWidth="2" strokeLinecap="round" />
        </>
      )}
      {isSuspect && (
        <text x={x} y={y + 5} textAnchor="middle" fontSize="13" fill="#D97706" fontWeight="800">!</text>
      )}

      {/* Step label below */}
      <text
        x={x} y={y + R + 14}
        textAnchor="middle"
        fontSize="9"
        fontWeight={isSuspect ? "700" : "500"}
        fill={isSuspect ? "#B45309" : isDownstream ? "#DC2626" : "#6B7A99"}
        fontFamily="Inter,sans-serif"
      >
        {step.step_name.length > 13 ? step.step_name.slice(0, 13) + "…" : step.step_name}
      </text>

      {/* Suspicion score chip */}
      {isSuspect && step.suspicion_score != null && (
        <>
          <rect x={x - 22} y={y + R + 18} width={44} height={14} rx={7}
            fill="#F59E0B" />
          <text x={x} y={y + R + 28} textAnchor="middle" fontSize="8"
            fontWeight="700" fill="white" fontFamily="Inter,sans-serif">
            Score {Math.round(step.suspicion_score)}
          </text>
        </>
      )}

      {/* "N impact" label for downstream */}
      {isDownstream && (
        <>
          <rect x={x - 18} y={y + R + 18} width={36} height={13} rx={6}
            fill="#FFF1F2" stroke="#FCA5A5" strokeWidth="0.8" />
          <text x={x} y={y + R + 27} textAnchor="middle" fontSize="7.5"
            fontWeight="600" fill="#EF4444" fontFamily="Inter,sans-serif">
            impact
          </text>
        </>
      )}
    </g>
  );
}

export default function RadialGraph({
  agentName, scenario, status, durationMs, steps, selectedStepId, onSelectStep,
}: RadialGraphProps) {
  const W = 880, H = 560;
  const cx = W / 2, cy = H / 2 - 10;
  const orbitR = 200;
  const total  = steps.length;

  const angleOf = (i: number) =>
    (2 * Math.PI * i) / Math.max(total, 1) - Math.PI / 2;

  return (
    <div
      className="relative w-full rounded-2xl overflow-hidden"
      style={{
        background: "#F0F4FA",
        border: "1px solid #DDE3EE",
        boxShadow: "0 2px 16px rgba(26,34,54,0.07)",
        minHeight: 480,
      }}
    >
      {/* Canvas label */}
      <div
        className="absolute top-4 left-4 z-10 flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-xl"
        style={{ background: "rgba(255,255,255,0.85)", border: "1px solid #DDE3EE", color: "#6B7A99" }}
      >
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: "#22C55E", boxShadow: "0 0 6px #22C55E" }}
        />
        Radial Graph Canvas
        <span style={{ color: "#C8D0E0" }}>|</span>
        <span className="truncate max-w-[200px]">{scenario}</span>
      </div>

      <svg
        width="100%" viewBox={`0 0 ${W} ${H}`}
        style={{ display: "block" }}
      >
        {/* ── Mesh background ── */}
        <defs>
          <pattern id="mesh" width="80" height="80" patternUnits="userSpaceOnUse">
            <path d="M40 0 L80 40 L40 80 L0 40 Z" fill="none" stroke="#C8D4E8" strokeWidth="0.5" opacity="0.5" />
            <path d="M40 10 L70 40 L40 70 L10 40 Z" fill="none" stroke="#C8D4E8" strokeWidth="0.4" opacity="0.35" />
          </pattern>
          <radialGradient id="centreGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="#3B82F6" stopOpacity="0.06" />
            <stop offset="100%" stopColor="#7C5CFF" stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect width={W} height={H} fill="url(#mesh)" />
        <circle cx={cx} cy={cy} r={220} fill="url(#centreGlow)" />

        {/* Orbit ring (dashed circle) */}
        <circle
          cx={cx} cy={cy} r={orbitR}
          fill="none"
          stroke="#C8D4E8"
          strokeWidth="1"
          strokeDasharray="6 5"
          opacity="0.7"
        />

        {/* ── Spokes from centre to each node ── */}
        {steps.map((step, i) => {
          const angle = angleOf(i);
          const nx = cx + orbitR * Math.cos(angle);
          const ny = cy + orbitR * Math.sin(angle);
          const isSuspect = step.is_root_suspect || (step.suspicion_score != null && step.suspicion_score > 75);
          const isDown    = step.is_downstream_impact || (step.status === "FAILED" && !isSuspect);

          return (
            <line
              key={`spoke-${step.id}`}
              x1={cx} y1={cy} x2={nx} y2={ny}
              stroke={isSuspect ? "#F59E0B" : isDown ? "#EF4444" : "#C8D4E8"}
              strokeWidth={isSuspect ? 2 : isDown ? 1.5 : 1}
              strokeDasharray={isDown ? "4 3" : "none"}
              opacity={isSuspect ? 1 : 0.7}
            />
          );
        })}

        {/* ── Sequential orbit arc connectors ── */}
        {steps.map((step, i) => {
          if (i === steps.length - 1) return null;
          const a1 = angleOf(i);
          const a2 = angleOf(i + 1);
          const x1 = cx + orbitR * Math.cos(a1);
          const y1 = cy + orbitR * Math.sin(a1);
          const x2 = cx + orbitR * Math.cos(a2);
          const y2 = cy + orbitR * Math.sin(a2);
          return (
            <line
              key={`seq-${i}`}
              x1={x1} y1={y1} x2={x2} y2={y2}
              stroke="#B8C4D8" strokeWidth="1" strokeDasharray="3 4" opacity="0.5"
            />
          );
        })}

        {/* ── Donut centre ── */}
        <DonutCenter cx={cx} cy={cy} agentName={agentName} status={status} total={total} />

        {/* ── Step nodes ── */}
        {steps.map((step, i) => {
          const angle = angleOf(i);
          const nx = cx + orbitR * Math.cos(angle);
          const ny = cy + orbitR * Math.sin(angle);
          return (
            <StepCircle
              key={step.id}
              x={nx} y={ny}
              step={step}
              isSelected={selectedStepId === step.id}
              onClick={() => onSelectStep(step.id)}
            />
          );
        })}
      </svg>
    </div>
  );
}
