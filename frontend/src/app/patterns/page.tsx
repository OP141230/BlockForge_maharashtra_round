"use client";

import React, { useEffect, useState } from "react";
import { fetchPatterns } from "@/lib/api";

export default function PatternsPage() {
  const [patterns, setPatterns] = useState<any[]>([]);

  useEffect(() => {
    fetchPatterns().then((d) => setPatterns(d.patterns || []));
  }, []);

  return (
    <div className="p-7 space-y-6 max-w-6xl mx-auto w-full">
      {/* Header */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", padding: "3px 10px", borderRadius: 999, background: "#EFF6FF", color: "#3B82F6", border: "1px solid #BFDBFE" }}>
            Historical Knowledge Base
          </span>
          <span style={{ fontSize: 11, color: "#9BA8BF" }}>● Verified Failure Signatures</span>
        </div>
        <h1 style={{ fontSize: 24, fontWeight: 900, color: "#1A2236", letterSpacing: "-0.02em", margin: 0 }}>
          AI Agent Failure Pattern Catalog
        </h1>
        <p style={{ fontSize: 13, color: "#6B7A99", marginTop: 5 }}>
          Historical taxonomy of recurring logic faults, constraint inversions, and schema drift patterns.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {patterns.map((pat) => (
          <div key={pat.pattern_id} style={{
            background: "#FFFFFF", borderRadius: 16, padding: "20px 22px",
            border: "1px solid #E4EAF4", boxShadow: "0 2px 10px rgba(26,34,54,0.05)",
            display: "flex", flexDirection: "column", gap: 14,
            transition: "box-shadow 0.15s",
          }}
            onMouseEnter={e => ((e.currentTarget as HTMLElement).style.boxShadow = "0 4px 20px rgba(26,34,54,0.09)")}
            onMouseLeave={e => ((e.currentTarget as HTMLElement).style.boxShadow = "0 2px 10px rgba(26,34,54,0.05)")}
          >
            {/* Top */}
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
              <div>
                <span style={{ fontSize: 10, fontFamily: "monospace", fontWeight: 700, padding: "2px 8px", borderRadius: 6, background: "#F2F5FB", color: "#6B7A99" }}>
                  {pat.category}
                </span>
                <h3 style={{ fontSize: 14, fontWeight: 800, color: "#1A2236", margin: "8px 0 0" }}>
                  {pat.title}
                </h3>
              </div>
              <span style={{ fontSize: 10.5, fontFamily: "monospace", fontWeight: 700, padding: "3px 10px", borderRadius: 999, background: "#FEF3C7", color: "#B45309", border: "1px solid #FDE68A", flexShrink: 0 }}>
                {pat.historical_frequency}
              </span>
            </div>

            <p style={{ fontSize: 12, color: "#6B7A99", lineHeight: 1.6, margin: 0 }}>
              {pat.description}
            </p>

            {/* Signature */}
            <div>
              <p style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "#9BA8BF", marginBottom: 6 }}>
                Signature Keywords
              </p>
              <p style={{ fontSize: 11, fontFamily: "monospace", padding: "8px 12px", borderRadius: 9, background: "#F8FAFD", border: "1px solid #EEF2F8", color: "#6B7A99", margin: 0, lineHeight: 1.6 }}>
                {pat.signature_text}
              </p>
            </div>

            {/* Remediation */}
            <div style={{ padding: "12px 14px", borderRadius: 10, background: "#F0FDF4", border: "1px solid #BBF7D0" }}>
              <p style={{ fontSize: 10.5, fontWeight: 700, color: "#15803D", margin: "0 0 4px" }}>
                Recommended Remediation
              </p>
              <p style={{ fontSize: 12, color: "#166534", lineHeight: 1.55, margin: 0 }}>
                {pat.recommended_fix}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
