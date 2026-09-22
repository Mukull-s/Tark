import type React from "react";
import { useState } from "react";
import { runInvestigation } from "../api/client";
import type { CaseMetadata, InvestigationResultPayload } from "../api/types";
import { AnalystDecision } from "./AnalystDecision";
import { DecisionGate } from "./DecisionGate";
import { EvidenceCompassView } from "./EvidenceCompassView";
import { ExplanationSarView } from "./ExplanationSarView";
import { InvestigationActivity } from "./InvestigationActivity";
import { InvestigationConclusion } from "./InvestigationConclusion";
import { InvestigationNetwork } from "./InvestigationNetwork";
import { formatTriggerType, parseAmount } from "./InvestigationQueue";
import { KeyEvidenceFindings } from "./KeyEvidenceFindings";
import { NextBestAction } from "./NextBestAction";
import { RiskAssessment } from "./RiskAssessment";
import { InvestigationProgressStepper } from "./InvestigationProgressStepper";

interface InvestigationPreStartViewProps {
	caseItem: CaseMetadata;
	onBack: () => void;
	onResultUpdate?: (result: InvestigationResultPayload | null) => void;
}

export type InvestigationTab =
	| "activity"
	| "evidence"
	| "compass"
	| "network"
	| "risk"
	| "sar";

export const InvestigationPreStartView: React.FC<
	InvestigationPreStartViewProps
