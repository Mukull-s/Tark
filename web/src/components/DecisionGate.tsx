import type React from "react";
import { useState } from "react";
import type { InvestigationResultPayload } from "../api/types";

interface DecisionGateProps {
	result: InvestigationResultPayload;
}

export const DecisionGate: React.FC<DecisionGateProps> = ({ result }) => {
	const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

	const finalState = result.run_result?.final_state;
	const primaryAction = result.run_result?.primary_action;
	const terminationReason = result.run_result?.termination_reason;
	const exposureUsd = result.exposure_usd;

	const fraudProb = finalState?.fraud_probability ?? 0.5;
	const coverage = finalState?.evidence_coverage;
	const epistemicUncertainty = finalState?.epistemic_uncertainty;
	const aleatoricUncertainty = finalState?.aleatoric_uncertainty ?? 0.0;
	const gatePassed = finalState?.decision_gate_passed ?? false;
	const decisionState = finalState?.decision_state ?? "PENDING";
	const approvalRoute = primaryAction?.approval_route;

	// Determine Canonical Gate Status
	let gateStatusBadge = "UNKNOWN";
	let gateStatusSubtext = "";
	let gateBadgeBg = "#f8fafc";
	let gateBadgeText = "#475569";
	let gateBadgeBorder = "#e2e8f0";

	if (
		decisionState === "INSUFFICIENT_EVIDENCE" ||
		(!gatePassed && decisionState !== "REQUIRES_HUMAN_APPROVAL")
	) {
		gateStatusBadge = "INSUFFICIENT EVIDENCE";
		gateStatusSubtext = "Automated decision blocked due to incomplete evidence";
		gateBadgeBg = "#f8fafc";
		gateBadgeText = "#475569";
		gateBadgeBorder = "#cbd5e1";
	} else if (
		decisionState === "REQUIRES_HUMAN_APPROVAL" ||
		(gatePassed && approvalRoute && approvalRoute !== "auto")
	) {
		gateStatusBadge = "HUMAN APPROVAL REQUIRED";
		gateStatusSubtext = approvalRoute
			? `Policy requires ${approvalRoute.toUpperCase()} sign-off`
			: "Policy requires analyst sign-off";
		gateBadgeBg = "#fffbeb";
		gateBadgeText = "#b45309";
		gateBadgeBorder = "#fde68a";
	} else if (gatePassed && (approvalRoute === "auto" || !approvalRoute)) {
		gateStatusBadge = "AUTOMATIC ACTION ALLOWED";
		gateStatusSubtext = "Autonomous execution permitted by policy";
		gateBadgeBg = "#f0fdf4";
		gateBadgeText = "#15803d";
		gateBadgeBorder = "#bbf7d0";
	} else {
		gateStatusBadge = decisionState.replace(/_/g, " ");
		gateStatusSubtext = "Investigation evaluation completed";
		gateBadgeBg = "#f8fafc";
		gateBadgeText = "#475569";
		gateBadgeBorder = "#e2e8f0";
	}

	// Why this gate checklist items (strictly derived from backend fields)
	const isCoverageSufficient =
		coverage !== undefined ? coverage >= 0.4 || gatePassed : gatePassed;
	const isRiskDeterminate = fraudProb >= 0.7 || fraudProb <= 0.3;
	const isConflictLow = aleatoricUncertainty < 0.4;
	const isAutoPermitted = approvalRoute === "auto";

	return (
		<div
			style={{
				backgroundColor: "#ffffff",
				borderRadius: "8px",
				border: "1px solid #e2e8f0",
				padding: "18px 20px",
				boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
				display: "flex",
				flexDirection: "column",
				gap: "16px",
			}}
		>
			{/* 1. Header */}
			<div>
				<h2
					style={{
						fontSize: "15px",
						fontWeight: 700,
						color: "#0f172a",
						margin: "0 0 2px 0",
						letterSpacing: "-0.01em",
					}}
				>
					Decision gate
				</h2>
				<p style={{ margin: 0, color: "#64748b", fontSize: "12px" }}>
					Can Tark act on this case?
				</p>
			</div>

			{/* 2. Gate Status Card */}
			<div
				style={{
					padding: "12px 14px",
					backgroundColor: gateBadgeBg,
					border: `1px solid ${gateBadgeBorder}`,
					borderRadius: "6px",
					display: "flex",
					flexDirection: "column",
					gap: "4px",
					textAlign: "center",
				}}
			>
				<div
					style={{
						fontSize: "12.5px",
						fontWeight: 800,
						color: gateBadgeText,
						letterSpacing: "0.04em",
					}}
				>
					[ {gateStatusBadge} ]
				</div>
				<div style={{ fontSize: "11px", color: "#64748b" }}>
					{gateStatusSubtext}
				</div>
			</div>

			{/* Primary 3-Metric Summary Strip */}
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "1fr 1fr 1fr",
					gap: "6px",
					padding: "8px",
					backgroundColor: "#f8fafc",
					borderRadius: "6px",
					border: "1px solid #eef2f6",
					textAlign: "center",
				}}
			>
				<div>
					<div
						style={{
							color: "#64748b",
							fontSize: "9.5px",
							textTransform: "uppercase",
							fontWeight: 600,
						}}
					>
						Coverage
					</div>
					<div
						style={{
							fontSize: "13px",
							fontWeight: 700,
							color: "#0f172a",
							marginTop: "2px",
						}}
					>
						{coverage !== undefined ? `${(coverage * 100).toFixed(0)}%` : "—"}
					</div>
				</div>
				<div>
					<div
						style={{
							color: "#64748b",
							fontSize: "9.5px",
							textTransform: "uppercase",
							fontWeight: 600,
						}}
					>
						Uncertainty
					</div>
					<div
						style={{
							fontSize: "13px",
							fontWeight: 700,
							color: "#0f172a",
							marginTop: "2px",
						}}
					>
						{epistemicUncertainty !== undefined && epistemicUncertainty <= 0.25
							? "Low"
							: epistemicUncertainty !== undefined && epistemicUncertainty <= 0.4
								? "Moderate"
								: "Elevated"}
					</div>
				</div>
				<div>
					<div
						style={{
							color: "#64748b",
							fontSize: "9.5px",
							textTransform: "uppercase",
							fontWeight: 600,
						}}
					>
						Assessment
					</div>
					<div
						style={{
							fontSize: "13px",
							fontWeight: 700,
							color:
								fraudProb >= 0.7
									? "#ea580c"
									: fraudProb <= 0.3
										? "#15803d"
										: "#ca8a04",
							marginTop: "2px",
						}}
					>
						{fraudProb >= 0.7
							? "High Risk"
							: fraudProb <= 0.3
								? "Low Risk"
								: "Moderate"}
					</div>
				</div>
			</div>

			{/* 3. Why this gate? */}
			<div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
				<div
					style={{
						fontSize: "11px",
						fontWeight: 700,
						color: "#475569",
						textTransform: "uppercase",
						letterSpacing: "0.04em",
					}}
				>
					Why this gate?
				</div>

				<div
					style={{
						display: "flex",
						flexDirection: "column",
						gap: "6px",
						fontSize: "12px",
					}}
				>
					{/* Evidence Coverage Check */}
					<div
						style={{
							display: "flex",
							alignItems: "flex-start",
							justifyContent: "space-between",
							gap: "8px",
						}}
					>
						<span style={{ color: "#334155" }}>
							{isCoverageSufficient
								? "Evidence sufficient"
								: "Evidence below threshold"}
							{coverage !== undefined && (
								<span
									style={{
										color: "#64748b",
										fontSize: "11px",
										marginLeft: "4px",
									}}
								>
									({(coverage * 100).toFixed(0)}%)
								</span>
							)}
						</span>
						<span
							style={{
								fontWeight: 700,
								color: isCoverageSufficient ? "#16a34a" : "#d97706",
							}}
						>
							{isCoverageSufficient ? "✓" : "⚠"}
						</span>
					</div>

					{/* Risk Certainty Check */}
					<div
						style={{
							display: "flex",
							alignItems: "flex-start",
							justifyContent: "space-between",
							gap: "8px",
						}}
					>
						<span style={{ color: "#334155" }}>
							{isRiskDeterminate
								? "Risk assessment conclusive"
								: "Intermediate uncertainty band"}
							<span
								style={{
									color: "#64748b",
									fontSize: "11px",
									marginLeft: "4px",
								}}
							>
								({(fraudProb * 100).toFixed(1)}%)
							</span>
						</span>
						<span
							style={{
								fontWeight: 700,
								color: isRiskDeterminate ? "#16a34a" : "#d97706",
							}}
						>
							{isRiskDeterminate ? "✓" : "⚠"}
						</span>
					</div>

					{/* Evidentiary Conflict Check */}
					<div
						style={{
							display: "flex",
							alignItems: "flex-start",
							justifyContent: "space-between",
							gap: "8px",
						}}
					>
						<span style={{ color: "#334155" }}>
							{isConflictLow
								? "No evidentiary contradiction"
								: "Severe evidence conflict"}
						</span>
						<span
							style={{
								fontWeight: 700,
								color: isConflictLow ? "#16a34a" : "#dc2626",
							}}
						>
							{isConflictLow ? "✓" : "⚠"}
						</span>
					</div>

					{/* Action Approval Requirement */}
					{approvalRoute && (
						<div
							style={{
								display: "flex",
								alignItems: "flex-start",
								justifyContent: "space-between",
								gap: "8px",
							}}
						>
							<span style={{ color: "#334155" }}>
								{isAutoPermitted
									? "Automatic action permitted"
									: `Action requires ${approvalRoute.toUpperCase()} approval`}
							</span>
							<span
								style={{
									fontWeight: 700,
									color: isAutoPermitted ? "#16a34a" : "#d97706",
								}}
							>
								{isAutoPermitted ? "✓" : "⚠"}
							</span>
						</div>
					)}
				</div>
			</div>

			<div style={{ height: "1px", backgroundColor: "#eef2f6" }} />

			{/* 4. Decision Context */}
			<div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
				<div
					style={{
						fontSize: "11px",
						fontWeight: 700,
						color: "#475569",
						textTransform: "uppercase",
						letterSpacing: "0.04em",
					}}
				>
					Decision context
				</div>

				<div
					style={{
						display: "grid",
						gridTemplateColumns: "1fr 1fr",
						gap: "8px",
						padding: "10px 12px",
						backgroundColor: "#f8fafc",
						borderRadius: "6px",
						border: "1px solid #eef2f6",
						fontSize: "12px",
					}}
				>
					<div>
						<div
							style={{
								color: "#64748b",
								fontSize: "10px",
								textTransform: "uppercase",
							}}
						>
							Fraud assessment
						</div>
						<div
							style={{ fontWeight: 700, color: "#0f172a", fontSize: "13.5px" }}
						>
							{(fraudProb * 100).toFixed(1)}%
						</div>
					</div>

					{coverage !== undefined && (
						<div>
							<div
								style={{
									color: "#64748b",
									fontSize: "10px",
									textTransform: "uppercase",
								}}
							>
								Evidence coverage
							</div>
							<div
								style={{
									fontWeight: 700,
									color: "#0f172a",
									fontSize: "13.5px",
								}}
							>
								{(coverage * 100).toFixed(0)}%
							</div>
						</div>
					)}

					{exposureUsd !== undefined && (
						<div>
							<div
								style={{
									color: "#64748b",
									fontSize: "10px",
									textTransform: "uppercase",
								}}
							>
								Exposure
							</div>
							<div style={{ fontWeight: 600, color: "#334155" }}>
								${exposureUsd.toFixed(2)}
							</div>
						</div>
					)}

					<div>
						<div
							style={{
								color: "#64748b",
								fontSize: "10px",
								textTransform: "uppercase",
							}}
						>
							Decision state
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
			</div>

			{/* 5. Constraints */}
			<div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
				<div
					style={{
						fontSize: "11px",
						fontWeight: 700,
						color: "#475569",
						textTransform: "uppercase",
						letterSpacing: "0.04em",
					}}
				>
					Constraints & Governance
				</div>

				<div
					style={{
						display: "flex",
						flexDirection: "column",
						gap: "4px",
						fontSize: "11px",
						color: "#475569",
					}}
				>
					{approvalRoute && (
						<div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
							<span
								style={{
									width: "4px",
									height: "4px",
									borderRadius: "50%",
									backgroundColor: "#ea580c",
								}}
							/>
							<span>
								Approval route: <strong>{approvalRoute}</strong>
							</span>
						</div>
					)}
					{primaryAction?.scope && (
						<div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
							<span
								style={{
									width: "4px",
									height: "4px",
									borderRadius: "50%",
									backgroundColor: "#ea580c",
								}}
							/>
							<span>
								Scope: <strong>{primaryAction.scope}</strong>
							</span>
						</div>
					)}
					{terminationReason && (
						<div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
							<span
								style={{
									width: "4px",
									height: "4px",
									borderRadius: "50%",
									backgroundColor: "#ea580c",
								}}
							/>
							<span>
								Termination: <strong>{terminationReason}</strong>
							</span>
						</div>
					)}
				</div>

				{/* Collapsible Technical Details */}
				<div style={{ paddingTop: "2px" }}>
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
								wordBreak: "break-all",
							}}
						>
							<div>
								<strong>decision_gate_passed:</strong> {String(gatePassed)}
							</div>
							<div>
								<strong>decision_state:</strong> {decisionState}
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
								<strong>termination_reason:</strong>{" "}
								{terminationReason || "N/A"}
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
};
