"use client";

import React, { useState } from "react";
import { Receipt, Search, ArrowDownRight, ArrowUpRight, CheckCircle2, XCircle } from "lucide-react";
import { EvidenceItem } from "@/types";

interface EvidenceTableProps {
  evidence: EvidenceItem[];
  onSelectTransaction?: (transactionId: string) => void;
}

export default function EvidenceTable({ evidence = [], onSelectTransaction }: EvidenceTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterFlow, setFilterFlow] = useState<"all" | "credit" | "debit">("all");

  const filtered = evidence.filter((ev) => {
    const matchesSearch =
      ev.transaction_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (ev.counterparty && ev.counterparty.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (ev.description && ev.description.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesFlow =
      filterFlow === "all" ||
      (filterFlow === "credit" && ev.flow_type === "credit") ||
      (filterFlow === "debit" && ev.flow_type === "debit");

    return matchesSearch && matchesFlow;
  });

  return (
    <div className="w-full bg-[#0b0f19]/80 backdrop-blur-xl rounded-2xl border border-white/10 p-5 shadow-2xl space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/10">
        <div className="flex items-center space-x-2">
          <Receipt className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-semibold tracking-wider text-gray-200 uppercase font-mono">
            Verified Statement Evidence Ledgers
          </h3>
        </div>

        {/* Search and Filter */}
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter by ID or Counterparty..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-lg bg-surface border border-white/10 text-xs text-gray-200 focus:outline-none focus:border-cyan-500/50 font-mono w-56"
            />
          </div>

          <div className="flex rounded-lg bg-surface p-0.5 border border-white/10 text-xs font-mono">
            <button
              onClick={() => setFilterFlow("all")}
              className={`px-2.5 py-1 rounded ${
                filterFlow === "all" ? "bg-cyan-950 text-cyan-300 font-bold" : "text-gray-400"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterFlow("credit")}
              className={`px-2.5 py-1 rounded ${
                filterFlow === "credit" ? "bg-cyan-950 text-cyan-300 font-bold" : "text-gray-400"
              }`}
            >
              Credits
            </button>
            <button
              onClick={() => setFilterFlow("debit")}
              className={`px-2.5 py-1 rounded ${
                filterFlow === "debit" ? "bg-purple-950 text-purple-300 font-bold" : "text-gray-400"
              }`}
            >
              Debits
            </button>
          </div>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="p-8 text-center text-gray-500 text-xs font-mono">
          No transactions match current filters.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-white/10">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface/80 font-mono text-gray-400 border-b border-white/10">
              <tr>
                <th className="p-3">Transaction ID</th>
                <th className="p-3">Date</th>
                <th className="p-3">Direction</th>
                <th className="p-3">Amount (INR)</th>
                <th className="p-3">Counterparty</th>
                <th className="p-3">Description</th>
                <th className="p-3">Grounding</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono">
              {filtered.map((item) => (
                <tr
                  key={item.transaction_id}
                  onClick={() => onSelectTransaction && onSelectTransaction(item.transaction_id)}
                  className="hover:bg-white/5 cursor-pointer transition-colors"
                >
                  <td className="p-3 text-cyan-300 font-bold">{item.transaction_id}</td>
                  <td className="p-3 text-gray-400">{item.date || "N/A"}</td>
                  <td className="p-3">
                    <span
                      className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${
                        item.flow_type === "credit"
                          ? "bg-cyan-950/60 text-cyan-400 border-cyan-500/30"
                          : "bg-purple-950/60 text-purple-400 border-purple-500/30"
                      }`}
                    >
                      {item.flow_type === "credit" ? (
                        <ArrowDownRight className="w-3 h-3" />
                      ) : (
                        <ArrowUpRight className="w-3 h-3" />
                      )}
                      <span>{item.flow_type || "N/A"}</span>
                    </span>
                  </td>
                  <td className="p-3 font-semibold text-emerald-400">
                    {item.amount ? `₹${item.amount.toLocaleString()}` : "N/A"}
                  </td>
                  <td className="p-3 text-gray-200">{item.counterparty || "Unspecified"}</td>
                  <td className="p-3 text-gray-400 max-w-xs truncate">{item.description || "N/A"}</td>
                  <td className="p-3">
                    {item.verified_in_statement ? (
                      <span className="inline-flex items-center space-x-1 text-emerald-400 text-[11px]">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Statement Match</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center space-x-1 text-rose-400 text-[11px]">
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Unverified</span>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
