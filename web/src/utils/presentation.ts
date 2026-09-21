/**
 * Tark Presentation Layer — Centralized Human-Readable Terminology & Formatting
 * 
 * Maps internal backend enums, GSQL queries, tool IDs, action codes,
 * and likelihood ratios into clear, professional banking & fraud analyst terminology.
 * 
 * STRICT RULE: Does NOT mutate backend data or enums; presentation transformation only.
 */

// 1. Tool & Graph Query Mappings
export interface ToolPresentation {
	title: string;
	shortName: string;
	checked: string;
	why: string;
	category: string;
	expectedBenefit: "High" | "Moderate" | "Standard";
}

export const TOOL_PRESENTATION_MAP: Record<string, ToolPresentation> = {
	QUERY_DEVICE_ANALYSIS: {
		title: "Shared-device network analysis",
		shortName: "Shared-device network",
		checked: "Device fingerprint and connected cardholder accounts.",
		why: "Evaluates whether multiple cards share the same hardware device or IP proxy.",
		category: "Hardware Syndicate",
		expectedBenefit: "High",
	},
	tool_device_analysis: {
		title: "Shared-device network analysis",
		shortName: "Shared-device network",
		checked: "Device fingerprint and connected cardholder accounts.",
		why: "Evaluates whether multiple cards share the same hardware device or IP proxy.",
		category: "Hardware Syndicate",
		expectedBenefit: "High",
	},
	device_analysis: {
		title: "Shared-device network analysis",
		shortName: "Shared-device network",
		checked: "Device fingerprint and connected cardholder accounts.",
		why: "Evaluates whether multiple cards share the same hardware device or IP proxy.",
		category: "Hardware Syndicate",
		expectedBenefit: "High",
	},
	QUERY_CARD_SEQUENCE: {
		title: "Card transaction pattern analysis",
		shortName: "Card transaction pattern",
		checked: "Sequence of authorizations and rapid micro-charges around the transaction.",
		why: "Detects automated bot testing sequences or micro-authorization probing.",
		category: "Pattern Sequence",
		expectedBenefit: "High",
	},
	tool_card_sequence: {
		title: "Card transaction pattern analysis",
		shortName: "Card transaction pattern",
		checked: "Sequence of authorizations and rapid micro-charges around the transaction.",
		why: "Detects automated bot testing sequences or micro-authorization probing.",
		category: "Pattern Sequence",
		expectedBenefit: "High",
	},
	card_sequence: {
		title: "Card transaction pattern analysis",
		shortName: "Card transaction pattern",
		checked: "Sequence of authorizations and rapid micro-charges around the transaction.",
		why: "Detects automated bot testing sequences or micro-authorization probing.",
		category: "Pattern Sequence",
		expectedBenefit: "High",
	},
	QUERY_TXN_VELOCITY: {
		title: "Transaction velocity assessment",
		shortName: "Transaction velocity",
		checked: "Spending frequency and cumulative volume across recent hourly windows.",
		why: "Checks whether transaction burst frequency exceeds the cardholder's historical baseline.",
		category: "Velocity",
		expectedBenefit: "Moderate",
	},
	tool_txn_velocity: {
		title: "Transaction velocity assessment",
		shortName: "Transaction velocity",
		checked: "Spending frequency and cumulative volume across recent hourly windows.",
		why: "Checks whether transaction burst frequency exceeds the cardholder's historical baseline.",
		category: "Velocity",
		expectedBenefit: "Moderate",
	},
	txn_velocity: {
		title: "Transaction velocity assessment",
		shortName: "Transaction velocity",
		checked: "Spending frequency and cumulative volume across recent hourly windows.",
		why: "Checks whether transaction burst frequency exceeds the cardholder's historical baseline.",
		category: "Velocity",
		expectedBenefit: "Moderate",
	},
	QUERY_REGION_ANALYSIS: {
		title: "Billing & geographic verification",
		shortName: "Billing & IP geography",
		checked: "Terminal billing region relative to cardholder registered home address.",
		why: "Identifies card-present transactions in unexpected geographic districts.",
		category: "Geography",
		expectedBenefit: "Moderate",
	},
	tool_region_analysis: {
		title: "Billing & geographic verification",
		shortName: "Billing & IP geography",
		checked: "Terminal billing region relative to cardholder registered home address.",
		why: "Identifies card-present transactions in unexpected geographic districts.",
		category: "Geography",
		expectedBenefit: "Moderate",
	},
	region_analysis: {
		title: "Billing & geographic verification",
		shortName: "Billing & IP geography",
		checked: "Terminal billing region relative to cardholder registered home address.",
		why: "Identifies card-present transactions in unexpected geographic districts.",
		category: "Geography",
		expectedBenefit: "Moderate",
	},
	QUERY_CUSTOMER_PROFILE: {
		title: "Customer activity profile",
		shortName: "Customer activity profile",
		checked: "Customer tenure, registered cards, and typical spending behavior.",
		why: "Establishes long-term account baseline for anomaly scoring.",
		category: "Profile",
		expectedBenefit: "Standard",
	},
	tool_customer_profile: {
		title: "Customer activity profile",
		shortName: "Customer activity profile",
		checked: "Customer activity profile",
		why: "Establishes long-term account baseline for anomaly scoring.",
		category: "Profile",
		expectedBenefit: "Standard",
	},
	customer_profile: {
		title: "Customer activity profile",
		shortName: "Customer activity profile",
		checked: "Customer activity profile",
		why: "Establishes long-term account baseline for anomaly scoring.",
		category: "Profile",
		expectedBenefit: "Standard",
	},
	RETRIEVE_HISTORICAL_CASES: {
		title: "Institutional case memory retrieval",
		shortName: "Similar past cases",
		checked: "Historical fraud investigations with matching behavioral patterns.",
		why: "Compares current transaction topology against verified precedent outcomes.",
		category: "Case Memory",
		expectedBenefit: "Moderate",
	},
	tool_similar_cases: {
		title: "Institutional case memory retrieval",
		shortName: "Similar past cases",
		checked: "Historical fraud investigations with matching behavioral patterns.",
		why: "Compares current transaction topology against verified precedent outcomes.",
		category: "Case Memory",
		expectedBenefit: "Moderate",
	},
	similar_cases: {
		title: "Institutional case memory retrieval",
		shortName: "Similar past cases",
		checked: "Historical fraud investigations with matching behavioral patterns.",
		why: "Compares current transaction topology against verified precedent outcomes.",
		category: "Case Memory",
		expectedBenefit: "Moderate",
	},
	VERIFY_WITH_CUSTOMER: {
		title: "Cardholder direct verification",
		shortName: "Customer verification",
		checked: "Out-of-band transaction confirmation channel (SMS/push).",
		why: "Resolves remaining uncertainty directly with the cardholder.",
		category: "Direct Confirmation",
		expectedBenefit: "High",
	},
	simulate_customer_reply: {
		title: "Cardholder direct verification",
		shortName: "Customer verification",
		checked: "Out-of-band transaction confirmation channel (SMS/push).",
		why: "Resolves remaining uncertainty directly with the cardholder.",
		category: "Direct Confirmation",
		expectedBenefit: "High",
	},
	QUERY_POLICY_GRAPH: {
		title: "Compliance & policy rules",
		shortName: "Policy compliance",
		checked: "Bank fraud policy and federal regulatory statutes.",
		why: "Validates statutory requirements and mandatory reporting thresholds.",
		category: "Governance",
		expectedBenefit: "Standard",
	},
};

