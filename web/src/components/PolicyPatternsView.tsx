import type React from "react";
import { useMemo, useState } from "react";

interface PolicyRule {
	id: string;
	name: string;
	action: string;
	approvalRoute: "auto" | "L1" | "L2";
	precondition: string;
	section: string;
	typology: string;
	statute: string;
}

const POLICY_RULES: PolicyRule[] = [
	{
		id: "R1",
		name: "Weak Single Signal Verification Mandate",
		action: "VERIFY_WITH_CUSTOMER",
		approvalRoute: "auto",
		precondition:
			"P(Fraud) < 0.70 with single uncorroborated signal; punitive blocks prohibited",
		section: "Risk Policy Manual § 4.1",
		typology: "Borderline / Single Signal",
		statute: "Bank Risk Governance § 4.1",
	},
	{
		id: "R2",
		name: "Customer Direct Dispute / Transaction Denial",
		action: "BLOCK_CARD",
		approvalRoute: "L1",
		precondition:
			"Inbound cardholder denial or dispute confirmed on active card",
		section: "Risk Policy Manual § 4.2",
		typology: "Direct Cardholder Denial",
		statute: "Regulation E (12 CFR § 1005.6) & FinCEN (31 CFR § 1020.320)",
	},
	{
		id: "R3",
		name: "Cardholder Legitimate Transaction Confirmation",
		action: "ALLOW_TRANSACTION",
		approvalRoute: "auto",
		precondition:
			"Cardholder explicitly confirms transaction as legitimate and authorized",
		section: "Risk Policy Manual § 4.3",
		typology: "Confirmed Legitimate / Travel",
		statute: "Bank Risk Governance § 4.3",
	},
	{
		id: "R4",
		name: "Out-of-Region Card-Present Activity",
		action: "DECLINE_TRANSACTION",
		approvalRoute: "L1",
		precondition:
			"Card-present authorization > 1,000km from registered profile address",
		section: "Risk Policy Manual § 4.4",
		typology: "Geographic Displacement",
		statute: "Bank Risk Governance § 4.4",
	},
	{
		id: "R5",
		name: "Card Testing Micro-Authorization Sequence",
		action: "DECLINE_TRANSACTION",
		approvalRoute: "L1",
		precondition:
			"≥ 2 micro-authorizations ($0-$2) followed by clearing charge over $100",
		section: "Risk Policy Manual § 4.5",
		typology: "Card Testing Probing",
		statute: "Bank Risk Governance § 5.1",
	},
	{
		id: "R6",
		name: "Multi-Card Shared Device Syndicate Ring",
		action: "CREATE_CASE",
		approvalRoute: "L2",
		precondition:
			"Shared device hardware profile linked to ≥ 3 distinct cardholders",
		section: "Risk Policy Manual § 4.6",
		typology: "Hardware Syndicate Ring",
		statute: "FinCEN Mandate (31 CFR § 1020.320)",
	},
	{
		id: "R7",
		name: "Recurring Merchant Charge Dispute Resolution",
		action: "ALLOW_TRANSACTION",
		approvalRoute: "auto",
		precondition:
			"Disputed charge matches verified historical subscription periodicity",
		section: "Risk Policy Manual § 4.7",
		typology: "Recurring Subscription Cadence",
		statute: "Regulation E (12 CFR § 1005.11)",
	},
	{
		id: "R8",
		name: "High Exposure Value Under Uncertainty",
		action: "MONITOR_CARD",
		approvalRoute: "L1",
		precondition:
			"0.30 < P(Fraud) < 0.70 with transaction exposure exceeding $500 threshold",
		section: "Risk Policy Manual § 4.8",
		typology: "High Exposure Under Uncertainty",
		statute: "Bank Risk Governance § 4.8",
	},
	{
		id: "R9",
		name: "High Risk on Undocumented / Novel Pattern",
		action: "CREATE_CASE",
		approvalRoute: "L2",
		precondition:
			"P(Fraud) ≥ 0.70 with evidence of coordinated abuse fitting no standard typology",
		section: "Risk Policy Manual § 4.9",
		typology: "Novel / Coordinated Abuse",
		statute: "L2 Senior Fraud Manager Protocol § 4.9",
	},
	{
		id: "R10",
		name: "Calibrated Bayesian Operational Dispositions",
		action: "ALLOW_TRANSACTION",
		approvalRoute: "auto",
		precondition:
			"General disposition governance: P(Fraud) < 0.30 clear, ≥ 0.70 escalate",
		section: "Risk Policy Manual § 4.10",
		typology: "Bayesian Baseline Governance",
		statute: "Bank Risk Governance § 4.10",
	},
];

