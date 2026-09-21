import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { OverviewView } from "../components/OverviewView";
import { BenchmarkView } from "../components/BenchmarkView";
import { PolicyPatternsView } from "../components/PolicyPatternsView";
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

	it("BenchmarkView renders truthful evaluation provenance and avoids static pass badges", async () => {
		await act(async () => {
			render(
				<BenchmarkView
					cases={mockCases}
					onSelectCase={vi.fn()}
				/>
			);
		});

		// Must render commit hash and evaluation header
		expect(screen.getByText(/COMMIT: [0-9a-f]{8}/i)).toBeInTheDocument();
		expect(screen.getByText("Next-Best-Action Agreement")).toBeInTheDocument();

		// Must NOT render fabricated baseline comparison rows
		expect(screen.queryByText("B0: Static Rules Baseline")).not.toBeInTheDocument();
		expect(screen.queryByText("B1: Raw LLM Zero-Shot")).not.toBeInTheDocument();

		// Must NOT render static ✓ PASS stamps
		expect(screen.queryByText("✓ PASS")).not.toBeInTheDocument();
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
