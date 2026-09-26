"use client";

import React from "react";
import { AlertTriangle, Activity, ShieldAlert, Info } from "lucide-react";
import { DetectionFindingItem, AnomalyFindingItem } from "@/types";

interface DetectionPanelProps {
  ruleSignals: DetectionFindingItem[];
  anomalySignals: AnomalyFindingItem[];
}

export default function DetectionPanel({
  ruleSignals = [],
  anomalySignals = [],
}: DetectionPanelProps) {
  return (
    <div className="w-full space-y-6">
      {/* Required Compliance Disclaimer Banner */}
      <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/30 flex items-start space-x-3">
        <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs text-amber-200/90 leading-relaxed font-sans">
          <span className="font-semibold text-amber-300">ANALYTICAL SIGNAL BOUNDARY:</span> An anomaly
          indicates statistical unusualness relative to historical or cohort baselines, not criminal
          wrongdoing or illicit activity. Detection signals serve as automated leads for human compliance review.
        </div>
      </div>

      {/* Metrics Summary Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-surface/80 border border-white/5 backdrop-blur-md">
          <div className="text-[11px] font-mono text-gray-400 uppercase">Deterministic Rules</div>
          <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">{ruleSignals.length}</div>
          <div className="text-[10px] text-gray-500 mt-1">Screening signals active</div>
        </div>
        <div className="p-4 rounded-xl bg-surface/80 border border-white/5 backdrop-blur-md">
          <div className="text-[11px] font-mono text-gray-400 uppercase">Statistical Anomalies</div>
          <div className="text-2xl font-bold font-mono text-purple-400 mt-1">
            {anomalySignals.filter((a) => a.is_anomaly).length}
          </div>
          <div className="text-[10px] text-gray-500 mt-1">Isolation Forest outliers</div>
        </div>
        <div className="p-4 rounded-xl bg-surface/80 border border-white/5 backdrop-blur-md">
          <div className="text-[11px] font-mono text-gray-400 uppercase">High Severity Flags</div>
          <div className="text-2xl font-bold font-mono text-rose-400 mt-1">
            {ruleSignals.filter((r) => r.severity === "HIGH").length}
          </div>
          <div className="text-[10px] text-gray-500 mt-1">Priority review signals</div>
        </div>
        <div className="p-4 rounded-xl bg-surface/80 border border-white/5 backdrop-blur-md">
          <div className="text-[11px] font-mono text-gray-400 uppercase">Screening Status</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">PASS</div>
          <div className="text-[10px] text-gray-500 mt-1">Deterministic execution</div>
        </div>
      </div>

      {/* Deterministic Rule Signals */}
      <div className="bg-[#0b0f19]/80 backdrop-blur-xl rounded-2xl border border-white/10 p-5 shadow-2xl">
        <div className="flex items-center space-x-2 mb-4 pb-3 border-b border-white/10">
          <ShieldAlert className="w-5 h-5 text-amber-400" />
          <h3 className="text-sm font-semibold tracking-wider text-gray-200 uppercase font-mono">
            Deterministic AML Rule Signals
          </h3>
        </div>

        {ruleSignals.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-xs font-mono">
            No deterministic rule signals triggered on this statement.
          </div>
        ) : (
          <div className="space-y-3">
            {ruleSignals.map((rule, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border border-white/5 bg-surface/40 hover:border-cyan-500/30 transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2.5">
                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                        rule.severity === "HIGH"
                          ? "bg-rose-950/60 text-rose-400 border-rose-500/40"
                          : rule.severity === "MEDIUM"
                          ? "bg-amber-950/60 text-amber-400 border-amber-500/40"
                          : "bg-blue-950/60 text-blue-400 border-blue-500/40"
                      }`}
                    >
                      {rule.severity}
                    </span>
                    <span className="text-sm font-bold text-gray-100">{rule.rule_name}</span>
                    <span className="text-xs font-mono text-gray-500">({rule.rule_id})</span>
                  </div>
                  {rule.supporting_transaction_ids.length > 0 && (
                    <div className="flex items-center space-x-1.5">
                      <span className="text-[10px] text-gray-400 font-mono">Txns:</span>
                      {rule.supporting_transaction_ids.map((tid) => (
                        <span
                          key={tid}
                          className="px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 font-mono text-[11px]"
                        >
                          {tid}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <p className="text-xs text-gray-300 leading-relaxed">{rule.explanation}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Isolation Forest Anomaly Detection */}
      <div className="bg-[#0b0f19]/80 backdrop-blur-xl rounded-2xl border border-white/10 p-5 shadow-2xl">
        <div className="flex items-center space-x-2 mb-4 pb-3 border-b border-white/10">
          <Activity className="w-5 h-5 text-purple-400" />
          <h3 className="text-sm font-semibold tracking-wider text-gray-200 uppercase font-mono">
            Unsupervised Anomaly Signals (Isolation Forest)
          </h3>
        </div>

        {anomalySignals.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-xs font-mono">
            No statistical outliers identified by Isolation Forest.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {anomalySignals.map((anom, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl border border-purple-500/20 bg-purple-950/10 hover:border-purple-500/40 transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-xs font-bold text-purple-300">
                    {anom.transaction_id}
                  </span>
                  <span className="text-xs font-mono text-purple-400">
                    Score: {anom.anomaly_score.toFixed(4)}
                  </span>
                </div>
                <div className="text-[11px] text-gray-400 font-mono space-y-1">
                  {Object.entries(anom.feature_context).map(([k, v]) => (
                    <div key={k} className="flex justify-between border-b border-white/5 pb-0.5">
                      <span className="text-gray-500">{k}:</span>
                      <span className="text-gray-300">{typeof v === "number" ? v.toFixed(2) : v}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
