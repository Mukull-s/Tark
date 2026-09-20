import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/layout/Sidebar';
import CaseHeaderCompact from './components/case/CaseHeaderCompact';
import InvestigationArea from './components/investigation/InvestigationArea';
import AssessmentPanel from './components/assessment/AssessmentPanel';
import PolicyApprovalModal from './components/PolicyApprovalModal';
import CaseMemoryModal from './components/memory/CaseMemoryModal';
import SARModal from './components/sar/SARModal';

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

export default function App() {
  // Navigation & Active View State
  const [activeNav, setActiveNav] = useState('cases');
  const [activeTab, setActiveTab] = useState('timeline');
  const [benchmarkCases, setBenchmarkCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState('HHG-017');
  const [caseData, setCaseData] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [caseMemory, setCaseMemory] = useState([]);
  const [isLoadingCase, setIsLoadingCase] = useState(true);

  // Investigation & SSE Streaming State
  const [isLiveStreaming, setIsLiveStreaming] = useState(false);
  const [streamEvents, setStreamEvents] = useState([]);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [isEvidenceProvided, setIsEvidenceProvided] = useState(false);

  // Operational State
  const [isMockMode, setIsMockMode] = useState(ApiConfig.isMockMode());
  const [pendingApprovalAction, setPendingApprovalAction] = useState(null);
  const [approvedActions, setApprovedActions] = useState([]);
  const [investigatedCases, setInvestigatedCases] = useState(['HHG-017']);

  // Modals / Drawers
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
          // Set to complete step index so analyst sees full grounded context by default
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
  const handleProvideEvidence = (evidenceType) => {
    setIsEvidenceProvided(true);
    setActiveStepIndex(6); // Step 7: Reassessment
  };

  // Human approval handler
  const handleApproveAction = async (action, route, analystNotes) => {
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

  // Active benchmark case metadata from sidebar
  const currentMeta = benchmarkCases.find((c) => c.id === selectedCaseId);

  // Investigation trace steps
  const replaySteps = buildInvestigationSteps(streamEvents);

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex overflow-hidden font-sans">
      {/* 1. Left Sidebar Navigation (220-240px) */}
      <Sidebar
        cases={benchmarkCases}
        selectedCaseId={selectedCaseId}
        onSelectCase={(id) => setSelectedCaseId(id)}
        investigatedCases={investigatedCases}
        activeNav={activeNav}
        onSelectNav={(navId) => {
          setActiveNav(navId);
          if (navId === 'graph') setActiveTab('graph');
          else if (navId === 'memory') setIsCaseMemoryOpen(true);
          else if (navId === 'reports') setIsSAROpen(true);
        }}
        isMockMode={isMockMode}
        onToggleMockMode={handleToggleMockMode}
      />

      {/* 2. Main Workstation Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
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

        {/* 65 / 35 Workstation Layout */}
        <div className="flex-1 overflow-y-auto p-4 scrollbar-thin scrollbar-thumb-slate-800">
          {isLoadingCase || !caseData ? (
            <div className="flex items-center justify-center h-80 text-slate-500 font-mono text-xs">
              Loading TigerGraph investigation record for {selectedCaseId}...
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
              {/* Left ~65% (Cols 1-8): INVESTIGATION (Timeline, Evidence, Graph) */}
              <div className="lg:col-span-8">
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

              {/* Right ~35% (Cols 9-12): ASSESSMENT + NEXT BEST ACTION */}
              <div className="lg:col-span-4">
                <AssessmentPanel
                  caseData={caseData}
                  approvedActions={approvedActions}
                  onApproveAction={(action, route) => {
                    const reason = caseData.next_best_actions?.final?.[0]?.reason;
                    setPendingApprovalAction({ action, route, reason });
                    setIsPolicyModalOpen(true);
                  }}
                  onRejectAction={(action) => {
                    console.log(`Action ${action} rejected.`);
                  }}
                  onRequestEvidence={() => {
                    setIsEvidenceProvided(false);
                    setActiveStepIndex(4); // Jump to uncertainty loop step
                    setActiveTab('timeline');
                  }}
                  onOpenPolicyModal={() => {
                    const primary = caseData.next_best_actions?.final?.[0] || {
                      action: 'BLOCK_CARD',
                      route: 'L1',
                      reason: 'Customer denied transaction + shared device linkage.'
                    };
                    setPendingApprovalAction(primary);
                    setIsPolicyModalOpen(true);
                  }}
                  onOpenCaseMemory={() => setIsCaseMemoryOpen(true)}
                  onOpenSAR={() => setIsSAROpen(true)}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Policy Approval Gate Modal */}
      {isPolicyModalOpen && pendingApprovalAction && (
        <PolicyApprovalModal
          actionItem={pendingApprovalAction}
          caseId={selectedCaseId}
          exposureUsd={caseData?.case?.exposure_usd || 268.43}
          onApprove={handleApproveAction}
          onReject={(action) => {
            console.log(`Action ${action} rejected by analyst.`);
          }}
          onClose={() => {
            setIsPolicyModalOpen(false);
            setPendingApprovalAction(null);
          }}
        />
      )}

      {/* Case Memory Modal (Progressive Disclosure) */}
      <CaseMemoryModal
        isOpen={isCaseMemoryOpen}
        onClose={() => setIsCaseMemoryOpen(false)}
        cases={caseMemory}
        graphCaseId={caseData?.case?.graph_case_id}
      />

      {/* SAR Regulatory Filing Modal (Progressive Disclosure) */}
      <SARModal
        isOpen={isSAROpen}
        onClose={() => setIsSAROpen(false)}
        sar={caseData?.sar}
      />
    </div>
  );
}
