"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Bot,
  Zap,
  Clock,
  ArrowRight,
} from "lucide-react";

interface NodeData {
  id: string;
  step_index?: number;
  step_name: string;
  tool_name: string;
  status: string;
  duration_ms: number;
  suspicion_score?: number;
  is_root_suspect?: boolean;
  is_downstream_impact?: boolean;
  side_effect_flag?: boolean;
  error_text?: string;
  position?: { x: number; y: number };
}

interface RadialGraphProps {
  agentName: string;
  scenario: string;
  status: string;
  durationMs: number;
  steps: NodeData[];
  selectedStepId: string | null;
  onSelectStep: (stepId: string) => void;
}

export default function RadialGraph({
  agentName,
  scenario,
  status,
  durationMs,
  steps,
  selectedStepId,
  onSelectStep,
}: RadialGraphProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const centerX = 440;
  const centerY = 280;
  const radius = 190;
  const total = steps.length;

  return (
    <div className="relative w-full h-[580px] rounded-2xl glass-panel overflow-hidden border border-panel-border/80 flex items-center justify-center select-none shadow-sm">
      {/* Background Grid Pattern */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-40">
        <defs>
          <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
            <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#CBD5E1" strokeWidth="0.75" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        {/* Concentric Orbit Rings */}
        <circle cx={centerX} cy={centerY} r={radius} fill="none" stroke="#E2E8F0" strokeWidth="1.5" strokeDasharray="6 6" />
        <circle cx={centerX} cy={centerY} r={radius + 45} fill="none" stroke="#F1F5F9" strokeWidth="1" />
      </svg>

      {/* SVG Connecting Edges */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
        {steps.map((step, idx) => {
          const angle = (2 * Math.PI * idx) / Math.max(total, 1) - Math.PI / 2;
          const nx = centerX + radius * Math.cos(angle);
          const ny = centerY + radius * Math.sin(angle);

          const isSuspect = step.is_root_suspect || (step.suspicion_score && step.suspicion_score > 75);
          const isDownstream = step.is_downstream_impact || (step.status === "FAILED" && !isSuspect);
          const isSelected = selectedStepId === step.id;

          // Sequential connecting curve
          const nextIdx = (idx + 1) % total;
          const nextAngle = (2 * Math.PI * nextIdx) / Math.max(total, 1) - Math.PI / 2;
          const nnx = centerX + radius * Math.cos(nextAngle);
          const nny = centerY + radius * Math.sin(nextAngle);

          return (
            <g key={`edges-${step.id}`}>
              {/* Radial spoke from center */}
              <line
                x1={centerX}
                y1={centerY}
                x2={nx}
                y2={ny}
                stroke={isSuspect ? "#F59E0B" : isDownstream ? "#EF4444" : "#CBD5E1"}
                strokeWidth={isSuspect ? 3 : isSelected ? 2.5 : 1.5}
                strokeDasharray={isDownstream ? "4 4" : "none"}
                className={isSuspect ? "animate-pulse" : ""}
                opacity={isSelected ? 1 : 0.75}
              />
              {/* Orbit step-to-step connecting line */}
              {idx < total - 1 && (
                <line
                  x1={nx}
                  y1={ny}
                  x2={nnx}
                  y2={nny}
                  stroke="#94A3B8"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                  opacity="0.6"
                />
              )}
            </g>
          );
        })}
      </svg>

      {/* Center Root Agent Node */}
      <div
        className="absolute z-20 flex flex-col items-center justify-center w-36 h-36 rounded-3xl glass-card border-2 border-primary/40 shadow-xl shadow-primary/10 transition-transform duration-300 hover:scale-105"
        style={{ left: centerX - 72, top: centerY - 72 }}
      >
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-primary to-intel text-white flex items-center justify-center shadow-md mb-1.5">
          <Bot className="w-6 h-6" />
        </div>
        <span className="font-bold text-xs text-text-primary text-center px-2 line-clamp-1">
          {agentName}
        </span>
        <span className="text-[10px] text-text-muted mt-0.5">{total} Nodes Recorded</span>
        <span
          className={`mt-1 text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
            status === "SUCCESS"
              ? "bg-emerald-100 text-emerald-700"
              : "bg-rose-100 text-rose-700"
          }`}
        >
          {status}
        </span>
      </div>

      {/* Orbiting Step Nodes */}
      {steps.map((step, idx) => {
        const angle = (2 * Math.PI * idx) / Math.max(total, 1) - Math.PI / 2;
        const nx = centerX + radius * Math.cos(angle);
        const ny = centerY + radius * Math.sin(angle);

        const isSuspect = step.is_root_suspect || (step.suspicion_score && step.suspicion_score > 75);
        const isDownstream = step.is_downstream_impact || (step.status === "FAILED" && !isSuspect);
        const isSelected = selectedStepId === step.id;

        return (
          <div
            key={step.id}
            onClick={() => onSelectStep(step.id)}
            onMouseEnter={() => setHoveredNode(step.id)}
            onMouseLeave={() => setHoveredNode(null)}
            style={{ left: nx - 55, top: ny - 42 }}
            className={`absolute z-20 w-28 p-2.5 rounded-2xl cursor-pointer transition-all duration-300 flex flex-col items-center text-center ${
              isSuspect
                ? "bg-amber-50/95 border-2 border-warning shadow-glow-amber pulse-suspect scale-105"
                : isDownstream
                ? "bg-rose-50/90 border-2 border-danger shadow-glow-red"
                : isSelected
                ? "bg-white border-2 border-primary shadow-lg scale-105"
                : "bg-white/90 border border-slate-200 hover:border-slate-400 hover:shadow-md"
            }`}
          >
            {/* Step Icon badge */}
            <div className="mb-1">
              {isSuspect ? (
                <div className="w-6 h-6 rounded-full bg-amber-500 text-white flex items-center justify-center shadow">
                  <AlertTriangle className="w-3.5 h-3.5" />
                </div>
              ) : step.status === "FAILED" ? (
                <div className="w-6 h-6 rounded-full bg-rose-500 text-white flex items-center justify-center shadow">
                  <XCircle className="w-3.5 h-3.5" />
                </div>
              ) : (
                <div className="w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center shadow">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                </div>
              )}
            </div>

            <span className="font-bold text-[11px] text-text-primary leading-tight line-clamp-1">
              {step.step_name}
            </span>
            <span className="text-[9px] text-text-muted font-mono mt-0.5">
              {step.tool_name}
            </span>

            {/* Suspicion badge for suspect node */}
            {isSuspect && (
              <span className="mt-1 text-[9px] font-mono font-bold bg-amber-500 text-white px-1.5 py-0.2 rounded shadow-sm">
                Score {step.suspicion_score || 91.2}
              </span>
            )}
            {isDownstream && (
              <span className="mt-1 text-[8px] font-mono text-rose-600 bg-rose-100 px-1 py-0.2 rounded">
                Impacted
              </span>
            )}
          </div>
        );
      })}

      {/* Canvas Controls overlay */}
      <div className="absolute top-4 left-4 z-20 flex items-center gap-2 text-xs font-medium text-text-muted bg-white/80 px-3 py-1.5 rounded-xl border border-panel-border shadow-sm">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span>Radial Graph Canvas</span>
        <span className="text-slate-300">|</span>
        <span className="text-[11px] font-mono">{scenario}</span>
      </div>
    </div>
  );
}
