import type React from "react";
import { useState } from "react";
import type {
	EvidenceItemView,
	InvestigationResultPayload,
} from "../api/types";
import { formatEvidenceImpact } from "../utils/presentation";

interface KeyEvidenceFindingsProps {
	result: InvestigationResultPayload;
}

export const EVIDENCE_TYPE_DISPLAY: Record<
	string,
	{ title: string; category: string }
> = {
	SHARED_DEVICE_RING: {
		title: "Shared device network",
		category: "Device Intelligence",
	},
	CARD_TESTING_SEQUENCE: {
		title: "Card transaction sequence",
		category: "Sequence Analysis",
	},
	HIGH_VELOCITY: {
		title: "Transaction velocity",
		category: "Velocity & Frequency",
	},
	OUT_OF_REGION: {
		title: "Billing & IP geography",
		category: "Geographic Profile",
	},
	CALIBRATED_RISK_SCORE: {
		title: "Calibrated alert risk score",
		category: "Alert Assessment",
	},
	CUSTOMER_DENIAL: {
		title: "Cardholder fraud report",
		category: "Customer Reporting",
	},
	CUSTOMER_CONFIRMATION: {
		title: "Cardholder verification confirmation",
		category: "Customer Verification",
	},
	CUSTOMER_COMMUNICATION_UNAVAILABLE: {
		title: "Cardholder verification channel",
		category: "Customer Verification",
	},
	HISTORICAL_CASE_PRECEDENT: {
		title: "Historical precedent match",
		category: "Case Memory",
	},
};

export const SOURCE_DISPLAY_NAMES: Record<string, string> = {
	"tigergraph_query:device_analysis":
		"Device neighborhood analysis (TigerGraph)",
	"tigergraph_query:card_sequence": "Card transaction sequence (TigerGraph)",
	"tigergraph_query:txn_velocity": "Transaction velocity analysis (TigerGraph)",
	"tigergraph_query:region_analysis": "Billing region analysis (TigerGraph)",
	bank_detection_model: "Real-time bank detection model",
	customer_report_trigger: "Inbound customer fraud alert",
	"gateway:simulate_customer_reply":
		"Out-of-band customer verification gateway",
};

export function formatLikelihoodRatio(
	lr: number,
	isExculpatory: boolean,
): string {
	if (lr === 1.0) return "LR 1.0 (Neutral)";
	if (lr > 1.0) return `LR +${lr >= 10 ? lr.toFixed(1) : lr.toFixed(2)}`;
	if (isExculpatory || (lr < 1.0 && lr > 0)) {
		return `LR ${lr.toFixed(2)} (Exculpatory)`;
	}
	return `LR ${lr.toFixed(2)}`;
}

export function cleanFindingText(finding: string): string {
	if (!finding) return "";
	const colonIndex = finding.indexOf(": ");
	if (colonIndex !== -1 && (finding.includes("LR=") || finding.includes("("))) {
		return finding.slice(colonIndex + 2).trim();
	}
	return finding;
}

export function classifyEvidenceItem(item: EvidenceItemView): {
	type: "strong" | "supporting" | "neutral" | "unavailable";
	badgeLabel: string;
	badgeBg: string;
	badgeText: string;
	badgeBorder: string;
} {
	const isUnavailable =
		item.evidence_type.includes("UNAVAILABLE") ||
		(item.details &&
			(item.details.raw?.status === "UNAVAILABLE" ||
				item.details.status === "UNAVAILABLE"));

	if (isUnavailable) {
		return {
			type: "unavailable",
			badgeLabel: "Unavailable check",
			badgeBg: "#f8fafc",
			badgeText: "#64748b",
			badgeBorder: "#e2e8f0",
		};
	}

	if (item.lr >= 2.0 || item.log_lr >= 0.69) {
		return {
			type: "strong",
			badgeLabel: "STRONGEST SIGNAL",
			badgeBg: "#fff7ed",
			badgeText: "#ea580c",
			badgeBorder: "#ffedd5",
		};
	}

	if (item.lr > 1.0 || item.is_exculpatory || item.lr < 1.0) {
		return {
			type: "supporting",
			badgeLabel: "Supporting evidence",
			badgeBg: "#f0fdf4",
			badgeText: "#15803d",
			badgeBorder: "#bbf7d0",
		};
	}

	return {
		type: "neutral",
		badgeLabel: "Normal finding",
		badgeBg: "#f1f5f9",
		badgeText: "#475569",
		badgeBorder: "#e2e8f0",
	};
}

