// Official HHGOA Types matching backend/models/schemas.py and docs/frontend-backend-contract.md

export type StatusEnum = "open" | "closed_fraud" | "closed_legitimate" | "escalated";
export type VerdictEnum = "fraud" | "legitimate" | "uncertain";
export type PatternEnum =
  | "card_testing"
  | "card_not_present_fraud"
  | "card_not_present_new_device"
  | "out_of_region_use"
  | "account_takeover"
  | "undocumented"
  | "none";

export type ActionEnum =
  | "ALLOW_TRANSACTION"
  | "DECLINE_TRANSACTION"
  | "MONITOR_CARD"
  | "MONITOR_CONNECTED_CARDS"
  | "WARN_CUSTOMER"
  | "VERIFY_WITH_CUSTOMER"
  | "STEP_UP_AUTH"
  | "BLOCK_CARD"
  | "BLOCK_ALL_CARDS"
  | "GENERATE_REPORT"
  | "CREATE_CASE"
  | "FILE_REPORT"
  | "ESCALATE_TO_ANALYST"
  | "CLOSE_NO_FRAUD";

export type RouteEnum = "auto" | "L1" | "L2";
export type EvidenceTypeEnum = "customer_validation" | "step_up_auth" | "analyst_info";
export type SourceEnum = "graph" | "document" | "customer" | "external";

export interface EvidenceItem {
  claim: string;
  source: SourceEnum;
  ref: string;
  entity_ids: string[];
  category?: "TRANSACTION" | "CUSTOMER" | "CARD" | "DEVICE" | "NETWORK" | "HISTORICAL CASE";
  timestamp?: string;
  why_it_matters?: string;
}
export const EvidenceItem = {};

export interface CaseRecord {
  status: StatusEnum;
  verdict: VerdictEnum;
  fraud_probability: number;
  pattern: PatternEnum;
  pattern_description: string;
  affected_txn_ids: string[];
  first_suspicious_txn_id: string;
  connected_card_ids: string[];
  connected_device_profiles: string[];
  exposure_usd: number;
  evidence: EvidenceItem[];
  similar_prior_cases: string[];
  summary: string;
  written_to_graph: boolean;
  graph_case_id: string;
}
export const CaseRecord = {};

export interface SARRecord {
  file: boolean;
  reason: string;
  narrative: string;
  subjects: string[];
  total_amount_usd: number;
  activity_dates: string[];
}
export const SARRecord = {};

export interface ActionItem {
  action: ActionEnum;
  route: RouteEnum;
  reason: string;
  supporting_evidence?: string[];
}
export const ActionItem = {};

export interface NextBestActionsRecord {
  initial: ActionItem[];
  final: ActionItem[];
  what_changed: string;
}
export const NextBestActionsRecord = {};

export interface EvidenceRequestItem {
  type: EvidenceTypeEnum;
  asked_after_step: number;
  assumed_response: string;
  reason?: string;
  status?: "pending" | "received" | "waived";
}
export const EvidenceRequestItem = {};

export interface CaseAnswerFile {
  case_id: string;
  case: CaseRecord;
  evidence_requests: EvidenceRequestItem[];
  next_best_actions: NextBestActionsRecord;
  sar: SARRecord;
  stop_reason: string;
  tool_calls: number;
  tokens: number;
  latency_s: number;
}
export const CaseAnswerFile = {};

// Benchmark Cases (20 cases in case_pack.csv)
export interface BenchmarkCaseSummary {
  id: string;
  opened_at?: string;
  type: "risk_score" | "customer_report" | "analyst_request";
  desc: string;
  flagged_txn_id?: string;
  card_id?: string;
  customer_id?: string;
  risk_score?: number;
}
export const BenchmarkCaseSummary = {};

// Cytoscape Graph Types
export type NodeType =
  | "customer"
  | "card"
  | "card_compromised"
  | "device"
  | "txn_flagged"
  | "txn_testing"
  | "closed_case"
  | "email"
  | "region";

export interface GraphNode {
  id: string;
  label: string;
  type: NodeType;
  properties?: Record<string, any>;
}
export const GraphNode = {};

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  properties?: Record<string, any>;
}
export const GraphEdge = {};

export interface GraphData {
  case_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}
export const GraphData = {};

// SSE Event Stream Types
export type SSEEventType =
  | "TRIGGER_RECEIVED"
  | "GSQL_TRAVERSAL"
  | "GRAPH_CLUSTER"
  | "POLICY_EVALUATION"
  | "UNCERTAINTY_LOOP"
  | "EVIDENCE_INJECTED"
  | "NBA_FORMULATED"
  | "GRAPH_PERSISTED";

export interface SSEEvent {
  event: SSEEventType;
  data: string;
  timestamp?: string;
  step?: number;
  status?: "COMPLETED" | "ACTIVE" | "WAITING FOR EVIDENCE" | "FAILED" | "PENDING";
  tool?: string;
}
export const SSEEvent = {};

// Human Approval Action
export interface ApprovalRequest {
  action: ActionEnum;
  case_id: string;
  route: RouteEnum;
  analyst_id?: string;
  notes?: string;
}
export const ApprovalRequest = {};

export interface ApprovalResponse {
  status: "APPROVED" | "REJECTED";
  case_id: string;
  action: ActionEnum;
  executed_at: string;
  message: string;
}
export const ApprovalResponse = {};

// Case Memory Item
export interface CaseMemoryItem {
  case_id: string;
  similarity: "HIGH" | "MEDIUM" | "LOW";
  pattern: string;
  outcome: "confirmed_fraud" | "cleared";
  exposure_usd: number;
  actions_taken: string[];
  analyst_notes: string;
  opened_at?: string;
  closed_at?: string;
}
export const CaseMemoryItem = {};

// Step in Investigation Replay
export interface InvestigationStep {
  stepNumber: number;
  totalSteps: number;
  title: string;
  eventType: SSEEventType;
  description: string;
  toolCall?: string;
  evidenceSnippet?: string;
  confidenceScore?: number;
  status: "COMPLETED" | "ACTIVE" | "WAITING FOR EVIDENCE" | "FAILED" | "PENDING";
  timestamp: string;
}
export const InvestigationStep = {};
