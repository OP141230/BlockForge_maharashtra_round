"use client";

import React from "react";
import Link from "next/link";
import {
  AlertTriangle,
  RotateCcw,
  Sparkles,
  ShieldAlert,
  TrendingUp,
  Cpu,
  GitFork,
  History,
  Info,
} from "lucide-react";

interface DiagnosisSignals {
  rule_match: number;
  anomaly_signal: number;
  learned_ranker: number;
  dependency_impact: number;
  historical_evidence: number;
}

interface DiagnosisProps {
  runId: string;
  suspectStepName: string;
  suspectStepId: string;
  suspicionScore: number;
  confidenceLabel: string;
  explanationText: string;
  signals: DiagnosisSignals;
  evidenceItems?: any;
}

export default function DiagnosisPanel({
  runId,
  suspectStepName,
  suspectStepId,
  suspicionScore,
  confidenceLabel,
  explanationText,
  signals,
  evidenceItems,
}: DiagnosisProps) {
  return (
    <div className="w-96 rounded-2xl glass-card border border-panel-border/90 p-5 shadow-lg flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-intel/10 text-intel flex items-center justify-center">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-text-primary">Hybrid Diagnosis</h3>
            <p className="text-[10px] text-text-muted">Multi-Signal Root Cause Analysis</p>
          </div>
        </div>
        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
          {confidenceLabel} Confidence
        </span>
      </div>

      {/* Primary Suspect Card */}
      <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-300/60 flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-amber-500 text-white flex items-center justify-center shrink-0 shadow-sm mt-0.5">
          <AlertTriangle className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline justify-between">
            <span className="text-[11px] uppercase font-semibold text-amber-800">Primary Suspect</span>
            <span className="text-base font-black text-amber-700 font-mono">{suspicionScore}</span>
          </div>
          <p className="font-bold text-sm text-text-primary truncate">{suspectStepName}</p>
          <p className="text-[10px] text-text-muted mt-0.5">
            Suspicion Score is a heuristic ranking score, not a probability.
          </p>
        </div>
      </div>

      {/* 5-Signal Weight Spectrum */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold text-text-muted">
          <span>Signal Contributions</span>
          <span className="text-[10px] font-mono">Calibrated Weights</span>
        </div>

        {/* 1. Rule Match (30%) */}
        <div className="space-y-1">
          <div className="flex justify-between text-[11px]">
            <span className="flex items-center gap-1.5 text-slate-700">
              <ShieldAlert className="w-3 h-3 text-amber-500" />
              Rule Match (30%)
            </span>
            <span className="font-mono font-bold text-amber-600">{signals.rule_match.toFixed(2)}</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-500 rounded-full"
              style={{ width: `${signals.rule_match * 100}%` }}
            />
          </div>
        </div>

        {/* 2. Anomaly Signal (20%) */}
        <div className="space-y-1">
          <div className="flex justify-between text-[11px]">
            <span className="flex items-center gap-1.5 text-slate-700">
              <TrendingUp className="w-3 h-3 text-blue-500" />
              Anomaly Signal (20%)
            </span>
            <span className="font-mono font-bold text-blue-600">{signals.anomaly_signal.toFixed(2)}</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full"
              style={{ width: `${signals.anomaly_signal * 100}%` }}
            />
          </div>
        </div>

        {/* 3. Learned Ranker (20%) */}
        <div className="space-y-1">
          <div className="flex justify-between text-[11px]">
            <span className="flex items-center gap-1.5 text-slate-700">
              <Cpu className="w-3 h-3 text-purple-500" />
              Learned Ranker (20%)
            </span>
            <span className="font-mono font-bold text-purple-600">{signals.learned_ranker.toFixed(2)}</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-purple-500 rounded-full"
              style={{ width: `${signals.learned_ranker * 100}%` }}
            />
          </div>
        </div>

        {/* 4. Dependency Impact (15%) */}
        <div className="space-y-1">
          <div className="flex justify-between text-[11px]">
            <span className="flex items-center gap-1.5 text-slate-700">
              <GitFork className="w-3 h-3 text-rose-500" />
              Dependency Impact (15%)
            </span>
            <span className="font-mono font-bold text-rose-600">{signals.dependency_impact.toFixed(2)}</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-rose-500 rounded-full"
              style={{ width: `${signals.dependency_impact * 100}%` }}
            />
          </div>
        </div>

        {/* 5. Historical Evidence (15%) */}
        <div className="space-y-1">
          <div className="flex justify-between text-[11px]">
            <span className="flex items-center gap-1.5 text-slate-700">
              <History className="w-3 h-3 text-emerald-500" />
              Historical Evidence (15%)
            </span>
            <span className="font-mono font-bold text-emerald-600">{signals.historical_evidence.toFixed(2)}</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full"
              style={{ width: `${signals.historical_evidence * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Transparent Explanation Text */}
      <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-[11px] leading-relaxed text-text-primary">
        <div className="flex items-center gap-1.5 font-semibold text-slate-600 mb-1">
          <Info className="w-3.5 h-3.5" />
          <span>Diagnostic Evidence</span>
        </div>
        <p className="text-slate-700">{explanationText}</p>
      </div>

      {/* Action Button: Send to Replay Lab */}
      <Link
        href={`/replay?run_id=${runId}&step_id=${suspectStepId}`}
        className="w-full py-2.5 px-4 rounded-xl bg-primary hover:bg-blue-600 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-md shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
      >
        <RotateCcw className="w-4 h-4" />
        <span>Open in Replay Lab</span>
      </Link>
    </div>
  );
}
