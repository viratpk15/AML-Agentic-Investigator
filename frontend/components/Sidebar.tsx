"use client";

import React from "react";
import {
  LayoutDashboard,
  Search,
  Receipt,
  ShieldAlert,
  Network,
  BookOpen,
  ShieldCheck,
  FileText,
  UserCheck,
  Layers,
} from "lucide-react";

export type NavTab =
  | "overview"
  | "investigate"
  | "convergence"
  | "transactions"
  | "detection"
  | "profile"
  | "network"
  | "knowledge"
  | "critic"
  | "report";

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  hasReport: boolean;
}

export default function Sidebar({ currentTab, onSelectTab, hasReport }: SidebarProps) {
  const tabs = [
    { id: "overview", label: "Overview & Core", icon: LayoutDashboard },
    { id: "investigate", label: "New Investigation", icon: Search },
    { id: "convergence", label: "Evidence & Review", icon: Layers, badge: hasReport ? "REVIEW" : undefined },
    { id: "transactions", label: "Evidence Ledgers", icon: Receipt },
    { id: "detection", label: "Rules & Anomalies", icon: ShieldAlert },
    { id: "profile", label: "Customer Profile", icon: UserCheck },
    { id: "network", label: "Counterparty Network", icon: Network },
    { id: "knowledge", label: "AML Knowledge RAG", icon: BookOpen },
    { id: "critic", label: "Critic & Self-Audit", icon: ShieldCheck },
    { id: "report", label: "Final Report", icon: FileText, badge: hasReport ? "READY" : undefined },
  ];

  return (
    <aside className="w-64 bg-[#030712]/95 border-r border-white/10 p-4 flex flex-col justify-between shrink-0 h-[calc(100vh-4rem)] sticky top-16">
      <div className="space-y-1">
        <div className="text-[10px] font-mono text-gray-500 uppercase px-3 mb-2 tracking-widest">
          NAVIGATION // WORKSTATION
        </div>

        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = currentTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onSelectTab(tab.id as NavTab)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl font-mono text-xs transition-all ${
                isActive
                  ? "bg-cyan-950/60 text-cyan-300 border border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.2)] font-bold"
                  : "text-gray-400 hover:text-gray-200 hover:bg-surface/50 border border-transparent"
              }`}
            >
              <div className="flex items-center space-x-3">
                <Icon className={`w-4 h-4 ${isActive ? "text-cyan-400" : "text-gray-500"}`} />
                <span>{tab.label}</span>
              </div>
              {tab.badge && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-500/30">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="p-3.5 rounded-xl bg-surface/50 border border-white/5 text-[11px] font-mono text-gray-400">
        <div className="text-gray-300 font-bold text-xs mb-1">Human-In-The-Loop</div>
        Automated compliance signals provide analytical assistance. Final action requires qualified officer review.
      </div>
    </aside>
  );
}