export function getToolPresentation(rawTool: string): ToolPresentation {
	if (!rawTool) {
		return {
			title: "Investigation analysis",
			shortName: "Investigation check",
			checked: "Graph entity relations and transaction attributes.",
			why: "Investigates context to resolve case uncertainty.",
			category: "General",
			expectedBenefit: "Standard",
		};
	}

	if (TOOL_PRESENTATION_MAP[rawTool]) {
		return TOOL_PRESENTATION_MAP[rawTool];
	}

	const normalized = rawTool.toUpperCase();
	for (const key of Object.keys(TOOL_PRESENTATION_MAP)) {
		if (normalized.includes(key) || key.includes(normalized)) {
			return TOOL_PRESENTATION_MAP[key];
		}
	}

	const humanTitle = rawTool
		.replace(/^(tool_|QUERY_)/i, "")
		.replace(/_/g, " ")
		.replace(/\b\w/g, (c) => c.toUpperCase());

	return {
		title: humanTitle,
		shortName: humanTitle,
		checked: "Transaction and connected account signals.",
		why: "Evaluated to reduce remaining case uncertainty.",
		category: "Graph Signal",
		expectedBenefit: "Standard",
	};
}

// 2. Policy Action Terminology
export interface ActionPresentation {
	title: string;
	shortTitle: string;
	description: string;
	urgency: "high" | "medium" | "low";
}

