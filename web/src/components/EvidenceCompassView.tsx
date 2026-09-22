import React, { useState } from "react";
import type { InvestigationResultPayload, IterationTraceView, CandidateDecisionMetrics } from "../api/types";
import { TechnicalDetails } from "./TechnicalDetails";

interface EvidenceCompassViewProps {
	result: InvestigationResultPayload;
}

interface ActionMetadata {
	title: string;
	tool: string;
	protocol: "TigerGraph MCP" | "External Adapter" | "Deterministic Core";
	cost: number;
	description: string;
}

const ACTION_REGISTRY: Record<string, ActionMetadata> = {
	QUERY_CARD_SEQUENCE: {
		title: "Card Transaction Sequence Query",
		tool: "card_sequence",
		protocol: "TigerGraph MCP",
		cost: 1.0,
		description: "Traverses TigerGraph to detect micro-authorization card testing patterns (<$5) within a 24-hour anchor window.",
	},
	QUERY_DEVICE_ANALYSIS: {
		title: "Device Neighborhood Syndicate Analysis",
		tool: "device_analysis",
		protocol: "TigerGraph MCP",
		cost: 1.0,
		description: "Executes 2-hop graph traversal to discover multi-card sharing and proxy routing on the focal device.",
	},
	QUERY_TXN_VELOCITY: {
		title: "Short-Window Velocity Scan",
		tool: "txn_velocity",
		protocol: "TigerGraph MCP",
		cost: 1.0,
		description: "Calculates burst velocity and cumulative spend volume across 1-hour and 24-hour sliding temporal windows.",
	},
	QUERY_REGION_ANALYSIS: {
		title: "Geographic & Billing Region Scan",
		tool: "region_analysis",
		protocol: "TigerGraph MCP",
		cost: 1.0,
		description: "Verifies whether transaction billing region matches customer historical profile and card-present travel patterns.",
	},
	QUERY_CUSTOMER_PROFILE: {
		title: "Customer Behavioral Baseline",
		tool: "customer_profile",
		protocol: "TigerGraph MCP",
		cost: 1.0,
		description: "Completes the customer's historical spending baseline (volume, average amount, channel mix) to resolve coverage.",
	},
	VERIFY_WITH_CUSTOMER: {
		title: "Out-of-Band Customer SMS/Email Challenge",
		tool: "verify_with_customer",
		protocol: "External Adapter",
		cost: 3.5,
		description: "Dispatches SMS/push challenge to cardholder. High operational latency burden relative to graph traversal.",
	},
	SIMULATE_CUSTOMER_REPLY: {
		title: "Out-of-Band Customer SMS/Email Challenge",
		tool: "verify_with_customer",
		protocol: "External Adapter",
		cost: 3.5,
		description: "Dispatches SMS/push challenge to cardholder. High operational latency burden relative to graph traversal.",
	},
	STEP_UP_AUTH: {
		title: "Step-Up Multi-Factor Authentication",
		tool: "step_up_auth",
		protocol: "External Adapter",
		cost: 2.0,
		description: "Prompts cardholder for biometric or FIDO2 cryptographic step-up authentication.",
	},
	TRIGGER_STEP_UP_AUTH: {
		title: "Step-Up Multi-Factor Authentication",
		tool: "step_up_auth",
		protocol: "External Adapter",
		cost: 2.0,
		description: "Prompts cardholder for biometric or FIDO2 cryptographic step-up authentication.",
	},
};

function getActionMeta(actionId: string): ActionMetadata {
	const normalized = actionId.toUpperCase();
	if (ACTION_REGISTRY[normalized]) {
		return ACTION_REGISTRY[normalized];
	}
	for (const key of Object.keys(ACTION_REGISTRY)) {
		if (normalized.includes(key) || key.includes(normalized)) {
			return ACTION_REGISTRY[key];
		}
	}
	return {
		title: actionId.replace(/_/g, " "),
		tool: actionId.toLowerCase(),
		protocol: "Deterministic Core",
		cost: 1.0,
		description: `Evaluates ${actionId.replace(/_/g, " ").toLowerCase()} on the active entity graph.`,
	};
}

function parseBeliefProb(val: any): number {
	if (typeof val === "number") return val;
	if (val && typeof val.fraud_probability === "number") return val.fraud_probability;
	return 0.5;
}

interface ParsedEvidence {
	raw: string;
	type: string;
	lr?: number;
	logLr?: number;
	finding: string;
	direction: "incriminating" | "exculpatory" | "neutral";
}

