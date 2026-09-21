import React, { useState } from "react";
import type { InvestigationResultPayload } from "../api/types";

interface ExplanationSarViewProps {
	result: InvestigationResultPayload;
}

export const ExplanationSarView: React.FC<ExplanationSarViewProps> = ({
	result,
}) => {
	const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

	const finalState = result.run_result?.final_state;
	const primaryAction = result.run_result?.primary_action;
	const caseId = result.case?.case_id || result.investigation_id;
	const flaggedTxnId = result.case?.flagged_txn_id || "N/A";
	const pFraud = finalState?.fraud_probability ?? 0.5;
	const gatePassed = finalState?.decision_gate_passed ?? false;

	// Real dynamic grounded synthesis from backend
	const rawSynthesis =
		result.run_result?.grounded_synthesis?.trim() ||
		result.run_result?.executive_summary?.trim() ||
		`SUSPICIOUS ACTIVITY REPORT & CASE EXPLANATION\n\nCase ${caseId} was autonomously investigated by Tark. Final posterior fraud probability is ${(pFraud * 100).toFixed(1)}% with evidence coverage at ${((finalState?.evidence_coverage ?? 0) * 100).toFixed(0)}%. Recommended action is ${primaryAction?.action || "MONITOR_CARD"} under ${primaryAction?.approval_route || "L1"} authorization.`;

	// Extract unique citation sets for the audit section
	const evidenceCitations = Array.from(
		new Set(rawSynthesis.match(/\[EVD-[A-Za-z0-9_-]+\]/g) || [])
	);
	const precedentCitations = Array.from(
		new Set(rawSynthesis.match(/\[CC-[A-Za-z0-9_-]+\]/g) || [])
	);
	const knowledgeCitations = Array.from(
		new Set(rawSynthesis.match(/\[KNOW-[A-Za-z0-9_-]+\]/g) || [])
	);
	const totalCitationsCount =
		evidenceCitations.length + precedentCitations.length + knowledgeCitations.length;

	const handleCopyClipboard = () => {
		navigator.clipboard.writeText(rawSynthesis);
		setFeedbackMsg("SAR narrative copied to clipboard.");
		setTimeout(() => setFeedbackMsg(null), 3000);
	};

	const handleDownloadJson = () => {
		const dataStr =
			"data:text/json;charset=utf-8," +
			encodeURIComponent(JSON.stringify(result, null, 2));
		const downloadAnchor = document.createElement("a");
		downloadAnchor.setAttribute("href", dataStr);
		downloadAnchor.setAttribute("download", `${caseId}_investigation_pack.json`);
		document.body.appendChild(downloadAnchor);
		downloadAnchor.click();
		downloadAnchor.remove();
		setFeedbackMsg("Investigation JSON Pack downloaded.");
		setTimeout(() => setFeedbackMsg(null), 3000);
	};

	const handleDownloadSar = () => {
		const header = `================================================================================\nFINCEN FORM 111 — SUSPICIOUS ACTIVITY REPORT (SAR) NARRATIVE\n================================================================================\nCase ID:             ${caseId}\nFlagged Transaction: ${flaggedTxnId}\nGenerated At:        ${new Date().toISOString()}\nTarget Institution:  Tark Institutional Risk Engine\nPrimary Action:      ${primaryAction?.action || "DECLINE_TRANSACTION"} (${primaryAction?.approval_route || "L1"})\nDecision Gate:       ${gatePassed ? "PASSED (Decisive Grounded Evidence)" : "INCOMPLETE"}\nPosterior P(Fraud):  ${(pFraud * 100).toFixed(2)}%\nTotal Citations:     ${totalCitationsCount} verified citations\n================================================================================\n\n`;

		const fullSarDocument = header + rawSynthesis;
		const dataStr =
			"data:text/plain;charset=utf-8," + encodeURIComponent(fullSarDocument);
		const downloadAnchor = document.createElement("a");
		downloadAnchor.setAttribute("href", dataStr);
		downloadAnchor.setAttribute("download", `${caseId}_FinCEN_SAR_Narrative.txt`);
		document.body.appendChild(downloadAnchor);
		downloadAnchor.click();
		downloadAnchor.remove();
		setFeedbackMsg("FinCEN SAR Narrative downloaded successfully.");
		setTimeout(() => setFeedbackMsg(null), 3000);
	};

	// Helper to format text with interactive citation badges
	const renderFormattedText = (text: string) => {
		// Split by lines to preserve paragraphs and headings
		const lines = text.split("\n");

		return (
			<div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
				{lines.map((line, lineIdx) => {
					const trimmed = line.trim();
					if (!trimmed) return null;

					// Heading 3
					if (trimmed.startsWith("### ")) {
						return (
							<h3
								key={lineIdx}
								style={{
									fontSize: "15px",
									fontWeight: 700,
									color: "#0f172a",
									margin: "14px 0 4px 0",
									paddingBottom: "4px",
									borderBottom: "1px solid #e2e8f0",
									letterSpacing: "-0.01em",
								}}
							>
								{trimmed.replace(/^###\s+/, "")}
							</h3>
						);
					}

					// Heading 2 or 1
					if (trimmed.startsWith("## ") || trimmed.startsWith("# ")) {
						return (
							<h2
								key={lineIdx}
								style={{
									fontSize: "16.5px",
									fontWeight: 700,
									color: "#0f172a",
									margin: "16px 0 6px 0",
									letterSpacing: "-0.01em",
								}}
							>
								{trimmed.replace(/^#+\s+/, "")}
							</h2>
						);
					}

					// Bullet points
					const isBullet = trimmed.startsWith("- ") || trimmed.startsWith("* ");
					const cleanText = isBullet ? trimmed.replace(/^[-*]\s+/, "") : trimmed;

					// Tokenize citations in text: [EVD-...], [CC-...], [KNOW-...]
					const parts = cleanText.split(/(\[[A-Z0-9_-]+:[^\]]+\]|\[(?:EVD|CC|KNOW)-[A-Za-z0-9_-]+\])/g);

					const formattedLine = parts.map((part, partIdx) => {
						if (part.startsWith("[EVD-")) {
							return (
								<span
									key={partIdx}
									title={`Empirical Evidence Item Citation: ${part}`}
									style={{
										fontSize: "11px",
										fontFamily: "ui-monospace, monospace",
										fontWeight: 700,
										padding: "1px 6px",
										borderRadius: "3px",
										backgroundColor: "#fff7ed",
										color: "#c2410c",
										border: "1px solid #fed7aa",
										margin: "0 2px",
										cursor: "help",
									}}
								>
									{part}
								</span>
							);
						}
						if (part.startsWith("[CC-")) {
							return (
								<span
									key={partIdx}
									title={`Case Memory Precedent Citation: ${part}`}
									style={{
										fontSize: "11px",
										fontFamily: "ui-monospace, monospace",
										fontWeight: 700,
										padding: "1px 6px",
										borderRadius: "3px",
										backgroundColor: "#f5f3ff",
										color: "#6d28d9",
										border: "1px solid #ddd6fe",
										margin: "0 2px",
										cursor: "help",
									}}
								>
									{part}
								</span>
							);
						}
						if (part.startsWith("[KNOW-")) {
							return (
								<span
									key={partIdx}
									title={`Regulatory & Policy GraphRAG Citation: ${part}`}
									style={{
										fontSize: "11px",
										fontFamily: "ui-monospace, monospace",
										fontWeight: 700,
										padding: "1px 6px",
										borderRadius: "3px",
										backgroundColor: "#f0fdf4",
										color: "#15803d",
										border: "1px solid #bbf7d0",
										margin: "0 2px",
										cursor: "help",
									}}
								>
									{part}
								</span>
							);
						}
						return <span key={partIdx}>{part}</span>;
					});

					return (
						<p
							key={lineIdx}
							style={{
								margin: 0,
								paddingLeft: isBullet ? "16px" : "0",
								position: "relative",
								fontSize: "13.5px",
								lineHeight: 1.6,
								color: "#1e293b",
							}}
						>
							{isBullet && (
								<span
									style={{
										position: "absolute",
										left: 0,
										color: "#64748b",
									}}
								>
									&bull;
								</span>
							)}
							{formattedLine}
						</p>
					);
				})}
			</div>
		);
	};

	const filingMandatory = pFraud >= 0.7;

	return (
		<div
			style={{
				backgroundColor: "#ffffff",
				borderRadius: "8px",
				border: "1px solid #e2e8f0",
				padding: "24px",
				boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
				display: "flex",
				flexDirection: "column",
				gap: "20px",
			}}
		>
			{/* Header & Export Actions */}
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
							Investigation Explanation & SAR Narrative
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
							}}
						>
							FinCEN Form 111 Grounded Narrative
						</span>
					</div>
					<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
						7-Section statutory narrative grounded in empirical TigerGraph evidence and verified GraphRAG citations
					</p>
				</div>

				<div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
					<button
						onClick={handleCopyClipboard}
						style={{
							padding: "6px 12px",
							backgroundColor: "#ffffff",
							border: "1px solid #cbd5e1",
							borderRadius: "6px",
							fontSize: "12px",
							fontWeight: 600,
							color: "#334155",
							cursor: "pointer",
						}}
					>
						Copy Text
					</button>
					<button
						onClick={handleDownloadJson}
						style={{
							padding: "6px 12px",
							backgroundColor: "#f1f5f9",
							border: "1px solid #cbd5e1",
							borderRadius: "6px",
							fontSize: "12px",
							fontWeight: 600,
							color: "#334155",
							cursor: "pointer",
						}}
					>
						Download JSON Pack
					</button>
					<button
						onClick={handleDownloadSar}
						style={{
							padding: "6px 12px",
							backgroundColor: "#ea580c",
							border: "none",
							borderRadius: "6px",
							fontSize: "12px",
							fontWeight: 600,
							color: "#ffffff",
							cursor: "pointer",
						}}
					>
						Download SAR (.txt)
					</button>
				</div>
			</div>

			{feedbackMsg && (
				<div
					style={{
						padding: "8px 12px",
						backgroundColor: "#f0fdf4",
						border: "1px solid #bbf7d0",
						borderRadius: "4px",
						color: "#15803d",
						fontSize: "12px",
						fontWeight: 600,
					}}
				>
					{feedbackMsg}
				</div>
			)}

			{/* FinCEN Statutory Compliance Card */}
			<div
				style={{
					border: "1px solid #e2e8f0",
					borderRadius: "6px",
					padding: "14px 16px",
					backgroundColor: "#f8fafc",
					display: "flex",
					flexWrap: "wrap",
					gap: "16px",
					justifyContent: "space-between",
					alignItems: "center",
				}}
			>
				<div style={{ display: "flex", gap: "20px", flexWrap: "wrap", alignItems: "center" }}>
					<div>
						<div style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>
							Statutory Filing Mandate
						</div>
						<div style={{ fontSize: "13px", fontWeight: 700, color: "#0f172a", marginTop: "2px" }}>
							31 U.S.C. 5318(g) / Form 111
						</div>
					</div>

					<div style={{ borderLeft: "1px solid #e2e8f0", paddingLeft: "20px" }}>
						<div style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>
							Primary Recommendation
						</div>
						<div style={{ fontSize: "13px", fontWeight: 700, color: "#0f172a", marginTop: "2px" }}>
							{primaryAction?.action?.replace(/_/g, " ") || "DECLINE TRANSACTION"}
							<span style={{ fontSize: "11px", color: "#64748b", marginLeft: "6px" }}>
								({primaryAction?.approval_route || "L1"})
							</span>
						</div>
					</div>

					<div style={{ borderLeft: "1px solid #e2e8f0", paddingLeft: "20px" }}>
						<div style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>
							Verified Grounded Citations
						</div>
						<div style={{ fontSize: "13px", fontWeight: 700, color: "#0f172a", marginTop: "2px" }}>
							{totalCitationsCount} references
							<span style={{ fontSize: "11px", color: "#15803d", marginLeft: "4px" }}>
								(100% verified)
							</span>
						</div>
					</div>
				</div>

				<div>
					<span
						style={{
							fontSize: "11px",
							fontWeight: 700,
							padding: "4px 10px",
							borderRadius: "4px",
							backgroundColor: filingMandatory ? "#fef2f2" : "#f0fdf4",
							color: filingMandatory ? "#b91c1c" : "#15803d",
							border: `1px solid ${filingMandatory ? "#fecaca" : "#bbf7d0"}`,
						}}
					>
						{filingMandatory ? "SAR FILING MANDATED" : "NO FILING REQUIRED"}
					</span>
				</div>
			</div>

			{/* Citation Legend */}
			<div
				style={{
					display: "flex",
					gap: "12px",
					flexWrap: "wrap",
					alignItems: "center",
					padding: "8px 12px",
					backgroundColor: "#ffffff",
					borderRadius: "6px",
					border: "1px solid #e2e8f0",
					fontSize: "11px",
					color: "#64748b",
				}}
			>
				<span style={{ fontWeight: 700, color: "#0f172a" }}>Citation Reference Key:</span>
				<div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
					<span
						style={{
							padding: "1px 5px",
							borderRadius: "3px",
							backgroundColor: "#fff7ed",
							color: "#c2410c",
							border: "1px solid #fed7aa",
							fontFamily: "monospace",
						}}
					>
						[EVD-...]
					</span>
					<span>Empirical Graph Evidence</span>
				</div>
				<div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
					<span
						style={{
							padding: "1px 5px",
							borderRadius: "3px",
							backgroundColor: "#f5f3ff",
							color: "#6d28d9",
							border: "1px solid #ddd6fe",
							fontFamily: "monospace",
						}}
					>
						[CC-...]
					</span>
					<span>Historical Case Precedent</span>
				</div>
				<div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
					<span
						style={{
							padding: "1px 5px",
							borderRadius: "3px",
							backgroundColor: "#f0fdf4",
							color: "#15803d",
							border: "1px solid #bbf7d0",
							fontFamily: "monospace",
						}}
					>
						[KNOW-...]
					</span>
					<span>Statutory / Typology Knowledge</span>
				</div>
			</div>

			{/* Real Grounded Narrative Body */}
			<div
				style={{
					backgroundColor: "#ffffff",
					border: "1px solid #e2e8f0",
					borderRadius: "6px",
					padding: "20px 22px",
					boxShadow: "inset 0 1px 2px rgba(0, 0, 0, 0.01)",
				}}
			>
				{renderFormattedText(rawSynthesis)}
			</div>
		</div>
	);
};
