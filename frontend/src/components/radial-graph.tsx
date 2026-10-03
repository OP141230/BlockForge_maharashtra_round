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

/* Truncate label cleanly */
const trunc = (s: string, n: number) => s.length > n ? s.slice(0, n) + "…" : s;

/* Compute label position offset to avoid overlap with orbit edge */
function labelOffset(angle: number, R: number, extraR: number) {
  const lx = Math.cos(angle) * (R + extraR);
  const ly = Math.sin(angle) * (R + extraR);
  return { lx, ly };
}

export default function RadialGraph({
  agentName, scenario, status, durationMs, steps, selectedStepId, onSelectStep,
}: RadialGraphProps) {
  const [hovered, setHovered] = useState<string | null>(null);

  /* Canvas dimensions — wider viewport */
  const W = 920, H = 560;
  const cx = W / 2 - 20, cy = H / 2;

  /* Orbit radius — generous so nodes don't crowd centre */
  const orbitR = 195;

  /* Node radii */
  const R_NORMAL  = 14;
  const R_SUSPECT = 20;

  const total = steps.length;
  const angleOf = (i: number) =>
    (2 * Math.PI * i) / Math.max(total, 1) - Math.PI / 2;

  /* ── Donut segments ── */
  const donutR = 42, donutSW = 7;
  const circ   = 2 * Math.PI * donutR;
  const segs   = [
    { c: "#3B82F6", p: 0.30 },
    { c: "#7C5CFF", p: 0.25 },
    { c: "#F59E0B", p: 0.25 },
    { c: "#22C55E", p: 0.20 },
  ];
  let segOff = 0;

  return (
    <div
      className="relative w-full rounded-2xl overflow-hidden"
      style={{
        background: "#F2F5FB",
        border: "1px solid #E0E7F0",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.8), 0 2px 16px rgba(26,34,54,0.06)",
        minHeight: 480,
      }}
    >
      {/* Canvas label */}
      <div
        className="absolute top-4 left-4 z-10 flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-xl"
        style={{
          background: "rgba(255,255,255,0.80)",
          backdropFilter: "blur(8px)",
          border: "1px solid rgba(220,228,242,0.9)",
          color: "#6B7A99",
        }}
      >
        <span
          style={{
            width: 7, height: 7, borderRadius: "50%",
            background: "#22C55E",
            boxShadow: "0 0 5px #22C55E",
            display: "inline-block",
          }}
        />
        Radial Graph
        <span style={{ color: "#DDE3EE" }}>|</span>
        <span
          className="truncate"
          style={{ maxWidth: 180, color: "#9BA8BF" }}
        >
          {scenario}
        </span>
      </div>

      <svg
        width="100%"
        viewBox={`0 0 ${W} ${H}`}
        style={{ display: "block" }}
      >
        <defs>
          {/* Very subtle diamond mesh */}
          <pattern id="rg-mesh" width="72" height="72" patternUnits="userSpaceOnUse">
            <path
              d="M36 0 L72 36 L36 72 L0 36 Z"
              fill="none" stroke="#C8D4E8" strokeWidth="0.4" opacity="0.35"
            />
          </pattern>
          {/* Soft radial glow behind donut */}
          <radialGradient id="rg-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="#7C5CFF" stopOpacity="0.07" />
            <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
          </radialGradient>
          {/* Amber halo filter */}
          <filter id="rg-amber" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* Drop shadow for nodes */}
          <filter id="rg-shadow" x="-30%" y="-30%" width="160%" height="160%">
            <feDropShadow dx="0" dy="1" stdDeviation="3" floodColor="#1A2236" floodOpacity="0.10" />
          </filter>
        </defs>

        {/* Mesh fill */}
        <rect width={W} height={H} fill="url(#rg-mesh)" />

        {/* Centre glow disc */}
        <circle cx={cx} cy={cy} r={230} fill="url(#rg-glow)" />

        {/* ── Outer orbit ring (dashed) ── */}
        <circle
          cx={cx} cy={cy} r={orbitR}
          fill="none"
          stroke="#C8D4E8"
          strokeWidth="1"
          strokeDasharray="5 6"
          opacity="0.55"
        />

        {/* ── Spokes ── */}
        {steps.map((step, i) => {
          const angle = angleOf(i);
          const nx = cx + orbitR * Math.cos(angle);
          const ny = cy + orbitR * Math.sin(angle);
          const isSuspect = step.is_root_suspect || (step.suspicion_score != null && step.suspicion_score > 75);
          const isDown    = step.is_downstream_impact || (step.status === "FAILED" && !isSuspect);
          return (
            <line
              key={`sp-${step.id}`}
              x1={cx} y1={cy} x2={nx} y2={ny}
              stroke={isSuspect ? "#F59E0B" : isDown ? "#EF4444" : "#C8D4E8"}
              strokeWidth={isSuspect ? 1.8 : 1}
              strokeDasharray={isDown ? "4 3" : undefined}
              opacity={isSuspect ? 0.9 : 0.55}
            />
          );
        })}

        {/* ── Sequential orbit connectors ── */}
        {steps.map((_, i) => {
          if (i === steps.length - 1) return null;
          const a1 = angleOf(i), a2 = angleOf(i + 1);
          return (
            <line
              key={`seq-${i}`}
              x1={cx + orbitR * Math.cos(a1)} y1={cy + orbitR * Math.sin(a1)}
              x2={cx + orbitR * Math.cos(a2)} y2={cy + orbitR * Math.sin(a2)}
              stroke="#BCC8DA" strokeWidth="0.7" strokeDasharray="3 5" opacity="0.40"
            />
          );
        })}

        {/* ── Donut centre ── */}
        {(() => {
          return (
            <g>
              {/* Subtle outer halo */}
              <circle cx={cx} cy={cy} r={donutR + donutSW / 2 + 12}
                fill="rgba(255,255,255,0.55)" />
              {/* White backing disc */}
              <circle cx={cx} cy={cy} r={donutR + donutSW / 2 + 3}
                fill="white"
                style={{ filter: "drop-shadow(0 2px 10px rgba(59,130,246,0.12))" }}
              />
              {/* Coloured arc segments */}
              {segs.map((seg, i) => {
                const dash = seg.p * circ;
                const gap  = circ - dash;
                const el = (
                  <circle
                    key={i}
                    cx={cx} cy={cy} r={donutR}
                    fill="none"
                    stroke={seg.c}
                    strokeWidth={donutSW}
                    strokeDasharray={`${dash} ${gap}`}
                    strokeDashoffset={-segOff}
                    strokeLinecap="round"
                    style={{ transformOrigin: `${cx}px ${cy}px`, transform: "rotate(-90deg)" }}
                  />
                );
                segOff += dash;
                return el;
              })}
              {/* Inner white hole */}
              <circle cx={cx} cy={cy} r={donutR - donutSW / 2 - 2} fill="white" />
              {/* Labels */}
              <text x={cx} y={cy - 9} textAnchor="middle"
                fontSize="10" fontWeight="700" fill="#1A2236" fontFamily="Inter,sans-serif">
                {trunc(agentName, 14)}
              </text>
              <text x={cx} y={cy + 5} textAnchor="middle"
                fontSize="8.5" fill="#9BA8BF" fontFamily="Inter,sans-serif">
                {total} nodes
              </text>
              <text x={cx} y={cy + 19} textAnchor="middle"
                fontSize="8.5" fontWeight="700"
                fill={status === "FAILED" ? "#EF4444" : "#22C55E"}
                fontFamily="Inter,sans-serif">
                {status}
              </text>
            </g>
          );
        })()}

        {/* ── Step nodes ── */}
        {steps.map((step, i) => {
          const angle    = angleOf(i);
          const nx       = cx + orbitR * Math.cos(angle);
          const ny       = cy + orbitR * Math.sin(angle);
          const isSuspect = step.is_root_suspect || (step.suspicion_score != null && step.suspicion_score > 75);
          const isDown    = step.is_downstream_impact || (step.status === "FAILED" && !isSuspect);
          const isOk      = !isSuspect && !isDown;
          const isSelected = selectedStepId === step.id;
          const isHovered  = hovered === step.id;

          const R = isSuspect ? R_SUSPECT : R_NORMAL;

          /* Push label outward from orbit edge */
          const labelDist = R + 18;
          const lx = cx + (orbitR + labelDist) * Math.cos(angle);
          const ly = cy + (orbitR + labelDist) * Math.sin(angle);

          /* Anchor label: left-align on left side, right-align on right */
          const anchor = Math.cos(angle) > 0.15 ? "start"
                       : Math.cos(angle) < -0.15 ? "end"
                       : "middle";

          return (
            <g
              key={step.id}
              onClick={() => onSelectStep(step.id)}
              onMouseEnter={() => setHovered(step.id)}
              onMouseLeave={() => setHovered(null)}
              style={{ cursor: "pointer" }}
            >
              {/* Amber glow halos for suspect */}
              {isSuspect && (
                <>
                  <circle cx={nx} cy={ny} r={R + 18}
                    fill="rgba(245,158,11,0.08)" />
                  <circle cx={nx} cy={ny} r={R + 11}
                    fill="rgba(245,158,11,0.15)" />
                  <circle cx={nx} cy={ny} r={R + 5}
                    fill="rgba(245,158,11,0.25)" />
                </>
              )}
              {/* Red glow for downstream */}
              {isDown && (
                <circle cx={nx} cy={ny} r={R + 9}
                  fill="rgba(239,68,68,0.10)" />
              )}

              {/* Main circle */}
              <circle
                cx={nx} cy={ny} r={R}
                fill={
                  isSuspect  ? "#FEF9EC"
                  : isDown   ? "#FEF2F2"
                  : isSelected || isHovered ? "#F0F6FF"
                  : "#FFFFFF"
                }
                stroke={
                  isSuspect  ? "#F59E0B"
                  : isDown   ? "#EF4444"
                  : isSelected ? "#3B82F6"
                  : isHovered  ? "#93C5FD"
                  : "#DDE3EE"
                }
                strokeWidth={isSuspect ? 2 : isSelected ? 2 : 1.5}
                style={{
                  filter: isSuspect ? "drop-shadow(0 0 6px rgba(245,158,11,0.45))"
                        : isDown    ? "drop-shadow(0 0 5px rgba(239,68,68,0.35))"
                        : "drop-shadow(0 1px 3px rgba(26,34,54,0.08))",
                  transition: "all 0.15s ease",
                }}
              />

              {/* Icon inside */}
              {isOk && (
                <path
                  d={`M ${nx - 4.5} ${ny} l 3 3 l 5.5 -5.5`}
                  fill="none" stroke="#22C55E" strokeWidth="1.8"
                  strokeLinecap="round" strokeLinejoin="round"
                />
              )}
              {isDown && (
                <>
                  <line x1={nx-3.5} y1={ny-3.5} x2={nx+3.5} y2={ny+3.5}
                    stroke="#EF4444" strokeWidth="1.8" strokeLinecap="round" />
                  <line x1={nx+3.5} y1={ny-3.5} x2={nx-3.5} y2={ny+3.5}
                    stroke="#EF4444" strokeWidth="1.8" strokeLinecap="round" />
                </>
              )}
              {isSuspect && (
                <text x={nx} y={ny + 5} textAnchor="middle"
                  fontSize="12" fontWeight="800" fill="#D97706"
                  fontFamily="Inter,sans-serif">!</text>
              )}

              {/* ── Label positioned outside the orbit, not overlapping node ── */}
              <text
                x={lx} y={ly - 5}
                textAnchor={anchor}
                fontSize="8.5"
                fontWeight={isSuspect ? "700" : "500"}
                fill={isSuspect ? "#B45309" : isDown ? "#DC2626" : "#6B7A99"}
                fontFamily="Inter,sans-serif"
              >
                {trunc(step.step_name, 13)}
              </text>

              {/* Suspicion score pill — only for suspect */}
              {isSuspect && step.suspicion_score != null && (
                <>
                  <rect
                    x={lx - (anchor === "middle" ? 22 : anchor === "start" ? 0 : 44)}
                    y={ly + 1}
                    width={44} height={13} rx={6.5}
                    fill="#F59E0B"
                  />
                  <text
                    x={lx + (anchor === "middle" ? 0 : anchor === "start" ? 22 : -22)}
                    y={ly + 11}
                    textAnchor="middle"
                    fontSize="7.5" fontWeight="700" fill="white"
                    fontFamily="Inter,sans-serif"
                  >
                    Score {Math.round(step.suspicion_score)}
                  </text>
                </>
              )}

              {/* Downstream "impact" pill */}
              {isDown && (
                <>
                  <rect
                    x={lx - (anchor === "middle" ? 17 : anchor === "start" ? 0 : 34)}
                    y={ly + 1}
                    width={34} height={12} rx={6}
                    fill="#FFF1F2" stroke="#FCA5A5" strokeWidth="0.8"
                  />
                  <text
                    x={lx + (anchor === "middle" ? 0 : anchor === "start" ? 17 : -17)}
                    y={ly + 10}
                    textAnchor="middle"
                    fontSize="7" fontWeight="600" fill="#EF4444"
                    fontFamily="Inter,sans-serif"
                  >
                    impact
                  </text>
                </>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
