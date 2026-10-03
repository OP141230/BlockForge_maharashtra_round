"use client";

import React from "react";

export default function SpectrumBar() {
  return (
    <div
      className="w-full flex items-center justify-between px-6 py-3 shrink-0"
      style={{
        background: "rgba(255,255,255,0.90)",
        backdropFilter: "blur(12px)",
        borderTop: "1px solid #DDE3EE",
      }}
    >
      {/* Gradient bar with labels */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium" style={{ color: "#9BA8BF" }}>base</span>
          <div
            className="w-48 h-2.5 rounded-full"
            style={{
              background: "linear-gradient(to right, #94A3B8 0%, #3B82F6 30%, #7C5CFF 55%, #F59E0B 75%, #EF4444 100%)",
              boxShadow: "0 1px 4px rgba(26,34,54,0.10)",
            }}
          />
          <span className="text-xs font-medium" style={{ color: "#9BA8BF" }}>Intelligence</span>
          <div
            className="w-24 h-2.5 rounded-full ml-1"
            style={{
              background: "linear-gradient(to right, #F59E0B 0%, #EF4444 100%)",
              boxShadow: "0 1px 4px rgba(239,68,68,0.15)",
            }}
          />
          <span className="text-xs font-semibold" style={{ color: "#EF4444" }}>Failure</span>
        </div>
      </div>

      {/* Legend dots */}
      <div className="flex items-center gap-5 text-xs" style={{ color: "#9BA8BF" }}>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#22C55E" }} />
          Nominal
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ background: "#F59E0B", boxShadow: "0 0 6px rgba(245,158,11,0.6)" }}
          />
          <span style={{ color: "#B45309", fontWeight: 600 }}>Suspect</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#EF4444" }} />
          <span style={{ color: "#EF4444" }}>Downstream Impact</span>
        </span>
        <span className="font-mono text-[11px]" style={{ color: "#C8D0E0" }}>
          Offline · No API Key
        </span>
      </div>
    </div>
  );
}
