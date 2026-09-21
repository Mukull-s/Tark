export interface CaseMetadata {
	case_id: string;
	opened_at: string;
	trigger_type: string;
	trigger_text: string;
	flagged_txn_id: string;
	card_id: string;
	customer_id: string;
	risk_score: number | null;
	status?: string;
}

export interface HealthStatus {
	status: string;
	tigergraph: "connected" | "disconnected";
	total_cases: number;
	frozen_memory_cases: number;
	timestamp: string;
}

export interface EvidenceItemView {
	evidence_id: string;
	evidence_type: string;
	source: string;
	finding: string;
	value: any;
	lr: number;
	log_lr: number;
	is_exculpatory: boolean;
	observed_at: string;
	details?: Record<string, any>;
}

export interface IterationTraceView {
	iteration: number;
	selected_action: string;
	candidate_net_decision_values?: Record<string, number>;
	belief_before:
		| number
		| {
				fraud_probability: number;
				log_odds?: number;
		  };
	belief_after:
		| number
		| {
				fraud_probability: number;
				log_odds?: number;
		  };
	coverage_before?: number;
	coverage_after?: number;
	observed_evidence_summary?: string;
	termination_check?: any;
	mcp_telemetry?: {
		tool_name?: string;
		action_id?: string;
		status?: string;
		duration_ms?: number;
		session_id?: string;
		request_id?: string;
		[key: string]: any;
	};
}

export interface ActionRecommendationView {
	action: string;
	role: "primary" | "consequential" | "secondary";
	approval_route: string;
	reason: string;
	scope: string;
}

export interface SimilarPrecedentView {
	case_id: string;
	similarity_score: number;
	historical_outcome: string;
	pattern: string;
	exposure_usd: number;
	role: string;
}

export interface RetrievedKnowledgeView {
	item_id: string;
	title: string;
	source: string;
	excerpt: string;
	role: string;
	statute?: string;
}

export interface InvestigationEventView {
	id: string;
	timestamp: string;
	type:
		| "CASE_OPENED"
		| "INITIAL_ASSESSMENT"
		| "COMPASS_SELECTION"
		| "TOOL_COMPLETED"
		| "INVESTIGATION_TERMINATED"
		| "ACTION_SELECTED"
		| "ACTION_APPROVED"
		| "ACTION_REJECTED"
		| "ANALYST_REQUEST"
		| "ERROR"
		| string;
	title: string;
	status: "info" | "success" | "warning" | "error";
	tool?: string;
	summary: string;
	belief_before?: number;
	belief_after?: number;
	coverage_before?: number;
	coverage_after?: number;
	details?: Record<string, any>;
}

export interface GraphNode {
	id: string;
	type: "Transaction" | "Card" | "Customer" | "Device" | "Region" | string;
	label: string;
	subLabel?: string;
	isFocal?: boolean;
	metadata: Record<string, any>;
	relevance: "focal" | "inculpatory" | "exculpatory" | "neutral";
}

export interface GraphEdge {
	id: string;
	source: string;
	target: string;
	relationship: string;
	evidence_id?: string;
	evidence_family?: string;
	lr?: number;
	is_exculpatory?: boolean;
	highlighted?: boolean;
}

export interface GraphView {
	investigation_id: string;
	focal_entity: string;
	nodes: GraphNode[];
	edges: GraphEdge[];
	summary: {
		node_count: number;
		edge_count: number;
		evidence_edge_count: number;
	};
}

export interface InvestigationResultPayload {
	investigation_id: string;
	case: CaseMetadata;
	exposure_usd: number;
	initial_state: {
		fraud_probability: number;
		evidence_coverage: number;
		epistemic_uncertainty: number;
		aleatoric_uncertainty: number;
		evidence_items: string[];
	};
	run_result: {
		step_count: number;
		termination_reason: string;
		execution_duration_sec: number;
		iteration_traces: IterationTraceView[];
		primary_action: ActionRecommendationView | null;
		consequential_actions: ActionRecommendationView[];
		all_actions: ActionRecommendationView[];
		retrieved_precedents: SimilarPrecedentView[];
		retrieved_knowledge: RetrievedKnowledgeView[];
		executive_summary: string;
		grounded_synthesis: string;
		final_state: {
			fraud_probability: number;
			evidence_coverage: number;
			epistemic_uncertainty: number;
			aleatoric_uncertainty: number;
			conflict_metric: number;
			decision_gate_passed: boolean;
			decision_state: string;
			classification: "fraud" | "legitimate" | "uncertain";
			evidence_items: EvidenceItemView[];
		};
	};
	events: InvestigationEventView[];
	graph?: GraphView;
}

export type InvestigationRunStatus =
	| "IDLE"
	| "STARTING"
	| "RUNNING"
	| "COMPLETED"
	| "FAILED"
	| "REQUIRES_HUMAN_APPROVAL"
	| "CLOSED"
	| "REJECTED";

export interface InvestigationStatusResponse {
	investigation_id: string;
	status: InvestigationRunStatus;
	case?: CaseMetadata;
	result?: InvestigationResultPayload;
	error?: string;
}

export interface AnalystDecisionPayload {
	decision: "APPROVE" | "REJECT" | "REQUEST_MORE_EVIDENCE";
	analyst_id?: string;
	rationale?: string;
}

export interface ControlledPivotPayload {
	entity_type: "Device" | "Card" | "Transaction";
	entity_id: string;
	pivot_intent?:
		| "INVESTIGATE_DEVICE_RING"
		| "ANALYZE_CARD_SEQUENCE"
		| "ANALYZE_VELOCITY";
	analyst_id?: string;
	reason?: string;
}
