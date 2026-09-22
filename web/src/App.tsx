import type React from "react";
import { useEffect, useState } from "react";
import { fetchCases, fetchHealth, runTransactionInvestigation } from "./api/client";
import type {
	CaseMetadata,
	HealthStatus,
	InvestigationResultPayload,
} from "./api/types";
import { BenchmarkView } from "./components/BenchmarkView";
import { GlobalGraphExplorer } from "./components/GlobalGraphExplorer";
import { Header } from "./components/Header";
import { InvestigationHistoryView } from "./components/InvestigationHistoryView";
import { InvestigationPreStartView } from "./components/InvestigationPreStartView";
import { InvestigationQueue } from "./components/InvestigationQueue";
import { NewInvestigationModal } from "./components/NewInvestigationModal";
import { OverviewView } from "./components/OverviewView";
import { PolicyPatternsView } from "./components/PolicyPatternsView";
import { RunTraceConsole } from "./components/RunTraceConsole";
import { type NavigationPage, SidebarNav } from "./components/SidebarNav";

export const App: React.FC = () => {
	const [health, setHealth] = useState<HealthStatus | null>(null);
	const [cases, setCases] = useState<CaseMetadata[]>([]);
	const [isLoadingCases, setIsLoadingCases] = useState(true);
	const [casesError, setCasesError] = useState<string | null>(null);

	// Navigation & Workspace State
	const [activePage, setActivePage] =
		useState<NavigationPage>("investigations");
	const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
	const [isNewModalOpen, setIsNewModalOpen] = useState(false);
	const [isTraceOpen, setIsTraceOpen] = useState(false);
	const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
	const [activeResult, setActiveResult] =
		useState<InvestigationResultPayload | null>(null);

	// Poll system health
	useEffect(() => {
		let isMounted = true;
		const checkHealth = () => {
			fetchHealth()
				.then((data) => {
					if (isMounted) setHealth(data);
				})
				.catch(() => {
					if (isMounted) setHealth(null);
				});
		};

		checkHealth();
		const interval = setInterval(checkHealth, 5000);
		return () => {
			isMounted = false;
			clearInterval(interval);
		};
	}, []);

	// Fetch benchmark/incoming investigation cases
	useEffect(() => {
		let isMounted = true;
		setIsLoadingCases(true);
		fetchCases()
			.then((data) => {
				if (isMounted) {
					setCases(data);
					setIsLoadingCases(false);
				}
			})
			.catch((err) => {
				if (isMounted) {
					setCasesError(
						err instanceof Error ? err.message : "Unknown error loading cases",
					);
					setIsLoadingCases(false);
				}
			});

		return () => {
			isMounted = false;
		};
	}, []);

	const selectedCase = cases.find((c) => c.case_id === selectedCaseId);

	const handleSelectCase = (caseId: string) => {
		setSelectedCaseId(caseId);
		setActivePage("investigations");
	};

	const handleOpenNewInvestigation = () => {
		setIsNewModalOpen(true);
	};

	const handleStartModalCase = (caseId: string) => {
		setIsNewModalOpen(false);
		handleSelectCase(caseId);
	};

	const handleStartTransactionInvestigation = async (txnId: string) => {
		setIsNewModalOpen(false);
		try {
			setIsLoadingCases(true);
			const res = await runTransactionInvestigation(txnId);
			const updatedCases = await fetchCases();
			setCases(updatedCases);
			setActiveResult(res.result);
			setSelectedCaseId(res.investigation_id);
			setActivePage("investigations");
		} catch (err) {
			setCasesError(
				err instanceof Error
					? err.message
					: "Failed to run transaction investigation",
			);
		} finally {
			setIsLoadingCases(false);
		}
	};

	return (
		<div
			style={{
				minHeight: "100vh",
				backgroundColor: "#f8fafc",
				color: "#0f172a",
				fontFamily:
					'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
				display: "flex",
			}}
		>
			{/* Global Left Navigation Sidebar */}
			<SidebarNav
				activePage={activePage}
				onSelectPage={(page) => {
					setActivePage(page);
					if (page !== "investigations") {
						setSelectedCaseId(null);
					}
				}}
				onOpenNewInvestigation={handleOpenNewInvestigation}
				caseCount={cases.length}
				health={health}
				isCollapsed={isSidebarCollapsed}
				onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
			/>

			{/* Main Content Area */}
			<div
				style={{
					flex: 1,
					display: "flex",
					flexDirection: "column",
					minWidth: 0,
					paddingBottom: "48px", // Space for collapsed bottom trace bar
				}}
			>
				<Header
					health={health}
					onNavigateHome={() => {
						setActivePage("overview");
						setSelectedCaseId(null);
					}}
				/>

				<main
					style={{
						flex: 1,
						width: "100%",
						maxWidth: "1680px",
						margin: "0 auto",
						padding: "24px 32px",
						boxSizing: "border-box",
					}}
				>
					{/* Overview / Command Center */}
					{activePage === "overview" && (
						<OverviewView
							cases={cases}
							onSelectCase={handleSelectCase}
							onNavigateBenchmark={() => setActivePage("benchmark")}
						/>
					)}

					{/* Investigations Workspace */}
					{activePage === "investigations" && (
						<>
							{selectedCaseId && selectedCase ? (
								<InvestigationPreStartView
									caseItem={selectedCase}
									onBack={() => setSelectedCaseId(null)}
									onResultUpdate={(res) => setActiveResult(res)}
								/>
							) : (
								<InvestigationQueue
									cases={cases}
									isLoading={isLoadingCases}
									error={casesError}
									onSelectCase={handleSelectCase}
								/>
							)}
						</>
					)}

					{/* Investigation History & Session Audit Log */}
					{activePage === "history" && (
						<InvestigationHistoryView
							onSelectCase={handleSelectCase}
							onOpenNewInvestigation={handleOpenNewInvestigation}
						/>
					)}

					{/* Benchmark Scoreboard */}
					{activePage === "benchmark" && (
						<BenchmarkView cases={cases} onSelectCase={handleSelectCase} />
					)}

					{/* Policy & Patterns (GraphRAG) */}
					{activePage === "policy" && <PolicyPatternsView />}

					{/* Global Graph Explorer */}
					{activePage === "graph_explorer" && <GlobalGraphExplorer />}
				</main>
			</div>

			{/* Real-time Streaming Run Trace Console Drawer */}
			<RunTraceConsole
				result={activeResult}
				isOpen={isTraceOpen}
				onToggle={() => setIsTraceOpen(!isTraceOpen)}
				isSidebarCollapsed={isSidebarCollapsed}
			/>

			{/* New Investigation Modal */}
			<NewInvestigationModal
				isOpen={isNewModalOpen}
				onClose={() => setIsNewModalOpen(false)}
				onStartInvestigation={handleStartModalCase}
				onStartTransactionInvestigation={handleStartTransactionInvestigation}
				cases={cases}
			/>
		</div>
	);
};

export default App;
