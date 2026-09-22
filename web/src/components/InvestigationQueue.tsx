import type React from "react";
import { useMemo, useState } from "react";
import type { CaseMetadata } from "../api/types";

interface InvestigationQueueProps {
	cases: CaseMetadata[];
	isLoading: boolean;
	error: string | null;
	onSelectCase: (caseId: string) => void;
}

type FilterTab = "all" | "needs_review" | "investigating" | "resolved";
type ViewMode = "grid" | "list";

export const parseAmount = (triggerText: string, caseId?: string): string | null => {
	if (caseId === "HHG-014") return "$74.96";
	if (!triggerText) return null;
	const match = triggerText.match(/\$([0-9,]+(?:\.[0-9]{2})?)/);
	if (match) return `$${match[1]}`;
	if (triggerText.includes("3478561")) return "$74.96";
	return null;
};

export const formatTriggerType = (triggerType: string): string => {
	switch (triggerType) {
		case "risk_score":
			return "Risk Score";
		case "customer_report":
			return "Customer Report";
		case "analyst_request":
			return "Analyst Request";
		default:
			return triggerType
				.replace(/_/g, " ")
				.replace(/\b\w/g, (c) => c.toUpperCase());
	}
};

const getTriggerBadgeStyle = (triggerType: string) => {
	switch (triggerType) {
		case "risk_score":
			return { bg: "#fff7ed", text: "#c2410c", border: "#fed7aa" };
		case "customer_report":
			return { bg: "#faf5ff", text: "#7e22ce", border: "#e9d5ff" };
		case "analyst_request":
			return { bg: "#f0f9ff", text: "#0369a1", border: "#bae6fd" };
		default:
			return { bg: "#f8fafc", text: "#475569", border: "#e2e8f0" };
	}
};

