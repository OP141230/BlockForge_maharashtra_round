"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Search,
  Activity,
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
  Sparkles,
  ArrowRight,
  Code2,
} from "lucide-react";
import RadialGraph from "@/components/radial-graph";
import DiagnosisPanel from "@/components/diagnosis-panel";
import SpectrumBar from "@/components/spectrum-bar";
import Timeline from "@/components/timeline";
import { fetchRun, fetchDiagnosis } from "@/lib/api";

function InvestigationContent() {
  const searchParams = useSearchParams();
  const runIdParam = searchParams.get("run_id") || "run_travel_paris_fail";

  const [run, setRun] = useState<any>(null);
  const [diagnosis, setDiagnosis] = useState<any>(null);
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"graph" | "timeline">("graph");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchRun(runIdParam).catch(() => null),
      fetchDiagnosis(runIdParam).catch(() => null),
    ]).then(([runData, diagData]) => {
      setRun(runData);
      setDiagnosis(diagData);
      if (runData?.steps?.length > 0) {
        // Auto-select suspect step or first step
        const suspect = runData.steps.find((s: any) => s.is_root_suspect) || runData.steps[0];
        setSelectedStepId(suspect.id);
      }
      setLoading(false);
    });
  }, [runIdParam]);

  if (loading || !run) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-muted text-sm gap-2">
        <Activity className="w-5 h-5 animate-spin text-primary" />
        <span>Loading Flight Recorder Trace...</span>
      </div>
    );
  }

  const selectedStep = run.steps.find((s: any) => s.id === selectedStepId) || run.steps[0];

  return (
    <div className="flex flex-col h-full overflow-hidden bg-bg">
      {/* Top Header Bar: Clean human-readable titles, NO raw hashes in main title */}
      <div className="px-8 py-4 bg-white border-b border-panel-border flex items-center justify-between shrink-0 shadow-sm">
        <div className="flex items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-black text-text-primary tracking-tight">
                {run.agent_name} Execution
              </h2>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                  run.status === "SUCCESS"
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-rose-100 text-rose-700"
                }`}
              >
                {run.status}
              </span>
            </div>
            <p className="text-xs text-text-muted mt-0.5">{run.scenario}</p>
          </div>
        </div>

        {/* View mode toggle */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-semibold">
            <button
              onClick={() => setViewMode("graph")}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                viewMode === "graph"
                  ? "bg-white text-primary shadow-sm"
                  : "text-text-muted hover:text-text-primary"
              }`}
            >
              Radial Graph
            </button>
            <button
              onClick={() => setViewMode("timeline")}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                viewMode === "timeline"
                  ? "bg-white text-primary shadow-sm"
                  : "text-text-muted hover:text-text-primary"
              }`}
            >
              Linear Timeline
            </button>
          </div>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 p-6 overflow-y-auto flex gap-6 relative">
        {/* Left: Interactive Canvas */}
        <div className="flex-1 flex flex-col gap-6">
          {viewMode === "graph" ? (
            <RadialGraph
              agentName={run.agent_name}
              scenario={run.scenario}
              status={run.status}
              durationMs={run.total_duration_ms}
              steps={run.steps}
              selectedStepId={selectedStepId}
              onSelectStep={(id) => setSelectedStepId(id)}
            />
          ) : (
            <div className="p-5 rounded-2xl glass-card border border-panel-border">
              <Timeline
                steps={run.steps}
                selectedStepId={selectedStepId}
                onSelectStep={(id) => setSelectedStepId(id)}
              />
            </div>
          )}

          {/* Selected Step Payload Inspector */}
          {selectedStep && (
            <div className="p-5 rounded-2xl glass-card border border-panel-border space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-primary" />
                  <h4 className="font-bold text-xs text-text-primary">
                    Step {selectedStep.step_index}: {selectedStep.step_name} ({selectedStep.tool_name})
                  </h4>
                  {selectedStep.is_root_suspect && (
                    <span className="text-[9px] font-bold font-mono bg-amber-500 text-white px-1.5 py-0.2 rounded">
                      ROOT SUSPECT
                    </span>
                  )}
                </div>
                <span className="text-[11px] font-mono text-text-muted">
                  Duration: {selectedStep.duration_ms.toFixed(0)}ms
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                <div>
                  <span className="text-[10px] font-bold text-text-muted uppercase">Input Payload:</span>
                  <pre className="mt-1 p-3 rounded-xl bg-slate-900 text-emerald-400 overflow-x-auto max-h-48 text-[11px]">
                    {JSON.stringify(selectedStep.input_data, null, 2)}
                  </pre>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-text-muted uppercase">Output State:</span>
                  <pre className="mt-1 p-3 rounded-xl bg-slate-900 text-cyan-300 overflow-x-auto max-h-48 text-[11px]">
                    {JSON.stringify(selectedStep.output_data, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right: Floating Glassmorphism Diagnosis Panel */}
        {diagnosis && (
          <div className="sticky top-0 self-start">
            <DiagnosisPanel
              runId={run.id}
              suspectStepName={diagnosis.suspect_step_name}
              suspectStepId={diagnosis.suspect_step_id}
              suspicionScore={diagnosis.suspicion_score}
              confidenceLabel={diagnosis.confidence_label}
              explanationText={diagnosis.explanation_text}
              signals={diagnosis.signals}
              evidenceItems={diagnosis.evidence_items}
            />
          </div>
        )}
      </div>

      {/* Bottom Spectrum Legend Bar */}
      <SpectrumBar />
    </div>
  );
}

export default function InvestigationPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-text-muted">Loading investigation...</div>}>
      <InvestigationContent />
    </Suspense>
  );
}
