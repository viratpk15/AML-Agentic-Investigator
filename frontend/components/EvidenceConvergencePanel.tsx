"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  AlertTriangle,
  ArrowDownLeft,
  ArrowUpRight,
  Search,
  ExternalLink,
  Layers,
  CheckCircle,
} from "lucide-react";
import { EvidenceConvergenceItem, HumanReviewItem, InvestigationReport } from "@/types";

interface EvidenceConvergencePanelProps {
  report: InvestigationReport | null;
  onSelectTransaction: (transactionId: string) => void;
}

export default function EvidenceConvergencePanel({
  report,
  onSelectTransaction,
}: EvidenceConvergencePanelProps) {
  const [highExpanded, setHighExpanded] = useState<boolean>(true);
  const [mediumExpanded, setMediumExpanded] = useState<boolean>(false);
  const [lowExpanded, setLowExpanded] = useState<boolean>(false);
  const [searchFilter, setSearchFilter] = useState<string>("");

  if (!report) {
    return (
      <div className="p-12 text-center bg-surface/50 border border-white/5 rounded-2xl text-gray-500 font-mono text-xs">
        No active investigation report. Run an investigation or open Demo Mode to explore multi-domain evidence convergence.
      </div>
    );
  }

  // Top convergence items (Top 7)
  const topConvergence = (report.evidence_convergence || []).slice(0, 7);

  // Group all human review items by priority
  const allItems: HumanReviewItem[] = report.human_review_items || [];
  const highItems = allItems.filter((i) => i.priority === "HIGH");
  const mediumItems = allItems.filter((i) => i.priority === "MEDIUM");
  const lowItems = allItems.filter((i) => i.priority === "LOW");

  const filterMatches = (item: HumanReviewItem | EvidenceConvergenceItem) => {
    if (!searchFilter.trim()) return true;
    const q = searchFilter.toLowerCase();
    const matchesId = item.transaction_id ? item.transaction_id.toLowerCase().includes(q) : false;
    const matchesCp = item.counterparty ? item.counterparty.toLowerCase().includes(q) : false;
    const matchesReasons = Array.isArray(item.reasons)
      ? item.reasons.some((r) => typeof r === "string" && r.toLowerCase().includes(q))
      : false;
    return matchesId || matchesCp || matchesReasons;
  };

  const formatAmount = (amt: number | null | undefined): string => {
    if (amt === null || amt === undefined || isNaN(Number(amt))) return "N/A";
    return `₹${Number(amt).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
  };

  const getFlowDirection = (item: { flow_type?: string | null; direction?: string | null }): string => {
    return (item.flow_type || item.direction || "debit").toLowerCase();
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-5 rounded-2xl bg-surface/80 border border-white/10 backdrop-blur-md">
        <div>
          <div className="flex items-center space-x-2 text-[11px] font-mono text-cyan-400 uppercase tracking-wider">
            <Layers className="w-3.5 h-3.5" />
            <span>Multi-Domain Evidence Convergence & Review Prioritization</span>
          </div>
          <h3 className="text-xl font-black text-white mt-1">
            Prioritized Compliance Review Queue
          </h3>
          <p className="text-xs text-gray-400 font-mono mt-0.5">
            Total Analyzed: {report.total_transactions_analyzed || report.observed_evidence.length} | Prioritized Review Items: {allItems.length} ({highItems.length} HIGH, {mediumItems.length} MEDIUM, {lowItems.length} LOW)
          </p>
        </div>

        {/* Search / Filter */}
        <div className="relative w-full md:w-64">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Filter transactions, counterparties..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-black/40 border border-white/10 text-xs font-mono text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>

      {/* TOP PRIORITY CONVERGENCE SECTION */}
      {topConvergence.length > 0 && !searchFilter && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-rose-400 flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4" />
              <span>Priority Review: Top {topConvergence.length} High-Convergence Items</span>
            </h4>
            <span className="text-[11px] font-mono text-gray-500">
              Ranked by multi-domain signal overlap
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {topConvergence.map((item) => {
              const flow = getFlowDirection(item);
              const isCredit = flow === "credit";
              const rawFlowLabel = item.flow_type || item.direction || (isCredit ? "CREDIT" : "DEBIT");

              return (
                <div
                  key={item.transaction_id}
                  onClick={() => onSelectTransaction(item.transaction_id)}
                  className="p-4 rounded-xl bg-surface/90 hover:bg-surface border border-rose-500/30 hover:border-rose-500/60 shadow-lg cursor-pointer transition-all hover:scale-[1.01] group space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-black text-sm text-white group-hover:text-cyan-300 transition-colors">
                        {item.transaction_id}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                        {item.priority || "HIGH"}
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-gray-400 flex items-center space-x-1">
                      <span>{item.date || "N/A"}</span>
                      <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity text-cyan-400 ml-1" />
                    </div>
                  </div>

                  <div className="flex items-baseline justify-between font-mono">
                    <div className="text-base font-bold text-white">
                      {formatAmount(item.amount)}
                    </div>
                    <span
                      className={`text-[10px] font-bold uppercase flex items-center space-x-1 ${
                        isCredit ? "text-emerald-400" : "text-rose-400"
                      }`}
                    >
                      {isCredit ? (
                        <ArrowDownLeft className="w-3 h-3 inline" />
                      ) : (
                        <ArrowUpRight className="w-3 h-3 inline" />
                      )}
                      <span>{rawFlowLabel}</span>
                    </span>
                  </div>

                  <div className="text-xs text-cyan-300 font-mono font-semibold truncate">
                    {item.counterparty || "Unspecified Counterparty"}
                  </div>

                  {/* Signal Domain Badges */}
                  <div className="flex flex-wrap gap-1 pt-1">
                    {(item.signal_domains || []).map((dom, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded text-[9px] font-mono font-semibold bg-white/5 border border-white/10 text-gray-300"
                      >
                        {dom}
                      </span>
                    ))}
                  </div>

                  <p className="text-[11px] text-gray-400 line-clamp-2 leading-relaxed">
                    {item.convergence_summary || "Multi-signal convergence flagged for compliance review."}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* EXPANDABLE HUMAN REVIEW QUEUES */}
      <div className="space-y-4">
        {/* HIGH PRIORITY ACCORDION */}
        <div className="rounded-xl border border-rose-500/30 bg-surface/60 overflow-hidden shadow-lg">
          <button
            onClick={() => setHighExpanded(!highExpanded)}
            className="w-full p-4 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
          >
            <div className="flex items-center space-x-3">
              <span className="w-3 h-3 rounded-full bg-rose-500 shadow-glow" />
              <span className="font-mono font-bold text-sm text-white">
                HIGH PRIORITY QUEUE
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                {highItems.length} items
              </span>
            </div>
            {highExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {highExpanded && (
            <div className="p-4 pt-0 border-t border-white/5 overflow-x-auto">
              {highItems.filter(filterMatches).length === 0 ? (
                <div className="py-6 text-center text-gray-500 font-mono text-xs">
                  No high priority transactions match the current filter.
                </div>
              ) : (
                <table className="w-full text-left font-mono text-xs">
                  <thead>
                    <tr className="text-gray-400 border-b border-white/10 text-[10px] uppercase">
                      <th className="py-2.5 px-3">Transaction</th>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3">Flow</th>
                      <th className="py-2.5 px-3 text-right">Amount</th>
                      <th className="py-2.5 px-3">Counterparty</th>
                      <th className="py-2.5 px-3">Triggered Reasons</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {highItems.filter(filterMatches).map((item) => {
                      const flow = getFlowDirection(item);
                      const isCredit = flow === "credit";
                      const rawFlowLabel = item.direction || item.flow_type || (isCredit ? "CREDIT" : "DEBIT");

                      return (
                        <tr
                          key={item.transaction_id}
                          onClick={() => onSelectTransaction(item.transaction_id)}
                          className="hover:bg-white/5 cursor-pointer transition-colors group"
                        >
                          <td className="py-2.5 px-3 font-bold text-white group-hover:text-cyan-400 flex items-center space-x-1.5">
                            <span>{item.transaction_id}</span>
                            <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 text-cyan-400" />
                          </td>
                          <td className="py-2.5 px-3 text-gray-400">{item.date || "N/A"}</td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`uppercase text-[10px] font-bold ${
                                isCredit ? "text-emerald-400" : "text-rose-400"
                              }`}
                            >
                              {rawFlowLabel}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right font-bold text-white">
                            {formatAmount(item.amount)}
                          </td>
                          <td className="py-2.5 px-3 text-cyan-300 font-semibold truncate max-w-xs">
                            {item.counterparty || "Unspecified"}
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="flex flex-wrap gap-1">
                              {(item.reasons || []).slice(0, 3).map((r, idx) => (
                                <span
                                  key={idx}
                                  className="px-1.5 py-0.5 rounded text-[9px] bg-black/40 border border-white/5 text-gray-300"
                                >
                                  {r}
                                </span>
                              ))}
                              {(item.reasons || []).length > 3 && (
                                <span className="text-[9px] text-gray-500">
                                  +{(item.reasons || []).length - 3}
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>

        {/* MEDIUM PRIORITY ACCORDION */}
        <div className="rounded-xl border border-amber-500/20 bg-surface/60 overflow-hidden shadow-lg">
          <button
            onClick={() => setMediumExpanded(!mediumExpanded)}
            className="w-full p-4 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
          >
            <div className="flex items-center space-x-3">
              <span className="w-3 h-3 rounded-full bg-amber-400" />
              <span className="font-mono font-bold text-sm text-white">
                MEDIUM PRIORITY QUEUE
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                {mediumItems.length} items
              </span>
            </div>
            {mediumExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {mediumExpanded && (
            <div className="p-4 pt-0 border-t border-white/5 overflow-x-auto">
              {mediumItems.filter(filterMatches).length === 0 ? (
                <div className="py-6 text-center text-gray-500 font-mono text-xs">
                  No medium priority transactions match the current filter.
                </div>
              ) : (
                <table className="w-full text-left font-mono text-xs">
                  <thead>
                    <tr className="text-gray-400 border-b border-white/10 text-[10px] uppercase">
                      <th className="py-2.5 px-3">Transaction</th>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3">Flow</th>
                      <th className="py-2.5 px-3 text-right">Amount</th>
                      <th className="py-2.5 px-3">Counterparty</th>
                      <th className="py-2.5 px-3">Triggered Reasons</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {mediumItems.filter(filterMatches).map((item) => {
                      const flow = getFlowDirection(item);
                      const isCredit = flow === "credit";
                      const rawFlowLabel = item.direction || item.flow_type || (isCredit ? "CREDIT" : "DEBIT");

                      return (
                        <tr
                          key={item.transaction_id}
                          onClick={() => onSelectTransaction(item.transaction_id)}
                          className="hover:bg-white/5 cursor-pointer transition-colors group"
                        >
                          <td className="py-2.5 px-3 font-bold text-white group-hover:text-cyan-400 flex items-center space-x-1.5">
                            <span>{item.transaction_id}</span>
                            <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 text-cyan-400" />
                          </td>
                          <td className="py-2.5 px-3 text-gray-400">{item.date || "N/A"}</td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`uppercase text-[10px] font-bold ${
                                isCredit ? "text-emerald-400" : "text-rose-400"
                              }`}
                            >
                              {rawFlowLabel}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right font-bold text-white">
                            {formatAmount(item.amount)}
                          </td>
                          <td className="py-2.5 px-3 text-cyan-300 font-semibold truncate max-w-xs">
                            {item.counterparty || "Unspecified"}
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="flex flex-wrap gap-1">
                              {(item.reasons || []).slice(0, 3).map((r, idx) => (
                                <span
                                  key={idx}
                                  className="px-1.5 py-0.5 rounded text-[9px] bg-black/40 border border-white/5 text-gray-300"
                                >
                                  {r}
                                </span>
                              ))}
                              {(item.reasons || []).length > 3 && (
                                <span className="text-[9px] text-gray-500">
                                  +{(item.reasons || []).length - 3}
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>

        {/* LOW PRIORITY ACCORDION */}
        <div className="rounded-xl border border-blue-500/20 bg-surface/60 overflow-hidden shadow-lg">
          <button
            onClick={() => setLowExpanded(!lowExpanded)}
            className="w-full p-4 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
          >
            <div className="flex items-center space-x-3">
              <span className="w-3 h-3 rounded-full bg-blue-400" />
              <span className="font-mono font-bold text-sm text-white">
                LOW PRIORITY QUEUE
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                {lowItems.length} items
              </span>
            </div>
            {lowExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {lowExpanded && (
            <div className="p-4 pt-0 border-t border-white/5 overflow-x-auto">
              {lowItems.filter(filterMatches).length === 0 ? (
                <div className="py-6 text-center text-gray-500 font-mono text-xs">
                  No low priority transactions match the current filter.
                </div>
              ) : (
                <table className="w-full text-left font-mono text-xs">
                  <thead>
                    <tr className="text-gray-400 border-b border-white/10 text-[10px] uppercase">
                      <th className="py-2.5 px-3">Transaction</th>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3">Flow</th>
                      <th className="py-2.5 px-3 text-right">Amount</th>
                      <th className="py-2.5 px-3">Counterparty</th>
                      <th className="py-2.5 px-3">Triggered Reasons</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {lowItems.filter(filterMatches).map((item) => {
                      const flow = getFlowDirection(item);
                      const isCredit = flow === "credit";
                      const rawFlowLabel = item.direction || item.flow_type || (isCredit ? "CREDIT" : "DEBIT");

                      return (
                        <tr
                          key={item.transaction_id}
                          onClick={() => onSelectTransaction(item.transaction_id)}
                          className="hover:bg-white/5 cursor-pointer transition-colors group"
                        >
                          <td className="py-2.5 px-3 font-bold text-white group-hover:text-cyan-400 flex items-center space-x-1.5">
                            <span>{item.transaction_id}</span>
                            <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 text-cyan-400" />
                          </td>
                          <td className="py-2.5 px-3 text-gray-400">{item.date || "N/A"}</td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`uppercase text-[10px] font-bold ${
                                isCredit ? "text-emerald-400" : "text-rose-400"
                              }`}
                            >
                              {rawFlowLabel}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right font-bold text-white">
                            {formatAmount(item.amount)}
                          </td>
                          <td className="py-2.5 px-3 text-cyan-300 font-semibold truncate max-w-xs">
                            {item.counterparty || "Unspecified"}
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="flex flex-wrap gap-1">
                              {(item.reasons || []).slice(0, 3).map((r, idx) => (
                                <span
                                  key={idx}
                                  className="px-1.5 py-0.5 rounded text-[9px] bg-black/40 border border-white/5 text-gray-300"
                                >
                                  {r}
                                </span>
                              ))}
                              {(item.reasons || []).length > 3 && (
                                <span className="text-[9px] text-gray-500">
                                  +{(item.reasons || []).length - 3}
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
