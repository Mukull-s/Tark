import React, { useEffect, useState } from "react";
import type { InvestigationResultPayload } from "../api/types";

interface InvestigationProgressStepperProps {
	txnId: string;
	amount?: string;
	onCompleted: () => void;
	resultPayload: InvestigationResultPayload | null;
	error: string | null;
}

interface StepStage {
	title: string;
	description: string;
	completedLabel: string;
}

const STAGES: StepStage[] = [
	{
		title: "Resolving transaction context",
		description: "Customer, card and device relationships",
		completedLabel: "Transaction context resolved",
	},
	{
		title: "Investigating connected entities",
		description: "Traversing graph relationships in TigerGraph",
		completedLabel: "Graph relationship traversal complete",
	},
	{
		title: "Evaluating evidence & uncertainty",
		description: "Bayesian belief updating & Decision Gate assessment",
		completedLabel: "Evidence evaluated & belief updated",
	},
	{
		title: "Determining next action",
		description: "Applying bank policy & approval governance",
		completedLabel: "Recommended action determined",
	},
];

export const InvestigationProgressStepper: React.FC<
	InvestigationProgressStepperProps
> = ({ txnId, amount, onCompleted, resultPayload, error }) => {
	const [activeStage, setActiveStage] = useState<number>(0);
	const [allDone, setAllDone] = useState<boolean>(false);
	const [showTechnicalTrace, setShowTechnicalTrace] = useState<boolean>(false);

	// Stage advancement driven by lifecycle timing while waiting for backend
	useEffect(() => {
		if (error) return;

		const t1 = setTimeout(() => {
			setActiveStage((prev) => Math.max(prev, 1));
		}, 450);

		const t2 = setTimeout(() => {
			setActiveStage((prev) => Math.max(prev, 2));
		}, 950);

		const t3 = setTimeout(() => {
			setActiveStage((prev) => Math.max(prev, 3));
		}, 1450);

		return () => {
			clearTimeout(t1);
			clearTimeout(t2);
			clearTimeout(t3);
		};
	}, [error]);

	// When real result payload arrives from backend, finalize all stages
	useEffect(() => {
		if (resultPayload) {
			setActiveStage(4);
			setAllDone(true);
			const delay =
				typeof window !== "undefined" &&
				(window as any).process?.env?.NODE_ENV === "test"
					? 10
					: 500;
			const completionTimer = setTimeout(() => {
				onCompleted();
			}, delay);
			return () => clearTimeout(completionTimer);
		}
	}, [resultPayload, onCompleted]);

	return (
		<div
			style={{
				backgroundColor: "#ffffff",
				borderRadius: "8px",
				border: "1px solid #e2e8f0",
				padding: "28px 32px",
				boxShadow: "0 1px 3px rgba(0, 0, 0, 0.03)",
				display: "flex",
				flexDirection: "column",
				gap: "24px",
				maxWidth: "680px",
				margin: "20px auto",
			}}
		>
			{/* Header */}
			<div style={{ borderBottom: "1px solid #f1f5f9", paddingBottom: "16px" }}>
				<div
					style={{
						fontSize: "11px",
						fontWeight: 700,
						color: "#ea580c",
						textTransform: "uppercase",
						letterSpacing: "0.04em",
						marginBottom: "4px",
					}}
				>
					Autonomous Investigation in Progress
				</div>
				<h2
					style={{
						fontSize: "19px",
						fontWeight: 700,
						color: "#0f172a",
						margin: 0,
						letterSpacing: "-0.01em",
					}}
				>
					Investigating transaction #{txnId}
				</h2>
				{amount && (
					<p style={{ margin: "4px 0 0 0", color: "#64748b", fontSize: "13px" }}>
						Amount: <strong style={{ color: "#0f172a" }}>{amount}</strong> · Real-time graph & policy analysis
					</p>
				)}
			</div>

			{/* Staged Progress Indicator */}
			<div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
				{STAGES.map((stage, idx) => {
					const isCompleted = activeStage > idx || allDone;
					const isCurrent = activeStage === idx && !allDone;
					const isPending = activeStage < idx && !allDone;

					return (
						<div
							key={idx}
							style={{
								display: "flex",
								gap: "14px",
								alignItems: "flex-start",
								opacity: isPending ? 0.45 : 1,
								transition: "opacity 0.25s ease",
							}}
						>
							{/* Status Icon */}
							<div
								style={{
									width: "24px",
									height: "24px",
									borderRadius: "50%",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									fontSize: "12px",
									fontWeight: 700,
									flexShrink: 0,
									marginTop: "1px",
									backgroundColor: isCompleted
										? "#f0fdf4"
										: isCurrent
											? "#fff7ed"
											: "#f8fafc",
									color: isCompleted
										? "#15803d"
										: isCurrent
											? "#ea580c"
											: "#94a3b8",
									border: `1.5px solid ${
										isCompleted
											? "#86efac"
											: isCurrent
												? "#fdba74"
												: "#cbd5e1"
									}`,
								}}
							>
								{isCompleted ? (
									<span>✓</span>
								) : isCurrent ? (
									<span
										style={{
											width: "8px",
											height: "8px",
											borderRadius: "50%",
											backgroundColor: "#ea580c",
											display: "inline-block",
											animation: "pulse 1.2s infinite ease-in-out",
										}}
									/>
								) : (
									<span style={{ fontSize: "10px" }}>○</span>
								)}
							</div>

							{/* Step Content */}
							<div style={{ flex: 1 }}>
								<div
									style={{
										fontSize: "13.5px",
										fontWeight: isCurrent || isCompleted ? 600 : 500,
										color: isCompleted
											? "#15803d"
											: isCurrent
												? "#0f172a"
												: "#64748b",
									}}
								>
									{isCompleted ? stage.completedLabel : stage.title}
								</div>
								<div
									style={{
										fontSize: "12px",
										color: isCompleted ? "#64748b" : "#64748b",
										marginTop: "2px",
									}}
								>
									{stage.description}
								</div>
							</div>
						</div>
					);
				})}
			</div>

			{/* Subtle Progress Bar */}
			<div
				style={{
					height: "4px",
					width: "100%",
					backgroundColor: "#f1f5f9",
					borderRadius: "2px",
					overflow: "hidden",
				}}
			>
				<div
					style={{
						height: "100%",
						backgroundColor: allDone ? "#16a34a" : "#ea580c",
						width: allDone
							? "100%"
							: `${Math.min(95, Math.max(15, (activeStage + 1) * 25))}%`,
						transition: "width 0.4s ease, background-color 0.3s ease",
					}}
				/>
			</div>

			{/* Optional Collapsible Technical Trace */}
			<div style={{ borderTop: "1px solid #f1f5f9", paddingTop: "12px" }}>
				<button
					type="button"
					onClick={() => setShowTechnicalTrace(!showTechnicalTrace)}
					style={{
						background: "none",
						border: "none",
						padding: 0,
						fontSize: "11px",
						fontWeight: 600,
						color: "#64748b",
						cursor: "pointer",
					}}
				>
					{showTechnicalTrace
						? "▼ Hide technical details"
						: "▶ View technical details"}
				</button>

				{showTechnicalTrace && (
					<div
						style={{
							marginTop: "8px",
							padding: "10px 12px",
							backgroundColor: "#f8fafc",
							borderRadius: "4px",
							border: "1px solid #e2e8f0",
							fontSize: "11px",
							fontFamily: "ui-monospace, monospace",
							color: "#334155",
							display: "flex",
							flexDirection: "column",
							gap: "4px",
						}}
					>
						<div>
							<strong>Target:</strong> Transaction #{txnId}
						</div>
						<div>
							<strong>Graph Engine:</strong> TigerGraph Cloud Savanna (REST + GSQL)
						</div>
						<div>
							<strong>Orchestrator:</strong> Bayesian Log-Odds + EVOI Decision Gate
						</div>
						<div>
							<strong>Status:</strong> {allDone ? "COMPLETED" : "PROCESSING"}
						</div>
					</div>
				)}
			</div>
		</div>
	);
};
