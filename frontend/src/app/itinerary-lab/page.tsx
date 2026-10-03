"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Map, Plus, Upload, Play, ChevronRight, ChevronDown,
  AlertTriangle, AlertCircle, Info, Zap, CheckCircle2,
  Search, RotateCcw, ArrowRight, X, Lightbulb, Clock,
  DollarSign, Users, Calendar, Wrench, Eye,
} from "lucide-react";
import {
  fetchItineraries, fetchItinerary, validateItinerary, applyItineraryFix, importItinerary,
} from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ItineraryItem {
  title: string; category: string; location: string; date: string;
  start_time: string; end_time: string; cost: number; currency: string;
  booking_status: string; notes: string;
}

interface Finding {
  rule_id: string; severity: string; title: string;
  affected_item_indices: number[]; related_item_indices: number[];
  evidence: Record<string, any>; expected: string; actual: string;
  why_it_matters: string; suggested_fix: string;
  fix_type: string; fix_payload: Record<string, any>;
  linked_run_id?: string; linked_step_id?: string;
}

interface ValidationSummary {
  passed: number; critical: number; high: number;
  medium: number; low: number; optimization: number; total_findings: number;
}

interface ValidationResult {
  validation_run_id: string; label: string;
  findings: Finding[]; summary: ValidationSummary;
  patched_items?: ItineraryItem[] | null;
  linked_run_id?: string;
  change_applied?: string;   // present on apply-fix response
}

// ── Severity helpers ──────────────────────────────────────────────────────────

const SEV_CONFIG: Record<string, { color: string; bg: string; border: string; icon: React.ElementType; label: string }> = {
  CRITICAL:     { color: "#DC2626", bg: "#FFF1F2", border: "#FCA5A5", icon: AlertCircle,  label: "Critical"     },
  HIGH:         { color: "#B45309", bg: "#FEF3C7", border: "#FDE68A", icon: AlertTriangle, label: "High"        },
  MEDIUM:       { color: "#1D4ED8", bg: "#EFF6FF", border: "#BFDBFE", icon: Info,          label: "Medium"      },
  LOW:          { color: "#6B7A99", bg: "#F2F5FB", border: "#E4EAF4", icon: Info,          label: "Low"         },
  OPTIMIZATION: { color: "#7C5CFF", bg: "#F5F3FF", border: "#DDD6FE", icon: Zap,           label: "Optimization"},
};

function SevBadge({ sev }: { sev: string }) {
  const c = SEV_CONFIG[sev] || SEV_CONFIG.LOW;
  const Icon = c.icon;
  return (
    <span style={{ display:"inline-flex", alignItems:"center", gap:4, fontSize:10.5, fontWeight:700,
      padding:"2px 8px", borderRadius:999, background:c.bg, color:c.color, border:`1px solid ${c.border}` }}>
      <Icon style={{ width:10, height:10 }} />{c.label}
    </span>
  );
}

// ── Summary bar ───────────────────────────────────────────────────────────────

