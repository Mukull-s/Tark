import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Search,
  FileText,
  Zap,
  Activity,
  Cpu,
  Clock,
  DollarSign,
  Layers,
  ArrowRight,
  ExternalLink,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Terminal,
  Compass,
  Share2,
  RotateCcw,
  Play,
  CheckSquare,
  Lock,
  Server,
  Database,
  UserCheck,
  UserX,
  User,
  CreditCard,
  Laptop
} from 'lucide-react';

import GraphNetwork from './components/GraphNetwork';
import EvidenceCompass from './components/EvidenceCompass';
import SarDrawer from './components/SarDrawer';

const CASE_IDS = Array.from({ length: 20 }, (_, i) => {
  const num = (i + 1).toString().padStart(3, '0');
  return `HHG-${num}`;
});

export default function App() {
  const [selectedCaseId, setSelectedCaseId] = useState('HHG-004');
  const [activeNav, setActiveNav] = useState('investigations'); // 'cases' | 'investigations' | 'approvals' | 'memory' | 'graph' | 'evidence' | 'reports'
  const [activeTab, setActiveTab] = useState('timeline'); // 'timeline' | 'evidence' | 'graph'
  const [caseData, setCaseData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSarDrawerOpen, setIsSarDrawerOpen] = useState(false);

  // Investigation Simulation & Adaptive Loop State
  const [activeStepIndex, setActiveStepIndex] = useState(7);
  const [isEvidenceProvided, setIsEvidenceProvided] = useState(false);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [actionApproved, setActionApproved] = useState(false);

  // Dynamically load case data from cases/${selectedCaseId}.json
  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setActionApproved(false);
    setIsEvidenceProvided(false);
    setActiveStepIndex(7);

    fetch(`/cases/${selectedCaseId}.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (isMounted) {
          setCaseData(data);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        console.error(`Failed to load case data for ${selectedCaseId}:`, err);
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedCaseId]);

  const filteredCases = CASE_IDS.filter((id) =>
    id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const caseInfo = caseData?.case || {};
  const exposureUsd = caseInfo.exposure_usd !== undefined ? caseInfo.exposure_usd.toFixed(2) : '128.33';
  const latency = caseData?.latency_s || '6.72';
  const tokens = caseData?.tokens ? caseData.tokens.toLocaleString() : '1,090';
  const verdict = caseInfo.verdict || 'confirmed_fraud';
  const fraudProb = caseInfo.fraud_probability || 0.925;

  // Extract Customer & Device details
  let custId = 'C08106';
  let cardId = 'C08106-K1';
  let deviceId = `DEV-9104 (Samsung SM-G892A)`;

  if (caseData?.tool_calls) {
    const cCall = caseData.tool_calls.find((t) => t.params?.cust_id);
    if (cCall?.params?.cust_id) custId = cCall.params.cust_id;
    const cardCall = caseData.tool_calls.find((t) => t.params?.c_id);
    if (cardCall?.params?.c_id) cardId = cardCall.params.c_id;
  }

  // Canonical Investigation Steps for Replay
  const steps = [
    {
      time: '09:01:15',
      title: 'ALERT TRIGGER RECEIVED',
      status: 'COMPLETED',
      desc: 'Real-time fraud detection alert ingested into investigation queue.',
      details: 'Bank risk score 0.61 exceeded threshold 0.50'
    },
    {
      time: '09:02:15',
      title: 'TIGERGRAPH WINDOW TRAVERSAL',
      status: 'COMPLETED',
      desc: 'Executing card_window(window_hours=24)... Found 3 sub-$3 micro-authorizations.',
      details: 'High velocity micro-transactions detected in window'
    },
    {
      time: '09:03:15',
      title: 'MULTI-HOP HARDWARE LINKAGE',
      status: 'COMPLETED',
      desc: `Executing device_neighbors()... Device profile shared with card ${cardId} and closed case CC-0141.`,
      details: '3 distinct customer accounts linked to single device fingerprint'
    },
    {
      time: '09:04:15',
      title: 'POLICY FIREWALL EVALUATION',
      status: 'COMPLETED',
      desc: 'Evaluating bank policy Rule R1: single weak pattern requires identity/transaction verification.',
      details: 'Policy check passed - trigger adaptive evidence loop'
    },
    {
      time: '09:05:15',
      title: 'ADAPTIVE EVIDENCE REQUESTED',
      status: isEvidenceProvided ? 'COMPLETED' : 'PENDING',
      desc: 'Agent paused execution: dispatching customer_validation inquiry.',
      details: 'SMS/Email gateway verification requested'
    },
    {
      time: '09:06:15',
      title: 'GRAPH EVIDENCE INTEGRATION',
      status: isEvidenceProvided ? 'COMPLETED' : 'PENDING',
      desc: 'Out-of-band response processed. Likelihood Ratio (LR) recalculated to 2.4.',
      details: 'Calibrated fraud probability updated to 92.5%'
    },
    {
      time: '09:07:15',
      title: 'GOVERNANCE POLICY ACTION',
      status: actionApproved ? 'COMPLETED' : 'PENDING',
      desc: 'Formulating Next Best Action: BLOCK_CARD under Rule R2.',
      details: 'Route: L1 - Team Lead approval mandated'
    },
    {
      time: '09:08:15',
      title: 'CONFIDENT DECISION REACHED',
      status: actionApproved ? 'COMPLETED' : 'PENDING',
      desc: 'Investigation closed. Audit trace written to TigerGraph Savanna.',
      details: 'CONFIDENCE: 99% | VERDICT: CONFIRMED_FRAUD'
    }
  ];

  const handleStartInvestigation = () => {
    setIsInvestigating(true);
    setActiveStepIndex(0);
    setIsEvidenceProvided(false);
    setActionApproved(false);

    let idx = 0;
    const interval = setInterval(() => {
      idx++;
      if (idx <= 7) {
        setActiveStepIndex(idx);
        if (idx === 4) setIsEvidenceProvided(true);
      } else {
        clearInterval(interval);
        setIsInvestigating(false);
      }
    }, 600);
  };

  return (
    <div className="h-screen w-screen bg-[#050505] text-[#FFFFFF] flex flex-col font-sans overflow-hidden select-none">
      {/* 1. Global Header Bar */}
      <header className="h-14 bg-[#0F0F0F] border-b border-[#222222] px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-[#FFFFFF] text-[#050505] flex items-center justify-center font-mono font-black text-xs">
              T
            </div>
            <div>
              <h1 className="font-space text-sm font-bold tracking-tight text-[#FFFFFF] flex items-center gap-2">
                TARK <span className="font-mono text-[10px] bg-[#222222] px-1.5 py-0.5 text-[#777777]">v1.0</span>
              </h1>
              <span className="font-mono text-[10px] text-[#777777] block -mt-0.5">
                Fraud Investigation Workstation
              </span>
            </div>
          </div>

          <div className="h-5 w-[1px] bg-[#222222]" />

          {/* Search Bar */}
          <div className="relative w-72">
            <Search className="w-3.5 h-3.5 text-[#777777] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search cases, customers, cards... (e.g. HHG-004)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#050505] border border-[#222222] pl-8 pr-3 py-1 text-xs font-mono text-[#FFFFFF] placeholder-[#777777] focus:outline-none focus:border-[#FFFFFF]"
            />
          </div>
        </div>

        {/* Header Status Badges */}
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="flex items-center gap-1.5 bg-[#050505] border border-[#222222] px-2.5 py-1">
            <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
            <span className="text-[#777777]">API:</span>
            <span className="text-[#FFFFFF] font-bold">:8000</span>
          </span>

          <span className="flex items-center gap-1.5 bg-[#050505] border border-[#222222] px-2.5 py-1">
            <Database className="w-3.5 h-3.5 text-[#06B6D4]" />
            <span className="text-[#777777]">Savanna GSQL:</span>
            <span className="text-[#06B6D4] font-bold">24ms</span>
          </span>

          <span className="flex items-center gap-1.5 bg-[#FFFFFF] text-[#050505] font-bold px-3 py-1">
            CASE: {selectedCaseId}
          </span>

          <button
            onClick={() => setIsSarDrawerOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1 bg-[#FF3366]/10 border border-[#FF3366]/40 text-[#FF3366] font-mono text-xs font-bold hover:bg-[#FF3366]/20 transition"
          >
            <FileText className="w-3.5 h-3.5" />
            REPORTS (SAR)
          </button>
        </div>
      </header>

      {/* 2. Main App Body (Sidebar + Central Workstation) */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Left Sidebar Navigation */}
        <aside className="w-56 bg-[#0F0F0F] border-r border-[#222222] flex flex-col justify-between shrink-0 font-mono text-xs">
          <div className="p-3 space-y-4">
            {/* WORKSPACE GROUP */}
            <div>
              <span className="text-[10px] font-bold text-[#777777] uppercase tracking-wider block mb-2 px-2">
                WORKSPACE
              </span>
              <nav className="space-y-1">
                <button
                  onClick={() => setActiveNav('cases')}
                  className={`w-full flex items-center justify-between px-3 py-2 transition-colors ${
                    activeNav === 'cases' ? 'bg-[#FFFFFF] text-[#050505] font-bold' : 'text-[#777777] hover:bg-[#151515] hover:text-[#FFFFFF]'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5" /> Cases
                  </span>
                  <span className={`px-1.5 py-0.5 text-[10px] ${activeNav === 'cases' ? 'bg-[#050505] text-[#FFFFFF]' : 'bg-[#222222] text-[#777777]'}`}>
                    20
                  </span>
                </button>

                <button
                  onClick={() => setActiveNav('investigations')}
                  className={`w-full flex items-center justify-between px-3 py-2 transition-colors ${
                    activeNav === 'investigations' ? 'bg-[#FFFFFF] text-[#050505] font-bold' : 'text-[#777777] hover:bg-[#151515] hover:text-[#FFFFFF]'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Activity className="w-3.5 h-3.5" /> Investigations
                  </span>
                  <span className={`px-1.5 py-0.5 text-[10px] ${activeNav === 'investigations' ? 'bg-[#050505] text-[#FFFFFF]' : 'bg-[#222222] text-[#10B981]'}`}>
                    1
                  </span>
                </button>

                <button
                  onClick={() => setActiveNav('approvals')}
                  className={`w-full flex items-center justify-between px-3 py-2 transition-colors ${
                    activeNav === 'approvals' ? 'bg-[#FFFFFF] text-[#050505] font-bold' : 'text-[#777777] hover:bg-[#151515] hover:text-[#FFFFFF]'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <CheckSquare className="w-3.5 h-3.5" /> Approvals
                  </span>
                  <span className={`px-1.5 py-0.5 text-[10px] ${activeNav === 'approvals' ? 'bg-[#050505] text-[#FFFFFF]' : 'bg-[#222222] text-[#F59E0B]'}`}>
                    {actionApproved ? 0 : 1}
                  </span>
                </button>

                <button
                  onClick={() => setActiveNav('memory')}
                  className={`w-full flex items-center justify-between px-3 py-2 transition-colors ${
                    activeNav === 'memory' ? 'bg-[#FFFFFF] text-[#050505] font-bold' : 'text-[#777777] hover:bg-[#151515] hover:text-[#FFFFFF]'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Database className="w-3.5 h-3.5" /> Case Memory
                  </span>
                </button>
              </nav>
            </div>

            {/* ANALYSIS GROUP */}
            <div>
              <span className="text-[10px] font-bold text-[#777777] uppercase tracking-wider block mb-2 px-2">
                ANALYSIS
              </span>
              <nav className="space-y-1">
                <button
                  onClick={() => setActiveNav('graph')}
                  className={`w-full flex items-center gap-2 px-3 py-2 transition-colors ${
                    activeNav === 'graph' ? 'bg-[#FFFFFF] text-[#050505] font-bold' : 'text-[#777777] hover:bg-[#151515] hover:text-[#FFFFFF]'
                  }`}
                >
                  <Share2 className="w-3.5 h-3.5" /> Graph Explorer
                </button>

                <button
                  onClick={() => setActiveNav('evidence')}
                  className={`w-full flex items-center gap-2 px-3 py-2 transition-colors ${
                    activeNav === 'evidence' ? 'bg-[#FFFFFF] text-[#050505] font-bold' : 'text-[#777777] hover:bg-[#151515] hover:text-[#FFFFFF]'
                  }`}
                >
                  <ShieldAlert className="w-3.5 h-3.5" /> Evidence
                </button>
              </nav>
            </div>

            {/* REPORTING GROUP */}
            <div>
              <span className="text-[10px] font-bold text-[#777777] uppercase tracking-wider block mb-2 px-2">
                REPORTING
              </span>
              <nav className="space-y-1">
                <button
                  onClick={() => setIsSarDrawerOpen(true)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-[#777777] hover:bg-[#151515] hover:text-[#FFFFFF] transition-colors"
                >
                  <FileText className="w-3.5 h-3.5" /> Reports (SAR)
                </button>
              </nav>
            </div>
          </div>

          {/* SYSTEM STATUS FOOTER */}
          <div className="p-3 border-t border-[#222222] bg-[#050505] space-y-1 text-[10px] text-[#777777]">
            <span className="font-bold text-[#FFFFFF] block mb-1 uppercase">SYSTEM STATUS</span>
            <div className="flex items-center justify-between">
              <span>FastAPI Gateway</span>
              <span className="text-[#10B981] font-bold">ONLINE</span>
            </div>
            <div className="flex items-center justify-between">
              <span>TigerGraph Savanna</span>
              <span className="text-[#10B981] font-bold">CONNECTED</span>
            </div>
            <div className="flex items-center justify-between">
              <span>DataSource Mode</span>
              <span className="text-[#06B6D4] font-bold">LIVE</span>
            </div>
          </div>
        </aside>

        {/* Central Workstation Pane */}
        <main className="flex-1 flex flex-col min-w-0 bg-[#050505] overflow-y-auto">
          {/* Top Active Case Banner */}
          <div className="p-4 border-b border-[#222222] bg-[#0F0F0F] flex flex-wrap items-center justify-between gap-4 shrink-0">
            <div>
              <div className="flex items-center gap-3">
                <h2 className="font-mono text-xl font-bold text-[#FFFFFF]">
                  {selectedCaseId}
                </h2>
                <span className="px-2 py-0.5 bg-[#222222] text-[#FFFFFF] font-mono text-xs">
                  Customer Report
                </span>
                <span className="font-space text-lg font-bold text-[#FFFFFF]">
                  ${exposureUsd} USD
                </span>
                <span className="px-2 py-0.5 bg-[#FF3366]/20 text-[#FF3366] border border-[#FF3366]/40 font-mono text-xs font-bold uppercase">
                  HIGH RISK
                </span>
                <span className="flex items-center gap-1 text-[#10B981] font-mono text-xs">
                  <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" /> ACTIVE
                </span>
              </div>

              <div className="flex items-center gap-4 mt-2 font-mono text-xs text-[#777777]">
                <span>
                  CUSTOMER: <strong className="text-[#FFFFFF]">{custId}</strong>
                </span>
                <span>
                  CARD: <strong className="text-[#FFFFFF]">{cardId}</strong>
                </span>
                <span>
                  DEVICE: <strong className="text-[#FFFFFF]">{deviceId}</strong>
                </span>
                <span>
                  PATTERN: <strong className="text-[#FFFFFF] uppercase">{caseInfo.pattern ? caseInfo.pattern.replace(/_/g, ' ') : 'CARD NOT PRESENT'}</strong>
                </span>
              </div>
            </div>

            {/* Start Investigation / Replay Controls */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleStartInvestigation}
                disabled={isInvestigating}
                className="flex items-center gap-2 px-4 py-2 bg-[#2563EB] hover:bg-[#1D4ED8] text-[#FFFFFF] font-mono text-xs font-bold uppercase transition disabled:opacity-50"
              >
                {isInvestigating ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" /> RUNNING...
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" /> START INVESTIGATION
                  </>
                )}
              </button>

              <button
                onClick={() => {
                  setActiveStepIndex(0);
                  setIsEvidenceProvided(false);
                }}
                className="flex items-center gap-1.5 px-3 py-2 bg-[#050505] hover:bg-[#151515] border border-[#222222] text-[#FFFFFF] font-mono text-xs transition"
              >
                <RotateCcw className="w-3.5 h-3.5 text-[#777777]" /> Replay
              </button>
            </div>
          </div>

          {/* DYNAMIC VIEW CONTENT */}
          {isLoading ? (
            <div className="flex-1 flex flex-col items-center justify-center p-12 gap-3 text-center">
              <RefreshCw className="w-6 h-6 text-[#777777] animate-spin" />
              <span className="font-mono text-xs text-[#777777]">
                LOADING INVESTIGATION DATASET FOR {selectedCaseId}...
              </span>
            </div>
          ) : (
            <>
              {/* VIEW A: INVESTIGATIONS WORKSTATION (3-COLUMN WORKFLOW) */}
              {activeNav === 'investigations' && (
                <div className="p-4 flex-1 overflow-y-auto">
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
                    {/* LEFT COLUMN (~25% / 3 cols): INVESTIGATION TIMELINE */}
                    <div className="lg:col-span-3 bg-[#0F0F0F] border border-[#222222] p-3 flex flex-col h-[740px]">
                      <div className="flex items-center justify-between pb-2 border-b border-[#222222] mb-3">
                        <div className="flex items-center gap-2 font-mono text-xs font-bold text-[#FFFFFF]">
                          <Clock className="w-3.5 h-3.5 text-[#FFFFFF]" />
                          <span>INVESTIGATION TIMELINE</span>
                        </div>
                        <span className="font-mono text-[10px] text-[#777777]">
                          8 EVENTS
                        </span>
                      </div>

                      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                        {steps.map((s, idx) => {
                          const isActive = idx === activeStepIndex;
                          const isDone = idx <= activeStepIndex;
                          return (
                            <div
                              key={idx}
                              onClick={() => setActiveStepIndex(idx)}
                              title={s.details}
                              className={`p-2.5 border transition-all cursor-pointer font-mono text-xs ${
                                isActive
                                  ? 'bg-[#050505] border-[#FFFFFF] text-[#FFFFFF]'
                                  : isDone
                                  ? 'bg-[#050505]/60 border-[#222222] text-[#FFFFFF]'
                                  : 'bg-[#050505]/20 border-[#1A1A1A] text-[#777777]'
                              }`}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-[10px] text-[#777777]">{s.time}</span>
                                <span
                                  className={`text-[9px] font-bold px-1.5 py-0.2 border ${
                                    isDone
                                      ? 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/30'
                                      : 'bg-[#222222] text-[#777777] border-[#333333]'
                                  }`}
                                >
                                  {isDone ? 'COMPLETED' : 'PENDING'}
                                </span>
                              </div>
                              <h4 className="font-bold text-xs leading-snug">{s.title}</h4>
                              <p className="text-[11px] text-[#777777] mt-1 line-clamp-2">
                                {s.desc}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* CENTER COLUMN (~45% / 5 cols): TABS & ADAPTIVE LOOP AREA */}
                    <div className="lg:col-span-5 space-y-4">
                      {/* Main Tab Switcher Bar */}
                      <div className="bg-[#0F0F0F] border border-[#222222] p-1 flex items-center justify-between font-mono text-xs">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => setActiveTab('timeline')}
                            className={`px-3 py-1.5 font-bold transition ${
                              activeTab === 'timeline' ? 'bg-[#FFFFFF] text-[#050505]' : 'text-[#777777] hover:text-[#FFFFFF]'
                            }`}
                          >
                            Timeline
                          </button>
                          <button
                            onClick={() => setActiveTab('evidence')}
                            className={`px-3 py-1.5 font-bold transition ${
                              activeTab === 'evidence' ? 'bg-[#FFFFFF] text-[#050505]' : 'text-[#777777] hover:text-[#FFFFFF]'
                            }`}
                          >
                            Evidence
                          </button>
                          <button
                            onClick={() => setActiveTab('graph')}
                            className={`px-3 py-1.5 font-bold transition ${
                              activeTab === 'graph' ? 'bg-[#FFFFFF] text-[#050505]' : 'text-[#777777] hover:text-[#FFFFFF]'
                            }`}
                          >
                            Graph
                          </button>
                        </div>
                        <span className="text-[10px] text-[#777777] pr-2">
                          8 Trace Events Recorded
                        </span>
                      </div>

                      {/* TAB Content 1: TIMELINE OVERVIEW & ADAPTIVE EVIDENCE BANNER */}
                      {activeTab === 'timeline' && (
                        <div className="space-y-4">
                          {/* ADAPTIVE LOOP BANNER */}
                          <div className="bg-[#0F0F0F] border border-[#F59E0B]/40 p-4 space-y-3">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2 text-[#F59E0B] font-mono text-xs font-bold">
                                <AlertTriangle className="w-4 h-4" />
                                <span>MORE EVIDENCE REQUIRED (ADAPTIVE LOOP)</span>
                              </div>
                              <span className="text-[10px] font-mono text-[#777777]">
                                Initial pattern score: {(fraudProb * 100).toFixed(0)}%
                              </span>
                            </div>

                            <p className="font-mono text-xs text-[#FFFFFF]">
                              Customer authorization status is unknown. Out-of-band verification required to resolve risk shift.
                            </p>

                            <div className="flex items-center gap-3 pt-1">
                              <button
                                onClick={() => setIsEvidenceProvided(true)}
                                className={`flex items-center gap-1.5 px-3 py-1.5 font-mono text-xs font-bold transition ${
                                  isEvidenceProvided
                                    ? 'bg-[#10B981] text-[#050505]'
                                    : 'bg-[#F59E0B] hover:bg-[#D97706] text-[#050505]'
                                }`}
                              >
                                <UserX className="w-3.5 h-3.5" />
                                {isEvidenceProvided ? 'Customer Denial Received' : 'Provide Customer Denial'}
                              </button>

                              <button
                                onClick={() => setIsEvidenceProvided(true)}
                                className="px-3 py-1.5 bg-[#050505] hover:bg-[#151515] border border-[#222222] text-[#FFFFFF] font-mono text-xs transition"
                              >
                                Authorize
                              </button>
                            </div>
                          </div>

                          {/* Replay Step Progress Indicator */}
                          <div className="bg-[#0F0F0F] border border-[#222222] p-3 flex items-center justify-between font-mono text-xs">
                            <span className="text-[#777777]">
                              Replay Step: <strong className="text-[#FFFFFF]">{activeStepIndex + 1} / 8</strong>
                            </span>
                            <div className="flex items-center gap-1">
                              {steps.map((_, i) => (
                                <button
                                  key={i}
                                  onClick={() => setActiveStepIndex(i)}
                                  className={`w-6 h-6 flex items-center justify-center text-[10px] font-bold border transition ${
                                    i === activeStepIndex
                                      ? 'bg-[#2563EB] text-[#FFFFFF] border-[#2563EB]'
                                      : i <= activeStepIndex
                                      ? 'bg-[#222222] text-[#FFFFFF] border-[#333333]'
                                      : 'bg-[#050505] text-[#777777] border-[#1A1A1A]'
                                  }`}
                                >
                                  {i + 1}
                                </button>
                              ))}
                            </div>
                          </div>

                          {/* Detailed Step Cards list */}
                          <div className="space-y-2">
                            {steps.slice(0, activeStepIndex + 1).map((st, i) => (
                              <div
                                key={i}
                                className="bg-[#0F0F0F] border border-[#222222] p-3 font-mono text-xs space-y-1.5 transition-all"
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981]" />
                                    <span className="font-bold text-[#FFFFFF]">{st.title}</span>
                                    <span className="text-[10px] text-[#777777]">[{st.time}]</span>
                                  </div>
                                  <span className="text-[9px] bg-[#10B981]/10 text-[#10B981] px-1.5 py-0.2 border border-[#10B981]/30 uppercase">
                                    {st.status}
                                  </span>
                                </div>
                                <p className="text-[#777777] text-xs leading-relaxed">{st.desc}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* TAB Content 2: EVIDENCE GRID */}
                      {activeTab === 'evidence' && (
                        <div className="bg-[#0F0F0F] border border-[#222222] p-4 space-y-3">
                          <h3 className="font-mono text-xs font-bold text-[#FFFFFF] uppercase border-b border-[#222222] pb-2">
                            Empirical Evidence Records
                          </h3>
                          <div className="space-y-2">
                            {caseInfo.evidence?.map((ev, i) => (
                              <div key={i} className="bg-[#050505] border border-[#222222] p-3 font-mono text-xs space-y-1">
                                <div className="flex items-center justify-between text-[#FFFFFF] font-bold">
                                  <span>{ev.type}</span>
                                  <span className="text-[#10B981]">LR: {ev.lr}</span>
                                </div>
                                <p className="text-[#777777]">{ev.finding}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* TAB Content 3: GRAPH EXPLORER */}
                      {activeTab === 'graph' && (
                        <div className="h-[480px]">
                          <GraphNetwork caseData={caseData} selectedCaseId={selectedCaseId} />
                        </div>
                      )}
                    </div>

                    {/* RIGHT COLUMN (~30% / 4 cols): INVESTIGATION ASSESSMENT & NEXT BEST ACTION */}
                    <div className="lg:col-span-4 space-y-4">
                      {/* ASSESSMENT CARD */}
                      <div className="bg-[#0F0F0F] border border-[#222222] p-4 space-y-4">
                        <div className="flex items-center justify-between pb-2 border-b border-[#222222]">
                          <span className="font-mono text-xs font-bold text-[#FFFFFF] uppercase">
                            INVESTIGATION ASSESSMENT
                          </span>
                          <span className="px-2 py-0.5 bg-[#FF3366]/20 text-[#FF3366] border border-[#FF3366]/40 font-mono text-[10px] font-bold uppercase">
                            HIGH RISK
                          </span>
                        </div>

                        {/* Metrics Bar */}
                        <div className="grid grid-cols-3 gap-2 text-center font-mono">
                          <div className="bg-[#050505] border border-[#222222] p-2">
                            <span className="text-[10px] text-[#777777] block uppercase">BANK SCORE</span>
                            <span className="font-space text-base font-bold text-[#FFFFFF]">0.61</span>
                          </div>

                          <div className="bg-[#050505] border border-[#222222] p-2">
                            <span className="text-[10px] text-[#777777] block uppercase">VERDICT</span>
                            <span className="font-mono text-xs font-bold text-[#FF3366] uppercase block mt-1">
                              CONFIRMED_FRAUD
                            </span>
                          </div>

                          <div className="bg-[#050505] border border-[#222222] p-2">
                            <span className="text-[10px] text-[#777777] block uppercase">CONFIDENCE</span>
                            <span className="font-space text-base font-bold text-[#10B981]">99%</span>
                          </div>
                        </div>

                        {/* Confidence Progress Bar */}
                        <div className="space-y-1 font-mono text-[10px]">
                          <div className="flex justify-between text-[#777777]">
                            <span>Agent Confidence Bar</span>
                            <span className="text-[#FFFFFF] font-bold">99%</span>
                          </div>
                          <div className="w-full bg-[#050505] h-1.5 border border-[#222222] overflow-hidden">
                            <div className="bg-[#FF3366] h-full w-[99%]" />
                          </div>
                        </div>

                        {/* KEY FINDINGS CHECKLIST */}
                        <div className="space-y-2 pt-2 border-t border-[#222222]">
                          <span className="font-mono text-[10px] font-bold text-[#777777] uppercase block">
                            KEY FINDINGS
                          </span>
                          <ul className="space-y-1.5 font-mono text-xs text-[#FFFFFF]">
                            <li className="flex items-start gap-2">
                              <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981] shrink-0 mt-0.5" />
                              <span>Customer denied transaction (out-of-band validation)</span>
                            </li>
                            <li className="flex items-start gap-2">
                              <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981] shrink-0 mt-0.5" />
                              <span>Shared device {deviceId} links to 3 distinct customer accounts</span>
                            </li>
                            <li className="flex items-start gap-2">
                              <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981] shrink-0 mt-0.5" />
                              <span>Rapid micro-authorizations pattern (card testing)</span>
                            </li>
                            <li className="flex items-start gap-2">
                              <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981] shrink-0 mt-0.5" />
                              <span>Similar historical closed case found in Case Memory (CC-0141)</span>
                            </li>
                          </ul>
                        </div>

                        {/* CURRENT UNCERTAINTY NOTE */}
                        <div className="bg-[#050505] border border-[#222222] p-3 space-y-1 font-mono text-xs">
                          <span className="text-[10px] font-bold text-[#F59E0B] uppercase flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" /> CURRENT UNCERTAINTY
                          </span>
                          <p className="text-[#777777] text-[11px]">
                            Customer authorization was initially unknown. Resolved via out-of-band verification.
                          </p>
                        </div>
                      </div>

                      {/* NEXT BEST ACTION CARD */}
                      <div className="bg-[#0F0F0F] border border-[#222222] p-4 space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-[#222222]">
                          <span className="font-mono text-xs font-bold text-[#FFFFFF] uppercase">
                            NEXT BEST ACTION
                          </span>
                          <span className="px-2 py-0.5 bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/40 font-mono text-[10px] font-bold uppercase">
                            REQUIRES APPROVAL
                          </span>
                        </div>

                        <div className="bg-[#050505] border border-[#222222] p-3 space-y-2 font-mono text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-[#FFFFFF] text-sm flex items-center gap-2">
                              <Lock className="w-4 h-4 text-[#FF3366]" /> BLOCK_CARD
                            </span>
                            <span className="px-2 py-0.5 bg-[#2563EB]/20 text-[#2563EB] text-[10px] font-bold border border-[#2563EB]/40">
                              L1
                            </span>
                          </div>
                          <p className="text-[#777777] text-xs">
                            R2: Customer reported/denied transaction.
                          </p>
                          <div className="text-[10px] text-[#777777]">
                            Governance Route: <strong className="text-[#FFFFFF]">L1 - Team Lead</strong>
                          </div>
                        </div>

                        {actionApproved ? (
                          <div className="bg-[#10B981]/10 border border-[#10B981]/40 p-3 text-center font-mono text-xs text-[#10B981] font-bold flex items-center justify-center gap-2">
                            <CheckCircle2 className="w-4 h-4" /> ACTION APPROVED & EXECUTED
                          </div>
                        ) : (
                          <div className="grid grid-cols-2 gap-2 pt-1 font-mono text-xs">
                            <button
                              onClick={() => setActionApproved(true)}
                              className="flex items-center justify-center gap-1.5 py-2 bg-[#10B981] hover:bg-[#059669] text-[#050505] font-bold uppercase transition"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5" /> APPROVE
                            </button>
                            <button
                              onClick={() => setActionApproved(false)}
                              className="flex items-center justify-center gap-1.5 py-2 bg-[#050505] hover:bg-[#151515] border border-[#222222] text-[#FF3366] font-bold uppercase transition"
                            >
                              <UserX className="w-3.5 h-3.5" /> REJECT
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* VIEW B: CASES TABLE VIEW */}
              {activeNav === 'cases' && (
                <div className="p-5 space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-[#222222]">
                    <h3 className="font-mono text-sm font-bold text-[#FFFFFF] uppercase">
                      BENCHMARK TEST CASES ({CASE_IDS.length})
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 font-mono text-xs">
                    {CASE_IDS.map((cId) => {
                      const isSel = cId === selectedCaseId;
                      return (
                        <div
                          key={cId}
                          onClick={() => {
                            setSelectedCaseId(cId);
                            setActiveNav('investigations');
                          }}
                          className={`p-4 border transition cursor-pointer flex flex-col justify-between h-32 ${
                            isSel
                              ? 'bg-white text-black font-bold'
                              : 'bg-[#0F0F0F] text-[#FFFFFF] border-[#222222] hover:border-[#FFFFFF]'
                          }`}
                        >
                          <div className="flex justify-between items-center">
                            <span className="text-sm font-bold">{cId}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 border ${isSel ? 'bg-black text-white border-black' : 'bg-[#222222] text-[#777777] border-[#333333]'}`}>
                              READY
                            </span>
                          </div>
                          <div className="text-[11px] opacity-80">
                            Status: Active Alert
                          </div>
                          <div className="flex justify-between items-center pt-2 border-t border-current/20 text-[10px]">
                            <span>Click to Investigate</span>
                            <ChevronRight className="w-3.5 h-3.5" />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* VIEW C: FULL GRAPH EXPLORER */}
              {activeNav === 'graph' && (
                <div className="p-5 h-full flex flex-col">
                  <div className="flex-1">
                    <GraphNetwork caseData={caseData} selectedCaseId={selectedCaseId} />
                  </div>
                </div>
              )}

              {/* VIEW D: FULL EVIDENCE VIEW */}
              {activeNav === 'evidence' && (
                <div className="p-5 space-y-4">
                  <h3 className="font-mono text-sm font-bold text-[#FFFFFF] uppercase border-b border-[#222222] pb-3">
                    Grounded Evidence Registry ({caseInfo.evidence?.length || 0})
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
                    {caseInfo.evidence?.map((ev, idx) => (
                      <div key={idx} className="bg-[#0F0F0F] border border-[#222222] p-4 space-y-2">
                        <div className="flex justify-between items-center text-[#FFFFFF] font-bold">
                          <span>{ev.type}</span>
                          <span className="text-[#10B981]">LR: {ev.lr}</span>
                        </div>
                        <p className="text-[#777777] leading-relaxed">{ev.finding}</p>
                        <div className="text-[10px] text-[#777777] pt-2 border-t border-[#222222]">
                          SOURCE: <span className="text-[#FFFFFF]">{ev.source}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* VIEW E: APPROVALS QUEUE */}
              {activeNav === 'approvals' && (
                <div className="p-5 space-y-4">
                  <h3 className="font-mono text-sm font-bold text-[#FFFFFF] uppercase border-b border-[#222222] pb-3">
                    Governance Sign-Off Queue
                  </h3>
                  <div className="bg-[#0F0F0F] border border-[#222222] p-5 space-y-4 font-mono text-xs">
                    <div className="flex justify-between items-center border-b border-[#222222] pb-3">
                      <span className="font-bold text-[#FFFFFF]">Pending Actions Queue ({actionApproved ? 0 : 1})</span>
                      <span className="text-[#777777]">Case: {selectedCaseId}</span>
                    </div>

                    {actionApproved ? (
                      <div className="p-6 text-center text-[#10B981] font-bold space-y-2">
                        <CheckCircle2 className="w-8 h-8 mx-auto" />
                        <div>All Pending Policy Actions Approved & Dispatched</div>
                      </div>
                    ) : (
                      <div className="bg-[#050505] border border-[#222222] p-4 flex items-center justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-[#FFFFFF] text-sm">BLOCK_CARD</span>
                            <span className="px-2 py-0.5 bg-[#F59E0B]/20 text-[#F59E0B] text-[10px] font-bold border border-[#F59E0B]/40">
                              L1 - Team Lead
                            </span>
                          </div>
                          <p className="text-[#777777]">
                            Policy Rule R2: Customer reported/denied transaction with shared device link.
                          </p>
                        </div>
                        <button
                          onClick={() => setActionApproved(true)}
                          className="px-4 py-2 bg-[#10B981] hover:bg-[#059669] text-[#050505] font-bold uppercase transition"
                        >
                          Approve Action
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* VIEW F: CASE MEMORY VIEW */}
              {activeNav === 'memory' && (
                <div className="p-5 space-y-4 font-mono text-xs">
                  <h3 className="font-mono text-sm font-bold text-[#FFFFFF] uppercase border-b border-[#222222] pb-3">
                    TigerGraph Case Memory (GraphRAG Vector Retrieval)
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {['CC-0141', 'CC-3748', 'CC-2649', 'CC-4086'].map((cId, idx) => (
                      <div key={idx} className="bg-[#0F0F0F] border border-[#222222] p-4 space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="font-bold text-[#FFFFFF]">{cId}</span>
                          <span className="text-[10px] bg-[#FF3366]/20 text-[#FF3366] px-2 py-0.5 border border-[#FF3366]/40 uppercase font-bold">
                            CARD TESTING
                          </span>
                        </div>
                        <p className="text-[#777777]">
                          Confirmed card testing cluster involving shared hardware hash DEV-9104. Account blocked and SAR filed.
                        </p>
                        <div className="flex justify-between pt-2 border-t border-[#222222] text-[10px] text-[#777777]">
                          <span>Actions: BLOCK_CARD, FILE_SAR</span>
                          <span className="text-[#FFFFFF] font-bold">$1,240.00 USD</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>

      {/* 3. SAR Narrative Drawer */}
      <SarDrawer
        isOpen={isSarDrawerOpen}
        onClose={() => setIsSarDrawerOpen(false)}
        sarData={caseData?.sar}
        selectedCaseId={selectedCaseId}
      />
    </div>
  );
}
