"use client";

import React, { useEffect, useState } from "react";
import { BookOpen } from "lucide-react";
import { fetchPatterns } from "@/lib/api";

export default function PatternsPage() {
  const [patterns, setPatterns] = useState<any[]>([]);

  useEffect(() => {
    fetchPatterns().then((d) => setPatterns(d.patterns || []));
  }, []);

  return (
    <div className="p-8 space-y-7 max-w-6xl mx-auto w-full">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full"
            style={{ background: "#EEF2FF", color: "#3B82F6", border: "1px solid #C7D7FD" }}>
            Historical Knowledge Base
          </span>
        </div>
        <h1 className="text-3xl font-black tracking-tight" style={{ color: "#1A2236" }}>
          AI Agent Failure Pattern Catalog
        </h1>
        <p className="text-sm mt-1" style={{ color: "#6B7A99" }}>
          Historical taxonomy of recurring logic faults, constraint inversions, and schema drift patterns.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {patterns.map((pat) => (
          <div key={pat.pattern_id}
            className="rounded-2xl p-6 space-y-4 transition-all hover:shadow-md"
            style={{ background: "#FFFFFF", border: "1px solid #DDE3EE", boxShadow: "0 2px 10px rgba(26,34,54,0.05)" }}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded"
                  style={{ background: "#F0F4FA", color: "#6B7A99" }}>
                  {pat.category}
                </span>
                <h3 className="text-sm font-bold mt-2" style={{ color: "#1A2236" }}>{pat.title}</h3>
              </div>
              <span className="text-[11px] font-mono font-semibold px-2.5 py-1 rounded-full shrink-0"
                style={{ background: "#FEF3C7", color: "#B45309", border: "1px solid #FDE68A" }}>
                {pat.historical_frequency}
              </span>
            </div>

            <p className="text-xs leading-relaxed" style={{ color: "#6B7A99" }}>{pat.description}</p>

            <div>
              <p className="text-[10px] font-bold uppercase mb-1.5" style={{ color: "#9BA8BF" }}>Signature Keywords</p>
              <p className="text-[11px] font-mono p-2.5 rounded-xl"
                style={{ background: "#F8FAFD", border: "1px solid #EEF2F7", color: "#6B7A99" }}>
                {pat.signature_text}
              </p>
            </div>

            <div className="rounded-xl p-3.5"
              style={{ background: "#F0FDF4", border: "1px solid #BBF7D0" }}>
              <p className="text-[11px] font-bold mb-0.5" style={{ color: "#15803D" }}>Recommended Remediation</p>
              <p className="text-xs leading-relaxed" style={{ color: "#166534" }}>{pat.recommended_fix}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
