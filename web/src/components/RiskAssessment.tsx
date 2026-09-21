import type React from "react";
import { useState } from "react";
import type {
	InvestigationResultPayload,
	IterationTraceView,
} from "../api/types";
import { cleanFindingText, TOOL_DISPLAY_NAMES } from "./InvestigationActivity";
import { TechnicalDetails } from "./TechnicalDetails";

interface RiskAssessmentProps {
	result: InvestigationResultPayload;
}

export function extractFraudProb(val: any): number {
	if (typeof val === "number") return val;
	if (val && typeof val.fraud_probability === "number")
		return val.fraud_probability;
	return 0.5;
}

export function getRiskLevel(prob: number): {
	label: string;
	bg: string;
	text: string;
	border: string;
} {
	if (prob >= 0.85) {
		return {
			label: "HIGH RISK",
			bg: "#fff7ed",
			text: "#ea580c",
			border: "#ffedd5",
		};
	}
	if (prob >= 0.4) {
		return {
			label: "MODERATE RISK",
			bg: "#fefce8",
			text: "#ca8a04",
			border: "#fef08a",
		};
	}
	return {
		label: "LOW RISK",
		bg: "#f0fdf4",
		text: "#15803d",
		border: "#bbf7d0",
	};
}

export const RiskAssessment: React.FC<RiskAssessmentProps> = ({ result }) => {
	const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
	const [expandedDetails, setExpandedDetails] = useState<
		Record<string, boolean>
	>({});

	const toggleDetail = (id: string) => {
		setExpandedDetails((prev) => ({
			...prev,
			[id]: !prev[id],
		}));
	};

	const initialProb = extractFraudProb(
		result.initial_state?.fraud_probability ?? 0.5,
	);
	const finalProb = extractFraudProb(
		result.run_result?.final_state?.fraud_probability ?? initialProb,
	);

	const initialPercent = (initialProb * 100).toFixed(1);
	const finalPercent = (finalProb * 100).toFixed(1);
	const delta = (finalProb - initialProb) * 100;
	const deltaSign = delta > 0 ? "+" : "";
	const currentRisk = getRiskLevel(finalProb);
	const initialRisk = getRiskLevel(initialProb);

	const traces: IterationTraceView[] =
		result.run_result?.iteration_traces || [];

	const priorOdds = initialProb < 1 ? initialProb / Math.max(0.0001, 1 - initialProb) : 999;
	const posteriorOdds = finalProb < 1 ? finalProb / Math.max(0.0001, 1 - finalProb) : 999;
	const lrItems = traces.map((t, i) => {
		const lrMatch = t.observed_evidence_summary?.match(/LR=([0-9.]+)/);
		const logLrMatch = t.observed_evidence_summary?.match(/log_lr=([0-9.-]+)/);
		const lr = lrMatch ? lrMatch[1] : "1.0";
		const logLr = logLrMatch ? logLrMatch[1] : "0.0";
		return `Step ${i + 1} (${t.selected_action}): LR=${lr}x, Δln(O)=${logLr}`;
	});

	// Build trajectory points
	const trajectoryPoints = [
		{
			name: "Initial",
			subName: "Prior",
			prob: initialProb,
			action: "INITIAL_PRIOR",
			finding: "Initial alert-conditioned prior baseline",
			impact: "Baseline prior probability",
		},
		...traces.map((t, idx) => {
			const probBefore = extractFraudProb(t.belief_before);
			const probAfter = extractFraudProb(t.belief_after);
			const diff = probAfter - probBefore;
			const rawTool = t.selected_action;
			const toolInfo = TOOL_DISPLAY_NAMES[rawTool] || {
				title: rawTool.replace(/_/g, " ").toLowerCase(),
				checked: "",
				why: "",
			};

			let impact = "No material change";
			let impactType: "positive" | "negative" | "neutral" = "neutral";

			if (diff > 0.05) {
				impact = `Strongly increased fraud probability (+${(diff * 100).toFixed(1)}%)`;
				impactType = "positive";
			} else if (diff < -0.05) {
				impact = `Decreased fraud probability (${(diff * 100).toFixed(1)}%)`;
				impactType = "negative";
			} else if (
				t.observed_evidence_summary?.includes("UNAVAILABLE") ||
				rawTool.includes("CUSTOMER")
			) {
				impact = "Assessment unchanged";
				impactType = "neutral";
			}

			return {
				name: toolInfo.title,
				subName: `Step ${idx + 1}`,
				prob: probAfter,
				probBefore,
				diff,
				action: rawTool,
				finding: cleanFindingText(t.observed_evidence_summary || ""),
				rawSummary: t.observed_evidence_summary || "",
				impact,
				impactType,
			};
		}),
	];

	// SVG Chart Dimensions
	const chartWidth = 780;
	const chartHeight = 180;
	const padLeft = 50;
	const padRight = 40;
	const padTop = 20;
	const padBottom = 35;
	const innerWidth = chartWidth - padLeft - padRight;
	const innerHeight = chartHeight - padTop - padBottom;

	const numPoints = trajectoryPoints.length;
	const stepX = numPoints > 1 ? innerWidth / (numPoints - 1) : innerWidth;

	const pointsCoordinates = trajectoryPoints.map((pt, i) => {
		const x = padLeft + (numPoints > 1 ? i * stepX : innerWidth / 2);
		const y = padTop + (1 - Math.max(0, Math.min(1, pt.prob))) * innerHeight;
		return { ...pt, x, y, index: i };
	});

	const polylinePoints = pointsCoordinates
		.map((p) => `${p.x},${p.y}`)
		.join(" ");

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
				gap: "22px",
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
						Risk assessment
					</h2>
					<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
						How the evidence changed Tark’s assessment
					</p>
				</div>

				<div>
					<span
						style={{
							fontSize: "11px",
							fontWeight: 700,
							padding: "3px 8px",
							borderRadius: "4px",
							backgroundColor: currentRisk.bg,
							color: currentRisk.text,
							border: `1px solid ${currentRisk.border}`,
							letterSpacing: "0.04em",
						}}
					>
						{currentRisk.label}
					</span>
				</div>
			</div>

			{/* PART 1 — ASSESSMENT SUMMARY (Horizontal Comparison) */}
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
					gap: "16px",
					padding: "14px 18px",
					backgroundColor: "#f8fafc",
					borderRadius: "6px",
					border: "1px solid #eef2f6",
				}}
			>
				{/* Initial Assessment */}
				<div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
					<div
						style={{
							fontSize: "11px",
							fontWeight: 600,
							color: "#64748b",
							textTransform: "uppercase",
							letterSpacing: "0.03em",
						}}
					>
						Initial assessment
					</div>
					<div style={{ display: "flex", alignItems: "baseline", gap: "10px" }}>
						<span
							style={{
								fontSize: "26px",
								fontWeight: 800,
								color: "#0f172a",
								letterSpacing: "-0.02em",
							}}
						>
							{initialPercent}%
						</span>
						<span
							style={{
								fontSize: "10.5px",
								fontWeight: 600,
								padding: "2px 6px",
								borderRadius: "4px",
								backgroundColor: initialRisk.bg,
								color: initialRisk.text,
								border: `1px solid ${initialRisk.border}`,
							}}
						>
							{initialRisk.label}
						</span>
					</div>
					<div style={{ fontSize: "12px", color: "#64748b" }}>
						Pre-investigation alert prior
					</div>
				</div>

				{/* Current Assessment */}
				<div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
					<div
						style={{
							fontSize: "11px",
							fontWeight: 600,
							color: "#64748b",
							textTransform: "uppercase",
							letterSpacing: "0.03em",
						}}
					>
						Current assessment
					</div>
					<div style={{ display: "flex", alignItems: "baseline", gap: "10px" }}>
						<span
							style={{
								fontSize: "26px",
								fontWeight: 800,
								color: "#ea580c",
								letterSpacing: "-0.02em",
							}}
						>
							{finalPercent}%
						</span>
						<span
							style={{
								fontSize: "10.5px",
								fontWeight: 600,
								padding: "2px 6px",
								borderRadius: "4px",
								backgroundColor: currentRisk.bg,
								color: currentRisk.text,
								border: `1px solid ${currentRisk.border}`,
							}}
						>
							{currentRisk.label}
						</span>
					</div>
					<div
						style={{
							fontSize: "12px",
							color: delta > 0 ? "#c2410c" : "#15803d",
							fontWeight: 500,
						}}
					>
						{delta !== 0
							? `${deltaSign}${delta.toFixed(1)}% change from evidence`
							: "Consistent with prior alert"}
					</div>
				</div>
			</div>

			{/* TECHNICAL VIEW — View calculation (Bayesian Derivation) */}
			<div>
				<TechnicalDetails
					title="View calculation & Bayesian log-odds derivation"
					summaryItems={[
						{
							label: "Prior Probability",
							value: `${initialPercent}% (Prior odds O₀ = ${priorOdds.toFixed(2)})`,
						},
						{
							label: "Posterior Probability",
							value: `${finalPercent}% (Posterior odds O = ${posteriorOdds.toFixed(2)})`,
						},
						{
							label: "Bayesian Equation",
							value: "ln(O_posterior) = ln(O_prior) + Σ ln(LR_i)",
						},
						{
							label: "Evidence Impact",
							value: `${delta > 0 ? "Strongly increased fraud risk" : delta < 0 ? "Decreased fraud risk" : "Assessment consistent with prior"} (${deltaSign}${delta.toFixed(1)}%)`,
						},
						{
							label: "Empirical Likelihood Ratios",
							value: lrItems.length > 0 ? lrItems.join(" · ") : "No steps executed; baseline prior applies.",
						},
					]}
				/>
			</div>

			{/* PART 2 — BELIEF TRAJECTORY (SVG Line Chart) */}
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
					Belief trajectory
				</div>

				{traces.length === 0 ? (
					<div
						style={{
							padding: "24px",
							textAlign: "center",
							backgroundColor: "#f8fafc",
							border: "1px solid #e2e8f0",
							borderRadius: "6px",
							color: "#64748b",
							fontSize: "13px",
						}}
					>
						Belief trajectory unavailable for this investigation.
					</div>
				) : (
					<div
						style={{
							backgroundColor: "#ffffff",
							border: "1px solid #e2e8f0",
							borderRadius: "6px",
							padding: "16px 12px 10px 12px",
							overflowX: "auto",
						}}
					>
						<svg
							viewBox={`0 0 ${chartWidth} ${chartHeight}`}
							style={{
								width: "100%",
								height: "auto",
								display: "block",
								maxHeight: "200px",
							}}
						>
							{/* Y-Axis Grid Lines & Labels */}
							{[1.0, 0.75, 0.5, 0.25, 0.0].map((level) => {
								const y = padTop + (1 - level) * innerHeight;
								return (
									<g key={level}>
										<line
											x1={padLeft}
											y1={y}
											x2={chartWidth - padRight}
											y2={y}
											stroke="#f1f5f9"
											strokeWidth="1"
										/>
										<text
											x={padLeft - 8}
											y={y + 3}
											textAnchor="end"
											fontSize="10"
											fill="#94a3b8"
											fontFamily="ui-monospace, monospace"
										>
											{Math.round(level * 100)}%
										</text>
									</g>
								);
							})}

							{/* Trajectory Polyline */}
							<polyline
								fill="none"
								stroke="#ea580c"
								strokeWidth="2.5"
								strokeLinecap="round"
								strokeLinejoin="round"
								points={polylinePoints}
							/>

							{/* Data Points */}
							{pointsCoordinates.map((pt) => {
								const isHovered = hoveredIndex === pt.index;
								return (
									<g
										key={pt.index}
										onMouseEnter={() => setHoveredIndex(pt.index)}
										onMouseLeave={() => setHoveredIndex(null)}
										style={{ cursor: "pointer" }}
									>
										{/* Outer hover ring */}
										<circle
											cx={pt.x}
											cy={pt.y}
											r={isHovered ? 6 : 4}
											fill={isHovered ? "#ea580c" : "#ffffff"}
											stroke="#ea580c"
											strokeWidth="2.5"
										/>

										{/* Probability value tooltip badge */}
										<g transform={`translate(${pt.x}, ${pt.y - 12})`}>
											<rect
												x="-20"
												y="-12"
												width="40"
												height="14"
												rx="3"
												fill="#0f172a"
												opacity={isHovered ? 1 : 0.85}
											/>
											<text
												x="0"
												y="-2"
												textAnchor="middle"
												fontSize="9"
												fontWeight="700"
												fill="#ffffff"
												fontFamily="ui-monospace, monospace"
											>
												{(pt.prob * 100).toFixed(0)}%
											</text>
										</g>

										{/* X-Axis Step Label */}
										<text
											x={pt.x}
											y={chartHeight - 12}
											textAnchor="middle"
											fontSize="10"
											fontWeight={isHovered ? 700 : 500}
											fill={isHovered ? "#0f172a" : "#64748b"}
										>
											{pt.subName}
										</text>
									</g>
								);
							})}
						</svg>
					</div>
				)}
			</div>

			{/* PART 3 — WHAT CHANGED THE ASSESSMENT */}
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
					What changed the assessment
				</div>

				<div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
					{traces.map((trace, idx) => {
						const rawTool = trace.selected_action;
						const toolInfo = TOOL_DISPLAY_NAMES[rawTool] || {
							title: rawTool.replace(/_/g, " ").toLowerCase(),
							checked: "",
							why: "",
						};
						const probBefore = extractFraudProb(trace.belief_before);
						const probAfter = extractFraudProb(trace.belief_after);
						const diff = probAfter - probBefore;
						const cleanFinding = cleanFindingText(
							trace.observed_evidence_summary || "",
						);
						const isExpanded = !!expandedDetails[`trace-${idx}`];

						let impactText = "Assessment unchanged";
						let impactBg = "#f1f5f9";
						let impactColor = "#475569";
						let impactBorder = "#e2e8f0";

						if (diff > 0.05) {
							impactText = `Strongly increased fraud probability (+${(diff * 100).toFixed(1)}%)`;
							impactBg = "#fff7ed";
							impactColor = "#ea580c";
							impactBorder = "#ffedd5";
						} else if (diff < -0.05) {
							impactText = `Decreased fraud probability (${(diff * 100).toFixed(1)}%)`;
							impactBg = "#f0fdf4";
							impactColor = "#15803d";
							impactBorder = "#bbf7d0";
						} else if (
							trace.observed_evidence_summary?.includes("UNAVAILABLE") ||
							rawTool.includes("CUSTOMER")
						) {
							impactText = "Cardholder response unavailable";
							impactBg = "#f8fafc";
							impactColor = "#64748b";
							impactBorder = "#e2e8f0";
						} else {
							impactText = "No material change";
							impactBg = "#f8fafc";
							impactColor = "#475569";
							impactBorder = "#e2e8f0";
						}

						return (
							<div
								key={idx}
								style={{
									backgroundColor: "#ffffff",
									border: "1px solid #e2e8f0",
									borderRadius: "6px",
									padding: "12px 16px",
									display: "flex",
									flexDirection: "column",
									gap: "6px",
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
										<span
											style={{
												fontSize: "13px",
												fontWeight: 700,
												color: "#0f172a",
											}}
										>
											{toolInfo.title}
										</span>
										<p
											style={{
												margin: "2px 0 0 0",
												fontSize: "12px",
												color: "#334155",
												lineHeight: "1.4",
											}}
										>
											{cleanFinding || "No evidence findings recorded."}
										</p>
									</div>

									<span
										style={{
											fontSize: "11px",
											fontWeight: 600,
											padding: "2px 7px",
											borderRadius: "4px",
											backgroundColor: impactBg,
											color: impactColor,
											border: `1px solid ${impactBorder}`,
											whiteSpace: "nowrap",
										}}
									>
										{impactText}
									</span>
								</div>

								{/* Collapsible Technical Details */}
								<div style={{ paddingTop: "2px" }}>
									<button
										onClick={() => toggleDetail(`trace-${idx}`)}
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
										{isExpanded
											? "Hide technical details"
											: "View technical details"}
									</button>

									{isExpanded && (
										<div
											style={{
												marginTop: "6px",
												padding: "8px 10px",
												backgroundColor: "#f8fafc",
												border: "1px solid #e2e8f0",
												borderRadius: "4px",
												fontSize: "10px",
												fontFamily: "ui-monospace, monospace",
												color: "#334155",
												display: "flex",
												flexDirection: "column",
												gap: "4px",
											}}
										>
											<div>
												<strong>Action:</strong> {rawTool}
											</div>
											<div>
												<strong>Belief Before:</strong>{" "}
												{(probBefore * 100).toFixed(2)}% ·{" "}
												<strong>Belief After:</strong>{" "}
												{(probAfter * 100).toFixed(2)}%
											</div>
											<div>
												<strong>Raw Finding:</strong>{" "}
												{trace.observed_evidence_summary}
											</div>
										</div>
									)}
								</div>
							</div>
						);
					})}
				</div>
			</div>
		</div>
	);
};
