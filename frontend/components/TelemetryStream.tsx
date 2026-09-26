"use client";

import React, { useEffect, useRef } from "react";
import { Terminal, Activity } from "lucide-react";
import { TelemetryLog } from "@/types";

interface TelemetryStreamProps {
  logs: TelemetryLog[];
}

export default function TelemetryStream({ logs }: TelemetryStreamProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="w-full bg-[#0b0f19]/90 border border-white/10 rounded-2xl p-4 backdrop-blur-xl shadow-2xl font-mono text-xs">
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/10">
        <div className="flex items-center space-x-2 text-cyan-400">
          <Terminal className="w-4 h-4" />
          <span className="text-xs font-bold uppercase tracking-wider">LIVE TELEMETRY STREAM</span>
        </div>
        <div className="flex items-center space-x-2 text-[10px] text-gray-500">
          <Activity className="w-3 h-3 text-emerald-400 animate-pulse" />
          <span>EVENTS: {logs.length}</span>
        </div>
      </div>

      <div
        ref={containerRef}
        className="max-h-36 overflow-y-auto space-y-1.5 pr-2 font-mono scrollbar-thin scrollbar-thumb-white/10"
      >
        {logs.length === 0 ? (
          <div className="text-gray-600 italic py-2">System standby. Awaiting investigation trigger...</div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex items-start space-x-2.5 text-[11px] leading-relaxed">
              <span className="text-gray-500 shrink-0">[{log.timestamp}]</span>
              <span
                className={`font-semibold shrink-0 ${
                  log.type === "error"
                    ? "text-rose-400"
                    : log.type === "warning"
                    ? "text-amber-400"
                    : log.type === "success"
                    ? "text-emerald-400"
                    : "text-cyan-400"
                }`}
              >
                {log.source}:
              </span>
              <span className="text-gray-300">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
