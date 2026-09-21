import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { InvestigationResultPayload } from "../api/types";
import { ExplanationSarView } from "../components/ExplanationSarView";

const mockResultWithGroundedSar: InvestigationResultPayload = {
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
		iteration_traces: [],
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
		executive_summary: "Deterministic executive summary",
		grounded_synthesis: `### 1. Primary Subject & Case Metadata
Subject Cardholder C19512 with Card C19512-K1. Flagged transaction 3018431 ($150.00).

### 2. Suspicious Activity Pattern & Typology
Empirical investigation observed card testing sequence [EVD-CARD_TESTING_SEQUENCE-1] followed by rapid authorization.

### 3. Chronological Trajectory of Events
Initial trigger high risk score 0.88 led to TigerGraph graph exploration.

### 4. Graph & Entity Topology Analysis
Device profile analysis confirmed device sharing across multiple cards [EVD-SHARED_DEVICE_RING-1]. Similar precedent [CC-2016-0814] exhibits matching modus operandi.

### 5. Policy Rules & Statutory Basis
Governed under statutory mandate [KNOW-REG-SAR-MANDATE] and policy rule [KNOW-POLICY-R2].

### 6. Investigation Trajectory & EVOI Rationale
Evidence Compass prioritized GSQL query sequence based on positive Net Decision Value.

### 7. Recommended Action & Risk Mitigation
Immediate card block [BLOCK_CARD] under L1 authorization.`,
		final_state: {
			fraud_probability: 0.992,
			evidence_coverage: 0.67,
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

describe("ExplanationSarView", () => {
	it("renders live grounded synthesis sections from backend rather than hardcoded text", () => {
		render(<ExplanationSarView result={mockResultWithGroundedSar} />);

		// Verify 7 sections are rendered from the grounded synthesis
		expect(screen.getByText("1. Primary Subject & Case Metadata")).toBeDefined();
		expect(screen.getByText("2. Suspicious Activity Pattern & Typology")).toBeDefined();
		expect(screen.getByText("4. Graph & Entity Topology Analysis")).toBeDefined();
		expect(screen.getByText("5. Policy Rules & Statutory Basis")).toBeDefined();
		expect(screen.getByText("7. Recommended Action & Risk Mitigation")).toBeDefined();

		// Check that the hardcoded R5 text from the old view is NOT present
		expect(
			screen.queryByText(/Policy rule R5: Micro-authorization detection sequence/i)
		).toBeNull();
	});

	it("renders dynamic citation badges for empirical evidence, precedents, and knowledge", () => {
		render(<ExplanationSarView result={mockResultWithGroundedSar} />);

		expect(screen.getByText("[EVD-CARD_TESTING_SEQUENCE-1]")).toBeDefined();
		expect(screen.getByText("[EVD-SHARED_DEVICE_RING-1]")).toBeDefined();
		expect(screen.getByText("[CC-2016-0814]")).toBeDefined();
		expect(screen.getByText("[KNOW-REG-SAR-MANDATE]")).toBeDefined();
		expect(screen.getByText("[KNOW-POLICY-R2]")).toBeDefined();

		// Check FinCEN compliance card
		expect(screen.getByText("SAR FILING MANDATED")).toBeDefined();
		expect(screen.getByText(/31 U.S.C. 5318\(g\)/i)).toBeDefined();
	});

	it("handles copy text and export clicks without crashing", () => {
		// Mock clipboard
		Object.assign(navigator, {
			clipboard: {
				writeText: vi.fn().mockImplementation(() => Promise.resolve()),
			},
		});

		render(<ExplanationSarView result={mockResultWithGroundedSar} />);

		const copyBtn = screen.getByRole("button", { name: /Copy Text/i });
		fireEvent.click(copyBtn);

		expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
			expect.stringContaining("### 1. Primary Subject & Case Metadata")
		);
	});
});
