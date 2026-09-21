import React, { useState } from "react";

export interface TechnicalDetailItem {
	label: string;
	value: React.ReactNode;
}

interface TechnicalDetailsProps {
	title?: string;
	items?: TechnicalDetailItem[];
	summaryItems?: TechnicalDetailItem[];
	rawPayload?: any;
	defaultOpen?: boolean;
	style?: React.CSSProperties;
}

export const TechnicalDetails: React.FC<TechnicalDetailsProps> = ({
	title = "Technical details",
	items = [],
	summaryItems,
	rawPayload,
	defaultOpen = false,
	style = {},
}) => {
	const [isOpen, setIsOpen] = useState(defaultOpen);
	const [copied, setCopied] = useState(false);

	const effectiveItems = items.length > 0 ? items : (summaryItems || []);
	const hasContent = effectiveItems.length > 0 || rawPayload !== undefined;

	if (!hasContent) return null;

	const handleCopyPayload = (e: React.MouseEvent) => {
		e.stopPropagation();
		if (!rawPayload) return;
		navigator.clipboard.writeText(JSON.stringify(rawPayload, null, 2));
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	};

	return (
		<div
			style={{
				display: "flex",
				flexDirection: "column",
				gap: "6px",
				marginTop: "4px",
				...style,
			}}
		>
			<button
				type="button"
				onClick={() => setIsOpen(!isOpen)}
				style={{
					background: "none",
					border: "none",
					padding: "3px 0",
					display: "inline-flex",
					alignItems: "center",
					gap: "5px",
					fontSize: "11px",
					fontWeight: 600,
					color: "#64748b",
					cursor: "pointer",
					textAlign: "left",
					width: "fit-content",
					transition: "color 0.15s ease",
				}}
				onMouseEnter={(e) => {
					(e.currentTarget as HTMLElement).style.color = "#ea580c";
				}}
				onMouseLeave={(e) => {
					(e.currentTarget as HTMLElement).style.color = "#64748b";
				}}
			>
				<span style={{ fontSize: "9px" }}>{isOpen ? "▼" : "▶"}</span>
				<span>{isOpen ? `Hide ${title.toLowerCase()}` : `View ${title.toLowerCase()}`}</span>
			</button>

			{isOpen && (
				<div
					style={{
						padding: "10px 12px",
						backgroundColor: "#f8fafc",
						borderRadius: "6px",
						border: "1px solid #e2e8f0",
						fontSize: "11px",
						fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
						color: "#334155",
						display: "flex",
						flexDirection: "column",
						gap: "6px",
					}}
				>
					{/* Structured Key-Value Items */}
					{effectiveItems && effectiveItems.length > 0 && (
						<div
							style={{
								display: "grid",
								gridTemplateColumns: "minmax(120px, auto) 1fr",
								gap: "4px 12px",
								alignItems: "baseline",
							}}
						>
							{effectiveItems.map((item, idx) => (
								<React.Fragment key={idx}>
									<span style={{ color: "#64748b", fontWeight: 600 }}>{item.label}:</span>
									<span style={{ color: "#0f172a", wordBreak: "break-all" }}>{item.value}</span>
								</React.Fragment>
							))}
						</div>
					)}

					{/* Formatted JSON Raw Payload (Only when explicitly provided) */}
					{rawPayload !== undefined && (
						<div style={{ marginTop: effectiveItems && effectiveItems.length > 0 ? "6px" : "0px" }}>
							<div
								style={{
									display: "flex",
									justifyContent: "space-between",
									alignItems: "center",
									marginBottom: "4px",
								}}
							>
								<span style={{ fontSize: "10px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>
									Raw Payload
								</span>
								<button
									type="button"
									onClick={handleCopyPayload}
									style={{
										background: "none",
										border: "1px solid #cbd5e1",
										borderRadius: "3px",
										padding: "1px 6px",
										fontSize: "9.5px",
										color: copied ? "#15803d" : "#475569",
										cursor: "pointer",
										backgroundColor: copied ? "#f0fdf4" : "#ffffff",
									}}
								>
									{copied ? "Copied ✓" : "Copy JSON"}
								</button>
							</div>
							<pre
								style={{
									margin: 0,
									padding: "8px 10px",
									backgroundColor: "#ffffff",
									borderRadius: "4px",
									border: "1px solid #cbd5e1",
									fontSize: "10px",
									lineHeight: "1.4",
									color: "#0f172a",
									maxHeight: "180px",
									overflowY: "auto",
									whiteSpace: "pre-wrap",
									wordBreak: "break-all",
								}}
							>
								{typeof rawPayload === "string" ? rawPayload : JSON.stringify(rawPayload, null, 2)}
							</pre>
						</div>
					)}
				</div>
			)}
		</div>
	);
};
