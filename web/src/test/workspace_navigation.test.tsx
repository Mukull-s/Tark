import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import * as apiClient from "../api/client";
import type { CaseMetadata, InvestigationResultPayload } from "../api/types";
import { InvestigationPreStartView } from "../components/InvestigationPreStartView";

const mockCase: CaseMetadata = {
	case_id: "HHG-014",
	opened_at: "2016-11-22 20:11:00",
	trigger_type: "analyst_request",
	trigger_text: "Analyst requested review for txn 3478561 ($74.96).",
	flagged_txn_id: "3478561",
	card_id: "C13487-K1",
	customer_id: "C13487",
	risk_score: null,
};

const mockResult: InvestigationResultPayload = {
	investigation_id: "HHG-014",
	case: mockCase,
	exposure_usd: 74.96,
	initial_state: {
		fraud_probability: 0.8383,
		evidence_coverage: 0.0,
		epistemic_uncertainty: 1.0,
		aleatoric_uncertainty: 0.5,
		evidence_items: [],
	},
	run_result: {
		step_count: 2,
		termination_reason: "DECISION_REACHED",
		execution_duration_sec: 0.18,
		iteration_traces: [
			{
				iteration: 1,
				selected_action: "QUERY_DEVICE_ANALYSIS",
				belief_before: 0.8383,
				belief_after: 0.9866,
				coverage_before: 0.0,
				coverage_after: 0.2,
				observed_evidence_summary:
					"SHARED_DEVICE_RING (LR=14.2): Device DEV_c5a193fe0d03 is shared across 52 distinct cards.",
			},
		],
		primary_action: {
			action: "FREEZE_CARD_ACCOUNT",
			role: "primary",
			approval_route: "L1",
			reason: "High risk observed",
			scope: "card_account",
		},
		consequential_actions: [],
		all_actions: [],
		retrieved_precedents: [],
		retrieved_knowledge: [],
		executive_summary: "",
		grounded_synthesis: "",
		final_state: {
			fraud_probability: 0.9866,
			evidence_coverage: 0.4,
			epistemic_uncertainty: 0.1,
			aleatoric_uncertainty: 0.0,
			conflict_metric: 0.0,
			decision_gate_passed: true,
			decision_state: "DECIDED",
			classification: "fraud",
			evidence_items: [
				{
					evidence_id: "EVD-1",
					evidence_type: "SHARED_DEVICE_RING",
					source: "TigerGraph",
					finding:
						"Device DEV_c5a193fe0d03 is shared across 52 distinct cards.",
					value: "DEV_c5a193fe0d03",
					lr: 14.2,
					log_lr: 2.653,
					is_exculpatory: false,
					observed_at: "2016-11-22 20:11:00",
				},
			],
		},
	},
	events: [
		{
			id: "EVT-1",
			timestamp: "2016-11-22 20:11:00",
			type: "INITIAL_ASSESSMENT",
			title: "Initial Assessment Completed",
			status: "info",
			summary: "Prior established at 83.8%",
			belief_after: 0.8383,
		},
	],
	graph: {
		investigation_id: "HHG-014",
		focal_entity: "3478561",
		nodes: [
			{
				id: "3478561",
				type: "Transaction",
				label: "Txn #3478561",
				isFocal: true,
				metadata: {},
				relevance: "focal",
			},
		],
		edges: [],
		summary: { node_count: 1, edge_count: 0, evidence_edge_count: 0 },
	},
};

describe("Phase UI-07.1 — Investigation Workspace Navigation", () => {
	it("renders Activity by default and allows switching between workspace tabs while DecisionGate remains visible", async () => {
		vi.spyOn(apiClient, "runInvestigation").mockResolvedValueOnce({
			investigation_id: "HHG-014",
			status: "COMPLETED",
			result: mockResult,
		});

		render(<InvestigationPreStartView caseItem={mockCase} onBack={() => {}} />);

		// Start investigation
		const startBtn = screen.getByRole("button", {
			name: /Start Investigation/i,
		});
		fireEvent.click(startBtn);

		await waitFor(() => {
			expect(screen.getByText(/Investigation Activity/i)).toBeInTheDocument();
		});

		// 1. Activity is active by default
		expect(
			screen.getByRole("button", { name: "Activity" }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Evidence" }),
		).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Network" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Risk" })).toBeInTheDocument();

		// Persistent Decision Gate is visible
		expect(screen.getByText("Decision gate")).toBeInTheDocument();
		expect(
			screen.getByText(/\[ HUMAN APPROVAL REQUIRED \]/i),
		).toBeInTheDocument();

		// Key Evidence, Network, Risk should NOT be in DOM currently
		expect(screen.queryByText("Key evidence findings")).not.toBeInTheDocument();
		expect(screen.queryByText("Investigation network")).not.toBeInTheDocument();
		expect(screen.queryByText("Belief trajectory")).not.toBeInTheDocument();

		// 2. Click Evidence tab
		fireEvent.click(screen.getByRole("button", { name: "Evidence" }));
		expect(screen.getByText("Evidence found")).toBeInTheDocument();
		expect(
			screen.queryByText(/Investigation Activity/i),
		).not.toBeInTheDocument();
		expect(screen.getByText("Decision gate")).toBeInTheDocument();

		// 3. Click Network tab
		fireEvent.click(screen.getByRole("button", { name: "Network" }));
		expect(screen.getByText(/Investigation Network/i)).toBeInTheDocument();
		expect(screen.queryByText("Evidence found")).not.toBeInTheDocument();
		expect(screen.getByText("Decision gate")).toBeInTheDocument();

		// 4. Click Risk tab
		fireEvent.click(screen.getByRole("button", { name: "Risk" }));
		expect(screen.getByText("Belief trajectory")).toBeInTheDocument();
		expect(
			screen.getByText(/How the evidence changed Tark’s assessment/i),
		).toBeInTheDocument();
		expect(
			screen.queryByText(/Investigation Network/i),
		).not.toBeInTheDocument();
		expect(screen.getByText("Decision gate")).toBeInTheDocument();

		// 5. Switch back to Activity
		fireEvent.click(screen.getByRole("button", { name: "Activity" }));
		expect(screen.getByText(/Investigation Activity/i)).toBeInTheDocument();
		expect(screen.queryByText("Belief trajectory")).not.toBeInTheDocument();
		expect(screen.getByText("Decision gate")).toBeInTheDocument();
	});
});
