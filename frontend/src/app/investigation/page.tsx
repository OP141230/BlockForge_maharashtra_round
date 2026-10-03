"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Search,
  Activity,
  Code2,
  LayoutList,
  Waypoints,
} from "lucide-react";
import RadialGraph from "@/components/radial-graph";
import DiagnosisPanel from "@/components/diagnosis-panel";
import SpectrumBar from "@/components/spectrum-bar";
import Timeline from "@/components/timeline";
import { fetchRun, fetchDiagnosis } from "@/lib/api";

function InvestigationContent() {
  const searchParams = useSearchParams();
  const runIdParam   = searchParams.get("run_id") || "run_travel_paris_fail";

  const [run,          setRun]          = useState<any>(null);
  const [diagnosis,    setDiagnosis]    = useState<any>(null);
  const [selectedId,   setSelectedId]   = useState<string | null>(null);
  const [viewMode,     setViewMode]     = useState<"graph" | "timeline">("graph");
  const [loading,      setLoading]      = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchRun(runIdParam).catch(() => null),
      fetchDiagnosis(runIdParam).catch(() => null),
    ]).then(([runData, diagData]) => {
      setRun(runData);
      setDiagnosis(diagData);
      if (runData?.steps?.length) {
        const suspect = runData.steps.find((s: any) => s.is_root_suspect) || runData.steps[0];
        setSelectedId(suspect.id);
      }
      setLoading(false);
    });
  }, [runIdParam]);

  if (loading || !run) {
    return (
      <div className="flex-1 flex items-center justify-center gap-3" style={{ color: "#6B7A99" }}>
        <Activity className="w-5 h-5 animate-spin" style={{ color: "#3B82F6" }} />
        <span className="text-sm">Loading flight trace…</span>
      </div>
    );
  }

  const selectedStep = run.steps.find((s: any) => s.id === selectedId) || run.steps[0];

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ background: "#EEF2F7" }}>

      {/* ── Top bar ── */}
      <div
        className="px-7 py-3.5 flex items-center justify-between shrink-0"
        style={{
          background: "#FFFFFF",
          borderBottom: "1px solid #DDE3EE",
          boxShadow: "0 1px 6px rgba(26,34,54,0.05)",
        }}
      >
        <div className="flex items-center gap-3">
          <Search className="w-4 h-4" style={{ color: "#3B82F6" }} />
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-black" style={{ color: "#1A2236" }}>
                {run.agent_name} Execution
              </h2>
              <span
                className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase"
                style={
                  run.status === "FAILED"
                    ? { background: "#FFF1F2", color: "#DC2626" }
                    : { background: "#ECFDF5", color: "#16A34A" }
                }
              >
                {run.status}
              </span>
            </div>
            <p className="text-xs mt-0.5" style={{ color: "#9BA8BF" }}>
              {run.scenario}
            </p>
          </div>
        </div>

        {/* View toggle */}
        <div
          className="flex items-center p-1 gap-1 rounded-xl"
          style={{ background: "#F0F4FA", border: "1px solid #DDE3EE" }}
        >
          <button
            onClick={() => setViewMode("graph")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
            style={
              viewMode === "graph"
                ? { background: "#FFFFFF", color: "#3B82F6", boxShadow: "0 1px 4px rgba(26,34,54,0.07)" }
                : { color: "#6B7A99" }
            }
          >
            <Waypoints className="w-3.5 h-3.5" />
            Radial Graph
          </button>
          <button
            onClick={() => setViewMode("timeline")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
            style={
              viewMode === "timeline"
                ? { background: "#FFFFFF", color: "#3B82F6", boxShadow: "0 1px 4px rgba(26,34,54,0.07)" }
                : { color: "#6B7A99" }
            }
          >
            <LayoutList className="w-3.5 h-3.5" />
            Timeline
          </button>
        </div>
      </div>

      {/* ── Main canvas ── */}
      <div className="flex-1 relative overflow-hidden p-5 flex gap-5">

        {/* Left: graph / timeline */}
        <div className="flex-1 flex flex-col gap-4 min-w-0 overflow-y-auto">
          {viewMode === "graph" ? (
            <RadialGraph
              agentName={run.agent_name}
              scenario={run.scenario}
              status={run.status}
              durationMs={run.total_duration_ms}
              steps={run.steps}
              selectedStepId={selectedId}
              onSelectStep={setSelectedId}
            />
          ) : (
            <div
              className="rounded-2xl p-5"
              style={{
                background: "#FFFFFF",
                border: "1px solid #DDE3EE",
                boxShadow: "0 2px 10px rgba(26,34,54,0.05)",
              }}
            >
              <Timeline
                steps={run.steps}
                selectedStepId={selectedId}
                onSelectStep={setSelectedId}
              />
            </div>
          )}

          {/* Event inspector */}
          {selectedStep && (
            <div
              className="rounded-2xl p-5 space-y-3"
              style={{
                background: "#FFFFFF",
                border: "1px solid #DDE3EE",
                boxShadow: "0 2px 10px rgba(26,34,54,0.05)",
              }}
            >
              <div
                className="flex items-center justify-between pb-3"
                style={{ borderBottom: "1px solid #EEF2F7" }}
              >
                <div className="flex items-center gap-2">
                  <Code2 className="w-4 h-4" style={{ color: "#3B82F6" }} />
                  <h4 className="text-xs font-bold" style={{ color: "#1A2236" }}>
                    Step {selectedStep.step_index}: {selectedStep.step_name}
                    <span className="font-mono ml-1" style={{ color: "#9BA8BF" }}>
                      ({selectedStep.tool_name})
                    </span>
                  </h4>
                  {selectedStep.is_root_suspect && (
                    <span
                      className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded"
                      style={{ background: "#F59E0B", color: "#FFFFFF" }}
                    >
                      ROOT SUSPECT
                    </span>
                  )}
                </div>
                <span className="text-[11px] font-mono" style={{ color: "#9BA8BF" }}>
                  {selectedStep.duration_ms?.toFixed(0)}ms
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div>
                  <p
                    className="text-[10px] font-bold uppercase mb-1.5"
                    style={{ color: "#9BA8BF" }}
                  >
                    Input Payload
                  </p>
                  <pre
                    className="p-3 rounded-xl overflow-x-auto max-h-44 text-[11px] leading-relaxed"
                    style={{ background: "#0F172A", color: "#86EFAC" }}
                  >
                    {JSON.stringify(selectedStep.input_data, null, 2)}
                  </pre>
                </div>
                <div>
                  <p
                    className="text-[10px] font-bold uppercase mb-1.5"
                    style={{ color: "#9BA8BF" }}
                  >
                    Output State
                  </p>
                  <pre
                    className="p-3 rounded-xl overflow-x-auto max-h-44 text-[11px] leading-relaxed"
                    style={{ background: "#0F172A", color: "#93C5FD" }}
                  >
                    {JSON.stringify(selectedStep.output_data, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right: floating diagnosis panel — sticky */}
        {diagnosis && (
          <div className="shrink-0 self-start sticky top-0">
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

      {/* ── Spectrum bar ── */}
      <SpectrumBar />
    </div>
  );
}

export default function InvestigationPage() {
  return (
    <Suspense
      fallback={
        <div
          className="flex-1 flex items-center justify-center text-sm"
          style={{ color: "#6B7A99" }}
        >
          Loading investigation…
        </div>
      }
    >
      <InvestigationContent />
    </Suspense>
  );
}
