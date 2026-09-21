import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { InvestigationResultPayload } from "../api/types";
import { EvidenceCompassView } from "../components/EvidenceCompassView";

const mockResultWithTraces: InvestigationResultPayload = {
	investigation_id: "HHG-002",
	case: {
		case_id: "HHG-002",
		opened_at: "2016-11-20 12:00:00",
		trigger_type: "high_risk_score",
		trigger_text: "High risk score 0.88 on transaction 3018431",
		flagged_txn_id: "3018431",
		card_id: "C19512-K1",
		customer_id: "C19512",
		risk_score: 0.88,
	},
	exposure_usd: 150.0,
	initial_state: {
		fraud_probability: 0.88,
		evidence_coverage: 0.17,
		epistemic_uncertainty: 0.83,
		aleatoric_uncertainty: 0.2,
		evidence_items: [],
	},
	run_result: {
		step_count: 2,
		termination_reason: "DECISION_REACHED",
		execution_duration_sec: 0.45,
		iteration_traces: [
			{
				iteration: 1,
				selected_action: "QUERY_CARD_SEQUENCE",
				candidate_net_decision_values: {
					QUERY_CARD_SEQUENCE: 0.4125,
					QUERY_DEVICE_ANALYSIS: 0.284,
					QUERY_TXN_VELOCITY: -0.0512,
					VERIFY_WITH_CUSTOMER: -0.125,
				},
				belief_before: 0.88,
				belief_after: 0.985,
				coverage_before: 0.17,
				coverage_after: 0.33,
				observed_evidence_summary:
					"CARD_TESTING_SEQUENCE (LR=34.3, log_lr=3.535): 3 micro-authorizations observed",
				mcp_telemetry: {
					tool_name: "card_sequence",
					status: "COMPLETED",
					duration_ms: 185,
					session_id: "mcp-session-001",
					request_id: "req-001",
				},
				termination_check: "CONTINUE",
			},
			{
				iteration: 2,
				selected_action: "QUERY_DEVICE_ANALYSIS",
				candidate_net_decision_values: {
					QUERY_DEVICE_ANALYSIS: 0.312,
					QUERY_TXN_VELOCITY: -0.045,
				},
				belief_before: 0.985,
				belief_after: 0.999,
				coverage_before: 0.33,
				coverage_after: 0.5,
				observed_evidence_summary:
					"SHARED_DEVICE_RING (LR=14.2, log_lr=2.653): Device shared across 4 cards",
				mcp_telemetry: {
					tool_name: "device_analysis",
					status: "COMPLETED",
					duration_ms: 220,
				},
				termination_check: "TERMINATE",
			},
		],
		primary_action: {
			action: "BLOCK_CARD",
			role: "primary",
			approval_route: "L1",
			reason: "Confirmed card testing and shared device ring",
			scope: "CARD",
		},
		consequential_actions: [],
		all_actions: [],
		retrieved_precedents: [],
		retrieved_knowledge: [],
		executive_summary: "Test summary",
		grounded_synthesis: "Test synthesis",
		final_state: {
			fraud_probability: 0.999,
			evidence_coverage: 0.5,
			epistemic_uncertainty: 0.05,
			aleatoric_uncertainty: 0.05,
			conflict_metric: 0.0,
			decision_gate_passed: true,
			decision_state: "DECISION_REACHED",
			classification: "fraud",
			evidence_items: [],
		},
	},
	events: [],
};

describe("EvidenceCompassView", () => {
	it("renders dynamic candidates and Net EVOI scores from real iteration trace", () => {
		render(<EvidenceCompassView result={mockResultWithTraces} />);

		// Check headers and mathematically grounded title
		expect(screen.getByText(/Evidence Compass \(EVOI Planner\)/i)).toBeDefined();
		expect(screen.getByText(/Deterministic Decision-Theoretic Core/i)).toBeDefined();

		// Check selected candidate
		expect(screen.getAllByText(/Card Transaction Sequence Query/i).length).toBeGreaterThanOrEqual(1);
		expect(screen.getByText(/Net EVOI: \+0.4125/i)).toBeDefined();
		expect(screen.getByText("EXECUTED")).toBeDefined();

		// Check declined candidates
		expect(screen.getAllByText(/Short-Window Velocity Scan/i).length).toBeGreaterThanOrEqual(1);
		expect(screen.getAllByText(/DECLINED \(EVOI ≤ 0\)/i).length).toBeGreaterThanOrEqual(1);

		// Check telemetry
		expect(screen.getByText(/185ms/i)).toBeDefined();
		expect(screen.getAllByText(/card_sequence/i).length).toBeGreaterThanOrEqual(1);
	});

	it("switches iteration steps when clicking step buttons", () => {
		render(<EvidenceCompassView result={mockResultWithTraces} />);

		const step2Btn = screen.getByRole("button", { name: /Step 2/i });
		expect(step2Btn).toBeDefined();

		fireEvent.click(step2Btn);

		// Step 2 has QUERY_DEVICE_ANALYSIS selected
		expect(screen.getAllByText(/Device Neighborhood Syndicate Analysis/i).length).toBeGreaterThanOrEqual(1);
		expect(screen.getByText(/Net EVOI: \+0.3120/i)).toBeDefined();
		expect(screen.getByText(/220ms/i)).toBeDefined();
	});

	it("handles zero-step / cold-start investigations cleanly", () => {
		const coldStartResult: InvestigationResultPayload = {
			...mockResultWithTraces,
			run_result: {
				...mockResultWithTraces.run_result,
				step_count: 0,
				iteration_traces: [],
			},
		};

		render(<EvidenceCompassView result={coldStartResult} />);
		expect(screen.getByText(/Trigger-Only Resolution/i)).toBeDefined();
	});
});
