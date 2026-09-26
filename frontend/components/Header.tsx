"use client";

import React from "react";
import { Shield, Sparkles, Terminal, Activity, History } from "lucide-react";

interface HeaderProps {
  isDemoMode: boolean;
  onToggleDemoMode: () => void;
  onOpenHistory?: () => void;
  caseId?: string;
  isBackendOnline?: boolean;
}

export default function Header({
  isDemoMode,
  onToggleDemoMode,
  onOpenHistory,
  caseId = "CASE #AML-2026-001",
  isBackendOnline = true,
}: HeaderProps) {
  return (
    <header className="w-full h-16 bg-[#030712]/90 border-b border-white/10 backdrop-blur-xl px-6 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.3)]">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-black tracking-widest text-white font-mono">
                AML // INTELLIGENCE CORE
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/30 text-cyan-300">
                v0.1.0
              </span>
            </div>
            <div className="text-[10px] font-mono text-gray-400">
              AI FINANCIAL INVESTIGATION COMMAND CENTER
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {/* Backend Status indicator */}
        <div className="hidden sm:flex items-center space-x-2 font-mono text-xs px-3 py-1 rounded-full bg-surface border border-white/10">
          <span
            className={`w-2 h-2 rounded-full ${
              isBackendOnline ? "bg-emerald-400 shadow-[0_0_8px_#34d399]" : "bg-rose-400"
            }`}
          />
          <span className="text-gray-300">
            {isBackendOnline ? "FASTAPI // ONLINE" : "BACKEND // OFFLINE"}
          </span>
        </div>

        {/* Case ID badge */}
        <div className="hidden md:flex items-center space-x-1.5 font-mono text-xs text-gray-400 bg-surface/50 border border-white/5 px-3 py-1 rounded-lg">
          <Terminal className="w-3.5 h-3.5 text-cyan-400" />
          <span>{caseId}</span>
        </div>

        {/* History Button */}
        {onOpenHistory && (
          <button
            onClick={onOpenHistory}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-white/10 bg-surface hover:bg-surface/80 text-gray-300 font-mono text-xs transition-all"
            title="View Investigation History"
          >
            <History className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">HISTORY</span>
          </button>
        )}

        {/* Demo Mode Toggle */}
        <button
          onClick={onToggleDemoMode}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border font-mono text-xs transition-all ${
            isDemoMode
              ? "bg-purple-950/60 border-purple-500/50 text-purple-300 shadow-[0_0_15px_rgba(168,85,247,0.3)]"
              : "bg-gradient-to-r from-cyan-500/20 to-purple-500/20 hover:from-cyan-500/30 hover:to-purple-500/30 border-cyan-500/40 text-cyan-300"
          }`}
        >
          <Sparkles className={`w-3.5 h-3.5 ${isDemoMode ? "text-purple-400 animate-spin" : "text-cyan-400"}`} />
          <span>{isDemoMode ? "DEMO ACTIVE (54 TXNS)" : "RUN AML DEMO"}</span>
        </button>
      </div>
    </header>
  );
}
