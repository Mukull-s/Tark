import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { InvestigationResultPayload } from "../api/types";
import { InvestigationNetwork } from "../components/InvestigationNetwork";

const mockResultWithGraph: InvestigationResultPayload = {
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
			evidence_items: [],
		},
	},
	events: [],
	graph: {
		investigation_id: "HHG-014",
		focal_entity: "3478561",
		nodes: [
			{
				id: "3478561",
				type: "Transaction",
				label: "Txn #3478561",
				subLabel: "$74.96",
				isFocal: true,
				metadata: {
					amount: 74.96,
					timestamp: "2016-11-22 20:11:00",
				},
				relevance: "focal",
			},
			{
				id: "C13487-K1",
				type: "Card",
				label: "Card 7-K1",
				subLabel: "C13487-K1",
				isFocal: false,
				metadata: {
					card_id: "C13487-K1",
					customer_id: "C13487",
				},
				relevance: "inculpatory",
			},
			{
				id: "C13487",
				type: "Customer",
				label: "Customer 3487",
				subLabel: "C13487",
				isFocal: false,
				metadata: {
					customer_id: "C13487",
				},
				relevance: "neutral",
			},
			{
				id: "DEV_c5a193fe0d03",
				type: "Device",
				label: "Device 0d03",
				subLabel: "Ring: 52 cards (Proxy)",
				isFocal: false,
				metadata: {
					device_id: "DEV_c5a193fe0d03",
					is_proxy: true,
					shared_cards: 52,
				},
				relevance: "inculpatory",
			},
			{
				id: "CARD_RING_1",
				type: "Card",
				label: "Card NG_1",
				subLabel: "Syndicate Card",
				isFocal: false,
				metadata: {
					card_id: "CARD_RING_1",
					ring_member: true,
				},
				relevance: "inculpatory",
			},
			{
				id: "CARD_RING_2",
				type: "Card",
				label: "Card NG_2",
				subLabel: "Syndicate Card",
				isFocal: false,
				metadata: {
					card_id: "CARD_RING_2",
					ring_member: true,
				},
				relevance: "inculpatory",
			},
			{
				id: "CARD_RING_3",
				type: "Card",
				label: "Card NG_3",
				subLabel: "Syndicate Card",
				isFocal: false,
				metadata: {
					card_id: "CARD_RING_3",
					ring_member: true,
				},
				relevance: "inculpatory",
			},
			{
				id: "CARD_RING_4",
				type: "Card",
				label: "Card NG_4",
				subLabel: "Syndicate Card",
				isFocal: false,
				metadata: {
					card_id: "CARD_RING_4",
					ring_member: true,
				},
				relevance: "inculpatory",
			},
		],
		edges: [
			{
				id: "EDGE-TXN-CARD",
				source: "3478561",
				target: "C13487-K1",
				relationship: "PERFORMED_WITH_CARD",
				evidence_family: "BASELINE",
				lr: 1.0,
			},
			{
				id: "EDGE-CARD-CUST",
				source: "C13487-K1",
				target: "C13487",
				relationship: "BELONGS_TO_CUSTOMER",
				evidence_family: "BASELINE",
				lr: 1.0,
			},
			{
				id: "EDGE-TXN-DEV",
				source: "3478561",
				target: "DEV_c5a193fe0d03",
				relationship: "USED_DEVICE",
				evidence_family: "SHARED_DEVICE_RING",
				lr: 14.2,
			},
			{
				id: "EDGE-DEV-CARD-1",
				source: "DEV_c5a193fe0d03",
				target: "CARD_RING_1",
				relationship: "SHARED_DEVICE_RING",
				evidence_family: "SHARED_DEVICE_RING",
				lr: 14.2,
			},
		],
		summary: {
			node_count: 8,
			edge_count: 4,
			evidence_edge_count: 2,
		},
	},
};

