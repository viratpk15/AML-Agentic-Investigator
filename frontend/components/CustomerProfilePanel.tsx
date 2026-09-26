"use client";

import React from "react";
import { UserCheck, ArrowUpRight, ArrowDownRight, Calendar, Users, Activity, BarChart2 } from "lucide-react";
import { CustomerProfileSummary } from "@/types";

interface CustomerProfilePanelProps {
  profile: CustomerProfileSummary | null;
}

export default function CustomerProfilePanel({ profile }: CustomerProfilePanelProps) {
  if (!profile) {
    return (
      <div className="p-12 text-center bg-surface/50 border border-white/5 rounded-2xl text-gray-500 font-mono text-xs">
        No customer profile generated yet. Run an investigation to view behavioral baseline metrics.
      </div>
    );
  }

  return (
    <div className="w-full space-y-6">
      {/* Account Identity Header */}
      <div className="p-5 rounded-2xl bg-gradient-to-r from-surface to-[#0d1527] border border-cyan-500/20 backdrop-blur-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3.5">
          <div className="p-3 rounded-xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
            <UserCheck className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white tracking-wide">
              {profile.customer_name || "Account Profile"}
            </h3>
            <div className="flex items-center space-x-3 text-xs font-mono text-gray-400 mt-0.5">
              <span>ACC: <span className="text-cyan-300 font-semibold">{profile.account_number || "N/A"}</span></span>
              <span>•</span>
              <span>Period: {profile.statement_period || "N/A"}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono px-3 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-300">
          <Activity className="w-3.5 h-3.5" />
          <span>Dominant Flow: {profile.dominant_type.toUpperCase()}</span>
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-surface/80 border border-white/5 backdrop-blur-md">
          <div className="text-[11px] font-mono text-gray-400 uppercase">Total Turnover</div>
          <div className="text-xl font-bold font-mono text-white mt-1">
            ₹{(profile.total_credits + profile.total_debits).toLocaleString()}
          </div>
          <div className="text-[10px] text-gray-500 mt-1">{profile.total_transactions} transactions</div>
        </div>

        <div className="p-4 rounded-xl bg-surface/80 border border-white/5 backdrop-blur-md">
          <div className="text-[11px] font-mono text-gray-400 uppercase">Incoming Credits</div>
          <div className="text-xl font-bold font-mono text-cyan-400 mt-1">
            ₹{profile.total_credits.toLocaleString()}
          </div>
          <div className="flex items-center space-x-1 text-[10px] text-cyan-500 mt-1">
            <ArrowDownRight className="w-3 h-3" />
            <span>Deposited to account</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface/80 border border-white/5 backdrop-blur-md">
          <div className="text-[11px] font-mono text-gray-400 uppercase">Outgoing Debits</div>
          <div className="text-xl font-bold font-mono text-purple-400 mt-1">
            ₹{profile.total_debits.toLocaleString()}
          </div>
          <div className="flex items-center space-x-1 text-[10px] text-purple-400 mt-1">
            <ArrowUpRight className="w-3 h-3" />
            <span>Disbursed from account</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface/80 border border-white/5 backdrop-blur-md">
          <div className="text-[11px] font-mono text-gray-400 uppercase">Net Cash Flow</div>
          <div className={`text-xl font-bold font-mono mt-1 ${profile.net_cash_flow >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
            ₹{profile.net_cash_flow.toLocaleString()}
          </div>
          <div className="text-[10px] text-gray-500 mt-1">
            Ratio: {profile.credit_to_debit_ratio ? profile.credit_to_debit_ratio.toFixed(2) : "N/A"}
          </div>
        </div>
      </div>

      {/* Secondary Metrics & Peak Records */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Velocity Metrics */}
        <div className="p-5 rounded-2xl bg-[#0b0f19]/80 border border-white/10 backdrop-blur-xl">
          <h4 className="text-xs font-mono font-semibold text-gray-400 uppercase mb-4 flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-cyan-400" />
            <span>Velocity & Counterparty Metrics</span>
          </h4>
          <div className="space-y-3 font-mono text-xs">
            <div className="flex justify-between border-b border-white/5 pb-2">
              <span className="text-gray-400">Active Transaction Days:</span>
              <span className="text-gray-200 font-semibold">{profile.active_days} days</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-2">
              <span className="text-gray-400">Average Transaction Size:</span>
              <span className="text-gray-200 font-semibold">₹{profile.average_transaction_amount.toLocaleString()}</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-2">
              <span className="text-gray-400">Unique Counterparties:</span>
              <span className="text-cyan-400 font-semibold">{profile.unique_counterparties} entities</span>
            </div>
          </div>
        </div>

        {/* Peak Transactions */}
        <div className="p-5 rounded-2xl bg-[#0b0f19]/80 border border-white/10 backdrop-blur-xl">
          <h4 className="text-xs font-mono font-semibold text-gray-400 uppercase mb-4 flex items-center space-x-2">
            <BarChart2 className="w-4 h-4 text-purple-400" />
            <span>Peak Transaction Outliers</span>
          </h4>
          <div className="space-y-3 font-mono text-xs">
            <div className="p-2.5 rounded-lg bg-cyan-950/20 border border-cyan-500/20 flex justify-between items-center">
              <div>
                <span className="text-[10px] text-cyan-400 block uppercase">Peak Inflow (Credit)</span>
                <span className="text-sm font-bold text-white">
                  {profile.largest_credit_amount ? `₹${profile.largest_credit_amount.toLocaleString()}` : "N/A"}
                </span>
              </div>
              <ArrowDownRight className="w-5 h-5 text-cyan-400" />
            </div>

            <div className="p-2.5 rounded-lg bg-purple-950/20 border border-purple-500/20 flex justify-between items-center">
              <div>
                <span className="text-[10px] text-purple-400 block uppercase">Peak Outflow (Debit)</span>
                <span className="text-sm font-bold text-white">
                  {profile.largest_debit_amount ? `₹${profile.largest_debit_amount.toLocaleString()}` : "N/A"}
                </span>
              </div>
              <ArrowUpRight className="w-5 h-5 text-purple-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Behavioral Indicators */}
      {profile.indicators.length > 0 && (
        <div className="p-5 rounded-2xl bg-[#0b0f19]/80 border border-white/10 backdrop-blur-xl">
          <h4 className="text-xs font-mono font-semibold text-gray-400 uppercase mb-3">
            Factual Behavioral Indicators
          </h4>
          <div className="space-y-2">
            {profile.indicators.map((ind, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-surface/50 border border-white/5 text-xs text-gray-300 flex items-start space-x-2.5"
              >
                <span className="w-2 h-2 rounded-full bg-cyan-400 shrink-0 mt-1.5" />
                <span className="leading-relaxed">{ind}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
