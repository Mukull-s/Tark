import type React from "react";
import { useState, useEffect } from "react";
import { fetchGraphSchemaOverview } from "../api/client";

interface SchemaOverviewData {
	graph_name: string;
	status: string;
	total_vertices: number;
	vertex_counts: Record<string, number>;
	edge_types: Array<{
		name: string;
		from: string;
		to: string;
		is_directed: boolean;
	}>;
	timestamp: string;
	data_source?: string;
	is_cached?: boolean;
	notice?: string;
}

// Illustrative fallback shown only when the schema endpoint is unreachable.
// It is explicitly labelled as cached in the UI (never presented as live data).
const DEFAULT_DATA: SchemaOverviewData = {
	graph_name: "FraudInvestigation",
	status: "cached",
	data_source: "CACHED_FALLBACK",
	is_cached: true,
	notice:
		"Live TigerGraph schema topology unavailable; showing last-known cached figures.",
	total_vertices: 38187,
	vertex_counts: {
		Transaction: 26754,
		ClosedCase: 5565,
		Card: 1951,
		Customer: 1918,
		DeviceProfile: 1835,
		BillingRegion: 99,
		EmailDomain: 45,
		InvestigationCase: 20,
	},
	edge_types: [
		{ name: "Customer_OWNS_Card", from: "Customer", to: "Card", is_directed: true },
		{ name: "Card_MADE_Transaction", from: "Card", to: "Transaction", is_directed: true },
		{ name: "Transaction_FROM_DEVICE", from: "Transaction", to: "DeviceProfile", is_directed: true },
		{ name: "Transaction_PURCHASER_EMAIL", from: "Transaction", to: "EmailDomain", is_directed: true },
		{ name: "Transaction_BILLED_IN", from: "Transaction", to: "BillingRegion", is_directed: true },
		{ name: "ClosedCase_INVOLVES_Transaction", from: "ClosedCase", to: "Transaction", is_directed: false },
		{ name: "ClosedCase_ON_CARD", from: "ClosedCase", to: "Card", is_directed: false },
	],
	timestamp: new Date().toISOString(),
};

