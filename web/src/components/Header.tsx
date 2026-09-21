import type React from "react";
import type { HealthStatus } from "../api/types";

interface HeaderProps {
	health: HealthStatus | null;
	onNavigateHome?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ health, onNavigateHome }) => {
	const isTgConnected = health?.tigergraph === "connected";

	return (
		<header
			style={{
				backgroundColor: "#ffffff",
				borderBottom: "1px solid #e2e8f0",
				width: "100%",
			}}
		>
			<div
				style={{
					maxWidth: "1680px",
					width: "calc(100% - 48px)",
					margin: "0 auto",
					padding: "12px 0",
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
				}}
			>
				{/* Brand & System Descriptor */}
				<div
					onClick={onNavigateHome}
					style={{
						cursor: onNavigateHome ? "pointer" : "default",
						display: "flex",
						alignItems: "center",
						gap: "12px",
						userSelect: "none",
					}}
				>
					<div
						style={{
							fontSize: "17px",
							fontWeight: 800,
							letterSpacing: "0.06em",
							color: "#0f172a",
							display: "flex",
							alignItems: "center",
							gap: "8px",
						}}
					>
						<span>TARK</span>
						<span
							style={{
								fontSize: "10px",
								fontWeight: 700,
								padding: "2px 5px",
								borderRadius: "3px",
								backgroundColor: "#fff7ed",
								color: "#ea580c",
								border: "1px solid #ffedd5",
								letterSpacing: "0.06em",
							}}
						>
							FRAUD AI
						</span>
					</div>
					<div
						style={{ width: "1px", height: "14px", backgroundColor: "#cbd5e1" }}
					/>
					<span style={{ fontSize: "13px", color: "#64748b", fontWeight: 500 }}>
						Autonomous TigerGraph Fraud Investigation
					</span>
				</div>

				{/* Live TigerGraph Status Indicator */}
				<div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
					<div
						style={{
							fontSize: "11.5px",
							display: "inline-flex",
							alignItems: "center",
							gap: "6px",
							padding: "4px 10px",
							borderRadius: "4px",
							backgroundColor: isTgConnected ? "#f0fdf4" : "#fef2f2",
							color: isTgConnected ? "#15803d" : "#b91c1c",
							border: `1px solid ${isTgConnected ? "#bbf7d0" : "#fecaca"}`,
							fontWeight: 600,
							letterSpacing: "0.02em",
						}}
					>
						<span
							style={{
								display: "inline-block",
								width: "6px",
								height: "6px",
								borderRadius: "50%",
								backgroundColor: isTgConnected ? "#16a34a" : "#dc2626",
							}}
						/>
						<span>
							TigerGraph: {isTgConnected ? "CONNECTED" : "DISCONNECTED"}
						</span>
					</div>
				</div>
			</div>
		</header>
	);
};
