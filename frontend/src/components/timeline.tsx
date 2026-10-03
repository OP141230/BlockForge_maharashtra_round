"use client";

import React from "react";
import { CheckCircle2, AlertTriangle, XCircle, Clock, ShieldCheck, ArrowRight } from "lucide-react";

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
  input_data?: any;
  output_data?: any;
}

interface TimelineProps {
  steps: StepItem[];
  selectedStepId: string | null;
  onSelectStep: (stepId: string) => void;
}

export default function Timeline({ steps, selectedStepId, onSelectStep }: TimelineProps) {
  return (
    <div className="w-full space-y-2">
      {steps.map((step) => {
        const isSuspect = step.is_root_suspect || (step.suspicion_score && step.suspicion_score > 75);
        const isDownstream = step.is_downstream_impact || (step.status === "FAILED" && !isSuspect);
        const isSelected = selectedStepId === step.id;

        return (
          <div
            key={step.id}
            onClick={() => onSelectStep(step.id)}
            className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
              isSelected
                ? "bg-blue-50/80 border-primary shadow-sm"
                : isSuspect
                ? "bg-amber-50/70 border-amber-300 hover:bg-amber-50"
                : isDownstream
                ? "bg-rose-50/70 border-rose-200 hover:bg-rose-50"
                : "bg-white/80 border-slate-200/80 hover:bg-slate-50"
            }`}
          >
            <div className="flex items-center gap-3">
              <span className="w-6 h-6 rounded-full bg-slate-100 text-slate-600 font-mono text-xs flex items-center justify-center font-bold">
                {step.step_index}
              </span>

              <div>
                <div className="flex items-center gap-2">
                  <h4 className="font-bold text-xs text-text-primary">{step.step_name}</h4>
                  <span className="text-[10px] font-mono text-text-muted px-1.5 py-0.2 rounded bg-slate-100">
                    {step.tool_name}
                  </span>
                  {step.side_effect_flag && (
                    <span className="text-[9px] uppercase font-bold text-purple-700 bg-purple-100 px-1.5 py-0.2 rounded">
                      Side Effect
                    </span>
                  )}
                </div>
                {step.error_text && (
                  <p className="text-[11px] text-rose-600 font-mono mt-0.5">{step.error_text}</p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3">
              {isSuspect && (
                <span className="text-[10px] font-mono font-bold text-amber-800 bg-amber-200/80 px-2 py-0.5 rounded-full">
                  Suspect Score: {step.suspicion_score || 91.2}
                </span>
              )}
              <div className="flex items-center gap-1 text-[11px] text-text-muted font-mono">
                <Clock className="w-3 h-3" />
                <span>{step.duration_ms.toFixed(0)}ms</span>
              </div>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                  step.status === "SUCCESS"
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-rose-100 text-rose-700"
                }`}
              >
                {step.status}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
