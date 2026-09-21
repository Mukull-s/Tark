import type React from "react";
import { useState } from "react";
import type { InvestigationResultPayload } from "../api/types";
import { cleanReasonText, formatActionName } from "./NextBestAction";

interface InvestigationConclusionProps {
	result: InvestigationResultPayload;
}

export const InvestigationConclusion: React.FC<
	InvestigationConclusionProps
> = ({ result }) => {
	const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

	const finalState = result.run_result?.final_state;
	const primaryAction = result.run_result?.primary_action;
	const terminationReason = result.run_result?.termination_reason;

	const fraudProb = finalState?.fraud_probability ?? 0.5;
	const coverage = finalState?.evidence_coverage;
	const epistemicUncertainty = finalState?.epistemic_uncertainty;
	const aleatoricUncertainty = finalState?.aleatoric_uncertainty ?? 0.0;
	const gatePassed = finalState?.decision_gate_passed ?? false;
	const decisionState = finalState?.decision_state ?? "PENDING";
	const approvalRoute = primaryAction?.approval_route;

	const isInsufficientEvidence =
		decisionState === "INSUFFICIENT_EVIDENCE" ||
		(!gatePassed && decisionState !== "REQUIRES_HUMAN_APPROVAL");

	// Determine Risk Assessment Heading & Banner Styles
	let assessmentHeading = "INTERMEDIATE RISK";
	let bannerBg = "#f8fafc";
	let bannerBorder = "#e2e8f0";
	let bannerTextColor = "#475569";
	let summarySentence =
		"Tark’s investigation completed with an intermediate risk assessment.";

	if (isInsufficientEvidence) {
		assessmentHeading = "INVESTIGATION INCONCLUSIVE";
		bannerBg = "#f8fafc";
		bannerBorder = "#cbd5e1";
		bannerTextColor = "#475569";
		summarySentence =
			"Tark’s investigation found insufficient evidence to support an automated policy determination.";
	} else if (fraudProb >= 0.7) {
		assessmentHeading = "HIGH FRAUD RISK";
		bannerBg = "#fff7ed";
		bannerBorder = "#ffedd5";
		bannerTextColor = "#c2410c";
		summarySentence =
			"Tark’s investigation found sufficient evidence to support the current fraud-risk assessment.";
	} else if (fraudProb <= 0.3) {
		assessmentHeading = "LOW FRAUD RISK";
		bannerBg = "#f0fdf4";
		bannerBorder = "#bbf7d0";
		bannerTextColor = "#15803d";
		summarySentence =
			"Tark’s investigation found exculpatory evidence supporting a legitimate transaction assessment.";
	}

	const reasonText = primaryAction?.reason
		? cleanReasonText(primaryAction.reason)
		: "";
	const isAuto = approvalRoute === "auto";

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
			{/* 1. Header & Top Summary Row */}
			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "flex-start",
					flexWrap: "wrap",
					gap: "16px",
				}}
			>
				<div style={{ flex: "1", minWidth: "280px" }}>
					<div
						style={{
							fontSize: "11px",
							fontWeight: 700,
							color: "#64748b",
							textTransform: "uppercase",
							letterSpacing: "0.04em",
							marginBottom: "4px",
						}}
					>
						Investigation Conclusion
					</div>
					<div
						style={{
							fontSize: "22px",
							fontWeight: 800,
							color: bannerTextColor,
							letterSpacing: "-0.02em",
						}}
					>
						{assessmentHeading}
					</div>
					<p
						style={{
							margin: "6px 0 0 0",
							color: "#475569",
							fontSize: "13.5px",
							lineHeight: "1.45",
							maxWidth: "640px",
						}}
					>
						{summarySentence}
					</p>
				</div>

				{/* Fraud Assessment Percentage */}
				<div
					style={{
						display: "flex",
						flexDirection: "column",
						alignItems: "flex-end",
						padding: "10px 16px",
						backgroundColor: bannerBg,
						border: `1px solid ${bannerBorder}`,
						borderRadius: "6px",
					}}
				>
					<div
						style={{
							fontSize: "11px",
							fontWeight: 600,
							color: "#64748b",
							textTransform: "uppercase",
							letterSpacing: "0.03em",
						}}
					>
						Fraud assessment
					</div>
					<div
						style={{
							fontSize: "28px",
							fontWeight: 800,
							color: bannerTextColor,
							letterSpacing: "-0.02em",
							lineHeight: "1.1",
						}}
					>
						{(fraudProb * 100).toFixed(1)}%
					</div>
				</div>
			</div>

			<div style={{ height: "1px", backgroundColor: "#eef2f6" }} />

			{/* 2. Key Operational Findings Summary Strip */}
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
					gap: "14px",
					padding: "12px 16px",
					backgroundColor: "#f8fafc",
					borderRadius: "6px",
					border: "1px solid #eef2f6",
					fontSize: "13px",
				}}
			>
				{/* Recommended Action */}
				<div>
					<div
						style={{
							color: "#64748b",
							fontSize: "11px",
							fontWeight: 600,
							textTransform: "uppercase",
							marginBottom: "3px",
						}}
					>
						Recommended Action
					</div>
					<div style={{ fontWeight: 700, color: "#0f172a", fontSize: "14px" }}>
						{isInsufficientEvidence || !primaryAction
							? "No action recommended"
							: formatActionName(primaryAction.action)}
					</div>
				</div>

				{/* Approval Route */}
				<div>
					<div
						style={{
							color: "#64748b",
							fontSize: "11px",
							fontWeight: 600,
							textTransform: "uppercase",
							marginBottom: "3px",
						}}
					>
						Approval Status
					</div>
					<div style={{ fontWeight: 600, color: "#1e293b" }}>
						{approvalRoute ? (
							<span
								style={{
									fontSize: "11px",
									fontWeight: 700,
									padding: "2px 8px",
									borderRadius: "4px",
									backgroundColor: isAuto ? "#f0fdf4" : "#fffbeb",
									color: isAuto ? "#15803d" : "#b45309",
									border: `1px solid ${isAuto ? "#bbf7d0" : "#fde68a"}`,
								}}
							>
								{isAuto
									? "AUTOMATIC ACTION ALLOWED"
									: `${approvalRoute.toUpperCase()} APPROVAL REQUIRED`}
							</span>
						) : (
							"—"
						)}
					</div>
				</div>

				{/* Evidence Coverage */}
				{coverage !== undefined && (
					<div>
						<div
							style={{
								color: "#64748b",
								fontSize: "11px",
								fontWeight: 600,
								textTransform: "uppercase",
								marginBottom: "3px",
							}}
						>
							Evidence Coverage
						</div>
						<div style={{ fontWeight: 700, color: "#0f172a" }}>
							{(coverage * 100).toFixed(0)}% observed
						</div>
					</div>
				)}

				{/* Investigation State */}
				<div>
					<div
						style={{
							color: "#64748b",
							fontSize: "11px",
							fontWeight: 600,
							textTransform: "uppercase",
							marginBottom: "3px",
						}}
					>
						Decision State
					</div>
					<div
						style={{
							fontWeight: 600,
							color: "#334155",
							textTransform: "capitalize",
						}}
					>
						{decisionState.toLowerCase().replace(/_/g, " ")}
					</div>
				</div>
			</div>

			{/* 3. Policy Rationale Statement */}
			{reasonText && !isInsufficientEvidence && (
				<div style={{ fontSize: "13px", color: "#334155", lineHeight: "1.5" }}>
					<span style={{ fontWeight: 600, color: "#0f172a" }}>Why: </span>
					<span>{reasonText}</span>
				</div>
			)}

			{/* 4. Collapsible Technical Details */}
			<div>
				<button
					onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
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
					{showTechnicalDetails
						? "Hide technical details"
						: "View technical details"}
				</button>

				{showTechnicalDetails && (
					<div
						style={{
							marginTop: "8px",
							padding: "10px 12px",
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
							<strong>decision_state:</strong> {decisionState}
						</div>
						<div>
							<strong>decision_gate_passed:</strong> {String(gatePassed)}
						</div>
						<div>
							<strong>classification:</strong>{" "}
							{finalState?.classification || "N/A"}
						</div>
						<div>
							<strong>epistemic_uncertainty:</strong>{" "}
							{epistemicUncertainty ?? "N/A"}
						</div>
						<div>
							<strong>aleatoric_uncertainty:</strong> {aleatoricUncertainty}
						</div>
						<div>
							<strong>termination_reason:</strong> {terminationReason || "N/A"}
						</div>
					</div>
				)}
			</div>
		</div>
	);
};
