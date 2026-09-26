"use client";

import React from "react";
import { CheckCircle2, XCircle, AlertTriangle, ShieldAlert, RotateCcw, ShieldCheck } from "lucide-react";
import { CriticSummary, RevisionSummary } from "@/types";

interface CriticPanelProps {
  critic: CriticSummary;
  revision: RevisionSummary;
}

export default function CriticPanel({ critic, revision }: CriticPanelProps) {
  const isPassed = critic.passed && critic.status === "PASS";

  const checklist = [
    {
      title: "Transaction IDs Validated",
      desc: "Every cited transaction exists in verified statement records",
      status: critic.invalid_transaction_ids.length === 0,
      details: `${critic.checked_transaction_ids.length} transaction IDs verified`,
    },
    {
      title: "Amounts & Dates Reconciled",
      desc: "Cited monetary values and timestamps match statement ledgers",
      status: !critic.issues.some((i) => i.toLowerCase().includes("amount") || i.toLowerCase().includes("date")),
      details: "Deterministic reconciliation passed",
    },
    {
      title: "AML Safety Guardrails Enforced",
      desc: "Zero prohibited declarations of criminal guilt or autonomous orders",
      status: critic.safety_violations.length === 0,
      details: "Non-accusatory compliance language preserved",
    },
    {
      title: "Question Inquiries Addressed",
      desc: "Specific transactions or counterparties in query were examined",
      status: critic.missing_evidence.length === 0,
      details: "Evidence scope complete",
    },
  ];

  return (
    <div className="w-full space-y-6">
      {/* Top Status Card */}
      <div
        className={`p-6 rounded-2xl border backdrop-blur-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
          isPassed
            ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-200"
            : "bg-rose-950/20 border-rose-500/30 text-rose-200"
        }`}
      >
        <div className="flex items-center space-x-3.5">
          <div
            className={`p-3 rounded-xl border ${
              isPassed
                ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                : "bg-rose-500/20 text-rose-400 border-rose-500/40"
            }`}
          >
            {isPassed ? <ShieldCheck className="w-7 h-7" /> : <ShieldAlert className="w-7 h-7" />}
          </div>
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-gray-400">
              ADVERSARIAL CRITIC AUDIT
            </div>
            <h3 className="text-xl font-bold tracking-wide mt-0.5 text-white">
              {isPassed ? "AUDIT PASSED // EVIDENCE VERIFIED" : "AUDIT FLAGGED DISCREPANCIES"}
            </h3>
            <p className="text-xs text-gray-300 mt-1 font-mono">
              Factual claims independently cross-examined against underlying statement records.
            </p>
          </div>
        </div>

        <div className="flex flex-col items-end">
          <div className="flex items-center space-x-2 font-mono text-xs px-3 py-1 rounded-full bg-black/40 border border-white/10">
            <RotateCcw className="w-3.5 h-3.5 text-purple-400" />
            <span>
              Revision {revision.revision_count} of {revision.max_revisions}
            </span>
          </div>
          {revision.revisions_applied && (
            <span className="text-[11px] text-purple-400 font-mono mt-1">
              ✓ Self-Correction Applied
            </span>
          )}
        </div>
      </div>

      {/* Unresolved limitations banner if failed */}
      {revision.unresolved_limitations && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/40 flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="text-xs text-rose-200 font-sans leading-relaxed">
            <span className="font-semibold text-rose-300">UNRESOLVED VALIDATION LIMITATION:</span> The
            investigation reached its maximum revision limit with unresolved critic findings. Mandatory manual
            compliance officer review is required before taking any action.
          </div>
        </div>
      )}

      {/* Verification Checklist */}
      <div className="bg-[#0b0f19]/80 backdrop-blur-xl rounded-2xl border border-white/10 p-5 shadow-2xl">
        <h4 className="text-xs font-mono font-semibold text-gray-400 uppercase mb-4 pb-2 border-b border-white/10">
          Deterministic Verification Checklist
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {checklist.map((item, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-xl border border-white/5 bg-surface/40 flex items-start space-x-3"
            >
              {item.status ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <XCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              )}
              <div>
                <div className="text-xs font-bold text-gray-100">{item.title}</div>
                <div className="text-[11px] text-gray-400 mt-0.5">{item.desc}</div>
                <div className="text-[10px] font-mono text-cyan-400 mt-1">{item.details}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Audit Issues or Flags (if any) */}
      {critic.issues.length > 0 && (
        <div className="p-5 rounded-2xl bg-[#0b0f19]/80 border border-white/10 backdrop-blur-xl">
          <h4 className="text-xs font-mono font-semibold text-amber-400 uppercase mb-3 flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4" />
            <span>Critic Findings & Required Revisions</span>
          </h4>
          <div className="space-y-2">
            {critic.issues.map((iss, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-amber-950/20 border border-amber-500/20 text-xs text-amber-200"
              >
                {iss}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