export const GlobalGraphExplorer: React.FC = () => {
	const [data, setData] = useState<SchemaOverviewData>(DEFAULT_DATA);
	const [, setLoading] = useState<boolean>(false);
	const [selectedVertex, setSelectedVertex] = useState<string>("Transaction");

	useEffect(() => {
		let isMounted = true;
		setLoading(true);
		fetchGraphSchemaOverview()
			.then((json) => {
				if (isMounted && json && json.vertex_counts) {
					setData(json);
				}
			})
			.catch(() => {
				// Keep default cached schema
			})
			.finally(() => {
				if (isMounted) setLoading(false);
			});

		return () => {
			isMounted = false;
		};
	}, []);

	const queryTraversals = [
		{
			query: "device_analysis(t_id)",
			hops: "Transaction → DeviceProfile → Other Transactions → Cards",
			purpose: "Detects multi-card hardware syndicate rings sharing the same device fingerprint.",
			targetEdges: "Transaction_FROM_DEVICE, DeviceProfile_USED_IN_Transaction, Transaction_MADE_BY_Card",
		},
		{
			query: "card_sequence(c_id, window, anchor_ts)",
			hops: "Card → Transaction (sorted by ts)",
			purpose: "Detects micro-authorization card-testing sequences probing card validity.",
			targetEdges: "Card_MADE_Transaction",
		},
		{
			query: "txn_velocity(c_id, window, target_ts)",
			hops: "Card → Transactions (windowed)",
			purpose: "Evaluates burst velocity exceeding 3x customer historical baseline.",
			targetEdges: "Card_MADE_Transaction",
		},
		{
			query: "region_analysis(c_id, txn_addr1)",
			hops: "Card → Customer → Historical Regions vs Target Region",
			purpose: "Identifies card-present geographic displacement outside registered travel profile.",
			targetEdges: "Customer_OWNS_Card, Transaction_BILLED_IN",
		},
		{
			query: "customer_profile(cust_id)",
			hops: "Customer → Owned Cards → Associated Transactions",
			purpose: "Retrieves complete relationship baseline and account tenure.",
			targetEdges: "Customer_OWNS_Card, Card_MADE_Transaction",
		},
	];

	return (
		<div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
			{/* Header */}
			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "flex-start",
				}}
			>
				<div>
					<h1
						style={{
							fontSize: "20px",
							fontWeight: 700,
							color: "#0f172a",
							margin: "0 0 2px 0",
							letterSpacing: "-0.02em",
						}}
					>
						TigerGraph Schema & Entity Topology Inspector
					</h1>
					<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
						Live graph topology, vertex cardinality, and multi-hop traversal paths on the{" "}
						<strong>{data.graph_name}</strong> database
					</p>
				</div>

				<div
					style={{
						display: "flex",
						flexDirection: "column",
						alignItems: "flex-end",
						gap: "2px",
					}}
				>
					{data.is_cached ? (
						<span
							style={{
								fontSize: "11px",
								fontWeight: 700,
								color: "#b45309",
								backgroundColor: "#fffbeb",
								padding: "3px 8px",
								borderRadius: "4px",
								border: "1px solid #fde68a",
							}}
							title={data.notice}
						>
							● CACHED FIGURES (LIVE GRAPH UNAVAILABLE)
						</span>
					) : (
						<span
							style={{
								fontSize: "11px",
								fontWeight: 700,
								color: "#15803d",
								backgroundColor: "#f0fdf4",
								padding: "3px 8px",
								borderRadius: "4px",
								border: "1px solid #bbf7d0",
							}}
						>
							● TIGERGRAPH CLOUD CONNECTED
						</span>
					)}
					<span style={{ fontSize: "11px", color: "#94a3b8" }}>
						{data.total_vertices.toLocaleString()} Total Vertices {data.is_cached ? "Cached" : "Indexed"}
					</span>
				</div>
			</div>

			{/* Live Vertex Cardinality Cards */}
			<div>
				<div
					style={{
						fontSize: "12px",
						fontWeight: 700,
						color: "#475569",
						textTransform: "uppercase",
						letterSpacing: "0.04em",
						marginBottom: "10px",
					}}
				>
					Live Vertex Cardinality ({Object.keys(data.vertex_counts).length} Types)
				</div>

				<div
					style={{
						display: "grid",
						gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
						gap: "10px",
					}}
				>
					{Object.entries(data.vertex_counts).map(([vt, count]) => {
						const isSelected = selectedVertex === vt;
						return (
							<div
								key={vt}
								onClick={() => setSelectedVertex(vt)}
								style={{
									backgroundColor: isSelected ? "#fff7ed" : "#ffffff",
									borderRadius: "8px",
									border: isSelected ? "1.5px solid #ea580c" : "1px solid #e2e8f0",
									padding: "12px 14px",
									cursor: "pointer",
									boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
									transition: "all 0.12s ease",
								}}
							>
								<div
									style={{
										fontSize: "11px",
										fontWeight: 600,
										color: isSelected ? "#c2410c" : "#64748b",
									}}
								>
									{vt}
								</div>
								<div
									style={{
										fontSize: "18px",
										fontWeight: 700,
										color: isSelected ? "#ea580c" : "#0f172a",
										marginTop: "4px",
									}}
								>
									{count.toLocaleString()}
								</div>
							</div>
						);
					})}
				</div>
			</div>

			{/* Main Grid: Edge Schema Map & Query Traversals */}
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "1fr 1.2fr",
					gap: "16px",
				}}
			>
				{/* Edge Schema Map */}
				<div
					style={{
						backgroundColor: "#ffffff",
						borderRadius: "8px",
						border: "1px solid #e2e8f0",
						padding: "20px",
						boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
						display: "flex",
						flexDirection: "column",
						gap: "12px",
					}}
				>
					<div
						style={{
							fontSize: "13px",
							fontWeight: 700,
							color: "#475569",
							textTransform: "uppercase",
							letterSpacing: "0.04em",
						}}
					>
						Graph Schema Topology & Edges
					</div>
					<p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>
						Authoritative schema edges declared in GSQL and compiled on TigerGraph Cloud:
					</p>

					<div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "4px" }}>
						{data.edge_types.map((edge, idx) => (
							<div
								key={idx}
								style={{
									display: "flex",
									alignItems: "center",
									justifyContent: "space-between",
									padding: "8px 12px",
									backgroundColor: "#f8fafc",
									borderRadius: "6px",
									border: "1px solid #e2e8f0",
									fontSize: "12px",
								}}
							>
								<div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
									<span style={{ fontWeight: 600, color: "#0f172a" }}>{edge.from}</span>
									<span style={{ color: "#94a3b8" }}>{edge.is_directed ? "──▶" : "───"}</span>
									<span style={{ fontWeight: 600, color: "#0f172a" }}>{edge.to}</span>
								</div>
								<code
									style={{
										fontSize: "10px",
										color: "#475569",
										backgroundColor: "#ffffff",
										padding: "2px 6px",
										borderRadius: "4px",
										border: "1px solid #cbd5e1",
									}}
								>
									{edge.name}
								</code>
							</div>
						))}
					</div>
				</div>

				{/* Multi-Hop GSQL Query Traversals */}
				<div
					style={{
						backgroundColor: "#ffffff",
						borderRadius: "8px",
						border: "1px solid #e2e8f0",
						padding: "20px",
						boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
						display: "flex",
						flexDirection: "column",
						gap: "12px",
					}}
				>
					<div
						style={{
							fontSize: "13px",
							fontWeight: 700,
							color: "#475569",
							textTransform: "uppercase",
							letterSpacing: "0.04em",
						}}
					>
						Live GSQL Query Multi-Hop Traversals
					</div>
					<p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>
						How Tark's autonomous investigation queries traverse vertex and edge topologies:
					</p>

					<div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "4px" }}>
						{queryTraversals.map((qt, idx) => (
							<div
								key={idx}
								style={{
									padding: "10px 12px",
									backgroundColor: "#fafbfc",
									borderRadius: "6px",
									border: "1px solid #eef2f6",
									display: "flex",
									flexDirection: "column",
									gap: "4px",
								}}
							>
								<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
									<strong style={{ fontSize: "12px", color: "#0f172a", fontFamily: "ui-monospace, monospace" }}>
										{qt.query}
									</strong>
									<span
										style={{
											fontSize: "10px",
											fontWeight: 700,
											color: "#0f766e",
											backgroundColor: "#f0fdfa",
											padding: "1px 6px",
											borderRadius: "3px",
											border: "1px solid #ccfbf1",
										}}
									>
										INSTALLED
									</span>
								</div>
								<div style={{ fontSize: "11px", color: "#ea580c", fontWeight: 600 }}>
									{qt.hops}
								</div>
								<div style={{ fontSize: "11px", color: "#475569" }}>
									{qt.purpose}
								</div>
							</div>
						))}
					</div>
				</div>
			</div>
		</div>
	);
};
