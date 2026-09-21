import type React from "react";

export interface CardProps
	extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
	title?: React.ReactNode;
	subtitle?: React.ReactNode;
	headerRight?: React.ReactNode;
	noPadding?: boolean;
}

export const Card: React.FC<CardProps> = ({
	title,
	subtitle,
	headerRight,
	children,
	noPadding = false,
	className = "",
	...props
}) => {
	return (
		<div
			className={`bg-surface border border-border rounded-lg shadow-card overflow-hidden ${className}`}
			{...props}
		>
			{(title || headerRight) && (
				<div className="px-5 py-3.5 border-b border-border bg-surface-secondary/40 flex items-center justify-between">
					<div>
						{title && (
							<h3 className="text-sm font-semibold text-primary flex items-center gap-2">
								{title}
							</h3>
						)}
						{subtitle && (
							<p className="text-xs text-primary-muted mt-0.5">{subtitle}</p>
						)}
					</div>
					{headerRight && <div>{headerRight}</div>}
				</div>
			)}
			<div className={noPadding ? "" : "p-5"}>{children}</div>
		</div>
	);
};
