import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import * as apiClient from "../api/client";
import type { InvestigationResultPayload } from "../api/types";
import { AnalystDecision } from "../components/AnalystDecision";

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

const mockResultAuto: InvestigationResultPayload = {
	...mockResultHumanApproval,
	run_result: {
		...mockResultHumanApproval.run_result,
		primary_action: {
			action: "CLOSE_NO_FRAUD",
			role: "primary",
			approval_route: "auto",
			reason: "Customer verified transaction.",
			scope: "case_management",
		},
		final_state: {
			...mockResultHumanApproval.run_result.final_state,
			fraud_probability: 0.05,
			decision_gate_passed: true,
			decision_state: "DECIDED",
			classification: "legitimate",
		},
	},
};

const mockResultInsufficient: InvestigationResultPayload = {
	...mockResultHumanApproval,
	run_result: {
		...mockResultHumanApproval.run_result,
		primary_action: null,
		final_state: {
			...mockResultHumanApproval.run_result.final_state,
			fraud_probability: 0.52,
			evidence_coverage: 0.2,
			decision_gate_passed: false,
			decision_state: "INSUFFICIENT_EVIDENCE",
			classification: "uncertain",
		},
	},
};

describe("Phase UI-10 — Human Approval / Analyst Decision", () => {
	it("displays Tark recommendation and approval controls for human-approval cases", () => {
		render(<AnalystDecision result={mockResultHumanApproval} />);

		expect(screen.getByText("Your decision")).toBeInTheDocument();
		expect(screen.getByText(/Tark recommends:/i)).toBeInTheDocument();
		expect(screen.getByText("DECLINE TRANSACTION")).toBeInTheDocument();
		expect(screen.getByText(/L1 approval required/i)).toBeInTheDocument();

		expect(
			screen.getByRole("button", { name: /Approve recommendation/i }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: /Reject \/ Override/i }),
		).toBeInTheDocument();
	});

	it("approves recommendation and updates UI to show recorded decision after backend success", async () => {
		const submitSpy = vi
			.spyOn(apiClient, "submitAnalystDecision")
			.mockResolvedValueOnce({
				investigation_id: "HHG-014",
				case_status: "CLOSED",
				result: mockResultHumanApproval,
			});

		render(<AnalystDecision result={mockResultHumanApproval} />);

		fireEvent.click(
			screen.getByRole("button", { name: /Approve recommendation/i }),
		);

		await waitFor(() => {
			expect(submitSpy).toHaveBeenCalledWith("HHG-014", {
				decision: "APPROVE",
				analyst_id: "ANALYST_01",
				rationale: expect.any(String),
			});
			expect(screen.getByText("RECOMMENDATION APPROVED")).toBeInTheDocument();
			expect(screen.getByText(/Approved Recommendation/i)).toBeInTheDocument();
			expect(screen.getByText(/Tark Recommended:/i)).toBeInTheDocument();
			expect(screen.getByText("DECLINE TRANSACTION")).toBeInTheDocument();
		});
	});

	it("displays error and keeps approval controls when backend API fails", async () => {
		vi.spyOn(apiClient, "submitAnalystDecision").mockRejectedValueOnce(
			new Error("Backend connection timeout"),
		);

		render(<AnalystDecision result={mockResultHumanApproval} />);

		fireEvent.click(
			screen.getByRole("button", { name: /Approve recommendation/i }),
		);

		await waitFor(() => {
			expect(
				screen.getByText("Backend connection timeout"),
			).toBeInTheDocument();
			expect(
				screen.getByRole("button", { name: /Approve recommendation/i }),
			).toBeInTheDocument();
			expect(
				screen.queryByText("RECOMMENDATION APPROVED"),
			).not.toBeInTheDocument();
		});
	});

	it("opens override form, enforces rationale, and records rejection while preserving original recommendation", async () => {
		const submitSpy = vi
			.spyOn(apiClient, "submitAnalystDecision")
			.mockResolvedValueOnce({
				investigation_id: "HHG-014",
				case_status: "REJECTED",
				result: mockResultHumanApproval,
			});

		render(<AnalystDecision result={mockResultHumanApproval} />);

		// 1. Click Reject / Override
		fireEvent.click(
			screen.getByRole("button", { name: /Reject \/ Override/i }),
		);

		expect(
			screen.getByText(/Reject \/ Override Tark Recommendation/i),
		).toBeInTheDocument();
		const confirmBtn = screen.getByRole("button", {
			name: /Confirm override/i,
		});

		// Confirm button is disabled when rationale is empty
		expect(confirmBtn).toBeDisabled();

		// 2. Enter rationale
		const textarea = screen.getByPlaceholderText(
			/Provide mandatory reason for override/i,
		);
		fireEvent.change(textarea, {
			target: { value: "Verified with VIP cardholder directly via phone." },
		});

		expect(confirmBtn).not.toBeDisabled();

		// 3. Confirm override
		fireEvent.click(confirmBtn);

		await waitFor(() => {
			expect(submitSpy).toHaveBeenCalledWith("HHG-014", {
				decision: "REJECT",
				analyst_id: "ANALYST_01",
				rationale: "Verified with VIP cardholder directly via phone.",
			});
			expect(screen.getByText("RECOMMENDATION OVERRIDDEN")).toBeInTheDocument();
			expect(screen.getByText(/Overridden \/ Rejected/i)).toBeInTheDocument();
			expect(
				screen.getByText(/Verified with VIP cardholder directly via phone/i),
			).toBeInTheDocument();
			// Original recommendation is preserved
			expect(screen.getByText(/Tark Recommended:/i)).toBeInTheDocument();
			expect(screen.getByText("DECLINE TRANSACTION")).toBeInTheDocument();
		});
	});

	it("displays automatic action status and avoids showing misleading human approval controls", () => {
		render(<AnalystDecision result={mockResultAuto} />);

		expect(
			screen.getByText(/\[ AUTOMATIC ACTION ALLOWED \]/i),
		).toBeInTheDocument();
		expect(
			screen.getByText(
				/Policy permits autonomous execution without prior analyst sign-off/i,
			),
		).toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /Approve recommendation/i }),
		).not.toBeInTheDocument();
	});

	it("displays further investigation required when decision state is INSUFFICIENT_EVIDENCE", () => {
		render(<AnalystDecision result={mockResultInsufficient} />);

		expect(
			screen.getByText(/\[ FURTHER INVESTIGATION REQUIRED \]/i),
		).toBeInTheDocument();
		expect(
			screen.getByText(/No actionable policy recommendation reached/i),
		).toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: /Approve recommendation/i }),
		).not.toBeInTheDocument();
	});
});
