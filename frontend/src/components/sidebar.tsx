"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Layers,
  Search,
  RotateCcw,
  GitCompare,
  BarChart3,
  BookOpen,
  Radio,
  ShieldCheck,
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
}

const navItems: NavItem[] = [
  { name: "Overview", href: "/", icon: Activity },
  { name: "Executions", href: "/executions", icon: Layers, badge: "3 Runs" },
  { name: "Investigation", href: "/investigation", icon: Search, badge: "Live" },
  { name: "Replay Lab", href: "/replay", icon: RotateCcw },
  { name: "Comparison", href: "/compare", icon: GitCompare },
  { name: "Evaluation", href: "/evaluation", icon: BarChart3, badge: "Benchmark" },
  { name: "Patterns", href: "/patterns", icon: BookOpen },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 h-screen bg-sidebar border-r border-panel-border flex flex-col justify-between shrink-0 shadow-sm z-30">
      <div>
        {/* SINGLE SIDEBAR BRANDING: Top-left corner logo icon + subtitle exactly once */}
        <div className="p-5 border-b border-panel-border">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary via-intel to-primary flex items-center justify-center text-white shadow-md shadow-primary/20 group-hover:scale-105 transition-transform">
              <Radio className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-black text-lg tracking-wider text-text-primary">BLACKBOX</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-blue-50 text-primary border border-blue-200">v2.1</span>
              </div>
              <p className="text-xs text-text-muted font-medium">AI Agent Flight Recorder</p>
            </div>
          </Link>
        </div>

        {/* Navigation items placed directly below branding */}
        <nav className="p-3 space-y-1">
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
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? "bg-primary text-white shadow-sm shadow-primary/25"
                    : "text-text-muted hover:text-text-primary hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-500"}`} />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                      isActive
                        ? "bg-white/20 text-white"
                        : "bg-slate-100 text-slate-600 border border-slate-200"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Info: Offline & Integrity notice */}
      <div className="p-4 m-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs">
        <div className="flex items-center gap-2 text-emerald-600 font-semibold mb-1">
          <ShieldCheck className="w-4 h-4" />
          <span>Offline Diagnostic Core</span>
        </div>
        <p className="text-[11px] text-text-muted leading-relaxed">
          100% deterministic local rules, statistical z-scores & ML ranker.
        </p>
        <div className="mt-2 pt-2 border-t border-slate-200 flex items-center justify-between text-[10px] text-slate-400 font-mono">
          <span>Synthetic demo data</span>
          <span className="text-emerald-500">● Live</span>
        </div>
      </div>
    </aside>
  );
}