export const ACTION_PRESENTATION_MAP: Record<string, ActionPresentation> = {
	DECLINE_TRANSACTION: {
		title: "Decline transaction",
		shortTitle: "Decline transaction",
		description: "Block the authorization attempt immediately to prevent loss.",
		urgency: "high",
	},
	BLOCK_CARD: {
		title: "Decline transaction & block card",
		shortTitle: "Decline & block card",
		description: "Decline the transaction and suspend the card to prevent further unauthorized use.",
		urgency: "high",
	},
	FREEZE_ACCOUNT: {
		title: "Freeze account",
		shortTitle: "Freeze account",
		description: "Temporarily restrict all activity across the cardholder account.",
		urgency: "high",
	},
	MONITOR_CARD: {
		title: "Monitor account activity",
		shortTitle: "Monitor account",
		description: "Permit transaction with enhanced monitoring for subsequent abnormal transactions.",
		urgency: "medium",
	},
	REQUEST_CUSTOMER_VERIFICATION: {
		title: "Request customer verification",
		shortTitle: "Verify with customer",
		description: "Contact the account owner via out-of-band channel to confirm transaction legitimacy.",
		urgency: "medium",
	},
	STEP_UP_AUTH: {
		title: "Request step-up authentication",
		shortTitle: "Step-up authentication",
		description: "Prompt the cardholder for two-factor or biometric verification.",
		urgency: "medium",
	},
	FILE_SAR: {
		title: "File Suspicious Activity Report (SAR)",
		shortTitle: "File SAR",
		description: "Submit FinCEN Form 111 documentation to compliance for suspicious transaction patterns.",
		urgency: "high",
	},
	CLOSE_NO_FRAUD: {
		title: "Clear transaction (no fraud)",
		shortTitle: "Clear transaction",
		description: "Mark transaction legitimate based on conclusive exculpatory evidence.",
		urgency: "low",
	},
	ESCALATE_TO_ANALYST: {
		title: "Escalate to senior fraud analyst",
		shortTitle: "Escalate to analyst",
		description: "Transfer case to fraud operations lead for specialized review.",
		urgency: "medium",
	},
	NOTIFY_CARDHOLDER: {
		title: "Notify cardholder of suspicious activity",
		shortTitle: "Notify cardholder",
		description: "Send automated security alert to cardholder regarding flagged transaction.",
		urgency: "low",
	},
};

