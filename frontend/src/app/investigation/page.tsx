"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Activity, Code2, Waypoints, LayoutList } from "lucide-react";
import RadialGraph from "@/components/radial-graph";
import DiagnosisPanel from "@/components/diagnosis-panel";
import Timeline from "@/components/timeline";
import { fetchRun, fetchDiagnosis } from "@/lib/api";

/* ─── Spectrum bar (same as overview) ─── */
function SpectrumStrip() {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "center", gap: 12,
      padding: "10px 24px",
      background: "rgba(255,255,255,0.88)",
      backdropFilter: "blur(12px)",
      borderTop: "1px solid #E4EAF4",
      flexShrink: 0,
    }}>
      <span style={{ fontSize: 11, color: "#9BA8BF" }}>base</span>
      <div style={{
        width: 200, height: 9, borderRadius: 99,
        background: "linear-gradient(to right,#94A3B8 0%,#3B82F6 30%,#7C5CFF 55%,#F59E0B 75%,#EF4444 100%)",
        boxShadow: "0 1px 4px rgba(26,34,54,0.08)",
      }} />
      <span style={{ fontSize: 11, color: "#9BA8BF" }}>Intelligence</span>
      <div style={{ width: 72, height: 9, borderRadius: 99, background: "linear-gradient(to right,#F59E0B,#EF4444)" }} />
      <span style={{ fontSize: 11, fontWeight: 700, color: "#EF4444" }}>Failure</span>
    </div>
  );
}

