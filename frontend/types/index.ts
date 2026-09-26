export interface EvidenceItem {
  transaction_id: string;
  date: string | null;
  amount: number | null;
  flow_type: "credit" | "debit" | null;
  counterparty: string | null;
  description: string | null;
  verified_in_statement: boolean;
}

export interface DetectionFindingItem {
  rule_id: string;
  rule_name: string;
  severity: "INFO" | "LOW" | "MEDIUM" | "HIGH";
  explanation: string;
  supporting_transaction_ids: string[];
  supporting_values: Record<string, any>;
}

export interface AnomalyFindingItem {
  transaction_id: string;
  anomaly_score: number;
  is_anomaly: boolean;
  feature_context: Record<string, number>;
}

export interface CustomerProfileSummary {
  customer_name: string | null;
  account_number: string | null;
  statement_period: string | null;
  total_transactions: number;
  total_credits: number;
  total_debits: number;
  net_cash_flow: number;
  average_transaction_amount: number;
  credit_to_debit_ratio: number | null;
  unique_counterparties: number;
  active_days: number;
  dominant_type: string;
  largest_credit_amount: number | null;
  largest_debit_amount: number | null;
  indicators: string[];
}

export interface NetworkFindingItem {
  pattern_name: string;
  description: string;
  involved_nodes: string[];
  supporting_transaction_ids: string[];
}

export interface KnowledgeReferenceItem {
  source: string;
  title: string | null;
  snippet: string | null;
}

export interface CriticSummary {
  passed: boolean;
  status: string;
  issues: string[];
  missing_evidence: string[];
  unsupported_claims: string[];
  safety_violations: string[];
  checked_transaction_ids: string[];
  invalid_transaction_ids: string[];
  required_revisions: string[];
  statement_transaction_count?: number;
  narrative_transaction_reference_count?: number;
  human_review_transaction_count?: number;
  verified_transaction_reference_count?: number;
  unverified_transaction_reference_count?: number;
}

export interface RevisionSummary {
  revision_count: number;
  max_revisions: number;
  revisions_applied: boolean;
  unresolved_limitations: boolean;
}

export interface NetworkSummary {
  unique_counterparties: number;
  graph_nodes: number;
  graph_edges: number;
  dominant_counterparties: string[];
}

export interface RuleSummaryGroup {
  rule_id: string;
  rule_name: string;
  granularity?: "TRANSACTION_LEVEL" | "EVENT_LEVEL" | string;
  finding_count?: number;
  associated_transaction_count?: number;
  count: number;
  severity: string;
  severity_distribution: Record<string, number>;
  supporting_transaction_ids: string[];
  representative_examples: any[];
  explanation: string;
}

export interface EvidenceConvergenceItem {
  transaction_id: string;
  date: string | null;
  amount: number | null;
  flow_type?: string | null;
  direction?: string | null;
  counterparty: string | null;
  signal_domains: string[];
  reasons: string[];
  priority: "HIGH" | "MEDIUM" | "LOW";
  convergence_summary: string;
}

export interface HumanReviewItem {
  transaction_id: string;
  date: string | null;
  amount: number | null;
  direction?: string | null;
  flow_type?: string | null;
  counterparty: string | null;
  reasons: string[];
  supporting_finding_ids: string[];
  priority: "HIGH" | "MEDIUM" | "LOW";
  evidence_summary: string;
}

export interface InvestigationReport {
  report_id: string;
  generated_at: string;
  customer_name: string;
  account_number: string;
  statement_period: string;
  investigation_question: string;
  total_transactions_analyzed?: number;
  executive_summary: string;
  observed_evidence: EvidenceItem[];
  detection_findings: DetectionFindingItem[];
  rule_summary_groups?: RuleSummaryGroup[];
  anomaly_findings: AnomalyFindingItem[];
  customer_profile: CustomerProfileSummary | null;
  network_summary?: NetworkSummary | null;
  network_findings: NetworkFindingItem[];
  aml_reference_context: KnowledgeReferenceItem[];
  evidence_convergence?: EvidenceConvergenceItem[];
  human_review_items?: HumanReviewItem[];
  human_review_summary?: {
    total_evaluated_count?: number;
    prioritized_review_count?: number;
    high_priority_count?: number;
    medium_priority_count?: number;
    low_priority_count?: number;
    [key: string]: any;
  };
  interpretation: string;
  critic_validation: CriticSummary;
  revision_history: RevisionSummary;
  limitations: string[];
  human_review_recommendation: string;
}

export interface TransactionEvidenceDossier {
  transaction_id: string;
  date: string | null;
  amount: number | null;
  flow_type: string | null;
  counterparty: string | null;
  description: string | null;
  verified_in_statement: boolean;
  is_anomaly: boolean;
  anomaly_score: number | null;
  anomaly_features: Record<string, number>;
  rules_triggered: Array<{
    rule_id: string;
    rule_name: string;
    severity: string;
    explanation: string;
    supporting_values: Record<string, any>;
  }>;
  network_patterns: Array<{
    pattern_name: string;
    description: string;
    involved_nodes: string[];
  }>;
  human_review_priority: string | null;
  human_review_reasons: string[];
  evidence_convergence_summary: string | null;
  signal_domains: string[];
  related_rag_guidance: Array<{
    source: string;
    guidance: string;
  }>;
}

export interface InvestigationHistoryRecord {
  investigation_id: string;
  report_id: string;
  timestamp: string;
  customer_name: string;
  account_number: string;
  statement_period: string;
  transaction_count: number;
  status: string;
  review_count: number;
  high_priority_count: number;
  runtime_seconds: number;
  report_path?: string | null;
}

export interface InvestigationAPIResponse {
  report: InvestigationReport;
  markdown: string;
  execution_time_seconds: number;
}

export interface InvestigationEvent {
  event_id: string;
  investigation_id: string;
  timestamp: string;
  event_type: string;
  node?: string | null;
  status?: string | null;
  message: string;
  tool_name?: string | null;
  iteration?: number;
  revision?: number;
  metadata?: Record<string, any>;
}

export interface InvestigationStartResponse {
  investigation_id: string;
  status: string;
  message: string;
}

export interface InvestigationStatusResponse {
  investigation_id: string;
  status: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | "MAX_ITERATIONS_REACHED";
  latest_event?: InvestigationEvent | null;
  report?: InvestigationReport | null;
  markdown?: string | null;
  execution_time_seconds?: number | null;
  error?: string | null;
}

export type EngineState =
  | "IDLE"
  | "QUEUED"
  | "ANALYZING"
  | "TOOL_EXECUTION"
  | "RAG_RETRIEVAL"
  | "SYNTHESIS"
  | "CRITIC"
  | "REVISION"
  | "COMPLETE"
  | "ERROR";

export interface TelemetryLog {
  id: string;
  timestamp: string;
  source: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
}