function SummaryBar({ summary, before, after }: { summary: ValidationSummary; before?: ValidationSummary; after?: ValidationSummary }) {
  const chips = [
    { label: "Passed",       val: summary.passed,       color: "#16A34A", bg: "#F0FDF4" },
    { label: "Critical",     val: summary.critical,     color: "#DC2626", bg: "#FFF1F2" },
    { label: "High",         val: summary.high,         color: "#B45309", bg: "#FEF3C7" },
    { label: "Medium",       val: summary.medium,       color: "#1D4ED8", bg: "#EFF6FF" },
    { label: "Low",          val: summary.low,          color: "#6B7A99", bg: "#F2F5FB" },
    { label: "Optimization", val: summary.optimization, color: "#7C5CFF", bg: "#F5F3FF" },
  ];
  return (
    <div style={{ display:"flex", alignItems:"center", gap:8, flexWrap:"wrap" }}>
      {chips.map(c => (
        <div key={c.label} style={{ display:"flex", alignItems:"center", gap:6,
          padding:"6px 14px", borderRadius:10, background:c.bg, border:`1px solid ${c.color}22` }}>
          <span style={{ fontSize:18, fontWeight:900, fontFamily:"monospace", color:c.color, lineHeight:1 }}>
            {c.val}
          </span>
          <span style={{ fontSize:11, color:c.color, fontWeight:600 }}>{c.label}</span>
        </div>
      ))}
      {before && after && (
        <div style={{ marginLeft:"auto", display:"flex", alignItems:"center", gap:10 }}>
          <div style={{ textAlign:"center" }}>
            <p style={{ fontSize:9.5, color:"#9BA8BF", margin:"0 0 1px", textTransform:"uppercase", fontWeight:700 }}>Before</p>
            <p style={{ fontSize:17, fontWeight:900, color:"#EF4444", fontFamily:"monospace", margin:0 }}>{before.total_findings}</p>
          </div>
          <ArrowRight style={{ width:16, height:16, color:"#9BA8BF" }} />
          <div style={{ textAlign:"center" }}>
            <p style={{ fontSize:9.5, color:"#9BA8BF", margin:"0 0 1px", textTransform:"uppercase", fontWeight:700 }}>After</p>
            <p style={{ fontSize:17, fontWeight:900, color:"#22C55E", fontFamily:"monospace", margin:0 }}>{after.total_findings}</p>
          </div>
          <div style={{ padding:"4px 10px", borderRadius:9, background:"#F0FDF4", border:"1px solid #86EFAC" }}>
            <p style={{ fontSize:9.5, color:"#9BA8BF", margin:"0 0 1px", textTransform:"uppercase", fontWeight:700 }}>Resolved</p>
            <p style={{ fontSize:15, fontWeight:900, color:"#16A34A", fontFamily:"monospace", margin:0, textAlign:"center" }}>
              {Math.max(0, before.total_findings - after.total_findings)}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Timeline view ─────────────────────────────────────────────────────────────

function ItineraryTimeline({
  items, findings, selectedFindingIdx, onSelectItem,
}: {
  items: ItineraryItem[]; findings: Finding[];
  selectedFindingIdx: number | null; onSelectItem: (idx: number) => void;
}) {
  // Group by date
  const byDate: Record<string, { item: ItineraryItem; origIdx: number }[]> = {};
  items.forEach((item, i) => {
    const d = item.date || "Undated";
    (byDate[d] = byDate[d] || []).push({ item, origIdx: i });
  });

  // Build index: itemIndex → affected findings
  const itemFindings: Record<number, Finding[]> = {};
  findings.forEach(f => {
    f.affected_item_indices.forEach(i => {
      (itemFindings[i] = itemFindings[i] || []).push(f);
    });
  });

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
      {Object.entries(byDate).sort(([a],[b]) => a.localeCompare(b)).map(([date, dayItems]) => (
        <div key={date}>
          <p style={{ fontSize:11, fontWeight:700, color:"#9BA8BF", textTransform:"uppercase",
            letterSpacing:"0.06em", marginBottom:8 }}>{date}</p>
          <div style={{ display:"flex", flexDirection:"column", gap:3 }}>
            {dayItems.map(({ item, origIdx }) => {
              const founds = itemFindings[origIdx] || [];
              const worstSev = founds.reduce<string | null>((w, f) => {
                const order = ["CRITICAL","HIGH","MEDIUM","LOW","OPTIMIZATION"];
                return w === null || order.indexOf(f.severity) < order.indexOf(w) ? f.severity : w;
              }, null);
              const cfg = worstSev ? SEV_CONFIG[worstSev] : null;

              return (
                <div key={origIdx}>
                  {/* Transfer gap indicator — shown before items with impossible transfer */}
                  {founds.some(f => f.rule_id === "IMPOSSIBLE_TRANSFER") && (
                    <div style={{ display:"flex", alignItems:"center", gap:8, padding:"5px 14px",
                      marginLeft:32, marginBottom:2 }}>
                      <div style={{ width:1, height:18, background:"#FCA5A5", margin:"0 9px" }} />
                      <span style={{ fontSize:10.5, color:"#DC2626", fontWeight:600, fontFamily:"monospace" }}>
                        {founds.find(f=>f.rule_id==="IMPOSSIBLE_TRANSFER")?.evidence?.gap_available_min} min available
                        {" "}·{" "}
                        {founds.find(f=>f.rule_id==="IMPOSSIBLE_TRANSFER")?.evidence?.travel_time_estimated_min} min needed
                      </span>
                      <span style={{ fontSize:10, color:"#DC2626", fontWeight:700,
                        background:"#FFF1F2", border:"1px solid #FCA5A5", padding:"1px 7px", borderRadius:99 }}>
                        🔴 Impossible Transfer
                      </span>
                    </div>
                  )}

                  <div
                    onClick={() => founds.length && onSelectItem(
                      findings.indexOf(founds[0])
                    )}
                    style={{
                      display:"flex", alignItems:"flex-start", gap:12,
                      padding:"10px 14px", borderRadius:12, cursor: founds.length ? "pointer" : "default",
                      background: cfg ? cfg.bg : "#FFFFFF",
                      border: `1px solid ${cfg ? cfg.border : "#E4EAF4"}`,
                      boxShadow: cfg ? `0 0 0 2px ${cfg.color}18` : "none",
                      transition:"all 0.12s",
                    }}
                  >
                    {/* Time column */}
                    <div style={{ width:72, flexShrink:0, textAlign:"right" }}>
                      {item.start_time && (
                        <p style={{ fontSize:10.5, fontFamily:"monospace", fontWeight:700,
                          color: cfg ? cfg.color : "#6B7A99", margin:0 }}>
                          {item.start_time}
                        </p>
                      )}
                      {item.end_time && (
                        <p style={{ fontSize:9.5, fontFamily:"monospace", color:"#9BA8BF", margin:0 }}>
                          → {item.end_time}
                        </p>
                      )}
                    </div>

                    {/* Dot */}
                    <div style={{ marginTop:3, flexShrink:0 }}>
                      <div style={{ width:8, height:8, borderRadius:"50%",
                        background: cfg ? cfg.color : "#C8D0E0",
                        boxShadow: cfg ? `0 0 6px ${cfg.color}88` : "none" }} />
                    </div>

                    {/* Content */}
                    <div style={{ flex:1, minWidth:0 }}>
                      <div style={{ display:"flex", alignItems:"center", gap:8, flexWrap:"wrap" }}>
                        <p style={{ fontSize:12.5, fontWeight:700, color:"#1A2236", margin:0 }}>
                          {item.title}
                        </p>
                        <span style={{ fontSize:9.5, padding:"1px 7px", borderRadius:99,
                          background:"#F2F5FB", color:"#6B7A99", fontWeight:500, border:"1px solid #E4EAF4" }}>
                          {item.category}
                        </span>
                        {founds.map((f, fi) => <SevBadge key={fi} sev={f.severity} />)}
                      </div>
                      {item.location && (
                        <p style={{ fontSize:11, color:"#9BA8BF", margin:"2px 0 0" }}>{item.location}</p>
                      )}
                      {founds.length > 0 && (
                        <div style={{ marginTop:5, display:"flex", flexDirection:"column", gap:2 }}>
                          {founds.map((f, fi) => (
                            <p key={fi} style={{ fontSize:11, color: SEV_CONFIG[f.severity]?.color || "#6B7A99",
                              margin:0, fontWeight:500 }}>
                              ↳ {f.title}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Cost */}
                    {item.cost > 0 && (
                      <span style={{ fontSize:11, fontFamily:"monospace", fontWeight:700,
                        color:"#6B7A99", flexShrink:0 }}>
                        {item.currency || "€"}{item.cost}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Finding detail panel ──────────────────────────────────────────────────────

function FindingDetail({
  finding, itemIndex, items, itineraryId, onClose, onFixApplied,
}: {
  finding: Finding; itemIndex: number; items: ItineraryItem[];
  itineraryId: string; onClose: () => void;
  onFixApplied: (result: any) => void;
}) {
  const [applying, setApplying] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const cfg = SEV_CONFIG[finding.severity] || SEV_CONFIG.LOW;
  const Icon = cfg.icon;

  const canAutoFix = finding.fix_type === "AUTO_RESCHEDULE" || finding.fix_type === "AUTO_REMOVE";

  const handleApply = async () => {
    setApplying(true);
    try {
      const result = await applyItineraryFix(
        itineraryId,
        finding.fix_type,
        finding.affected_item_indices[0] ?? itemIndex,
        finding.fix_payload,
      );
      onFixApplied(result);
    } catch (e) { console.error(e); }
    finally { setApplying(false); }
  };

  return (
    <div style={{
      position:"fixed", inset:0, zIndex:50,
      display:"flex", alignItems:"flex-end", justifyContent:"flex-end",
      pointerEvents:"none",
    }}>
      {/* Backdrop */}
      <div onClick={onClose} style={{ position:"absolute", inset:0, background:"rgba(26,34,54,0.25)",
        pointerEvents:"all" }} />

      {/* Drawer */}
      <div style={{
        position:"relative", zIndex:1, pointerEvents:"all",
        width:440, height:"100vh", overflowY:"auto",
        background:"#FFFFFF", borderLeft:"1px solid #E4EAF4",
        boxShadow:"-8px 0 40px rgba(26,34,54,0.12)",
        display:"flex", flexDirection:"column",
      }}>
        {/* Header */}
        <div style={{ padding:"20px 22px 16px", borderBottom:"1px solid #EEF2F8",
          background: cfg.bg, flexShrink:0 }}>
          <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", gap:10 }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <div style={{ width:36, height:36, borderRadius:10, background:cfg.color+"20",
                display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
                <Icon style={{ width:18, height:18, color:cfg.color }} />
              </div>
              <div>
                <p style={{ fontSize:10, fontWeight:700, color:cfg.color, textTransform:"uppercase",
                  letterSpacing:"0.06em", margin:"0 0 2px" }}>{cfg.label}</p>
                <h3 style={{ fontSize:15, fontWeight:800, color:"#1A2236", margin:0 }}>{finding.title}</h3>
              </div>
            </div>
            <button onClick={onClose} style={{ background:"none", border:"none", cursor:"pointer",
              color:"#9BA8BF", padding:4 }}>
              <X style={{ width:18, height:18 }} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{ flex:1, padding:"18px 22px", display:"flex", flexDirection:"column", gap:16 }}>

          {/* Affected item */}
          {finding.affected_item_indices.map(idx => items[idx]).filter(Boolean).map((item, i) => (
            <div key={i} style={{ padding:"12px 14px", borderRadius:11,
              background:"#F8FAFD", border:"1px solid #E4EAF4" }}>
              <p style={{ fontSize:9.5, fontWeight:700, textTransform:"uppercase", color:"#9BA8BF",
                letterSpacing:"0.04em", margin:"0 0 5px" }}>Affected Item</p>
              <p style={{ fontWeight:700, color:"#1A2236", fontSize:13, margin:"0 0 3px" }}>{item.title}</p>
              <p style={{ fontSize:11, color:"#6B7A99", margin:0 }}>
                {item.date}{item.start_time && ` · ${item.start_time}${item.end_time ? ` – ${item.end_time}` : ""}`}
                {item.location && ` · ${item.location}`}
              </p>
            </div>
          ))}

          {/* Expected vs Actual */}
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
            <div style={{ padding:"10px 12px", borderRadius:10, background:"#F0FDF4", border:"1px solid #BBF7D0" }}>
              <p style={{ fontSize:9.5, fontWeight:700, color:"#15803D", textTransform:"uppercase",
                letterSpacing:"0.04em", margin:"0 0 4px" }}>Expected</p>
              <p style={{ fontSize:11.5, color:"#166534", margin:0, lineHeight:1.5 }}>{finding.expected}</p>
            </div>
            <div style={{ padding:"10px 12px", borderRadius:10, background:"#FFF1F2", border:"1px solid #FCA5A5" }}>
              <p style={{ fontSize:9.5, fontWeight:700, color:"#DC2626", textTransform:"uppercase",
                letterSpacing:"0.04em", margin:"0 0 4px" }}>Actual</p>
              <p style={{ fontSize:11.5, color:"#7F1D1D", margin:0, lineHeight:1.5 }}>{finding.actual}</p>
            </div>
          </div>

          {/* Evidence */}
          <div style={{ padding:"12px 14px", borderRadius:11, background:"#F8FAFD", border:"1px solid #E4EAF4" }}>
            <p style={{ fontSize:9.5, fontWeight:700, textTransform:"uppercase", color:"#9BA8BF",
              letterSpacing:"0.04em", margin:"0 0 8px" }}>Evidence</p>
            <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
              {Object.entries(finding.evidence).map(([k, v]) => (
                <div key={k} style={{ display:"flex", justifyContent:"space-between",
                  fontSize:11, padding:"3px 0", borderBottom:"1px solid #EEF2F8" }}>
                  <span style={{ color:"#6B7A99", fontWeight:500 }}>{k.replace(/_/g," ")}</span>
                  <span style={{ fontFamily:"monospace", fontWeight:700, color:"#1A2236",
                    maxWidth:200, textAlign:"right", wordBreak:"break-all" }}>
                    {typeof v === "object" ? JSON.stringify(v) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Why it matters */}
          <div style={{ padding:"12px 14px", borderRadius:11, background:"#FFFBEB", border:"1px solid #FDE68A" }}>
            <p style={{ fontSize:9.5, fontWeight:700, textTransform:"uppercase", color:"#B45309",
              letterSpacing:"0.04em", margin:"0 0 5px" }}>Why it matters</p>
            <p style={{ fontSize:12, color:"#78716C", margin:0, lineHeight:1.55 }}>{finding.why_it_matters}</p>
          </div>

          {/* Suggested fix */}
          <div style={{ padding:"12px 14px", borderRadius:11, background:"#F5F3FF", border:"1px solid #DDD6FE" }}>
            <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:6 }}>
              <Lightbulb style={{ width:13, height:13, color:"#7C5CFF" }} />
              <p style={{ fontSize:9.5, fontWeight:700, textTransform:"uppercase", color:"#7C5CFF",
                letterSpacing:"0.04em", margin:0 }}>Suggested Fix</p>
            </div>
            <p style={{ fontSize:12, color:"#4C1D95", margin:0, lineHeight:1.55 }}>{finding.suggested_fix}</p>
          </div>

          {/* BLACKBOX trace links */}
          {finding.linked_run_id && (
            <div style={{ padding:"12px 14px", borderRadius:11, background:"#EFF6FF", border:"1px solid #BFDBFE" }}>
              <p style={{ fontSize:9.5, fontWeight:700, textTransform:"uppercase", color:"#1D4ED8",
                letterSpacing:"0.04em", margin:"0 0 8px" }}>Linked BLACKBOX Execution</p>
              <p style={{ fontSize:11, color:"#6B7A99", margin:"0 0 10px" }}>
                This itinerary was generated by an agent execution. Investigate the root cause in BLACKBOX.
              </p>
              <div style={{ display:"flex", gap:8 }}>
                <Link href={`/investigation?run_id=${finding.linked_run_id}`}
                  style={{ display:"flex", alignItems:"center", gap:6, padding:"8px 14px",
                    borderRadius:9, fontSize:12, fontWeight:700, color:"white", textDecoration:"none",
                    background:"#3B82F6", boxShadow:"0 3px 10px rgba(59,130,246,0.25)" }}>
                  <Search style={{ width:13, height:13 }} /> Investigate
                </Link>
                <Link href={`/replay?run_id=${finding.linked_run_id}`}
                  style={{ display:"flex", alignItems:"center", gap:6, padding:"8px 14px",
                    borderRadius:9, fontSize:12, fontWeight:700, color:"#7C5CFF", textDecoration:"none",
                    background:"#F5F3FF", border:"1px solid #DDD6FE" }}>
                  <RotateCcw style={{ width:13, height:13 }} /> Replay
                </Link>
              </div>
            </div>
          )}
          {!finding.linked_run_id && (
            <p style={{ fontSize:11, color:"#C8D0E0", fontStyle:"italic" }}>
              No linked execution trace — standalone itinerary.
            </p>
          )}

          {/* Fix actions */}
          {canAutoFix && (
            <div style={{ display:"flex", gap:8, paddingTop:4 }}>
              <button onClick={() => setPreviewOpen(!previewOpen)}
                style={{ display:"flex", alignItems:"center", gap:7, flex:1, padding:"10px 14px",
                  borderRadius:10, border:"1px solid #E4EAF4", background:"#F8FAFD",
                  fontSize:12, fontWeight:700, color:"#1A2236", cursor:"pointer" }}>
                <Eye style={{ width:14, height:14, color:"#6B7A99" }} />
                Preview Fix
              </button>
              <button onClick={handleApply} disabled={applying}
                style={{ display:"flex", alignItems:"center", gap:7, flex:1, padding:"10px 14px",
                  borderRadius:10, border:"none",
                  background: applying ? "#94A3B8" : "#22C55E",
                  fontSize:12, fontWeight:700, color:"white", cursor: applying ? "not-allowed" : "pointer",
                  boxShadow:"0 3px 10px rgba(34,197,94,0.28)" }}>
                <Wrench style={{ width:14, height:14 }} />
                {applying ? "Applying…" : "Apply Fix + Retest"}
              </button>
            </div>
          )}
          {!canAutoFix && (
            <div style={{ padding:"10px 14px", borderRadius:10, background:"#F8FAFD", border:"1px solid #E4EAF4" }}>
              <p style={{ fontSize:11, color:"#9BA8BF", margin:0 }}>
                This finding requires manual correction. Use the suggested fix above.
              </p>
            </div>
          )}

          {/* Preview */}
          {previewOpen && finding.fix_payload && Object.keys(finding.fix_payload).length > 0 && (
            <div style={{ padding:"12px 14px", borderRadius:11, background:"#ECFDF5", border:"1px solid #BBF7D0" }}>
              <p style={{ fontSize:9.5, fontWeight:700, textTransform:"uppercase", color:"#15803D",
                letterSpacing:"0.04em", margin:"0 0 8px" }}>Fix Preview</p>
              {Object.entries(finding.fix_payload).map(([k, v]) => (
                <div key={k} style={{ display:"flex", justifyContent:"space-between", fontSize:11,
                  padding:"3px 0", borderBottom:"1px solid #D1FAE5" }}>
                  <span style={{ color:"#166534" }}>{k}</span>
                  <span style={{ fontFamily:"monospace", fontWeight:700, color:"#15803D" }}>{String(v)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Import JSON modal ─────────────────────────────────────────────────────────

function ImportModal({ onClose, onImported }: { onClose: () => void; onImported: (id: string) => void }) {
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handle = async () => {
    setError("");
    let parsed: any;
    try { parsed = JSON.parse(text); }
    catch { setError("Invalid JSON — check syntax."); return; }
    setLoading(true);
    try {
      const result = await importItinerary(parsed);
      onImported(result.imported_id || result.id);
    } catch (e: any) { setError(e.message || "Import failed"); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ position:"fixed", inset:0, zIndex:60, display:"flex",
      alignItems:"center", justifyContent:"center" }}>
      <div onClick={onClose} style={{ position:"absolute", inset:0, background:"rgba(26,34,54,0.35)" }} />
      <div style={{ position:"relative", zIndex:1, width:540, background:"#FFFFFF",
        borderRadius:18, border:"1px solid #E4EAF4", boxShadow:"0 16px 48px rgba(26,34,54,0.15)",
        padding:"24px 26px", display:"flex", flexDirection:"column", gap:14 }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
          <h3 style={{ fontSize:16, fontWeight:800, color:"#1A2236", margin:0 }}>Import Itinerary JSON</h3>
          <button onClick={onClose} style={{ background:"none", border:"none", cursor:"pointer", color:"#9BA8BF" }}>
            <X style={{ width:18, height:18 }} />
          </button>
        </div>
        <p style={{ fontSize:12, color:"#6B7A99", margin:0 }}>
          Paste an itinerary JSON. Only data fields are accepted — no code is executed.
        </p>
        <textarea value={text} onChange={e => setText(e.target.value)}
          placeholder='{ "name": "My Trip", "destination": "Paris", "items": [...] }'
          style={{ width:"100%", height:200, padding:"10px 12px", borderRadius:10,
            border:"1px solid #E4EAF4", fontSize:11.5, fontFamily:"monospace",
            color:"#1A2236", background:"#F8FAFD", resize:"vertical", outline:"none" }}
        />
        {error && <p style={{ fontSize:11.5, color:"#DC2626", margin:0 }}>{error}</p>}
        <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
          <button onClick={onClose} style={{ padding:"9px 18px", borderRadius:10,
            border:"1px solid #E4EAF4", background:"#F8FAFD", fontSize:12, fontWeight:600,
            color:"#6B7A99", cursor:"pointer" }}>Cancel</button>
          <button onClick={handle} disabled={loading || !text.trim()}
            style={{ padding:"9px 18px", borderRadius:10, border:"none",
              background:"#3B82F6", fontSize:12, fontWeight:700, color:"white",
              cursor: loading || !text.trim() ? "not-allowed" : "pointer",
              opacity: loading || !text.trim() ? 0.6 : 1,
              boxShadow:"0 3px 10px rgba(59,130,246,0.25)" }}>
            {loading ? "Importing…" : "Import & Open"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── MAIN PAGE ─────────────────────────────────────────────────────────────────

export default function ItineraryLabPage() {
  const [itineraries, setItineraries]     = useState<any[]>([]);
  const [activeItin,  setActiveItin]      = useState<any>(null);
  const [validating,  setValidating]      = useState(false);
  const [valResult,   setValResult]       = useState<ValidationResult | null>(null);
  const [afterResult, setAfterResult]     = useState<ValidationResult | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<number | null>(null);
  const [showImport,  setShowImport]      = useState(false);
  const [loading,     setLoading]         = useState(true);
  const [activeTab,   setActiveTab]       = useState<"timeline"|"findings">("timeline");

  const items: ItineraryItem[] = activeItin
    ? (afterResult?.patched_items ?? activeItin.items ?? [])
    : [];
  const findings: Finding[] = valResult?.findings ?? [];

  useEffect(() => {
    fetchItineraries().then(d => {
      const list = d.itineraries || [];
      setItineraries(list);
      // auto-open demo
      const demo = list.find((i: any) => i.is_demo);
      if (demo) loadItinerary(demo.id);
      else setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const loadItinerary = async (id: string) => {
    setLoading(true);
    setValResult(null);
    setAfterResult(null);
    setSelectedFinding(null);
    try {
      const data = await fetchItinerary(id);
      setActiveItin(data);
      // restore last validation run if exists
      const runs: ValidationResult[] = data.validation_runs || [];
      const before = runs.find(r => r.label === "BEFORE") || runs[0];
      const after  = runs.find(r => r.label === "AFTER");
      if (before) setValResult(before);
      if (after)  setAfterResult(after);
    } catch {}
    setLoading(false);
  };

  const handleValidate = async () => {
    if (!activeItin) return;
    setValidating(true);
    setValResult(null);
    setAfterResult(null);
    setSelectedFinding(null);
    try {
      const r = await validateItinerary(activeItin.id);
      setValResult(r);
    } catch {}
    setValidating(false);
  };

  const handleFixApplied = (result: any) => {
    setAfterResult(result);
    setSelectedFinding(null);
    // rebuild valResult from before if needed
    if (!valResult) setValResult(result);
  };

  const totalCost = items.reduce((s, i) => s + (i.cost || 0), 0);
  const budget    = activeItin?.budget ?? 0;
  const overBudget = budget > 0 && totalCost > budget;

  const card: React.CSSProperties = {
    background:"#FFFFFF", borderRadius:16,
    border:"1px solid #E4EAF4",
    boxShadow:"0 2px 10px rgba(26,34,54,0.05)",
  };

  return (
    <div style={{ padding:"28px 28px 28px 28px", display:"flex", flexDirection:"column",
      gap:22, maxWidth:1280, margin:"0 auto", width:"100%" }}>

      {/* ── Header ── */}
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", gap:16 }}>
        <div>
          <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8 }}>
            <span style={{ fontSize:10, fontWeight:700, letterSpacing:"0.06em",
              textTransform:"uppercase", padding:"3px 10px", borderRadius:999,
              background:"#EFF6FF", color:"#3B82F6", border:"1px solid #BFDBFE" }}>
              Itinerary Lab
            </span>
            <span style={{ fontSize:11, color:"#9BA8BF" }}>● Deterministic Validation Engine</span>
          </div>
          <h1 style={{ fontSize:24, fontWeight:900, color:"#1A2236",
            letterSpacing:"-0.02em", margin:0 }}>
            Itinerary Lab
          </h1>
          <p style={{ fontSize:13, color:"#6B7A99", marginTop:5, maxWidth:520, lineHeight:1.5 }}>
            Validate AI-generated travel itineraries before they reach users.
            Detect errors, suspicious decisions and inconsistencies automatically.
          </p>
          <div style={{ display:"flex", alignItems:"center", gap:6, marginTop:8, flexWrap:"wrap" }}>
            {["Detect","→","Explain","→","Investigate","→","Replay","→","Fix","→","Verify"].map((s,i) => (
              <span key={i} style={{ fontSize:11, fontWeight: s==="→" ? 400 : 700,
                color: s==="→" ? "#C8D0E0" : "#3B82F6" }}>{s}</span>
            ))}
          </div>
        </div>
        <div style={{ display:"flex", gap:10, flexShrink:0 }}>
          <button onClick={() => setShowImport(true)}
            style={{ display:"flex", alignItems:"center", gap:7, padding:"9px 16px",
              borderRadius:11, border:"1px solid #E4EAF4", background:"#FFFFFF",
              fontSize:12, fontWeight:700, color:"#1A2236", cursor:"pointer" }}>
            <Upload style={{ width:14, height:14, color:"#6B7A99" }} /> Import JSON
          </button>
        </div>
      </div>

      {/* ── Itinerary selector strip ── */}
      <div style={{ display:"flex", gap:10, flexWrap:"wrap" }}>
        {itineraries.map(itin => (
          <button key={itin.id} onClick={() => loadItinerary(itin.id)}
            style={{ display:"flex", alignItems:"center", gap:8, padding:"8px 16px", borderRadius:11,
              border:`1px solid ${activeItin?.id === itin.id ? "#3B82F6" : "#E4EAF4"}`,
              background: activeItin?.id === itin.id ? "#EFF6FF" : "#FFFFFF",
              fontSize:12, fontWeight:600, color: activeItin?.id === itin.id ? "#3B82F6" : "#1A2236",
              cursor:"pointer", transition:"all 0.12s",
              boxShadow: activeItin?.id === itin.id ? "0 2px 8px rgba(59,130,246,0.15)" : "none" }}>
            <Map style={{ width:13, height:13 }} />
            {itin.name}
            {itin.is_demo && (
              <span style={{ fontSize:9, fontWeight:800, textTransform:"uppercase", padding:"1px 6px",
                borderRadius:99, background:"#FEF3C7", color:"#B45309" }}>Demo</span>
            )}
          </button>
        ))}
      </div>

      {loading && (
        <div style={{ textAlign:"center", padding:"60px 0", color:"#9BA8BF", fontSize:13 }}>
          Loading itinerary…
        </div>
      )}

      {!loading && activeItin && (
        <div style={{ display:"grid", gridTemplateColumns:"1fr 380px", gap:18, alignItems:"start" }}>

          {/* ── LEFT: meta + timeline/findings ── */}
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

            {/* Itinerary meta card */}
            <div style={{ ...card, padding:"18px 22px" }}>
              <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", gap:16,
                flexWrap:"wrap" }}>
                <div>
                  <h2 style={{ fontSize:17, fontWeight:900, color:"#1A2236", margin:"0 0 4px" }}>
                    {activeItin.name}
                  </h2>
                  <p style={{ fontSize:12, color:"#6B7A99", margin:0 }}>{activeItin.destination}</p>
                </div>
                <div style={{ display:"flex", gap:20, flexWrap:"wrap" }}>
                  {[
                    { Icon: Calendar, label:"Dates",    val:`${activeItin.start_date} → ${activeItin.end_date}` },
                    { Icon: Users,    label:"Travelers", val:String(activeItin.travelers) },
                    { Icon: DollarSign, label:"Budget",
                      val:`${activeItin.currency} ${activeItin.budget.toLocaleString()}`,
                      warn: overBudget },
                    { Icon: Clock,    label:"Items",     val:String(items.length) },
                  ].map(({ Icon, label, val, warn }) => (
                    <div key={label} style={{ display:"flex", alignItems:"center", gap:7 }}>
                      <div style={{ width:30, height:30, borderRadius:9, flexShrink:0,
                        background: warn ? "#FFF1F2" : "#F2F5FB",
                        display:"flex", alignItems:"center", justifyContent:"center" }}>
                        <Icon style={{ width:14, height:14, color: warn ? "#EF4444" : "#6B7A99" }} />
                      </div>
                      <div>
                        <p style={{ fontSize:9.5, color:"#9BA8BF", fontWeight:500, margin:0 }}>{label}</p>
                        <p style={{ fontSize:12, fontWeight:700, color: warn ? "#DC2626" : "#1A2236", margin:0 }}>
                          {val}
                          {warn && ` (total: ${activeItin.currency} ${totalCost.toLocaleString()})`}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {activeItin.preferences?.length > 0 && (
                <div style={{ display:"flex", gap:6, marginTop:12, flexWrap:"wrap" }}>
                  {activeItin.preferences.map((p: string) => (
                    <span key={p} style={{ fontSize:11, padding:"2px 10px", borderRadius:999,
                      background:"#F5F3FF", color:"#7C5CFF", border:"1px solid #DDD6FE", fontWeight:500 }}>
                      {p}
                    </span>
                  ))}
                </div>
              )}

              {/* Linked run */}
              {activeItin.linked_run_id && (
                <div style={{ marginTop:12, display:"flex", alignItems:"center", gap:10 }}>
                  <span style={{ fontSize:11, color:"#6B7A99" }}>
                    Linked execution:
                  </span>
                  <Link href={`/investigation?run_id=${activeItin.linked_run_id}`}
                    style={{ fontSize:11, fontFamily:"monospace", fontWeight:700, color:"#3B82F6",
                      textDecoration:"none", display:"flex", alignItems:"center", gap:4 }}>
                    <Search style={{ width:11, height:11 }} />
                    {activeItin.linked_run_id}
                  </Link>
                  <Link href={`/replay?run_id=${activeItin.linked_run_id}`}
                    style={{ fontSize:11, fontFamily:"monospace", fontWeight:700, color:"#7C5CFF",
                      textDecoration:"none", display:"flex", alignItems:"center", gap:4 }}>
                    <RotateCcw style={{ width:11, height:11 }} />
                    Replay
                  </Link>
                </div>
              )}
            </div>

            {/* Tab bar */}
            <div style={{ display:"flex", gap:4, padding:4, background:"#FFFFFF",
              border:"1px solid #E4EAF4", borderRadius:12, width:"fit-content" }}>
              {(["timeline","findings"] as const).map(tab => (
                <button key={tab} onClick={() => setActiveTab(tab)}
                  style={{ padding:"6px 18px", borderRadius:9, border:"none", cursor:"pointer",
                    fontSize:12, fontWeight:600, transition:"all 0.12s",
                    ...(activeTab === tab
                      ? { background:"#3B82F6", color:"white", boxShadow:"0 2px 8px rgba(59,130,246,0.25)" }
                      : { background:"transparent", color:"#6B7A99" }) }}>
                  {tab === "timeline" ? "Itinerary Timeline" : `Findings ${findings.length > 0 ? `(${findings.length})` : ""}`}
                </button>
              ))}
            </div>

            {/* Timeline or findings list */}
            <div style={{ ...card, padding:"20px 22px" }}>
              {activeTab === "timeline" ? (
                <ItineraryTimeline
                  items={items}
                  findings={findings}
                  selectedFindingIdx={selectedFinding}
                  onSelectItem={idx => { setSelectedFinding(idx); setActiveTab("findings"); }}
                />
              ) : findings.length === 0 ? (
                <div style={{ textAlign:"center", padding:"40px 0", color:"#9BA8BF" }}>
                  <CheckCircle2 style={{ width:32, height:32, margin:"0 auto 10px", color:"#22C55E" }} />
                  <p style={{ fontSize:13, margin:0 }}>
                    {valResult ? "No issues found." : "Run validation to see findings."}
                  </p>
                </div>
              ) : (
                <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                  {findings.map((f, i) => {
                    const cfg = SEV_CONFIG[f.severity] || SEV_CONFIG.LOW;
                    const Icon = cfg.icon;
                    return (
                      <div key={i} onClick={() => setSelectedFinding(i)}
                        style={{ display:"flex", alignItems:"flex-start", gap:12,
                          padding:"11px 14px", borderRadius:11, cursor:"pointer",
                          background: selectedFinding === i ? cfg.bg : "#FAFBFD",
                          border:`1px solid ${selectedFinding === i ? cfg.border : "#E4EAF4"}`,
                          transition:"all 0.12s" }}>
                        <div style={{ width:28, height:28, borderRadius:8, flexShrink:0,
                          background:cfg.bg, display:"flex", alignItems:"center", justifyContent:"center",
                          border:`1px solid ${cfg.border}` }}>
                          <Icon style={{ width:13, height:13, color:cfg.color }} />
                        </div>
                        <div style={{ flex:1, minWidth:0 }}>
                          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                            <p style={{ fontSize:12.5, fontWeight:700, color:"#1A2236", margin:0 }}>
                              {f.title}
                            </p>
                            <SevBadge sev={f.severity} />
                          </div>
                          <p style={{ fontSize:11, color:"#6B7A99", margin:"3px 0 0",
                            overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                            {f.actual}
                          </p>
                        </div>
                        <ChevronRight style={{ width:14, height:14, color:"#C8D0E0", flexShrink:0, marginTop:4 }} />
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* ── RIGHT: run validation + results ── */}
          <div style={{ display:"flex", flexDirection:"column", gap:14, position:"sticky", top:24 }}>

            {/* Run button */}
            <button onClick={handleValidate} disabled={validating}
              style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:9,
                padding:"13px 20px", borderRadius:13, border:"none", fontSize:14, fontWeight:800,
                color:"white", cursor: validating ? "not-allowed" : "pointer",
                background: validating ? "#94A3B8" : "#3B82F6",
                boxShadow: validating ? "none" : "0 4px 18px rgba(59,130,246,0.30)",
                transition:"all 0.15s" }}>
              <Play style={{ width:16, height:16 }} />
              {validating ? "Running Validation…" : "Run Validation"}
            </button>

            {/* Summary */}
            {valResult && (
              <div style={{ ...card, padding:"18px 20px", display:"flex", flexDirection:"column", gap:12 }}>
                <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                  <p style={{ fontSize:12, fontWeight:700, color:"#1A2236", margin:0 }}>
                    {afterResult ? "Before vs After" : "Validation Results"}
                  </p>
                  <span style={{ fontSize:10, fontFamily:"monospace", color:"#9BA8BF" }}>
                    {valResult.label}
                  </span>
                </div>
                <SummaryBar
                  summary={afterResult?.summary ?? valResult.summary}
                  before={afterResult ? valResult.summary : undefined}
                  after={afterResult?.summary}
                />
              </div>
            )}

            {/* Findings count by severity */}
            {valResult && !afterResult && (
              <div style={{ ...card, padding:"16px 18px", display:"flex", flexDirection:"column", gap:8 }}>
                <p style={{ fontSize:11, fontWeight:700, color:"#9BA8BF", textTransform:"uppercase",
                  letterSpacing:"0.04em", margin:0 }}>Issues by Severity</p>
                {Object.entries(valResult.summary)
                  .filter(([k]) => k !== "passed" && k !== "total_findings")
                  .map(([sev, count]) => {
                    const key = sev.toUpperCase();
                    const cfg = SEV_CONFIG[key] || SEV_CONFIG.LOW;
                    const val = count as number;
                    if (val === 0) return null;
                    return (
                      <div key={sev} style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                        <SevBadge sev={key} />
                        <span style={{ fontSize:14, fontWeight:900, fontFamily:"monospace",
                          color: cfg.color }}>{val}</span>
                      </div>
                    );
                  })}
              </div>
            )}

            {/* After-fix notice */}
            {afterResult && (
              <div style={{ padding:"12px 16px", borderRadius:12, background:"#F0FDF4",
                border:"1px solid #BBF7D0" }}>
                <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:4 }}>
                  <CheckCircle2 style={{ width:14, height:14, color:"#16A34A" }} />
                  <p style={{ fontSize:12, fontWeight:700, color:"#15803D", margin:0 }}>Fix Applied</p>
                </div>
                <p style={{ fontSize:11, color:"#166534", margin:"0 0 6px" }}>{afterResult.change_applied}</p>
                <button onClick={handleValidate} style={{ fontSize:11, fontWeight:700, color:"#3B82F6",
                  background:"none", border:"none", cursor:"pointer", padding:0, textDecoration:"underline" }}>
                  Re-run full validation →
                </button>
              </div>
            )}

            {/* Hint when no results */}
            {!valResult && !validating && (
              <div style={{ padding:"20px 18px", borderRadius:14, background:"#F8FAFD",
                border:"1px solid #E4EAF4", textAlign:"center" }}>
                <Play style={{ width:28, height:28, color:"#C8D0E0", margin:"0 auto 10px" }} />
                <p style={{ fontSize:12, color:"#9BA8BF", margin:0, lineHeight:1.55 }}>
                  Click <strong style={{ color:"#3B82F6" }}>Run Validation</strong> to detect issues,
                  inconsistencies and budget problems in this itinerary.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Finding detail drawer */}
      {selectedFinding !== null && findings[selectedFinding] && activeItin && (
        <FindingDetail
          finding={findings[selectedFinding]}
          itemIndex={findings[selectedFinding].affected_item_indices[0] ?? 0}
          items={items}
          itineraryId={activeItin.id}
          onClose={() => setSelectedFinding(null)}
          onFixApplied={handleFixApplied}
        />
      )}

      {/* Import modal */}
      {showImport && (
        <ImportModal
          onClose={() => setShowImport(false)}
          onImported={id => { setShowImport(false); loadItinerary(id); }}
        />
      )}
    </div>
  );
}
