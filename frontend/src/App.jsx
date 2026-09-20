import React, { useState, useEffect } from 'react';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import CasesTable from './components/case/CasesTable';
import CaseHeaderCompact from './components/case/CaseHeaderCompact';
import AgentTimeline from './components/AgentTimeline';
import InvestigationArea from './components/investigation/InvestigationArea';
import AssessmentPanel from './components/assessment/AssessmentPanel';
import PolicyApprovalModal from './components/PolicyApprovalModal';
import CaseMemoryModal from './components/memory/CaseMemoryModal';
import SARModal from './components/sar/SARModal';
import GraphExplorer from './components/GraphExplorer';
import EvidenceCardGrid from './components/evidence/EvidenceCardGrid';

import {
  fetchBenchmarkCases,
  fetchCaseDetails,
  fetchGraphData,
  fetchCaseMemory,
  approvePolicyAction,
  triggerInvestigation,
  ApiConfig
} from './services/api';

import {
  subscribeToInvestigationStream,
  buildInvestigationSteps,
  CANONICAL_STEPS
} from './services/events';

import { CheckSquare, History, FileBadge, ArrowRight, CheckCircle2 } from './components/common/Icons';

export default function App() {
  // Navigation & Active View State
  const [activeNav, setActiveNav] = useState('cases'); // 'cases' | 'investigations' | 'approvals' | 'memory' | 'graph' | 'evidence' | 'reports'
  const [activeTab, setActiveTab] = useState('timeline'); // 'timeline' | 'evidence' | 'graph'
  const [benchmarkCases, setBenchmarkCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState('HHG-017');
  const [caseData, setCaseData] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [caseMemory, setCaseMemory] = useState([]);
  const [isLoadingCase, setIsLoadingCase] = useState(true);
  const [globalSearch, setGlobalSearch] = useState('');

  // Investigation & SSE Streaming State
  const [isLiveStreaming, setIsLiveStreaming] = useState(false);
  const [streamEvents, setStreamEvents] = useState([]);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [isEvidenceProvided, setIsEvidenceProvided] = useState(false);

  // Governance & Approvals State
  const [isMockMode, setIsMockMode] = useState(ApiConfig.isMockMode());
  const [pendingApprovalAction, setPendingApprovalAction] = useState(null);
  const [approvedActions, setApprovedActions] = useState([]);
  const [investigatedCases, setInvestigatedCases] = useState(['HHG-017']);

  // Modals
  const [isPolicyModalOpen, setIsPolicyModalOpen] = useState(false);
  const [isCaseMemoryOpen, setIsCaseMemoryOpen] = useState(false);
  const [isSAROpen, setIsSAROpen] = useState(false);

  // Load benchmark cases list on mount or mode switch
  useEffect(() => {
    async function loadCases() {
      const cases = await fetchBenchmarkCases();
      setBenchmarkCases(cases);
    }
    loadCases();
  }, [isMockMode]);

  // Load active case details, subgraph, and memory when selected case changes
  useEffect(() => {
    let isCancelled = false;

    async function loadActiveCase() {
      setIsLoadingCase(true);
      try {
        const [loadedCase, loadedGraph, loadedMemory] = await Promise.all([
          fetchCaseDetails(selectedCaseId),
          fetchGraphData(selectedCaseId),
          fetchCaseMemory(selectedCaseId)
        ]);

        if (!isCancelled) {
          setCaseData(loadedCase);
          setGraphData(loadedGraph);
          setCaseMemory(loadedMemory);
          setIsEvidenceProvided(false);
          setActiveStepIndex(CANONICAL_STEPS.length - 1);
        }
      } catch (err) {
        console.error('[Tark] Failed to load case record:', err);
      } finally {
        if (!isCancelled) {
          setIsLoadingCase(false);
        }
      }
    }

    loadActiveCase();

    return () => {
      isCancelled = true;
    };
  }, [selectedCaseId, isMockMode]);

  // Start Live Investigation (SSE Stream or Simulation)
  const handleStartInvestigation = () => {
    setIsLiveStreaming(true);
    setStreamEvents([]);
    setActiveStepIndex(0);
    setIsEvidenceProvided(false);
    setActiveTab('timeline');

    triggerInvestigation(selectedCaseId);

    const unsubscribe = subscribeToInvestigationStream(selectedCaseId, {
      onEvent: (event) => {
        setStreamEvents((prev) => {
          const next = [...prev, event];
          const matchIdx = CANONICAL_STEPS.findIndex((s) => s.event === event.event);
          if (matchIdx !== -1) {
            setActiveStepIndex(matchIdx);
            if (event.event === 'EVIDENCE_INJECTED') {
              setIsEvidenceProvided(true);
            }
          }
          return next;
        });
      },
      onComplete: () => {
        setIsLiveStreaming(false);
        if (!investigatedCases.includes(selectedCaseId)) {
          setInvestigatedCases((prev) => [...prev, selectedCaseId]);
        }
      },
      onError: () => {
        setIsLiveStreaming(false);
      }
    });

    return unsubscribe;
  };

  const handleResetInvestigation = () => {
    setIsLiveStreaming(false);
    setStreamEvents([]);
    setActiveStepIndex(0);
    setIsEvidenceProvided(false);
  };

  // Provide interactive evidence injection (Adaptive loop)
  const handleProvideEvidence = () => {
    setIsEvidenceProvided(true);
    setActiveStepIndex(6); // Step 7: Reassessment
  };

  // Human approval handler
  const handleApproveAction = async (actionItem) => {
    const action = actionItem.action || 'BLOCK_CARD';
    const route = actionItem.approval_route || actionItem.route || 'L1';
    const reason = actionItem.reason || 'Confirmed card testing pattern with shared device link';
    setPendingApprovalAction({ action, route, reason });
    setIsPolicyModalOpen(true);
  };

  const handleConfirmApproval = async (action, route, analystNotes) => {
    const res = await approvePolicyAction({
      action,
      case_id: selectedCaseId,
      route,
      analyst_id: 'analyst_lead',
      notes: analystNotes || 'Confirmed card testing pattern with shared device link'
    });

    if (res.status === 'APPROVED') {
      setApprovedActions((prev) => [...prev, action]);
    }
  };

  const handleToggleMockMode = () => {
    const newMode = ApiConfig.toggleMockMode();
    setIsMockMode(newMode);
  };

  // Active benchmark case metadata
  const currentMeta = benchmarkCases.find((c) => c.id === selectedCaseId);

  // Investigation trace steps
  const replaySteps = buildInvestigationSteps(streamEvents);

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col overflow-hidden font-sans">
      {/* 1. Global Header (56px) */}
      <Header
        searchTerm={globalSearch}
        onSearchChange={setGlobalSearch}
        isMockMode={isMockMode}
        onToggleMockMode={handleToggleMockMode}
        selectedCaseId={selectedCaseId}
        isLiveStreaming={isLiveStreaming}
      />

      {/* 2. Main Workspace Body (Sidebar + Content) */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Left Sidebar Navigation (220-240px) */}
        <Sidebar
          activeNav={activeNav}
          onSelectNav={(navId) => {
            setActiveNav(navId);
            if (navId === 'memory') setIsCaseMemoryOpen(true);
            else if (navId === 'reports') setIsSAROpen(true);
          }}
          casesCount={benchmarkCases.length}
          investigatedCount={investigatedCases.length}
          approvalsCount={approvedActions.length > 0 ? 0 : 1}
          isMockMode={isMockMode}
          onToggleMockMode={handleToggleMockMode}
        />

        {/* Dynamic Center Workstation View */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-950">
          {/* VIEW A: CASES MANAGEMENT TABLE */}
          {activeNav === 'cases' && (
            <CasesTable
              cases={benchmarkCases}
              selectedCaseId={selectedCaseId}
              onSelectCase={(id) => setSelectedCaseId(id)}
              onOpenInvestigation={(id) => {
                setSelectedCaseId(id);
                setActiveNav('investigations');
              }}
              selectedCaseDetails={caseData}
            />
          )}

          {/* VIEW B: INVESTIGATION WORKSPACE */}
          {activeNav === 'investigations' && (
            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
              {/* Top Case Header (Compact) */}
              <div className="p-4 border-b border-slate-800 bg-slate-950 shrink-0">
                <CaseHeaderCompact
                  caseData={caseData}
                  benchmarkMeta={currentMeta}
                  isLiveStreaming={isLiveStreaming}
                  onStartInvestigation={handleStartInvestigation}
                  onResetInvestigation={handleResetInvestigation}
                  onOpenReplay={() => {
                    setActiveTab('timeline');
                    setActiveStepIndex(0);
                  }}
                />
              </div>

              {/* 3-Area Layout: Left 22% Timeline | Center 48% Tabs | Right 30% Assessment */}
              <div className="flex-1 overflow-y-auto p-4 scrollbar-thin scrollbar-thumb-slate-800">
                {isLoadingCase || !caseData ? (
                  <div className="flex items-center justify-center h-80 text-slate-500 font-mono text-xs">
                    Loading TigerGraph investigation record for {selectedCaseId}...
                  </div>
                ) : (
                  <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 items-start">
                    {/* LEFT ~22% (Cols 1-3): Investigation Timeline */}
                    <div className="xl:col-span-3 h-[780px]">
                      <AgentTimeline
                        steps={replaySteps}
                        activeStepIndex={activeStepIndex}
                        onStepChange={(idx) => setActiveStepIndex(idx)}
                        isLiveStreaming={isLiveStreaming}
                      />
                    </div>

                    {/* CENTER ~48% (Cols 4-8): Main Tabs (Timeline Overview / Evidence / Graph) */}
                    <div className="xl:col-span-5">
                      <InvestigationArea
                        activeTab={activeTab}
                        onTabChange={(tab) => setActiveTab(tab)}
                        steps={replaySteps}
                        activeStepIndex={activeStepIndex}
                        onStepChange={(idx) => setActiveStepIndex(idx)}
                        evidence={caseData.case?.evidence}
                        graphData={graphData}
                        caseId={selectedCaseId}
                        isEvidenceProvided={isEvidenceProvided}
                        onProvideEvidence={handleProvideEvidence}
                        isLiveStreaming={isLiveStreaming}
                      />
                    </div>

                    {/* RIGHT ~30% (Cols 9-12): Assessment + Next Best Action */}
                    <div className="xl:col-span-4">
                      <AssessmentPanel
                        caseData={caseData}
                        approvedActions={approvedActions}
                        onApproveAction={handleApproveAction}
                        onRejectAction={(actionItem) => {
                          console.log(`Action ${actionItem.action} rejected.`);
                        }}
                        onRequestEvidence={() => {
                          setActiveTab('timeline');
                        }}
                        onOpenPolicyModal={() => {
                          const primary = caseData.next_best_actions?.final?.[0];
                          if (primary) handleApproveAction(primary);
                        }}
                        onOpenCaseMemory={() => setIsCaseMemoryOpen(true)}
                        onOpenSAR={() => setIsSAROpen(true)}
                        isEvidenceProvided={isEvidenceProvided}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VIEW C: GRAPH EXPLORER VIEW */}
          {activeNav === 'graph' && (
            <div className="flex-1 flex flex-col p-4 overflow-hidden">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                <div>
                  <h2 className="text-base font-black text-slate-100 font-mono uppercase">
                    TigerGraph Subgraph Explorer — {selectedCaseId}
                  </h2>
                  <p className="text-xs text-slate-400">
                    Live Cytoscape canvas mapped across Customers, Cards, Devices, Transactions, and Closed Cases
                  </p>
                </div>
                <button
                  onClick={() => setActiveNav('investigations')}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold"
                >
                  Back to Investigation
                </button>
              </div>
              <div className="flex-1 min-h-0 bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
                <GraphExplorer graphData={graphData} caseId={selectedCaseId} />
              </div>
            </div>
          )}

          {/* VIEW D: EVIDENCE VIEW */}
          {activeNav === 'evidence' && (
            <div className="flex-1 flex flex-col p-4 overflow-y-auto">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                <div>
                  <h2 className="text-base font-black text-slate-100 font-mono uppercase">
                    Grounded Evidence Registry — {selectedCaseId}
                  </h2>
                  <p className="text-xs text-slate-400">
                    Full empirical evidence signals categorized across transactions, identity, device, relationships, and policy
                  </p>
                </div>
                <button
                  onClick={() => setActiveNav('investigations')}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold"
                >
                  Back to Investigation
                </button>
              </div>
              <EvidenceCardGrid evidence={caseData?.case?.evidence || []} />
            </div>
          )}

          {/* VIEW E: APPROVALS GOVERNANCE VIEW */}
          {activeNav === 'approvals' && (
            <div className="flex-1 flex flex-col p-6 overflow-y-auto space-y-4">
              <div>
                <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-sans">
                  Governance & Policy Approvals
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Human-in-the-loop sign-off queue for deterministic L1 & L2 policy actions
                </p>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <span className="text-xs font-bold uppercase font-mono text-slate-300">
                    Pending Action Queue ({approvedActions.length > 0 ? 0 : 1})
                  </span>
                  <span className="text-xs text-slate-500 font-mono">Case: {selectedCaseId}</span>
                </div>

                {approvedActions.length > 0 ? (
                  <div className="bg-slate-950 p-6 rounded border border-slate-800 text-center space-y-2">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                    <div className="text-sm font-bold text-slate-200">All Pending Actions Approved</div>
                    <p className="text-xs text-slate-400">
                      Executed {approvedActions.join(', ')} on core banking gateway for {selectedCaseId}.
                    </p>
                  </div>
                ) : (
                  <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-slate-100 font-mono">BLOCK_CARD</span>
                        <span className="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded font-mono font-bold">
                          L1 — Team Lead
                        </span>
                      </div>
                      <p className="text-xs text-slate-300">
                        Exposure $100.09 is under $2,500 threshold. Mandated by Policy Rule R2 upon confirmed customer denial.
                      </p>
                    </div>

                    <button
                      onClick={() => {
                        const primary = caseData?.next_best_actions?.final?.[0] || {
                          action: 'BLOCK_CARD',
                          route: 'L1',
                          reason: 'Policy Rule R2: Customer denial + shared device.'
                        };
                        handleApproveAction(primary);
                      }}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold rounded-lg text-xs tracking-wider uppercase transition"
                    >
                      Review & Approve
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VIEW F: CASE MEMORY VIEW */}
          {activeNav === 'memory' && (
            <div className="flex-1 flex flex-col p-6 overflow-y-auto space-y-4">
              <div>
                <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-sans">
                  TigerGraph Case Memory (GraphRAG)
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Historical closed investigations retrieved via vector & graph similarity
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {caseMemory.map((c, idx) => (
                  <div key={idx} className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-2 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="font-mono font-bold text-slate-100 text-sm">{c.case_id}</span>
                      <span className="text-[10px] bg-red-500/20 text-red-400 px-2 py-0.5 rounded font-mono font-bold">
                        {c.pattern.replace(/_/g, ' ').toUpperCase()}
                      </span>
                    </div>
                    <p className="text-slate-300 leading-relaxed text-[11px]">{c.analyst_notes}</p>
                    <div className="flex justify-between pt-2 border-t border-slate-800/80 font-mono text-[11px] text-slate-400">
                      <span>Actions: {c.actions_taken.join(', ')}</span>
                      <span className="text-slate-200 font-bold">${c.exposure_usd.toFixed(2)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* VIEW G: REPORTS / SAR VIEW */}
          {activeNav === 'reports' && (
            <div className="flex-1 flex flex-col p-6 overflow-y-auto space-y-4">
              <div>
                <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-sans">
                  Regulatory Compliance & SAR Filing
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  FinCEN Suspicious Activity Report generation under 31 CFR § 1020.320
                </p>
              </div>

              {caseData?.sar && (
                <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
                  <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                    <span className="text-xs font-mono font-bold text-slate-300">
                      SAR FILING STATUS: <strong className="text-red-400">MANDATORY (L2 REVIEW)</strong>
                    </span>
                    <span className="text-xs text-slate-400 font-mono">Case: {selectedCaseId}</span>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[11px] font-bold text-slate-400 uppercase font-mono">Filing Reason:</span>
                    <p className="text-xs text-slate-300 bg-slate-950 p-2.5 rounded border border-slate-800">
                      {caseData.sar.reason}
                    </p>
                  </div>

                  <div className="space-y-1.5">
                    <span className="text-[11px] font-bold text-slate-400 uppercase font-mono">Narrative Draft:</span>
                    <div className="bg-slate-950 p-4 rounded border border-slate-800 text-slate-300 font-mono text-xs leading-relaxed whitespace-pre-wrap select-text">
                      {caseData.sar.narrative}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* MODALS & DRAWERS */}
      {/* 1. Policy Approval Modal */}
      <PolicyApprovalModal
        isOpen={isPolicyModalOpen}
        onClose={() => setIsPolicyModalOpen(false)}
        action={pendingApprovalAction}
        exposure={caseData?.case?.exposure_usd || 100.09}
        onConfirm={handleConfirmApproval}
      />

      {/* 2. TigerGraph Case Memory Modal */}
      <CaseMemoryModal
        isOpen={isCaseMemoryOpen}
        onClose={() => setIsCaseMemoryOpen(false)}
        cases={caseMemory}
        graphCaseId={caseData?.case?.graph_case_id}
      />

      {/* 3. FinCEN SAR Filing Modal */}
      <SARModal
        isOpen={isSAROpen}
        onClose={() => setIsSAROpen(false)}
        sar={caseData?.sar}
      />
    </div>
  );
}