describe("Phase UI-05 — Investigation Network / Evidence Graph", () => {
	beforeEach(() => {
		vi.restoreAllMocks();
	});

	it("renders section header, subtitle, and zoom controls", () => {
		render(<InvestigationNetwork result={mockResultWithGraph} />);

		expect(screen.getByText("Investigation network")).toBeInTheDocument();
		expect(
			screen.getByText(
				"Relationships relevant to the evidence discovered during this investigation",
			),
		).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Zoom +" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Zoom -" })).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Reset" })).toBeInTheDocument();
	});

	it("identifies focal transaction with FOCAL TXN badge", () => {
		render(<InvestigationNetwork result={mockResultWithGraph} />);

		expect(screen.getByText("FOCAL TXN")).toBeInTheDocument();
		expect(screen.getAllByText("Txn #3478561").length).toBeGreaterThanOrEqual(
			1,
		);
		expect(screen.getByText("$74.96")).toBeInTheDocument();
	});

	it("renders key entity nodes (Card, Customer, Device)", () => {
		render(<InvestigationNetwork result={mockResultWithGraph} />);

		expect(screen.getByText("Card 7-K1")).toBeInTheDocument();
		expect(screen.getByText("Customer 3487")).toBeInTheDocument();
		expect(screen.getByText("Device 0d03")).toBeInTheDocument();
		expect(screen.getByText("KEY SIGNAL")).toBeInTheDocument();
	});

	it("summarizes large card ring neighborhood without overwhelming the view", () => {
		render(<InvestigationNetwork result={mockResultWithGraph} />);

		expect(
			screen.getByText("+48 additional cards in ring"),
		).toBeInTheDocument();
	});

	it("keeps technical details collapsed by default and only shows raw JSON when expanded", () => {
		render(<InvestigationNetwork result={mockResultWithGraph} />);

		// Default focal transaction is selected
		// Raw JSON is NOT in the document initially
		expect(screen.queryByText(/Raw Metadata:/i)).not.toBeInTheDocument();
		expect(
			screen.queryByText(/"timestamp": "2016-11-22 20:11:00"/i),
		).not.toBeInTheDocument();

		// Default view shows only entity type, name, context
		expect(screen.getAllByText(/Transaction/i).length).toBeGreaterThanOrEqual(
			1,
		);
		expect(
			screen.getAllByText(/FLAGGED TRANSACTION/i).length,
		).toBeGreaterThanOrEqual(1);
		expect(
			screen.getByRole("button", { name: "View technical details" }),
		).toBeInTheDocument();

		// Click to expand technical details
		fireEvent.click(
			screen.getByRole("button", { name: "View technical details" }),
		);

		expect(screen.getByText("Hide technical details")).toBeInTheDocument();
		expect(screen.getByText(/Raw Metadata:/i)).toBeInTheDocument();
		expect(
			screen.getByText(/"timestamp": "2016-11-22 20:11:00"/i),
		).toBeInTheDocument();

		// Click to collapse
		fireEvent.click(
			screen.getByRole("button", { name: "Hide technical details" }),
		);
		expect(screen.queryByText(/Raw Metadata:/i)).not.toBeInTheDocument();

		// Switch to Device node - ensures it starts collapsed
		fireEvent.click(screen.getByText("Device 0d03"));
		expect(screen.queryByText(/Raw Metadata:/i)).not.toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "View technical details" }),
		).toBeInTheDocument();

		// Expand device technical details
		fireEvent.click(
			screen.getByRole("button", { name: "View technical details" }),
		);
		expect(screen.getByText(/"shared_cards": 52/i)).toBeInTheDocument();
	});

	it("handles missing graph data gracefully", () => {
		const emptyResult: InvestigationResultPayload = {
			...mockResultWithGraph,
			graph: undefined,
		};

		render(<InvestigationNetwork result={emptyResult} />);

		expect(
			screen.getByText(
				"No graph relationships recorded for this investigation.",
			),
		).toBeInTheDocument();
	});

	it("discloses reconstructed representative entities instead of presenting them as queried vertices", () => {
		const baseGraph = mockResultWithGraph.graph!;
		const reconstructedResult: InvestigationResultPayload = {
			...mockResultWithGraph,
			graph: {
				...baseGraph,
				nodes: baseGraph.nodes.map((n) =>
					n.id.startsWith("CARD_RING_") ? { ...n, is_reconstructed: true } : { ...n, is_reconstructed: false },
				),
				summary: {
					...baseGraph.summary,
					live_node_count: 4,
					reconstructed_node_count: 4,
					reconstructed_node_ids: ["CARD_RING_1", "CARD_RING_2", "CARD_RING_3", "CARD_RING_4"],
					has_reconstructed_nodes: true,
					reconstruction_notice:
						"Related entities reconstructed from investigation evidence: 4 representative node(s).",
				},
			},
		};

		render(<InvestigationNetwork result={reconstructedResult} />);

		// Disclosure banner is shown, and explicitly describes the reconstruction.
		const notice = screen.getByTestId("reconstructed-nodes-notice");
		expect(notice).toBeInTheDocument();
		expect(notice.textContent).toMatch(/Related entities reconstructed from investigation evidence/i);
		expect(notice.textContent).toMatch(/4 of 8 nodes/i);

		// Selecting a reconstructed node shows the per-node badge.
		fireEvent.click(screen.getByText("Card NG_1"));
		expect(screen.getByText("Reconstructed")).toBeInTheDocument();
	});
});
