import { describe, it, expect, vi } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import { OverviewView } from "../components/OverviewView";
import { BenchmarkView } from "../components/BenchmarkView";
import { PolicyPatternsView } from "../components/PolicyPatternsView";
import * as client from "../api/client";
import type { CaseMetadata } from "../api/types";

const mockCases: CaseMetadata[] = [
	{
		case_id: "HHG-001",
		opened_at: "2016-11-12 00:00:00",
		trigger_type: "risk_score",
		trigger_text: "High risk score 0.88",
		flagged_txn_id: "3000001",
		card_id: "C10001-A1",
		customer_id: "U10001",
		risk_score: 0.88,
		status: "OPEN",
	},
	{
		case_id: "HHG-002",
		opened_at: "2016-11-12 01:00:00",
		trigger_type: "customer_report",
		trigger_text: "Customer report",
		flagged_txn_id: "3000002",
		card_id: "C10002-A2",
		customer_id: "U10002",
		risk_score: 0.72,
		status: "OPEN",
	},
];

describe("P0.2 — Frontend Truthfulness & Integrity", () => {
	it("OverviewView displays truthful operational metrics and avoids fabricated 100% claims", () => {
		render(
			<OverviewView
				cases={mockCases}
				onSelectCase={vi.fn()}
				onNavigateBenchmark={vi.fn()}
			/>
		);

		// Must render dynamic queue count
		expect(screen.getByText("Queue Cases")).toBeInTheDocument();
		expect(screen.getByText("2")).toBeInTheDocument();

		// Must NOT render fabricated marketing claims
		expect(screen.queryByText("Action Accuracy")).not.toBeInTheDocument();
		expect(screen.queryByText("Decision-Flip Precision")).not.toBeInTheDocument();
		expect(screen.queryByText("Wasted Requests")).not.toBeInTheDocument();
	});

	it("BenchmarkView never shows fabricated metrics before the artifact loads, then renders real values", async () => {
		let resolveSummary: (v: any) => void = () => {};
		const pending = new Promise((resolve) => {
			resolveSummary = resolve;
		});
		const spy = vi.spyOn(client, "fetchBenchmarkSummary").mockReturnValue(pending as any);

		act(() => {
			render(<BenchmarkView cases={mockCases} onSelectCase={vi.fn()} />);
		});

		// While loading: a skeleton is shown and NO fabricated numbers appear.
		expect(screen.getByTestId("benchmark-loading-skeleton")).toBeInTheDocument();
		expect(screen.queryByText(/20\/20/)).not.toBeInTheDocument();
		expect(screen.queryByText(/100%/)).not.toBeInTheDocument();
		expect(screen.queryByText(/13\/20/)).not.toBeInTheDocument();
		expect(screen.queryByText(/COMMIT:/)).not.toBeInTheDocument();

		await act(async () => {
			resolveSummary({
				commit_sha: "abcdef1234567890",
				timestamp: "2026-09-23T00:00:00Z",
				total_cases: 20,
				headline: {
					policy_invariant_conformance_pct: 100,
					partial_credit_pct: 96.5,
					partial_credit_score: 0.965,
					rubric_agreement_detail: { pct: 90, count: 18, scored_cases: 20 },
				},
				policy_conformance_count: 20,
				policy_conformance_pct: 100,
				partial_credit_score: 0.965,
				partial_credit_pct: 96.5,
				nba_agreement_count: 18,
				nba_agreement_pct: 90,
				gate_pass_count: 15,
				gate_pass_pct: 75,
				fraud_verdict_count: 15,
				fraud_verdict_pct: 75,
				avg_steps: 2.6,
				avg_coverage: 0.4,
				avg_duration_sec: 1.0,
				tool_distribution: { QUERY_DEVICE_ANALYSIS: 19, QUERY_CARD_SEQUENCE: 10 },
				case_comparisons: [],
			});
		});

		await waitFor(() =>
			expect(screen.getByText(/COMMIT: abcdef12/)).toBeInTheDocument(),
		);
		// Real, artifact-sourced values are shown (not the removed fallback values).
		expect(screen.getByText("Next-Best-Action Agreement")).toBeInTheDocument();
		expect(screen.getByText("18/20")).toBeInTheDocument();
		// Percentages are intentionally not displayed in the scoreboard tiles.
		expect(screen.queryByText(/100%/)).not.toBeInTheDocument();
		// The old fabricated gate-pass "13/20" must never appear for this artifact.
		expect(screen.queryByText(/13\/20/)).not.toBeInTheDocument();

		// Must NOT render fabricated baseline comparison rows or static pass stamps.
		expect(screen.queryByText("B0: Static Rules Baseline")).not.toBeInTheDocument();
		expect(screen.queryByText("B1: Raw LLM Zero-Shot")).not.toBeInTheDocument();
		expect(screen.queryByText("✓ PASS")).not.toBeInTheDocument();

		spy.mockRestore();
	});

	it("BenchmarkView shows an explicit unavailable state (no placeholder scores) when the artifact cannot load", async () => {
		const spy = vi
			.spyOn(client, "fetchBenchmarkSummary")
			.mockRejectedValue(new Error("network down"));

		await act(async () => {
			render(<BenchmarkView cases={mockCases} onSelectCase={vi.fn()} />);
		});

		await waitFor(() =>
			expect(screen.getByTestId("benchmark-unavailable")).toBeInTheDocument(),
		);
		expect(screen.queryByText(/100%/)).not.toBeInTheDocument();
		expect(screen.queryByText(/20\/20/)).not.toBeInTheDocument();

		spy.mockRestore();
	});

	it("PolicyPatternsView displays authoritative institutional rules without benchmark case coupling", () => {
		render(<PolicyPatternsView />);

		// Must render institutional rules R1 through R10
		expect(screen.getByText("R1")).toBeInTheDocument();
		expect(screen.getByText("Weak Single Signal Verification Mandate")).toBeInTheDocument();
		expect(screen.getByText("R6")).toBeInTheDocument();
		expect(screen.getByText("Multi-Card Shared Device Syndicate Ring")).toBeInTheDocument();
		expect(screen.getByText("R10")).toBeInTheDocument();

		// Must NOT render benchmark case citations
		expect(screen.queryByText("Cited in Benchmark Cases")).not.toBeInTheDocument();
		expect(screen.queryByText(/HHG-003, HHG-004/i)).not.toBeInTheDocument();
	});
});
