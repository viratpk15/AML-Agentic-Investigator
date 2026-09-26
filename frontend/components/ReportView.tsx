"use client";

import React, { useState } from "react";
import { Download, Copy, Check, FileText, Code2, ShieldAlert } from "lucide-react";
import { InvestigationReport } from "@/types";

interface ReportViewProps {
  report: InvestigationReport;
  markdown: string;
}

export default function ReportView({ report, markdown }: ReportViewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadMarkdown = () => {
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.report_id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadJson = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.report_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full space-y-6">
      {/* Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-surface/80 border border-white/10 backdrop-blur-xl">
        <div className="flex items-center space-x-2">
          <FileText className="w-5 h-5 text-cyan-400" />
          <span className="text-sm font-bold text-white font-mono">{report.report_id}</span>
          <span className="text-xs px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 font-mono">
            {report.critic_validation.status}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleCopy}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-surface/60 hover:bg-surface border border-white/10 text-xs font-mono text-gray-300 transition-all"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? "Copied!" : "Copy"}</span>
          </button>
          <button
            onClick={handleDownloadMarkdown}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-cyan-950/50 hover:bg-cyan-900/60 border border-cyan-500/30 text-xs font-mono text-cyan-300 transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Markdown</span>
          </button>
          <button
            onClick={handleDownloadJson}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-purple-950/50 hover:bg-purple-900/60 border border-purple-500/30 text-xs font-mono text-purple-300 transition-all"
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* Styled Markdown Viewport */}
      <div className="p-8 rounded-2xl bg-[#0b0f19]/90 border border-white/10 shadow-2xl backdrop-blur-xl text-gray-200 leading-relaxed font-sans max-w-4xl mx-auto space-y-6">
        <div className="border-b border-white/10 pb-4">
          <div className="text-xs font-mono text-cyan-400 uppercase tracking-widest mb-1">
            CONFIDENTIAL COMPLIANCE AUDIT
          </div>
          <h1 className="text-2xl font-bold text-white tracking-wide">AML Investigation Report</h1>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono text-gray-400 mt-3 pt-3 border-t border-white/5">
            <div>
              <span className="text-gray-500 block">Report ID:</span>
              <span className="text-cyan-300">{report.report_id}</span>
            </div>
            <div>
              <span className="text-gray-500 block">Customer:</span>
              <span className="text-white">{report.customer_name}</span>
            </div>
            <div>
              <span className="text-gray-500 block">Account:</span>
              <span className="text-white">{report.account_number}</span>
            </div>
            <div>
              <span className="text-gray-500 block">Audit Outcome:</span>
              <span className="text-emerald-400 font-semibold">{report.critic_validation.status}</span>
            </div>
          </div>
        </div>

        {/* Question */}
        <div>
          <h3 className="text-xs font-mono text-gray-400 uppercase font-bold tracking-wider mb-1">
            Investigation Question
          </h3>
          <p className="p-3.5 rounded-xl bg-cyan-950/20 border border-cyan-500/20 text-cyan-200 text-sm font-sans">
            "{report.investigation_question}"
          </p>
        </div>

        {/* Executive Summary */}
        <div>
          <h3 className="text-xs font-mono text-gray-400 uppercase font-bold tracking-wider mb-2">
            Executive Summary
          </h3>
          <div className="p-4 rounded-xl bg-surface/50 border border-white/5 text-sm text-gray-300 leading-relaxed whitespace-pre-line">
            {report.executive_summary}
          </div>
        </div>

        {/* 1. Observed Evidence Table */}
        <div>
          <h3 className="text-xs font-mono text-gray-400 uppercase font-bold tracking-wider mb-2">
            1. Observed Evidence
          </h3>
          {report.observed_evidence.length > 0 ? (
            <div className="overflow-x-auto rounded-xl border border-white/10">
              <table className="w-full text-left text-xs">
                <thead className="bg-surface/80 font-mono text-gray-400 border-b border-white/10">
                  <tr>
                    <th className="p-2.5">ID</th>
                    <th className="p-2.5">Date</th>
                    <th className="p-2.5">Flow</th>
                    <th className="p-2.5">Amount</th>
                    <th className="p-2.5">Counterparty</th>
                    <th className="p-2.5">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-mono">
                  {report.observed_evidence.map((ev) => (
                    <tr key={ev.transaction_id} className="hover:bg-white/5">
                      <td className="p-2.5 text-cyan-400 font-bold">{ev.transaction_id}</td>
                      <td className="p-2.5 text-gray-400">{ev.date || "N/A"}</td>
                      <td className="p-2.5 uppercase text-gray-300">{ev.flow_type || "N/A"}</td>
                      <td className="p-2.5 text-emerald-400 font-semibold">
                        {ev.amount ? `₹${ev.amount.toLocaleString()}` : "N/A"}
                      </td>
                      <td className="p-2.5 text-gray-200">{ev.counterparty || "Unspecified"}</td>
                      <td className="p-2.5">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">
                          {ev.verified_in_statement ? "✓ Verified" : "✗ Unverified"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-gray-500 italic">No specific transaction records cited.</p>
          )}
        </div>

        {/* 2. Detection Findings */}
        <div>
          <h3 className="text-xs font-mono text-gray-400 uppercase font-bold tracking-wider mb-2">
            2. Detection Findings
          </h3>
          <div className="space-y-2">
            {report.detection_findings.map((df) => (
              <div key={df.rule_id} className="p-3 rounded-lg bg-surface/40 border border-white/5 text-xs">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-gray-100">{df.rule_name}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/60 text-amber-400 border border-amber-500/30">
                    {df.severity}
                  </span>
                </div>
                <p className="text-gray-300 text-xs">{df.explanation}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Critic & Audit Checklist */}
        <div>
          <h3 className="text-xs font-mono text-gray-400 uppercase font-bold tracking-wider mb-2">
            Critic Validation & Self-Correction
          </h3>
          <div className="p-4 rounded-xl bg-surface/40 border border-white/5 text-xs space-y-2 font-mono">
            <div className="flex justify-between">
              <span className="text-gray-400">Audit Status:</span>
              <span className="text-emerald-400 font-bold">{report.critic_validation.status}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Transaction IDs Verified:</span>
              <span className="text-gray-200">{report.critic_validation.checked_transaction_ids.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Revision Cycles:</span>
              <span className="text-purple-400">
                {report.revision_history.revision_count} of {report.revision_history.max_revisions}
              </span>
            </div>
          </div>
        </div>

        {/* Limitations & Human Review */}
        <div className="border-t border-white/10 pt-4 space-y-3">
          <h3 className="text-xs font-mono text-gray-400 uppercase font-bold tracking-wider">
            Limitations & Mandatory Compliance Notice
          </h3>
          <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-500/20 text-xs text-gray-300 space-y-2">
            <p className="font-semibold text-cyan-300">{report.human_review_recommendation}</p>
            {report.limitations.map((lim, i) => (
              <p key={i} className="text-gray-400">• {lim}</p>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
