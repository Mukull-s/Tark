import type {
	CaseMetadata,
	GraphView,
	HealthStatus,
	InvestigationEventView,
	InvestigationHistoryItem,
	InvestigationResultPayload,
	InvestigationStatusResponse,
} from "./types";

const rawBase = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const API_BASE = rawBase
	? (rawBase.endsWith("/api") ? rawBase : `${rawBase}/api`)
	: "/api";

export async function fetchHealth(): Promise<HealthStatus> {
	const res = await fetch(`${API_BASE}/health`);
	if (!res.ok) {
		throw new Error(`Health check failed with status: ${res.status}`);
	}
	return res.json();
}

export async function fetchCases(): Promise<CaseMetadata[]> {
	const res = await fetch(`${API_BASE}/cases`);
	if (!res.ok) {
		throw new Error(`Failed to load cases: ${res.status}`);
	}
	return res.json();
}

export async function fetchCase(caseId: string): Promise<CaseMetadata> {
	const res = await fetch(`${API_BASE}/cases/${encodeURIComponent(caseId)}`);
	if (!res.ok) {
		throw new Error(`Failed to fetch case ${caseId}: ${res.status}`);
	}
	return res.json();
}

export async function runInvestigation(caseId: string): Promise<{
	investigation_id: string;
	status: string;
	result: InvestigationResultPayload;
}> {
	const res = await fetch(
		`${API_BASE}/investigations/${encodeURIComponent(caseId)}/run`,
		{
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
		},
	);
	if (!res.ok) {
		const errorData = await res.json().catch(() => ({}));
		throw new Error(
			errorData.detail ||
				`Investigation execution failed with status ${res.status}`,
		);
	}
	return res.json();
}

export async function runTransactionInvestigation(txnId: string): Promise<{
	investigation_id: string;
	status: string;
	result: InvestigationResultPayload;
}> {
	const res = await fetch(
		`${API_BASE}/investigations/transaction/${encodeURIComponent(txnId)}/run`,
		{
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
		},
	);
	if (!res.ok) {
		const errorData = await res.json().catch(() => ({}));
		throw new Error(
			errorData.detail ||
				`Transaction investigation failed with status ${res.status}`,
		);
	}
	return res.json();
}

export async function fetchInvestigationStatus(
	investigationId: string,
): Promise<InvestigationStatusResponse> {
	const res = await fetch(
		`${API_BASE}/investigations/${encodeURIComponent(investigationId)}`,
	);
	if (!res.ok) {
		throw new Error(
			`Failed to get status for ${investigationId}: ${res.status}`,
		);
	}
	return res.json();
}

export async function fetchInvestigationEvents(
	investigationId: string,
): Promise<InvestigationEventView[]> {
	const res = await fetch(
		`${API_BASE}/investigations/${encodeURIComponent(investigationId)}/events`,
	);
	if (!res.ok) {
		throw new Error(
			`Failed to fetch events for ${investigationId}: ${res.status}`,
		);
	}
	return res.json();
}

export async function fetchInvestigationGraph(
	investigationId: string,
): Promise<GraphView> {
	const res = await fetch(
		`${API_BASE}/investigations/${encodeURIComponent(investigationId)}/graph`,
	);
	if (!res.ok) {
		throw new Error(
			`Failed to fetch graph for ${investigationId}: ${res.status}`,
		);
	}
	return res.json();
}

export async function submitAnalystDecision(
	investigationId: string,
	payload: { decision: string; analyst_id?: string; rationale?: string },
): Promise<any> {
	const res = await fetch(
		`${API_BASE}/investigations/${encodeURIComponent(investigationId)}/decision`,
		{
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(payload),
		},
	);
	if (!res.ok) {
		const errorData = await res.json().catch(() => ({}));
		throw new Error(
			errorData.detail || `Analyst decision submission failed (${res.status})`,
		);
	}
	return res.json();
}

export async function triggerControlledPivot(
	investigationId: string,
	payload: {
		entity_type: string;
		entity_id: string;
		pivot_intent?: string;
		analyst_id?: string;
		reason?: string;
	},
): Promise<any> {
	const res = await fetch(
		`${API_BASE}/investigations/${encodeURIComponent(investigationId)}/pivot`,
		{
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(payload),
		},
	);
	if (!res.ok) {
		const errorData = await res.json().catch(() => ({}));
		throw new Error(
			errorData.detail || `Controlled pivot failed (${res.status})`,
		);
	}
	return res.json();
}

export async function fetchInvestigationHistory(): Promise<InvestigationHistoryItem[]> {
	const res = await fetch(`${API_BASE}/investigations/history`);
	if (!res.ok) {
		throw new Error(`Failed to load investigation history (${res.status})`);
	}
	return res.json();
}