export const PolicyPatternsView: React.FC = () => {
	const [searchQuery, setSearchQuery] = useState("");
	const [selectedAction, setSelectedAction] = useState<string>("all");

	const filteredRules = useMemo(() => {
		return POLICY_RULES.filter((rule) => {
			const matchesSearch =
				rule.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
				rule.precondition.toLowerCase().includes(searchQuery.toLowerCase()) ||
				rule.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
				rule.typology.toLowerCase().includes(searchQuery.toLowerCase()) ||
				rule.statute.toLowerCase().includes(searchQuery.toLowerCase());

			const matchesAction =
				selectedAction === "all" || rule.action === selectedAction;

			return matchesSearch && matchesAction;
		});
	}, [searchQuery, selectedAction]);

	return (
		<div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
			{/* Header */}
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
					Institutional Fraud Policy Rules & Typologies
				</h1>
				<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
					Deterministic bank risk policies (R1–R10) governing autonomous next best
					actions, authorization roles, and multi-tiered human approval routes
				</p>
			</div>

			{/* Filters */}
			<div
				style={{
					display: "flex",
					gap: "12px",
					backgroundColor: "#ffffff",
					padding: "12px 16px",
					borderRadius: "8px",
					border: "1px solid #e2e8f0",
				}}
			>
				<input
					type="text"
					placeholder="Search by rule, typology, statutory mandate, or precondition..."
					value={searchQuery}
					onChange={(e) => setSearchQuery(e.target.value)}
					style={{
						flex: 1,
						padding: "6px 12px",
						fontSize: "13px",
						border: "1px solid #cbd5e1",
						borderRadius: "4px",
						outline: "none",
					}}
				/>

				<select
					value={selectedAction}
					onChange={(e) => setSelectedAction(e.target.value)}
					style={{
						padding: "6px 12px",
						fontSize: "13px",
						border: "1px solid #cbd5e1",
						borderRadius: "4px",
						outline: "none",
						backgroundColor: "#ffffff",
						color: "#334155",
					}}
				>
					<option value="all">All Actions</option>
					<option value="BLOCK_CARD">BLOCK_CARD</option>
					<option value="DECLINE_TRANSACTION">DECLINE_TRANSACTION</option>
					<option value="CREATE_CASE">CREATE_CASE</option>
					<option value="ALLOW_TRANSACTION">ALLOW_TRANSACTION</option>
					<option value="VERIFY_WITH_CUSTOMER">VERIFY_WITH_CUSTOMER</option>
					<option value="MONITOR_CARD">MONITOR_CARD</option>
				</select>
			</div>

			{/* Rules List */}
			<div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
				{filteredRules.map((rule) => (
					<div
						key={rule.id}
						style={{
							backgroundColor: "#ffffff",
							borderRadius: "8px",
							border: "1px solid #e2e8f0",
							padding: "16px 20px",
							display: "flex",
							flexDirection: "column",
							gap: "8px",
							boxShadow: "0 1px 2px rgba(0, 0, 0, 0.02)",
						}}
					>
						<div
							style={{
								display: "flex",
								justifyContent: "space-between",
								alignItems: "center",
							}}
						>
							<div
								style={{ display: "flex", alignItems: "center", gap: "10px" }}
							>
								<span
									style={{
										fontSize: "12px",
										fontWeight: 700,
										padding: "2px 8px",
										borderRadius: "4px",
										backgroundColor: "#fff7ed",
										color: "#ea580c",
										border: "1px solid #ffedd5",
									}}
								>
									{rule.id}
								</span>
								<span
									style={{
										fontSize: "14px",
										fontWeight: 700,
										color: "#0f172a",
									}}
								>
									{rule.name}
								</span>
							</div>

							<div
								style={{ display: "flex", alignItems: "center", gap: "8px" }}
							>
								<span style={{ fontSize: "11px", color: "#64748b" }}>
									Mandates:{" "}
									<strong style={{ color: "#0f172a" }}>{rule.action}</strong>
								</span>
								<span
									style={{
										fontSize: "10px",
										fontWeight: 700,
										padding: "2px 6px",
										borderRadius: "3px",
										backgroundColor:
											rule.approvalRoute === "auto" ? "#f0fdf4" : "#fffbeb",
										color:
											rule.approvalRoute === "auto" ? "#15803d" : "#b45309",
										border: `1px solid ${rule.approvalRoute === "auto" ? "#bbf7d0" : "#fde68a"}`,
										textTransform: "uppercase",
									}}
								>
									{rule.approvalRoute}
								</span>
							</div>
						</div>

						<div style={{ fontSize: "13px", color: "#334155" }}>
							<strong>Precondition: </strong> {rule.precondition}
						</div>

						<div
							style={{
								display: "flex",
								justifyContent: "space-between",
								alignItems: "center",
								paddingTop: "6px",
								borderTop: "1px solid #f8fafc",
								fontSize: "11px",
								color: "#64748b",
							}}
						>
							<div>
								<span>Source: </span>
								<span style={{ color: "#475569", fontWeight: 600 }}>
									{rule.section}
								</span>
								<span style={{ marginLeft: "12px" }}>Typology: </span>
								<span style={{ color: "#0f172a", fontWeight: 600 }}>
									{rule.typology}
								</span>
							</div>

							<div>
								<span>Governing Statute: </span>
								<span style={{ color: "#0f172a", fontWeight: 600 }}>
									{rule.statute}
								</span>
							</div>
						</div>
					</div>
				))}
			</div>
		</div>
	);
};
