"use client";

import React, { useEffect, useState } from "react";
import {
  BookOpen,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  ArrowRight,
  Code2,
  Sparkles,
} from "lucide-react";
import { fetchPatterns } from "@/lib/api";

export default function PatternsPage() {
  const [patterns, setPatterns] = useState<any[]>([]);

  useEffect(() => {
    fetchPatterns().then((data) => setPatterns(data.patterns || []));
  }, []);

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs uppercase font-mono tracking-wider text-primary font-bold px-2 py-0.5 rounded bg-blue-50 border border-blue-200">
            Historical Knowledge Base
          </span>
          <span className="text-xs text-text-muted">● Verified Failure Signatures</span>
        </div>
        <h1 className="text-3xl font-black text-text-primary tracking-tight">
          AI Agent Failure Pattern Catalog
        </h1>
        <p className="text-sm text-text-muted mt-1 max-w-2xl">
          Historical taxonomy of recurring logic faults, constraint inversions, and schema drift patterns with concrete remediation recipes.
        </p>
      </div>

      {/* Patterns Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {patterns.map((pat) => (
          <div
            key={pat.pattern_id}
            className="p-6 rounded-2xl glass-card border border-panel-border space-y-4 hover:shadow-md transition-all"
          >
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                  {pat.category}
                </span>
                <h3 className="text-base font-bold text-text-primary mt-1.5">{pat.title}</h3>
              </div>
              <span className="text-[11px] font-mono font-semibold text-amber-700 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-200">
                {pat.historical_frequency}
              </span>
            </div>

            <p className="text-xs text-text-muted leading-relaxed">{pat.description}</p>

            {/* Signature Tokens */}
            <div>
              <span className="text-[10px] uppercase font-bold text-text-muted">Signature Keywords:</span>
              <p className="text-[11px] font-mono text-slate-600 bg-slate-50 p-2 rounded-lg mt-1 border border-slate-200/60">
                {pat.signature_text}
              </p>
            </div>

            {/* Remediation Guide */}
            <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs">
              <span className="font-bold text-emerald-900 block mb-0.5">Recommended Remediation:</span>
              <p className="text-emerald-800 leading-relaxed">{pat.recommended_fix}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
