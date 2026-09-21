import { Loader2 } from "lucide-react";
import type React from "react";

export interface ButtonProps
	extends React.ButtonHTMLAttributes<HTMLButtonElement> {
	variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
	size?: "sm" | "md" | "lg";
	loading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
	children,
	variant = "primary",
	size = "md",
	loading = false,
	disabled,
	className = "",
	...props
}) => {
	const variantStyles = {
		primary:
			"bg-accent text-white hover:bg-accent-hover active:bg-accent-hover shadow-subtle",
		secondary:
			"bg-surface-secondary text-primary hover:bg-surface-tertiary border border-border",
		outline:
			"bg-surface text-primary hover:bg-surface-secondary border border-border",
		ghost:
			"bg-transparent text-primary-muted hover:text-primary hover:bg-surface-secondary",
		danger: "bg-risk-high text-white hover:bg-red-800",
	}[variant];

	const sizeStyles = {
		sm: "text-xs px-3 py-1.5 rounded-md gap-1.5 font-medium",
		md: "text-sm px-4 py-2 rounded-lg gap-2 font-medium",
		lg: "text-base px-5 py-2.5 rounded-lg gap-2.5 font-semibold",
	}[size];

	return (
		<button
			disabled={disabled || loading}
			className={`inline-flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:opacity-50 disabled:cursor-not-allowed ${variantStyles} ${sizeStyles} ${className}`}
			{...props}
		>
			{loading && <Loader2 className="w-4 h-4 animate-spin" />}
			{children}
		</button>
	);
};
