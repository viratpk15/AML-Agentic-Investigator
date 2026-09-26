"use client";

import React, { useMemo, useState, useEffect, useRef } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  MarkerType,
  Handle,
  Position,
  type ReactFlowInstance,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  User,
  Building2,
  ArrowDownLeft,
  ArrowUpRight,
  Network,
  Maximize2,
  Minimize2,
  RotateCcw,
  ExternalLink,
  ShieldAlert,
  Layers,
  ChevronUp,
  ChevronDown,
  X,
} from "lucide-react";
import { NetworkFindingItem, EvidenceItem } from "@/types";

interface NetworkGraphViewProps {
  customerName: string;
  evidence: EvidenceItem[];
  networkFindings?: NetworkFindingItem[];
  onSelectTransaction?: (transactionId: string) => void;
}

function CustomNode({ data }: { data: any }) {
  const isCustomer = data.isCustomer;
  const isCredit = data.flow === "credit";

  return (
    <div
      className={`px-4 py-3 rounded-2xl border backdrop-blur-xl transition-all shadow-2xl min-w-[200px] max-w-[280px] cursor-pointer group hover:scale-[1.03] ${
        isCustomer
          ? "bg-cyan-950/90 border-cyan-400 text-cyan-200 shadow-[0_0_30px_rgba(6,182,212,0.35)] ring-1 ring-cyan-400/50"
          : isCredit
          ? "bg-[#091522]/90 border-cyan-500/30 text-gray-200 hover:border-cyan-400 hover:shadow-[0_0_20px_rgba(6,182,212,0.25)]"
          : "bg-[#180d24]/90 border-purple-500/30 text-gray-200 hover:border-purple-400 hover:shadow-[0_0_20px_rgba(168,85,247,0.25)]"
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className={`!w-2.5 !h-2.5 !border-2 !border-[#030712] ${
          isCustomer ? "!bg-cyan-400" : isCredit ? "!bg-cyan-400" : "!bg-purple-400"
        }`}
      />

      <div className="flex items-center space-x-3">
        <div
          className={`p-2 rounded-xl shrink-0 ${
            isCustomer
              ? "bg-cyan-500/20 text-cyan-300 ring-1 ring-cyan-400/40"
              : isCredit
              ? "bg-cyan-500/10 text-cyan-400"
              : "bg-purple-500/10 text-purple-400"
          }`}
        >
          {isCustomer ? <User className="w-5 h-5" /> : <Building2 className="w-4 h-4" />}
        </div>
        <div className="overflow-hidden min-w-0">
          <div className="text-xs font-bold font-mono truncate text-white group-hover:text-cyan-300 transition-colors">
            {data.label}
          </div>
          <div className="text-[10px] font-mono text-gray-400 uppercase tracking-wider flex items-center space-x-1">
            <span>{data.role || "Entity"}</span>
          </div>
        </div>
      </div>

      {data.amount !== undefined && (
        <div className="mt-2.5 pt-2 border-t border-white/10 flex items-center justify-between text-xs font-mono">
          <span className="text-[10px] text-gray-400 uppercase">
            {isCredit ? "Total Remitted" : "Total Received"}
          </span>
          <span
            className={`font-bold ${
              isCredit ? "text-cyan-300" : "text-purple-300"
            }`}
          >
            ₹{Number(data.amount).toLocaleString("en-IN", { minimumFractionDigits: 0 })}
          </span>
        </div>
      )}

      {data.txnCount !== undefined && (
        <div className="mt-1 flex items-center justify-between text-[10px] font-mono text-gray-500">
          <span>Transactions:</span>
          <span className="text-gray-300 font-semibold">{data.txnCount}</span>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className={`!w-2.5 !h-2.5 !border-2 !border-[#030712] ${
          isCustomer ? "!bg-purple-400" : isCredit ? "!bg-cyan-400" : "!bg-purple-400"
        }`}
      />
    </div>
  );
}

const nodeTypes = {
  custom: CustomNode,
};

export default function NetworkGraphView({
  customerName,
  evidence = [],
  networkFindings = [],
  onSelectTransaction,
}: NetworkGraphViewProps) {
  const [selectedEntity, setSelectedEntity] = useState<any>(null);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [flowFilter, setFlowFilter] = useState<"all" | "credit" | "debit">("all");
  const [showPatternsInFullscreen, setShowPatternsInFullscreen] = useState<boolean>(false);
  const rfInstanceRef = useRef<ReactFlowInstance | null>(null);

  // Keyboard shortcut: Press Escape to exit fullscreen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFullscreen]);

  // Auto recenter and fit view whenever fullscreen toggles or filter changes
  useEffect(() => {
    const timer = setTimeout(() => {
      if (rfInstanceRef.current) {
        rfInstanceRef.current.fitView({ padding: 0.18, duration: 400 });
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [isFullscreen, flowFilter]);

  // Aggregate counterparties & build graph deterministically
  const { initialNodes, initialEdges, totalCreditVolume, totalDebitVolume, creditCount, debitCount } =
    useMemo(() => {
      const counterpartiesMap = new Map<
        string,
        { totalAmount: number; flow: string; txns: string[] }
      >();

      let credVol = 0;
      let debVol = 0;

      evidence.forEach((ev) => {
        const cp = (ev.counterparty || "Unspecified Counterparty").trim();
        const flow = (ev.flow_type || "credit").toLowerCase();
        const amt = Number(ev.amount) || 0;

        if (flow === "credit") {
          credVol += amt;
        } else {
          debVol += amt;
        }

        if (!counterpartiesMap.has(cp)) {
          counterpartiesMap.set(cp, {
            totalAmount: 0,
            flow,
            txns: [],
          });
        }
        const item = counterpartiesMap.get(cp)!;
        item.totalAmount += amt;
        if (ev.transaction_id && !item.txns.includes(ev.transaction_id)) {
          item.txns.push(ev.transaction_id);
        }
      });

      // Filter counterparties if filter active
      const entries = Array.from(counterpartiesMap.entries()).filter(([_, info]) => {
        if (flowFilter === "credit") return info.flow === "credit";
        if (flowFilter === "debit") return info.flow === "debit";
        return true;
      });

      const credits = entries.filter(([_, info]) => info.flow === "credit");
      const debits = entries.filter(([_, info]) => info.flow === "debit");

      const nodes: Node[] = [];
      const edges: Edge[] = [];

      const maxCount = Math.max(credits.length, debits.length, 1);
      const rowSpacing = 135;
      const totalGraphHeight = Math.max(500, maxCount * rowSpacing);
      const centerY = Math.max(220, totalGraphHeight / 2 - 40);

      // Central Primary Customer Hub Node
      nodes.push({
        id: "customer",
        type: "custom",
        position: { x: 500, y: centerY },
        data: {
          label: customerName || "Customer Account",
          isCustomer: true,
          role: "Primary Account Holder",
          amount: credVol + debVol,
          txnCount: evidence.length,
        },
      });

      // Left Nodes: Incoming Credits
      credits.forEach(([cp, info], index) => {
        const nodeId = `cp-${cp.replace(/[^a-zA-Z0-9]/g, "_")}`;
        const yPos = 40 + index * rowSpacing;

        nodes.push({
          id: nodeId,
          type: "custom",
          position: { x: 60, y: yPos },
          data: {
            label: cp,
            isCustomer: false,
            flow: "credit",
            role: "Incoming Remitter",
            amount: info.totalAmount,
            txnCount: info.txns.length,
            txns: info.txns,
          },
        });

        // Directed Edge: Remitter -> Customer
        const formattedK =
          info.totalAmount >= 100000
            ? `₹${(info.totalAmount / 100000).toFixed(2)}L`
            : `₹${(info.totalAmount / 1000).toFixed(0)}K`;

        edges.push({
          id: `e-${nodeId}-to-customer`,
          source: nodeId,
          target: "customer",
          animated: true,
          label: formattedK,
          labelStyle: { fill: "#38bdf8", fontWeight: 700, fontSize: 11, fontFamily: "monospace" },
          labelBgStyle: { fill: "#030712", fillOpacity: 0.95, stroke: "#06b6d4", strokeWidth: 1 },
          style: {
            stroke: "#06b6d4",
            strokeWidth: 2.2,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: "#06b6d4",
          },
        });
      });

      // Right Nodes: Outgoing Debits
      debits.forEach(([cp, info], index) => {
        const nodeId = `cp-${cp.replace(/[^a-zA-Z0-9]/g, "_")}`;
        const yPos = 40 + index * rowSpacing;

        nodes.push({
          id: nodeId,
          type: "custom",
          position: { x: 940, y: yPos },
          data: {
            label: cp,
            isCustomer: false,
            flow: "debit",
            role: "Outgoing Beneficiary",
            amount: info.totalAmount,
            txnCount: info.txns.length,
            txns: info.txns,
          },
        });

        // Directed Edge: Customer -> Beneficiary
        const formattedK =
          info.totalAmount >= 100000
            ? `₹${(info.totalAmount / 100000).toFixed(2)}L`
            : `₹${(info.totalAmount / 1000).toFixed(0)}K`;

        edges.push({
          id: `e-customer-to-${nodeId}`,
          source: "customer",
          target: nodeId,
          animated: true,
          label: formattedK,
          labelStyle: { fill: "#c084fc", fontWeight: 700, fontSize: 11, fontFamily: "monospace" },
          labelBgStyle: { fill: "#030712", fillOpacity: 0.95, stroke: "#a855f7", strokeWidth: 1 },
          style: {
            stroke: "#a855f7",
            strokeWidth: 2.2,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: "#a855f7",
          },
        });
      });

      return {
        initialNodes: nodes,
        initialEdges: edges,
        totalCreditVolume: credVol,
        totalDebitVolume: debVol,
        creditCount: credits.length,
        debitCount: debits.length,
      };
    }, [customerName, evidence, flowFilter]);

  const handleFitView = () => {
    if (rfInstanceRef.current) {
      rfInstanceRef.current.fitView({ padding: 0.18, duration: 400 });
    }
  };

  const containerClasses = isFullscreen
    ? "fixed inset-0 z-[100] w-screen h-screen bg-[#030712] p-5 flex flex-col overflow-hidden"
    : "w-full bg-[#0b0f19]/80 backdrop-blur-xl rounded-2xl border border-white/10 p-5 shadow-2xl relative space-y-4";

  return (
    <div className={containerClasses}>
      {/* Top Header Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-white/10 shrink-0">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 ring-1 ring-cyan-500/20">
            <Network className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold tracking-wider text-white uppercase font-mono">
                Directed Counterparty Network Simulation
              </h3>
              {isFullscreen && (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 animate-pulse">
                  FULLSCREEN SIMULATION MODE
                </span>
              )}
            </div>
            <div className="text-[11px] font-mono text-gray-400 mt-0.5 flex flex-wrap items-center gap-x-3">
              <span>
                Total Entities: <strong className="text-white">{creditCount + debitCount}</strong> ({creditCount} Incoming, {debitCount} Outgoing)
              </span>
              <span>•</span>
              <span className="text-cyan-400 font-semibold">
                Inflow: ₹{totalCreditVolume.toLocaleString("en-IN", { minimumFractionDigits: 0 })}
              </span>
              <span>•</span>
              <span className="text-purple-400 font-semibold">
                Outflow: ₹{totalDebitVolume.toLocaleString("en-IN", { minimumFractionDigits: 0 })}
              </span>
            </div>
          </div>
        </div>

        {/* Controls, Filters & Fullscreen Action */}
        <div className="flex items-center space-x-2.5">
          {/* Flow Filter */}
          <div className="flex rounded-xl bg-black/50 p-1 border border-white/10 text-xs font-mono">
            <button
              onClick={() => setFlowFilter("all")}
              className={`px-3 py-1 rounded-lg transition-all ${
                flowFilter === "all"
                  ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              All Flows
            </button>
            <button
              onClick={() => setFlowFilter("credit")}
              className={`px-3 py-1 rounded-lg flex items-center space-x-1 transition-all ${
                flowFilter === "credit"
                  ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30"
                  : "text-gray-400 hover:text-cyan-400"
              }`}
            >
              <ArrowDownLeft className="w-3 h-3" />
              <span>Credits ({creditCount})</span>
            </button>
            <button
              onClick={() => setFlowFilter("debit")}
              className={`px-3 py-1 rounded-lg flex items-center space-x-1 transition-all ${
                flowFilter === "debit"
                  ? "bg-purple-500/20 text-purple-300 font-bold border border-purple-500/30"
                  : "text-gray-400 hover:text-purple-400"
              }`}
            >
              <ArrowUpRight className="w-3 h-3" />
              <span>Debits ({debitCount})</span>
            </button>
          </div>

          {/* Re-center / Fit View Button */}
          <button
            onClick={handleFitView}
            title="Auto-Center / Fit Topology in Canvas"
            className="p-2 rounded-xl bg-surface hover:bg-surface/80 border border-white/10 text-gray-300 hover:text-white transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Fullscreen Toggle Button */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className={`px-3.5 py-1.5 rounded-xl font-mono text-xs font-bold flex items-center space-x-2 transition-all ${
              isFullscreen
                ? "bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-300 shadow-glow"
                : "bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 text-cyan-300 shadow-glow"
            }`}
          >
            {isFullscreen ? (
              <>
                <Minimize2 className="w-4 h-4" />
                <span>Exit Fullscreen (ESC)</span>
              </>
            ) : (
              <>
                <Maximize2 className="w-4 h-4" />
                <span>Fullscreen Simulation</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Graph Simulation Canvas */}
      <div
        className={`w-full rounded-2xl overflow-hidden bg-[#030712] border border-cyan-500/20 relative shadow-2xl ${
          isFullscreen ? "flex-1 min-h-0" : "h-[720px] min-h-[620px]"
        }`}
      >
        <ReactFlow
          nodes={initialNodes}
          edges={initialEdges}
          nodeTypes={nodeTypes}
          onInit={(instance) => {
            rfInstanceRef.current = instance;
            instance.fitView({ padding: 0.18 });
          }}
          onNodeClick={(_, node) => setSelectedEntity(node.data)}
          fitView
          minZoom={0.2}
          maxZoom={2.5}
        >
          <Background color="#0f172a" gap={20} size={1} />
          <Controls className="!bg-[#091122]/95 !border-white/10 !fill-gray-300 !rounded-xl !shadow-2xl" />
          <MiniMap
            nodeStrokeWidth={3}
            zoomable
            pannable
            className="!bg-[#091122]/90 !border-white/10 !rounded-xl hidden md:block"
            nodeColor={(node) => {
              if (node.id === "customer") return "#06b6d4";
              if (node.data?.flow === "credit") return "#06b6d4";
              return "#a855f7";
            }}
          />
        </ReactFlow>

        {/* Selected Entity Inspector Floating Drawer */}
        {selectedEntity && (
          <div className="absolute top-4 right-4 z-20 w-80 bg-[#091122]/95 backdrop-blur-xl border border-cyan-500/40 rounded-2xl p-4 shadow-2xl animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="flex items-center justify-between pb-2 border-b border-white/10 mb-3">
              <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider flex items-center space-x-1.5">
                <Building2 className="w-3.5 h-3.5" />
                <span>Entity Inspector</span>
              </span>
              <button
                onClick={() => setSelectedEntity(null)}
                className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-sm font-bold text-white mb-1 font-mono">{selectedEntity.label}</div>
            <div className="text-xs text-gray-400 font-mono mb-3">{selectedEntity.role}</div>

            {selectedEntity.amount !== undefined && (
              <div className="p-3 rounded-xl bg-black/40 border border-white/5 space-y-1 mb-3 font-mono">
                <span className="text-[10px] text-gray-400 block uppercase">Total Aggregated Volume</span>
                <span className="text-base font-bold text-emerald-400">
                  ₹{Number(selectedEntity.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                </span>
              </div>
            )}

            {selectedEntity.txns && selectedEntity.txns.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-[11px] font-mono text-gray-400">
                  <span>Linked Transactions:</span>
                  <span className="text-cyan-300 font-bold">{selectedEntity.txns.length}</span>
                </div>
                <div className="max-h-36 overflow-y-auto space-y-1 pr-1 font-mono">
                  {selectedEntity.txns.map((tid: string) => (
                    <button
                      key={tid}
                      onClick={() => onSelectTransaction && onSelectTransaction(tid)}
                      className="w-full px-2.5 py-1.5 rounded-lg bg-surface hover:bg-surface/80 border border-white/5 hover:border-cyan-500/30 text-left text-xs text-gray-200 hover:text-cyan-300 flex items-center justify-between transition-colors group"
                    >
                      <span className="font-bold">{tid}</span>
                      <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 text-cyan-400" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Fullscreen Overlay Bottom Bar Toggle for Topological Patterns */}
        {isFullscreen && networkFindings.length > 0 && (
          <div className="absolute bottom-4 left-4 z-20">
            <button
              onClick={() => setShowPatternsInFullscreen(!showPatternsInFullscreen)}
              className="px-3.5 py-2 rounded-xl bg-[#091122]/95 backdrop-blur-md border border-cyan-500/30 text-xs font-mono font-bold text-cyan-300 hover:bg-[#091122] flex items-center space-x-2 shadow-2xl transition-all"
            >
              <ShieldAlert className="w-4 h-4 text-cyan-400" />
              <span>Observable Topological Patterns ({networkFindings.length})</span>
              {showPatternsInFullscreen ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronUp className="w-4 h-4" />
              )}
            </button>

            {showPatternsInFullscreen && (
              <div className="mt-2 w-[420px] max-h-72 overflow-y-auto p-3 rounded-2xl bg-[#091122]/95 backdrop-blur-xl border border-cyan-500/30 shadow-2xl space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-200">
                {networkFindings.map((pat, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-xl bg-surface/60 border border-white/5 text-xs text-gray-300"
                  >
                    <div className="font-bold text-cyan-300 uppercase font-mono text-[11px] mb-1">
                      {pat.pattern_name.replace(/_/g, " ")}
                    </div>
                    <div className="text-gray-400 text-[11px] leading-relaxed">{pat.description}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Identified Observable Patterns (Standard Mode) */}
      {!isFullscreen && networkFindings.length > 0 && (
        <div className="pt-2">
          <div className="text-xs font-mono font-bold text-gray-400 mb-2.5 flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-cyan-400" />
            <span>OBSERVABLE TOPOLOGICAL PATTERNS IDENTIFIED:</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {networkFindings.map((pat, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl bg-surface/60 border border-white/10 text-xs text-gray-300 hover:border-cyan-500/30 transition-colors"
              >
                <div className="font-bold font-mono text-cyan-300 text-xs mb-1">
                  {pat.pattern_name.replace(/_/g, " ").toUpperCase()}
                </div>
                <div className="text-gray-400 text-xs leading-relaxed">{pat.description}</div>
                {pat.involved_nodes && pat.involved_nodes.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {pat.involved_nodes.map((node, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded text-[9px] font-mono bg-black/40 border border-white/5 text-gray-300"
                      >
                        {node}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
