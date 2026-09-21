import type React from "react";
import type {
	ActionRecommendationView,
	InvestigationResultPayload,
} from "../api/types";
import { TechnicalDetails } from "./TechnicalDetails";

interface NextBestActionProps {
	result: InvestigationResultPayload;
}

export const formatActionName = (action: string): string => {
	return action.replace(/_/g, " ").toUpperCase();
};

export const formatScopeName = (scope: string): string => {
	return scope.replace(/_/g, " ").toUpperCase();
};

export const cleanReasonText = (reason: string): string => {
	if (!reason) return "";
	// Clean internal rule codes like "R5: " or "R2: " if present for human reading
	return reason.replace(/^R\d+:\s*/i, "");
};

export const NextBestAction: React.FC<NextBestActionProps> = ({ result }) => {
	const finalState = result.run_result?.final_state;
	const primaryAction = result.run_result?.primary_action;
	const consequentialActions = result.run_result?.consequential_actions || [];
	const decisionState = finalState?.decision_state ?? "PENDING";
	const gatePassed = finalState?.decision_gate_passed ?? false;

	const isInsufficientEvidence =
		decisionState === "INSUFFICIENT_EVIDENCE" ||
		(!gatePassed && decisionState !== "REQUIRES_HUMAN_APPROVAL");

	// Fallback / Insufficient Evidence State
	if (isInsufficientEvidence || !primaryAction) {
		return (
			<div
				style={{
					backgroundColor: "#ffffff",
					borderRadius: "8px",
					border: "1px solid #e2e8f0",
					padding: "20px",
					boxShadow: "0 1px 3px rgba(0, 0, 0, 0.03)",
					display: "flex",
					flexDirection: "column",
					gap: "14px",
				}}
			>
				<div>
					<h2
						style={{
							fontSize: "16px",
							fontWeight: 700,
							color: "#0f172a",
							margin: "0 0 4px 0",
							letterSpacing: "-0.01em",
						}}
					>
						Next best action
					</h2>
					<p style={{ margin: 0, color: "#64748b", fontSize: "12px" }}>
						What should happen next
					</p>
				</div>

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
							fontSize: "13px",
							fontWeight: 700,
							color: "#475569",
							letterSpacing: "0.04em",
						}}
					>
						[ NO ACTION RECOMMENDED ]
					</div>
					<div
						style={{ fontSize: "11px", color: "#64748b", lineHeight: "1.4" }}
					>
						Investigation ended with insufficient evidence. Autonomous
						operational action is withheld.
					</div>
				</div>
			</div>
		);
	}

	const approvalRoute = primaryAction.approval_route;
	const isAuto = approvalRoute === "auto";
	const reasonText = cleanReasonText(primaryAction.reason);

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
					Next best action
				</h2>
				<p style={{ margin: 0, color: "#64748b", fontSize: "12px" }}>
					What should happen next
				</p>
			</div>

			{/* 2. Primary Action Prominent Banner */}
			<div
				style={{
					padding: "12px 14px",
					backgroundColor: "#fff7ed",
					border: "1px solid #ffedd5",
					borderRadius: "6px",
					display: "flex",
					flexDirection: "column",
					gap: "3px",
				}}
			>
				<div
					style={{
						fontSize: "14.5px",
						fontWeight: 800,
						color: "#c2410c",
						letterSpacing: "0.02em",
					}}
				>
					{formatActionName(primaryAction.action)}
				</div>
				<div
					style={{
						fontSize: "10.5px",
						fontWeight: 600,
						color: "#ea580c",
						textTransform: "uppercase",
						letterSpacing: "0.04em",
					}}
				>
					Primary recommendation
				</div>
			</div>

			{/* 3. Key Action Details: Approval & Scope */}
			<div
				style={{
					display: "flex",
					flexDirection: "column",
					gap: "8px",
					fontSize: "12px",
				}}
			>
				{approvalRoute && (
					<div>
						<div
							style={{
								color: "#64748b",
								fontSize: "10px",
								textTransform: "uppercase",
								fontWeight: 600,
								marginBottom: "2px",
							}}
						>
							Approval Requirement
						</div>
						<div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
							<span
								style={{
									fontSize: "11px",
									fontWeight: 700,
									padding: "2px 8px",
									borderRadius: "4px",
									backgroundColor: isAuto ? "#f0fdf4" : "#fffbeb",
									color: isAuto ? "#15803d" : "#b45309",
									border: `1px solid ${isAuto ? "#bbf7d0" : "#fde68a"}`,
									letterSpacing: "0.02em",
								}}
							>
								{isAuto
									? "AUTOMATIC ACTION ALLOWED"
									: `${approvalRoute.toUpperCase()} APPROVAL REQUIRED`}
							</span>
						</div>
					</div>
				)}

				{primaryAction.scope && (
					<div>
						<div
							style={{
								color: "#64748b",
								fontSize: "10px",
								textTransform: "uppercase",
								fontWeight: 600,
								marginBottom: "2px",
							}}
						>
							Target Scope
						</div>
						<div style={{ fontWeight: 600, color: "#1e293b" }}>
							{formatScopeName(primaryAction.scope)}
						</div>
					</div>
				)}

				{/* 4. Why / Rationale */}
				{reasonText && (
					<div>
						<div
							style={{
								color: "#64748b",
								fontSize: "10px",
								textTransform: "uppercase",
								fontWeight: 600,
								marginBottom: "2px",
							}}
						>
							Policy Rationale
						</div>
						<div style={{ color: "#334155", lineHeight: "1.45" }}>
							{reasonText}
						</div>
					</div>
				)}
			</div>

			{/* 5. Secondary / Consequential Actions (if present) */}
			{consequentialActions.length > 0 && (
				<>
					<div style={{ height: "1px", backgroundColor: "#eef2f6" }} />
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
							Consequential Actions ({consequentialActions.length})
						</div>

						<div
							style={{ display: "flex", flexDirection: "column", gap: "6px" }}
						>
							{consequentialActions.map(
								(secAction: ActionRecommendationView, idx: number) => (
									<div
										key={idx}
										style={{
											padding: "8px 10px",
											backgroundColor: "#f8fafc",
											borderRadius: "4px",
											border: "1px solid #eef2f6",
											fontSize: "11px",
											display: "flex",
											flexDirection: "column",
											gap: "2px",
										}}
									>
										<div
											style={{
												display: "flex",
												justifyContent: "space-between",
												alignItems: "center",
											}}
										>
											<span style={{ fontWeight: 700, color: "#0f172a" }}>
												{formatActionName(secAction.action)}
											</span>
											<span
												style={{
													fontSize: "9px",
													fontWeight: 600,
													padding: "1px 5px",
													borderRadius: "3px",
													backgroundColor:
														secAction.approval_route === "auto"
															? "#f0fdf4"
															: "#fffbeb",
													color:
														secAction.approval_route === "auto"
															? "#15803d"
															: "#b45309",
													border: `1px solid ${secAction.approval_route === "auto" ? "#bbf7d0" : "#fde68a"}`,
													textTransform: "uppercase",
												}}
											>
												{secAction.approval_route}
											</span>
										</div>
										{secAction.scope && (
											<div style={{ color: "#64748b", fontSize: "10px" }}>
												Scope: {formatScopeName(secAction.scope)}
											</div>
										)}
									</div>
								),
							)}
						</div>
					</div>
				</>
			)}

			{/* Collapsible Technical Details Drawer */}
			<div style={{ marginTop: "4px" }}>
				<TechnicalDetails
					title="Policy Engine & Action Specifications"
					summaryItems={[
						{ label: "Internal Action Code", value: primaryAction.action },
						{ label: "Approval Route Tier", value: primaryAction.approval_route || "auto" },
						{ label: "Target Entity Scope", value: primaryAction.scope || "TRANSACTION" },
						{ label: "Deterministic Role", value: primaryAction.role || "primary" },
					]}
					rawPayload={primaryAction}
				/>
			</div>
		</div>
	);
};