function InvestigationContent() {
  const searchParams = useSearchParams();
  const runIdParam   = searchParams.get("run_id") || "run_travel_paris_fail";

  const [run,        setRun]        = useState<any>(null);
  const [diagnosis,  setDiagnosis]  = useState<any>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [viewMode,   setViewMode]   = useState<"graph" | "timeline">("graph");
  const [loading,    setLoading]    = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchRun(runIdParam).catch(() => null),
      fetchDiagnosis(runIdParam).catch(() => null),
    ]).then(([r, d]) => {
      setRun(r); setDiagnosis(d);
      const suspect = r?.steps?.find((s: any) => s.is_root_suspect);
      setSelectedId(suspect?.id ?? r?.steps?.[0]?.id ?? null);
      setLoading(false);
    });
  }, [runIdParam]);

  if (loading || !run) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: "#EEF2F7", gap: 12 }}>
        <Activity style={{ width: 18, height: 18, color: "#3B82F6" }} className="animate-spin" />
        <span style={{ fontSize: 13, color: "#6B7A99" }}>Loading flight trace…</span>
      </div>
    );
  }

  const selStep = run.steps.find((s: any) => s.id === selectedId) || run.steps[0];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden", background: "#EEF2F7" }}>

      {/* ── Top bar ── */}
      <div style={{
        flexShrink: 0, padding: "11px 22px",
        background: "#FFFFFF", borderBottom: "1px solid #E4EAF4",
        boxShadow: "0 1px 6px rgba(26,34,54,0.05)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <h2 style={{ fontSize: 15, fontWeight: 900, color: "#1A2236", margin: 0 }}>
                {run.agent_name} Execution
              </h2>
              <span style={{
                fontSize: 9.5, fontWeight: 700, padding: "2px 8px",
                borderRadius: 999, textTransform: "uppercase" as const,
                ...(run.status === "FAILED"
                  ? { background: "#FFF1F2", color: "#DC2626" }
                  : { background: "#ECFDF5", color: "#16A34A" }),
              }}>
                {run.status}
              </span>
            </div>
            <p style={{ fontSize: 11, color: "#9BA8BF", margin: "2px 0 0" }}>{run.scenario}</p>
          </div>
        </div>

        {/* View toggle */}
        <div style={{
          display: "flex", alignItems: "center", gap: 4, padding: 4,
          background: "#F2F5FB", border: "1px solid #E0E7F0", borderRadius: 12,
        }}>
          {([
            { mode: "graph",    label: "Radial Graph", Icon: Waypoints    },
            { mode: "timeline", label: "Timeline",     Icon: LayoutList   },
          ] as const).map(({ mode, label, Icon }) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              style={{
                display: "flex", alignItems: "center", gap: 5,
                padding: "6px 14px", borderRadius: 9, fontSize: 11.5,
                fontWeight: 600, border: "none", cursor: "pointer",
                transition: "all 0.15s",
                ...(viewMode === mode
                  ? { background: "#FFFFFF", color: "#3B82F6", boxShadow: "0 1px 4px rgba(26,34,54,0.08)" }
                  : { background: "transparent", color: "#6B7A99" }),
              }}
            >
              <Icon style={{ width: 13, height: 13 }} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Main area ── */}
      <div style={{ flex: 1, display: "flex", gap: 16, padding: 16, overflow: "hidden" }}>

        {/* Left: graph / timeline + inspector */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 14, minWidth: 0, overflowY: "auto" }}>

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
            <div style={{
              background: "#FFFFFF", border: "1px solid #E4EAF4",
              borderRadius: 16, padding: 18,
              boxShadow: "0 2px 10px rgba(26,34,54,0.05)",
            }}>
              <Timeline
                steps={run.steps}
                selectedStepId={selectedId}
                onSelectStep={setSelectedId}
              />
            </div>
          )}

          {/* Event inspector */}
          {selStep && (
            <div style={{
              background: "#FFFFFF", border: "1px solid #E4EAF4",
              borderRadius: 16, padding: 18,
              boxShadow: "0 2px 10px rgba(26,34,54,0.05)",
              flexShrink: 0,
            }}>
              <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                paddingBottom: 12, marginBottom: 12, borderBottom: "1px solid #EEF2F8",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Code2 style={{ width: 14, height: 14, color: "#3B82F6" }} />
                  <span style={{ fontSize: 12, fontWeight: 700, color: "#1A2236" }}>
                    Step {selStep.step_index}: {selStep.step_name}
                    <span style={{ fontSize: 11, fontFamily: "monospace", color: "#9BA8BF", marginLeft: 6 }}>
                      ({selStep.tool_name})
                    </span>
                  </span>
                  {selStep.is_root_suspect && (
                    <span style={{
                      fontSize: 8.5, fontWeight: 800, textTransform: "uppercase" as const,
                      padding: "2px 7px", borderRadius: 4,
                      background: "#F59E0B", color: "#FFFFFF",
                    }}>ROOT SUSPECT</span>
                  )}
                </div>
                <span style={{ fontSize: 10.5, fontFamily: "monospace", color: "#9BA8BF" }}>
                  {selStep.duration_ms?.toFixed(0)}ms
                </span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                {[
                  { label: "Input Payload", data: selStep.input_data, color: "#86EFAC" },
                  { label: "Output State",  data: selStep.output_data, color: "#93C5FD" },
                ].map(({ label, data, color }) => (
                  <div key={label}>
                    <p style={{ fontSize: 9.5, fontWeight: 700, textTransform: "uppercase" as const, letterSpacing: "0.04em", color: "#9BA8BF", marginBottom: 6 }}>
                      {label}
                    </p>
                    <pre style={{
                      margin: 0, padding: 12, borderRadius: 10,
                      background: "#0F172A", color,
                      fontSize: 10.5, lineHeight: 1.6,
                      overflowX: "auto", maxHeight: 180,
                      fontFamily: "JetBrains Mono, monospace",
                    }}>
                      {JSON.stringify(data, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: floating diagnosis panel */}
        {diagnosis && (
          <div style={{ flexShrink: 0, alignSelf: "flex-start", position: "sticky", top: 0 }}>
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
      <SpectrumStrip />
    </div>
  );
}

export default function InvestigationPage() {
  return (
    <Suspense fallback={
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, color: "#6B7A99" }}>
        Loading investigation…
      </div>
    }>
      <InvestigationContent />
    </Suspense>
  );
}
