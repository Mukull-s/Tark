import type React from "react";
import { useEffect, useRef } from "react";
import type { InvestigationResultPayload } from "../api/types";

interface RunTraceConsoleProps {
	result: InvestigationResultPayload | null;
	isOpen: boolean;
	onToggle: () => void;
	isSidebarCollapsed: boolean;
}

export const RunTraceConsole: React.FC<RunTraceConsoleProps> = ({
	result,
	isOpen,
	onToggle,
	isSidebarCollapsed,
}) => {
	const scrollRef = useRef<HTMLDivElement>(null);
	const events = result?.events || [];
	const finalState = result?.run_result?.final_state;
	const isComplete = !!result?.run_result;

	useEffect(() => {
		if (isOpen && scrollRef.current) {
			scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
		}
	}, [isOpen, events.length]);

	return (
		<div
			style={{
				position: "fixed",
				bottom: 0,
				left: isSidebarCollapsed ? "64px" : "230px",
				right: 0,
				backgroundColor: "#0f172a",
				color: "#f8fafc",
				borderTop: "1px solid #334155",
				zIndex: 30,
				display: "flex",
				flexDirection: "column",
				boxShadow: isOpen ? "0 -4px 16px rgba(0, 0, 0, 0.25)" : "none",
				transition: "left 0.2s ease, all 0.15s ease",
			}}
		>
			{/* Console Header Bar */}
			<div
				onClick={onToggle}
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
					padding: "7px 18px",
					backgroundColor: "#1e293b",
					cursor: "pointer",
					fontSize: "11.5px",
					fontFamily: "ui-monospace, monospace",
					userSelect: "none",
				}}
			>
				{/* Pipeline Status Indicator */}
				<div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
					<div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
						<span style={{ color: "#ea580c", fontWeight: 700 }}>⚡ PIPELINE TELEMETRY</span>
						<span style={{ color: "#64748b" }}>|</span>
					</div>

					{/* 4 Pipeline Stages */}
					<div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "10.5px" }}>
						<span style={{ color: result ? "#4ade80" : "#94a3b8" }}>
							① Prior Calibration
						</span>
						<span style={{ color: "#475569" }}>→</span>
						<span style={{ color: events.some(e => e.type === "TOOL_COMPLETED") ? "#38bdf8" : "#94a3b8" }}>
							② TigerGraph Queries
						</span>
						<span style={{ color: "#475569" }}>→</span>
						<span style={{ color: isComplete ? "#fb923c" : "#94a3b8" }}>
							③ EVOI Decision Gate
						</span>
						<span style={{ color: "#475569" }}>→</span>
						<span style={{ color: isComplete ? "#a78bfa" : "#94a3b8" }}>
							④ Grounded Synthesis
						</span>
					</div>

					<span style={{ color: "#64748b" }}>·</span>
					<span style={{ color: "#cbd5e1" }}>
						{events.length > 0
							? `${events.length} execution events recorded`
							: "Pipeline ready"}
					</span>
				</div>

				<div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
					{finalState && (
						<span style={{ color: "#94a3b8", fontSize: "11px" }}>
							Final P(Fraud): <strong style={{ color: "#f8fafc" }}>{((finalState.fraud_probability ?? 0.5) * 100).toFixed(1)}%</strong>
						</span>
					)}
					<span style={{ color: "#ea580c", fontSize: "10.5px", fontWeight: 600 }}>
						{isOpen ? "▼ Collapse" : "▲ View Execution Pipeline"}
					</span>
				</div>
			</div>

			{/* Monospace Execution Telemetry Log */}
			{isOpen && (
				<div
					ref={scrollRef}
					style={{
						height: "180px",
						overflowY: "auto",
						padding: "12px 18px",
						fontSize: "11.5px",
						fontFamily: "ui-monospace, monospace",
						lineHeight: "1.65",
						backgroundColor: "#090d16",
					}}
				>
					{events.length === 0 ? (
						<div style={{ color: "#64748b", fontStyle: "italic", padding: "8px 0" }}>
							Pipeline standby. When you start an investigation, live GSQL queries, tool execution latencies (ms), Bayesian likelihood ratio (LR) updates, and EVOI decision branches stream here in real time.
						</div>
					) : (
						events.map((evt, idx) => {
							const timeStr = evt.timestamp
								? new Date(evt.timestamp).toLocaleTimeString()
								: "12:03:00";
							const isTool = evt.type === "TOOL_COMPLETED";
							const isCase = evt.type === "CASE_OPENED";
							const isDecision = evt.type === "INVESTIGATION_COMPLETED" || evt.type === "DECISION_REACHED";

							let typeColor = "#fb923c"; // state/evidence
							if (isTool) typeColor = "#38bdf8";
							if (isCase) typeColor = "#4ade80";
							if (isDecision) typeColor = "#a78bfa";

							return (
								<div
									key={evt.id || idx}
									style={{ display: "flex", gap: "12px", borderBottom: "1px solid #111827", padding: "2px 0" }}
								>
									<span style={{ color: "#64748b", flexShrink: 0 }}>
										{timeStr}
									</span>
									<span
										style={{
											color: typeColor,
											fontWeight: 600,
											width: "90px",
											flexShrink: 0,
										}}
									>
										{isTool ? "query:tg" : isCase ? "stage:init" : isDecision ? "stage:gate" : "stage:evoi"}
									</span>
									<span style={{ color: "#f1f5f9", flex: 1, wordBreak: "break-word" }}>
										{evt.summary}
									</span>
								</div>
							);
						})
					)}
				</div>
			)}
		</div>
	);
};