export const KeyEvidenceFindings: React.FC<KeyEvidenceFindingsProps> = ({
	result,
}) => {
	const [expandedDetails, setExpandedDetails] = useState<
		Record<string, boolean>
	>({});

	const toggleDetail = (id: string) => {
		setExpandedDetails((prev) => ({
			...prev,
			[id]: !prev[id],
		}));
	};

	const rawEvidenceItems: EvidenceItemView[] =
		result.run_result?.final_state?.evidence_items || [];

	if (rawEvidenceItems.length === 0) {
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
					Evidence found
				</h2>
				<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
					No evidence signals recorded for this case.
				</p>
			</div>
		);
	}

	// Sort items to prioritize highest signal strength
	const sortedItems = [...rawEvidenceItems].sort((a, b) => {
		const aDev = Math.abs(a.log_lr || Math.log(a.lr || 1.0));
		const bDev = Math.abs(b.log_lr || Math.log(b.lr || 1.0));
		return bDev - aDev;
	});

	// Identify primary/strongest signal vs secondary/supporting findings
	const primaryEvidence =
		sortedItems.find((item) => {
			const classification = classifyEvidenceItem(item);
			return classification.type === "strong";
		}) || (sortedItems[0]?.lr > 1.0 ? sortedItems[0] : null);

	const supportingItems = sortedItems.filter(
		(item) => item !== primaryEvidence,
	);

	// Evidence coverage percentage
	const coverageRatio = result.run_result?.final_state?.evidence_coverage ?? 0;
	const coveragePercent = Math.round(
		coverageRatio <= 1 ? coverageRatio * 100 : coverageRatio,
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
				gap: "20px",
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
						Evidence found
					</h2>
					<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
						The strongest signals discovered during this investigation
					</p>
				</div>

				<div>
					<span
						style={{
							fontSize: "11px",
							fontWeight: 700,
							padding: "3px 8px",
							borderRadius: "4px",
							backgroundColor: "#f1f5f9",
							color: "#475569",
							border: "1px solid #e2e8f0",
							letterSpacing: "0.03em",
						}}
					>
						{rawEvidenceItems.length} SIGNALS EVALUATED
					</span>
				</div>
			</div>

			{/* Primary / Strongest Evidence Card */}
			{primaryEvidence &&
				(() => {
					const typeInfo = EVIDENCE_TYPE_DISPLAY[
						primaryEvidence.evidence_type
					] || {
						title: primaryEvidence.evidence_type
							.replace(/_/g, " ")
							.toLowerCase(),
						category: "Graph Signal",
					};
					const sourceName =
						SOURCE_DISPLAY_NAMES[primaryEvidence.source] ||
						primaryEvidence.source;
					const cleanFinding = cleanFindingText(primaryEvidence.finding);
					const lrDisplay = formatLikelihoodRatio(
						primaryEvidence.lr,
						primaryEvidence.is_exculpatory,
					);
					const classification = classifyEvidenceItem(primaryEvidence);
					const isExpanded = !!expandedDetails[primaryEvidence.evidence_id];

					return (
						<div
							style={{
								backgroundColor: "#fff7ed",
								border: "1px solid #fed7aa",
								borderRadius: "8px",
								padding: "18px 20px",
								display: "flex",
								flexDirection: "column",
								gap: "12px",
							}}
						>
							{/* Top Row: Badge & LR */}
							<div
								style={{
									display: "flex",
									justifyContent: "space-between",
									alignItems: "center",
									flexWrap: "wrap",
									gap: "8px",
								}}
							>
								<div
									style={{ display: "flex", alignItems: "center", gap: "8px" }}
								>
									<span
										style={{
											fontSize: "11px",
											fontWeight: 800,
											padding: "2px 8px",
											borderRadius: "4px",
											backgroundColor: classification.badgeBg,
											color: classification.badgeText,
											border: `1px solid ${classification.badgeBorder}`,
											letterSpacing: "0.04em",
										}}
									>
										{classification.badgeLabel}
									</span>
									<span
										style={{
											fontSize: "15.5px",
											fontWeight: 700,
											color: "#0f172a",
										}}
									>
										{typeInfo.title}
									</span>
								</div>

								<span
									style={{
										fontSize: "13px",
										fontWeight: 700,
										color: "#ea580c",
										fontFamily:
											"ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
									}}
								>
									{lrDisplay}
								</span>
							</div>

							{/* Finding Statement */}
							<div
								style={{
									fontSize: "13.5px",
									color: "#1e293b",
									lineHeight: "1.5",
									fontWeight: 500,
								}}
							>
								{cleanFinding || primaryEvidence.finding}
							</div>

							{/* Impact and Source */}
							{(() => {
								const impactInfo = formatEvidenceImpact(
									primaryEvidence.lr,
									primaryEvidence.is_exculpatory,
								);
								return (
									<div
										style={{
											display: "flex",
											alignItems: "center",
											gap: "10px",
											flexWrap: "wrap",
											fontSize: "12px",
											color: "#64748b",
											padding: "4px 0",
										}}
									>
										<div>
											<strong style={{ color: "#475569" }}>Impact: </strong>
											<span
												style={{
													color: impactInfo.badgeText,
													fontWeight: 700,
												}}
											>
												{impactInfo.label}
											</span>
										</div>
										<span style={{ color: "#cbd5e1" }}>·</span>
										<div>
											<strong style={{ color: "#475569" }}>Source: </strong>
											<span>{sourceName}</span>
										</div>
									</div>
								);
							})()}

							{/* Source and Toggle */}
							<div
								style={{
									display: "flex",
									justifyContent: "flex-end",
									alignItems: "center",
									flexWrap: "wrap",
									gap: "8px",
									paddingTop: "2px",
								}}
							>

								<button
									onClick={() => toggleDetail(primaryEvidence.evidence_id)}
									style={{
										background: "none",
										border: "none",
										padding: 0,
										color: "#ea580c",
										fontSize: "11.5px",
										fontWeight: 600,
										cursor: "pointer",
									}}
								>
									{isExpanded
										? "▼ Hide evidence details"
										: "▶ View evidence details"}
								</button>
							</div>

							{/* Collapsible Technical Details */}
							{isExpanded && (
								<div
									style={{
										marginTop: "6px",
										padding: "12px",
										backgroundColor: "#ffffff",
										border: "1px solid #fed7aa",
										borderRadius: "6px",
										fontSize: "11px",
										fontFamily:
											"ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
										color: "#334155",
										display: "flex",
										flexDirection: "column",
										gap: "6px",
									}}
								>
									<div>
										<strong style={{ color: "#0f172a" }}>Evidence ID:</strong>{" "}
										{primaryEvidence.evidence_id}
									</div>
									<div>
										<strong style={{ color: "#0f172a" }}>Evidence Type:</strong>{" "}
										{primaryEvidence.evidence_type}
									</div>
									<div>
										<strong style={{ color: "#0f172a" }}>
											Likelihood Ratio:
										</strong>{" "}
										{primaryEvidence.lr} (Log LR: {primaryEvidence.log_lr})
									</div>
									<div>
										<strong style={{ color: "#0f172a" }}>Source Engine:</strong>{" "}
										{primaryEvidence.source}
									</div>
									{primaryEvidence.details &&
										Object.keys(primaryEvidence.details).length > 0 && (
											<div style={{ marginTop: "4px" }}>
												<strong style={{ color: "#0f172a" }}>
													Attributes:
												</strong>
												<pre
													style={{
														margin: "4px 0 0 0",
														padding: "6px",
														backgroundColor: "#f8fafc",
														borderRadius: "4px",
														border: "1px solid #f1f5f9",
														whiteSpace: "pre-wrap",
														fontSize: "10px",
													}}
												>
													{JSON.stringify(primaryEvidence.details, null, 2)}
												</pre>
											</div>
										)}
								</div>
							)}
						</div>
					);
				})()}

			{/* Supporting / Secondary Evidence Grid */}
			{supportingItems.length > 0 && (
				<div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
					<div
						style={{
							fontSize: "12px",
							fontWeight: 700,
							color: "#475569",
							textTransform: "uppercase",
							letterSpacing: "0.04em",
						}}
					>
						Supporting Evidence & Checks
					</div>

					<div
						style={{
							display: "grid",
							gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
							gap: "12px",
						}}
					>
						{supportingItems.map((item) => {
							const typeInfo = EVIDENCE_TYPE_DISPLAY[item.evidence_type] || {
								title: item.evidence_type.replace(/_/g, " ").toLowerCase(),
								category: "Signal",
							};
							const sourceName =
								SOURCE_DISPLAY_NAMES[item.source] || item.source;
							const cleanFinding = cleanFindingText(item.finding);
							const classification = classifyEvidenceItem(item);
							const isExpanded = !!expandedDetails[item.evidence_id];

							return (
								<div
									key={item.evidence_id}
									style={{
										backgroundColor: "#ffffff",
										border: "1px solid #e2e8f0",
										borderRadius: "6px",
										padding: "14px",
										display: "flex",
										flexDirection: "column",
										justifyContent: "space-between",
										gap: "10px",
									}}
								>
									<div
										style={{
											display: "flex",
											flexDirection: "column",
											gap: "8px",
										}}
									>
										{/* Header: Title + Badge */}
										<div
											style={{
												display: "flex",
												justifyContent: "space-between",
												alignItems: "flex-start",
												gap: "8px",
											}}
										>
											<span
												style={{
													fontSize: "13px",
													fontWeight: 700,
													color: "#0f172a",
												}}
											>
												{typeInfo.title}
											</span>
											<span
												style={{
													fontSize: "10px",
													fontWeight: 600,
													padding: "2px 6px",
													borderRadius: "3px",
													backgroundColor: classification.badgeBg,
													color: classification.badgeText,
													border: `1px solid ${classification.badgeBorder}`,
													whiteSpace: "nowrap",
												}}
											>
												{classification.badgeLabel}
											</span>
										</div>

										{/* Finding Text */}
										<p
											style={{
												margin: 0,
												fontSize: "12px",
												color: "#334155",
												lineHeight: "1.4",
											}}
										>
											{cleanFinding || item.finding}
										</p>

										{/* Impact */}
										{(() => {
											const itemImpact = formatEvidenceImpact(
												item.lr,
												item.is_exculpatory,
												item.evidence_type.includes("UNAVAILABLE"),
											);
											return (
												<div
													style={{
														fontSize: "11px",
														color: "#64748b",
														marginTop: "2px",
													}}
												>
													<strong style={{ color: "#475569" }}>Impact: </strong>
													<span
														style={{
															color: itemImpact.badgeText,
															fontWeight: 600,
														}}
													>
														{itemImpact.label}
													</span>
												</div>
											);
										})()}
									</div>

									{/* Footer: Source + Details */}
									<div
										style={{
											display: "flex",
											justifyContent: "space-between",
											alignItems: "center",
											paddingTop: "6px",
											borderTop: "1px solid #f1f5f9",
										}}
									>
										<span style={{ fontSize: "11px", color: "#64748b" }}>
											{sourceName.split("(")[0].trim()}
										</span>

										<button
											onClick={() => toggleDetail(item.evidence_id)}
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
											{isExpanded ? "▼ Details" : "▶ Details"}
										</button>
									</div>

									{/* Collapsible Details */}
									{isExpanded && (
										<div
											style={{
												marginTop: "4px",
												padding: "8px",
												backgroundColor: "#f8fafc",
												border: "1px solid #e2e8f0",
												borderRadius: "4px",
												fontSize: "10px",
												fontFamily:
													"ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
												color: "#334155",
												display: "flex",
												flexDirection: "column",
												gap: "4px",
											}}
										>
											<div>
												<strong>ID:</strong> {item.evidence_id}
											</div>
											<div>
												<strong>Type:</strong> {item.evidence_type}
											</div>
											<div>
												<strong>LR:</strong> {item.lr}
											</div>
											<div>
												<strong>Source:</strong> {item.source}
											</div>
											{item.details && Object.keys(item.details).length > 0 && (
												<pre
													style={{
														margin: "2px 0 0 0",
														whiteSpace: "pre-wrap",
														fontSize: "9px",
													}}
												>
													{JSON.stringify(item.details, null, 2)}
												</pre>
											)}
										</div>
									)}
								</div>
							);
						})}
					</div>
				</div>
			)}

			{/* Evidence Coverage Summary */}
			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
					flexWrap: "wrap",
					gap: "12px",
					padding: "10px 14px",
					backgroundColor: "#f8fafc",
					borderRadius: "6px",
					border: "1px solid #eef2f6",
					fontSize: "12px",
					color: "#64748b",
				}}
			>
				<div>
					<span style={{ fontWeight: 600, color: "#334155" }}>
						Evidence coverage:{" "}
					</span>
					<span>{coveragePercent}% of graph evidence space examined</span>
				</div>

				<div>
					<span style={{ fontWeight: 600, color: "#334155" }}>Sources: </span>
					<span>TigerGraph Engine · Detection Model</span>
				</div>
			</div>
		</div>
	);
};
