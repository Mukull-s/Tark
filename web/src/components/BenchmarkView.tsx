import React, { useState, useEffect } from "react";
import type { CaseMetadata } from "../api/types";
import { fetchBenchmarkSummary } from "../api/client";

interface BenchmarkViewProps {
	cases: CaseMetadata[];
	onSelectCase: (caseId: string) => void;
}

interface CaseComparison {
	case_id: string;
	actual_nba: string;
	expected_nba: string | null;
	/** Current harness artifact field. */
	is_match?: boolean | null;
	/** Legacy artifact field (pre-de-circularization). */
	nba_match?: boolean;
	policy_conformant?: boolean;
	fraud_probability?: number;
	/** Legacy artifact field. */
	final_p_fraud?: number;
	gate_passed: boolean;
	coverage?: number;
	steps?: number;
	duration_sec?: number;
}

interface BenchmarkSummaryPayload {
	benchmark_name?: string;
	benchmark_run_id?: string;
	commit_sha: string;
	timestamp: string;
	total_cases: number;
	headline?: {
		primary_metric?: string;
		policy_invariant_conformance_pct?: number;
		partial_credit_score?: number;
		partial_credit_pct?: number;
		partial_credit_definition?: string;
		rubric_agreement_detail?: {
			label?: string;
			pct?: number;
			count?: number;
			scored_cases?: number;
		};
		note?: string;
	};
	policy_conformance_count?: number;
	policy_conformance_pct?: number;
	partial_credit_score?: number;
	partial_credit_pct?: number;
	rubric_agreement_label?: string;
	nba_agreement_count: number;
	nba_agreement_pct: number;
	nba_metric_label?: string;
	expected_nba_source?: string;
	gate_pass_count: number;
	gate_pass_pct: number;
	fraud_verdict_count: number;
	fraud_verdict_pct: number;
	avg_steps: number;
	avg_coverage: number;
	avg_duration_sec: number;
	tool_distribution: Record<string, number>;
	case_comparisons: CaseComparison[];
}

const TOOL_NAMES: Record<string, string> = {
	QUERY_DEVICE_ANALYSIS: "Device Neighborhood Analysis",
	QUERY_CARD_SEQUENCE: "Card Sequence & Micro-Auth",
	QUERY_TXN_VELOCITY: "Transaction Velocity Analysis",
	QUERY_REGION_ANALYSIS: "Billing Region Analysis",
	QUERY_CUSTOMER_PROFILE: "Customer Behavioral Baseline",
	VERIFY_WITH_CUSTOMER: "Out-of-Band Customer Verify",
	SIMULATE_CUSTOMER_REPLY: "Out-of-Band Customer Verify",
	STEP_UP_AUTH: "Step-Up Multi-Factor Authentication",
};

const cardStyle: React.CSSProperties = {
	backgroundColor: "#ffffff",
	borderRadius: "8px",
	border: "1px solid #e2e8f0",
	padding: "14px 16px",
	boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
};

const SkeletonBar: React.FC<{ width: string; height?: string }> = ({ width, height = "18px" }) => (
	<div
		aria-hidden="true"
		style={{
			width,
			height,
			borderRadius: "4px",
			backgroundColor: "#e2e8f0",
			animation: "tark-pulse 1.4s ease-in-out infinite",
		}}
	/>
);

const LoadingSkeleton: React.FC = () => (
	<div
		data-testid="benchmark-loading-skeleton"
		style={{ display: "flex", flexDirection: "column", gap: "20px" }}
	>
		<div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px" }}>
			<div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
				<SkeletonBar width="320px" height="22px" />
				<SkeletonBar width="440px" height="12px" />
			</div>
			<div style={{ display: "flex", flexDirection: "column", gap: "6px", alignItems: "flex-end" }}>
				<SkeletonBar width="220px" height="16px" />
				<SkeletonBar width="160px" height="12px" />
			</div>
		</div>

		<div
			style={{
				display: "grid",
				gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
				gap: "12px",
			}}
		>
			{[0, 1, 2, 3, 4].map((i) => (
				<div key={i} style={cardStyle}>
					<SkeletonBar width="70%" height="10px" />
					<div style={{ height: "8px" }} />
					<SkeletonBar width="45%" height="20px" />
					<div style={{ height: "6px" }} />
					<SkeletonBar width="60%" height="10px" />
				</div>
			))}
		</div>

		<div
			style={{
				backgroundColor: "#ffffff",
				borderRadius: "8px",
				border: "1px solid #e2e8f0",
				padding: "20px 24px",
				display: "flex",
				flexDirection: "column",
				gap: "14px",
			}}
		>
			<SkeletonBar width="300px" height="12px" />
			{[0, 1, 2, 3].map((i) => (
				<div key={i} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
					<SkeletonBar width="55%" height="11px" />
					<SkeletonBar width="100%" height="6px" />
				</div>
			))}
		</div>

		<div style={{ fontSize: "12.5px", color: "#94a3b8", textAlign: "center" }}>
			Loading authoritative evaluation artifact&hellip;
		</div>
	</div>
);

