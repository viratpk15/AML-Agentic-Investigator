"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  BrainCircuit,
  Wrench,
  FileCheck2,
  ShieldAlert,
  RotateCcw,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  AlertTriangle,
} from "lucide-react";
import { EngineState } from "@/types";

interface LangGraphVisualizerProps {
  engineState: EngineState;
  activeNode?: string | null;
  activeTool?: string | null;
  revisionCount?: number;
  criticPassed?: boolean;
  criticIssues?: string[];
}

export default function LangGraphVisualizer({
  engineState,
  activeNode,
  activeTool,
  revisionCount = 0,
  criticPassed = true,
  criticIssues = [],
}: LangGraphVisualizerProps) {
  const isAgentActive = activeNode === "investigator" || engineState === "ANALYZING";
  const isToolActive =
    activeNode === "tools" ||
    engineState === "TOOL_EXECUTION" ||
    engineState === "RAG_RETRIEVAL";
  const isSynthesisActive = activeNode === "synthesis" || engineState === "SYNTHESIS";
  const isCriticActive = activeNode === "critic" || engineState === "CRITIC";
  const isRevisionActive = activeNode === "revision" || engineState === "REVISION";
  const isComplete = activeNode === "report" || engineState === "COMPLETE";

  const nodes = [
    {
      id: "investigator",
      title: "Investigator Node",
      role: "Reasoning & Planning",
      icon: BrainCircuit,
      active: isAgentActive,
      done: isToolActive || isSynthesisActive || isCriticActive || isComplete,
      color: "from-cyan-500/20 to-blue-500/20 border-cyan-500/40 text-cyan-400",
      activeBorder: "border-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.4)]",
    },
    {
      id: "tools",
      title: "Tool Node",
      role: isToolActive && activeTool ? activeTool : "Deterministic Tools & RAG",
      icon: Wrench,
      active: isToolActive,
      done: isSynthesisActive || isCriticActive || isComplete,
      color: "from-amber-500/20 to-orange-500/20 border-amber-500/40 text-amber-400",
      activeBorder: "border-amber-400 shadow-[0_0_20px_rgba(245,158,11,0.4)]",
    },
    {
      id: "synthesis",
      title: "Synthesis Node",
      role: "Evidence Structuring",
      icon: Sparkles,
      active: isSynthesisActive,
      done: isCriticActive || isComplete,
      color: "from-blue-500/20 to-indigo-500/20 border-blue-500/40 text-blue-400",
      activeBorder: "border-blue-400 shadow-[0_0_20px_rgba(59,130,246,0.4)]",
    },
    {
      id: "critic",
      title: "Critic Node",
      role: !criticPassed ? "Discrepancies Flagged" : "Adversarial Factual Audit",
      icon: !criticPassed ? AlertTriangle : ShieldAlert,
      active: isCriticActive,
      done: isComplete && criticPassed,
      color: !criticPassed
        ? "from-rose-500/20 to-amber-500/20 border-rose-500/40 text-rose-400"
        : "from-purple-500/20 to-pink-500/20 border-purple-500/40 text-purple-400",
      activeBorder: !criticPassed
        ? "border-rose-400 shadow-[0_0_20px_rgba(244,63,94,0.4)]"
        : "border-purple-400 shadow-[0_0_20px_rgba(168,85,247,0.4)]",
    },
    {
      id: "report",
      title: "Final Report",
      role: "Verified Compliance Artifact",
      icon: FileCheck2,
      active: isComplete,
      done: isComplete,
      color: "from-emerald-500/20 to-teal-500/20 border-emerald-500/40 text-emerald-400",
      activeBorder: "border-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.4)]",
    },
  ];

  return (
    <div className="w-full bg-[#0b0f19]/80 backdrop-blur-xl rounded-2xl border border-white/10 p-5 shadow-2xl relative overflow-hidden">
      {/* HUD Header */}
      <div className="flex items-center justify-between mb-6 pb-3 border-b border-white/10">
        <div className="flex items-center space-x-2">
          <BrainCircuit className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-semibold tracking-wider text-gray-200 uppercase font-mono">
            LangGraph Execution Topology
          </h3>
        </div>
        <div className="flex items-center space-x-3 text-xs font-mono">
          {revisionCount > 0 && (
            <span className="flex items-center space-x-1 text-purple-300 bg-purple-950/60 px-2.5 py-1 rounded-full border border-purple-500/30">
              <RotateCcw className="w-3.5 h-3.5 animate-spin" />
              <span>Revision {revisionCount} Active</span>
            </span>
          )}
          <span className="text-gray-400">
            Node: <span className="text-cyan-400">{activeNode || engineState}</span>
          </span>
        </div>
      </div>

      {/* Main Graph Node Flow */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 relative">
        {nodes.map((node, index) => {
          const Icon = node.icon;
          return (
            <div key={node.id} className="relative flex flex-col items-center">
              <motion.div
                animate={{
                  scale: node.active ? 1.04 : 1,
                  borderColor: node.active
                    ? "rgba(6, 182, 212, 0.8)"
                    : "rgba(255, 255, 255, 0.1)",
                }}
                transition={{ duration: 0.3 }}
                className={`w-full p-4 rounded-xl border bg-gradient-to-b ${node.color} ${
                  node.active ? node.activeBorder : ""
                } transition-all duration-300 relative group cursor-pointer`}
              >
                {/* Active Indicator Pulse */}
                {node.active && (
                  <span className="absolute -top-1 -right-1 flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500"></span>
                  </span>
                )}

                <div className="flex items-center space-x-3 mb-2">
                  <div className="p-2 rounded-lg bg-black/40 border border-white/5">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-gray-100">{node.title}</h4>
                    <p className="text-[10px] text-gray-400 font-mono truncate max-w-[120px]">
                      {node.role}
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[10px] font-mono text-gray-400 pt-2 border-t border-white/5">
                  <span>Step 0{index + 1}</span>
                  {node.done ? (
                    <span className="flex items-center space-x-1 text-emerald-400">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Done</span>
                    </span>
                  ) : node.active ? (
                    <span className="text-cyan-400 animate-pulse font-semibold">
                      Running...
                    </span>
                  ) : (
                    <span className="text-gray-500">Standby</span>
                  )}
                </div>
              </motion.div>

              {/* Connecting arrow for larger screens */}
              {index < nodes.length - 1 && (
                <div className="hidden md:block absolute -right-2 top-1/2 -translate-y-1/2 z-10 text-gray-600">
                  <ArrowRight className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Revision Feedback Loop Indicator */}
      <motion.div
        animate={{ opacity: isRevisionActive || revisionCount > 0 ? 1 : 0.4 }}
        className={`mt-5 p-3 rounded-xl border flex items-center justify-between text-xs transition-all ${
          isRevisionActive
            ? "border-purple-500/50 bg-purple-950/40 shadow-[0_0_15px_rgba(168,85,247,0.2)]"
            : "border-purple-500/20 bg-purple-950/20"
        }`}
      >
        <div className="flex items-center space-x-2 text-purple-300 font-mono">
          <RotateCcw
            className={`w-4 h-4 ${isRevisionActive ? "animate-spin text-purple-400" : ""}`}
          />
          <span className="font-semibold">Self-Correction Feedback Loop:</span>
          <span className="text-gray-400">
            Critic FAIL ──► Structured Feedback ──► Investigator Revision
          </span>
        </div>
        <div className="font-mono text-[11px] text-purple-400">
          Guardrail: {revisionCount}/2 Revisions Used
        </div>
      </motion.div>
    </div>
  );
}
