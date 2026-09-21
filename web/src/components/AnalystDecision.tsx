import type React from "react";
import { useState } from "react";
import { submitAnalystDecision } from "../api/client";
import type { InvestigationResultPayload } from "../api/types";
import { formatActionName } from "./NextBestAction";

interface AnalystDecisionProps {
	result: InvestigationResultPayload;
	onDecisionSubmitted?: (updatedResult: InvestigationResultPayload) => void;
}

export const AnalystDecision: React.FC<AnalystDecisionProps> = ({
	result,
	onDecisionSubmitted,
}) => {
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [showOverrideForm, setShowOverrideForm] = useState(false);
	const [overrideRationale, setOverrideRationale] = useState("");
	const [localRecordedDecision, setLocalRecordedDecision] = useState<{
		decision: "APPROVE" | "REJECT";
		analystId: string;
		rationale?: string;
		timestamp: string;
	} | null>(null);

	const finalState = result.run_result?.final_state;
	const primaryAction = result.run_result?.primary_action;
	const decisionState = finalState?.decision_state ?? "PENDING";
	const gatePassed = finalState?.decision_gate_passed ?? false;
	const isInsufficientEvidence =
		decisionState === "INSUFFICIENT_EVIDENCE" ||
		(!gatePassed && decisionState !== "REQUIRES_HUMAN_APPROVAL");

	const approvalRoute = primaryAction?.approval_route;
	const isAuto = approvalRoute === "auto";
	const actionName = primaryAction?.action
		? formatActionName(primaryAction.action)
		: "NO ACTION";

	// Check if case was already closed/rejected in backend events
	const existingApproveEvent = (result.events || []).find(
		(e) => e.type === "ACTION_APPROVED",
	);
	const existingRejectEvent = (e: any) => e.type === "ACTION_REJECTED";
	const existingReject = (result.events || []).find(existingRejectEvent);

	const recorded =
		localRecordedDecision ||
		(existingApproveEvent
			? {
					decision: "APPROVE" as const,
					analystId: existingApproveEvent.details?.analyst_id || "ANALYST_01",
					rationale:
						existingApproveEvent.details?.rationale ||
						"Policy criteria validated.",
					timestamp: existingApproveEvent.timestamp,
				}
			: existingReject
				? {
						decision: "REJECT" as const,
						analystId: existingReject.details?.analyst_id || "ANALYST_01",
						rationale: existingReject.details?.rationale || "Analyst override.",
						timestamp: existingReject.timestamp,
					}
				: null);

	const handleApprove = async () => {
		setIsSubmitting(true);
		setError(null);
		try {
			const response = await submitAnalystDecision(result.investigation_id, {
				decision: "APPROVE",
				analyst_id: "ANALYST_01",
				rationale: "Policy criteria and evidence verified by risk analyst.",
			});

			setLocalRecordedDecision({
				decision: "APPROVE",
				analystId: "ANALYST_01",
				rationale: "Policy criteria and evidence verified by risk analyst.",
				timestamp: new Date().toISOString(),
			});

			if (onDecisionSubmitted && response.result) {
				onDecisionSubmitted(response.result);
			}
		} catch (err: any) {
			setError(err?.message || "Failed to record decision. Please try again.");
		} finally {
			setIsSubmitting(false);
		}
	};

	const handleConfirmOverride = async () => {
		if (!overrideRationale.trim()) {
			setError("Please provide an override rationale before confirming.");
			return;
		}

		setIsSubmitting(true);
		setError(null);
		try {
			const response = await submitAnalystDecision(result.investigation_id, {
				decision: "REJECT",
				analyst_id: "ANALYST_01",
				rationale: overrideRationale.trim(),
			});

			setLocalRecordedDecision({
				decision: "REJECT",
				analystId: "ANALYST_01",
				rationale: overrideRationale.trim(),
				timestamp: new Date().toISOString(),
			});
			setShowOverrideForm(false);

			if (onDecisionSubmitted && response.result) {
				onDecisionSubmitted(response.result);
			}
		} catch (err: any) {
			setError(err?.message || "Failed to record override. Please try again.");
		} finally {
			setIsSubmitting(false);
		}
	};

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
				gap: "14px",
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
					Your decision
				</h2>
				<p style={{ margin: 0, color: "#64748b", fontSize: "12px" }}>
					Human-in-the-loop analyst governance
				</p>
			</div>

			{/* Error Alert */}
			{error && (
				<div
					style={{
						padding: "8px 12px",
						backgroundColor: "#fef2f2",
						border: "1px solid #fecaca",
						borderRadius: "4px",
						color: "#b91c1c",
						fontSize: "12px",
						lineHeight: "1.4",
					}}
				>
					{error}
				</div>
			)}

			{/* 2. State A: Insufficient Evidence Case */}
			{isInsufficientEvidence ? (
				<div
					style={{
						padding: "14px",
						backgroundColor: "#f8fafc",
						border: "1px solid #e2e8f0",
						borderRadius: "6px",
						textAlign: "center",
						display: "flex",
						flexDirection: "column",
						gap: "4px",
					}}
				>
					<div
						style={{
							fontSize: "12px",
							fontWeight: 700,
							color: "#475569",
							letterSpacing: "0.03em",
						}}
					>
						[ FURTHER INVESTIGATION REQUIRED ]
					</div>
					<div style={{ fontSize: "11px", color: "#64748b" }}>
						No actionable policy recommendation reached. Human sign-off is
						unavailable until evidence criteria are met.
					</div>
				</div>
			) : isAuto ? (
				/* 3. State B: Automatic Action Allowed Case */
				<div
					style={{
						padding: "12px 14px",
						backgroundColor: "#f0fdf4",
						border: "1px solid #bbf7d0",
						borderRadius: "6px",
						display: "flex",
						flexDirection: "column",
						gap: "4px",
					}}
				>
					<div
						style={{
							fontSize: "12px",
							fontWeight: 700,
							color: "#15803d",
							letterSpacing: "0.03em",
						}}
					>
						[ AUTOMATIC ACTION ALLOWED ]
					</div>
					<div style={{ fontSize: "12px", color: "#1e293b" }}>
						Tark recommended: <strong>{actionName}</strong>
					</div>
					<div style={{ fontSize: "11px", color: "#15803d" }}>
						Policy permits autonomous execution without prior analyst sign-off.
					</div>
				</div>
			) : recorded ? (
				/* 4. State C: Decision Already Recorded */
				<div
					style={{
						padding: "12px 14px",
						backgroundColor:
							recorded.decision === "APPROVE" ? "#f0fdf4" : "#fffbeb",
						border: `1px solid ${recorded.decision === "APPROVE" ? "#bbf7d0" : "#fde68a"}`,
						borderRadius: "6px",
						display: "flex",
						flexDirection: "column",
						gap: "8px",
					}}
				>
					<div>
						<span
							style={{
								fontSize: "11px",
								fontWeight: 700,
								padding: "2px 8px",
								borderRadius: "4px",
								backgroundColor:
									recorded.decision === "APPROVE" ? "#dcfce7" : "#fef3c7",
								color: recorded.decision === "APPROVE" ? "#15803d" : "#b45309",
								border: `1px solid ${recorded.decision === "APPROVE" ? "#86efac" : "#fcd34d"}`,
								letterSpacing: "0.03em",
							}}
						>
							{recorded.decision === "APPROVE"
								? "RECOMMENDATION APPROVED"
								: "RECOMMENDATION OVERRIDDEN"}
						</span>
					</div>

					<div
						style={{
							fontSize: "12px",
							display: "flex",
							flexDirection: "column",
							gap: "3px",
						}}
					>
						<div style={{ color: "#334155" }}>
							<strong>Tark Recommended:</strong> {actionName}
						</div>
						<div style={{ color: "#334155" }}>
							<strong>Analyst Action:</strong>{" "}
							{recorded.decision === "APPROVE"
								? "Approved Recommendation"
								: "Overridden / Rejected"}
						</div>
						{recorded.rationale && (
							<div
								style={{
									color: "#475569",
									fontSize: "11px",
									lineHeight: "1.4",
								}}
							>
								<strong>Analyst Rationale:</strong> {recorded.rationale}
							</div>
						)}
						<div
							style={{ color: "#64748b", fontSize: "10px", marginTop: "2px" }}
						>
							Recorded by {recorded.analystId} ·{" "}
							{new Date(recorded.timestamp).toLocaleTimeString()}
						</div>
					</div>
				</div>
			) : showOverrideForm ? (
				/* 5. State D: Override Confirmation Form */
				<div
					style={{
						padding: "12px 14px",
						backgroundColor: "#fffbeb",
						border: "1px solid #fde68a",
						borderRadius: "6px",
						display: "flex",
						flexDirection: "column",
						gap: "10px",
					}}
				>
					<div style={{ fontSize: "12px", fontWeight: 700, color: "#92400e" }}>
						Reject / Override Tark Recommendation
					</div>
					<p style={{ margin: 0, fontSize: "11px", color: "#78350f" }}>
						Why are you overriding Tark’s recommendation ({actionName})?
					</p>

					<textarea
						value={overrideRationale}
						onChange={(e) => setOverrideRationale(e.target.value)}
						placeholder="Provide mandatory reason for override..."
						rows={3}
						style={{
							width: "100%",
							padding: "8px",
							fontSize: "12px",
							borderRadius: "4px",
							border: "1px solid #cbd5e1",
							boxSizing: "border-box",
							resize: "vertical",
							fontFamily: "inherit",
						}}
					/>

					<div
						style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}
					>
						<button
							onClick={() => {
								setShowOverrideForm(false);
								setError(null);
							}}
							disabled={isSubmitting}
							style={{
								padding: "6px 12px",
								fontSize: "12px",
								fontWeight: 500,
								color: "#475569",
								backgroundColor: "#ffffff",
								border: "1px solid #cbd5e1",
								borderRadius: "4px",
								cursor: "pointer",
							}}
						>
							Cancel
						</button>
						<button
							onClick={handleConfirmOverride}
							disabled={isSubmitting || !overrideRationale.trim()}
							style={{
								padding: "6px 14px",
								fontSize: "12px",
								fontWeight: 600,
								color: "#ffffff",
								backgroundColor:
									!overrideRationale.trim() || isSubmitting
										? "#fca5a5"
										: "#dc2626",
								border: "none",
								borderRadius: "4px",
								cursor:
									!overrideRationale.trim() || isSubmitting
										? "not-allowed"
										: "pointer",
							}}
						>
							{isSubmitting ? "Recording..." : "Confirm override"}
						</button>
					</div>
				</div>
			) : (
				/* 6. State E: Awaiting Analyst Decision */
				<div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
					<div style={{ fontSize: "12px", color: "#334155" }}>
						<div>
							Tark recommends:{" "}
							<strong style={{ color: "#0f172a" }}>{actionName}</strong>
						</div>
						<div
							style={{
								color: "#ea580c",
								fontWeight: 600,
								fontSize: "11px",
								marginTop: "2px",
							}}
						>
							{approvalRoute
								? `${approvalRoute.toUpperCase()} approval required`
								: "Human approval required"}
						</div>
					</div>

					<div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
						<button
							onClick={handleApprove}
							disabled={isSubmitting}
							style={{
								width: "100%",
								padding: "9px 16px",
								backgroundColor: isSubmitting ? "#fdba74" : "#ea580c",
								color: "#ffffff",
								fontSize: "13px",
								fontWeight: 700,
								borderRadius: "6px",
								border: "none",
								cursor: isSubmitting ? "not-allowed" : "pointer",
								transition: "background-color 0.15s ease",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								gap: "6px",
							}}
							onMouseEnter={(e) => {
								if (!isSubmitting)
									(e.currentTarget as HTMLElement).style.backgroundColor =
										"#c2410c";
							}}
							onMouseLeave={(e) => {
								if (!isSubmitting)
									(e.currentTarget as HTMLElement).style.backgroundColor =
										"#ea580c";
							}}
						>
							<span>Approve recommendation</span>
						</button>

						<button
							onClick={() => {
								setShowOverrideForm(true);
								setError(null);
							}}
							disabled={isSubmitting}
							style={{
								width: "100%",
								padding: "7px 12px",
								backgroundColor: "#ffffff",
								color: "#64748b",
								fontSize: "12px",
								fontWeight: 600,
								borderRadius: "6px",
								border: "1px solid #cbd5e1",
								cursor: "pointer",
								transition: "all 0.15s ease",
							}}
							onMouseEnter={(e) => {
								(e.currentTarget as HTMLElement).style.backgroundColor =
									"#f1f5f9";
								(e.currentTarget as HTMLElement).style.color = "#0f172a";
							}}
							onMouseLeave={(e) => {
								(e.currentTarget as HTMLElement).style.backgroundColor =
									"#ffffff";
								(e.currentTarget as HTMLElement).style.color = "#64748b";
							}}
						>
							Reject / Override
						</button>
					</div>
				</div>
			)}
		</div>
	);
};
