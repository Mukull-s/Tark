import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { InvestigationResultPayload } from "../api/types";
import { InvestigationActivity } from "../components/InvestigationActivity";

const mockInvestigationResult: InvestigationResultPayload = {
	investigation_id: "HHG-014",
	case: {
		case_id: "HHG-014",
		opened_at: "2016-11-22 20:11:00",
		trigger_type: "analyst_request",
		trigger_text:
			"Analyst requested review for txn 3478561 ($74.96). Potential account takeover.",
		flagged_txn_id: "3478561",
		card_id: "C13487-K1",
		customer_id: "C13487",
		risk_score: null,
	},
	exposure_usd: 74.96,
	initial_state: {
		fraud_probability: 0.5,
		evidence_coverage: 0.0,
		epistemic_uncertainty: 1.0,
		aleatoric_uncertainty: 0.5,
		evidence_items: [],
	},
	run_result: {
		step_count: 2,
		termination_reason: "DECISION_REACHED",
		execution_duration_sec: 0.18,
		iteration_traces: [],
		primary_action: {
			action: "CREATE_CASE",
			role: "primary",
			approval_route: "STANDARD",
			reason: "Fraud ring confirmed",
			scope: "CASE",
		},
		consequential_actions: [],
		all_actions: [],
		retrieved_precedents: [],
		retrieved_knowledge: [],
		executive_summary: "Summary text",
		grounded_synthesis: "Synthesis text",
		final_state: {
			fraud_probability: 0.9866,
			evidence_coverage: 0.33,
			epistemic_uncertainty: 0.1,
			aleatoric_uncertainty: 0.2,
			conflict_metric: 0.0,
			decision_gate_passed: true,
			decision_state: "DECISION_REACHED",
			classification: "fraud",
			evidence_items: [],
		},
	},
	events: [
		{
			id: "EVT-HHG-014-OPEN",
			timestamp: "2016-11-22 20:11:00",
			type: "CASE_OPENED",
			title: "Investigation Opened — Case HHG-014",
			status: "info",
			summary:
				"Alert triggered via analyst_request: 'Analyst requested review for txn 3478561 ($74.96).'",
			details: {
				flagged_txn_id: "3478561",
				customer_id: "C13487",
				card_id: "C13487-K1",
				amount_usd: 74.96,
				trigger_type: "analyst_request",
			},
		},
		{
			id: "EVT-HHG-014-IT1-TOOL",
			timestamp: "2016-11-22 20:11:00",
			type: "TOOL_COMPLETED",
			title: "Step 1: QUERY_DEVICE_ANALYSIS Executed on TigerGraph",
			status: "success",
			tool: "QUERY_DEVICE_ANALYSIS",
			summary:
				"SHARED_DEVICE_RING (LR=14.2, log_lr=2.653): Device DEV_c5a193fe0d03 is shared across 52 distinct cards in graph ring (proxy=True).",
			details: {
				evidence_observed: "SHARED_DEVICE_RING",
			},
		},
		{
			id: "EVT-HHG-014-IT2-TOOL",
			timestamp: "2016-11-22 20:11:00",
			type: "TOOL_COMPLETED",
			title: "Step 2: QUERY_CARD_SEQUENCE Executed on TigerGraph",
			status: "success",
			tool: "QUERY_CARD_SEQUENCE",
			summary:
				"CARD_TESTING_SEQUENCE (LR=1.0, log_lr=0.0): No micro-authorization card testing sequence observed within 24h window.",
			details: {
				evidence_observed: "CARD_TESTING_SEQUENCE",
			},
		},
		{
			id: "EVT-HHG-014-TERM",
			timestamp: "2026-09-20T12:00:00Z",
			type: "INVESTIGATION_TERMINATED",
			title: "Investigation Terminated: DECISION_REACHED",
			status: "info",
			summary: "Stopped after 2 steps.",
			details: {
				termination_reason: "DECISION_REACHED",
			},
		},
	],
};

describe("Phase UI-03 — Investigation Activity", () => {
	beforeEach(() => {
		vi.restoreAllMocks();
	});

	it("renders section header, subtitle, and case opened event", () => {
		render(<InvestigationActivity result={mockInvestigationResult} />);

		expect(screen.getByText("Investigation Activity")).toBeInTheDocument();
		expect(
			screen.getByText("Tark’s evidence-gathering process"),
		).toBeInTheDocument();
		expect(screen.getByText("Investigation opened")).toBeInTheDocument();
		expect(
			screen.getByText(/Case HHG-014 · Trigger: analyst request/i),
		).toBeInTheDocument();
	});

	it("humanizes tool names and renders why/checked/found information", () => {
		render(<InvestigationActivity result={mockInvestigationResult} />);

		// Step 1: Device analysis
		expect(
			screen.getByText("Step 1 · Device neighborhood analysis"),
		).toBeInTheDocument();
		expect(
			screen.getByText(
				/Tark selected device analysis based on expected information value\./i,
			),
		).toBeInTheDocument();
		expect(
			screen.getByText(
				"Device fingerprint and shared device graph neighborhood.",
			),
		).toBeInTheDocument();
		expect(
			screen.getByText(
				/Device DEV_c5a193fe0d03 is shared across 52 distinct cards in graph ring/i,
			),
		).toBeInTheDocument();

		// Step 2: Card sequence
		expect(
			screen.getByText("Step 2 · Card transaction sequence"),
		).toBeInTheDocument();
		expect(
			screen.getByText(
				/No micro-authorization card testing sequence observed within 24h window\./i,
			),
		).toBeInTheDocument();
	});

	it("toggles technical details on demand without polluting default view", () => {
		render(<InvestigationActivity result={mockInvestigationResult} />);

		const detailButtons = screen.getAllByRole("button", {
			name: /View technical details/i,
		});
		expect(detailButtons.length).toBe(2);

		// Initial state: technical identifiers not rendered in raw format
		expect(
			screen.queryByText("TigerGraph Graph Engine"),
		).not.toBeInTheDocument();

		// Click to expand Step 1 technical details
		fireEvent.click(detailButtons[0]);

		expect(screen.getByText(/Hide technical details/i)).toBeInTheDocument();
		expect(screen.getByText("QUERY_DEVICE_ANALYSIS")).toBeInTheDocument();
		expect(screen.getByText("TigerGraph Graph Engine")).toBeInTheDocument();
		expect(screen.getByText(/Likelihood Ratio \(LR\):/i)).toBeInTheDocument();

		// Click to collapse
		const hideButton = screen.getByRole("button", {
			name: /Hide technical details/i,
		});
		fireEvent.click(hideButton);

		expect(
			screen.queryByText("TigerGraph Graph Engine"),
		).not.toBeInTheDocument();
	});

	it("displays human-readable termination reason", () => {
		render(<InvestigationActivity result={mockInvestigationResult} />);

		expect(screen.getByText("Investigation complete")).toBeInTheDocument();
		expect(
			screen.getByText(
				"Evidence was sufficient for a definitive policy decision.",
			),
		).toBeInTheDocument();
	});

	it("handles other termination conditions (e.g. MAX_STEPS_REACHED) cleanly", () => {
		const stoppedResult: InvestigationResultPayload = {
			...mockInvestigationResult,
			run_result: {
				...mockInvestigationResult.run_result,
				termination_reason: "MAX_STEPS_REACHED",
			},
		};

		render(<InvestigationActivity result={stoppedResult} />);

		expect(screen.getByText("Investigation stopped")).toBeInTheDocument();
		expect(
			screen.getByText("Investigation reached the maximum allowed step limit."),
		).toBeInTheDocument();
	});
});
