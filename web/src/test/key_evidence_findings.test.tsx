import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { InvestigationResultPayload } from "../api/types";
import { KeyEvidenceFindings } from "../components/KeyEvidenceFindings";

const mockResultWithSignals: InvestigationResultPayload = {
	investigation_id: "HHG-014",
	case: {
		case_id: "HHG-014",
		opened_at: "2016-11-22 20:11:00",
		trigger_type: "analyst_request",
		trigger_text: "Analyst requested review for txn 3478561 ($74.96).",
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
		step_count: 3,
		termination_reason: "DECISION_REACHED",
		execution_duration_sec: 0.18,
		iteration_traces: [],
		primary_action: null,
		consequential_actions: [],
		all_actions: [],
		retrieved_precedents: [],
		retrieved_knowledge: [],
		executive_summary: "",
		grounded_synthesis: "",
		final_state: {
			fraud_probability: 0.9866,
			evidence_coverage: 0.33,
			epistemic_uncertainty: 0.1,
			aleatoric_uncertainty: 0.2,
			conflict_metric: 0.0,
			decision_gate_passed: true,
			decision_state: "DECISION_REACHED",
			classification: "fraud",
			evidence_items: [
				{
					evidence_id: "EVD-101",
					evidence_type: "SHARED_DEVICE_RING",
					source: "tigergraph_query:device_analysis",
					finding:
						"Device DEV_c5a193fe0d03 is shared across 52 distinct cards in graph ring (proxy=True).",
					value: { shared_card_count: 52 },
					lr: 14.2,
					log_lr: 2.653,
					is_exculpatory: false,
					observed_at: "2026-09-20T12:00:00Z",
					details: { shared_count: 52, device_id: "DEV_c5a193fe0d03" },
				},
				{
					evidence_id: "EVD-102",
					evidence_type: "CARD_TESTING_SEQUENCE",
					source: "tigergraph_query:card_sequence",
					finding:
						"No micro-authorization card testing sequence observed within 24h window.",
					value: "NO_MATCH",
					lr: 1.0,
					log_lr: 0.0,
					is_exculpatory: false,
					observed_at: "2026-09-20T12:00:01Z",
					details: { scope_status: "NO_MATCH" },
				},
				{
					evidence_id: "EVD-103",
					evidence_type: "CUSTOMER_COMMUNICATION_UNAVAILABLE",
					source: "gateway:simulate_customer_reply",
					finding: "Customer communication channel timed out without response.",
					value: "UNAVAILABLE",
					lr: 1.0,
					log_lr: 0.0,
					is_exculpatory: false,
					observed_at: "2026-09-20T12:00:02Z",
					details: { raw: { status: "UNAVAILABLE" } },
				},
			],
		},
	},
	events: [],
};

describe("Phase UI-04 — Key Evidence / Investigation Findings", () => {
	beforeEach(() => {
		vi.restoreAllMocks();
	});

	it("renders section title, subtitle, and evaluated signals count", () => {
		render(<KeyEvidenceFindings result={mockResultWithSignals} />);

		expect(screen.getByText("Evidence found")).toBeInTheDocument();
		expect(
			screen.getByText(
				"The strongest signals discovered during this investigation",
			),
		).toBeInTheDocument();
		expect(screen.getByText("3 SIGNALS EVALUATED")).toBeInTheDocument();
	});

	it("gives primary visual treatment to the strongest signal with LR badge", () => {
		render(<KeyEvidenceFindings result={mockResultWithSignals} />);

		// Strongest Signal badge and title
		expect(screen.getByText("STRONGEST SIGNAL")).toBeInTheDocument();
		expect(screen.getByText("Shared device network")).toBeInTheDocument();
		expect(
			screen.getByText(
				/Device DEV_c5a193fe0d03 is shared across 52 distinct cards in graph ring/i,
			),
		).toBeInTheDocument();
		expect(screen.getByText("LR +14.2")).toBeInTheDocument();
	});

	it("renders supporting and neutral evidence in secondary grid with appropriate badges", () => {
		render(<KeyEvidenceFindings result={mockResultWithSignals} />);

		// Card transaction sequence (Neutral)
		expect(
			screen.getAllByText("Card transaction sequence").length,
		).toBeGreaterThanOrEqual(1);
		expect(screen.getByText("Normal finding")).toBeInTheDocument();
		expect(
			screen.getByText(
				/No micro-authorization card testing sequence observed within 24h window/i,
			),
		).toBeInTheDocument();

		// Customer communication (Unavailable)
		expect(
			screen.getByText("Cardholder verification channel"),
		).toBeInTheDocument();
		expect(screen.getByText("Unavailable check")).toBeInTheDocument();
	});

	it("collapses technical details by default and expands on click", () => {
		render(<KeyEvidenceFindings result={mockResultWithSignals} />);

		// Primary evidence toggle
		const primaryToggle = screen.getByRole("button", {
			name: /View evidence details/i,
		});
		expect(primaryToggle).toBeInTheDocument();

		// Raw evidence ID is hidden initially
		expect(screen.queryByText("EVD-101")).not.toBeInTheDocument();

		// Click to expand
		fireEvent.click(primaryToggle);
		expect(screen.getByText(/Hide evidence details/i)).toBeInTheDocument();
		expect(screen.getByText("EVD-101")).toBeInTheDocument();

		// Click to collapse
		fireEvent.click(
			screen.getByRole("button", { name: /Hide evidence details/i }),
		);
		expect(screen.queryByText("EVD-101")).not.toBeInTheDocument();
	});

	it("displays evidence coverage summary accurately", () => {
		render(<KeyEvidenceFindings result={mockResultWithSignals} />);

		expect(
			screen.getByText(/33% of graph evidence space examined/i),
		).toBeInTheDocument();
		expect(
			screen.getByText(/TigerGraph Engine · Detection Model/i),
		).toBeInTheDocument();
	});

	it("handles empty evidence items gracefully", () => {
		const emptyResult: InvestigationResultPayload = {
			...mockResultWithSignals,
			run_result: {
				...mockResultWithSignals.run_result,
				final_state: {
					...mockResultWithSignals.run_result.final_state,
					evidence_items: [],
				},
			},
		};

		render(<KeyEvidenceFindings result={emptyResult} />);

		expect(
			screen.getByText("No evidence signals recorded for this case."),
		).toBeInTheDocument();
	});
});
