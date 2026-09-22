import type React from "react";
import type { HealthStatus } from "../api/types";

export type NavigationPage =
	| "overview"
	| "investigations"
	| "history"
	| "benchmark"
	| "policy"
	| "graph_explorer";

interface SidebarNavProps {
	activePage: NavigationPage;
	onSelectPage: (page: NavigationPage) => void;
	onOpenNewInvestigation: () => void;
	caseCount: number;
	health: HealthStatus | null;
	isCollapsed: boolean;
	onToggleCollapse: () => void;
}

export const SidebarNav: React.FC<SidebarNavProps> = ({
	activePage,
	onSelectPage,
	onOpenNewInvestigation,
	caseCount,
	health,
	isCollapsed,
	onToggleCollapse,
}) => {
	const isTgConnected = health?.tigergraph === "connected";

	const navItems = [
		{ id: "overview" as NavigationPage, label: "Overview", icon: "▣" },
		{
			id: "investigations" as NavigationPage,
			label: "Cases",
			icon: "▤",
			badge: caseCount,
		},
		{
			id: "history" as NavigationPage,
			label: "History",
			icon: "◷",
		},
		{ id: "benchmark" as NavigationPage, label: "Benchmark", icon: "▦" },
		{ id: "policy" as NavigationPage, label: "Policy & Patterns", icon: "▥" },
		{
			id: "graph_explorer" as NavigationPage,
			label: "Graph Explorer",
			icon: "◈",
		},
	];

	return (
		<aside
			style={{
				width: isCollapsed ? "64px" : "230px",
				backgroundColor: "#ffffff",
				borderRight: "1px solid #e2e8f0",
				display: "flex",
				flexDirection: "column",
				justifyContent: "space-between",
				height: "100vh",
				position: "sticky",
				top: 0,
				flexShrink: 0,
				userSelect: "none",
				zIndex: 20,
				transition: "width 0.2s ease",
			}}
		>
			{/* Top Section: Branding, Toggle, Primary Action, Nav List */}
			<div
				style={{
					display: "flex",
					flexDirection: "column",
					padding: isCollapsed ? "16px 8px" : "16px 14px",
					gap: "14px",
				}}
			>
				{/* Header Strip with Toggle */}
				<div
					style={{
						display: "flex",
						alignItems: "center",
						justifyContent: isCollapsed ? "center" : "space-between",
						padding: "2px 4px",
					}}
				>
					{!isCollapsed ? (
						<div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
							<div
								style={{
									width: "24px",
									height: "24px",
									borderRadius: "5px",
									backgroundColor: "#ea580c",
									color: "#ffffff",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									fontWeight: 800,
									fontSize: "13px",
								}}
							>
								T
							</div>
							<div style={{ display: "flex", flexDirection: "column" }}>
								<span
									style={{
										fontSize: "14px",
										fontWeight: 800,
										letterSpacing: "0.04em",
										color: "#0f172a",
										lineHeight: 1.1,
									}}
								>
									Console
								</span>
								<span style={{ fontSize: "10px", color: "#64748b", fontWeight: 500 }}>
									Fraud AI Workstation
								</span>
							</div>
						</div>
					) : (
						<div
							style={{
								width: "28px",
								height: "28px",
								borderRadius: "6px",
								backgroundColor: "#ea580c",
								color: "#ffffff",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								fontWeight: 800,
								fontSize: "14px",
							}}
							title="Tark Fraud AI"
						>
							T
						</div>
					)}

					{/* Collapse Toggle Button */}
					<button
						type="button"
						onClick={onToggleCollapse}
						style={{
							backgroundColor: "transparent",
							border: "1px solid #e2e8f0",
							borderRadius: "4px",
							width: "24px",
							height: "24px",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							cursor: "pointer",
							color: "#64748b",
							fontSize: "11px",
							transition: "all 0.15s ease",
							padding: 0,
							marginTop: isCollapsed ? "6px" : "0",
						}}
						title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
						onMouseEnter={(e) => {
							(e.currentTarget as HTMLElement).style.backgroundColor = "#f1f5f9";
							(e.currentTarget as HTMLElement).style.color = "#0f172a";
						}}
						onMouseLeave={(e) => {
							(e.currentTarget as HTMLElement).style.backgroundColor = "transparent";
							(e.currentTarget as HTMLElement).style.color = "#64748b";
						}}
					>
						{isCollapsed ? "»" : "«"}
					</button>
				</div>

				{/* Primary Action Button */}
				<button
					type="button"
					onClick={onOpenNewInvestigation}
					style={{
						width: "100%",
						padding: isCollapsed ? "8px 0" : "7px 12px",
						backgroundColor: "#ea580c",
						color: "#ffffff",
						fontSize: "12.5px",
						fontWeight: 600,
						borderRadius: "6px",
						border: "none",
						cursor: "pointer",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						gap: "6px",
						transition: "background-color 0.15s ease",
					}}
					title="New Investigation"
					onMouseEnter={(e) =>
						((e.currentTarget as HTMLElement).style.backgroundColor = "#c2410c")
					}
					onMouseLeave={(e) =>
						((e.currentTarget as HTMLElement).style.backgroundColor = "#ea580c")
					}
				>
					<span style={{ fontSize: "14px", lineHeight: 1 }}>+</span>
					{!isCollapsed && <span>New Investigation</span>}
				</button>

				{/* Navigation Items */}
				<nav style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
					{navItems.map((item) => {
						const isActive = activePage === item.id;
						return (
							<button
								type="button"
								key={item.id}
								onClick={() => onSelectPage(item.id)}
								title={isCollapsed ? item.label : undefined}
								style={{
									display: "flex",
									alignItems: "center",
									justifyContent: isCollapsed ? "center" : "space-between",
									padding: isCollapsed ? "9px 0" : "7px 10px",
									borderRadius: "6px",
									fontSize: "12.5px",
									fontWeight: isActive ? 600 : 500,
									color: isActive ? "#0f172a" : "#475569",
									backgroundColor: isActive ? "#f1f5f9" : "transparent",
									border: "none",
									cursor: "pointer",
									textAlign: "left",
									transition: "all 0.12s ease",
								}}
								onMouseEnter={(e) => {
									if (!isActive)
										(e.currentTarget as HTMLElement).style.backgroundColor =
											"#f8fafc";
								}}
								onMouseLeave={(e) => {
									if (!isActive)
										(e.currentTarget as HTMLElement).style.backgroundColor =
											"transparent";
								}}
							>
								<div
									style={{
										display: "flex",
										alignItems: "center",
										gap: isCollapsed ? "0" : "9px",
									}}
								>
									<span
										style={{
											fontSize: "14px",
											color: isActive ? "#ea580c" : "#64748b",
										}}
									>
										{item.icon}
									</span>
									{!isCollapsed && <span>{item.label}</span>}
								</div>

								{!isCollapsed && item.badge !== undefined && (
									<span
										style={{
											fontSize: "10px",
											fontWeight: 600,
											padding: "1px 5px",
											borderRadius: "10px",
											backgroundColor: isActive ? "#e2e8f0" : "#f1f5f9",
											color: isActive ? "#0f172a" : "#64748b",
										}}
									>
										{item.badge}
									</span>
								)}
							</button>
						);
					})}
				</nav>
			</div>

			{/* Bottom Pinned: System Status Strip */}
			{!isCollapsed ? (
				<div
					style={{
						padding: "12px 14px",
						borderTop: "1px solid #eef2f6",
						backgroundColor: "#fafbfc",
						fontSize: "11px",
						display: "flex",
						flexDirection: "column",
						gap: "5px",
					}}
				>
					<div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
						<span
							style={{
								width: "6px",
								height: "6px",
								borderRadius: "50%",
								backgroundColor: isTgConnected ? "#16a34a" : "#dc2626",
							}}
						/>
						<span style={{ color: "#334155", fontWeight: 600 }}>TigerGraph:</span>
						<span style={{ color: isTgConnected ? "#15803d" : "#b91c1c" }}>
							{isTgConnected ? "Connected" : "Offline"}
						</span>
					</div>

					<div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
						<span
							style={{
								width: "6px",
								height: "6px",
								borderRadius: "50%",
								backgroundColor: "#16a34a",
							}}
						/>
						<span style={{ color: "#334155", fontWeight: 600 }}>Engine:</span>
						<span style={{ color: "#64748b" }}>EVOI Planner</span>
					</div>
				</div>
			) : (
				<div
					style={{
						padding: "10px 0",
						borderTop: "1px solid #eef2f6",
						backgroundColor: "#fafbfc",
						display: "flex",
						justifyContent: "center",
					}}
					title={isTgConnected ? "TigerGraph Connected" : "TigerGraph Disconnected"}
				>
					<span
						style={{
							width: "8px",
							height: "8px",
							borderRadius: "50%",
							backgroundColor: isTgConnected ? "#16a34a" : "#dc2626",
						}}
					/>
				</div>
			)}
		</aside>
	);
};
