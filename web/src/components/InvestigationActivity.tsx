import type React from "react";
import { useState } from "react";
import type { InvestigationResultPayload } from "../api/types";

interface InvestigationActivityProps {
	result: InvestigationResultPayload;
}

export const TOOL_DISPLAY_NAMES: Record<
	string,
	{ title: string; checked: string; why: string }
> = {
	QUERY_DEVICE_ANALYSIS: {
		title: "Device neighborhood analysis",
		checked: "Device fingerprint and shared device graph neighborhood.",
		why: "Tark selected device analysis based on expected information value.",
	},
	QUERY_CARD_SEQUENCE: {
		title: "Card transaction sequence",
		checked: "Prior and subsequent transaction velocity and testing patterns.",
		why: "Tark selected card sequence analysis to check for micro-authorization probing.",
	},
	QUERY_TXN_VELOCITY: {
		title: "Transaction velocity analysis",
		checked: "Short-term and medium-term spending frequency on card.",
		why: "Tark selected transaction velocity to detect abnormal transaction bursts.",
	},
	QUERY_REGION_ANALYSIS: {
		title: "Billing & IP region analysis",
		checked:
			"Geographic and IP routing distance relative to cardholder profile.",
		why: "Tark selected billing region analysis to verify geographic consistency.",
	},
	RETRIEVE_HISTORICAL_CASES: {
		title: "Historical case memory retrieval",
		checked:
			"High-dimensional GraphRAG case embeddings for similar precedent fraud patterns.",
		why: "Tark queried historical case memory to retrieve institutional precedents.",
	},
	VERIFY_WITH_CUSTOMER: {
		title: "Cardholder verification simulation",
		checked: "Out-of-band customer verification response channel.",
		why: "Tark simulated customer confirmation channel based on remaining uncertainty.",
	},
	QUERY_POLICY_GRAPH: {
		title: "Policy rule & compliance retrieval",
		checked: "Regulatory mandates and operational escalation policies.",
		why: "Tark retrieved institutional policy rules for required actions.",
	},
};

export const TERMINATION_DISPLAY_NAMES: Record<
	string,
	{ title: string; description: string }
> = {
	DECISION_REACHED: {
		title: "Investigation complete",
		description: "Evidence was sufficient for a definitive policy decision.",
	},
	NO_ADMISSIBLE_EVIDENCE: {
		title: "Investigation stopped",
		description: "No additional admissible evidence was available.",
	},
	MAX_STEPS_REACHED: {
		title: "Investigation stopped",
		description: "Investigation reached the maximum allowed step limit.",
	},
	NEGATIVE_EVOI: {
		title: "Investigation stopped",
		description:
			"Remaining evidence actions had negative expected information value.",
	},
	CONSECUTIVE_FAILURES: {
		title: "Investigation stopped",
		description: "Consecutive tool query threshold reached.",
	},
};

export function cleanFindingText(finding: string): string {
	if (!finding) return "";
	const colonIndex = finding.indexOf(": ");
	if (colonIndex !== -1 && (finding.includes("LR=") || finding.includes("("))) {
		return finding.slice(colonIndex + 2).trim();
	}
	return finding;
}

export function extractLikelihoodRatio(text: string): {
	lr?: string;
	log_lr?: string;
} {
	const lrMatch = text?.match(/LR=([0-9.]+)/);
	const logLrMatch = text?.match(/log_lr=([0-9.-]+)/);
	return {
		lr: lrMatch ? lrMatch[1] : undefined,
		log_lr: logLrMatch ? logLrMatch[1] : undefined,
	};
}

