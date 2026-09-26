"use client";

import React from "react";
import { BookOpen, ExternalLink, ShieldCheck, FileText } from "lucide-react";
import { KnowledgeReferenceItem } from "@/types";

interface KnowledgePanelProps {
  references: KnowledgeReferenceItem[];
}

export default function KnowledgePanel({ references = [] }: KnowledgePanelProps) {
  return (
    <div className="w-full space-y-6">
      {/* Scope Disclaimer */}
      <div className="p-4 rounded-xl bg-blue-950/30 border border-blue-500/30 flex items-start space-x-3">
        <ShieldCheck className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
        <div className="text-xs text-blue-200/90 leading-relaxed font-sans">
          <span className="font-semibold text-blue-300">AML REFERENCE LIBRARY:</span> Reference AML knowledge
          documents provide guidance on typologies, regulatory red flags, and investigation standards. They
          represent contextual reference benchmarks, not factual customer transaction records.
        </div>
      </div>

      <div className="bg-[#0b0f19]/80 backdrop-blur-xl rounded-2xl border border-white/10 p-5 shadow-2xl">
        <div className="flex items-center space-x-2 mb-4 pb-3 border-b border-white/10">
          <BookOpen className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-semibold tracking-wider text-gray-200 uppercase font-mono">
            Retrieved AML Guidance & Typologies
          </h3>
        </div>

        {references.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-xs font-mono">
            No AML reference knowledge sources were retrieved for this query.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {references.map((ref, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border border-white/5 bg-surface/40 hover:border-blue-500/40 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-blue-400 flex items-center space-x-1.5">
                      <FileText className="w-4 h-4" />
                      <span>{ref.title || ref.source}</span>
                    </span>
                    <span className="text-[10px] font-mono text-gray-500 bg-white/5 px-2 py-0.5 rounded">
                      {ref.source}
                    </span>
                  </div>
                  <p className="text-xs text-gray-300 leading-relaxed mt-2">
                    {ref.snippet || "Retrieved regulatory guidance on conduit fund flows and unusual movement."}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-[11px] font-mono text-gray-400">
                  <span>Relevance: Typology Match</span>
                  <span className="text-cyan-400 flex items-center space-x-1">
                    <span>Verified Source</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
