"use client";

import React, { useEffect, useState } from "react";
import {
  X,
  History,
  FileText,
  User,
  Calendar,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  RotateCcw,
} from "lucide-react";
import { InvestigationHistoryRecord, InvestigationReport } from "@/types";
import { fetchHistoricalReport, fetchInvestigationHistory } from "@/lib/api";

interface InvestigationHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectReport: (report: InvestigationReport, markdown: string) => void;
}

export default function InvestigationHistoryModal({
  isOpen,
  onClose,
  onSelectReport,
}: InvestigationHistoryModalProps) {
  const [historyRecords, setHistoryRecords] = useState<InvestigationHistoryRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingReportId, setLoadingReportId] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    setLoading(true);

    async function loadHistory() {
      try {
        const records = await fetchInvestigationHistory();
        if (isMounted) {
          setHistoryRecords(records);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) setLoading(false);
      }
    }

    loadHistory();

    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleOpen = async (record: InvestigationHistoryRecord) => {
    setLoadingReportId(record.report_id);
    try {
      const data = await fetchHistoricalReport(record.report_id);
      if (data && data.report) {
        onSelectReport(data.report, data.markdown || "");
        onClose();
      }
    } catch (err) {
      console.error("Failed to load historical report:", err);
    } finally {
      setLoadingReportId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div
        className="w-full max-w-4xl bg-[#091122] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-white/10 flex items-center justify-between bg-surface/50">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold font-mono text-white">
                Investigation History & Case Archive
              </h3>
              <p className="text-xs text-gray-400 font-mono">
                Persistent audit registry of past AML investigations (Phase 11)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* List Table */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="py-20 text-center text-gray-400 font-mono text-xs">
              Loading archived investigation cases...
            </div>
          ) : historyRecords.length === 0 ? (
            <div className="py-20 text-center space-y-3 font-mono text-xs text-gray-500">
              <History className="w-8 h-8 text-gray-600 mx-auto" />
              <p>No historical investigations saved yet.</p>
              <p className="text-[11px] text-gray-600">
                Run an investigation or try Demo Mode to generate your first archived compliance record.
              </p>
            </div>
          ) : (
            <div className="border border-white/10 rounded-xl overflow-hidden">
              <table className="w-full text-left font-mono text-xs">
                <thead>
                  <tr className="bg-surface/80 text-gray-400 border-b border-white/10 text-[10px] uppercase">
                    <th className="py-3 px-4">Report ID</th>
                    <th className="py-3 px-4">Customer</th>
                    <th className="py-3 px-4">Transactions</th>
                    <th className="py-3 px-4">Review Items</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {historyRecords.map((r) => (
                    <tr key={r.report_id} className="hover:bg-white/5 transition-colors">
                      <td className="py-3 px-4 font-bold text-cyan-300">
                        {r.report_id}
                        <div className="text-[10px] text-gray-500 font-normal">
                          {r.timestamp ? new Date(r.timestamp).toLocaleString() : "N/A"}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-white">
                        <div className="font-semibold">{r.customer_name}</div>
                        <div className="text-[10px] text-gray-400">{r.account_number}</div>
                      </td>
                      <td className="py-3 px-4 text-gray-300">
                        {r.transaction_count} txns
                        <div className="text-[10px] text-gray-500">{r.statement_period}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-white font-bold">{r.review_count}</span>
                        <span className="text-rose-400 text-[10px] ml-1">
                          ({r.high_priority_count} HIGH)
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            r.status === "COMPLETED"
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                              : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleOpen(r)}
                          disabled={loadingReportId === r.report_id}
                          className="px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 font-mono text-xs font-semibold inline-flex items-center space-x-1.5 transition-all"
                        >
                          {loadingReportId === r.report_id ? (
                            <span>Opening...</span>
                          ) : (
                            <>
                              <ExternalLink className="w-3.5 h-3.5" />
                              <span>Open Report</span>
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-white/10 bg-surface/50 flex items-center justify-between">
          <span className="text-[10px] text-gray-500 font-mono">
            {historyRecords.length} historical case(s) archived
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white font-mono text-xs transition-all"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
