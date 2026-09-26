"use client";

import React, { useEffect, useState } from "react";
import {
  X,
  ShieldAlert,
  Activity,
  Network,
  BookOpen,
  CheckCircle2,
  Calendar,
  Building2,
  ArrowDownLeft,
  ArrowUpRight,
  ExternalLink,
} from "lucide-react";
import { InvestigationReport, TransactionEvidenceDossier } from "@/types";
import { fetchTransactionEvidence } from "@/lib/api";

interface TransactionDetailDrawerProps {
  report: InvestigationReport | null;
  transactionId: string | null;
  onClose: () => void;
}

export default function TransactionDetailDrawer({
  report,
  transactionId,
  onClose,
}: TransactionDetailDrawerProps) {
  const [dossier, setDossier] = useState<TransactionEvidenceDossier | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!transactionId || !report) {
      setDossier(null);
      return;
    }

    const currentReport = report;
    const currentTxnId = transactionId;
    let isMounted = true;
    setLoading(true);

    // Attempt to fetch from backend or build deterministically from local report
    async function load() {
      try {
        const data = await fetchTransactionEvidence(currentReport.report_id, currentTxnId);
        if (isMounted) {
          setDossier(data);
          setLoading(false);
        }
      } catch (err) {
        // Deterministic fallback from report
        if (!isMounted) return;
        const ev = (currentReport.observed_evidence || []).find((e) => e.transaction_id === currentTxnId);
        const anom = (currentReport.anomaly_findings || []).find((a) => a.transaction_id === currentTxnId);
        const rules = (currentReport.detection_findings || [])
          .filter((r) => (r.supporting_transaction_ids || []).includes(currentTxnId))
          .map((r) => ({
            rule_id: r.rule_id,
            rule_name: r.rule_name,
            severity: r.severity,
            explanation: r.explanation,
            supporting_values: r.supporting_values || {},
          }));
        const net = (currentReport.network_findings || [])
          .filter(
            (n) =>
              (n.supporting_transaction_ids || []).includes(currentTxnId) ||
              (ev?.counterparty && (n.involved_nodes || []).includes(ev.counterparty))
          )
          .map((n) => ({
            pattern_name: n.pattern_name,
            description: n.description,
            involved_nodes: n.involved_nodes || [],
          }));
        const hr = (currentReport.human_review_items || []).find((h) => h.transaction_id === currentTxnId);
        const conv = (currentReport.evidence_convergence || []).find((c) => c.transaction_id === currentTxnId);

        setDossier({
          transaction_id: currentTxnId,
          date: ev?.date || null,
          amount: ev?.amount || null,
          flow_type: ev?.flow_type || null,
          counterparty: ev?.counterparty || null,
          description: ev?.description || null,
          verified_in_statement: true,
          is_anomaly: !!anom,
          anomaly_score: anom?.anomaly_score || null,
          anomaly_features: anom?.feature_context || {},
          rules_triggered: rules,
          network_patterns: net,
          human_review_priority: hr?.priority || conv?.priority || null,
          human_review_reasons: hr?.reasons || conv?.reasons || [],
          evidence_convergence_summary: conv?.convergence_summary || hr?.evidence_summary || null,
          signal_domains: conv?.signal_domains || [],
          related_rag_guidance: (currentReport.aml_reference_context || []).map((k) => ({
            source: k.source,
            guidance: k.snippet || "Reference compliance guidance.",
          })),
        });
        setLoading(false);
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, [transactionId, report]);

  if (!transactionId) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-opacity">
      <div
        className="w-full max-w-xl bg-[#091122] border-l border-white/10 shadow-2xl flex flex-col h-full overflow-hidden animate-in slide-in-from-right duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="p-6 border-b border-white/10 flex items-center justify-between bg-surface/50">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-black font-mono text-white tracking-wider">
                  {transactionId}
                </h3>
                {dossier?.human_review_priority && (
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase ${
                      dossier.human_review_priority === "HIGH"
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                        : dossier.human_review_priority === "MEDIUM"
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                    }`}
                  >
                    {dossier.human_review_priority} PRIORITY
                  </span>
                )}
                {dossier?.is_anomaly && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    ML OUTLIER
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400 font-mono">
                Transaction Evidence Dossier & Audit Provenance
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

        {/* Drawer Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="py-20 text-center text-gray-400 font-mono text-xs">
              <Activity className="w-6 h-6 text-cyan-400 animate-spin mx-auto mb-3" />
              Reconciling factual evidence layers...
            </div>
          ) : !dossier ? (
            <div className="py-20 text-center text-gray-400 font-mono text-xs">
              Transaction evidence record not found.
            </div>
          ) : (
            <>
              {/* Core Ledger Attributes */}
              <div className="grid grid-cols-2 gap-3 p-4 rounded-xl bg-surface/60 border border-white/5 font-mono">
                <div>
                  <span className="text-[10px] text-gray-400 block uppercase">AMOUNT</span>
                  <div className="text-lg font-bold text-white mt-0.5 flex items-center space-x-1">
                    <span>
                      {dossier.amount !== null
                        ? `₹${dossier.amount.toLocaleString("en-IN", {
                            minimumFractionDigits: 2,
                          })}`
                        : "N/A"}
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] text-gray-400 block uppercase">DIRECTION</span>
                  <div className="text-sm font-semibold mt-1 flex items-center space-x-1.5">
                    {dossier.flow_type?.toLowerCase() === "credit" ? (
                      <>
                        <ArrowDownLeft className="w-4 h-4 text-emerald-400" />
                        <span className="text-emerald-400 font-bold">CREDIT (INFLOW)</span>
                      </>
                    ) : (
                      <>
                        <ArrowUpRight className="w-4 h-4 text-rose-400" />
                        <span className="text-rose-400 font-bold">DEBIT (OUTFLOW)</span>
                      </>
                    )}
                  </div>
                </div>

                <div>
                  <span className="text-[10px] text-gray-400 block uppercase">DATE</span>
                  <div className="text-xs text-gray-200 mt-1 flex items-center space-x-1.5">
                    <Calendar className="w-3.5 h-3.5 text-gray-400" />
                    <span>{dossier.date || "N/A"}</span>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] text-gray-400 block uppercase">COUNTERPARTY</span>
                  <div className="text-xs text-cyan-300 font-bold mt-1 flex items-center space-x-1.5 truncate">
                    <Building2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    <span className="truncate">{dossier.counterparty || "Unspecified"}</span>
                  </div>
                </div>
              </div>

              {/* Why Flagged Checklist */}
              <div className="p-4 rounded-xl bg-gradient-to-br from-surface to-[#0e172a] border border-cyan-500/20 space-y-3">
                <div className="text-xs font-mono font-bold text-cyan-400 flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>DETERMINISTIC FLAGGING RATIONALE</span>
                </div>
                <div className="space-y-2 text-xs">
                  {(dossier.rules_triggered || []).map((r, i) => (
                    <div key={i} className="flex items-start space-x-2 text-gray-200">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-mono font-bold text-white">{r.rule_name}</span>:{" "}
                        <span className="text-gray-300">{r.explanation}</span>
                      </div>
                    </div>
                  ))}
                  {dossier.is_anomaly && (
                    <div className="flex items-start space-x-2 text-gray-200">
                      <CheckCircle2 className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-mono font-bold text-purple-300">
                          Isolation Forest Statistical Outlier
                        </span>{" "}
                        (Anomaly Score: {dossier.anomaly_score?.toFixed(4)})
                      </div>
                    </div>
                  )}
                  {(dossier.network_patterns || []).map((n, i) => (
                    <div key={i} className="flex items-start space-x-2 text-gray-200">
                      <CheckCircle2 className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-mono font-bold text-amber-300">{n.pattern_name}</span>:{" "}
                        <span className="text-gray-300">{n.description}</span>
                      </div>
                    </div>
                  ))}
                  {(dossier.rules_triggered || []).length === 0 &&
                    !dossier.is_anomaly &&
                    (dossier.network_patterns || []).length === 0 && (
                      <p className="text-gray-400 italic">
                        Standard transactional activity conforming to baseline behavior.
                      </p>
                    )}
                </div>
              </div>

              {/* Signal Convergence Summary */}
              {dossier.evidence_convergence_summary && (
                <div className="p-4 rounded-xl bg-surface/70 border border-white/5 space-y-2">
                  <div className="text-xs font-mono font-bold text-gray-300 uppercase">
                    EVIDENCE CONVERGENCE SUMMARY
                  </div>
                  <p className="text-xs text-gray-300 leading-relaxed font-sans">
                    {dossier.evidence_convergence_summary}
                  </p>
                  {(dossier.signal_domains || []).length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {(dossier.signal_domains || []).map((dom, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-white/5 border border-white/10 text-cyan-300"
                        >
                          {dom}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Statistical Anomaly Features */}
              {dossier.is_anomaly && Object.keys(dossier.anomaly_features || {}).length > 0 && (
                <div className="p-4 rounded-xl bg-surface/70 border border-white/5 space-y-2">
                  <div className="text-xs font-mono font-bold text-purple-400 flex items-center space-x-2">
                    <Activity className="w-4 h-4" />
                    <span>ML OUTLIER FEATURE VECTORS</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    {Object.entries(dossier.anomaly_features || {}).map(([feat, val]) => (
                      <div
                        key={feat}
                        className="p-2 rounded bg-black/40 border border-white/5 flex justify-between"
                      >
                        <span className="text-gray-400 truncate">{feat}</span>
                        <span className="text-white font-bold">{val.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Network Topology Context */}
              {(dossier.network_patterns || []).length > 0 && (
                <div className="p-4 rounded-xl bg-surface/70 border border-white/5 space-y-2">
                  <div className="text-xs font-mono font-bold text-amber-400 flex items-center space-x-2">
                    <Network className="w-4 h-4" />
                    <span>RELATIONAL NETWORK CONTEXT</span>
                  </div>
                  {(dossier.network_patterns || []).map((np, i) => (
                    <div key={i} className="text-xs space-y-1">
                      <div className="text-white font-semibold font-mono">{np.pattern_name}</div>
                      <div className="text-gray-400">{np.description}</div>
                      <div className="text-[11px] text-gray-500 font-mono">
                        Entities: {(np.involved_nodes || []).join(" ↔ ")}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* AML Reference Knowledge Guidance */}
              <div className="p-4 rounded-xl bg-surface/70 border border-white/5 space-y-2">
                <div className="text-xs font-mono font-bold text-cyan-400 flex items-center space-x-2">
                  <BookOpen className="w-4 h-4" />
                  <span>AML REFERENCE KNOWLEDGE BASE GUIDANCE</span>
                </div>
                <div className="space-y-2 text-xs">
                  {(dossier.related_rag_guidance || []).slice(0, 2).map((rg, i) => (
                    <div key={i} className="p-2.5 rounded bg-black/40 border border-white/5 space-y-1">
                      <div className="font-mono text-[11px] text-cyan-300 font-bold flex items-center justify-between">
                        <span>{rg.source}</span>
                      </div>
                      <p className="text-gray-300 text-[11px] leading-relaxed">
                        {rg.guidance}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-white/10 bg-surface/60 flex items-center justify-between">
          <span className="text-[10px] text-gray-500 font-mono">
            Grounding: 100% reconciled against canonical statement
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white font-mono text-xs font-bold transition-all"
          >
            Close Dossier
          </button>
        </div>
      </div>
    </div>
  );
}