export const InvestigationActivity: React.FC<InvestigationActivityProps> = ({
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

	const termination =
		result.run_result?.termination_reason || "DECISION_REACHED";
	const termInfo = TERMINATION_DISPLAY_NAMES[termination] || {
		title: "Investigation complete",
		description: `Investigation terminated (${termination}).`,
	};

	// Group events into logical steps for clean reading
	const toolEvents = (result.events || []).filter(
		(e) => e.type === "TOOL_COMPLETED",
	);
	const caseOpenedEvent = (result.events || []).find(
		(e) => e.type === "CASE_OPENED",
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
						Investigation Activity
					</h2>
					<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
						Tark’s evidence-gathering process
					</p>
				</div>

				<div>
					<span
						style={{
							fontSize: "11px",
							fontWeight: 700,
							padding: "3px 8px",
							borderRadius: "4px",
							backgroundColor:
								termination === "DECISION_REACHED" ? "#f0fdf4" : "#fffbeb",
							color: termination === "DECISION_REACHED" ? "#15803d" : "#b45309",
							border: `1px solid ${termination === "DECISION_REACHED" ? "#bbf7d0" : "#fde68a"}`,
							letterSpacing: "0.03em",
						}}
					>
						{result.run_result?.step_count || toolEvents.length} STEPS EXECUTED
					</span>
				</div>
			</div>

			{/* Activity Timeline List */}
			<div
				style={{
					display: "flex",
					flexDirection: "column",
					gap: "14px",
					position: "relative",
				}}
			>
				{/* Step 0: Investigation Opened */}
				{caseOpenedEvent && (
					<div
						style={{
							display: "flex",
							gap: "14px",
							alignItems: "flex-start",
						}}
					>
						<div
							style={{
								width: "22px",
								height: "22px",
								borderRadius: "50%",
								backgroundColor: "#f1f5f9",
								color: "#475569",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								fontSize: "11px",
								fontWeight: 700,
								flexShrink: 0,
								marginTop: "2px",
							}}
						>
							✓
						</div>
						<div style={{ flex: 1 }}>
							<div
								style={{
									fontSize: "13.5px",
									fontWeight: 600,
									color: "#0f172a",
								}}
							>
								Investigation opened
							</div>
							<div
								style={{
									fontSize: "12.5px",
									color: "#64748b",
									marginTop: "2px",
								}}
							>
								Case {result.case?.case_id || result.investigation_id} ·
								Trigger:{" "}
								{result.case?.trigger_type?.replace(/_/g, " ") || "alert"}
							</div>
						</div>
					</div>
				)}

				{/* Steps 1..N: Tool Executions */}
				{toolEvents.map((evt, idx) => {
					const rawTool = evt.tool || "UNKNOWN";
					const toolConfig = TOOL_DISPLAY_NAMES[rawTool] || {
						title: rawTool.replace(/_/g, " ").toLowerCase(),
						checked: "Investigative context and graph entity relations.",
						why: "Tark selected this action based on information value.",
					};
					const cleanFinding = cleanFindingText(evt.summary);
					const { lr, log_lr } = extractLikelihoodRatio(evt.summary);
					const isExpanded = !!expandedDetails[evt.id];

					return (
						<div
							key={evt.id}
							style={{
								display: "flex",
								gap: "14px",
								alignItems: "flex-start",
							}}
						>
							{/* Step Icon */}
							<div
								style={{
									width: "22px",
									height: "22px",
									borderRadius: "50%",
									backgroundColor: "#f0fdf4",
									color: "#15803d",
									border: "1px solid #bbf7d0",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									fontSize: "11px",
									fontWeight: 700,
									flexShrink: 0,
									marginTop: "2px",
								}}
							>
								✓
							</div>

							{/* Step Content */}
							<div
								style={{
									flex: 1,
									backgroundColor: "#f8fafc",
									border: "1px solid #eef2f6",
									borderRadius: "6px",
									padding: "12px 16px",
									display: "flex",
									flexDirection: "column",
									gap: "6px",
								}}
							>
								{/* Step Header */}
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
										style={{
											fontSize: "13.5px",
											fontWeight: 600,
											color: "#0f172a",
										}}
									>
										Step {idx + 1} · {toolConfig.title}
									</div>
									<span
										style={{
											fontSize: "11px",
											color: "#64748b",
											backgroundColor: "#ffffff",
											padding: "2px 6px",
											borderRadius: "4px",
											border: "1px solid #e2e8f0",
										}}
									>
										TigerGraph Query
									</span>
								</div>

								{/* Reason (Why) */}
								<div
									style={{
										fontSize: "12px",
										color: "#64748b",
										fontStyle: "italic",
									}}
								>
									{toolConfig.why}
								</div>

								{/* What Tark Checked */}
								<div style={{ fontSize: "13px", color: "#334155" }}>
									<span style={{ fontWeight: 600, color: "#1e293b" }}>
										Checked:{" "}
									</span>
									<span>{toolConfig.checked}</span>
								</div>

								{/* What TigerGraph Found */}
								<div
									style={{
										fontSize: "13px",
										color: "#334155",
										lineHeight: "1.4",
									}}
								>
									<span style={{ fontWeight: 600, color: "#1e293b" }}>
										Found:{" "}
									</span>
									<span>{cleanFinding || evt.summary}</span>
								</div>

								{/* Collapsible Technical Details */}
								<div style={{ marginTop: "2px" }}>
									<button
										onClick={() => toggleDetail(evt.id)}
										style={{
											background: "none",
											border: "none",
											padding: 0,
											color: "#ea580c",
											fontSize: "11.5px",
											fontWeight: 600,
											cursor: "pointer",
											display: "inline-flex",
											alignItems: "center",
											gap: "4px",
										}}
									>
										<span>
											{isExpanded
												? "▼ Hide technical details"
												: "▶ View technical details"}
										</span>
									</button>

									{isExpanded && (
										<div
											style={{
												marginTop: "8px",
												padding: "10px 12px",
												backgroundColor: "#ffffff",
												border: "1px solid #e2e8f0",
												borderRadius: "4px",
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
												<strong style={{ color: "#0f172a" }}>Tool:</strong>{" "}
												{rawTool}
											</div>
											<div>
												<strong style={{ color: "#0f172a" }}>Source:</strong>{" "}
												TigerGraph Graph Engine
											</div>
											{lr && (
												<div>
													<strong style={{ color: "#0f172a" }}>
														Likelihood Ratio (LR):
													</strong>{" "}
													{lr} {log_lr ? `(Log LR: ${log_lr})` : ""}
												</div>
											)}
											<div>
												<strong style={{ color: "#0f172a" }}>
													Raw Finding:
												</strong>{" "}
												{evt.summary}
											</div>
											{evt.details && Object.keys(evt.details).length > 0 && (
												<div style={{ marginTop: "4px" }}>
													<strong style={{ color: "#0f172a" }}>Details:</strong>
													<pre
														style={{
															margin: "4px 0 0 0",
															padding: "6px",
															backgroundColor: "#f8fafc",
															borderRadius: "3px",
															border: "1px solid #f1f5f9",
															whiteSpace: "pre-wrap",
															fontSize: "10px",
															overflowX: "auto",
														}}
													>
														{JSON.stringify(evt.details, null, 2)}
													</pre>
												</div>
											)}
										</div>
									)}
								</div>
							</div>
						</div>
					);
				})}

				{/* Final Step: Investigation Termination */}
				<div
					style={{
						display: "flex",
						gap: "14px",
						alignItems: "flex-start",
					}}
				>
					<div
						style={{
							width: "22px",
							height: "22px",
							borderRadius: "50%",
							backgroundColor:
								termination === "DECISION_REACHED" ? "#f0fdf4" : "#fffbeb",
							color: termination === "DECISION_REACHED" ? "#15803d" : "#b45309",
							border: `1px solid ${termination === "DECISION_REACHED" ? "#bbf7d0" : "#fde68a"}`,
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							fontSize: "11px",
							fontWeight: 700,
							flexShrink: 0,
							marginTop: "2px",
						}}
					>
						✓
					</div>
					<div
						style={{
							flex: 1,
							backgroundColor:
								termination === "DECISION_REACHED" ? "#f0fdf4" : "#fffbeb",
							border: `1px solid ${termination === "DECISION_REACHED" ? "#bbf7d0" : "#fde68a"}`,
							borderRadius: "6px",
							padding: "12px 16px",
						}}
					>
						<div
							style={{ fontSize: "13.5px", fontWeight: 600, color: "#0f172a" }}
						>
							{termInfo.title}
						</div>
						<div
							style={{ fontSize: "12.5px", color: "#475569", marginTop: "2px" }}
						>
							{termInfo.description}
						</div>
						<div
							style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}
						>
							Reason: {termination} · Duration:{" "}
							{result.run_result?.execution_duration_sec
								? `${result.run_result.execution_duration_sec.toFixed(2)}s`
								: "0.2s"}
						</div>
					</div>
				</div>
			</div>
		</div>
	);
};
