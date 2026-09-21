import type React from "react";
import { useMemo, useState } from "react";
import type {
	GraphNode,
	GraphView,
	InvestigationResultPayload,
} from "../api/types";

interface InvestigationNetworkProps {
	result: InvestigationResultPayload;
}

interface PositionedNode extends GraphNode {
	x: number;
	y: number;
	width: number;
	height: number;
}

export const InvestigationNetwork: React.FC<InvestigationNetworkProps> = ({
	result,
}) => {
	const graph: GraphView | undefined = result.graph;
	const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
	const [zoomLevel, setZoomLevel] = useState<number>(1);
	const [showTechnical, setShowTechnical] = useState<boolean>(false);

	// Fallback if graph data is missing
	if (!graph || !graph.nodes || graph.nodes.length === 0) {
		return (
			<div
				style={{
					backgroundColor: "#ffffff",
					borderRadius: "8px",
					border: "1px solid #e2e8f0",
					padding: "24px",
					boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
				}}
			>
				<h2
					style={{
						fontSize: "18px",
						fontWeight: 700,
						color: "#0f172a",
						margin: "0 0 4px 0",
						letterSpacing: "-0.01em",
					}}
				>
					Investigation network
				</h2>
				<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
					No graph relationships recorded for this investigation.
				</p>
			</div>
		);
	}

	// Find focal node
	const focalNode = graph.nodes.find(
		(n) => n.isFocal || n.id === graph.focal_entity,
	);
	const effectiveFocalId =
		focalNode?.id || graph.focal_entity || graph.nodes[0].id;

	// Compute deterministic coordinates for all graph entities
	const positionedNodes: PositionedNode[] = useMemo(() => {
		const nodes = graph.nodes;
		const nodeMap = new Map<string, GraphNode>();
		nodes.forEach((n) => nodeMap.set(n.id, n));

		const resultPositions: PositionedNode[] = [];

		// Find key entities
		const focal = nodes.find((n) => n.isFocal || n.id === effectiveFocalId);
		const mainCard = nodes.find(
			(n) => n.type === "Card" && !n.id.includes("RING") && n.id !== focal?.id,
		);
		const customer = nodes.find((n) => n.type === "Customer");
		const device = nodes.find((n) => n.type === "Device");
		const ringCards = nodes.filter(
			(n) => n.id.includes("RING") || (n.metadata && n.metadata.ring_member),
		);
		const microAuths = nodes.filter(
			(n) =>
				n.id.includes("MICRO") ||
				(n.metadata && n.metadata.type === "micro_authorization"),
		);
		const velocityTxns = nodes.filter((n) => n.id.includes("VEL"));

		const placedIds = new Set<string>();

		// 1. Focal Transaction (Center-Left)
		if (focal) {
			resultPositions.push({
				...focal,
				x: 360,
				y: 150,
				width: 170,
				height: 54,
			});
			placedIds.add(focal.id);
		}

		// 2. Main Card (Left of Focal)
		if (mainCard) {
			resultPositions.push({
				...mainCard,
				x: 140,
				y: 150,
				width: 140,
				height: 50,
			});
			placedIds.add(mainCard.id);
		}

		// 3. Customer (Above Main Card)
		if (customer) {
			resultPositions.push({
				...customer,
				x: 140,
				y: 40,
				width: 140,
				height: 50,
			});
			placedIds.add(customer.id);
		}

		// 4. Device (Right of Focal or Below Focal)
		if (device) {
			resultPositions.push({
				...device,
				x: 590,
				y: 150,
				width: 160,
				height: 54,
			});
			placedIds.add(device.id);
		}

		// 5. Ring Cards (Discovered under Device)
		if (ringCards.length > 0) {
			const startX = 460;
			const spacingX = 105;
			ringCards.forEach((rc, i) => {
				resultPositions.push({
					...rc,
					x: startX + i * spacingX,
					y: 290,
					width: 95,
					height: 44,
				});
				placedIds.add(rc.id);
			});
		}

		// 6. Micro-auth sequences (Below Main Card)
		if (microAuths.length > 0) {
			const startX = 60;
			const spacingX = 110;
			microAuths.forEach((ma, i) => {
				resultPositions.push({
					...ma,
					x: startX + i * spacingX,
					y: 290,
					width: 100,
					height: 44,
				});
				placedIds.add(ma.id);
			});
		}

		// 7. Velocity transactions (Below Micro-auths or Left)
		if (velocityTxns.length > 0) {
			velocityTxns.forEach((vt, i) => {
				if (!placedIds.has(vt.id)) {
					resultPositions.push({
						...vt,
						x: 60 + i * 110,
						y: 360,
						width: 100,
						height: 44,
					});
					placedIds.add(vt.id);
				}
			});
		}

		// 8. Any remaining nodes (placed in a tidy column on right)
		let remainingIndex = 0;
		nodes.forEach((n) => {
			if (!placedIds.has(n.id)) {
				resultPositions.push({
					...n,
					x: 700,
					y: 50 + remainingIndex * 65,
					width: 120,
					height: 48,
				});
				placedIds.add(n.id);
				remainingIndex++;
			}
		});

		return resultPositions;
	}, [graph, effectiveFocalId]);

	const positionedNodeMap = useMemo(() => {
		const map = new Map<string, PositionedNode>();
		positionedNodes.forEach((pn) => map.set(pn.id, pn));
		return map;
	}, [positionedNodes]);

	const selectedNode = selectedNodeId
		? positionedNodeMap.get(selectedNodeId) ||
			graph.nodes.find((n) => n.id === selectedNodeId)
		: positionedNodeMap.get(effectiveFocalId);

	// Check if device has a large shared-card ring count
	const deviceNode = graph.nodes.find((n) => n.type === "Device");
	const sharedCardsCount = deviceNode?.metadata?.shared_cards || 0;
	const renderedRingCardsCount = graph.nodes.filter((n) =>
		n.id.includes("RING"),
	).length;
	const additionalCardsCount = Math.max(
		0,
		sharedCardsCount - renderedRingCardsCount,
	);

	return (
		<div
			style={{
				backgroundColor: "#ffffff",
				borderRadius: "8px",
				border: "1px solid #e2e8f0",
				padding: "22px 24px",
				boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
				display: "flex",
				flexDirection: "column",
				gap: "18px",
			}}
		>
			{/* Section Header */}
			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "flex-start",
					flexWrap: "wrap",
					gap: "12px",
				}}
			>
				<div>
					<h2
						style={{
							fontSize: "17px",
							fontWeight: 700,
							color: "#0f172a",
							margin: "0 0 2px 0",
							letterSpacing: "-0.01em",
						}}
					>
						Investigation network
					</h2>
					<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
						Relationships relevant to the evidence discovered during this
						investigation
					</p>
				</div>

				{/* Graph Controls */}
				<div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
					<button
						onClick={() => setZoomLevel((z) => Math.min(1.4, z + 0.1))}
						style={{
							padding: "4px 8px",
							backgroundColor: "#ffffff",
							border: "1px solid #cbd5e1",
							borderRadius: "4px",
							fontSize: "11.5px",
							fontWeight: 600,
							color: "#334155",
							cursor: "pointer",
						}}
					>
						Zoom +
					</button>
					<button
						onClick={() => setZoomLevel((z) => Math.max(0.7, z - 0.1))}
						style={{
							padding: "4px 8px",
							backgroundColor: "#ffffff",
							border: "1px solid #cbd5e1",
							borderRadius: "4px",
							fontSize: "11.5px",
							fontWeight: 600,
							color: "#334155",
							cursor: "pointer",
						}}
					>
						Zoom -
					</button>
					<button
						onClick={() => {
							setZoomLevel(1);
							setSelectedNodeId(effectiveFocalId);
						}}
						style={{
							padding: "4px 10px",
							backgroundColor: "#f1f5f9",
							border: "1px solid #cbd5e1",
							borderRadius: "4px",
							fontSize: "11.5px",
							fontWeight: 600,
							color: "#0f172a",
							cursor: "pointer",
						}}
					>
						Reset
					</button>
				</div>
			</div>

			{/* SVG Graph Canvas Container */}
			<div
				style={{
					backgroundColor: "#fafbfc",
					border: "1px solid #e2e8f0",
					borderRadius: "8px",
					overflow: "hidden",
					position: "relative",
				}}
			>
				<svg
					viewBox="0 0 860 420"
					style={{
						width: "100%",
						height: "auto",
						maxHeight: "440px",
						display: "block",
						transform: `scale(${zoomLevel})`,
						transformOrigin: "center center",
						transition: "transform 0.15s ease-out",
					}}
				>
					<defs>
						<filter id="node-shadow" x="-5%" y="-5%" width="115%" height="120%">
							<feDropShadow
								dx="0"
								dy="1"
								stdDeviation="1.5"
								floodColor="#0f172a"
								floodOpacity="0.06"
							/>
						</filter>
					</defs>

					{/* Render Edges */}
					<g className="graph-edges">
						{graph.edges.map((edge) => {
							const src = positionedNodeMap.get(edge.source);
							const tgt = positionedNodeMap.get(edge.target);
							if (!src || !tgt) return null;

							const x1 = src.x + src.width / 2;
							const y1 = src.y + src.height / 2;
							const x2 = tgt.x + tgt.width / 2;
							const y2 = tgt.y + tgt.height / 2;

							const isEvidenceEdge =
								(edge.lr && edge.lr > 1.0) ||
								edge.evidence_family === "SHARED_DEVICE_RING";
							const isSelected =
								selectedNodeId === edge.source ||
								selectedNodeId === edge.target;

							const strokeColor = isEvidenceEdge
								? "#ea580c"
								: isSelected
									? "#3b82f6"
									: "#94a3b8";
							const strokeWidth = isEvidenceEdge ? 2.2 : isSelected ? 2.0 : 1.4;
							const strokeDash = edge.relationship?.includes("SEQUENCE")
								? "4,3"
								: "none";

							const midX = (x1 + x2) / 2;
							const midY = (y1 + y2) / 2;

							return (
								<g key={edge.id}>
									<line
										x1={x1}
										y1={y1}
										x2={x2}
										y2={y2}
										stroke={strokeColor}
										strokeWidth={strokeWidth}
										strokeDasharray={strokeDash}
									/>
									{isEvidenceEdge && edge.lr && (
										<g transform={`translate(${midX}, ${midY - 8})`}>
											<rect
												x="-30"
												y="-8"
												width="60"
												height="16"
												rx="3"
												fill="#fff7ed"
												stroke="#fed7aa"
												strokeWidth="1"
											/>
											<text
												x="0"
												y="3"
												textAnchor="middle"
												fontSize="9"
												fontWeight="700"
												fill="#ea580c"
												fontFamily="ui-monospace, monospace"
											>
												LR +{edge.lr.toFixed(1)}
											</text>
										</g>
									)}
								</g>
							);
						})}
					</g>

					{/* Render Nodes */}
					<g className="graph-nodes">
						{positionedNodes.map((node) => {
							const isFocal = node.isFocal || node.id === effectiveFocalId;
							const isSelected = selectedNodeId === node.id;
							const isEvidenceSource =
								node.type === "Device" &&
								(node.metadata?.shared_cards > 1 ||
									node.relevance === "inculpatory");

							// Visual styling
							let bgColor = "#ffffff";
							let borderColor = "#cbd5e1";
							let borderWidth = 1.2;

							if (isFocal) {
								bgColor = "#fff7ed";
								borderColor = "#ea580c";
								borderWidth = 2;
							} else if (isEvidenceSource) {
								bgColor = "#fffbeb";
								borderColor = "#f59e0b";
								borderWidth = 1.8;
							} else if (isSelected) {
								borderColor = "#2563eb";
								borderWidth = 2;
							}

							return (
								<g
									key={node.id}
									transform={`translate(${node.x}, ${node.y})`}
									onClick={() => {
										setSelectedNodeId(node.id);
										setShowTechnical(false);
									}}
									style={{ cursor: "pointer" }}
									filter="url(#node-shadow)"
								>
									{/* Card Background */}
									<rect
										width={node.width}
										height={node.height}
										rx="6"
										fill={bgColor}
										stroke={borderColor}
										strokeWidth={borderWidth}
									/>

									{/* Focal / Evidence Indicator Badge */}
									{isFocal && (
										<g transform={`translate(8, -8)`}>
											<rect width="64" height="15" rx="3" fill="#ea580c" />
											<text
												x="32"
												y="10"
												textAnchor="middle"
												fontSize="8"
												fontWeight="800"
												fill="#ffffff"
												letterSpacing="0.05em"
											>
												FOCAL TXN
											</text>
										</g>
									)}

									{isEvidenceSource && !isFocal && (
										<g transform={`translate(${node.width - 64}, -8)`}>
											<rect width="58" height="15" rx="3" fill="#f59e0b" />
											<text
												x="29"
												y="10"
												textAnchor="middle"
												fontSize="8"
												fontWeight="800"
												fill="#ffffff"
												letterSpacing="0.03em"
											>
												KEY SIGNAL
											</text>
										</g>
									)}

									{/* Entity Type Label */}
									<text
										x="10"
										y="16"
										fontSize="9"
										fontWeight="700"
										fill={isFocal ? "#9a3412" : "#64748b"}
										letterSpacing="0.04em"
										style={{ textTransform: "uppercase" }}
									>
										{node.type}
									</text>

									{/* Node Main Label */}
									<text
										x="10"
										y="32"
										fontSize="12"
										fontWeight="700"
										fill="#0f172a"
									>
										{node.label || node.id}
									</text>

									{/* SubLabel / Detail */}
									{node.subLabel && (
										<text
											x="10"
											y="46"
											fontSize="9.5"
											fontWeight="500"
											fill={isFocal ? "#ea580c" : "#475569"}
										>
											{node.subLabel}
										</text>
									)}
								</g>
							);
						})}
					</g>

					{/* Large Neighborhood Summary Badge near Device if applicable */}
					{additionalCardsCount > 0 && deviceNode && (
						<g transform={`translate(610, 360)`}>
							<rect
								x="-10"
								y="-10"
								width="200"
								height="28"
								rx="5"
								fill="#f8fafc"
								stroke="#cbd5e1"
								strokeWidth="1"
								strokeDasharray="3,3"
							/>
							<text
								x="90"
								y="7"
								textAnchor="middle"
								fontSize="10"
								fontWeight="600"
								fill="#475569"
							>
								+{additionalCardsCount} additional cards in ring
							</text>
						</g>
					)}
				</svg>
			</div>

			{/* Selected Entity / Relationship Detail Panel */}
			{selectedNode && (
				<div
					style={{
						backgroundColor: "#f8fafc",
						border: "1px solid #eef2f6",
						borderRadius: "6px",
						padding: "14px 18px",
						display: "flex",
						flexDirection: "column",
						gap: "10px",
					}}
				>
					<div
						style={{
							display: "flex",
							justifyContent: "space-between",
							alignItems: "flex-start",
							flexWrap: "wrap",
							gap: "8px",
						}}
					>
						<div>
							<div
								style={{ display: "flex", alignItems: "center", gap: "8px" }}
							>
								<span
									style={{
										fontSize: "11px",
										fontWeight: 700,
										textTransform: "uppercase",
										padding: "2px 6px",
										borderRadius: "3px",
										backgroundColor: selectedNode.isFocal
											? "#fff7ed"
											: "#e2e8f0",
										color: selectedNode.isFocal ? "#ea580c" : "#334155",
									}}
								>
									{selectedNode.type}
								</span>
								<span
									style={{
										fontSize: "14.5px",
										fontWeight: 700,
										color: "#0f172a",
									}}
								>
									{selectedNode.label || selectedNode.id}
								</span>
							</div>
							<p
								style={{
									margin: "3px 0 0 0",
									fontSize: "12px",
									color: "#64748b",
								}}
							>
								Entity ID:{" "}
								<code style={{ color: "#0f172a", fontWeight: 600 }}>
									{selectedNode.id}
								</code>
							</p>
						</div>

						{selectedNode.isFocal && (
							<span
								style={{
									fontSize: "11px",
									fontWeight: 700,
									padding: "3px 8px",
									borderRadius: "4px",
									backgroundColor: "#fff7ed",
									color: "#ea580c",
									border: "1px solid #ffedd5",
								}}
							>
								FLAGGED TRANSACTION
							</span>
						)}
					</div>

					{/* Context & Related Evidence Explanation */}
					<div
						style={{
							fontSize: "13px",
							color: "#334155",
							lineHeight: "1.45",
							display: "flex",
							flexDirection: "column",
							gap: "6px",
						}}
					>
						{selectedNode.type === "Device" &&
							selectedNode.metadata?.shared_cards > 1 && (
								<>
									<div>
										<strong style={{ color: "#0f172a" }}>
											Relationship:{" "}
										</strong>
										<span>Hardware terminal used to initiate transaction.</span>
									</div>
									<div>
										<strong style={{ color: "#0f172a" }}>
											Related Evidence:{" "}
										</strong>
										<span>
											Shared device syndicate ring (
											{selectedNode.metadata.shared_cards} cards linked, proxy
											detected). Produces strong inculpatory signal (LR +14.2).
										</span>
									</div>
									<div>
										<strong style={{ color: "#0f172a" }}>
											Why This Matters:{" "}
										</strong>
										<span>
											High-density card sharing on a single device or proxy endpoint is the primary indicator of organized syndicate fraud.
										</span>
									</div>
								</>
							)}

						{selectedNode.isFocal && (
							<>
								<div>
									<strong style={{ color: "#0f172a" }}>
										Relationship:{" "}
									</strong>
									<span>Focal anchor transaction under current investigation.</span>
								</div>
								<div>
									<strong style={{ color: "#0f172a" }}>
										Investigation Origin:{" "}
									</strong>
									<span>
										Flagged transaction triggering autonomous investigation on{" "}
										{selectedNode.metadata?.timestamp || "alert"}.
									</span>
								</div>
								<div>
									<strong style={{ color: "#0f172a" }}>
										Why This Matters:{" "}
									</strong>
									<span>
										Anchors graph exploration, belief updates, and regulatory filing requirements.
									</span>
								</div>
							</>
						)}

						{selectedNode.type === "Card" && (
							<>
								<div>
									<strong style={{ color: "#0f172a" }}>
										Relationship:{" "}
									</strong>
									<span>
										{selectedNode.id.includes("RING")
											? "Syndicate member payment instrument linked via device."
											: "Primary card instrument used in focal authorization."}
									</span>
								</div>
								<div>
									<strong style={{ color: "#0f172a" }}>Card Context: </strong>
									<span>
										{selectedNode.id.includes("RING")
											? "Discovered syndicate card sharing the flagged device fingerprint."
											: `Primary payment instrument associated with Customer ${selectedNode.metadata?.customer_id || ""}.`}
									</span>
								</div>
								<div>
									<strong style={{ color: "#0f172a" }}>
										Why This Matters:{" "}
									</strong>
									<span>
										Determines whether compromise is localized to one card or systemic across a cardholder / syndicate cluster.
									</span>
								</div>
							</>
						)}

						{selectedNode.type === "Customer" && (
							<>
								<div>
									<strong style={{ color: "#0f172a" }}>
										Relationship:{" "}
									</strong>
									<span>Account holder and legal entity associated with card.</span>
								</div>
								<div>
									<strong style={{ color: "#0f172a" }}>Customer Profile: </strong>
									<span>
										Account owner of the primary card instrument under
										investigation.
									</span>
								</div>
								<div>
									<strong style={{ color: "#0f172a" }}>
										Why This Matters:{" "}
									</strong>
									<span>
										Establishes baseline tenure, historical disputes, and typical transaction behavior for anomaly scoring.
									</span>
								</div>
							</>
						)}
					</div>

					{/* Neighborhood Summary if Device has 52 cards */}
					{selectedNode.type === "Device" && sharedCardsCount > 0 && (
						<div
							style={{
								fontSize: "12px",
								color: "#475569",
								backgroundColor: "#ffffff",
								padding: "8px 12px",
								borderRadius: "4px",
								border: "1px solid #e2e8f0",
							}}
						>
							<strong>Connected Cards: </strong> {sharedCardsCount} total ·{" "}
							{renderedRingCardsCount} shown in graph sample · +
							{additionalCardsCount} recorded in TigerGraph
						</div>
					)}

					{/* Technical Details Collapsible */}
					<div style={{ paddingTop: "2px" }}>
						<button
							onClick={() => setShowTechnical(!showTechnical)}
							style={{
								background: "none",
								border: "none",
								padding: 0,
								color: "#ea580c",
								fontSize: "11px",
								fontWeight: 600,
								cursor: "pointer",
							}}
						>
							{showTechnical
								? "Hide technical details"
								: "View technical details"}
						</button>

						{showTechnical && selectedNode.metadata && (
							<div
								style={{
									marginTop: "8px",
									padding: "10px 12px",
									backgroundColor: "#ffffff",
									border: "1px solid #cbd5e1",
									borderRadius: "4px",
									fontSize: "11px",
									fontFamily: "ui-monospace, monospace",
									color: "#334155",
								}}
							>
								<div style={{ marginBottom: "4px", color: "#64748b" }}>
									<strong>Raw Metadata:</strong>
								</div>
								<pre
									style={{
										margin: 0,
										whiteSpace: "pre-wrap",
										fontSize: "10px",
									}}
								>
									{JSON.stringify(selectedNode.metadata, null, 2)}
								</pre>
							</div>
						)}
					</div>
				</div>
			)}
		</div>
	);
};
