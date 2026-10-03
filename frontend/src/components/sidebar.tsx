"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Layers,
  Search,
  RotateCcw,
  GitCompare,
  BarChart3,
  BookOpen,
  Crosshair,
  Map,
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
}

const navItems: NavItem[] = [
  { name: "Overview",        href: "/",                icon: LayoutDashboard },
  { name: "Executions",      href: "/executions",      icon: Layers },
  { name: "Investigation",   href: "/investigation",   icon: Search },
  { name: "Replay Lab",      href: "/replay",          icon: RotateCcw },
  { name: "Comparison",      href: "/compare",         icon: GitCompare },
  { name: "Evaluation",      href: "/evaluation",      icon: BarChart3 },
  { name: "Patterns",        href: "/patterns",        icon: BookOpen },
  { name: "Itinerary Lab",   href: "/itinerary-lab",   icon: Map },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="w-56 h-screen flex flex-col shrink-0 z-30"
      style={{ background: "#F0F4FA", borderRight: "1px solid #DDE3EE" }}
    >
      {/* ── Logo ── */}
      <div className="px-5 pt-6 pb-5">
        <Link href="/" className="flex items-center gap-3 group">
          {/* Donut-style logo icon matching reference */}
          <div className="relative w-10 h-10 shrink-0">
            <svg viewBox="0 0 40 40" className="w-10 h-10 drop-shadow-md">
              <circle cx="20" cy="20" r="18" fill="#EEF2F7" />
              {/* Donut segments — blue/violet/amber like reference center node */}
              <circle cx="20" cy="20" r="14" fill="none" stroke="#3B82F6" strokeWidth="5"
                strokeDasharray="22 66" strokeDashoffset="0" />
              <circle cx="20" cy="20" r="14" fill="none" stroke="#7C5CFF" strokeWidth="5"
                strokeDasharray="18 70" strokeDashoffset="-22" />
              <circle cx="20" cy="20" r="14" fill="none" stroke="#F59E0B" strokeWidth="5"
                strokeDasharray="14 74" strokeDashoffset="-40" />
              <circle cx="20" cy="20" r="14" fill="none" stroke="#22C55E" strokeWidth="5"
                strokeDasharray="14 74" strokeDashoffset="-54" />
              <circle cx="20" cy="20" r="8" fill="#F0F4FA" />
            </svg>
          </div>
          <div>
            <div className="font-black text-base tracking-tight" style={{ color: "#1A2236" }}>
              BLACKBOX
            </div>
            <div className="text-xs font-medium" style={{ color: "#6B7A99" }}>
              AI Agent Flight Recorder
            </div>
          </div>
        </Link>
      </div>

      {/* ── Nav items ── */}
      <nav className="flex-1 px-3 space-y-0.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                isActive
                  ? "bg-white text-primary shadow-sm font-semibold"
                  : "text-text-muted hover:bg-white/60 hover:text-text-primary"
              }`}
              style={
                isActive
                  ? { color: "#3B82F6", background: "#FFFFFF", boxShadow: "0 1px 6px rgba(26,34,54,0.07)" }
                  : {}
              }
            >
              <Icon
                className="w-[18px] h-[18px] shrink-0"
                style={{ color: isActive ? "#3B82F6" : "#6B7A99" }}
              />
              <span style={{ color: isActive ? "#3B82F6" : "#6B7A99" }}>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* ── Bottom status ── */}
      <div className="px-5 pb-6 pt-4 border-t" style={{ borderColor: "#DDE3EE" }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-sm font-semibold" style={{ color: "#22C55E" }}>
              Operational
            </span>
          </div>
          <Crosshair className="w-5 h-5" style={{ color: "#22C55E" }} />
        </div>
        <p className="text-xs mt-1.5 leading-relaxed" style={{ color: "#9BA8BF" }}>
          Offline · Deterministic Core
        </p>
      </div>
    </aside>
  );
}
