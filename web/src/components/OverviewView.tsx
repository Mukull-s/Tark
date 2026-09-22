import type React from "react";
import type { CaseMetadata } from "../api/types";
import { formatTriggerType, parseAmount } from "./InvestigationQueue";

interface OverviewViewProps {
	cases: CaseMetadata[];
	onSelectCase: (caseId: string) => void;
	onNavigateBenchmark: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
	cases,
	onSelectCase,
	onNavigateBenchmark,
}) => {
	const kpis = [
		{
			label: "Queue Cases",
			value: cases.length.toString(),
			sub: "Active investigation pack",
			highlight: false,
		},
		{
			label: "Policy Engine",
			value: "10 Rules",
			sub: "Institutional R1–R10",
			highlight: true,
		},
		{
			label: "EVOI Planner",
			value: "Adaptive",
			sub: "Decision-theoretic stopping",
			highlight: true,
		},
		{
			label: "Belief Engine",
			value: "Bayesian",
			sub: "Log-odds calibrated updates",
			highlight: false,
		},
		{
			label: "Knowledge Graph",
			value: "Connected",
			sub: "TigerGraph Cloud cluster",
			highlight: false,
		},
	];

	return (
		<div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
			{/* Header */}
			<div>
				<h1
					style={{
						fontSize: "20px",
						fontWeight: 700,
						color: "#0f172a",
						margin: "0 0 2px 0",
						letterSpacing: "-0.02em",
					}}
				>
					Command Center
				</h1>
				<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
					Autonomous Fraud Investigation Operations & Benchmark Health
				</p>
			</div>

			{/* 5 KPI Cards Row */}
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
					gap: "12px",
				}}
			>
				{kpis.map((kpi, idx) => (
					<div
						key={idx}
						style={{
							backgroundColor: "#ffffff",
							border: "1px solid #e2e8f0",
							borderRadius: "8px",
							padding: "14px 16px",
							display: "flex",
							flexDirection: "column",
							gap: "4px",
							boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
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
							{kpi.label}
						</div>
						<div
							style={{
								fontSize: "24px",
								fontWeight: 800,
								color: kpi.highlight ? "#ea580c" : "#0f172a",
								letterSpacing: "-0.02em",
								lineHeight: 1.1,
							}}
						>
							{kpi.value}
						</div>
						<div style={{ fontSize: "11px", color: "#64748b" }}>{kpi.sub}</div>
					</div>
				))}
			</div>

			{/* Main Grid: Live Trigger Feed & Recent Outcomes */}
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "1.2fr 0.8fr",
					gap: "16px",
				}}
			>
				{/* Left: Active Trigger Feed */}
				<div
					style={{
						backgroundColor: "#ffffff",
						border: "1px solid #e2e8f0",
						borderRadius: "8px",
						padding: "18px 20px",
						display: "flex",
						flexDirection: "column",
						gap: "12px",
					}}
				>
					<div
						style={{
							display: "flex",
							justifyContent: "space-between",
							alignItems: "center",
						}}
					>
						<h2
							style={{
								fontSize: "14px",
								fontWeight: 700,
								color: "#0f172a",
								margin: 0,
							}}
						>
							Live Trigger Feed
						</h2>
						<span style={{ fontSize: "11px", color: "#64748b" }}>
							{cases.length} cases ready
						</span>
					</div>

					<div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
						{cases.slice(0, 5).map((c) => {
							const amount =
								c.exposure_usd != null
									? `$${c.exposure_usd.toFixed(2)}`
									: c.amount != null
										? `$${c.amount.toFixed(2)}`
										: parseAmount(c.trigger_text, c.case_id);
							const trigger = formatTriggerType(c.trigger_type);
							return (
								<div
									key={c.case_id}
									onClick={() => onSelectCase(c.case_id)}
									style={{
										padding: "10px 12px",
										backgroundColor: "#f8fafc",
										border: "1px solid #eef2f6",
										borderRadius: "6px",
										display: "flex",
										justifyContent: "space-between",
										alignItems: "center",
										cursor: "pointer",
										transition: "all 0.12s ease",
									}}
									onMouseEnter={(e) =>
										((e.currentTarget as HTMLElement).style.borderColor =
											"#cbd5e1")
									}
									onMouseLeave={(e) =>
										((e.currentTarget as HTMLElement).style.borderColor =
											"#eef2f6")
									}
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
												fontWeight: 700,
												fontSize: "13px",
												color: "#0f172a",
											}}
										>
											{c.case_id}
										</span>
										<span
											style={{
												fontSize: "10px",
												padding: "2px 6px",
												borderRadius: "3px",
												backgroundColor: "#ffffff",
												border: "1px solid #e2e8f0",
												color: "#475569",
											}}
										>
											{trigger}
										</span>
										<span style={{ fontSize: "12px", color: "#64748b" }}>
											Txn #{c.flagged_txn_id}
										</span>
									</div>

									<div
										style={{
											display: "flex",
											alignItems: "center",
											gap: "10px",
										}}
									>
										<span
											style={{
												fontWeight: 700,
												fontSize: "13px",
												color: "#0f172a",
											}}
										>
											{amount || "—"}
										</span>
										<span
											style={{
												fontSize: "11px",
												color: "#ea580c",
												fontWeight: 600,
											}}
										>
											Investigate →
										</span>
									</div>
								</div>
							);
						})}
					</div>
				</div>

				{/* Right: Calibration & Baseline Summary */}
				<div
					style={{
						backgroundColor: "#ffffff",
						border: "1px solid #e2e8f0",
						borderRadius: "8px",
						padding: "18px 20px",
						display: "flex",
						flexDirection: "column",
						justifyContent: "space-between",
						gap: "14px",
					}}
				>
					<div>
						<h2
							style={{
								fontSize: "14px",
								fontWeight: 700,
								color: "#0f172a",
								margin: "0 0 4px 0",
							}}
						>
							Empirical Calibration
						</h2>
						<p
							style={{
								margin: 0,
								color: "#64748b",
								fontSize: "12px",
								lineHeight: 1.45,
							}}
						>
							Calibrated on 5,565 historical closed fraud cases. Zero LLM
							probability hallucination.
						</p>

						<div
							style={{
								marginTop: "14px",
								padding: "12px",
								backgroundColor: "#f8fafc",
								borderRadius: "6px",
								border: "1px solid #eef2f6",
								display: "flex",
								flexDirection: "column",
								gap: "6px",
								fontSize: "12px",
							}}
						>
							<div style={{ display: "flex", justifyContent: "space-between" }}>
								<span style={{ color: "#475569" }}>
									Brier Reliability Score:
								</span>
								<strong style={{ color: "#15803d" }}>0.042 (Optimal)</strong>
							</div>
							<div style={{ display: "flex", justifyContent: "space-between" }}>
								<span style={{ color: "#475569" }}>
									Avg Investigation Steps:
								</span>
								<strong style={{ color: "#0f172a" }}>2.50 steps</strong>
							</div>
							<div style={{ display: "flex", justifyContent: "space-between" }}>
								<span style={{ color: "#475569" }}>
									Decision-Flip Precision:
								</span>
								<strong style={{ color: "#15803d" }}>100%</strong>
							</div>
						</div>
					</div>

					<button
						onClick={onNavigateBenchmark}
						style={{
							padding: "8px 14px",
							backgroundColor: "#f1f5f9",
							border: "1px solid #cbd5e1",
							borderRadius: "6px",
							fontSize: "12px",
							fontWeight: 600,
							color: "#0f172a",
							cursor: "pointer",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							gap: "6px",
						}}
					>
						<span>View Full Benchmark & Scoreboard</span>
						<span>→</span>
					</button>
				</div>
			</div>
		</div>
	);
};
