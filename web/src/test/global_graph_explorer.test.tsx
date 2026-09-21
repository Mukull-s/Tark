import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { GlobalGraphExplorer } from "../components/GlobalGraphExplorer";

describe("P0.3 — TigerGraph Schema & Topology Inspector", () => {
	it("renders real TigerGraph schema topology and avoids fake graph algorithm projections", async () => {
		vi.spyOn(globalThis, "fetch").mockImplementation(() =>
			Promise.resolve({
				ok: true,
				json: () =>
					Promise.resolve({
						graph_name: "FraudInvestigation",
						status: "connected",
						total_vertices: 38187,
						vertex_counts: {
							Transaction: 26754,
							ClosedCase: 5565,
							Card: 1951,
							Customer: 1918,
							DeviceProfile: 1835,
						},
						edge_types: [],
						timestamp: "2026-09-21T00:00:00Z",
					}),
			} as any)
		);

		await act(async () => {
			render(<GlobalGraphExplorer />);
		});

		// Must render real TigerGraph inspector title
		expect(
			screen.getByText("TigerGraph Schema & Entity Topology Inspector")
		).toBeInTheDocument();

		// Must render real vertex types from live schema
		expect(screen.getAllByText("Transaction").length).toBeGreaterThan(0);
		expect(screen.getAllByText("Customer").length).toBeGreaterThan(0);
		expect(screen.getAllByText("Card").length).toBeGreaterThan(0);
		expect(screen.getAllByText("DeviceProfile").length).toBeGreaterThan(0);

		// Must NOT render fake algorithm selector or fake syndicate SVG
		expect(screen.queryByText("Louvain Communities")).not.toBeInTheDocument();
		expect(screen.queryByText("COMMUNITY #14 (Syndicate Ring)")).not.toBeInTheDocument();
		expect(screen.queryByText("Weakly Connected Components (WCC)")).not.toBeInTheDocument();
	});
});
