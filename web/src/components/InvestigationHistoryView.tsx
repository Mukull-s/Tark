import React, { useState, useEffect } from "react";
import type { InvestigationHistoryItem } from "../api/types";
import { fetchInvestigationHistory } from "../api/client";
import {
	Search,
	Clock,
	ArrowRight,
	ExternalLink,
	RefreshCw,
} from "lucide-react";

interface InvestigationHistoryViewProps {
	onSelectCase: (caseId: string) => void;
	onOpenNewInvestigation: () => void;
}

export const InvestigationHistoryView: React.FC<InvestigationHistoryViewProps> = ({
	onSelectCase,
	onOpenNewInvestigation,
}) => {
	const [history, setHistory] = useState<InvestigationHistoryItem[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [searchTerm, setSearchTerm] = useState("");
	const [filterVerdict, setFilterVerdict] = useState<string>("ALL");

	const loadHistory = () => {
		setIsLoading(true);
		setError(null);
		fetchInvestigationHistory()
			.then((data) => {
				setHistory(data);
				setIsLoading(false);
			})
			.catch((err) => {
				setError(err instanceof Error ? err.message : "Failed to load history");
				setIsLoading(false);
			});
	};

	useEffect(() => {
		loadHistory();
	}, []);

	// Filter history items
	const filteredHistory = history.filter((item) => {
		const matchesSearch =
			searchTerm === "" ||
			item.case_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
			item.flagged_txn_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
			item.card_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
			item.primary_action.toLowerCase().includes(searchTerm.toLowerCase());

		const matchesVerdict =
			filterVerdict === "ALL" ||
			(filterVerdict === "FRAUD" && item.verdict.toLowerCase().includes("fraud")) ||
			(filterVerdict === "CLEARED" && (item.verdict.toLowerCase().includes("legit") || item.verdict.toLowerCase().includes("cleared"))) ||
			(filterVerdict === "UNCERTAIN" && item.verdict.toLowerCase().includes("uncertain"));

		return matchesSearch && matchesVerdict;
	});

	// Metrics
	const totalCases = history.length;
	const fraudCount = history.filter((h) => h.verdict.toLowerCase().includes("fraud")).length;
	const totalExposure = history.reduce((sum, h) => sum + (h.exposure_usd || 0), 0);
	const sarCount = history.filter((h) => h.sar_mandated).length;

	return (
		<div
			style={{
				padding: "24px 28px",
				display: "flex",
				flexDirection: "column",
				gap: "20px",
				fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
				maxWidth: "1400px",
				margin: "0 auto",
				width: "100%",
			}}
		>
			{/* Top Header */}
			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "flex-start",
					flexWrap: "wrap",
					gap: "14px",
					borderBottom: "1px solid #e2e8f0",
					paddingBottom: "16px",
				}}
			>
				<div>
					<div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
						<h1
							style={{
								fontSize: "20px",
								fontWeight: 800,
								color: "#0f172a",
								margin: 0,
								letterSpacing: "-0.02em",
							}}
						>
							Investigation History & Session Audit Log
						</h1>
						<span
							style={{
								fontSize: "11px",
								fontWeight: 700,
								padding: "3px 8px",
								borderRadius: "4px",
								backgroundColor: "#f1f5f9",
								color: "#475569",
								border: "1px solid #e2e8f0",
							}}
						>
							{totalCases} Cases Logged
						</span>
					</div>
					<p style={{ margin: "4px 0 0 0", color: "#64748b", fontSize: "13px" }}>
						Chronological audit trail of all autonomous investigations, arbitrary transaction lookups, and analyst resolutions.
					</p>
				</div>

				<div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
					<button
						onClick={loadHistory}
						style={{
							padding: "7px 12px",
							backgroundColor: "#ffffff",
							border: "1px solid #cbd5e1",
							borderRadius: "6px",
							fontSize: "12.5px",
							fontWeight: 600,
							color: "#334155",
							cursor: "pointer",
							display: "flex",
							alignItems: "center",
							gap: "6px",
						}}
					>
						<RefreshCw size={13} />
						Refresh
					</button>

					<button
						onClick={onOpenNewInvestigation}
						style={{
							padding: "7px 14px",
							backgroundColor: "#ea580c",
							border: "none",
							borderRadius: "6px",
							fontSize: "12.5px",
							fontWeight: 600,
							color: "#ffffff",
							cursor: "pointer",
							display: "flex",
							alignItems: "center",
							gap: "6px",
						}}
					>
						+ New Investigation
					</button>
				</div>
			</div>

			{/* KPI Summary Tiles */}
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
					gap: "14px",
				}}
			>
				<div
					style={{
						backgroundColor: "#ffffff",
						border: "1px solid #e2e8f0",
						borderRadius: "8px",
						padding: "14px 16px",
						boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
					}}
				>
					<div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
						Total Investigated
					</div>
					<div style={{ fontSize: "22px", fontWeight: 800, color: "#0f172a", marginTop: "4px" }}>
						{totalCases}
					</div>
					<div style={{ fontSize: "11.5px", color: "#64748b", marginTop: "2px" }}>
						Session cases & lookups
					</div>
				</div>

				<div
					style={{
						backgroundColor: "#ffffff",
						border: "1px solid #e2e8f0",
						borderRadius: "8px",
						padding: "14px 16px",
						boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
					}}
				>
					<div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
						Confirmed Fraud
					</div>
					<div style={{ fontSize: "22px", fontWeight: 800, color: "#dc2626", marginTop: "4px" }}>
						{fraudCount}
					</div>
					<div style={{ fontSize: "11.5px", color: "#64748b", marginTop: "2px" }}>
						{totalCases > 0 ? `${((fraudCount / totalCases) * 100).toFixed(0)}% of total` : "0%"}
					</div>
				</div>

				<div
					style={{
						backgroundColor: "#ffffff",
						border: "1px solid #e2e8f0",
						borderRadius: "8px",
						padding: "14px 16px",
						boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
					}}
				>
					<div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
						Audited Exposure
					</div>
					<div style={{ fontSize: "22px", fontWeight: 800, color: "#0f172a", marginTop: "4px" }}>
						${totalExposure.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
					</div>
					<div style={{ fontSize: "11.5px", color: "#64748b", marginTop: "2px" }}>
						Cumulative portfolio risk
					</div>
				</div>

				<div
					style={{
						backgroundColor: "#ffffff",
						border: "1px solid #e2e8f0",
						borderRadius: "8px",
						padding: "14px 16px",
						boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
					}}
				>
					<div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
						FinCEN SAR Mandates
					</div>
					<div style={{ fontSize: "22px", fontWeight: 800, color: "#ea580c", marginTop: "4px" }}>
						{sarCount}
					</div>
					<div style={{ fontSize: "11.5px", color: "#64748b", marginTop: "2px" }}>
						Form 111 filings generated
					</div>
				</div>
			</div>

			{/* Search & Filter Controls */}
			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
					flexWrap: "wrap",
					gap: "12px",
					backgroundColor: "#ffffff",
					border: "1px solid #e2e8f0",
					borderRadius: "8px",
					padding: "12px 16px",
				}}
			>
				{/* Search Input */}
				<div
					style={{
						display: "flex",
						alignItems: "center",
						gap: "8px",
						backgroundColor: "#f8fafc",
						border: "1px solid #cbd5e1",
						borderRadius: "6px",
						padding: "6px 10px",
						width: "320px",
					}}
				>
					<Search size={14} style={{ color: "#64748b" }} />
					<input
						type="text"
						value={searchTerm}
						onChange={(e) => setSearchTerm(e.target.value)}
						placeholder="Search by Case ID, Card, Txn..."
						style={{
							border: "none",
							backgroundColor: "transparent",
							fontSize: "13px",
							color: "#0f172a",
							width: "100%",
							outline: "none",
						}}
					/>
				</div>

				{/* Verdict Filter Buttons */}
				<div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
					<span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600, marginRight: "4px" }}>
						Verdict:
					</span>
					{["ALL", "FRAUD", "CLEARED", "UNCERTAIN"].map((v) => {
						const isActive = filterVerdict === v;
						return (
							<button
								key={v}
								onClick={() => setFilterVerdict(v)}
								style={{
									padding: "4px 10px",
									borderRadius: "5px",
									fontSize: "11.5px",
									fontWeight: isActive ? 700 : 500,
									border: `1px solid ${isActive ? "#ea580c" : "#e2e8f0"}`,
									backgroundColor: isActive ? "#fff7ed" : "#ffffff",
									color: isActive ? "#c2410c" : "#64748b",
									cursor: "pointer",
								}}
							>
								{v}
							</button>
						);
					})}
				</div>
			</div>

			{/* History Table */}
			{isLoading ? (
				<div style={{ padding: "40px", textAlign: "center", color: "#64748b", fontSize: "13.5px" }}>
					Loading investigation audit history...
				</div>
			) : error ? (
				<div style={{ padding: "20px", backgroundColor: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", color: "#b91c1c", fontSize: "13px" }}>
					{error}
				</div>
			) : filteredHistory.length === 0 ? (
				<div
					style={{
						padding: "48px 24px",
						textAlign: "center",
						backgroundColor: "#ffffff",
						border: "1px solid #e2e8f0",
						borderRadius: "8px",
						display: "flex",
						flexDirection: "column",
						alignItems: "center",
						gap: "12px",
					}}
				>
					<Clock size={32} style={{ color: "#94a3b8" }} />
					<div style={{ fontSize: "15px", fontWeight: 700, color: "#0f172a" }}>
						No Matching Investigations Found
					</div>
					<p style={{ fontSize: "13px", color: "#64748b", maxWidth: "400px", margin: 0 }}>
						Try adjusting your search criteria or launch a new autonomous investigation on any transaction ID.
					</p>
					<button
						onClick={onOpenNewInvestigation}
						style={{
							marginTop: "8px",
							padding: "7px 16px",
							backgroundColor: "#ea580c",
							color: "#ffffff",
							border: "none",
							borderRadius: "6px",
							fontSize: "12.5px",
							fontWeight: 600,
							cursor: "pointer",
						}}
					>
						+ Start Investigation
					</button>
				</div>
			) : (
				<div
					style={{
						backgroundColor: "#ffffff",
						border: "1px solid #e2e8f0",
						borderRadius: "8px",
						overflow: "hidden",
						boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
					}}
				>
					<table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
						<thead>
							<tr style={{ backgroundColor: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
								<th style={{ padding: "12px 16px", fontWeight: 700, color: "#475569", fontSize: "11.5px", textTransform: "uppercase" }}>
									Case ID
								</th>
								<th style={{ padding: "12px 16px", fontWeight: 700, color: "#475569", fontSize: "11.5px", textTransform: "uppercase" }}>
									Subject Entities
								</th>
								<th style={{ padding: "12px 16px", fontWeight: 700, color: "#475569", fontSize: "11.5px", textTransform: "uppercase" }}>
									Verdict
								</th>
								<th style={{ padding: "12px 16px", fontWeight: 700, color: "#475569", fontSize: "11.5px", textTransform: "uppercase" }}>
									P(Fraud) Shift
								</th>
								<th style={{ padding: "12px 16px", fontWeight: 700, color: "#475569", fontSize: "11.5px", textTransform: "uppercase" }}>
									Primary Action
								</th>
								<th style={{ padding: "12px 16px", fontWeight: 700, color: "#475569", fontSize: "11.5px", textTransform: "uppercase" }}>
									Exposure
								</th>
								<th style={{ padding: "12px 16px", fontWeight: 700, color: "#475569", fontSize: "11.5px", textTransform: "uppercase" }}>
									SAR Mandate
								</th>
								<th style={{ padding: "12px 16px", fontWeight: 700, color: "#475569", fontSize: "11.5px", textTransform: "uppercase", textAlign: "right" }}>
									Action
								</th>
							</tr>
						</thead>
						<tbody>
							{filteredHistory.map((item, idx) => {
								const isFraud = item.verdict.toLowerCase().includes("fraud");
								const isCleared = item.verdict.toLowerCase().includes("legit") || item.verdict.toLowerCase().includes("cleared");

								return (
									<tr
										key={idx}
										style={{
											borderBottom: idx === filteredHistory.length - 1 ? "none" : "1px solid #f1f5f9",
											transition: "background-color 0.12s ease",
										}}
										onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.backgroundColor = "#fafbfc")}
										onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.backgroundColor = "transparent")}
									>
										{/* Case ID */}
										<td style={{ padding: "12px 16px" }}>
											<div style={{ fontWeight: 700, color: "#0f172a" }}>
												{item.case_id}
											</div>
											<div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
												{item.timestamp.slice(0, 16).replace("T", " ")}
											</div>
										</td>

										{/* Subject Entities */}
										<td style={{ padding: "12px 16px" }}>
											<div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
												<span style={{ fontSize: "12px", color: "#334155" }}>
													<strong style={{ color: "#64748b", fontSize: "11px" }}>Card:</strong> {item.card_id}
												</span>
												<span style={{ fontSize: "12px", color: "#334155" }}>
													<strong style={{ color: "#64748b", fontSize: "11px" }}>Txn:</strong> {item.flagged_txn_id}
												</span>
											</div>
										</td>

										{/* Verdict */}
										<td style={{ padding: "12px 16px" }}>
											<span
												style={{
													fontSize: "11.5px",
													fontWeight: 700,
													padding: "2px 8px",
													borderRadius: "4px",
													backgroundColor: isFraud ? "#fef2f2" : isCleared ? "#f0fdf4" : "#fffbeb",
													color: isFraud ? "#b91c1c" : isCleared ? "#15803d" : "#b45309",
													border: `1px solid ${isFraud ? "#fecaca" : isCleared ? "#bbf7d0" : "#fde68a"}`,
													textTransform: "uppercase",
												}}
											>
												{isFraud ? "CONFIRMED FRAUD" : isCleared ? "CLEARED" : "UNCERTAIN"}
											</span>
										</td>

										{/* Belief Shift */}
										<td style={{ padding: "12px 16px" }}>
											<div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
												<span style={{ fontSize: "12px", color: "#64748b" }}>
													{(item.prior_probability * 100).toFixed(0)}%
												</span>
												<ArrowRight size={11} style={{ color: "#94a3b8" }} />
												<span
													style={{
														fontSize: "12.5px",
														fontWeight: 800,
														color: item.fraud_probability >= 0.7 ? "#dc2626" : item.fraud_probability <= 0.3 ? "#16a34a" : "#ea580c",
													}}
												>
													{(item.fraud_probability * 100).toFixed(1)}%
												</span>
											</div>
										</td>

										{/* Primary Action */}
										<td style={{ padding: "12px 16px" }}>
											<div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
												<span style={{ fontWeight: 600, color: "#0f172a", fontSize: "12.5px" }}>
													{item.primary_action.replace(/_/g, " ")}
												</span>
												<span
													style={{
														fontSize: "10.5px",
														fontWeight: 700,
														padding: "1px 5px",
														borderRadius: "3px",
														backgroundColor: "#f1f5f9",
														color: "#475569",
														border: "1px solid #e2e8f0",
													}}
												>
													{item.approval_route}
												</span>
											</div>
										</td>

										{/* Exposure */}
										<td style={{ padding: "12px 16px", fontWeight: 700, color: "#0f172a" }}>
											${item.exposure_usd.toFixed(2)}
										</td>

										{/* SAR Mandate */}
										<td style={{ padding: "12px 16px" }}>
											<span
												style={{
													fontSize: "11px",
													fontWeight: 700,
													padding: "2px 7px",
													borderRadius: "4px",
													backgroundColor: item.sar_mandated ? "#fef2f2" : "#f8fafc",
													color: item.sar_mandated ? "#b91c1c" : "#64748b",
													border: `1px solid ${item.sar_mandated ? "#fecaca" : "#e2e8f0"}`,
												}}
											>
												{item.sar_mandated ? "SAR MANDATED" : "EXEMPT"}
											</span>
										</td>

										{/* Action Button */}
										<td style={{ padding: "12px 16px", textAlign: "right" }}>
											<button
												onClick={() => onSelectCase(item.case_id)}
												style={{
													padding: "4px 10px",
													backgroundColor: "#ffffff",
													border: "1px solid #cbd5e1",
													borderRadius: "5px",
													fontSize: "12px",
													fontWeight: 600,
													color: "#ea580c",
													cursor: "pointer",
													display: "inline-flex",
													alignItems: "center",
													gap: "4px",
												}}
												onMouseEnter={(e) => {
													(e.currentTarget as HTMLElement).style.backgroundColor = "#fff7ed";
													(e.currentTarget as HTMLElement).style.borderColor = "#fed7aa";
												}}
												onMouseLeave={(e) => {
													(e.currentTarget as HTMLElement).style.backgroundColor = "#ffffff";
													(e.currentTarget as HTMLElement).style.borderColor = "#cbd5e1";
												}}
											>
												Inspect
												<ExternalLink size={11} />
											</button>
										</td>
									</tr>
								);
							})}
						</tbody>
					</table>
				</div>
			)}
		</div>
	);
};
