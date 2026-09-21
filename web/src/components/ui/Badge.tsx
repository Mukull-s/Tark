import type React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
	variant?:
		| "default"
		| "high"
		| "warning"
		| "legit"
		| "approval"
		| "neutral"
		| "accent";
	size?: "sm" | "md";
}

export const Badge: React.FC<BadgeProps> = ({
	children,
	variant = "default",
	size = "md",
	className = "",
	...props
}) => {
	const variantStyles = {
		default: "bg-surface-secondary text-primary-muted border-border",
		high: "bg-risk-highBg text-risk-high border-risk-highBorder font-semibold",
		warning:
			"bg-risk-warningBg text-risk-warning border-risk-warningBorder font-semibold",
		legit:
			"bg-risk-legitBg text-risk-legit border-risk-legitBorder font-semibold",
		approval:
			"bg-risk-approvalBg text-risk-approval border-risk-approvalBorder font-semibold",
		neutral: "bg-surface-secondary text-primary-muted border-border",
		accent: "bg-accent-light text-accent border-accent-border font-medium",
	}[variant];

	const sizeStyles = {
		sm: "text-[11px] px-2 py-0.5 rounded",
		md: "text-xs px-2.5 py-1 rounded-md",
	}[size];

	return (
		<span
			className={`inline-flex items-center gap-1.5 border font-mono tracking-tight ${variantStyles} ${sizeStyles} ${className}`}
			{...props}
		>
			{children}
		</span>
	);
};
