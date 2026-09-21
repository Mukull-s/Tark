import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { InvestigationResultPayload } from "../api/types";
import { NextBestAction } from "../components/NextBestAction";

const mockResultWithActions: InvestigationResultPayload = {
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
			action: "DECLINE_TRANSACTION",
			role: "primary",
			approval_route: "L1",
			reason: "R5: Card testing sequence detected with high fraud probability.",
			scope: "transaction",
		},
		consequential_actions: [
			{
				action: "BLOCK_CARD",
				role: "consequential",
				approval_route: "L1",
				reason: "R5: Block compromised card account.",
				scope: "card_account",
			},
		],
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

const mockResultAutoAction: InvestigationResultPayload = {
	...mockResultWithActions,
	run_result: {
		...mockResultWithActions.run_result,
		primary_action: {
			action: "CLOSE_NO_FRAUD",
			role: "primary",
			approval_route: "auto",
			reason: "R3: Customer confirmed transaction as legitimate.",
			scope: "case_management",
		},
		consequential_actions: [],
		final_state: {
			...mockResultWithActions.run_result.final_state,
			fraud_probability: 0.05,
			decision_gate_passed: true,
			decision_state: "DECIDED",
			classification: "legitimate",
		},
	},
};

const mockResultInsufficientEvidence: InvestigationResultPayload = {
	...mockResultWithActions,
	run_result: {
		...mockResultWithActions.run_result,
		primary_action: null,
		consequential_actions: [],
		final_state: {
			...mockResultWithActions.run_result.final_state,
			fraud_probability: 0.52,
			evidence_coverage: 0.2,
			decision_gate_passed: false,
			decision_state: "INSUFFICIENT_EVIDENCE",
			classification: "uncertain",
		},
	},
};

describe("Phase UI-08 — Next Best Action (NBA)", () => {
	it("renders primary action, approval requirement, scope, and rationale from backend data", () => {
		render(<NextBestAction result={mockResultWithActions} />);

		expect(screen.getByText("Next best action")).toBeInTheDocument();
		expect(screen.getByText("What should happen next")).toBeInTheDocument();

		// Primary action banner
		expect(screen.getByText("DECLINE TRANSACTION")).toBeInTheDocument();
		expect(screen.getByText("Primary recommendation")).toBeInTheDocument();

		// Approval requirement
		expect(screen.getByText("L1 APPROVAL REQUIRED")).toBeInTheDocument();

		// Target Scope
		expect(screen.getByText("TRANSACTION")).toBeInTheDocument();

		// Policy Rationale
		expect(
			screen.getByText(
				"Card testing sequence detected with high fraud probability.",
			),
		).toBeInTheDocument();
	});

	it("renders automatic action indicator when approval route is auto", () => {
		render(<NextBestAction result={mockResultAutoAction} />);

		expect(screen.getByText("CLOSE NO FRAUD")).toBeInTheDocument();
		expect(screen.getByText("AUTOMATIC ACTION ALLOWED")).toBeInTheDocument();
		expect(screen.getByText("CASE MANAGEMENT")).toBeInTheDocument();
	});

	it("renders consequential/secondary actions when provided by backend", () => {
		render(<NextBestAction result={mockResultWithActions} />);

		expect(
			screen.getByText(/Consequential Actions \(1\)/i),
		).toBeInTheDocument();
		expect(screen.getByText("BLOCK CARD")).toBeInTheDocument();
		expect(screen.getByText("Scope: CARD ACCOUNT")).toBeInTheDocument();
	});

	it("does NOT render consequential actions section when none exist", () => {
		render(<NextBestAction result={mockResultAutoAction} />);

		expect(
			screen.queryByText(/Consequential Actions/i),
		).not.toBeInTheDocument();
	});

	it("renders fallback notice when decision state is INSUFFICIENT_EVIDENCE without showing fake action", () => {
		render(<NextBestAction result={mockResultInsufficientEvidence} />);

		expect(
			screen.getByText(/\[ NO ACTION RECOMMENDED \]/i),
		).toBeInTheDocument();
		expect(
			screen.getByText(/Investigation ended with insufficient evidence/i),
		).toBeInTheDocument();
		expect(screen.queryByText("DECLINE TRANSACTION")).not.toBeInTheDocument();
		expect(
			screen.queryByText("Primary recommendation"),
		).not.toBeInTheDocument();
	});

	it("does not render any action execution or mutation buttons", () => {
		render(<NextBestAction result={mockResultWithActions} />);

		expect(
			screen.queryByRole("button", { name: /Execute/i }),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /Approve/i }),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /Reject/i }),
		).not.toBeInTheDocument();
	});
});
