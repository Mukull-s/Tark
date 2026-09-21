import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import * as client from "../api/client";
import type {
	CaseMetadata,
	HealthStatus,
	InvestigationResultPayload,
} from "../api/types";

const mockHealth: HealthStatus = {
	status: "healthy",
	tigergraph: "connected",
	total_cases: 2,
	frozen_memory_cases: 5565,
	timestamp: "2026-09-20T12:00:00Z",
};

const mockCases: CaseMetadata[] = [
	{
		case_id: "HHG-014",
		opened_at: "2016-11-23 04:12:00",
		trigger_type: "analyst_request",
		trigger_text:
			"Analyst requested review for txn 3478561 ($74.96). Potential account takeover.",
		flagged_txn_id: "3478561",
		card_id: "C08623-K2",
		customer_id: "C08623",
		risk_score: null,
	},
	{
		case_id: "HHG-001",
		opened_at: "2016-12-05 01:55:28",
		trigger_type: "risk_score",
		trigger_text:
			"Real-time model scored transaction 3514030 ($77.07) at 0.61.",
		flagged_txn_id: "3514030",
		card_id: "C12382-K1",
		customer_id: "C12382",
		risk_score: 0.61,
	},
];

const mockRunResponse = {
	investigation_id: "HHG-014",
	status: "completed",
	result: {
		investigation_id: "HHG-014",
		case: mockCases[0],
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
			execution_duration_sec: 0.12,
			iteration_traces: [],
			primary_action: {
				action: "CREATE_CASE",
				role: "primary",
				approval_route: "STANDARD",
				reason: "High risk confirmed",
				scope: "CASE",
			},
			consequential_actions: [],
			all_actions: [],
			retrieved_precedents: [],
			retrieved_knowledge: [],
			executive_summary: "Test summary",
			grounded_synthesis: "Test synthesis",
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
		events: [],
	} as unknown as InvestigationResultPayload,
};

describe("Phase UI-02 — Case Header & Investigation Start", () => {
	beforeEach(() => {
		vi.restoreAllMocks();
	});

	it("renders header with brand and TigerGraph CONNECTED badge", async () => {
		vi.spyOn(client, "fetchHealth").mockResolvedValue(mockHealth);
		vi.spyOn(client, "fetchCases").mockResolvedValue(mockCases);

		render(<App />);

		expect(screen.getByText("TARK")).toBeInTheDocument();
		expect(
			screen.getByText("Autonomous TigerGraph Fraud Investigation"),
		).toBeInTheDocument();

		await waitFor(() => {
			expect(screen.getByText("TigerGraph: CONNECTED")).toBeInTheDocument();
		});
	});

	it("navigates from queue to pre-investigation case view with complete metadata", async () => {
		vi.spyOn(client, "fetchHealth").mockResolvedValue(mockHealth);
		vi.spyOn(client, "fetchCases").mockResolvedValue(mockCases);

		render(<App />);

		await waitFor(() => {
			expect(screen.getByText("HHG-014")).toBeInTheDocument();
		});

		const openButtons = screen.getAllByRole("button", {
			name: "Open Investigation",
		});
		fireEvent.click(openButtons[0]);

		// Check Case Header info
		await waitFor(() => {
			expect(screen.getByText("READY FOR INVESTIGATION")).toBeInTheDocument();
			expect(screen.getByText("Ready to investigate")).toBeInTheDocument();
			expect(
				screen.getByText(
					/You choose the case\. Tark chooses the investigation path\./i,
				),
			).toBeInTheDocument();
		});

		// Check metadata values
		expect(screen.getByText("#3478561")).toBeInTheDocument();
		expect(screen.getByText("$74.96")).toBeInTheDocument();
		expect(screen.getByText("C08623")).toBeInTheDocument();
		expect(screen.getByText("C08623-K2")).toBeInTheDocument();

		// Start button exists
		expect(
			screen.getByRole("button", { name: "Start Investigation" }),
		).toBeInTheDocument();
	});

	it("returns to queue when [Back to Investigations] is clicked", async () => {
		vi.spyOn(client, "fetchHealth").mockResolvedValue(mockHealth);
		vi.spyOn(client, "fetchCases").mockResolvedValue(mockCases);

		render(<App />);

		await waitFor(() => {
			expect(screen.getByText("HHG-014")).toBeInTheDocument();
		});

		fireEvent.click(
			screen.getAllByRole("button", { name: "Open Investigation" })[0],
		);

		await waitFor(() => {
			expect(screen.getByText("Ready to investigate")).toBeInTheDocument();
		});

		const backBtn = screen.getByRole("button", {
			name: /Back to Investigations/i,
		});
		fireEvent.click(backBtn);

		await waitFor(() => {
			expect(screen.getByText("Investigations")).toBeInTheDocument();
			expect(screen.getByText("HHG-014")).toBeInTheDocument();
		});
	});

	it("triggers runInvestigation when [Start Investigation] is clicked", async () => {
		vi.spyOn(client, "fetchHealth").mockResolvedValue(mockHealth);
		vi.spyOn(client, "fetchCases").mockResolvedValue(mockCases);
		const runSpy = vi
			.spyOn(client, "runInvestigation")
			.mockResolvedValue(mockRunResponse);

		render(<App />);

		await waitFor(() => {
			expect(screen.getByText("HHG-014")).toBeInTheDocument();
		});

		fireEvent.click(
			screen.getAllByRole("button", { name: "Open Investigation" })[0],
		);

		await waitFor(() => {
			expect(
				screen.getByRole("button", { name: "Start Investigation" }),
			).toBeInTheDocument();
		});

		const startBtn = screen.getByRole("button", {
			name: "Start Investigation",
		});
		fireEvent.click(startBtn);

		expect(runSpy).toHaveBeenCalledWith("HHG-014");

		await waitFor(() => {
			expect(screen.getByText("INVESTIGATION COMPLETED")).toBeInTheDocument();
			expect(screen.getByText("Investigation complete")).toBeInTheDocument();
		});
	});

	it("handles investigation error cleanly without raw backend stack trace", async () => {
		vi.spyOn(client, "fetchHealth").mockResolvedValue(mockHealth);
		vi.spyOn(client, "fetchCases").mockResolvedValue(mockCases);
		vi.spyOn(client, "runInvestigation").mockRejectedValue(
			new Error("TigerGraph query timeout on device vertex"),
		);

		render(<App />);

		await waitFor(() => {
			expect(screen.getByText("HHG-014")).toBeInTheDocument();
		});

		fireEvent.click(
			screen.getAllByRole("button", { name: "Open Investigation" })[0],
		);

		await waitFor(() => {
			expect(
				screen.getByRole("button", { name: "Start Investigation" }),
			).toBeInTheDocument();
		});

		fireEvent.click(
			screen.getByRole("button", { name: "Start Investigation" }),
		);

		await waitFor(() => {
			expect(
				screen.getByText("TigerGraph query timeout on device vertex"),
			).toBeInTheDocument();
		});
	});
});
