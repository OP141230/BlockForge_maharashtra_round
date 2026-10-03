"use client";

import React from "react";
import { CheckCircle2, XCircle, AlertTriangle, Clock, ShieldCheck } from "lucide-react";

interface StepItem {
  id: string;
  step_index: number;
  step_name: string;
  tool_name: string;
  duration_ms: number;
  status: string;
  error_text?: string;
  suspicion_score?: number;
  is_root_suspect?: boolean;
  is_downstream_impact?: boolean;
  side_effect_flag?: boolean;
}

interface TimelineProps {
  steps: StepItem[];
  selectedStepId: string | null;
  onSelectStep: (id: string) => void;
}

export default function Timeline({ steps, selectedStepId, onSelectStep }: TimelineProps) {
  return (
    <div className="space-y-1.5">
      {steps.map((step) => {
        const isSuspect    = step.is_root_suspect || (step.suspicion_score != null && step.suspicion_score > 75);
        const isDownstream = step.is_downstream_impact || (step.status === "FAILED" && !isSuspect);
        const isSelected   = selectedStepId === step.id;

        let bg      = isSelected ? "#F0F4FA" : "#FFFFFF";
        let border  = isSelected ? "#3B82F6" : "#DDE3EE";
        if (isSuspect)    { bg = "#FFFBEB"; border = "#F59E0B"; }
        if (isDownstream) { bg = "#FFF1F2"; border = "#FCA5A5"; }

        return (
          <div
            key={step.id}
            onClick={() => onSelectStep(step.id)}
            className="flex items-center justify-between px-4 py-3 rounded-xl cursor-pointer transition-all"
            style={{
              background: bg,
              border: `1px solid ${border}`,
              boxShadow: isSuspect ? "0 0 0 2px rgba(245,158,11,0.15)" : "none",
            }}
          >
            <div className="flex items-center gap-3">
              {/* Step index bubble */}
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold font-mono shrink-0"
                style={{
                  background: isSuspect ? "#FEF3C7" : isDownstream ? "#FFF1F2" : "#F0F4FA",
                  color: isSuspect ? "#B45309" : isDownstream ? "#DC2626" : "#6B7A99",
                }}
              >
                {step.step_index}
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold" style={{ color: "#1A2236" }}>
                    {step.step_name}
                  </span>
                  <span
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                    style={{ background: "#F0F4FA", color: "#6B7A99" }}
                  >
                    {step.tool_name}
                  </span>
                  {step.side_effect_flag && (
                    <span
                      className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded"
                      style={{ background: "#F3EEFF", color: "#7C5CFF" }}
                    >
                      side effect
                    </span>
                  )}
                </div>
                {step.error_text && (
                  <p className="text-[11px] font-mono mt-0.5" style={{ color: "#EF4444" }}>
                    {step.error_text}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              {isSuspect && (
                <span
                  className="text-[10px] font-bold font-mono px-2 py-0.5 rounded-full"
                  style={{ background: "#FEF3C7", color: "#B45309" }}
                >
                  Score {step.suspicion_score?.toFixed(0) || 91}
                </span>
              )}
              <span className="flex items-center gap-1 text-[11px] font-mono" style={{ color: "#9BA8BF" }}>
                <Clock className="w-3 h-3" />
                {step.duration_ms?.toFixed(0)}ms
              </span>
              <span
                className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase"
                style={
                  step.status === "SUCCESS"
                    ? { background: "#ECFDF5", color: "#16A34A" }
                    : { background: "#FFF1F2", color: "#DC2626" }
                }
              >
                {step.status === "SUCCESS"
                  ? <CheckCircle2 className="w-3 h-3" />
                  : <XCircle className="w-3 h-3" />}
                {step.status}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
