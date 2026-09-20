import React, { useState } from 'react';
import {
  Clock,
  Layers,
  Share2,
  AlertTriangle,
  CheckCircle2,
  UserCheck,
  Terminal,
  Database,
  ChevronDown,
  ChevronUp,
  Activity,
  ArrowRight
} from '../common/Icons';
import GraphExplorer from '../GraphExplorer';

export default function InvestigationArea({
  activeTab,
  onTabChange,
  steps = [],
  activeStepIndex = 0,
  onStepChange,
  evidence = [],
  graphData,
  caseId,
  isEvidenceProvided,
  onProvideEvidence,
  isLiveStreaming
}) {
  const [expandedEventIdx, setExpandedEventIdx] = useState(null);
  const [expandedEvidenceIdx, setExpandedEvidenceIdx] = useState(null);
  const [showWhatChangedModal, setShowWhatChangedModal] = useState(false);

  const toggleEventExpand = (idx) => {
    setExpandedEventIdx(expandedEventIdx === idx ? null : idx);
  };

  const toggleEvidenceExpand = (idx) => {
    setExpandedEvidenceIdx(expandedEvidenceIdx === idx ? null : idx);
  };

  // Structured evidence categories
  const evidenceCategories = [
    {
      category: 'TRANSACTION',
      title: 'Flagged Transaction & Velocity',
      source: 'TigerGraph: card_window()',
      claim: 'Three sub-$3 online authorizations within 40 minutes, followed by a $100.09 purchase in an unprecedented product category.',
      details: 'Product code R used for the first time on this card. Micro-authorizations executed at 00:05, 00:18, and 00:32.'
    },
    {
      category: 'DEVICE',
      title: 'Device Hardware Profile',
      source: 'TigerGraph: device_neighbors()',
      claim: 'Device profile SAMSUNG SM-G892A (Android 7.0, Samsung Browser 6.2) marked New for this cardholder.',
      details: 'Multi-hop graph query reveals identical hardware fingerprint active on closed fraud case CC-0141 and card C00877-K1.'
    },
    {
      category: 'CUSTOMER',
      title: 'Cardholder Validation Inquiry',
      source: isEvidenceProvided ? 'Customer Verification Loop' : 'Pending Inquiry',
      claim: isEvidenceProvided
        ? 'Customer explicitly denied making the transactions and remains in physical possession of the card.'
        : 'Dispatched outbound customer verification to distinguish account takeover from authorized cardholder activity.',
      details: 'Verified via automated telephony/SMS verification loop.'
    },
    {
      category: 'NETWORK',
      title: 'Syndicate Hardware Clustering',
      source: 'TigerGraph: graph_cluster()',
      claim: 'Shared hardware fingerprint directly connects 2 independent compromised cards across different accounts.',
      details: 'Cards C04570-K1 and C00877-K1 share identical screen resolution (2220x1080) and device user-agent strings.'
    },
    {
      category: 'HISTORICAL CASE',
      title: 'Case Memory Pattern Match',
      source: 'TigerGraph: find_prior_cases()',
      claim: 'Exact pattern match to closed case CC-0141 (confirmed card testing syndicate fraud from August).',
      details: 'Prior case CC-0141 resulted in confirmed card block and law enforcement SAR regulatory filing.'
    }
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-sm flex flex-col overflow-hidden">
      {/* Tab Navigation Header */}
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2.5 bg-slate-950/60">
        <div className="flex items-center gap-1.5 text-xs font-mono">
          {[
            { id: 'timeline', label: 'Timeline', icon: Clock },
            { id: 'evidence', label: 'Evidence', icon: Layers },
            { id: 'graph', label: 'Graph', icon: Share2 }
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition font-semibold ${
                  isActive
                    ? 'bg-slate-800 text-slate-100 border border-slate-700 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-blue-400' : 'text-slate-500'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Context Telemetry */}
        <div className="text-[11px] text-slate-500 font-mono">
          {activeTab === 'timeline' && `${steps.length} Trace Events Recorded`}
          {activeTab === 'evidence' && `${evidenceCategories.length} Grounded Evidence Points`}
          {activeTab === 'graph' && 'TigerGraph Subgraph Explorer'}
        </div>
      </div>

      {/* Adaptive Evidence Request / Received Banner */}
      <div className="p-4 border-b border-slate-800/80 bg-slate-950/40">
        {!isEvidenceProvided ? (
          <div className="bg-amber-950/20 border border-amber-500/30 rounded-lg p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5 font-bold text-amber-300 font-mono text-[11px] uppercase">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>More Evidence Required (Adaptive Loop)</span>
              </div>
              <p className="text-slate-300 text-[11px]">
                Customer authorization status is unknown. Initial pattern score: 72%.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => onProvideEvidence('DENIAL')}
                className="px-3 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold font-mono text-xs rounded transition shadow"
              >
                Provide Customer Denial
              </button>
              <button
                onClick={() => onProvideEvidence('CONFIRM')}
                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded border border-slate-700 transition"
              >
                Authorize
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-lg p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5 font-bold text-emerald-400 font-mono text-[11px] uppercase">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Evidence Received: Customer Denied Purchases</span>
              </div>
              <p className="text-slate-300 text-[11px]">
                Investigation assessment updated:{' '}
                <strong className="text-amber-400 font-mono">Medium (72%)</strong> →{' '}
                <strong className="text-red-400 font-mono">High (86%)</strong>.
              </p>
            </div>

            <button
              onClick={() => setShowWhatChangedModal(true)}
              className="text-xs text-blue-400 hover:text-blue-300 font-mono underline"
            >
              View changes →
            </button>
          </div>
        )}
      </div>

      {/* Main Tab Content */}
      <div className="p-4 flex-1">
        {/* ================= TAB 1: TIMELINE ================= */}
        {activeTab === 'timeline' && (
          <div className="space-y-3">
            {/* Step Scrubber Bar */}
            <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 font-mono">
                <span className="text-slate-400">Replay Step:</span>
                <strong className="text-blue-400">{activeStepIndex + 1}</strong>
                <span className="text-slate-600">/</span>
                <span className="text-slate-400">{steps.length}</span>
              </div>

              {/* Scrubber step buttons */}
              <div className="flex items-center gap-1">
                {steps.map((s, idx) => (
                  <button
                    key={idx}
                    onClick={() => onStepChange(idx)}
                    title={`Step ${idx + 1}: ${s.title}`}
                    className={`w-5 h-5 rounded text-[10px] font-mono font-bold transition flex items-center justify-center ${
                      idx === activeStepIndex
                        ? 'bg-blue-600 text-slate-950 font-black'
                        : idx < activeStepIndex
                        ? 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                        : 'bg-slate-900 text-slate-600'
                    }`}
                  >
                    {idx + 1}
                  </button>
                ))}
              </div>
            </div>

            {/* Events List */}
            <div className="space-y-2">
              {steps.map((step, idx) => {
                const isCurrent = idx === activeStepIndex;
                const isExpanded = expandedEventIdx === idx;
                const isWaiting = step.status === 'WAITING FOR EVIDENCE';

                return (
                  <div
                    key={idx}
                    className={`border rounded-lg p-2.5 text-xs transition ${
                      isCurrent
                        ? 'bg-slate-950 border-slate-700 shadow-sm ring-1 ring-blue-500/20'
                        : 'bg-slate-950/40 border-slate-800/80 hover:bg-slate-950'
                    }`}
                  >
                    <div
                      onClick={() => toggleEventExpand(idx)}
                      className="flex items-center justify-between cursor-pointer"
                    >
                      <div className="flex items-center gap-2">
                        {isWaiting ? (
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        ) : (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        )}
                        <span className="font-mono font-bold text-slate-200">
                          {step.title}
                        </span>
                        <span className="text-slate-500 font-mono text-[10px]">
                          [{step.timestamp}]
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold uppercase ${
                            isWaiting
                              ? 'bg-amber-500/20 text-amber-400'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {step.status}
                        </span>
                        {isExpanded ? (
                          <ChevronUp className="w-3 h-3 text-slate-500" />
                        ) : (
                          <ChevronDown className="w-3 h-3 text-slate-500" />
                        )}
                      </div>
                    </div>

                    <p className="text-[11px] text-slate-400 mt-1 leading-snug">
                      {step.description}
                    </p>

                    {isExpanded && step.toolCall && (
                      <div className="mt-2 pt-2 border-t border-slate-800 text-[10px] font-mono text-emerald-400 bg-slate-900/60 p-1.5 rounded">
                        <span>Tool Invocation: {step.toolCall}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ================= TAB 2: EVIDENCE ================= */}
        {activeTab === 'evidence' && (
          <div className="space-y-2.5">
            {evidenceCategories.map((item, idx) => {
              const isExpanded = expandedEvidenceIdx === idx;

              return (
                <div
                  key={idx}
                  className="bg-slate-950/70 border border-slate-800 rounded-lg p-3 text-xs space-y-1.5 hover:border-slate-700 transition"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800 uppercase">
                        {item.category}
                      </span>
                      <span className="font-semibold text-slate-200">{item.title}</span>
                    </div>

                    <span className="text-[10px] font-mono text-slate-500">{item.source}</span>
                  </div>

                  <p className="text-[11px] text-slate-300 leading-relaxed">{item.claim}</p>

                  <div className="pt-1 flex items-center justify-between">
                    <button
                      onClick={() => toggleEvidenceExpand(idx)}
                      className="text-[10px] font-mono text-blue-400 hover:text-blue-300 flex items-center gap-1"
                    >
                      <span>{isExpanded ? 'Hide details' : 'View details →'}</span>
                    </button>
                  </div>

                  {isExpanded && (
                    <div className="mt-2 p-2 rounded bg-slate-900 border border-slate-800 text-[11px] text-slate-400 font-mono">
                      {item.details}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* ================= TAB 3: GRAPH ================= */}
        {activeTab === 'graph' && (
          <div className="h-[460px] w-full">
            <GraphExplorer graphData={graphData} caseId={caseId} />
          </div>
        )}
      </div>

      {/* What Changed Modal / Overlay */}
      {showWhatChangedModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-lg max-w-md w-full p-5 space-y-3 shadow-2xl">
            <h4 className="text-sm font-bold text-slate-100 uppercase font-mono">
              Investigation Assessment Delta
            </h4>
            <div className="bg-slate-950 p-3 rounded border border-slate-800 text-xs text-slate-300 space-y-2 font-mono">
              <p>
                <span className="text-slate-500">Before:</span> Confidence 0.72 (Residual uncertainty on authorization)
              </p>
              <p>
                <span className="text-slate-500">Evidence:</span> Customer denial confirmed via validation loop
              </p>
              <p>
                <span className="text-slate-500">After:</span> Confidence 0.86 (Verdict confirmed as fraud)
              </p>
              <p>
                <span className="text-slate-500">NBA Impact:</span> Elevated routing from VERIFY to BLOCK_CARD + L2 SAR filing
              </p>
            </div>
            <button
              onClick={() => setShowWhatChangedModal(false)}
              className="w-full py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
