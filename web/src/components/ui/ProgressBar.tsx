import type React from "react";

export interface ProgressBarProps {
	value: number; // 0.0 to 1.0 or 0 to 100
	variant?: "risk" | "coverage" | "neutral";
	height?: "sm" | "md" | "lg";
	showLabel?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
	value,
	variant = "risk",
	height = "md",
	showLabel = false,
}) => {
	// Normalize value to 0..100
	const percent = Math.min(100, Math.max(0, value > 1.0 ? value : value * 100));

	const heightClass = {
		sm: "h-1.5",
		md: "h-2.5",
		lg: "h-4",
	}[height];

	const getRiskColor = (pct: number) => {
		if (variant === "coverage") {
			return "bg-accent";
		}
		if (variant === "neutral") {
			return "bg-primary-muted";
		}
		// Risk gradient mapping
		if (pct >= 70) return "bg-risk-high";
		if (pct >= 30) return "bg-risk-warning";
		return "bg-risk-legit";
	};

	return (
		<div className="w-full">
			<div
				className={`w-full bg-surface-tertiary rounded-full overflow-hidden ${heightClass} border border-border/50`}
			>
				<div
					className={`h-full transition-all duration-300 rounded-full ${getRiskColor(percent)}`}
					style={{ width: `${percent}%` }}
				/>
			</div>
			{showLabel && (
				<div className="flex justify-between items-center text-[11px] font-mono text-primary-muted mt-1 tabular-nums">
					<span>0.00</span>
					<span className="font-semibold text-primary">
						{(percent / 100).toFixed(4)}
					</span>
					<span>1.00</span>
				</div>
			)}
		</div>
	);
};
