"use client";

import React from "react";
import { CheckCircle2, ShieldAlert, ArrowRight, Sparkles } from "lucide-react";

interface DiffProps {
  diffSummary: Record<string, any>;
  suppressedSideEffects: Array<{ step_id: string; tool_name: string; notice: string }>;
  replayStatus: string;
}

export default function DiffViewer({
  diffSummary,
  suppressedSideEffects,
  replayStatus,
}: DiffProps) {
  const diffEntries = Object.entries(diffSummary);

  return (
    <div className="space-y-4">
      {/* Side-Effect Suppression Banner */}
      {suppressedSideEffects.length > 0 && (
        <div className="p-4 rounded-xl bg-purple-50 border border-purple-200 flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-purple-600 text-white flex items-center justify-center shrink-0">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h4 className="font-bold text-xs text-purple-950 uppercase tracking-wider">
              Side-Effect Protection Active ({suppressedSideEffects.length} Actions Suppressed)
            </h4>
            <div className="mt-1 space-y-1">
              {suppressedSideEffects.map((item, idx) => (
                <p key={idx} className="text-xs text-purple-800 font-mono">
                  {item.notice}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Structured Field Diffs */}
      <div className="space-y-3">
        <h4 className="font-bold text-xs text-text-primary uppercase tracking-wider">
          Step-by-Step State Intervention Diff
        </h4>

        {diffEntries.map(([stepId, diffItem]: [string, any]) => {
          const changedFields = Object.entries(diffItem.changed_fields || {});
          return (
            <div
              key={stepId}
              className="p-4 rounded-xl bg-white border border-slate-200/80 shadow-sm"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-xs text-text-primary">
                    {diffItem.step_name}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                    {diffItem.tool_name}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[10px] font-bold">
                  <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-700">
                    {diffItem.original_status}
                  </span>
                  <ArrowRight className="w-3 h-3 text-slate-400" />
                  <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">
                    {diffItem.replayed_status}
                  </span>
                </div>
              </div>

              {/* Changed attributes */}
              {changedFields.length > 0 ? (
                <div className="mt-3 space-y-2 font-mono text-xs">
                  {changedFields.map(([field, val]: [string, any]) => (
                    <div
                      key={field}
                      className="p-2 rounded-lg bg-slate-50 border border-slate-200/60 flex items-center justify-between"
                    >
                      <span className="text-slate-600 font-semibold">{field}:</span>
                      <div className="flex items-center gap-2 text-[11px]">
                        <span className="text-rose-600 bg-rose-50 px-2 py-0.5 rounded line-through">
                          {typeof val.before === "object" ? JSON.stringify(val.before) : String(val.before)}
                        </span>
                        <ArrowRight className="w-3 h-3 text-slate-400" />
                        <span className="text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded">
                          {typeof val.after === "object" ? JSON.stringify(val.after) : String(val.after)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic mt-1">
                  Outputs matched nominal upstream execution.
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