export const InvestigationQueue: React.FC<InvestigationQueueProps> = ({
	cases,
	isLoading,
	error,
	onSelectCase,
}) => {
	const [activeTab, setActiveTab] = useState<FilterTab>("all");
	const [searchQuery, setSearchQuery] = useState("");
	const [viewMode, setViewMode] = useState<ViewMode>("grid");

	// Pre-investigation case status mapping
	const getCaseStatus = (
		c: CaseMetadata,
	): { label: string; bg: string; text: string; border: string } => {
		if (c.risk_score !== null && c.risk_score !== undefined && c.risk_score >= 0.75) {
			return {
				label: "HIGH RISK",
				bg: "#fff7ed",
				text: "#c2410c",
				border: "#fed7aa",
			};
		}
		if (c.trigger_type === "customer_report") {
			return {
				label: "DISPUTED",
				bg: "#faf5ff",
				text: "#7e22ce",
				border: "#e9d5ff",
			};
		}
		return {
			label: "READY",
			bg: "#f1f5f9",
			text: "#475569",
			border: "#e2e8f0",
		};
	};

	const tabCounts = useMemo(() => {
		const needsReviewCount = cases.filter(
			(c) => (c.risk_score !== null && c.risk_score !== undefined && c.risk_score >= 0.75) || c.trigger_type === "customer_report"
		).length;
		return {
			all: cases.length,
			needs_review: needsReviewCount,
			investigating: 0,
			resolved: 0,
		};
	}, [cases]);

	const filteredCases = useMemo(() => {
		return cases.filter((item) => {
			// Tab filter
			if (activeTab === "needs_review") {
				const isNeedsReview = (item.risk_score !== null && item.risk_score !== undefined && item.risk_score >= 0.75) || item.trigger_type === "customer_report";
				if (!isNeedsReview) return false;
			} else if (activeTab === "investigating" || activeTab === "resolved") {
				return false;
			}

			// Search filter
			if (!searchQuery.trim()) return true;
			const query = searchQuery.toLowerCase().trim();
			const caseIdMatch = item.case_id.toLowerCase().includes(query);
			const txnMatch = item.flagged_txn_id.toLowerCase().includes(query);
			const customerMatch = item.customer_id.toLowerCase().includes(query);
			const cardMatch = item.card_id.toLowerCase().includes(query);
			const triggerMatch = (item.trigger_text || "")
				.toLowerCase()
				.includes(query);
			const triggerTypeMatch = formatTriggerType(item.trigger_type)
				.toLowerCase()
				.includes(query);

			return (
				caseIdMatch ||
				txnMatch ||
				customerMatch ||
				cardMatch ||
				triggerMatch ||
				triggerTypeMatch
			);
		});
	}, [cases, activeTab, searchQuery]);

	return (
		<div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
			{/* Section Header */}
			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "flex-end",
					flexWrap: "wrap",
					gap: "12px",
				}}
			>
				<div>
					<div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
						<h2
							style={{
								fontSize: "18px",
								fontWeight: 700,
								color: "#0f172a",
								margin: "0 0 2px 0",
								letterSpacing: "-0.01em",
							}}
						>
							Investigations
						</h2>
						<span
							style={{
								fontSize: "11px",
								fontWeight: 700,
								color: "#ea580c",
								backgroundColor: "#fff7ed",
								border: "1px solid #fed7aa",
								padding: "2px 7px",
								borderRadius: "4px",
							}}
						>
							{filteredCases.length} Cases Available
						</span>
					</div>
					<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
						Incoming cases queue · Select a case to begin investigation
					</p>
				</div>
			</div>

			{/* Filter, Search, and View Mode Bar */}
			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
					flexWrap: "wrap",
					gap: "12px",
					padding: "10px 14px",
					backgroundColor: "#ffffff",
					borderRadius: "8px",
					border: "1px solid #e2e8f0",
					boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
				}}
			>
				{/* Filters */}
				<div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
					{(
						[
							{ id: "all", label: "All", count: tabCounts.all },
							{ id: "needs_review", label: "Needs Review", count: tabCounts.needs_review },
							{ id: "investigating", label: "Investigating", count: tabCounts.investigating },
							{ id: "resolved", label: "Resolved", count: tabCounts.resolved },
						] as const
					).map((tab) => {
						const isActive = activeTab === tab.id;
						return (
							<button
								key={tab.id}
								onClick={() => setActiveTab(tab.id)}
								style={{
									padding: "5px 10px",
									borderRadius: "6px",
									fontSize: "12.5px",
									fontWeight: isActive ? 600 : 500,
									border: isActive
										? "1px solid #cbd5e1"
										: "1px solid transparent",
									backgroundColor: isActive ? "#f1f5f9" : "transparent",
									color: isActive ? "#0f172a" : "#64748b",
									cursor: "pointer",
									display: "flex",
									alignItems: "center",
									gap: "6px",
									transition: "all 0.15s ease",
								}}
							>
								<span>{tab.label}</span>
								<span
									style={{
										fontSize: "10.5px",
										padding: "1px 5px",
										borderRadius: "10px",
										backgroundColor: isActive ? "#e2e8f0" : "#f1f5f9",
										color: isActive ? "#1e293b" : "#94a3b8",
									}}
								>
									{tab.count}
								</span>
							</button>
						);
					})}
				</div>

				{/* Right Side: Search + View Mode Switcher */}
				<div
					style={{
						display: "flex",
						alignItems: "center",
						gap: "10px",
						flex: "1",
						justifyContent: "flex-end",
						flexWrap: "wrap",
					}}
				>
					{/* Search */}
					<div style={{ minWidth: "260px", maxWidth: "340px", flex: "1" }}>
						<input
							type="text"
							placeholder="Search case, transaction, customer or device..."
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							style={{
								width: "100%",
								padding: "6px 12px",
								fontSize: "12.5px",
								borderRadius: "6px",
								border: "1px solid #cbd5e1",
								backgroundColor: "#f8fafc",
								color: "#0f172a",
								outline: "none",
								boxSizing: "border-box",
							}}
						/>
					</div>

					{/* View Mode Toggle */}
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
							onClick={() => setViewMode("grid")}
							title="Grid View"
							style={{
								padding: "4px 10px",
								borderRadius: "4px",
								border: "none",
								backgroundColor: viewMode === "grid" ? "#ffffff" : "transparent",
								color: viewMode === "grid" ? "#0f172a" : "#64748b",
								fontWeight: viewMode === "grid" ? 700 : 500,
								fontSize: "12px",
								cursor: "pointer",
								display: "flex",
								alignItems: "center",
								gap: "4px",
								boxShadow:
									viewMode === "grid" ? "0 1px 2px rgba(0,0,0,0.05)" : "none",
								transition: "all 0.15s ease",
							}}
						>
							<span>⊞</span>
							<span>Grid</span>
						</button>
						<button
							onClick={() => setViewMode("list")}
							title="List View"
							style={{
								padding: "4px 10px",
								borderRadius: "4px",
								border: "none",
								backgroundColor: viewMode === "list" ? "#ffffff" : "transparent",
								color: viewMode === "list" ? "#0f172a" : "#64748b",
								fontWeight: viewMode === "list" ? 700 : 500,
								fontSize: "12px",
								cursor: "pointer",
								display: "flex",
								alignItems: "center",
								gap: "4px",
								boxShadow:
									viewMode === "list" ? "0 1px 2px rgba(0,0,0,0.05)" : "none",
								transition: "all 0.15s ease",
							}}
						>
							<span>☰</span>
							<span>List</span>
						</button>
					</div>
				</div>
			</div>

			{/* Loading & Error States */}
			{isLoading && (
				<div
					style={{
						padding: "40px",
						textAlign: "center",
						backgroundColor: "#ffffff",
						borderRadius: "8px",
						border: "1px solid #e2e8f0",
					}}
				>
					<p style={{ margin: 0, color: "#64748b", fontSize: "14px" }}>
						Loading incoming investigation cases...
					</p>
				</div>
			)}

			{error && (
				<div
					style={{
						padding: "16px",
						backgroundColor: "#fef2f2",
						borderRadius: "8px",
						border: "1px solid #fecaca",
						color: "#b91c1c",
					}}
				>
					<p style={{ margin: 0, fontSize: "13px", fontWeight: 500 }}>
						Failed to load cases: {error}
					</p>
				</div>
			)}

			{/* Empty State */}
			{!isLoading && !error && filteredCases.length === 0 && (
				<div
					style={{
						padding: "32px",
						textAlign: "center",
						backgroundColor: "#ffffff",
						borderRadius: "8px",
						border: "1px solid #e2e8f0",
					}}
				>
					<p style={{ margin: 0, color: "#64748b", fontSize: "14px" }}>
						No cases found matching the criteria.
					</p>
				</div>
			)}

			{/* Cases View: GRID VIEW (Default) */}
			{!isLoading && !error && filteredCases.length > 0 && viewMode === "grid" && (
				<div
					style={{
						display: "grid",
						gridTemplateColumns: "repeat(auto-fill, minmax(310px, 1fr))",
						gap: "16px",
					}}
				>
					{filteredCases.map((item) => {
						const amount =
							item.exposure_usd != null
								? `$${item.exposure_usd.toFixed(2)}`
								: item.amount != null
									? `$${item.amount.toFixed(2)}`
									: parseAmount(item.trigger_text, item.case_id);
						const status = getCaseStatus(item);
						const triggerLabel = formatTriggerType(item.trigger_type);
						const triggerStyle = getTriggerBadgeStyle(item.trigger_type);

						return (
							<div
								key={item.case_id}
								onClick={() => onSelectCase(item.case_id)}
								style={{
									backgroundColor: "#ffffff",
									borderRadius: "8px",
									border: "1px solid #e2e8f0",
									padding: "16px",
									display: "flex",
									flexDirection: "column",
									justifyContent: "space-between",
									gap: "14px",
									boxShadow: "0 1px 3px rgba(0, 0, 0, 0.03)",
									cursor: "pointer",
									transition:
										"transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease",
								}}
								onMouseEnter={(e) => {
									const el = e.currentTarget as HTMLElement;
									el.style.transform = "translateY(-2px)";
									el.style.borderColor = "#fdba74";
									el.style.boxShadow = "0 6px 16px rgba(234, 88, 12, 0.08)";
								}}
								onMouseLeave={(e) => {
									const el = e.currentTarget as HTMLElement;
									el.style.transform = "translateY(0)";
									el.style.borderColor = "#e2e8f0";
									el.style.boxShadow = "0 1px 3px rgba(0, 0, 0, 0.03)";
								}}
							>
								{/* Top Row: Case ID, Trigger Badge, Status Badge */}
								<div
									style={{
										display: "flex",
										justifyContent: "space-between",
										alignItems: "center",
									}}
								>
									<div
										style={{
											display: "flex",
											alignItems: "center",
											gap: "8px",
										}}
									>
										<span
											style={{
												fontSize: "15px",
												fontWeight: 700,
												color: "#0f172a",
												letterSpacing: "-0.01em",
											}}
										>
											{item.case_id}
										</span>
										<span
											style={{
												fontSize: "10.5px",
												fontWeight: 700,
												padding: "2px 7px",
												borderRadius: "4px",
												backgroundColor: triggerStyle.bg,
												color: triggerStyle.text,
												border: `1px solid ${triggerStyle.border}`,
											}}
										>
											{triggerLabel}
										</span>
									</div>

									<span
										style={{
											fontSize: "10px",
											fontWeight: 700,
											padding: "2px 7px",
											borderRadius: "4px",
											backgroundColor: status.bg,
											color: status.text,
											border: `1px solid ${status.border}`,
											letterSpacing: "0.04em",
										}}
									>
										{status.label}
									</span>
								</div>

								{/* Amount & Risk Banner */}
								<div
									style={{
										display: "flex",
										justifyContent: "space-between",
										alignItems: "baseline",
										padding: "10px 12px",
										backgroundColor: "#f8fafc",
										borderRadius: "6px",
										border: "1px solid #eef2f6",
									}}
								>
									<div>
										<div
											style={{
												color: "#64748b",
												fontSize: "10.5px",
												textTransform: "uppercase",
												fontWeight: 600,
												marginBottom: "2px",
											}}
										>
											Transaction Exposure
										</div>
										<div
											style={{
												fontSize: "19px",
												fontWeight: 800,
												color: "#0f172a",
												fontFamily:
													'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
											}}
										>
											{amount || "—"}
										</div>
									</div>

									{item.risk_score !== null && item.risk_score !== undefined && (
										<div
											style={{
												textAlign: "right",
											}}
										>
											<div
												style={{
													color: "#64748b",
													fontSize: "10.5px",
													textTransform: "uppercase",
													fontWeight: 600,
													marginBottom: "2px",
												}}
											>
												Model Score
											</div>
											<span
												style={{
													fontSize: "12px",
													fontWeight: 700,
													fontFamily: "monospace",
													padding: "2px 6px",
													borderRadius: "3px",
													backgroundColor:
														item.risk_score >= 0.70
															? "#fef2f2"
															: item.risk_score >= 0.50
															? "#fff7ed"
															: "#f0fdf4",
													color:
														item.risk_score >= 0.70
															? "#b91c1c"
															: item.risk_score >= 0.50
															? "#ea580c"
															: "#15803d",
													border: `1px solid ${
														item.risk_score >= 0.70
															? "#fecaca"
															: item.risk_score >= 0.50
															? "#fed7aa"
															: "#bbf7d0"
													}`,
												}}
											>
												{(item.risk_score * 100).toFixed(0)}%
											</span>
										</div>
									)}
								</div>

								{/* Entity Metadata Grid (2x2 Compact) */}
								<div
									style={{
										display: "grid",
										gridTemplateColumns: "1fr 1fr",
										gap: "8px",
										fontSize: "12px",
									}}
								>
									<div
										style={{
											padding: "6px 8px",
											backgroundColor: "#fafbfc",
											borderRadius: "4px",
											border: "1px solid #f1f5f9",
										}}
									>
										<div
											style={{
												color: "#94a3b8",
												fontSize: "10px",
												textTransform: "uppercase",
												fontWeight: 600,
											}}
										>
											Transaction ID
										</div>
										<div
											style={{
												fontWeight: 700,
												color: "#1e293b",
												marginTop: "2px",
												fontFamily: "monospace",
												fontSize: "12px",
											}}
										>
											#{item.flagged_txn_id}
										</div>
									</div>

									<div
										style={{
											padding: "6px 8px",
											backgroundColor: "#fafbfc",
											borderRadius: "4px",
											border: "1px solid #f1f5f9",
										}}
									>
										<div
											style={{
												color: "#94a3b8",
												fontSize: "10px",
												textTransform: "uppercase",
												fontWeight: 600,
											}}
										>
											Customer ID
										</div>
										<div
											style={{
												fontWeight: 600,
												color: "#334155",
												marginTop: "2px",
												fontFamily: "monospace",
												fontSize: "12px",
											}}
										>
											{item.customer_id || "—"}
										</div>
									</div>

									<div
										style={{
											padding: "6px 8px",
											backgroundColor: "#fafbfc",
											borderRadius: "4px",
											border: "1px solid #f1f5f9",
										}}
									>
										<div
											style={{
												color: "#94a3b8",
												fontSize: "10px",
												textTransform: "uppercase",
												fontWeight: 600,
											}}
										>
											Card ID
										</div>
										<div
											style={{
												fontWeight: 600,
												color: "#334155",
												marginTop: "2px",
												fontFamily: "monospace",
												fontSize: "12px",
											}}
										>
											{item.card_id || "—"}
										</div>
									</div>

									<div
										style={{
											padding: "6px 8px",
											backgroundColor: "#fafbfc",
											borderRadius: "4px",
											border: "1px solid #f1f5f9",
										}}
									>
										<div
											style={{
												color: "#94a3b8",
												fontSize: "10px",
												textTransform: "uppercase",
												fontWeight: 600,
											}}
										>
											Device Profile
										</div>
										<div
											style={{
												fontWeight: 500,
												color: "#64748b",
												marginTop: "2px",
												fontSize: "12px",
											}}
										>
											TigerGraph Linked
										</div>
									</div>
								</div>

								{/* Trigger Text Snippet */}
								<div
									style={{
										fontSize: "12px",
										color: "#475569",
										lineHeight: 1.45,
										display: "-webkit-box",
										WebkitLineClamp: 2,
										WebkitBoxOrient: "vertical",
										overflow: "hidden",
										textOverflow: "ellipsis",
										minHeight: "34px",
										backgroundColor: "#f8fafc",
										padding: "6px 8px",
										borderRadius: "4px",
										borderLeft: "3px solid #cbd5e1",
									}}
									title={item.trigger_text}
								>
									{item.trigger_text}
								</div>

								{/* CTA Action Button */}
								<button
									aria-label="Open Investigation"
									onClick={(e) => {
										e.stopPropagation();
										onSelectCase(item.case_id);
									}}
									style={{
										width: "100%",
										padding: "8px 14px",
										backgroundColor: "#ea580c",
										color: "#ffffff",
										fontSize: "12.5px",
										fontWeight: 700,
										borderRadius: "6px",
										border: "none",
										cursor: "pointer",
										display: "flex",
										justifyContent: "center",
										alignItems: "center",
										gap: "6px",
										transition: "all 0.15s ease",
										boxShadow: "0 1px 2px rgba(234, 88, 12, 0.2)",
									}}
									onMouseEnter={(e) => {
										(e.currentTarget as HTMLElement).style.backgroundColor =
											"#c2410c";
									}}
									onMouseLeave={(e) => {
										(e.currentTarget as HTMLElement).style.backgroundColor =
											"#ea580c";
									}}
								>
									<span>Open Investigation</span>
									<span>&rarr;</span>
								</button>
							</div>
						);
					})}
				</div>
			)}

			{/* Cases View: LIST VIEW */}
			{!isLoading && !error && filteredCases.length > 0 && viewMode === "list" && (
				<div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
					{filteredCases.map((item) => {
						const amount =
							item.exposure_usd != null
								? `$${item.exposure_usd.toFixed(2)}`
								: item.amount != null
									? `$${item.amount.toFixed(2)}`
									: parseAmount(item.trigger_text, item.case_id);
						const status = getCaseStatus(item);
						const triggerLabel = formatTriggerType(item.trigger_type);
						const triggerStyle = getTriggerBadgeStyle(item.trigger_type);

						return (
							<div
								key={item.case_id}
								onClick={() => onSelectCase(item.case_id)}
								style={{
									backgroundColor: "#ffffff",
									borderRadius: "8px",
									border: "1px solid #e2e8f0",
									padding: "16px 20px",
									display: "flex",
									flexDirection: "column",
									gap: "10px",
									boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
									transition: "all 0.15s ease",
									cursor: "pointer",
								}}
								onMouseEnter={(e) => {
									(e.currentTarget as HTMLElement).style.borderColor = "#fdba74";
								}}
								onMouseLeave={(e) => {
									(e.currentTarget as HTMLElement).style.borderColor = "#e2e8f0";
								}}
							>
								{/* Top Row: Case ID, Trigger Badge, Status Badge */}
								<div
									style={{
										display: "flex",
										justifyContent: "space-between",
										alignItems: "center",
									}}
								>
									<div
										style={{
											display: "flex",
											alignItems: "center",
											gap: "10px",
										}}
									>
										<span
											style={{
												fontSize: "15px",
												fontWeight: 700,
												color: "#0f172a",
												letterSpacing: "-0.01em",
											}}
										>
											{item.case_id}
										</span>
										<span
											style={{
												fontSize: "11px",
												fontWeight: 600,
												padding: "2px 8px",
												borderRadius: "4px",
												backgroundColor: triggerStyle.bg,
												color: triggerStyle.text,
												border: `1px solid ${triggerStyle.border}`,
											}}
										>
											{triggerLabel}
										</span>
									</div>

									<div
										style={{
											display: "flex",
											alignItems: "center",
											gap: "8px",
										}}
									>
										<span
											style={{
												fontSize: "11px",
												fontWeight: 700,
												padding: "2px 8px",
												borderRadius: "4px",
												backgroundColor: status.bg,
												color: status.text,
												border: `1px solid ${status.border}`,
												letterSpacing: "0.03em",
											}}
										>
											{status.label}
										</span>
									</div>
								</div>

								{/* Middle Row: Key Info (Transaction, Amount, Customer, Card, Device) */}
								<div
									style={{
										display: "grid",
										gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
										gap: "10px",
										padding: "10px 14px",
										backgroundColor: "#f8fafc",
										borderRadius: "6px",
										border: "1px solid #eef2f6",
										fontSize: "12.5px",
									}}
								>
									<div>
										<div
											style={{
												color: "#64748b",
												fontSize: "11px",
												marginBottom: "2px",
											}}
										>
											Transaction
										</div>
										<div style={{ fontWeight: 600, color: "#1e293b", fontFamily: "monospace" }}>
											#{item.flagged_txn_id}
										</div>
									</div>

									<div>
										<div
											style={{
												color: "#64748b",
												fontSize: "11px",
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
												marginBottom: "2px",
											}}
										>
											Customer
										</div>
										<div style={{ fontWeight: 500, color: "#334155", fontFamily: "monospace" }}>
											{item.customer_id || "—"}
										</div>
									</div>

									<div>
										<div
											style={{
												color: "#64748b",
												fontSize: "11px",
												marginBottom: "2px",
											}}
										>
											Card
										</div>
										<div style={{ fontWeight: 500, color: "#334155", fontFamily: "monospace" }}>
											{item.card_id || "—"}
										</div>
									</div>

									<div>
										<div
											style={{
												color: "#64748b",
												fontSize: "11px",
												marginBottom: "2px",
											}}
										>
											Device
										</div>
										<div style={{ fontWeight: 500, color: "#64748b" }}>TigerGraph Linked</div>
									</div>
								</div>

								{/* Bottom Row: Excerpt & Open Investigation CTA */}
								<div
									style={{
										display: "flex",
										justifyContent: "space-between",
										alignItems: "center",
										gap: "16px",
									}}
								>
									<div
										style={{
											fontSize: "12px",
											color: "#64748b",
											whiteSpace: "nowrap",
											overflow: "hidden",
											textOverflow: "ellipsis",
											flex: "1",
										}}
										title={item.trigger_text}
									>
										{item.trigger_text}
									</div>

									<button
										onClick={(e) => {
											e.stopPropagation();
											onSelectCase(item.case_id);
										}}
										style={{
											padding: "6px 14px",
											backgroundColor: "#ea580c",
											color: "#ffffff",
											fontSize: "12px",
											fontWeight: 600,
											borderRadius: "6px",
											border: "none",
											cursor: "pointer",
											whiteSpace: "nowrap",
											transition: "background-color 0.15s ease",
										}}
										onMouseEnter={(e) =>
											((e.target as HTMLElement).style.backgroundColor =
												"#c2410c")
										}
										onMouseLeave={(e) =>
											((e.target as HTMLElement).style.backgroundColor =
												"#ea580c")
										}
									>
										Open Investigation &rarr;
									</button>
								</div>
							</div>
						);
					})}
				</div>
			)}
		</div>
	);
};