interface UnavailableStateProps {
	onRetry: () => void;
}

const UnavailableState: React.FC<UnavailableStateProps> = ({ onRetry }) => (
	<div
		data-testid="benchmark-unavailable"
		style={{
			backgroundColor: "#fffbeb",
			border: "1px solid #fde68a",
			borderRadius: "8px",
			padding: "24px",
			display: "flex",
			flexDirection: "column",
			gap: "10px",
			alignItems: "flex-start",
		}}
	>
		<div style={{ fontSize: "15px", fontWeight: 700, color: "#92400e" }}>
			Evaluation artifact unavailable
		</div>
		<div style={{ fontSize: "13px", color: "#78350f", lineHeight: 1.5 }}>
			No authoritative <code>analysis/evaluation_summary.json</code> could be loaded from the API.
			Benchmark metrics are intentionally not displayed until the real artifact is fetched — Tark
			does not show placeholder or reconstructed scores.
		</div>
		<button
			type="button"
			onClick={onRetry}
			style={{
				marginTop: "4px",
				padding: "7px 14px",
				borderRadius: "6px",
				border: "1px solid #f59e0b",
				backgroundColor: "#f59e0b",
				color: "#ffffff",
				fontSize: "12.5px",
				fontWeight: 600,
				cursor: "pointer",
			}}
		>
			Retry
		</button>
	</div>
);

