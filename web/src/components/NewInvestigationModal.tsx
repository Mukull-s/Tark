import type React from "react";
import { useState } from "react";
import type { CaseMetadata } from "../api/types";

interface NewInvestigationModalProps {
	isOpen: boolean;
	onClose: () => void;
	onStartInvestigation: (caseId: string) => void;
	onStartTransactionInvestigation?: (txnId: string) => void;
	cases: CaseMetadata[];
}

export const NewInvestigationModal: React.FC<NewInvestigationModalProps> = ({
	isOpen,
	onClose,
	onStartInvestigation,
	onStartTransactionInvestigation,
	cases,
}) => {
	const [activeTab, setActiveTab] = useState<"queue" | "arbitrary">("queue");
	const [selectedCaseId, setSelectedCaseId] = useState(
		cases[0]?.case_id || "HHG-001",
	);
	const [arbitraryTxnId, setArbitraryTxnId] = useState("");
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);

	if (!isOpen) return null;

	const handleSubmit = async () => {
		setError(null);
		if (activeTab === "queue") {
			onStartInvestigation(selectedCaseId);
			onClose();
		} else {
			const cleanTxn = arbitraryTxnId.trim();
			if (!cleanTxn) {
				setError("Please enter a valid Transaction ID.");
				return;
			}
			if (onStartTransactionInvestigation) {
				setIsSubmitting(true);
				try {
					await onStartTransactionInvestigation(cleanTxn);
					onClose();
				} catch (err) {
					setError(err instanceof Error ? err.message : "Investigation failed");
				} finally {
					setIsSubmitting(false);
				}
			} else {
				onStartInvestigation(`TXN-${cleanTxn}`);
				onClose();
			}
		}
	};

	return (
		<div
			data-testid="new-investigation-modal"
			style={{
				position: "fixed",
				top: 0,
				left: 0,
				right: 0,
				bottom: 0,
				backgroundColor: "rgba(15, 23, 42, 0.45)",
				display: "flex",
				alignItems: "center",
				justifyContent: "center",
				zIndex: 50,
			}}
		>
			<div
				style={{
					backgroundColor: "#ffffff",
					borderRadius: "10px",
					padding: "24px",
					width: "480px",
					boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
					display: "flex",
					flexDirection: "column",
					gap: "16px",
					border: "1px solid #e2e8f0",
				}}
			>
				<div>
					<h2
						style={{
							fontSize: "17px",
							fontWeight: 700,
							color: "#0f172a",
							margin: "0 0 4px 0",
						}}
					>
						Launch New Investigation
					</h2>
					<p style={{ margin: 0, color: "#64748b", fontSize: "13px" }}>
						Trigger autonomous Bayesian graph investigation on pre-staged alerts or arbitrary live TigerGraph transactions.
					</p>
				</div>

				{/* Tab Selector */}
				<div
					style={{
						display: "flex",
						borderRadius: "6px",
						backgroundColor: "#f1f5f9",
						padding: "3px",
						gap: "4px",
					}}
				>
					<button
						type="button"
						onClick={() => {
							setActiveTab("queue");
							setError(null);
						}}
						style={{
							flex: 1,
							padding: "7px 12px",
							fontSize: "12.5px",
							fontWeight: activeTab === "queue" ? 600 : 500,
							color: activeTab === "queue" ? "#0f172a" : "#64748b",
							backgroundColor: activeTab === "queue" ? "#ffffff" : "transparent",
							border: "none",
							borderRadius: "5px",
							boxShadow:
								activeTab === "queue"
									? "0 1px 3px rgba(0, 0, 0, 0.08)"
									: "none",
							cursor: "pointer",
							transition: "all 0.15s ease",
						}}
					>
						Alert Queue Cases ({cases.length})
					</button>
					<button
						type="button"
						onClick={() => {
							setActiveTab("arbitrary");
							setError(null);
						}}
						style={{
							flex: 1,
							padding: "7px 12px",
							fontSize: "12.5px",
							fontWeight: activeTab === "arbitrary" ? 600 : 500,
							color: activeTab === "arbitrary" ? "#0f172a" : "#64748b",
							backgroundColor: activeTab === "arbitrary" ? "#ffffff" : "transparent",
							border: "none",
							borderRadius: "5px",
							boxShadow:
								activeTab === "arbitrary"
									? "0 1px 3px rgba(0, 0, 0, 0.08)"
									: "none",
							cursor: "pointer",
							transition: "all 0.15s ease",
						}}
					>
						Arbitrary Transaction ID
					</button>
				</div>

				{/* Error banner if any */}
				{error && (
					<div
						style={{
							padding: "8px 12px",
							backgroundColor: "#fef2f2",
							border: "1px solid #fecaca",
							borderRadius: "6px",
							color: "#b91c1c",
							fontSize: "12px",
						}}
					>
						{error}
					</div>
				)}

				{activeTab === "queue" ? (
					<div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
						<label
							htmlFor="case-select-dropdown"
							style={{ fontSize: "12px", fontWeight: 600, color: "#475569" }}
						>
							Select Case / Flagged Transaction:
						</label>
						<select
							id="case-select-dropdown"
							value={selectedCaseId}
							onChange={(e) => setSelectedCaseId(e.target.value)}
							style={{
								padding: "8px 12px",
								fontSize: "13px",
								borderRadius: "6px",
								border: "1px solid #cbd5e1",
								backgroundColor: "#f8fafc",
								color: "#0f172a",
								outline: "none",
							}}
						>
							{cases.map((c) => (
								<option key={c.case_id} value={c.case_id}>
									{c.case_id} · Txn #{c.flagged_txn_id} ·{" "}
									{c.trigger_type.replace(/_/g, " ")}
								</option>
							))}
						</select>
					</div>
				) : (
					<div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
						<label
							htmlFor="arbitrary-txn-input"
							style={{ fontSize: "12px", fontWeight: 600, color: "#475569" }}
						>
							TigerGraph Transaction ID:
						</label>
						<input
							id="arbitrary-txn-input"
							type="text"
							placeholder="e.g. 3047878, 3018431, 3583368"
							value={arbitraryTxnId}
							onChange={(e) => setArbitraryTxnId(e.target.value)}
							style={{
								padding: "8px 12px",
								fontSize: "13px",
								borderRadius: "6px",
								border: "1px solid #cbd5e1",
								backgroundColor: "#f8fafc",
								color: "#0f172a",
								outline: "none",
								fontFamily: "monospace",
							}}
						/>
						<div style={{ fontSize: "11.5px", color: "#64748b", lineHeight: 1.4 }}>
							Resolves Card, Customer, DeviceProfile, and timestamp dynamically from live TigerGraph (26,754 vertices) before initiating autonomous evidence collection.
						</div>
						<div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "4px" }}>
							<span style={{ fontSize: "11px", color: "#475569", alignSelf: "center" }}>Sample IDs:</span>
							{["3047878", "3018431", "3017957", "3583368"].map((tid) => (
								<button
									key={tid}
									type="button"
									onClick={() => setArbitraryTxnId(tid)}
									style={{
										fontSize: "11px",
										padding: "2px 8px",
										backgroundColor: "#f1f5f9",
										border: "1px solid #e2e8f0",
										borderRadius: "4px",
										color: "#0284c7",
										cursor: "pointer",
										fontFamily: "monospace",
									}}
								>
									{tid}
								</button>
							))}
						</div>
					</div>
				)}

				<div
					style={{
						display: "flex",
						justifyContent: "flex-end",
						gap: "8px",
						marginTop: "8px",
					}}
				>
					<button
						type="button"
						onClick={onClose}
						disabled={isSubmitting}
						style={{
							padding: "7px 14px",
							fontSize: "12.5px",
							fontWeight: 500,
							color: "#475569",
							backgroundColor: "#ffffff",
							border: "1px solid #cbd5e1",
							borderRadius: "6px",
							cursor: isSubmitting ? "not-allowed" : "pointer",
						}}
					>
						Cancel
					</button>
					<button
						type="button"
						onClick={handleSubmit}
						disabled={isSubmitting}
						style={{
							padding: "7px 16px",
							fontSize: "12.5px",
							fontWeight: 600,
							color: "#ffffff",
							backgroundColor: isSubmitting ? "#94a3b8" : "#ea580c",
							border: "none",
							borderRadius: "6px",
							cursor: isSubmitting ? "not-allowed" : "pointer",
							display: "flex",
							alignItems: "center",
							gap: "6px",
						}}
					>
						{isSubmitting ? "Investigating..." : activeTab === "queue" ? "Start Investigation" : "Investigate Transaction"}
					</button>
				</div>
			</div>
		</div>
	);
};