function parseEvidenceSummary(raw?: string): ParsedEvidence | null {
	if (!raw || typeof raw !== "string") return null;

	const match = raw.match(/^([A-Z0-9_]+)\s*\((?:LR=([0-9.]+))?(?:,\s*log_lr=([0-9.-]+))?\):\s*(.*)$/);
	if (match) {
		const type = match[1];
		const lr = match[2] ? parseFloat(match[2]) : undefined;
		const logLr = match[3] ? parseFloat(match[3]) : undefined;
		const finding = match[4] || raw;
		const direction = lr !== undefined && lr > 1.5 ? "incriminating" : (lr !== undefined && lr < 0.8 ? "exculpatory" : "neutral");
		return { raw, type, lr, logLr, finding, direction };
	}

	return {
		raw,
		type: "EMPIRICAL_EVIDENCE",
		finding: raw,
		direction: "neutral",
	};
}

export const EvidenceCompassView: React.FC<EvidenceCompassViewProps> = ({ result }) => {
	const traces: IterationTraceView[] = result.run_result?.iteration_traces || [];
	const [activeStepIndex, setActiveStepIndex] = useState<number>(0);
	const [showTelemetryDetails, setShowTelemetryDetails] = useState<boolean>(false);

	const activeTrace: IterationTraceView | undefined =
		traces.length > 0
			? traces[Math.min(activeStepIndex, traces.length - 1)]
			: undefined;

	// Build candidate list for the active step
	const candidateEntries: Array<{
		actionId: string;
		netEvoi: number | null;
		isExecuted: boolean;
		meta: ActionMetadata;
		status: "SELECTED_AND_EXECUTED" | "DECLINED_NEGATIVE_EVOI" | "DECLINED_SUBOPTIMAL";
		rationale: string;
		metrics?: CandidateDecisionMetrics;
	}> = [];

	if (activeTrace) {
		const rawNetVals = activeTrace.candidate_net_decision_values || {};
		const hasNetVals = Object.keys(rawNetVals).length > 0;

		if (hasNetVals) {
			const sortedActionIds = Object.keys(rawNetVals).sort(
				(a, b) => (rawNetVals[b] ?? -999) - (rawNetVals[a] ?? -999)
			);

			for (const actionId of sortedActionIds) {
				const netEvoi = rawNetVals[actionId] ?? 0;
				const isExecuted =
					actionId.toUpperCase() === activeTrace.selected_action.toUpperCase() ||
					activeTrace.selected_action.toUpperCase().includes(actionId.toUpperCase());
				const meta = getActionMeta(actionId);

				let status: "SELECTED_AND_EXECUTED" | "DECLINED_NEGATIVE_EVOI" | "DECLINED_SUBOPTIMAL";
				let rationale: string;

				if (isExecuted) {
					status = "SELECTED_AND_EXECUTED";
					rationale = `Optimal action selected by Evidence Compass: Highest positive Net Decision Value (${netEvoi > 0 ? "+" : ""}${netEvoi.toFixed(4)}). Authorized and dispatched through TigerGraph MCP protocol boundary.`;
				} else if (netEvoi <= 0) {
					status = "DECLINED_NEGATIVE_EVOI";
					rationale = `Declined by planner: Net Decision Value is non-positive (${netEvoi.toFixed(4)}). Operational and latency cost exceeds expected decision-flip utility.`;
				} else {
					status = "DECLINED_SUBOPTIMAL";
					rationale = `Declined by planner: Positive Net Decision Value (${netEvoi > 0 ? "+" : ""}${netEvoi.toFixed(4)}), but subordinated to primary candidate with superior expected information gain.`;
				}

				candidateEntries.push({
					actionId,
					netEvoi,
					isExecuted,
					meta,
					status,
					rationale,
					metrics: activeTrace.candidate_decision_metrics?.[actionId],
				});
			}
		} else {
			const meta = getActionMeta(activeTrace.selected_action);
			candidateEntries.push({
				actionId: activeTrace.selected_action,
				// No planner Net Decision Value was recorded for this legacy/empty
				// trace; report it as unknown rather than fabricating a number.
				netEvoi: null,
				isExecuted: true,
				meta,
				status: "SELECTED_AND_EXECUTED",
				rationale: "Selected and executed by Evidence Compass as optimal information-gathering step.",
			});
		}
	}

	const beliefBefore = activeTrace ? parseBeliefProb(activeTrace.belief_before) : 0.5;
	const beliefAfter = activeTrace ? parseBeliefProb(activeTrace.belief_after) : 0.5;
	const beliefDelta = beliefAfter - beliefBefore;
	const coverageBefore = activeTrace?.coverage_before ?? 0;
	const coverageAfter = activeTrace?.coverage_after ?? 0;
	const parsedObservation = parseEvidenceSummary(activeTrace?.observed_evidence_summary);

	// Selected (highest-value) candidate for the active step, plus its real
	// decision-theoretic numbers. Prefer the executed candidate; fall back to the
	// top-ranked one when no execution marker is available.
	const selectedCandidate =
		candidateEntries.find((c) => c.isExecuted) ||
		(candidateEntries.length > 0
			? [...candidateEntries].sort((a, b) => (b.netEvoi ?? -Infinity) - (a.netEvoi ?? -Infinity))[0]
			: undefined);

	const netDecisionValue = selectedCandidate?.netEvoi ?? selectedCandidate?.metrics?.net_decision_value;
	const expectedInformationGain = selectedCandidate?.metrics?.expected_decision_value;
	// Normalized Shannon entropy of the current belief (max 1 bit at p = 0.5).
	const currentUncertainty =
		beliefBefore <= 0 || beliefBefore >= 1
			? 0
			: -(beliefBefore * Math.log2(beliefBefore) + (1 - beliefBefore) * Math.log2(1 - beliefBefore));
	const fmtUsd = (v: number | undefined) => (v === undefined ? "—" : `$${v.toFixed(2)}`);

	return (
		<div
			style={{
				backgroundColor: "#ffffff",
				borderRadius: "8px",
				border: "1px solid #e2e8f0",
				padding: "20px 24px",
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
					<div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
						<h2
							style={{
								fontSize: "17px",
								fontWeight: 700,
								color: "#0f172a",
								margin: "0 0 2px 0",
								letterSpacing: "-0.01em",
							}}
						>
							Evidence Compass (EVOI Planner)
						</h2>
						<span
							style={{
								fontSize: "10px",
								fontWeight: 700,
								padding: "2px 6px",
								borderRadius: "3px",
								backgroundColor: "#f8fafc",
								color: "#475569",
								border: "1px solid #e2e8f0",
								textTransform: "uppercase",
								letterSpacing: "0.03em",
							}}
						>
							Deterministic Decision-Theoretic Core
						</span>
					</div>
					<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
						Evaluates Expected Value of Information to select optimal investigative steps without human cognitive fatigue.
					</p>
				</div>

				<div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
					<span
						style={{
							fontSize: "11px",
							fontWeight: 700,
							padding: "4px 8px",
							borderRadius: "4px",
							backgroundColor: "#f0fdf4",
							color: "#15803d",
							border: "1px solid #bbf7d0",
						}}
					>
						OPTIMAL EVOI PATH
					</span>
				</div>
			</div>

			{/* LEVEL 1: DEFAULT HERO — Next Investigation Step */}
			{activeTrace && (
				<div
					style={{
						backgroundColor: "#fffaf5",
						border: "1px solid #fed7aa",
						borderRadius: "8px",
						padding: "16px 20px",
						display: "flex",
						flexDirection: "column",
						gap: "12px",
						boxShadow: "0 1px 3px rgba(234, 88, 12, 0.04)",
					}}
				>
					<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
						<span
							style={{
								fontSize: "11px",
								fontWeight: 800,
								color: "#ea580c",
								textTransform: "uppercase",
								letterSpacing: "0.05em",
							}}
						>
							Highest-Value Investigation Step
						</span>
						<span
							style={{
								fontSize: "11px",
								color: "#9a3412",
								backgroundColor: "#ffedd5",
								padding: "2px 8px",
								borderRadius: "4px",
								fontWeight: 600,
							}}
						>
							Step {activeTrace.iteration} of {traces.length}
						</span>
					</div>

					<div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: "10px" }}>
						<div style={{ fontSize: "17px", fontWeight: 800, color: "#0f172a", letterSpacing: "-0.01em" }}>
							{getActionMeta(activeTrace.selected_action).title}
						</div>
						<div
							style={{
								display: "flex",
								alignItems: "baseline",
								gap: "6px",
								backgroundColor: "#ffedd5",
								border: "1px solid #fed7aa",
								borderRadius: "6px",
								padding: "4px 10px",
							}}
						>
							<span style={{ fontSize: "10.5px", fontWeight: 700, color: "#9a3412", textTransform: "uppercase", letterSpacing: "0.03em" }}>
								Net Decision Value
							</span>
							<span
								style={{
									fontSize: "16px",
									fontWeight: 800,
									fontFamily: "ui-monospace, monospace",
									color: netDecisionValue !== undefined && netDecisionValue > 0 ? "#15803d" : "#9a3412",
								}}
							>
								{netDecisionValue === undefined ? "—" : `${netDecisionValue > 0 ? "+" : ""}${netDecisionValue.toFixed(2)}`}
							</span>
						</div>
					</div>

					<div
						style={{
							display: "grid",
							gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
							gap: "12px",
							paddingTop: "8px",
							borderTop: "1px solid #ffedd5",
						}}
					>
						<div>
							<div style={{ fontSize: "10.5px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
								Expected Information Gain (EDV)
							</div>
							<div style={{ fontSize: "14px", fontWeight: 700, fontFamily: "ui-monospace, monospace", color: "#0f172a", marginTop: "3px" }}>
								{fmtUsd(expectedInformationGain)}
							</div>
						</div>

						<div>
							<div style={{ fontSize: "10.5px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
								Current Uncertainty
							</div>
							<div style={{ fontSize: "14px", fontWeight: 700, fontFamily: "ui-monospace, monospace", color: "#0f172a", marginTop: "3px" }}>
								{currentUncertainty.toFixed(3)} bits
							</div>
						</div>

						<div>
							<div style={{ fontSize: "10.5px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
								Alternatives Evaluated
							</div>
							<div style={{ fontSize: "12px", color: "#64748b", marginTop: "3px", lineHeight: "1.4" }}>
								{candidateEntries
									.filter((c) => !c.isExecuted)
									.slice(0, 3)
									.map((c) => c.meta.title)
									.join(" · ") || "None remaining"}
							</div>
						</div>
					</div>

					<div style={{ fontSize: "11.5px", color: "#64748b", lineHeight: 1.5 }}>
						Selected because it maximises <strong>Net Decision Value</strong>, the highest-value evidence acquisition available at this step. Decision value is zero unless the action can flip the next-best-action or unlock the decision gate.
					</div>
				</div>
			)}

			{/* Multi-Step Iteration Selector */}
			{traces.length > 1 && (
				<div
					style={{
						display: "flex",
						gap: "8px",
						alignItems: "center",
						padding: "8px 12px",
						backgroundColor: "#f8fafc",
						borderRadius: "6px",
						border: "1px solid #e2e8f0",
						flexWrap: "wrap",
					}}
				>
					<span style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", letterSpacing: "0.04em", marginRight: "4px" }}>
						INVESTIGATION TRAJECTORY:
					</span>
					{traces.map((trace, idx) => {
						const isCurrent = idx === activeStepIndex;
						return (
							<button
								key={idx}
								onClick={() => setActiveStepIndex(idx)}
								style={{
									padding: "5px 12px",
									borderRadius: "5px",
									border: isCurrent ? "1px solid #ea580c" : "1px solid #cbd5e1",
									backgroundColor: isCurrent ? "#ea580c" : "#ffffff",
									color: isCurrent ? "#ffffff" : "#334155",
									fontSize: "12px",
									fontWeight: isCurrent ? 700 : 500,
									cursor: "pointer",
									display: "flex",
									alignItems: "center",
									gap: "6px",
									transition: "all 0.15s ease",
								}}
							>
								<span>Step {trace.iteration}</span>
								<span
									style={{
										fontSize: "10px",
										opacity: isCurrent ? 0.9 : 0.7,
										fontFamily: "monospace",
									}}
								>
									({trace.selected_action})
								</span>
							</button>
						);
					})}
				</div>
			)}

			{/* Zero-step alert if no traces were recorded */}
			{traces.length === 0 && (
				<div
					style={{
						backgroundColor: "#f8fafc",
						border: "1px solid #e2e8f0",
						borderRadius: "6px",
						padding: "16px 18px",
						color: "#475569",
						fontSize: "13px",
						lineHeight: 1.5,
					}}
				>
					<strong>Trigger-Only Resolution:</strong> The investigation completed at Step 0. Initial trigger evidence evaluation determined that further candidate queries have non-positive Expected Value of Information (&le; 0), preserving system latency and preventing redundant database traversal.
				</div>
			)}

			{/* Active Step Diagnostic Dashboard (4 Metric Cards) */}
			{activeTrace && (
				<div
					style={{
						display: "grid",
						gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
						gap: "12px",
					}}
				>
					{/* Card 1: Dispatched Tool & Execution Latency */}
					<div
						style={{
							backgroundColor: "#ffffff",
							border: "1px solid #fed7aa",
							borderRadius: "6px",
							padding: "12px 14px",
							display: "flex",
							flexDirection: "column",
							gap: "6px",
							boxShadow: "0 1px 2px rgba(234, 88, 12, 0.04)",
						}}
					>
						<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
							<span style={{ fontSize: "10.5px", fontWeight: 700, color: "#ea580c", textTransform: "uppercase", letterSpacing: "0.03em" }}>
								Dispatched Query
							</span>
							{activeTrace.mcp_telemetry?.duration_ms !== undefined && (
								<span
									style={{
										fontSize: "10.5px",
										fontWeight: 600,
										color: "#475569",
										backgroundColor: "#f1f5f9",
										padding: "1px 5px",
										borderRadius: "3px",
									}}
								>
									{activeTrace.mcp_telemetry.duration_ms}ms
								</span>
							)}
						</div>
						<div style={{ fontSize: "14px", fontWeight: 700, fontFamily: "ui-monospace, monospace", color: "#0369a1" }}>
							{activeTrace.mcp_telemetry?.tool_name || activeTrace.selected_action}
						</div>
						<div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap", marginTop: "auto" }}>
							<span style={{ fontSize: "10.5px", color: "#64748b" }}>
								Protocol: <strong>{getActionMeta(activeTrace.selected_action).protocol}</strong>
							</span>
						</div>
					</div>

					{/* Card 2: Bayesian Belief Shift */}
					<div
						style={{
							backgroundColor: "#ffffff",
							border: "1px solid #e2e8f0",
							borderRadius: "6px",
							padding: "12px 14px",
							display: "flex",
							flexDirection: "column",
							gap: "6px",
						}}
					>
						<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
							<span style={{ fontSize: "10.5px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.03em" }}>
								Belief Shift P(Fraud)
							</span>
							<span
								style={{
									fontSize: "10.5px",
									fontWeight: 700,
									color: beliefDelta >= 0 ? "#b91c1c" : "#15803d",
									backgroundColor: beliefDelta >= 0 ? "#fef2f2" : "#f0fdf4",
									padding: "1px 5px",
									borderRadius: "3px",
								}}
							>
								{beliefDelta >= 0 ? "+" : ""}{(beliefDelta * 100).toFixed(1)}%
							</span>
						</div>
						<div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "2px" }}>
							<span style={{ fontSize: "14px", fontFamily: "ui-monospace, monospace", color: "#64748b" }}>
								{(beliefBefore * 100).toFixed(1)}%
							</span>
							<span style={{ color: "#cbd5e1" }}>&rarr;</span>
							<span style={{ fontSize: "17px", fontFamily: "ui-monospace, monospace", fontWeight: 800, color: "#0f172a" }}>
								{(beliefAfter * 100).toFixed(1)}%
							</span>
						</div>
						<div style={{ width: "100%", height: "4px", backgroundColor: "#e2e8f0", borderRadius: "2px", overflow: "hidden", marginTop: "auto" }}>
							<div
								style={{
									width: `${Math.min(100, Math.max(0, beliefAfter * 100))}%`,
									height: "100%",
									backgroundColor: beliefAfter >= 0.7 ? "#ef4444" : beliefAfter <= 0.3 ? "#22c55e" : "#f59e0b",
									transition: "width 0.3s ease",
								}}
							/>
						</div>
					</div>

					{/* Card 3: Evidence Coverage Progress */}
					<div
						style={{
							backgroundColor: "#ffffff",
							border: "1px solid #e2e8f0",
							borderRadius: "6px",
							padding: "12px 14px",
							display: "flex",
							flexDirection: "column",
							gap: "6px",
						}}
					>
						<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
							<span style={{ fontSize: "10.5px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.03em" }}>
								Evidence Coverage
							</span>
							<span
								style={{
									fontSize: "10.5px",
									fontWeight: 700,
									color: coverageAfter >= 0.4 ? "#15803d" : "#ea580c",
									backgroundColor: coverageAfter >= 0.4 ? "#f0fdf4" : "#fff7ed",
									padding: "1px 5px",
									borderRadius: "3px",
								}}
							>
								{coverageAfter >= 0.4 ? "Gate Eligible" : "Sub-Gate (<40%)"}
							</span>
						</div>
						<div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "2px" }}>
							<span style={{ fontSize: "14px", fontFamily: "ui-monospace, monospace", color: "#64748b" }}>
								{(coverageBefore * 100).toFixed(0)}%
							</span>
							<span style={{ color: "#cbd5e1" }}>&rarr;</span>
							<span style={{ fontSize: "17px", fontFamily: "ui-monospace, monospace", fontWeight: 800, color: "#0f172a" }}>
								{(coverageAfter * 100).toFixed(0)}%
							</span>
						</div>
						<div style={{ width: "100%", height: "4px", backgroundColor: "#e2e8f0", borderRadius: "2px", overflow: "hidden", marginTop: "auto" }}>
							<div
								style={{
									width: `${Math.min(100, Math.max(0, coverageAfter * 100))}%`,
									height: "100%",
									backgroundColor: "#0284c7",
									transition: "width 0.3s ease",
								}}
							/>
						</div>
					</div>

					{/* Card 4: Termination & Policy Check */}
					<div
						style={{
							backgroundColor: "#ffffff",
							border: "1px solid #e2e8f0",
							borderRadius: "6px",
							padding: "12px 14px",
							display: "flex",
							flexDirection: "column",
							gap: "6px",
						}}
					>
						<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
							<span style={{ fontSize: "10.5px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.03em" }}>
								Loop Termination
							</span>
							<span
								style={{
									fontSize: "10.5px",
									fontWeight: 700,
									color: activeTrace.termination_check === "TERMINATE" ? "#b91c1c" : "#0369a1",
									backgroundColor: activeTrace.termination_check === "TERMINATE" ? "#fef2f2" : "#f0f9ff",
									padding: "1px 5px",
									borderRadius: "3px",
								}}
							>
								{activeTrace.termination_check || "EVALUATED"}
							</span>
						</div>
						<div style={{ fontSize: "13px", fontWeight: 600, color: "#0f172a", marginTop: "2px" }}>
							{activeTrace.termination_check === "TERMINATE"
								? "Terminal Criteria Met"
								: "Next Query Authorized"}
						</div>
						<div style={{ fontSize: "11px", color: "#64748b", marginTop: "auto" }}>
							Policy Action: <strong style={{ color: "#0f172a" }}>{result.run_result?.primary_action?.action || "MONITOR_CARD"}</strong>
						</div>
					</div>
				</div>
			)}

			{/* Empirical Evidence Observation Banner */}
			{parsedObservation && (
				<div
					style={{
						backgroundColor: parsedObservation.direction === "incriminating" ? "#fffbfb" : parsedObservation.direction === "exculpatory" ? "#fbfdfb" : "#f8fafc",
						border: `1px solid ${parsedObservation.direction === "incriminating" ? "#fecaca" : parsedObservation.direction === "exculpatory" ? "#bbf7d0" : "#e2e8f0"}`,
						borderRadius: "6px",
						padding: "12px 16px",
						display: "flex",
						flexDirection: "column",
						gap: "6px",
					}}
				>
					<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
						<div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
							<span
								style={{
									fontSize: "11px",
									fontWeight: 700,
									fontFamily: "ui-monospace, monospace",
									backgroundColor: "#ffffff",
									border: "1px solid #cbd5e1",
									padding: "2px 7px",
									borderRadius: "3px",
									color: "#0f172a",
								}}
							>
								{parsedObservation.type}
							</span>
							{parsedObservation.lr !== undefined && (
								<span
									style={{
										fontSize: "11px",
										fontWeight: 700,
										fontFamily: "ui-monospace, monospace",
										backgroundColor: parsedObservation.direction === "incriminating" ? "#fef2f2" : parsedObservation.direction === "exculpatory" ? "#f0fdf4" : "#f1f5f9",
										color: parsedObservation.direction === "incriminating" ? "#b91c1c" : parsedObservation.direction === "exculpatory" ? "#15803d" : "#475569",
										border: `1px solid ${parsedObservation.direction === "incriminating" ? "#fecaca" : parsedObservation.direction === "exculpatory" ? "#bbf7d0" : "#cbd5e1"}`,
										padding: "2px 6px",
										borderRadius: "3px",
									}}
								>
									LR = {parsedObservation.lr}x {parsedObservation.logLr !== undefined ? `(log_lr=${parsedObservation.logLr})` : ""}
								</span>
							)}
						</div>
						<span style={{ fontSize: "11px", color: "#64748b" }}>
							Grounded Observation
						</span>
					</div>

					<div style={{ fontSize: "12.5px", color: "#1e293b", lineHeight: 1.45 }}>
						{parsedObservation.finding}
					</div>

					{/* Collapsible raw observation toggle for forensics */}
					{activeTrace?.mcp_telemetry && (
						<div style={{ marginTop: "4px" }}>
							<button
								onClick={() => setShowTelemetryDetails(!showTelemetryDetails)}
								style={{
									background: "none",
									border: "none",
									padding: 0,
									fontSize: "11px",
									color: "#0284c7",
									cursor: "pointer",
									textDecoration: "underline",
									fontWeight: 500,
								}}
							>
								{showTelemetryDetails ? "Hide MCP Telemetry Trace ▲" : "View MCP Telemetry Trace ▼"}
							</button>

							{showTelemetryDetails && (
								<div
									style={{
										marginTop: "8px",
										backgroundColor: "#0f172a",
										color: "#e2e8f0",
										borderRadius: "4px",
										padding: "10px 12px",
										fontSize: "11px",
										fontFamily: "ui-monospace, monospace",
										overflowX: "auto",
									}}
								>
									<div>Tool: {activeTrace.mcp_telemetry.tool_name}</div>
									<div>Duration: {activeTrace.mcp_telemetry.duration_ms}ms</div>
									<div>Status: {activeTrace.mcp_telemetry.status || "COMPLETED"}</div>
									{activeTrace.mcp_telemetry.session_id && <div>Session: {activeTrace.mcp_telemetry.session_id}</div>}
									{activeTrace.mcp_telemetry.request_id && <div>Request: {activeTrace.mcp_telemetry.request_id}</div>}
									{activeTrace.mcp_telemetry.arguments && (
										<div>Arguments: {JSON.stringify(activeTrace.mcp_telemetry.arguments)}</div>
									)}
								</div>
							)}
						</div>
					)}
				</div>
			)}

			{/* EVOI Candidate Action Decision Matrix */}
			<div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
				<div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", borderBottom: "1px solid #e2e8f0", paddingBottom: "8px" }}>
					<h3 style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a", margin: 0 }}>
						Candidate Actions Evaluated by Evidence Compass
					</h3>
					<span style={{ fontSize: "11.5px", color: "#64748b" }}>
						Ranked by Net Decision Value (EVOI - Cost)
					</span>
				</div>

				<div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
					{candidateEntries.map((cand, idx) => {
						const isExecuted = cand.isExecuted;
						const isNegative = (cand.netEvoi ?? 0) <= 0;

						return (
							<div
								key={idx}
								style={{
									backgroundColor: isExecuted ? "#ffffff" : isNegative ? "#fafbfc" : "#f8fafc",
									border: `1px solid ${isExecuted ? "#fed7aa" : isNegative ? "#e2e8f0" : "#cbd5e1"}`,
									borderRadius: "6px",
									padding: "14px 16px",
									display: "flex",
									flexDirection: "column",
									gap: "10px",
									boxShadow: isExecuted ? "0 1px 3px rgba(234, 88, 12, 0.05)" : "none",
								}}
							>
								{/* Candidate Top Line: Rank, Title, Protocol, Status, Net EVOI */}
								<div
									style={{
										display: "flex",
										justifyContent: "space-between",
										alignItems: "center",
										flexWrap: "wrap",
										gap: "8px",
									}}
								>
									<div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
										<span
											style={{
												fontSize: "10.5px",
												fontWeight: 700,
												color: isExecuted ? "#ffffff" : "#475569",
												backgroundColor: isExecuted ? "#ea580c" : "#e2e8f0",
												padding: "2px 7px",
												borderRadius: "3px",
											}}
										>
											#{idx + 1}
										</span>
										<span
											style={{
												fontSize: "13.5px",
												fontWeight: 700,
												color: isExecuted ? "#0f172a" : "#334155",
											}}
										>
											{cand.meta.title}
										</span>
										<span
											style={{
												fontSize: "10px",
												fontWeight: 700,
												padding: "2px 6px",
												borderRadius: "3px",
												backgroundColor: isExecuted
													? "#fff7ed"
													: isNegative
													? "#f1f5f9"
													: "#f0fdf4",
												color: isExecuted
													? "#ea580c"
													: isNegative
													? "#64748b"
													: "#15803d",
												border: `1px solid ${
													isExecuted
														? "#fed7aa"
														: isNegative
														? "#e2e8f0"
														: "#bbf7d0"
												}`,
											}}
										>
											{cand.status === "SELECTED_AND_EXECUTED"
												? "EXECUTED"
												: cand.status === "DECLINED_NEGATIVE_EVOI"
												? "DECLINED (EVOI ≤ 0)"
												: "DECLINED (SUBOPTIMAL)"}
										</span>
										<span
											style={{
												fontSize: "10px",
												fontFamily: "monospace",
												padding: "1px 5px",
												borderRadius: "3px",
												backgroundColor: "#f1f5f9",
												color: "#475569",
											}}
										>
											{cand.meta.protocol}
										</span>
									</div>

									<div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
										<span
											style={{
												fontSize: "12.5px",
												fontWeight: 700,
												fontFamily: "ui-monospace, monospace",
												color: isExecuted
													? "#15803d"
													: isNegative
													? "#94a3b8"
													: "#0369a1",
												backgroundColor: isExecuted
													? "#f0fdf4"
													: isNegative
													? "#f8fafc"
													: "#f0f9ff",
												padding: "2px 8px",
												borderRadius: "4px",
												border: `1px solid ${
													isExecuted
														? "#bbf7d0"
														: isNegative
														? "#e2e8f0"
														: "#bae6fd"
												}`,
											}}
										>
											Net EVOI:{" "}
											{cand.netEvoi === null
												? "—"
												: `${cand.netEvoi > 0 ? "+" : ""}${cand.netEvoi.toFixed(4)}`}
										</span>
									</div>
								</div>

								{/* Graph Query Description */}
								<div
									style={{
										fontSize: "12px",
										color: "#475569",
										lineHeight: 1.45,
									}}
								>
									{cand.meta.description}
								</div>

								{/* Dynamic Decision Rationale */}
								<div
									style={{
										fontSize: "11.5px",
										color: isExecuted ? "#9a3412" : "#64748b",
										backgroundColor: isExecuted ? "#fffaf5" : "#f8fafc",
										padding: "6px 10px",
										borderRadius: "4px",
										borderLeft: `3px solid ${
											isExecuted ? "#ea580c" : isNegative ? "#cbd5e1" : "#0284c7"
										}`,
									}}
								>
									<strong>Planner Disposition:</strong> {cand.rationale}
								</div>

								{cand.metrics && (
									<div
										style={{
											display: "grid",
											gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
											gap: "8px",
											backgroundColor: "#f8fafc",
											border: "1px solid #e2e8f0",
											borderRadius: "4px",
											padding: "8px 10px",
										}}
									>
										{[
											{ label: "Baseline Loss", value: `$${cand.metrics.baseline_loss.toFixed(2)}`, hint: "Operational loss of the current admissible action." },
											{ label: "E[Posterior Loss]", value: `$${cand.metrics.expected_posterior_loss.toFixed(2)}`, hint: "Expected loss after observing this evidence." },
											{ label: "EDV", value: `+$${cand.metrics.expected_decision_value.toFixed(2)}`, hint: "Baseline loss − expected posterior loss." },
											{ label: "Net Decision Value", value: `${cand.metrics.net_decision_value > 0 ? "+" : ""}$${cand.metrics.net_decision_value.toFixed(2)}`, hint: "EDV − operational burden cost." },
											{ label: "Gate Unlock Prob", value: `${(cand.metrics.gate_unlock_prob * 100).toFixed(1)}%`, hint: "P(decision gate unlocks | acquire this evidence)." },
											{ label: "Action Flip Prob", value: `${(cand.metrics.flip_prob * 100).toFixed(1)}%`, hint: "P(next-best-action changes | acquire this evidence)." },
										].map((m) => (
											<div key={m.label} title={m.hint}>
												<div style={{ fontSize: "10px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.02em" }}>
													{m.label}
												</div>
												<div style={{ fontSize: "12.5px", fontWeight: 700, fontFamily: "ui-monospace, monospace", color: "#0f172a", marginTop: "2px" }}>
													{m.value}
												</div>
											</div>
										))}
									</div>
								)}
							</div>
						);
					})}
				</div>
			</div>

			{/* Technical Formulation & Formal Bellman Criteria Drawer */}
			<div style={{ marginTop: "4px" }}>
				<TechnicalDetails
					title="Mathematical Formulation & Decision-Theoretic Parameters"
					summaryItems={[
						{
							label: "EVOI Equation",
							value: "Net_EVOI(a) = E_y [ max_d U(d, y) ] - max_d U(d) - Cost(a)",
						},
						{
							label: "Admissibility Constraint",
							value: "Actions with non-positive net EVOI or violating policy boundaries are pruned prior to ranking.",
						},
						{
							label: "Active Protocol",
							value: getActionMeta(activeTrace?.selected_action || "").protocol,
						},
						{
							label: "Step Cost",
							value: `${getActionMeta(activeTrace?.selected_action || "").cost} latency/resource penalty units`,
						},
					]}
				/>
			</div>
		</div>
	);
};