export const BenchmarkView: React.FC<BenchmarkViewProps> = ({
	cases,
	onSelectCase,
}) => {
	const [summary, setSummary] = useState<BenchmarkSummaryPayload | null>(null);
	const [loading, setLoading] = useState<boolean>(true);
	const [error, setError] = useState<string | null>(null);
	const [reloadKey, setReloadKey] = useState<number>(0);

	useEffect(() => {
		let isMounted = true;
		setLoading(true);
		setError(null);
		fetchBenchmarkSummary()
			.then((data) => {
				if (!isMounted) return;
				if (data && typeof data.total_cases === "number") {
					setSummary(data);
				} else {
					setSummary(null);
					setError("Evaluation artifact returned no usable benchmark data.");
				}
			})
			.catch((err: unknown) => {
				if (!isMounted) return;
				setSummary(null);
				setError(err instanceof Error ? err.message : "Failed to load evaluation artifact.");
			})
			.finally(() => {
				if (isMounted) setLoading(false);
			});

		return () => {
			isMounted = false;
		};
	}, [reloadKey]);

	if (loading) {
		return <LoadingSkeleton />;
	}

	if (error || !summary) {
		return <UnavailableState onRetry={() => setReloadKey((k) => k + 1)} />;
	}

	const totalToolCalls = Object.values(summary.tool_distribution || {}).reduce(
		(a, b) => a + b,
		0
	);

	const toolEntries = Object.entries(summary.tool_distribution || {})
		.sort(([, a], [, b]) => b - a)
		.map(([tool, count]) => {
			const pct = totalToolCalls > 0 ? `${Math.round((count / totalToolCalls) * 100)}%` : "0%";
			return {
				tool,
				name: TOOL_NAMES[tool] || tool.replace(/_/g, " "),
				count,
				pct,
			};
		});

	const conformanceCount = summary.policy_conformance_count;
	const partialCreditScore = summary.headline?.partial_credit_score ?? summary.partial_credit_score;

	const evaluationStats: Array<{
		label: string;
		value: string;
		sub: string;
		highlight: boolean;
	}> = [
		{
			label: "Evaluated Cases",
			value: `${summary.total_cases}`,
			sub: "Frozen benchmark pack",
			highlight: false,
		},
		{
			label: "Policy-Invariant Conformance",
			value:
				conformanceCount != null
					? `${conformanceCount}/${summary.total_cases}`
					: "—",
			sub: "Independent governance invariants",
			highlight: true,
		},
		{
			label: "Graded Partial Credit",
			value:
				typeof partialCreditScore === "number"
					? partialCreditScore.toFixed(2)
					: "—",
			sub: "Conformance + route + rubric",
			highlight: true,
		},
		{
			label: "Next-Best-Action Agreement",
			value: `${summary.nba_agreement_count}/${summary.total_cases}`,
			sub: "Team-authored policy rubric (detail)",
			highlight: false,
		},
		{
			label: "Decision Gate Pass Rate",
			value: `${summary.gate_pass_count}/${summary.total_cases}`,
			sub: `${summary.total_cases - summary.gate_pass_count} safely pruned via EVOI`,
			highlight: true,
		},
		{
			label: "Average Steps",
			value: `${summary.avg_steps.toFixed(1)}`,
			sub: "Mean query depth",
			highlight: false,
		},
		{
			label: "Graph Tool Dispatches",
			value: `${totalToolCalls}`,
			sub: "Live TigerGraph queries",
			highlight: false,
		},
	];

	return (
		<div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
			{/* Header */}
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
					<h1
						style={{
							fontSize: "20px",
							fontWeight: 700,
							color: "#0f172a",
							margin: "0 0 2px 0",
							letterSpacing: "-0.02em",
						}}
					>
						Benchmark &amp; Independent Evaluation Scoreboard
					</h1>
					<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
						Authoritative frozen baseline execution against live TigerGraph Cloud cluster
					</p>
				</div>
				<div
					style={{
						display: "flex",
						flexDirection: "column",
						alignItems: "flex-end",
						gap: "2px",
					}}
				>
					<span
						style={{
							fontSize: "11px",
							fontWeight: 700,
							fontFamily: "ui-monospace, monospace",
							color: "#0f766e",
							backgroundColor: "#f0fdfa",
							padding: "3px 8px",
							borderRadius: "4px",
							border: "1px solid #ccfbf1",
						}}
					>
						COMMIT: {summary.commit_sha.slice(0, 8)} · EVALUATION ARTIFACT
					</span>
					<span style={{ fontSize: "11px", color: "#94a3b8" }}>
						Evaluated: {new Date(summary.timestamp).toLocaleString()}
					</span>
				</div>
			</div>

			{/* Headline note (independent vs. team-authored provenance) */}
			{summary.headline?.note && (
				<div
					style={{
						backgroundColor: "#f0fdfa",
						border: "1px solid #ccfbf1",
						borderRadius: "8px",
						padding: "12px 16px",
						fontSize: "12.5px",
						color: "#0f766e",
						lineHeight: 1.5,
					}}
				>
					<strong>Headline metric:</strong>{" "}
					{summary.headline.primary_metric || "policy_invariant_conformance_pct"}. {summary.headline.note}
				</div>
			)}

			{/* Evaluation Stats Grid */}
			<div
				style={{
					display: "grid",
					gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
					gap: "12px",
				}}
			>
				{evaluationStats.map((kpi, idx) => (
					<div
						key={idx}
						style={{
							...cardStyle,
							border: kpi.highlight ? "1px solid #fed7aa" : "1px solid #e2e8f0",
						}}
					>
						<div
							style={{
								fontSize: "11px",
								fontWeight: 600,
								color: "#64748b",
								textTransform: "uppercase",
								marginBottom: "4px",
							}}
						>
							{kpi.label}
						</div>
						<div
							style={{
								fontSize: "20px",
								fontWeight: 700,
								color: kpi.highlight ? "#ea580c" : "#0f172a",
								lineHeight: 1.2,
							}}
						>
							{kpi.value}
						</div>
						<div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>
							{kpi.sub}
						</div>
					</div>
				))}
			</div>

			{/* Tool Query Distribution Breakdown */}
			<div
				style={{
					backgroundColor: "#ffffff",
					borderRadius: "8px",
					border: "1px solid #e2e8f0",
					padding: "20px 24px",
					boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
					display: "flex",
					flexDirection: "column",
					gap: "14px",
				}}
			>
				<div
					style={{
						fontSize: "13px",
						fontWeight: 700,
						color: "#475569",
						textTransform: "uppercase",
						letterSpacing: "0.04em",
					}}
				>
					Empirical Tool Execution Distribution ({totalToolCalls} Total Dispatches)
				</div>

				<div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
					{toolEntries.map((item, idx) => (
						<div key={idx} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
							<div
								style={{
									display: "flex",
									justifyContent: "space-between",
									fontSize: "12px",
									color: "#334155",
								}}
							>
								<span>
									<strong>{item.name}</strong>{" "}
									<code style={{ fontSize: "11px", color: "#64748b" }}>({item.tool})</code>
								</span>
								<span style={{ fontWeight: 600 }}>
									{item.count} calls ({item.pct})
								</span>
							</div>
							<div
								style={{
									height: "6px",
									width: "100%",
									backgroundColor: "#f1f5f9",
									borderRadius: "3px",
									overflow: "hidden",
								}}
							>
								<div
									style={{
										height: "100%",
										width: item.pct,
										backgroundColor: idx === 0 ? "#ea580c" : "#3b82f6",
										borderRadius: "3px",
									}}
								/>
							</div>
						</div>
					))}
				</div>
			</div>

			{/* 20-Case Benchmark Grid */}
			<div
				style={{
					backgroundColor: "#ffffff",
					borderRadius: "8px",
					border: "1px solid #e2e8f0",
					padding: "20px 24px",
					boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
					display: "flex",
					flexDirection: "column",
					gap: "14px",
				}}
			>
				<div
					style={{
						display: "flex",
						justifyContent: "space-between",
						alignItems: "center",
					}}
				>
					<div>
						<div
							style={{
								fontSize: "13px",
								fontWeight: 700,
								color: "#475569",
								textTransform: "uppercase",
								letterSpacing: "0.04em",
							}}
						>
							20-Case Investigation Matrix
						</div>
						<div style={{ fontSize: "12px", color: "#64748b" }}>
							Select any benchmark case to inspect its live Bayesian reasoning timeline and graph
						</div>
					</div>
					<span
						style={{
							fontSize: "11px",
							fontWeight: 600,
							color: "#475569",
							backgroundColor: "#f8fafc",
							padding: "3px 8px",
							borderRadius: "4px",
							border: "1px solid #e2e8f0",
						}}
					>
						20 Verified Test Cases
					</span>
				</div>

				<div
					style={{
						display: "grid",
						gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
						gap: "8px",
					}}
				>
					{cases.map((c) => {
						const comp = summary.case_comparisons?.find((item) => item.case_id === c.case_id);
						const isMatch = comp?.is_match ?? comp?.nba_match;
						return (
							<div
								key={c.case_id}
								onClick={() => onSelectCase(c.case_id)}
								style={{
									padding: "10px 12px",
									backgroundColor: "#f8fafc",
									border: "1px solid #e2e8f0",
									borderRadius: "6px",
									cursor: "pointer",
									display: "flex",
									flexDirection: "column",
									gap: "4px",
									transition: "all 0.12s ease",
								}}
								onMouseEnter={(e) => {
									(e.currentTarget as HTMLElement).style.backgroundColor = "#fff7ed";
									(e.currentTarget as HTMLElement).style.borderColor = "#ea580c";
								}}
								onMouseLeave={(e) => {
									(e.currentTarget as HTMLElement).style.backgroundColor = "#f8fafc";
									(e.currentTarget as HTMLElement).style.borderColor = "#e2e8f0";
								}}
							>
								<div
									style={{
										display: "flex",
										justifyContent: "space-between",
										alignItems: "center",
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
											color: "#ea580c",
											fontWeight: 600,
										}}
									>
										INSPECT &rarr;
									</span>
								</div>
								<div style={{ fontSize: "11px", color: "#64748b" }}>
									Txn #{c.flagged_txn_id}
								</div>
								<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "2px" }}>
									<span style={{ fontSize: "10px", color: "#94a3b8", textTransform: "capitalize" }}>
										{c.trigger_type.replace(/_/g, " ")}
									</span>
									{comp && isMatch != null && (
										<span
											style={{
												fontSize: "9.5px",
												fontWeight: 700,
												color: isMatch ? "#15803d" : "#ea580c",
											}}
										>
											{comp.actual_nba}
										</span>
									)}
								</div>
							</div>
						);
					})}
				</div>
			</div>
		</div>
	);
};
