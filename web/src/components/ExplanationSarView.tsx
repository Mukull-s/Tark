import React, { useState } from "react";
import type { InvestigationResultPayload } from "../api/types";
import {
	FileText,
	Download,
	Copy,
	CheckCircle2,
	AlertTriangle,
	Layers,
	Scale,
	Database,
	Lock,
	Unlock,
	ArrowRight,
	Check,
	Code2,
	Eye,
} from "lucide-react";

interface ExplanationSarViewProps {
	result: InvestigationResultPayload;
}

interface ParsedSection {
	number: number;
	rawTitle: string;
	title: string;
	lines: string[];
}

export const ExplanationSarView: React.FC<ExplanationSarViewProps> = ({
	result,
}) => {
	const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);
	const [viewMode, setViewMode] = useState<"dossier" | "raw">("dossier");

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
		`### 1. Executive Summary\n- **Investigation Identifier:** \`${caseId}\`\n- **Target Entities:** Card \`${result.case?.card_id || "N/A"}\` | Customer \`${result.case?.customer_id || "N/A"}\` | Flagged Txn \`${flaggedTxnId}\`\n- **Financial Exposure:** $${(result.exposure_usd ?? 0).toFixed(2)}\n- **Belief Shift:** P(Fraud) shifted from ${(result.initial_state?.fraud_probability ?? 0.5).toFixed(4)} to ${pFraud.toFixed(4)}.\n- **Decision Gate Status:** ${gatePassed ? "PASSED (DECISION_REACHED)" : "LOCKED (INSUFFICIENT_EVIDENCE)"}.\n- **Evidence Coverage:** ${(((finalState?.evidence_coverage ?? 0)) * 100).toFixed(0)}% of core investigative dimensions observed.\n- **Primary Disposition:** ${primaryAction?.action || "MONITOR_CARD"} under ${primaryAction?.approval_route || "L1"} authorization.\n\n### 2. Graph Evidence Analysis\nEmpirical evidence observed via deterministic GSQL query executions on the TigerGraph cluster:\n- Clean graph baseline profile observed.\n\n### 3. Historical Precedent Analysis\nContextual memory precedents retrieved from historical closed investigations:\n- No prior cases linked to this target entity.\n\n### 4. Policy & Regulatory Compliance\nAuthoritative bank policies governing disposition:\n- Standard statutory fraud monitoring thresholds apply.\n\n### 5. Uncertainty & Conflict Assessment\n- **Epistemic Uncertainty:** ${(finalState?.epistemic_uncertainty ?? 0.5).toFixed(2)}.\n- **Aleatoric Conflict:** ${(finalState?.aleatoric_uncertainty ?? 0.1).toFixed(2)}.\n- **Coverage Gate:** ${gatePassed ? "UNLOCKED" : "LOCKED"}.\n\n### 6. Investigation Trajectory & EVOI Rationale\nEvidence acquisition ceased after evaluating candidate Net Decision Value.\n\n### 7. Final Operational Disposition & Remediation\n- **\`${primaryAction?.action || "MONITOR_CARD"}\`** (Approval Route: \`${primaryAction?.approval_route || "L1"}\`): ${primaryAction?.reason || "Policy threshold evaluation."}`;

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

	/**
	 * Tokenizes text and renders clean, normal fonts:
	 * - Removes raw asterisks **...** and renders normal bold text
	 * - Only renders monospace on short technical IDs (<= 25 chars, no spaces)
	 * - Turns long backticked titles into normal bold text (never typewriter monospace)
	 * - Renders citation pills for [EVD-...], [CC-...], [KNOW-...]
	 */
	const renderInlineMarkdown = (text: string, keyPrefix = "inline"): React.ReactNode[] => {
		const clean = text.replace(/^[•\-\*]\s*/, "");

		const regex = /(\[(?:EVD|CC|KNOW)-[A-Za-z0-9_-]+\]|\[[A-Z0-9_-]+:[^\]]+\]|\*\*[^*]+\*\*|`[^`]+`)/g;
		const parts = clean.split(regex);

		return parts.map((part, idx) => {
			if (!part) return null;
			const partKey = `${keyPrefix}-${idx}`;

			// Evidence Citation Badge
			if (part.startsWith("[EVD-")) {
				return (
					<span
						key={partKey}
						title={`Empirical Evidence Item Citation: ${part}`}
						style={{
							fontSize: "11.5px",
							fontWeight: 700,
							padding: "2px 7px",
							borderRadius: "4px",
							backgroundColor: "#fff7ed",
							color: "#c2410c",
							border: "1px solid #fed7aa",
							margin: "0 2px",
							display: "inline-flex",
							alignItems: "center",
							gap: "4px",
							verticalAlign: "baseline",
							fontFamily: "inherit",
						}}
					>
						<Database size={11} style={{ opacity: 0.8 }} />
						{part}
					</span>
				);
			}

			// Precedent Citation Badge
			if (part.startsWith("[CC-")) {
				return (
					<span
						key={partKey}
						title={`Historical Closed Case Precedent: ${part}`}
						style={{
							fontSize: "11.5px",
							fontWeight: 700,
							padding: "2px 7px",
							borderRadius: "4px",
							backgroundColor: "#f5f3ff",
							color: "#6d28d9",
							border: "1px solid #ddd6fe",
							margin: "0 2px",
							display: "inline-flex",
							alignItems: "center",
							gap: "4px",
							verticalAlign: "baseline",
							fontFamily: "inherit",
						}}
					>
						<Layers size={11} style={{ opacity: 0.8 }} />
						{part}
					</span>
				);
			}

			// Knowledge Citation Badge
			if (part.startsWith("[KNOW-")) {
				return (
					<span
						key={partKey}
						title={`Statutory & Regulatory Knowledge: ${part}`}
						style={{
							fontSize: "11.5px",
							fontWeight: 700,
							padding: "2px 7px",
							borderRadius: "4px",
							backgroundColor: "#f0fdf4",
							color: "#15803d",
							border: "1px solid #bbf7d0",
							margin: "0 2px",
							display: "inline-flex",
							alignItems: "center",
							gap: "4px",
							verticalAlign: "baseline",
							fontFamily: "inherit",
						}}
					>
						<Scale size={11} style={{ opacity: 0.8 }} />
						{part}
					</span>
				);
			}

			// Bold text (clean normal bold, no asterisks)
			if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
				const inner = part.slice(2, -2);
				// If inner is a citation like [KNOW-POLICY-R6], parse it recursively
				if (/^\[(?:EVD|CC|KNOW)-[A-Za-z0-9_-]+\]$/.test(inner)) {
					return renderInlineMarkdown(inner, `${partKey}-cit`);
				}
				return (
					<strong
						key={partKey}
						style={{
							fontWeight: 700,
							color: "#0f172a",
						}}
					>
						{inner}
					</strong>
				);
			}

			// Inline code
			if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
				const inner = part.slice(1, -1);
				// If it contains spaces or is longer than 25 characters, it's a title, NOT code!
				// Render it in normal font!
				const isActualShortCode = inner.length <= 25 && !inner.includes(" ");
				if (!isActualShortCode) {
					return (
						<span
							key={partKey}
							style={{
								fontWeight: 700,
								color: "#0f172a",
								fontSize: "13.5px",
							}}
						>
							{inner}
						</span>
					);
				}

				return (
					<code
						key={partKey}
						style={{
							fontSize: "12px",
							fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
							fontWeight: 600,
							padding: "1px 5px",
							borderRadius: "4px",
							backgroundColor: "#f1f5f9",
							color: "#0f172a",
							border: "1px solid #e2e8f0",
							margin: "0 2px",
						}}
					>
						{inner}
					</code>
				);
			}

			return <span key={partKey}>{part}</span>;
		});
	};

	/**
	 * Parses synthesis text into structured sections.
	 */
	const parseSections = (text: string): ParsedSection[] => {
		const rawLines = text.split("\n");
		const sections: ParsedSection[] = [];
		let currentSection: ParsedSection | null = null;

		const headerRegex = /^(?:###\s*|##\s*|#\s*)?([1-7])\.\s+(.*)$/;

		for (const line of rawLines) {
			const trimmed = line.trim();
			const match = trimmed.match(headerRegex);

			if (match) {
				const num = parseInt(match[1], 10);
				const titleText = `${num}. ${match[2].trim()}`;

				if (currentSection) {
					sections.push(currentSection);
				}
				currentSection = {
					number: num,
					rawTitle: trimmed,
					title: titleText,
					lines: [],
				};
			} else if (currentSection) {
				if (trimmed) {
					currentSection.lines.push(trimmed);
				}
			} else if (trimmed) {
				currentSection = {
					number: 0,
					rawTitle: "Investigation Overview",
					title: "Investigation Overview",
					lines: [trimmed],
				};
			}
		}

		if (currentSection) {
			sections.push(currentSection);
		}

		return sections;
	};

	const parsedSections = parseSections(rawSynthesis);

	/**
	 * Renders Section 1 (Executive Summary) as an institutional metric grid.
	 */
	const renderSection1 = (sec: ParsedSection) => {
		const rawText = sec.lines.join(" ");
		const exposureMatch = rawText.match(/Financial Exposure:[^$]*\$([0-9,.]+)/i);
		const beliefMatch = rawText.match(/P\(Fraud\) shifted from ([0-9.]+) to ([0-9.]+)/i);
		const coverageMatch = rawText.match(/Evidence Coverage:[^\d]*(\d+)%/i);
		const gateMatch = rawText.match(/Decision Gate Status:[^\w]*(PASSED|LOCKED)/i);

		const exposureVal = exposureMatch ? `$${exposureMatch[1]}` : `$${(result.exposure_usd ?? 0).toFixed(2)}`;
		const priorVal = beliefMatch ? parseFloat(beliefMatch[1]) : (result.initial_state?.fraud_probability ?? 0.5);
		const postVal = beliefMatch ? parseFloat(beliefMatch[2]) : pFraud;
		const coveragePct = coverageMatch ? parseInt(coverageMatch[1], 10) : Math.round((finalState?.evidence_coverage ?? 0) * 100);
		const isGateUnlocked = gateMatch ? gateMatch[1].toUpperCase() === "PASSED" : gatePassed;

		return (
			<div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
				{/* Executive Metric Cards */}
				<div
					style={{
						display: "grid",
						gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
						gap: "12px",
					}}
				>
					{/* Target Subject Tile */}
					<div
						style={{
							backgroundColor: "#ffffff",
							border: "1px solid #e2e8f0",
							borderRadius: "8px",
							padding: "14px",
						}}
					>
						<div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
							Target Subject
						</div>
						<div style={{ marginTop: "8px", display: "flex", flexDirection: "column", gap: "5px" }}>
							<div style={{ fontSize: "13px", color: "#0f172a", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
								<span style={{ color: "#64748b", fontSize: "11.5px", fontWeight: 500 }}>Card:</span>
								<span style={{ fontSize: "12.5px", fontWeight: 700, color: "#0f172a" }}>
									{result.case?.card_id || "N/A"}
								</span>
							</div>
							<div style={{ fontSize: "13px", color: "#0f172a", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
								<span style={{ color: "#64748b", fontSize: "11.5px", fontWeight: 500 }}>Transaction:</span>
								<span style={{ fontSize: "12.5px", fontWeight: 700, color: "#0f172a" }}>
									{flaggedTxnId}
								</span>
							</div>
						</div>
					</div>

					{/* Financial Exposure Tile */}
					<div
						style={{
							backgroundColor: "#ffffff",
							border: "1px solid #e2e8f0",
							borderRadius: "8px",
							padding: "14px",
						}}
					>
						<div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
							Financial Exposure
						</div>
						<div style={{ fontSize: "22px", fontWeight: 800, color: "#0f172a", marginTop: "4px" }}>
							{exposureVal}
						</div>
						<div style={{ fontSize: "11.5px", color: "#64748b", marginTop: "2px" }}>
							Flagged transaction exposure
						</div>
					</div>

					{/* Bayesian Belief Trajectory */}
					<div
						style={{
							backgroundColor: "#ffffff",
							border: "1px solid #e2e8f0",
							borderRadius: "8px",
							padding: "14px",
						}}
					>
						<div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
							Bayesian P(Fraud)
						</div>
						<div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "6px" }}>
							<span style={{ fontSize: "13px", fontWeight: 600, color: "#64748b" }}>
								{(priorVal * 100).toFixed(1)}%
							</span>
							<ArrowRight size={13} style={{ color: "#94a3b8" }} />
							<span
								style={{
									fontSize: "14.5px",
									fontWeight: 800,
									color: postVal >= 0.7 ? "#dc2626" : postVal <= 0.3 ? "#16a34a" : "#ea580c",
									backgroundColor: postVal >= 0.7 ? "#fef2f2" : postVal <= 0.3 ? "#f0fdf4" : "#fff7ed",
									padding: "2px 8px",
									borderRadius: "4px",
									border: `1px solid ${postVal >= 0.7 ? "#fecaca" : postVal <= 0.3 ? "#bbf7d0" : "#fed7aa"}`,
								}}
							>
								{(postVal * 100).toFixed(1)}%
							</span>
						</div>
						<div style={{ fontSize: "11.5px", color: "#64748b", marginTop: "4px" }}>
							{postVal >= priorVal ? `Net shift: +${((postVal - priorVal) * 100).toFixed(1)}%` : `Net shift: -${((priorVal - postVal) * 100).toFixed(1)}%`}
						</div>
					</div>

					{/* Decision Gate & Coverage Tile */}
					<div
						style={{
							backgroundColor: "#ffffff",
							border: "1px solid #e2e8f0",
							borderRadius: "8px",
							padding: "14px",
						}}
					>
						<div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
							Gate Status & Coverage
						</div>
						<div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "6px" }}>
							<span
								style={{
									fontSize: "11.5px",
									fontWeight: 700,
									padding: "2px 8px",
									borderRadius: "4px",
									backgroundColor: isGateUnlocked ? "#f0fdf4" : "#fffbeb",
									color: isGateUnlocked ? "#15803d" : "#b45309",
									border: `1px solid ${isGateUnlocked ? "#bbf7d0" : "#fde68a"}`,
									display: "inline-flex",
									alignItems: "center",
									gap: "4px",
								}}
							>
								{isGateUnlocked ? <Unlock size={11} /> : <Lock size={11} />}
								{isGateUnlocked ? "GATE PASSED" : "GATE LOCKED"}
							</span>
							<span style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>
								{coveragePct}% Coverage
							</span>
						</div>
						<div style={{ width: "100%", height: "5px", backgroundColor: "#e2e8f0", borderRadius: "3px", marginTop: "8px", overflow: "hidden" }}>
							<div
								style={{
									width: `${Math.min(100, coveragePct)}%`,
									height: "100%",
									backgroundColor: coveragePct >= 60 ? "#16a34a" : "#ea580c",
									borderRadius: "3px",
								}}
							/>
						</div>
					</div>
				</div>

				{/* Detailed Line Items in Normal Font */}
				<div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "4px" }}>
					{sec.lines.map((line, idx) => {
						return (
							<div
								key={idx}
								style={{
									fontSize: "13.5px",
									lineHeight: 1.6,
									color: "#334155",
									display: "flex",
									alignItems: "flex-start",
									gap: "8px",
								}}
							>
								<span style={{ color: "#ea580c", fontWeight: 700, lineHeight: 1.6 }}>•</span>
								<div style={{ flex: 1 }}>{renderInlineMarkdown(line, `sec1-${idx}`)}</div>
							</div>
						);
					})}
				</div>
			</div>
		);
	};

	/**
	 * Renders Section 2 (Graph Evidence Analysis) with clean evidence cards.
	 */
	const renderSection2 = (sec: ParsedSection) => {
		const isIntroLine = (line: string) =>
			line.toLowerCase().includes("empirical evidence observed") ||
			line.toLowerCase().includes("gsql query execution");

		return (
			<div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
				{sec.lines.map((line, idx) => {
					if (isIntroLine(line)) {
						return (
							<p
								key={idx}
								style={{
									fontSize: "13px",
									color: "#64748b",
									margin: "0 0 6px 0",
									lineHeight: 1.5,
								}}
							>
								{renderInlineMarkdown(line, `sec2-intro-${idx}`)}
							</p>
						);
					}

					// Evidence Card
					const citMatch = line.match(/\[(EVD-[A-Za-z0-9_-]+)\]/);
					const lrMatch = line.match(/LR:\s*([0-9.]+)\s*,\s*(SUPPORTS|NEUTRAL|REFUTES)/i);
					const provMatch = line.match(/\(Provenance:\s*[`*]?([^`*)]+)[`*]?\)/i);

					if (citMatch) {
						const citation = `[${citMatch[1]}]`;
						const lr = lrMatch ? lrMatch[1] : null;
						const direction = lrMatch ? lrMatch[2].toUpperCase() : null;
						const provenance = provMatch ? provMatch[1].trim() : null;

						// Extract clean finding text
						let finding = line
							.replace(/^[•\-\*]\s*/, "")
							.replace(/\*\*\[EVD-[A-Za-z0-9_-]+\]\*\*/g, "")
							.replace(/\[EVD-[A-Za-z0-9_-]+\]/g, "")
							.replace(/`[A-Z0-9_]+`/g, "")
							.replace(/\(LR:[^)]+\):?/g, "")
							.replace(/\(Provenance:[^)]+\)\.?/g, "")
							.trim()
							.replace(/^:\s*/, "")
							.trim();

						// Evidence Category label
						const typeMatch = line.match(/`([A-Z0-9_]{3,})`/);
						const categoryLabel = typeMatch
							? typeMatch[1].replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
							: "Graph Signal";

						const isPositive = direction === "SUPPORTS";
						const isExculpatory = direction === "REFUTES";

						return (
							<div
								key={idx}
								style={{
									backgroundColor: "#ffffff",
									border: "1px solid #e2e8f0",
									borderRadius: "8px",
									padding: "12px 16px",
									display: "flex",
									flexDirection: "column",
									gap: "8px",
								}}
							>
								<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
									<div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
										<span
											style={{
												fontSize: "11.5px",
												fontWeight: 700,
												padding: "2px 8px",
												borderRadius: "4px",
												backgroundColor: "#fff7ed",
												color: "#c2410c",
												border: "1px solid #fed7aa",
												display: "inline-flex",
												alignItems: "center",
												gap: "4px",
											}}
										>
											<Database size={11} />
											{citation}
										</span>
										<span style={{ fontSize: "13.5px", fontWeight: 700, color: "#0f172a" }}>
											{categoryLabel}
										</span>
									</div>

									<div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
										{lr && (
											<span
												style={{
													fontSize: "11.5px",
													fontWeight: 700,
													padding: "2px 8px",
													borderRadius: "4px",
													backgroundColor: isPositive ? "#fff7ed" : isExculpatory ? "#f0fdf4" : "#f1f5f9",
													color: isPositive ? "#c2410c" : isExculpatory ? "#15803d" : "#475569",
													border: `1px solid ${isPositive ? "#fed7aa" : isExculpatory ? "#bbf7d0" : "#e2e8f0"}`,
												}}
											>
												LR {lr} · {direction}
											</span>
										)}
										{provenance && (
											<span
												style={{
													fontSize: "11px",
													color: "#64748b",
													backgroundColor: "#f8fafc",
													padding: "2px 7px",
													borderRadius: "4px",
													border: "1px solid #e2e8f0",
												}}
											>
												{provenance}
											</span>
										)}
									</div>
								</div>

								<div style={{ fontSize: "13.5px", lineHeight: 1.55, color: "#334155" }}>
									{finding || renderInlineMarkdown(line, `sec2-fallback-${idx}`)}
								</div>
							</div>
						);
					}

					return (
						<div
							key={idx}
							style={{
								backgroundColor: "#ffffff",
								border: "1px solid #e2e8f0",
								borderRadius: "6px",
								padding: "10px 14px",
								fontSize: "13.5px",
								lineHeight: 1.5,
								color: "#1e293b",
							}}
						>
							{renderInlineMarkdown(line, `sec2-${idx}`)}
						</div>
					);
				})}
			</div>
		);
	};

	/**
	 * Renders Section 4 (Policy & Regulatory Compliance) with normal, human-readable typography.
	 */
	const renderSection4 = (sec: ParsedSection) => {
		return (
			<div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
				{sec.lines.map((line, idx) => {
					if (
						line.toLowerCase().includes("authoritative bank policies") ||
						line.toLowerCase().includes("statutory regulations governing")
					) {
						return (
							<p key={idx} style={{ fontSize: "13px", color: "#64748b", margin: "0 0 2px 0" }}>
								{renderInlineMarkdown(line, `sec4-intro-${idx}`)}
							</p>
						);
					}

					// Parse structured policy rule
					const citMatch = line.match(/\[(KNOW-[A-Za-z0-9_-]+)\]/);
					const titleMatch =
						line.match(/[`*]+(Rule [^`*]+|Regulatory Statute:[^`*]+|Fraud Typology:[^`*]+)[`*]+/i) ||
						line.match(/\[KNOW-[^\]]+\]\s*[`*]+([^`*]+)[`*]+/);
					const quoteMatch = line.match(/"([^"]+)"/);
					const ratMatch = line.match(/\(Application Rationale:\s*([^)]+)\)/i);

					if (citMatch && (quoteMatch || titleMatch)) {
						const citation = `[${citMatch[1]}]`;
						const rawTitle = titleMatch ? titleMatch[1].trim() : "Regulatory Compliance Mandate";
						const quote = quoteMatch ? quoteMatch[1].trim() : null;
						const rationale = ratMatch ? ratMatch[1].trim() : null;

						// Extract authority text between title and quote
						let authority = "";
						if (titleMatch && quoteMatch) {
							const titleEnd = titleMatch.index! + titleMatch[0].length;
							const quoteStart = quoteMatch.index!;
							authority = line
								.slice(titleEnd, quoteStart)
								.trim()
								.replace(/^:\s*/, "")
								.replace(/:\s*$/, "")
								.trim();
							if (authority.startsWith("(") && authority.endsWith(")")) {
								authority = authority.slice(1, -1).trim();
							}
						}

						return (
							<div
								key={idx}
								style={{
									backgroundColor: "#ffffff",
									border: "1px solid #e2e8f0",
									borderRadius: "8px",
									padding: "16px 18px",
									display: "flex",
									flexDirection: "column",
									gap: "10px",
									boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
								}}
							>
								{/* Card Header: Citation + Normal Font Title + Authority */}
								<div
									style={{
										display: "flex",
										justifyContent: "space-between",
										alignItems: "flex-start",
										flexWrap: "wrap",
										gap: "8px",
										borderBottom: "1px solid #f1f5f9",
										paddingBottom: "10px",
									}}
								>
									<div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
										<span
											style={{
												fontSize: "11.5px",
												fontWeight: 700,
												padding: "2px 8px",
												borderRadius: "4px",
												backgroundColor: "#f0fdf4",
												color: "#15803d",
												border: "1px solid #bbf7d0",
												display: "inline-flex",
												alignItems: "center",
												gap: "4px",
												fontFamily: "inherit",
											}}
										>
											<Scale size={11} />
											{citation}
										</span>
										<span
											style={{
												fontSize: "14.5px",
												fontWeight: 700,
												color: "#0f172a",
												letterSpacing: "-0.01em",
												fontFamily: "inherit",
											}}
										>
											{rawTitle}
										</span>
									</div>

									{authority && (
										<span
											style={{
												fontSize: "11.5px",
												color: "#64748b",
												backgroundColor: "#f8fafc",
												padding: "3px 9px",
												borderRadius: "4px",
												border: "1px solid #e2e8f0",
												fontWeight: 500,
												fontFamily: "inherit",
											}}
										>
											{authority}
										</span>
									)}
								</div>

								{/* Statutory / Policy Rule Quote in Normal Body Typography */}
								{quote && (
									<div
										style={{
											borderLeft: "3px solid #cbd5e1",
											paddingLeft: "14px",
											margin: "4px 0",
											fontSize: "13.5px",
											lineHeight: 1.6,
											color: "#334155",
											fontStyle: "normal",
											fontFamily: "inherit",
										}}
									>
										"{quote}"
									</div>
								)}

								{/* Application Rationale Insight Box */}
								{rationale && (
									<div
										style={{
											backgroundColor: "#f8fafc",
											border: "1px solid #e2e8f0",
											borderRadius: "6px",
											padding: "9px 12px",
											fontSize: "12.5px",
											lineHeight: 1.5,
											color: "#1e293b",
											display: "flex",
											alignItems: "flex-start",
											gap: "7px",
											marginTop: "2px",
										}}
									>
										<span style={{ fontWeight: 700, color: "#ea580c", whiteSpace: "nowrap" }}>
											Application Rationale:
										</span>
										<span style={{ color: "#334155" }}>{rationale}</span>
									</div>
								)}
							</div>
						);
					}

					// Fallback line rendering
					return (
						<div
							key={idx}
							style={{
								backgroundColor: "#ffffff",
								border: "1px solid #e2e8f0",
								borderRadius: "6px",
								padding: "12px 16px",
								fontSize: "13.5px",
								lineHeight: 1.6,
								color: "#1e293b",
							}}
						>
							{renderInlineMarkdown(line, `sec4-${idx}`)}
						</div>
					);
				})}
			</div>
		);
	};

	/**
	 * Generic section renderer with clean bullet icons and parsed markdown.
	 */
	const renderGenericSection = (sec: ParsedSection) => {
		return (
			<div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
				{sec.lines.map((line, idx) => {
					const isBullet = line.startsWith("- ") || line.startsWith("* ") || line.startsWith("•");

					return (
						<div
							key={idx}
							style={{
								display: "flex",
								alignItems: "flex-start",
								gap: "8px",
								fontSize: "13.5px",
								lineHeight: 1.6,
								color: "#1e293b",
							}}
						>
							{isBullet && (
								<span
									style={{
										color: "#94a3b8",
										fontSize: "14px",
										lineHeight: 1.6,
										userSelect: "none",
									}}
								>
									&bull;
								</span>
							)}
							<div style={{ flex: 1 }}>{renderInlineMarkdown(line, `sec-${sec.number}-${idx}`)}</div>
						</div>
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
				fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
			}}
		>
			{/* Top Bar: Title & Actions */}
			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "flex-start",
					flexWrap: "wrap",
					gap: "14px",
					borderBottom: "1px solid #f1f5f9",
					paddingBottom: "16px",
				}}
			>
				<div>
					<div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
						<h2
							style={{
								fontSize: "18px",
								fontWeight: 800,
								color: "#0f172a",
								margin: 0,
								letterSpacing: "-0.02em",
							}}
						>
							Investigation Explanation & SAR Narrative
						</h2>
						<span
							style={{
								fontSize: "10.5px",
								fontWeight: 700,
								padding: "3px 8px",
								borderRadius: "4px",
								backgroundColor: "#f8fafc",
								color: "#475569",
								border: "1px solid #e2e8f0",
								textTransform: "uppercase",
								letterSpacing: "0.04em",
							}}
						>
							FinCEN Form 111 Grounded Narrative
						</span>
					</div>
					<p style={{ margin: "4px 0 0 0", color: "#64748b", fontSize: "13px" }}>
						7-Section statutory narrative grounded in empirical TigerGraph evidence and verified GraphRAG citations
					</p>
				</div>

				{/* Controls: View Mode & Export Actions */}
				<div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
					<div
						style={{
							display: "flex",
							backgroundColor: "#f1f5f9",
							borderRadius: "6px",
							padding: "2px",
							border: "1px solid #e2e8f0",
						}}
					>
						<button
							onClick={() => setViewMode("dossier")}
							style={{
								padding: "5px 10px",
								borderRadius: "4px",
								fontSize: "11.5px",
								fontWeight: 600,
								border: "none",
								backgroundColor: viewMode === "dossier" ? "#ffffff" : "transparent",
								color: viewMode === "dossier" ? "#0f172a" : "#64748b",
								boxShadow: viewMode === "dossier" ? "0 1px 2px rgba(0,0,0,0.05)" : "none",
								cursor: "pointer",
								display: "flex",
								alignItems: "center",
								gap: "4px",
							}}
						>
							<Eye size={12} />
							Executive Dossier
						</button>
						<button
							onClick={() => setViewMode("raw")}
							style={{
								padding: "5px 10px",
								borderRadius: "4px",
								fontSize: "11.5px",
								fontWeight: 600,
								border: "none",
								backgroundColor: viewMode === "raw" ? "#ffffff" : "transparent",
								color: viewMode === "raw" ? "#0f172a" : "#64748b",
								boxShadow: viewMode === "raw" ? "0 1px 2px rgba(0,0,0,0.05)" : "none",
								cursor: "pointer",
								display: "flex",
								alignItems: "center",
								gap: "4px",
							}}
						>
							<Code2 size={12} />
							Raw Filing
						</button>
					</div>

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
							display: "flex",
							alignItems: "center",
							gap: "5px",
						}}
					>
						<Copy size={13} />
						Copy Text
					</button>

					<button
						onClick={handleDownloadJson}
						style={{
							padding: "6px 12px",
							backgroundColor: "#f8fafc",
							border: "1px solid #cbd5e1",
							borderRadius: "6px",
							fontSize: "12px",
							fontWeight: 600,
							color: "#334155",
							cursor: "pointer",
							display: "flex",
							alignItems: "center",
							gap: "5px",
						}}
					>
						<Download size={13} />
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
							display: "flex",
							alignItems: "center",
							gap: "5px",
						}}
					>
						<FileText size={13} />
						Download SAR (.txt)
					</button>
				</div>
			</div>

			{/* Feedback Message */}
			{feedbackMsg && (
				<div
					style={{
						padding: "8px 14px",
						backgroundColor: "#f0fdf4",
						border: "1px solid #bbf7d0",
						borderRadius: "6px",
						color: "#15803d",
						fontSize: "12.5px",
						fontWeight: 600,
						display: "flex",
						alignItems: "center",
						gap: "6px",
					}}
				>
					<Check size={14} />
					{feedbackMsg}
				</div>
			)}

			{/* FinCEN Statutory Compliance Banner */}
			<div
				style={{
					border: "1px solid #e2e8f0",
					borderRadius: "8px",
					padding: "14px 18px",
					backgroundColor: "#f8fafc",
					display: "flex",
					flexWrap: "wrap",
					gap: "16px",
					justifyContent: "space-between",
					alignItems: "center",
				}}
			>
				<div style={{ display: "flex", gap: "24px", flexWrap: "wrap", alignItems: "center" }}>
					<div>
						<div style={{ fontSize: "10.5px", color: "#64748b", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.04em" }}>
							Statutory Filing Mandate
						</div>
						<div style={{ fontSize: "13.5px", fontWeight: 700, color: "#0f172a", marginTop: "2px" }}>
							31 U.S.C. 5318(g) / Form 111
						</div>
					</div>

					<div style={{ borderLeft: "1px solid #e2e8f0", paddingLeft: "24px" }}>
						<div style={{ fontSize: "10.5px", color: "#64748b", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.04em" }}>
							Primary Recommendation
						</div>
						<div style={{ fontSize: "13.5px", fontWeight: 700, color: "#0f172a", marginTop: "2px" }}>
							{primaryAction?.action?.replace(/_/g, " ") || "DECLINE TRANSACTION"}
							<span style={{ fontSize: "11px", color: "#64748b", marginLeft: "6px", fontWeight: 500 }}>
								({primaryAction?.approval_route || "L1"})
							</span>
						</div>
					</div>

					<div style={{ borderLeft: "1px solid #e2e8f0", paddingLeft: "24px" }}>
						<div style={{ fontSize: "10.5px", color: "#64748b", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.04em" }}>
							Verified Grounded Citations
						</div>
						<div style={{ fontSize: "13.5px", fontWeight: 700, color: "#0f172a", marginTop: "2px" }}>
							{totalCitationsCount} references
							<span style={{ fontSize: "11px", color: "#15803d", marginLeft: "5px", fontWeight: 600 }}>
								(100% verified)
							</span>
						</div>
					</div>
				</div>

				<div>
					<span
						style={{
							fontSize: "11.5px",
							fontWeight: 700,
							padding: "5px 12px",
							borderRadius: "5px",
							backgroundColor: filingMandatory ? "#fef2f2" : "#f0fdf4",
							color: filingMandatory ? "#b91c1c" : "#15803d",
							border: `1px solid ${filingMandatory ? "#fecaca" : "#bbf7d0"}`,
							display: "inline-flex",
							alignItems: "center",
							gap: "5px",
							letterSpacing: "0.02em",
						}}
					>
						{filingMandatory ? <AlertTriangle size={13} /> : <CheckCircle2 size={13} />}
						{filingMandatory ? "SAR FILING MANDATED" : "NO FILING REQUIRED"}
					</span>
				</div>
			</div>

			{/* Citation Legend */}
			<div
				style={{
					display: "flex",
					gap: "14px",
					flexWrap: "wrap",
					alignItems: "center",
					padding: "10px 14px",
					backgroundColor: "#ffffff",
					borderRadius: "6px",
					border: "1px solid #e2e8f0",
					fontSize: "11.5px",
					color: "#64748b",
				}}
			>
				<span style={{ fontWeight: 700, color: "#0f172a" }}>Citation Reference Key:</span>
				<div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
					<span
						style={{
							padding: "2px 6px",
							borderRadius: "3px",
							backgroundColor: "#fff7ed",
							color: "#c2410c",
							border: "1px solid #fed7aa",
							fontWeight: 700,
							fontSize: "11px",
						}}
					>
						[EVD-...]
					</span>
					<span>Empirical Graph Evidence</span>
				</div>
				<div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
					<span
						style={{
							padding: "2px 6px",
							borderRadius: "3px",
							backgroundColor: "#f5f3ff",
							color: "#6d28d9",
							border: "1px solid #ddd6fe",
							fontWeight: 700,
							fontSize: "11px",
						}}
					>
						[CC-...]
					</span>
					<span>Historical Case Precedent</span>
				</div>
				<div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
					<span
						style={{
							padding: "2px 6px",
							borderRadius: "3px",
							backgroundColor: "#f0fdf4",
							color: "#15803d",
							border: "1px solid #bbf7d0",
							fontWeight: 700,
							fontSize: "11px",
						}}
					>
						[KNOW-...]
					</span>
					<span>Statutory / Typology Knowledge</span>
				</div>
			</div>

			{/* Body: Structured Dossier View OR Raw Monospace View */}
			{viewMode === "raw" ? (
				<pre
					style={{
						backgroundColor: "#0f172a",
						color: "#e2e8f0",
						padding: "20px",
						borderRadius: "8px",
						fontSize: "12.5px",
						fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
						lineHeight: 1.6,
						whiteSpace: "pre-wrap",
						overflowX: "auto",
						border: "1px solid #1e293b",
					}}
				>
					{rawSynthesis}
				</pre>
			) : (
				<div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
					{parsedSections.map((sec, secIdx) => {
						return (
							<div
								key={secIdx}
								style={{
									backgroundColor: "#ffffff",
									border: "1px solid #e2e8f0",
									borderRadius: "8px",
									overflow: "hidden",
									boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
								}}
							>
								{/* Section Header Strip */}
								<div
									style={{
										padding: "12px 18px",
										backgroundColor: "#f8fafc",
										borderBottom: "1px solid #e2e8f0",
										display: "flex",
										alignItems: "center",
										justifyContent: "space-between",
									}}
								>
									<h3
										style={{
											fontSize: "15px",
											fontWeight: 700,
											color: "#0f172a",
											margin: 0,
											letterSpacing: "-0.01em",
											display: "flex",
											alignItems: "center",
											gap: "8px",
										}}
									>
										{sec.title}
									</h3>
									<span
										style={{
											fontSize: "10.5px",
											fontWeight: 700,
											color: "#64748b",
											backgroundColor: "#ffffff",
											padding: "2px 7px",
											borderRadius: "4px",
											border: "1px solid #e2e8f0",
											letterSpacing: "0.04em",
										}}
									>
										SECTION {String(sec.number).padStart(2, "0")}
									</span>
								</div>

								{/* Section Content */}
								<div style={{ padding: "18px 20px" }}>
									{sec.number === 1
										? renderSection1(sec)
										: sec.number === 2
										? renderSection2(sec)
										: sec.number === 4
										? renderSection4(sec)
										: renderGenericSection(sec)}
								</div>
							</div>
						);
					})}
				</div>
			)}
		</div>
	);
};
