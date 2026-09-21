import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { InvestigationResultPayload } from "../api/types";
import { InvestigationConclusion } from "../components/InvestigationConclusion";

const mockResultHighRisk: InvestigationResultPayload = {
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

const mockResultLowRisk: InvestigationResultPayload = {
	...mockResultHighRisk,
	run_result: {
		...mockResultHighRisk.run_result,
		primary_action: {
			action: "CLOSE_NO_FRAUD",
			role: "primary",
			approval_route: "auto",
			reason: "R3: Customer confirmed transaction as legitimate.",
			scope: "case_management",
		},
		final_state: {
			...mockResultHighRisk.run_result.final_state,
			fraud_probability: 0.08,
			decision_gate_passed: true,
			decision_state: "DECIDED",
			classification: "legitimate",
		},
	},
};

const mockResultInsufficientEvidence: InvestigationResultPayload = {
	...mockResultHighRisk,
	run_result: {
		...mockResultHighRisk.run_result,
		primary_action: null,
		final_state: {
			...mockResultHighRisk.run_result.final_state,
			fraud_probability: 0.52,
			evidence_coverage: 0.2,
			decision_gate_passed: false,
			decision_state: "INSUFFICIENT_EVIDENCE",
			classification: "uncertain",
		},
	},
};

describe("Phase UI-09 — Investigation Conclusion / Final Decision Summary", () => {
	it("renders high-risk conclusion, probability, recommended action, and approval requirement", () => {
		render(<InvestigationConclusion result={mockResultHighRisk} />);

		expect(screen.getByText("Investigation Conclusion")).toBeInTheDocument();
		expect(screen.getByText("HIGH FRAUD RISK")).toBeInTheDocument();
		expect(screen.getByText("98.7%")).toBeInTheDocument();
		expect(
			screen.getByText(
				/Tark’s investigation found sufficient evidence to support the current fraud-risk assessment/i,
			),
		).toBeInTheDocument();

		expect(screen.getByText("DECLINE TRANSACTION")).toBeInTheDocument();
		expect(screen.getByText("L1 APPROVAL REQUIRED")).toBeInTheDocument();
		expect(screen.getByText("40% observed")).toBeInTheDocument();
		expect(screen.getByText("decided")).toBeInTheDocument();
		expect(
			screen.getByText(
				/Card testing sequence detected with high fraud probability/i,
			),
		).toBeInTheDocument();
	});

	it("renders low-risk conclusion and automatic action approval for legitimate cases", () => {
		render(<InvestigationConclusion result={mockResultLowRisk} />);

		expect(screen.getByText("LOW FRAUD RISK")).toBeInTheDocument();
		expect(screen.getByText("8.0%")).toBeInTheDocument();
		expect(
			screen.getByText(
				/Tark’s investigation found exculpatory evidence supporting a legitimate transaction assessment/i,
			),
		).toBeInTheDocument();

		expect(screen.getByText("CLOSE NO FRAUD")).toBeInTheDocument();
		expect(screen.getByText("AUTOMATIC ACTION ALLOWED")).toBeInTheDocument();
	});

	it("renders inconclusive status when decision state is INSUFFICIENT_EVIDENCE without claiming fraud", () => {
		render(<InvestigationConclusion result={mockResultInsufficientEvidence} />);

		expect(screen.getByText("INVESTIGATION INCONCLUSIVE")).toBeInTheDocument();
		expect(
			screen.getByText(
				/Tark’s investigation found insufficient evidence to support an automated policy determination/i,
			),
		).toBeInTheDocument();
		expect(screen.getByText("No action recommended")).toBeInTheDocument();
		expect(screen.queryByText("HIGH FRAUD RISK")).not.toBeInTheDocument();
	});

	it("toggles technical details on demand", () => {
		render(<InvestigationConclusion result={mockResultHighRisk} />);

		expect(
			screen.queryByText(/decision_gate_passed:/i),
		).not.toBeInTheDocument();

		fireEvent.click(
			screen.getByRole("button", { name: /View technical details/i }),
		);
		expect(screen.getByText(/decision_gate_passed:/i)).toBeInTheDocument();
		expect(screen.getByText(/epistemic_uncertainty:/i)).toBeInTheDocument();

		fireEvent.click(
			screen.getByRole("button", { name: /Hide technical details/i }),
		);
		expect(
			screen.queryByText(/decision_gate_passed:/i),
		).not.toBeInTheDocument();
	});

	it("does not contain any action execution or mutation triggers", () => {
		render(<InvestigationConclusion result={mockResultHighRisk} />);

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
