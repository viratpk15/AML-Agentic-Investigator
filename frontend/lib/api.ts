import {
  InvestigationAPIResponse,
  InvestigationEvent,
  InvestigationStartResponse,
  InvestigationStatusResponse,
} from "@/types";

const rawUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_BASE_URL = rawUrl.replace(/\/+$/, "");

export async function checkBackendHealth(): Promise<{ status: string; service: string }> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
    if (!res.ok) throw new Error("Health check failed");
    return await res.json();
  } catch (err) {
    return { status: "offline", service: "aml-copilot" };
  }
}

export async function startInvestigation(
  file: File,
  question: string
): Promise<InvestigationStartResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("question", question);

  const res = await fetch(`${API_BASE_URL}/investigations`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server error (${res.status}): Failed to start investigation.`);
  }

  return await res.json();
}

export async function startDemoInvestigation(): Promise<InvestigationStartResponse> {
  const res = await fetch(`${API_BASE_URL}/investigations/demo`, {
    method: "POST",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server error (${res.status}): Failed to start demo investigation.`);
  }

  return await res.json();
}

export async function getInvestigation(
  investigationId: string
): Promise<InvestigationStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/investigations/${investigationId}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Investigation ${investigationId} not found.`);
  }

  return await res.json();
}

export function subscribeToInvestigationEvents(
  investigationId: string,
  onEvent: (event: InvestigationEvent) => void,
  onError: (err: any) => void,
  onComplete: () => void
): () => void {
  const url = `${API_BASE_URL}/investigations/${investigationId}/events`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener("investigation_event", (e: MessageEvent) => {
    try {
      const parsed: InvestigationEvent = JSON.parse(e.data);
      onEvent(parsed);

      if (
        parsed.event_type === "INVESTIGATION_COMPLETED" ||
        parsed.event_type === "INVESTIGATION_MAX_ITERATIONS" ||
        parsed.event_type === "INVESTIGATION_FAILED"
      ) {
        eventSource.close();
        onComplete();
      }
    } catch (err) {
      console.error("[SSE] Failed to parse event JSON:", err, e.data);
    }
  });

  eventSource.onmessage = (e: MessageEvent) => {
    try {
      const parsed: InvestigationEvent = JSON.parse(e.data);
      onEvent(parsed);
      if (
        parsed.event_type === "INVESTIGATION_COMPLETED" ||
        parsed.event_type === "INVESTIGATION_MAX_ITERATIONS" ||
        parsed.event_type === "INVESTIGATION_FAILED"
      ) {
        eventSource.close();
        onComplete();
      }
    } catch {
      // ignore
    }
  };

  eventSource.onerror = (err) => {
    console.warn("[SSE] EventSource connection error or closed:", err);
    eventSource.close();
    onError(err);
  };

  return () => {
    eventSource.close();
  };
}

// ---------------------------------------------------------------------------
// Synchronous Fallbacks (Preserved for compatibility)
// ---------------------------------------------------------------------------

export async function fetchDemoInvestigation(): Promise<InvestigationAPIResponse> {
  const res = await fetch(`${API_BASE_URL}/demo`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to load demo investigation report.");
  }
  return await res.json();
}

export async function submitInvestigation(
  file: File,
  question: string
): Promise<InvestigationAPIResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("question", question);

  const res = await fetch(`${API_BASE_URL}/investigate`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server error (${res.status}): Investigation failed.`);
  }

  return await res.json();
}

// ---------------------------------------------------------------------------
// Phase 8, 9, 11 Endpoints
// ---------------------------------------------------------------------------

export function getReportDownloadMarkdownUrl(investigationId: string): string {
  return `${API_BASE_URL}/investigations/${investigationId}/download/markdown`;
}

export function getReportDownloadJsonUrl(investigationId: string): string {
  return `${API_BASE_URL}/investigations/${investigationId}/download/json`;
}

export async function fetchTransactionEvidence(
  investigationId: string,
  transactionId: string
) {
  const res = await fetch(
    `${API_BASE_URL}/investigations/${investigationId}/transactions/${transactionId}`,
    { cache: "no-store" }
  );
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Transaction evidence for ${transactionId} not found.`);
  }
  return await res.json();
}

export async function fetchInvestigationHistory() {
  const res = await fetch(`${API_BASE_URL}/history`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error("Failed to load investigation history.");
  }
  return await res.json();
}

export async function fetchHistoricalReport(reportId: string) {
  const res = await fetch(`${API_BASE_URL}/history/${reportId}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to load historical report ${reportId}.`);
  }
  return await res.json();
}

