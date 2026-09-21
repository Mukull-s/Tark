import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { InvestigationResultPayload } from "../api/types";
import { RiskAssessment } from "../components/RiskAssessment";

const mockResultWithRisk: InvestigationResultPayload = {
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
					"SHARED_DEVICE_RING (LR=14.2, log_lr=2.653): Device DEV_c5a193fe0d03 is shared across 52 distinct cards.",
			},
			{
				iteration: 2,
				selected_action: "QUERY_CARD_SEQUENCE",
				belief_before: 0.9866,
				belief_after: 0.9866,
				coverage_before: 0.2,
				coverage_after: 0.2,
				observed_evidence_summary:
					"CARD_TESTING_SEQUENCE (LR=1.0, log_lr=0.0): No micro-authorization card testing sequence observed.",
			},
		],
		primary_action: null,
		consequential_actions: [],
		all_actions: [],
		retrieved_precedents: [],
		retrieved_knowledge: [],
		executive_summary: "",
		grounded_synthesis: "",
		final_state: {
			fraud_probability: 0.9866,
			evidence_coverage: 0.2,
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
};

describe("Phase UI-06 — Risk Assessment / Belief Trajectory", () => {
	beforeEach(() => {
		vi.restoreAllMocks();
	});

	it("renders section header, subtitle, and risk badges", () => {
		render(<RiskAssessment result={mockResultWithRisk} />);

		expect(screen.getByText("Risk assessment")).toBeInTheDocument();
		expect(
			screen.getByText("How the evidence changed Tark’s assessment"),
		).toBeInTheDocument();
	});

	it("renders initial assessment vs current assessment comparison from backend data", () => {
		render(<RiskAssessment result={mockResultWithRisk} />);

		// Initial 83.8%
		expect(screen.getByText("Initial assessment")).toBeInTheDocument();
		expect(screen.getByText("83.8%")).toBeInTheDocument();

		// Current 98.7%
		expect(screen.getByText("Current assessment")).toBeInTheDocument();
		expect(screen.getByText("98.7%")).toBeInTheDocument();

		// Delta explanation
		expect(
			screen.getByText(/\+14.8% change from evidence/i),
		).toBeInTheDocument();
	});

	it("renders belief trajectory chart points and labels", () => {
		render(<RiskAssessment result={mockResultWithRisk} />);

		expect(screen.getByText("Belief trajectory")).toBeInTheDocument();
		expect(screen.getByText("Prior")).toBeInTheDocument();
		expect(screen.getByText("Step 1")).toBeInTheDocument();
		expect(screen.getByText("Step 2")).toBeInTheDocument();
	});

	it("renders what changed the assessment list with impact descriptions", () => {
		render(<RiskAssessment result={mockResultWithRisk} />);

		expect(screen.getByText("What changed the assessment")).toBeInTheDocument();

		// Step 1: Device analysis -> Strongly increased
		expect(
			screen.getByText("Device neighborhood analysis"),
		).toBeInTheDocument();
		expect(
			screen.getByText(/Strongly increased fraud probability \(\+14.8%\)/i),
		).toBeInTheDocument();

		// Step 2: Card sequence -> No material change
		expect(screen.getByText("Card transaction sequence")).toBeInTheDocument();
		expect(screen.getByText("No material change")).toBeInTheDocument();
	});

	it("toggles technical details in trace items", () => {
		render(<RiskAssessment result={mockResultWithRisk} />);

		const viewButtons = screen.getAllByRole("button", {
			name: "View technical details",
		});
		expect(viewButtons.length).toBe(2);

		// Click to expand Step 1
		fireEvent.click(viewButtons[0]);
		expect(screen.getByText(/Belief Before:/i)).toBeInTheDocument();
		expect(screen.getByText(/83\.83%/)).toBeInTheDocument();

		// Click to collapse
		const hideButtons = screen.getAllByRole("button", {
			name: "Hide technical details",
		});
		fireEvent.click(hideButtons[0]);
		expect(screen.queryByText(/Belief Before:/i)).not.toBeInTheDocument();
	});

	it("handles missing iteration traces gracefully with fallback message", () => {
		const noTraceResult: InvestigationResultPayload = {
			...mockResultWithRisk,
			run_result: {
				...mockResultWithRisk.run_result,
				iteration_traces: [],
			},
		};

		render(<RiskAssessment result={noTraceResult} />);

		expect(
			screen.getByText("Belief trajectory unavailable for this investigation."),
		).toBeInTheDocument();
	});
});
