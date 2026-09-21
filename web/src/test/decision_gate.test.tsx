import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { InvestigationResultPayload } from "../api/types";
import { DecisionGate } from "../components/DecisionGate";

const mockResultHumanApproval: InvestigationResultPayload = {
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
		iteration_traces: [],
		primary_action: {
			action: "FREEZE_CARD_ACCOUNT",
			role: "primary",
			approval_route: "L1",
			reason: "High fraud probability (0.987) with high financial exposure",
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
			evidence_items: [],
		},
	},
	events: [],
};

const mockResultAutoAllowed: InvestigationResultPayload = {
	...mockResultHumanApproval,
	run_result: {
		...mockResultHumanApproval.run_result,
		primary_action: {
			action: "MONITOR_CARD",
			role: "primary",
			approval_route: "auto",
			reason: "Low risk observed",
			scope: "card_account",
		},
		final_state: {
			...mockResultHumanApproval.run_result.final_state,
			fraud_probability: 0.12,
			decision_gate_passed: true,
			decision_state: "DECIDED",
			classification: "legitimate",
		},
	},
};

const mockResultInsufficientEvidence: InvestigationResultPayload = {
	...mockResultHumanApproval,
	run_result: {
		...mockResultHumanApproval.run_result,
		primary_action: null,
		final_state: {
			...mockResultHumanApproval.run_result.final_state,
			fraud_probability: 0.55,
			evidence_coverage: 0.2,
			decision_gate_passed: false,
			decision_state: "INSUFFICIENT_EVIDENCE",
			classification: "uncertain",
		},
	},
};

describe("Phase UI-07 — Decision Gate / Decision Readiness", () => {
	it("renders header, title, and subtitle correctly", () => {
		render(<DecisionGate result={mockResultHumanApproval} />);

		expect(screen.getByText("Decision gate")).toBeInTheDocument();
		expect(screen.getByText("Can Tark act on this case?")).toBeInTheDocument();
	});

	it("renders HUMAN APPROVAL REQUIRED when policy requires L1 sign-off", () => {
		render(<DecisionGate result={mockResultHumanApproval} />);

		expect(
			screen.getByText(/\[ HUMAN APPROVAL REQUIRED \]/i),
		).toBeInTheDocument();
		expect(
			screen.getByText(/Policy requires L1 sign-off/i),
		).toBeInTheDocument();
	});

	it("renders AUTOMATIC ACTION ALLOWED when policy permits autonomous execution", () => {
		render(<DecisionGate result={mockResultAutoAllowed} />);

		expect(
			screen.getByText(/\[ AUTOMATIC ACTION ALLOWED \]/i),
		).toBeInTheDocument();
		expect(
			screen.getByText(/Autonomous execution permitted by policy/i),
		).toBeInTheDocument();
	});

	it("renders INSUFFICIENT EVIDENCE when decision gate fails due to low coverage", () => {
		render(<DecisionGate result={mockResultInsufficientEvidence} />);

		expect(
			screen.getByText(/\[ INSUFFICIENT EVIDENCE \]/i),
		).toBeInTheDocument();
		expect(
			screen.getByText(
				/Automated decision blocked due to incomplete evidence/i,
			),
		).toBeInTheDocument();
	});

	it("renders Why this gate reasons accurately based on backend fields", () => {
		render(<DecisionGate result={mockResultHumanApproval} />);

		expect(screen.getByText("Why this gate?")).toBeInTheDocument();
		expect(screen.getByText(/Evidence sufficient/i)).toBeInTheDocument();
		expect(screen.getByText(/Risk assessment conclusive/i)).toBeInTheDocument();
		expect(
			screen.getByText(/No evidentiary contradiction/i),
		).toBeInTheDocument();
		expect(
			screen.getByText(/Action requires L1 approval/i),
		).toBeInTheDocument();
	});

	it("renders decision context metrics from backend without modification", () => {
		render(<DecisionGate result={mockResultHumanApproval} />);

		expect(screen.getByText("Decision context")).toBeInTheDocument();
		expect(screen.getByText("98.7%")).toBeInTheDocument();
		expect(screen.getAllByText("40%").length).toBeGreaterThanOrEqual(1);
		expect(screen.getByText("$74.96")).toBeInTheDocument();
	});

	it("renders constraints and collapses technical details by default", () => {
		render(<DecisionGate result={mockResultHumanApproval} />);

		expect(screen.getByText("Constraints & Governance")).toBeInTheDocument();
		expect(screen.getByText(/Approval route:/i)).toBeInTheDocument();
		expect(screen.getByText("L1")).toBeInTheDocument();

		// Technical details should be collapsed
		expect(
			screen.queryByText(/decision_gate_passed:/i),
		).not.toBeInTheDocument();

		// Expand
		const toggleBtn = screen.getByRole("button", {
			name: /View technical details/i,
		});
		fireEvent.click(toggleBtn);
		expect(screen.getByText(/decision_gate_passed:/i)).toBeInTheDocument();
		expect(screen.getByText(/epistemic_uncertainty:/i)).toBeInTheDocument();

		// Collapse
		fireEvent.click(
			screen.getByRole("button", { name: /Hide technical details/i }),
		);
		expect(
			screen.queryByText(/decision_gate_passed:/i),
		).not.toBeInTheDocument();
	});
});
