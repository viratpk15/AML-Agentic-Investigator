"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, FileText, Sparkles, AlertCircle, ArrowRight } from "lucide-react";

interface InvestigationUploadFormProps {
  onSubmit: (file: File, question: string) => Promise<void>;
  isLoading: boolean;
}

export default function InvestigationUploadForm({
  onSubmit,
  isLoading,
}: InvestigationUploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [question, setQuestion] = useState(
    "Investigate unusual movement of funds in this account and highlight transactions requiring human review."
  );
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const presets = [
    "Investigate unusual movement of funds in this account and highlight transactions requiring human review.",
    "Inspect TXN005 and evaluate counterparty relationships for rapid pass-through conduit flow.",
    "Analyze overall transaction turnover, active days, and customer behavioral profile indicators.",
  ];

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (uploadedFile: File) => {
    setError(null);
    if (!uploadedFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files (.pdf) are supported for bank statement ingestion.");
      return;
    }
    setFile(uploadedFile);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a customer bank statement PDF to investigate.");
      return;
    }
    if (!question.trim()) {
      setError("Please enter an investigation question.");
      return;
    }
    setError(null);
    await onSubmit(file, question);
  };

  return (
    <div className="w-full bg-[#0b0f19]/90 border border-white/10 rounded-2xl p-6 backdrop-blur-xl shadow-2xl space-y-6">
      <div className="flex items-center space-x-2 pb-3 border-b border-white/10">
        <UploadCloud className="w-5 h-5 text-cyan-400" />
        <h3 className="text-sm font-semibold tracking-wider text-gray-200 uppercase font-mono">
          Initiate New Statement Investigation
        </h3>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Drag and Drop Zone */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`w-full p-8 border-2 border-dashed rounded-xl cursor-pointer transition-all flex flex-col items-center justify-center text-center ${
            dragActive
              ? "border-cyan-400 bg-cyan-950/30"
              : file
              ? "border-emerald-500/50 bg-emerald-950/10"
              : "border-white/10 bg-surface/30 hover:border-cyan-500/40 hover:bg-surface/50"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            className="hidden"
          />

          {file ? (
            <div className="flex items-center space-x-3 text-emerald-400">
              <FileText className="w-8 h-8" />
              <div className="text-left font-mono">
                <div className="text-sm font-bold text-white">{file.name}</div>
                <div className="text-xs text-gray-400">{(file.size / 1024).toFixed(1)} KB • Ready for Ingestion</div>
              </div>
            </div>
          ) : (
            <div>
              <UploadCloud className="w-10 h-10 text-cyan-400 mx-auto mb-2 opacity-80" />
              <p className="text-xs font-mono text-gray-300">
                DRAG & DROP BANK STATEMENT PDF HERE, OR <span className="text-cyan-400 underline">BROWSE</span>
              </p>
              <p className="text-[10px] text-gray-500 font-mono mt-1">Accepts standard PDF transaction ledgers</p>
            </div>
          )}
        </div>

        {/* Question Input */}
        <div>
          <label className="block text-xs font-mono font-semibold text-gray-300 uppercase mb-1.5">
            Investigation Objective / Query
          </label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            className="w-full p-3 rounded-xl bg-surface border border-white/10 text-xs text-gray-200 font-sans focus:outline-none focus:border-cyan-500/60 transition-all resize-none"
            placeholder="E.g., Investigate unusual activity in this account..."
          />
        </div>

        {/* Quick-fill Presets */}
        <div>
          <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider block mb-1.5">
            Quick-Fill Investigation Templates:
          </span>
          <div className="flex flex-wrap gap-2">
            {presets.map((preset, idx) => (
              <button
                type="button"
                key={idx}
                onClick={() => setQuestion(preset)}
                className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-surface/60 hover:bg-surface border border-white/5 text-gray-400 hover:text-cyan-300 transition-all text-left"
              >
                Template 0{idx + 1}
              </button>
            ))}
          </div>
        </div>

        {/* Error notification */}
        {error && (
          <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 text-xs text-rose-300 flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Action */}
        <button
          type="submit"
          disabled={isLoading}
          className={`w-full py-3.5 px-6 rounded-xl font-mono text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center space-x-2 ${
            isLoading
              ? "bg-cyan-950 text-cyan-400 cursor-not-allowed border border-cyan-500/30 animate-pulse"
              : "bg-cyan-500 hover:bg-cyan-400 text-black shadow-glow hover:shadow-cyan-400/50"
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>{isLoading ? "ORCHESTRATING INVESTIGATION..." : "EXECUTE MULTI-ROLE INVESTIGATION"}</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
