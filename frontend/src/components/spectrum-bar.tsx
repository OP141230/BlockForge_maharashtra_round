"use client";

import React from "react";
import { CheckCircle2, AlertTriangle, XCircle, ShieldAlert, Cpu } from "lucide-react";

export default function SpectrumBar() {
  return (
    <div className="w-full bg-white/90 backdrop-blur-md border-t border-panel-border px-6 py-2.5 flex items-center justify-between text-xs text-text-muted select-none">
      <div className="flex items-center gap-6">
        <span className="font-semibold text-text-primary text-[11px] uppercase tracking-wider">
          Node Legend:
        </span>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-emerald-500 shadow-sm" />
          <span>Nominal Execution</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-amber-500 shadow-sm animate-pulse" />
          <span className="font-semibold text-amber-700">Primary Suspect (Score 91)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-rose-500 shadow-sm" />
          <span className="text-rose-600">Downstream Impact Victim</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-purple-500 shadow-sm" />
          <span className="text-purple-700">Side-Effect Protected</span>
        </div>
      </div>

      <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
        <span>Offline Mode</span>
        <span>•</span>
        <span>No API Key Required</span>
        <span>•</span>
        <span className="text-emerald-600 font-bold">100% Deterministic + ML</span>
      </div>
    </div>
  );
}