> = ({ caseItem, onBack, onResultUpdate }) => {
	const [isStarting, setIsStarting] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [investigationResult, setInvestigationResult] =
		useState<InvestigationResultPayload | null>(null);
	const [activeTab, setActiveTab] = useState<InvestigationTab>("activity");

	const amount =
		caseItem.exposure_usd != null
			? `$${caseItem.exposure_usd.toFixed(2)}`
			: caseItem.amount != null
				? `$${caseItem.amount.toFixed(2)}`
				: parseAmount(caseItem.trigger_text, caseItem.case_id);
	const triggerLabel = formatTriggerType(caseItem.trigger_type);

	const handleStartInvestigation = async () => {
		setIsStarting(true);
		setError(null);
		try {
			const response = await runInvestigation(caseItem.case_id);
			setInvestigationResult(response.result);
			if (onResultUpdate) {
				onResultUpdate(response.result);
			}
		} catch (err: any) {
			setError(
				err?.message ||
					"Failed to start autonomous investigation. Please check backend connection.",
			);
			setIsStarting(false);
		}
	};

	const getStatusLabel = () => {
		if (investigationResult) return "INVESTIGATION COMPLETED";
		if (isStarting) return "INVESTIGATING";
		return "READY FOR INVESTIGATION";
	};

	const isCompleted = !!investigationResult;

	return (
		<div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
			{/* Top Navigation */}
			<div>
				<button
					onClick={onBack}
					style={{
						display: "inline-flex",
						alignItems: "center",
						gap: "6px",
						padding: "6px 12px",
						fontSize: "13px",
						fontWeight: 500,
						color: "#475569",
						backgroundColor: "#ffffff",
						border: "1px solid #cbd5e1",
						borderRadius: "6px",
						cursor: "pointer",
						transition: "all 0.15s ease",
					}}
					onMouseEnter={(e) => {
						(e.currentTarget as HTMLElement).style.backgroundColor = "#f1f5f9";
						(e.currentTarget as HTMLElement).style.color = "#0f172a";
					}}
					onMouseLeave={(e) => {
						(e.currentTarget as HTMLElement).style.backgroundColor = "#ffffff";
						(e.currentTarget as HTMLElement).style.color = "#475569";
					}}
				>
					<span>←</span>
					<span>Back to Investigations</span>
				</button>
			</div>

			{/* Case Header Card */}
			<div
				style={{
					backgroundColor: "#ffffff",
					borderRadius: "8px",
					border: "1px solid #e2e8f0",
					padding: "20px 24px",
					boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
				}}
			>
				<div
					style={{
						display: "flex",
						justifyContent: "space-between",
						alignItems: "flex-start",
						flexWrap: "wrap",
						gap: "16px",
					}}
				>
					<div>
						<div
							style={{
								display: "flex",
								alignItems: "center",
								gap: "10px",
								marginBottom: "4px",
							}}
						>
							<h1
								style={{
									fontSize: "22px",
									fontWeight: 700,
									color: "#0f172a",
									margin: 0,
									letterSpacing: "-0.02em",
								}}
							>
								{caseItem.case_id}
							</h1>
							<span
								style={{
									fontSize: "11px",
									fontWeight: 600,
									padding: "2px 8px",
									borderRadius: "4px",
									backgroundColor: "#f8fafc",
									color: "#475569",
									border: "1px solid #e2e8f0",
								}}
							>
								{triggerLabel}
							</span>
						</div>
						<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
							Opened {caseItem.opened_at} · Flagged Transaction #
							{caseItem.flagged_txn_id}
						</p>
					</div>

					<div style={{ display: "flex", gap: "8px" }}>
						<span
							style={{
								fontSize: "11px",
								fontWeight: 700,
								padding: "4px 10px",
								borderRadius: "4px",
								backgroundColor: isCompleted
									? "#f0fdf4"
									: isStarting
										? "#eff6ff"
										: "#f1f5f9",
								color: isCompleted
									? "#15803d"
									: isStarting
										? "#1d4ed8"
										: "#475569",
								border: `1px solid ${isCompleted ? "#bbf7d0" : isStarting ? "#bfdbfe" : "#e2e8f0"}`,
								letterSpacing: "0.03em",
							}}
						>
							{getStatusLabel()}
						</span>
					</div>
				</div>

				{/* Case Metadata Strip */}
				<div
					style={{
						marginTop: "16px",
						display: "grid",
						gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
						gap: "12px",
						padding: "12px 16px",
						backgroundColor: "#f8fafc",
						borderRadius: "6px",
						border: "1px solid #eef2f6",
						fontSize: "13px",
					}}
				>
					<div>
						<div
							style={{
								color: "#64748b",
								fontSize: "11px",
								fontWeight: 500,
								marginBottom: "2px",
							}}
						>
							Transaction
						</div>
						<div style={{ fontWeight: 600, color: "#1e293b" }}>
							#{caseItem.flagged_txn_id}
						</div>
					</div>
					<div>
						<div
							style={{
								color: "#64748b",
								fontSize: "11px",
								fontWeight: 500,
								marginBottom: "2px",
							}}
						>
							Amount
						</div>
						<div style={{ fontWeight: 700, color: "#0f172a" }}>
							{amount || "—"}
						</div>
					</div>
					<div>
						<div
							style={{
								color: "#64748b",
								fontSize: "11px",
								fontWeight: 500,
								marginBottom: "2px",
							}}
						>
							Customer
						</div>
						<div style={{ fontWeight: 500, color: "#334155" }}>
							{caseItem.customer_id || "—"}
						</div>
					</div>
					<div>
						<div
							style={{
								color: "#64748b",
								fontSize: "11px",
								fontWeight: 500,
								marginBottom: "2px",
							}}
						>
							Card
						</div>
						<div style={{ fontWeight: 500, color: "#334155" }}>
							{caseItem.card_id || "—"}
						</div>
					</div>
					<div>
						<div
							style={{
								color: "#64748b",
								fontSize: "11px",
								fontWeight: 500,
								marginBottom: "2px",
							}}
						>
							Device
						</div>
						<div style={{ fontWeight: 500, color: "#64748b" }}>—</div>
					</div>
				</div>

				{/* Trigger Text Excerpt */}
				{caseItem.trigger_text && (
					<div
						style={{
							marginTop: "14px",
							fontSize: "13px",
							color: "#475569",
							lineHeight: "1.5",
						}}
					>
						<span style={{ fontWeight: 600, color: "#334155" }}>
							Alert Context:{" "}
						</span>
						<span>{caseItem.trigger_text}</span>
					</div>
				)}
			</div>

			{/* Staged Investigation Progress Experience */}
			{isStarting && (
				<InvestigationProgressStepper
					txnId={caseItem.flagged_txn_id}
					amount={amount || undefined}
					resultPayload={investigationResult}
					error={error}
					onCompleted={() => {
						setIsStarting(false);
					}}
				/>
			)}

			{/* Pre-Start or Re-start Action Panel */}
			{!isCompleted && !isStarting && (
				<div
					style={{
						backgroundColor: "#ffffff",
						borderRadius: "8px",
						border: "1px solid #e2e8f0",
						padding: "24px",
						boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
						display: "flex",
						flexDirection: "column",
						gap: "16px",
					}}
				>
					<div>
						<h2
							style={{
								fontSize: "17px",
								fontWeight: 700,
								color: "#0f172a",
								margin: "0 0 6px 0",
								letterSpacing: "-0.01em",
							}}
						>
							Ready to investigate
						</h2>
						<p
							style={{
								margin: "0 0 8px 0",
								color: "#475569",
								fontSize: "14px",
								lineHeight: "1.5",
							}}
						>
							Tark will select and execute the most informative
							evidence-gathering steps for this case.
						</p>
						<p
							style={{
								margin: 0,
								color: "#64748b",
								fontSize: "13px",
								fontStyle: "italic",
							}}
						>
							“You choose the case. Tark chooses the investigation path.”
						</p>
					</div>

					{error && (
						<div
							style={{
								padding: "12px 16px",
								backgroundColor: "#fef2f2",
								borderRadius: "6px",
								border: "1px solid #fecaca",
								color: "#b91c1c",
								fontSize: "13px",
								fontWeight: 500,
							}}
						>
							{error}
						</div>
					)}

					<div>
						<button
							onClick={handleStartInvestigation}
							disabled={isStarting}
							style={{
								padding: "10px 20px",
								backgroundColor: isStarting ? "#fdba74" : "#ea580c",
								color: "#ffffff",
								fontSize: "13.5px",
								fontWeight: 600,
								borderRadius: "6px",
								border: "none",
								cursor: isStarting ? "not-allowed" : "pointer",
								display: "inline-flex",
								alignItems: "center",
								gap: "8px",
								transition: "background-color 0.15s ease",
							}}
							onMouseEnter={(e) => {
								if (!isStarting) {
									(e.currentTarget as HTMLElement).style.backgroundColor =
										"#c2410c";
								}
							}}
							onMouseLeave={(e) => {
								if (!isStarting) {
									(e.currentTarget as HTMLElement).style.backgroundColor =
										"#ea580c";
								}
							}}
						>
							{isStarting && (
								<span
									style={{
										display: "inline-block",
										width: "12px",
										height: "12px",
										border: "2px solid #ffffff",
										borderTopColor: "transparent",
										borderRadius: "50%",
										animation: "spin 1s linear infinite",
									}}
								/>
							)}
							<span>
								{isStarting
									? "Investigation starting..."
									: "Start Investigation"}
							</span>
						</button>
					</div>
				</div>
			)}

			{/* Investigation Workstation Layout: Main Left Workspace + Sticky Right Decision Rail */}
			{isCompleted && investigationResult && (
				<div
					style={{
						display: "grid",
						gridTemplateColumns: "minmax(0, 1fr) 380px",
						gap: "24px",
						alignItems: "flex-start",
					}}
					className="investigation-workstation-grid"
				>
					{/* Main Left Workspace: Conclusion Summary + Tab Navigation + Selected View */}
					<div
						style={{
							minWidth: 0,
							display: "flex",
							flexDirection: "column",
							gap: "20px",
						}}
					>
						{/* Investigation Conclusion Summary */}
						<InvestigationConclusion result={investigationResult} />

						{/* Tab Navigation Row */}
						<div
							style={{
								display: "flex",
								alignItems: "center",
								gap: "4px",
								borderBottom: "1px solid #e2e8f0",
								paddingBottom: "2px",
								overflowX: "auto",
							}}
						>
							{(
								[
									{ id: "activity", label: "Activity" },
									{ id: "evidence", label: "Evidence" },
									{ id: "compass", label: "Compass" },
									{ id: "network", label: "Network" },
									{ id: "risk", label: "Risk" },
									{ id: "sar", label: "SAR & Report" },
								] as const
							).map((tab) => {
								const isActive = activeTab === tab.id;
								return (
									<button
										key={tab.id}
										onClick={() => setActiveTab(tab.id)}
										style={{
											padding: "8px 14px",
											fontSize: "13px",
											fontWeight: isActive ? 600 : 500,
											color: isActive ? "#ea580c" : "#475569",
											backgroundColor: isActive ? "#ffffff" : "transparent",
											borderTop: isActive
												? "1px solid #e2e8f0"
												: "1px solid transparent",
											borderLeft: isActive
												? "1px solid #e2e8f0"
												: "1px solid transparent",
											borderRight: isActive
												? "1px solid #e2e8f0"
												: "1px solid transparent",
											borderBottom: isActive
												? "2px solid #ea580c"
												: "2px solid transparent",
											borderRadius: "6px 6px 0 0",
											cursor: "pointer",
											transition: "all 0.15s ease",
											marginBottom: "-1px",
											whiteSpace: "nowrap",
										}}
									>
										{tab.label}
									</button>
								);
							})}
						</div>

						{/* Render ONLY the selected view */}
						{activeTab === "activity" && (
							<InvestigationActivity result={investigationResult} />
						)}
						{activeTab === "evidence" && (
							<KeyEvidenceFindings result={investigationResult} />
						)}
						{activeTab === "compass" && (
							<EvidenceCompassView result={investigationResult} />
						)}
						{activeTab === "network" && (
							<InvestigationNetwork result={investigationResult} />
						)}
						{activeTab === "risk" && (
							<RiskAssessment result={investigationResult} />
						)}
						{activeTab === "sar" && (
							<ExplanationSarView result={investigationResult} />
						)}
					</div>

					{/* Right-Side Decision Rail (Sticky Panel) */}
					<div
						style={{
							position: "sticky",
							top: "20px",
							alignSelf: "flex-start",
							display: "flex",
							flexDirection: "column",
							gap: "16px",
						}}
					>
						<DecisionGate result={investigationResult} />
						<NextBestAction result={investigationResult} />
						<AnalystDecision
							result={investigationResult}
							onDecisionSubmitted={(updated) => setInvestigationResult(updated)}
						/>
					</div>
				</div>
			)}
		</div>
	);
};
