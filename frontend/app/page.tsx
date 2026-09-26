"use client";

import React, { useState, useEffect, useRef } from "react";
import Header from "@/components/Header";
import Sidebar, { NavTab } from "@/components/Sidebar";
import InvestigationCore3D from "@/components/InvestigationCore3D";
import LangGraphVisualizer from "@/components/LangGraphVisualizer";
import InvestigationUploadForm from "@/components/InvestigationUploadForm";
import EvidenceTable from "@/components/EvidenceTable";
import DetectionPanel from "@/components/DetectionPanel";
import CustomerProfilePanel from "@/components/CustomerProfilePanel";
import NetworkGraphView from "@/components/NetworkGraphView";
import KnowledgePanel from "@/components/KnowledgePanel";
import CriticPanel from "@/components/CriticPanel";
import ReportView from "@/components/ReportView";
import EvidenceConvergencePanel from "@/components/EvidenceConvergencePanel";
import TransactionDetailDrawer from "@/components/TransactionDetailDrawer";
import InvestigationHistoryModal from "@/components/InvestigationHistoryModal";
import TelemetryStream from "@/components/TelemetryStream";
import {
  checkBackendHealth,
  getInvestigation,
  startDemoInvestigation,
  startInvestigation,
  subscribeToInvestigationEvents,
} from "@/lib/api";
import {
  EngineState,
  InvestigationEvent,
  InvestigationReport,
  InvestigationStatusResponse,
  TelemetryLog,
} from "@/types";
import {
  Receipt,
  ShieldAlert,
  FileCheck2,
  Layers,
  Activity,
  AlertTriangle,
  AlertCircle,
  Calendar,
  User,
  ArrowRight,
} from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState<NavTab>("overview");
  const [engineState, setEngineState] = useState<EngineState>("IDLE");
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [revisionCount, setRevisionCount] = useState<number>(0);
  const [criticPassed, setCriticPassed] = useState<boolean>(true);
  const [criticIssues, setCriticIssues] = useState<string[]>([]);
  const [currentReport, setCurrentReport] = useState<InvestigationReport | null>(null);
  const [currentMarkdown, setCurrentMarkdown] = useState<string>("");
  const [selectedTransactionId, setSelectedTransactionId] = useState<string | null>(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(true);
  const [logs, setLogs] = useState<TelemetryLog[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const activeSubscriptionRef = useRef<(() => void) | null>(null);
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  const addLog = (
    source: string,
    message: string,
    type: "info" | "success" | "warning" | "error" = "info"
  ) => {
    const timestamp = new Date().toTimeString().split(" ")[0];
    const newLog: TelemetryLog = {
      id: Math.random().toString(36).substring(7),
      timestamp,
      source,
      message,
      type,
    };
    setLogs((prev) => [...prev, newLog]);
  };

  // Initial mount health check & greeting
  useEffect(() => {
    async function init() {
      const health = await checkBackendHealth();
      setIsBackendOnline(health.status === "ok");
      addLog("System", "AML // Intelligence Core initialized.", "info");
      addLog("SSE Engine", "Real-time investigation event stream client ready.", "info");
      addLog("LangGraph", "Multi-role agent state machine standing by.", "info");
    }
    init();

    return () => {
      if (activeSubscriptionRef.current) {
        activeSubscriptionRef.current();
        activeSubscriptionRef.current = null;
      }
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, []);

  // Process live backend SSE events
  const handleLiveEvent = (event: InvestigationEvent) => {
    const sourceName = event.tool_name
      ? `Tool [${event.tool_name}]`
      : event.node
      ? event.node.toUpperCase()
      : "Engine";

    let logType: "info" | "success" | "warning" | "error" = "info";
    if (
      event.event_type === "CRITIC_FAILED" ||
      event.event_type === "INVESTIGATION_FAILED"
    ) {
      logType = "error";
    } else if (event.event_type === "REVISION_STARTED") {
      logType = "warning";
    } else if (
      event.event_type === "CRITIC_PASSED" ||
      event.event_type === "INVESTIGATION_COMPLETED" ||
      event.event_type === "REPORT_GENERATED"
    ) {
      logType = "success";
    }

    addLog(sourceName, event.message, logType);

    // Dynamic state mappings from real events
    switch (event.event_type) {
      case "INVESTIGATION_STARTED":
        setEngineState("ANALYZING");
        setActiveNode("investigator");
        break;
      case "NODE_STARTED":
        if (event.node === "investigator") {
          setEngineState("ANALYZING");
          setActiveNode("investigator");
        }
        break;
      case "TOOL_STARTED":
        setEngineState("TOOL_EXECUTION");
        setActiveNode("tools");
        setActiveTool(event.tool_name || null);
        break;
      case "RAG_STARTED":
        setEngineState("RAG_RETRIEVAL");
        setActiveNode("tools");
        setActiveTool("search_aml_knowledge");
        break;
      case "RAG_COMPLETED":
        setEngineState("TOOL_EXECUTION");
        break;
      case "TOOL_COMPLETED":
        setActiveTool(null);
        break;
      case "SYNTHESIS_STARTED":
        setEngineState("SYNTHESIS");
        setActiveNode("synthesis");
        break;
      case "CRITIC_STARTED":
        setEngineState("CRITIC");
        setActiveNode("critic");
        break;
      case "CRITIC_FAILED":
        setEngineState("CRITIC");
        setActiveNode("critic");
        setCriticPassed(false);
        if (event.metadata?.issues) {
          setCriticIssues(event.metadata.issues);
        }
        break;
      case "REVISION_STARTED":
        setEngineState("REVISION");
        setActiveNode("revision");
        setRevisionCount(event.revision || 1);
        break;
      case "CRITIC_PASSED":
        setEngineState("CRITIC");
        setActiveNode("critic");
        setCriticPassed(true);
        break;
      case "REPORT_GENERATED":
        setEngineState("COMPLETE");
        setActiveNode("report");
        break;
      case "INVESTIGATION_COMPLETED":
        setEngineState("COMPLETE");
        setActiveNode("report");
        break;
      case "INVESTIGATION_MAX_ITERATIONS":
        setEngineState("COMPLETE");
        setActiveNode("report");
        break;
      case "INVESTIGATION_FAILED": {
        setEngineState("ERROR");
        setActiveNode(null);
        // Build a structured diagnostic message from backend metadata
        const meta = event.metadata || {};
        const stage = meta.error_stage ? `during ${meta.error_stage.replace(/_/g, " ")}` : "";
        const errType = meta.error_type ? `${meta.error_type}: ` : "";
        const reqId = meta.request_id ? ` [ID: ${meta.request_id}]` : "";
        const humanMsg = `Investigation failed ${stage}. ${errType}${event.message}${reqId}`.trim();
        setErrorMessage(humanMsg);
        break;
      }
    }
  };

  // Demo mode toggle using real SSE pipeline
  const handleToggleDemoMode = async () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    if (isDemoMode) {
      if (activeSubscriptionRef.current) {
        activeSubscriptionRef.current();
        activeSubscriptionRef.current = null;
      }
      setIsDemoMode(false);
      setCurrentReport(null);
      setCurrentMarkdown("");
      setErrorMessage(null);
      setEngineState("IDLE");
      setActiveNode(null);
      setActiveTool(null);
      setRevisionCount(0);
      setCriticPassed(true);
      setCriticIssues([]);
      addLog("System", "Demo mode deactivated. Switched to live statement input.", "info");
      return;
    }

    try {
      setIsLoading(true);
      setErrorMessage(null);
      setEngineState("QUEUED");
      setActiveNode(null);
      setRevisionCount(0);
      setCriticPassed(true);
      setCriticIssues([]);
      setIsDemoMode(true);
      addLog("Demo Engine", "Submitting synthetic suspicious statement to live event bus...", "info");

      const startRes = await startDemoInvestigation();
      const invId = startRes.investigation_id;
      addLog("System", `Demo investigation queued (${invId}). Subscribing to SSE stream...`, "info");

      let isFinished = false;
      const finishDemo = (statusData: any) => {
        if (isFinished) return;
        if (statusData.report) {
          isFinished = true;
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          if (activeSubscriptionRef.current) {
            activeSubscriptionRef.current();
            activeSubscriptionRef.current = null;
          }
          setCurrentReport(statusData.report);
          setCurrentMarkdown(statusData.markdown || "");
          setEngineState("COMPLETE");
          setActiveNode("report");
          addLog(
            "System",
            `Demo investigation concluded (${statusData.execution_time_seconds || 1.2}s). Report: ${statusData.report.report_id}`,
            "success"
          );
          setIsLoading(false);
        }
      };

      // Polling fallback
      pollTimerRef.current = setInterval(async () => {
        if (isFinished) return;
        try {
          const statusData = await getInvestigation(invId);
          if (statusData.report) finishDemo(statusData);
        } catch {
          // ignore
        }
      }, 1000);

      // Subscribe to real Server-Sent Events stream
      activeSubscriptionRef.current = subscribeToInvestigationEvents(
        invId,
        handleLiveEvent,
        (err) => {
          console.warn("[Demo SSE Error]", err);
        },
        async () => {
          for (let attempt = 0; attempt < 8; attempt++) {
            if (isFinished) break;
            try {
              const statusData = await getInvestigation(invId);
              if (statusData.report) {
                finishDemo(statusData);
                break;
              }
            } catch (fetchErr: any) {
              console.warn(`[Demo Status Retry ${attempt + 1}]`, fetchErr);
            }
            await new Promise((r) => setTimeout(r, 400));
          }
        }
      );
    } catch (err: any) {
      addLog("Demo Engine", `Failed to start demo investigation: ${err.message}`, "error");
      setEngineState("ERROR");
      setErrorMessage(err.message || "Failed to start demo investigation.");
      setIsLoading(false);
    }
  };

  // Live PDF investigation submission with dual real-time SSE streaming & polling fallback
  const handleStartInvestigation = async (file: File, question: string) => {
    if (activeSubscriptionRef.current) {
      activeSubscriptionRef.current();
      activeSubscriptionRef.current = null;
    }
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setEngineState("QUEUED");
    setActiveNode(null);
    setActiveTool(null);
    setRevisionCount(0);
    setCriticPassed(true);
    setCriticIssues([]);
    setCurrentReport(null);
    setCurrentMarkdown("");

    addLog("Ingestion", `Uploading '${file.name}' (${(file.size / 1024).toFixed(1)} KB)...`, "info");

    try {
      const startRes = await startInvestigation(file, question);
      const invId = startRes.investigation_id;
      addLog("System", `Investigation queued [${invId}]. Connecting to real-time SSE telemetry & status monitor...`, "info");

      let isFinished = false;

      const finishInvestigation = (statusData: InvestigationStatusResponse) => {
        if (isFinished) return;
        if (statusData.report) {
          isFinished = true;
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          if (activeSubscriptionRef.current) {
            activeSubscriptionRef.current();
            activeSubscriptionRef.current = null;
          }
          setCurrentReport(statusData.report);
          setCurrentMarkdown(statusData.markdown || "");
          setEngineState("COMPLETE");
          setActiveNode("report");
          addLog(
            "System",
            `Investigation concluded (${statusData.execution_time_seconds || 0}s). Report ID: ${statusData.report.report_id}`,
            "success"
          );
          // Switch to report tab upon completion
          setActiveTab("report");
          setIsLoading(false);
          setErrorMessage(null);
        } else if (statusData.status === "FAILED" || statusData.error) {
          isFinished = true;
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          if (activeSubscriptionRef.current) {
            activeSubscriptionRef.current();
            activeSubscriptionRef.current = null;
          }
          setEngineState("ERROR");
          const rawError = statusData.error || "Investigation failed on server.";
          // Parse stage/type from structured error string: "[stage] ExcType: message"
          const stageMatch = rawError.match(/^\[([\w_]+)\]\s*/);
          const stageLabel = stageMatch
            ? `during ${stageMatch[1].replace(/_/g, " ")}`
            : "";
          const cleanError = stageMatch ? rawError.slice(stageMatch[0].length) : rawError;
          const humanMsg = stageLabel
            ? `Investigation failed ${stageLabel}. ${cleanError}`
            : cleanError;
          setErrorMessage(humanMsg);
          addLog("Error", humanMsg, "error");
          setIsLoading(false);
        }
      };

      // 1. Rock-solid polling fallback every 1.5s
      pollTimerRef.current = setInterval(async () => {
        if (isFinished) return;
        try {
          const statusData = await getInvestigation(invId);
          if (statusData.report || statusData.status === "FAILED" || statusData.error) {
            finishInvestigation(statusData);
          }
        } catch (pollErr: any) {
          console.warn("[Poll status check]", pollErr);
        }
      }, 1500);

      // 2. Real-time Server-Sent Events stream for instant live topology transitions
      activeSubscriptionRef.current = subscribeToInvestigationEvents(
        invId,
        handleLiveEvent,
        (err) => {
          console.warn("[Investigation SSE warning - polling fallback is active]:", err);
        },
        async () => {
          // Terminal completion callback: retry fetching status up to 10 times with 500ms spacing
          for (let attempt = 0; attempt < 10; attempt++) {
            if (isFinished) break;
            try {
              const statusData = await getInvestigation(invId);
              if (statusData.report || statusData.status === "FAILED" || statusData.error) {
                finishInvestigation(statusData);
                break;
              }
            } catch (statusErr: any) {
              console.warn(`[Investigation Status Retry ${attempt + 1}]`, statusErr);
            }
            await new Promise((r) => setTimeout(r, 500));
          }
        }
      );
    } catch (err: any) {
      setEngineState("ERROR");
      const errDetail = err.message || "Failed to initiate investigation.";
      setErrorMessage(errDetail);
      addLog("Error", errDetail, "error");
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#030712] text-gray-100 flex flex-col font-sans">
      <Header
        isDemoMode={isDemoMode}
        onToggleDemoMode={handleToggleDemoMode}
        onOpenHistory={() => setIsHistoryOpen(true)}
        caseId={currentReport ? currentReport.report_id : "CASE #AML-2026-LIVE"}
        isBackendOnline={isBackendOnline}
      />

      <div className="flex flex-1">
        <Sidebar
          currentTab={activeTab}
          onSelectTab={setActiveTab}
          hasReport={currentReport !== null}
        />

        <main className="flex-1 p-6 overflow-y-auto space-y-6 max-w-7xl mx-auto w-full">
          {/* OVERVIEW TAB */}
          {activeTab === "overview" && (
            <div className="space-y-6">
              {/* Top Banner */}
              <div className="p-6 rounded-2xl bg-gradient-to-r from-surface via-[#091122] to-surface border border-cyan-500/20 shadow-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                  <div className="text-[11px] font-mono text-cyan-400 uppercase tracking-widest flex items-center space-x-2">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                    <span>Real-Time AI Financial Intelligence Command Center</span>
                  </div>
                  <h2 className="text-2xl font-black text-white tracking-wide mt-1">
                    {currentReport ? currentReport.customer_name : "Live LangGraph Investigation"}
                  </h2>
                  <p className="text-xs text-gray-400 max-w-xl mt-1 font-mono">
                    Event-driven agentic orchestrator streaming real LangGraph transitions,
                    Isolation Forest anomalies, NetworkX relationships, and deterministic Critic validation.
                  </p>
                </div>

                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => setActiveTab("investigate")}
                    className="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black font-mono text-xs font-bold transition-all shadow-glow"
                  >
                    + NEW INVESTIGATION
                  </button>
                  <button
                    onClick={() => setIsHistoryOpen(true)}
                    className="px-4 py-2 rounded-xl bg-surface hover:bg-surface/80 border border-white/10 text-gray-300 font-mono text-xs transition-all"
                  >
                    ARCHIVE HISTORY
                  </button>
                  {!currentReport && (
                    <button
                      onClick={handleToggleDemoMode}
                      className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500/20 to-purple-500/20 hover:from-cyan-500/30 hover:to-purple-500/30 border border-cyan-500/40 text-cyan-300 font-mono text-xs font-bold transition-all"
                    >
                      RUN AML DEMO
                    </button>
                  )}
                </div>
              </div>

              {errorMessage && (
                <div className="p-4 rounded-xl bg-rose-950/70 border border-rose-500/50 text-rose-200 flex items-start space-x-3 shadow-lg">
                  <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <div className="font-bold text-sm">Investigation Notice</div>
                    <div className="text-xs text-rose-300 mt-1 font-mono break-all">{errorMessage}</div>
                  </div>
                  <button
                    onClick={() => setErrorMessage(null)}
                    className="text-xs text-rose-400 hover:text-white px-2 py-1"
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* POST-COMPLETION TOP PROFILE & 4 KPI CARDS (PHASE 6) */}
              {currentReport && (
                <div className="space-y-4">
                  {/* Customer + Period + Status */}
                  <div className="p-4 rounded-xl bg-surface/90 border border-white/10 flex flex-wrap items-center justify-between gap-3 font-mono text-xs">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
                        <User className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-gray-400 text-[10px] block">CUSTOMER / ACCOUNT</span>
                        <span className="font-bold text-white text-sm">{currentReport.customer_name}</span>
                        <span className="text-cyan-400 ml-2">({currentReport.account_number})</span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      <div className="p-2 rounded-lg bg-white/5 text-gray-400">
                        <Calendar className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-gray-400 text-[10px] block">STATEMENT PERIOD</span>
                        <span className="text-gray-200">{currentReport.statement_period}</span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold">
                        STATUS: {currentReport.critic_validation.status}
                      </span>
                      <button
                        onClick={() => setActiveTab("convergence")}
                        className="px-3 py-1 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 text-cyan-300 font-bold flex items-center space-x-1 transition-all"
                      >
                        <span>EVIDENCE CONVERGENCE</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* 4 CORE KPI CARDS */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono">
                    <div className="p-4 rounded-xl bg-surface/80 border border-white/10 shadow-lg">
                      <div className="flex items-center justify-between text-gray-400 text-xs">
                        <span>TRANSACTIONS</span>
                        <Receipt className="w-4 h-4 text-cyan-400" />
                      </div>
                      <div className="text-3xl font-black text-white mt-1">
                        {currentReport.total_transactions_analyzed || currentReport.observed_evidence.length}
                      </div>
                      <div className="text-[10px] text-gray-500 mt-0.5">Total analyzed</div>
                    </div>

                    <div className="p-4 rounded-xl bg-surface/80 border border-purple-500/30 shadow-lg">
                      <div className="flex items-center justify-between text-purple-400 text-xs">
                        <span>STATISTICAL OUTLIERS</span>
                        <Activity className="w-4 h-4 text-purple-400" />
                      </div>
                      <div className="text-3xl font-black text-purple-300 mt-1">
                        {currentReport.anomaly_findings.length}
                      </div>
                      <div className="text-[10px] text-gray-500 mt-0.5">Isolation Forest outliers</div>
                    </div>

                    <div className="p-4 rounded-xl bg-surface/80 border border-white/10 shadow-lg">
                      <div className="flex items-center justify-between text-cyan-400 text-xs">
                        <span>REVIEW ITEMS</span>
                        <Layers className="w-4 h-4 text-cyan-400" />
                      </div>
                      <div className="text-3xl font-black text-cyan-300 mt-1">
                        {currentReport.human_review_items?.length || 50}
                      </div>
                      <div className="text-[10px] text-gray-500 mt-0.5">Prioritized queue items</div>
                    </div>

                    <div className="p-4 rounded-xl bg-surface/80 border border-rose-500/30 shadow-lg">
                      <div className="flex items-center justify-between text-rose-400 text-xs">
                        <span>HIGH PRIORITY</span>
                        <AlertTriangle className="w-4 h-4 text-rose-400" />
                      </div>
                      <div className="text-3xl font-black text-rose-400 mt-1">
                        {currentReport.human_review_items?.filter((i) => i.priority === "HIGH").length || 25}
                      </div>
                      <div className="text-[10px] text-gray-500 mt-0.5">Multi-signal convergence</div>
                    </div>
                  </div>
                </div>
              )}

              {/* 3D Core + Real-time KPI Cards */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
                <div className="lg:col-span-2">
                  <InvestigationCore3D state={engineState} />
                </div>

                {/* Real-time stats */}
                <div className="space-y-3">
                  <div className="p-4 rounded-xl bg-surface/80 border border-white/5 backdrop-blur-md">
                    <div className="flex items-center justify-between text-gray-400 text-xs font-mono">
                      <span>VERIFIED EVIDENCE</span>
                      <Receipt className="w-4 h-4 text-cyan-400" />
                    </div>
                    <div className="text-2xl font-bold font-mono text-white mt-1">
                      {currentReport ? currentReport.observed_evidence.length : 0}
                    </div>
                    <div className="text-[10px] text-gray-500 font-mono mt-0.5">
                      Transactions referenced
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-surface/80 border border-white/5 backdrop-blur-md">
                    <div className="flex items-center justify-between text-gray-400 text-xs font-mono">
                      <span>RULE SIGNALS</span>
                      <ShieldAlert className="w-4 h-4 text-amber-400" />
                    </div>
                    <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
                      {currentReport ? currentReport.detection_findings.length : 0}
                    </div>
                    <div className="text-[10px] text-gray-500 font-mono mt-0.5">
                      Automated screening leads
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-surface/80 border border-white/5 backdrop-blur-md">
                    <div className="flex items-center justify-between text-gray-400 text-xs font-mono">
                      <span>CRITIC AUDIT</span>
                      <FileCheck2 className="w-4 h-4 text-emerald-400" />
                    </div>
                    <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
                      {currentReport
                        ? currentReport.critic_validation.status
                        : !criticPassed
                        ? "FAIL"
                        : "STANDBY"}
                    </div>
                    <div className="text-[10px] text-gray-500 font-mono mt-0.5">
                      {revisionCount > 0
                        ? `${revisionCount} self-correction revision(s) active`
                        : "Adversarial audit guard active"}
                    </div>
                  </div>
                </div>
              </div>

              {/* LangGraph Live Node Topology Driven by Real Events */}
              <LangGraphVisualizer
                engineState={engineState}
                activeNode={activeNode}
                activeTool={activeTool}
                revisionCount={revisionCount || currentReport?.revision_history.revision_count || 0}
                criticPassed={criticPassed}
                criticIssues={criticIssues}
              />

              {/* Real Telemetry Stream */}
              <TelemetryStream logs={logs} />
            </div>
          )}

          {/* INVESTIGATE TAB */}
          {activeTab === "investigate" && (
            <div className="space-y-6">
              {errorMessage && (
                <div className="p-4 rounded-xl bg-rose-950/70 border border-rose-500/50 text-rose-200 flex items-start space-x-3 shadow-lg">
                  <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <div className="font-bold text-sm">Investigation Notice</div>
                    <div className="text-xs text-rose-300 mt-1 font-mono break-all">{errorMessage}</div>
                  </div>
                  <button
                    onClick={() => setErrorMessage(null)}
                    className="text-xs text-rose-400 hover:text-white px-2 py-1"
                  >
                    ✕
                  </button>
                </div>
              )}
              <InvestigationUploadForm
                onSubmit={handleStartInvestigation}
                isLoading={isLoading}
              />
              <LangGraphVisualizer
                engineState={engineState}
                activeNode={activeNode}
                activeTool={activeTool}
                revisionCount={revisionCount || currentReport?.revision_history.revision_count || 0}
                criticPassed={criticPassed}
                criticIssues={criticIssues}
              />
              <TelemetryStream logs={logs} />
            </div>
          )}

          {/* CONVERGENCE TAB */}
          {activeTab === "convergence" && (
            currentReport ? (
              <EvidenceConvergencePanel
                report={currentReport}
                onSelectTransaction={(tid) => setSelectedTransactionId(tid)}
              />
            ) : (
              <div className="p-12 text-center bg-surface/50 border border-white/5 rounded-2xl text-gray-500 font-mono text-xs">
                No active investigation report. Run an investigation or load demo data to view evidence convergence.
              </div>
            )
          )}

          {/* TRANSACTIONS / EVIDENCE TAB */}
          {activeTab === "transactions" && (
            <EvidenceTable
              evidence={currentReport?.observed_evidence || []}
              onSelectTransaction={(tid) => setSelectedTransactionId(tid)}
            />
          )}

          {/* DETECTION TAB */}
          {activeTab === "detection" && (
            <DetectionPanel
              ruleSignals={currentReport?.detection_findings || []}
              anomalySignals={currentReport?.anomaly_findings || []}
            />
          )}

          {/* CUSTOMER PROFILE TAB */}
          {activeTab === "profile" && (
            <CustomerProfilePanel profile={currentReport?.customer_profile || null} />
          )}

          {/* NETWORK TAB */}
          {activeTab === "network" && (
            <NetworkGraphView
              customerName={currentReport?.customer_name || "Customer Account"}
              evidence={currentReport?.observed_evidence || []}
              networkFindings={currentReport?.network_findings || []}
              onSelectTransaction={(tid) => setSelectedTransactionId(tid)}
            />
          )}

          {/* KNOWLEDGE / RAG TAB */}
          {activeTab === "knowledge" && (
            <KnowledgePanel references={currentReport?.aml_reference_context || []} />
          )}

          {/* CRITIC / AUDIT TAB */}
          {activeTab === "critic" && (
            currentReport ? (
              <CriticPanel
                critic={currentReport.critic_validation}
                revision={currentReport.revision_history}
              />
            ) : (
              <div className="p-12 text-center bg-surface/50 border border-white/5 rounded-2xl text-gray-500 font-mono text-xs">
                No active investigation report. Run an investigation or toggle Demo Mode to review Critic verification.
              </div>
            )
          )}

          {/* REPORT VIEW TAB */}
          {activeTab === "report" && (
            currentReport ? (
              <ReportView report={currentReport} markdown={currentMarkdown} />
            ) : (
              <div className="p-12 text-center bg-surface/50 border border-white/5 rounded-2xl text-gray-500 font-mono text-xs">
                No report has been compiled yet. Start an investigation or load demo data to view the final report.
              </div>
            )
          )}
        </main>
      </div>

      {/* Transaction Detail Drawer */}
      <TransactionDetailDrawer
        report={currentReport}
        transactionId={selectedTransactionId}
        onClose={() => setSelectedTransactionId(null)}
      />

      {/* Investigation History Modal */}
      <InvestigationHistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectReport={(report, md) => {
          setCurrentReport(report);
          setCurrentMarkdown(md);
          setActiveTab("report");
        }}
      />
    </div>
  );
}