export function formatActionTitle(rawAction: string): string {
	if (!rawAction) return "Review transaction";
	const normalized = rawAction.toUpperCase().replace(/\s+/g, "_");
	if (ACTION_PRESENTATION_MAP[normalized]) {
		return ACTION_PRESENTATION_MAP[normalized].title;
	}
	return rawAction
		.replace(/_/g, " ")
		.toLowerCase()
		.replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatActionShort(rawAction: string): string {
	if (!rawAction) return "Review";
	const normalized = rawAction.toUpperCase().replace(/\s+/g, "_");
	if (ACTION_PRESENTATION_MAP[normalized]) {
		return ACTION_PRESENTATION_MAP[normalized].shortTitle;
	}
	return formatActionTitle(rawAction);
}

// 3. Approval Route Mappings
export function formatApprovalRoute(route?: string): {
	label: string;
	isAuto: boolean;
	badgeBg: string;
	badgeText: string;
	badgeBorder: string;
} {
	if (!route || route.toLowerCase() === "auto") {
		return {
			label: "Automatic execution permitted",
			isAuto: true,
			badgeBg: "#f0fdf4",
			badgeText: "#15803d",
			badgeBorder: "#bbf7d0",
		};
	}

	const normalized = route.toLowerCase();
	let roleLabel = "Fraud analyst approval required";
	if (normalized.includes("lead") || normalized.includes("senior")) {
		roleLabel = "Fraud lead approval required";
	} else if (normalized.includes("executive") || normalized.includes("manager")) {
		roleLabel = "Management approval required";
	} else if (normalized.includes("l1")) {
		roleLabel = "Tier 1 analyst approval required";
	} else if (normalized.includes("l2")) {
		roleLabel = "Senior analyst approval required";
	}

	return {
		label: roleLabel,
		isAuto: false,
		badgeBg: "#fffbeb",
		badgeText: "#b45309",
		badgeBorder: "#fde68a",
	};
}

// 4. Action Role Mappings
export function formatActionRole(role?: string): string {
	if (!role) return "Recommended action";
	const lower = role.toLowerCase();
	if (lower === "primary") return "Primary action";
	if (lower === "consequential" || lower === "secondary") return "Follow-up action";
	return `${role.replace(/_/g, " ")} action`;
}

// 5. Target Scope Mappings
export function formatScope(scope?: string): string {
	if (!scope) return "Transaction";
	const lower = scope.toLowerCase();
	if (lower.includes("txn") || lower.includes("transaction")) return "Transaction authorization";
	if (lower.includes("card")) return "Card account";
	if (lower.includes("customer")) return "Customer account";
	if (lower.includes("device")) return "Device & hardware profile";
	if (lower.includes("case")) return "Case management record";
	return scope.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// 6. Evidence Signal Impact Formatting
export interface EvidenceImpactPresentation {
	label: string;
	level: "strong_inculpatory" | "moderate_inculpatory" | "neutral" | "exculpatory" | "unavailable";
	description: string;
	badgeBg: string;
	badgeText: string;
	badgeBorder: string;
	symbol: string;
}

export function formatEvidenceImpact(
	lr: number = 1.0,
	isExculpatory: boolean = false,
	isUnavailable: boolean = false
): EvidenceImpactPresentation {
	if (isUnavailable) {
		return {
			label: "Channel unavailable",
			level: "unavailable",
			description: "Cardholder communication could not be reached",
			badgeBg: "#f8fafc",
			badgeText: "#64748b",
			badgeBorder: "#e2e8f0",
			symbol: "—",
		};
	}

	if (isExculpatory || (lr < 0.8 && lr > 0)) {
		return {
			label: "Reduces fraud risk",
			level: "exculpatory",
			description: "Exculpatory signal consistent with legitimate cardholder activity",
			badgeBg: "#f0fdf4",
			badgeText: "#15803d",
			badgeBorder: "#bbf7d0",
			symbol: "↓",
		};
	}

	if (lr >= 3.0) {
		return {
			label: "Strongly increases fraud risk",
			level: "strong_inculpatory",
			description: "Strong abnormal indicator heavily skewing risk assessment",
			badgeBg: "#fff7ed",
			badgeText: "#c2410c",
			badgeBorder: "#fed7aa",
			symbol: "↑↑",
		};
	}

	if (lr >= 1.4) {
		return {
			label: "Moderately increases fraud risk",
			level: "moderate_inculpatory",
			description: "Supporting suspicious signal elevating case risk",
			badgeBg: "#fefce8",
			badgeText: "#ca8a04",
			badgeBorder: "#fef08a",
			symbol: "↑",
		};
	}

	return {
		label: "Neutral finding",
		level: "neutral",
		description: "Within normal expected cardholder variance",
		badgeBg: "#f1f5f9",
		badgeText: "#475569",
		badgeBorder: "#e2e8f0",
		symbol: "→",
	};
}

// 7. Uncertainty Level Formatting
export function formatUncertaintyLevel(val: number): {
	label: string;
	text: string;
	level: "low" | "moderate" | "elevated";
} {
	if (val <= 0.25) {
		return { label: "Low", text: "High evidentiary confidence", level: "low" };
	}
	if (val <= 0.4) {
		return { label: "Moderate", text: "Minor remaining ambiguity", level: "moderate" };
	}
	return { label: "Elevated", text: "Substantial incomplete evidence", level: "elevated" };
}

// 8. Decision Gate Status Formatting
export interface GateStatusPresentation {
	badge: string;
	subtext: string;
	isReady: boolean;
	bg: string;
	text: string;
	border: string;
}

export function formatDecisionGateStatus(
	gatePassed: boolean,
	decisionState: string = "PENDING",
	approvalRoute?: string
): GateStatusPresentation {
	if (decisionState === "INSUFFICIENT_EVIDENCE" || (!gatePassed && decisionState !== "REQUIRES_HUMAN_APPROVAL")) {
		return {
			badge: "MORE EVIDENCE REQUIRED",
			subtext: "Automated action withheld due to incomplete evidence coverage",
			isReady: false,
			bg: "#f8fafc",
			text: "#475569",
			border: "#cbd5e1",
		};
	}

	if (decisionState === "REQUIRES_HUMAN_APPROVAL" || (gatePassed && approvalRoute && approvalRoute !== "auto")) {
		return {
			badge: "ANALYST APPROVAL REQUIRED",
			subtext: approvalRoute ? `Policy mandates ${approvalRoute.toUpperCase()} sign-off` : "Policy requires analyst sign-off",
			isReady: true,
			bg: "#fffbeb",
			text: "#b45309",
			border: "#fde68a",
		};
	}

	if (gatePassed) {
		return {
			badge: "DECISION READY",
			subtext: "Evidence criteria satisfied · Policy permits autonomous execution",
			isReady: true,
			bg: "#f0fdf4",
			text: "#15803d",
			border: "#bbf7d0",
		};
	}

	return {
		badge: "EVALUATING",
		subtext: "Investigation in progress",
		isReady: false,
		bg: "#f8fafc",
		text: "#475569",
		border: "#e2e8f0",
	};
}

// 9. Source Formatting
export function formatEvidenceSource(source?: string): string {
	if (!source) return "Internal Risk System";
	if (source.includes("device_analysis")) return "TigerGraph (Device Network)";
	if (source.includes("card_sequence")) return "TigerGraph (Transaction Sequence)";
	if (source.includes("txn_velocity")) return "TigerGraph (Velocity Radar)";
	if (source.includes("region_analysis")) return "TigerGraph (Geographic Distance)";
	if (source.includes("customer_profile")) return "TigerGraph (Customer Profile)";
	if (source.includes("similar_cases")) return "TigerGraph (Precedent Match)";
	if (source.includes("tigergraph")) return "TigerGraph Graph Database";
	if (source.includes("bank_detection_model")) return "Bank Real-Time Detection Model";
	if (source.includes("customer_report")) return "Inbound Customer Alert";
	if (source.includes("simulate_customer_reply") || source.includes("gateway")) return "Cardholder Verification Gateway";
	return source.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// 10. Clean Text Helpers
export function cleanFindingText(finding: string): string {
	if (!finding) return "";
	const colonIndex = finding.indexOf(": ");
	if (colonIndex !== -1 && (finding.includes("LR=") || finding.includes("("))) {
		return finding.slice(colonIndex + 2).trim();
	}
	return finding;
}

export function cleanReasonText(reason: string): string {
	if (!reason) return "";
	return reason.replace(/^R\d+:\s*/i, "").trim();
}

export function formatEvidenceId(evId?: string, index?: number): string {
	if (!evId) return index !== undefined ? `Evidence #${index + 1}` : "Evidence item";
	if (index !== undefined) {
		return `Evidence #${index + 1}`;
	}
	return "Evidence item";
}

// 11. Termination Reason Presentation
export function formatTerminationReason(reason?: string): { title: string; explanation: string } {
	switch (reason) {
		case "DECISION_REACHED":
			return {
				title: "Investigation complete",
				explanation: "Evidence threshold satisfied for policy decision.",
			};
		case "NO_ADMISSIBLE_EVIDENCE":
			return {
				title: "Investigation stopped",
				explanation: "No additional admissible evidence actions available.",
			};
		case "MAX_STEPS_REACHED":
			return {
				title: "Investigation stopped",
				explanation: "Investigation reached the maximum allowed step limit.",
			};
		case "NEGATIVE_EVOI":
			return {
				title: "Investigation stopped",
				explanation: "Remaining actions had non-positive expected information value.",
			};
		case "CONSECUTIVE_FAILURES":
			return {
				title: "Investigation stopped",
				explanation: "Consecutive query limit reached.",
			};
		default:
			return {
				title: "Investigation complete",
				explanation: "Autonomous inquiry concluded.",
			};
	}
}

