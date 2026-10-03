"use client";

import React from "react";
import { ShieldCheck, ArrowRight, CheckCircle2 } from "lucide-react";

interface DiffProps {
  diffSummary: Record<string, any>;
  suppressedSideEffects: Array<{ step_id: string; tool_name: string; notice: string }>;
  replayStatus: string;
}

export default function DiffViewer({ diffSummary, suppressedSideEffects, replayStatus }: DiffProps) {
  const entries = Object.entries(diffSummary);

  return (
    <div className="space-y-4">
      {/* Side-effect suppression banner */}
      {suppressedSideEffects.length > 0 && (
        <div
          className="rounded-xl p-4 flex items-start gap-3"
          style={{ background: "#F5F3FF", border: "1px solid #DDD6FE" }}
        >
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: "#7C5CFF" }}
          >
            <ShieldCheck className="w-4 h-4 text-white" />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider" style={{ color: "#4C1D95" }}>
              Side-Effect Protection Active — {suppressedSideEffects.length} action(s) suppressed
            </h4>
            <div className="mt-1.5 space-y-1">
              {suppressedSideEffects.map((item, i) => (
                <p key={i} className="text-xs font-mono" style={{ color: "#6D28D9" }}>
                  {item.notice}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Per-step diffs */}
      <div className="space-y-3">
        <p className="text-xs font-bold uppercase tracking-wider" style={{ color: "#6B7A99" }}>
          Step-by-Step State Diff
        </p>
        {entries.map(([stepId, item]: [string, any]) => {
          const changed = Object.entries(item.changed_fields || {});
          return (
            <div
              key={stepId}
              className="rounded-xl p-4"
              style={{ background: "#FFFFFF", border: "1px solid #DDE3EE", boxShadow: "0 1px 6px rgba(26,34,54,0.05)" }}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold" style={{ color: "#1A2236" }}>
                    {item.step_name}
                  </span>
                  <span
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                    style={{ background: "#F0F4FA", color: "#6B7A99" }}
                  >
                    {item.tool_name}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[10px] font-bold">
                  <span
                    className="px-2 py-0.5 rounded-full"
                    style={{ background: "#FFF1F2", color: "#DC2626" }}
                  >
                    {item.original_status}
                  </span>
                  <ArrowRight className="w-3 h-3" style={{ color: "#9BA8BF" }} />
                  <span
                    className="px-2 py-0.5 rounded-full"
                    style={
                      item.replayed_status === "SUCCESS"
                        ? { background: "#ECFDF5", color: "#16A34A" }
                        : { background: "#FFF1F2", color: "#DC2626" }
                    }
                  >
                    {item.replayed_status}
                  </span>
                </div>
              </div>

              {changed.length > 0 ? (
                <div className="space-y-2 font-mono text-xs">
                  {changed.map(([field, val]: [string, any]) => (
                    <div
                      key={field}
                      className="flex items-center justify-between px-3 py-2 rounded-lg"
                      style={{ background: "#F8FAFD", border: "1px solid #EEF2F7" }}
                    >
                      <span className="font-semibold" style={{ color: "#6B7A99" }}>{field}</span>
                      <div className="flex items-center gap-2 text-[11px]">
                        <span
                          className="px-2 py-0.5 rounded line-through"
                          style={{ background: "#FFF1F2", color: "#EF4444" }}
                        >
                          {typeof val.before === "object"
                            ? JSON.stringify(val.before)
                            : String(val.before)}
                        </span>
                        <ArrowRight className="w-3 h-3" style={{ color: "#9BA8BF" }} />
                        <span
                          className="px-2 py-0.5 rounded font-bold"
                          style={{ background: "#ECFDF5", color: "#16A34A" }}
                        >
                          {typeof val.after === "object"
                            ? JSON.stringify(val.after)
                            : String(val.after)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs italic" style={{ color: "#9BA8BF" }}>
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
