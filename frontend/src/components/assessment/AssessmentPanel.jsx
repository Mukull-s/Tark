import React from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Lock,
  ArrowRight,
  History,
  FileBadge,
  AlertTriangle,
  ExternalLink
} from '../common/Icons';

export default function AssessmentPanel({
  caseData,
  approvedActions = [],
  onApproveAction,
  onRejectAction,
  onRequestEvidence,
  onOpenPolicyModal,
  onOpenCaseMemory,
  onOpenSAR,
  isEvidenceProvided = false
}) {
  if (!caseData || !caseData.case) return null;

  const c = caseData.case;
  const isFraud = c.verdict === 'fraud' || (c.fraud_probability && c.fraud_probability >= 0.75);
  const confidence = c.fraud_probability ? (c.fraud_probability * 100).toFixed(0) : '86';
  const rawRiskScore = caseData.risk_score || (caseData.case_id === 'HHG-017' ? 0.57 : 0.61);

  // NBA recommendations
  const initialNba = caseData.next_best_actions?.initial || [
    { action: 'VERIFY_WITH_CUSTOMER', approval_route: 'auto', reason: 'R1: Weak model score, confirm authorization before block.' }
  ];
  const finalNba = caseData.next_best_actions?.final || [
    { action: 'BLOCK_CARD', approval_route: 'L1', reason: 'R2 & R5: Customer denied transaction + shared device syndicate.' }
  ];

  const primaryAction = finalNba[0] || {
    action: 'BLOCK_CARD',
    approval_route: 'L1',
    reason: 'Customer denial + shared device + rapid testing transactions.'
  };

  const isApproved = approvedActions.includes(primaryAction.action);
  const isHumanApprovalRequired = primaryAction.approval_route === 'L1' || primaryAction.approval_route === 'L2' || primaryAction.route === 'L1' || primaryAction.route === 'L2';

  // Key findings checklist
  const keyFindings = [
    'Customer denied transaction (out-of-band validation)',
    'Shared device DEV-9104 links to 3 distinct customer accounts',
    'Rapid micro-authorizations pattern (card testing)',
    'Similar historical closed case found in Case Memory (CC-0141)'
  ];

  return (
    <div className="space-y-4 text-slate-200">
      {/* 1. INVESTIGATION ASSESSMENT CARD */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3.5 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
          <span className="text-xs font-black uppercase tracking-wider text-slate-100 font-mono">
            Investigation Assessment
          </span>

          <span
            className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold uppercase border ${
              isFraud
                ? 'bg-red-500/20 text-red-400 border-red-500/40'
                : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
            }`}
          >
            {isFraud ? 'HIGH RISK' : 'MEDIUM RISK'}
          </span>
        </div>

        {/* Triple Metric Distinction: Bank Input vs Agent Assessment vs Confidence */}
        <div className="grid grid-cols-3 gap-2 bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 text-center font-mono">
          <div>
            <span className="text-[9px] uppercase text-slate-500 block">Bank Score</span>
            <span className="text-xs text-slate-300 font-bold">{rawRiskScore}</span>
          </div>
          <div className="border-x border-slate-800 px-1">
            <span className="text-[9px] uppercase text-slate-500 block">Verdict</span>
            <span className={`text-xs font-bold ${isFraud ? 'text-red-400' : 'text-emerald-400'}`}>
              {c.verdict ? c.verdict.toUpperCase() : 'FRAUD'}
            </span>
          </div>
          <div>
            <span className="text-[9px] uppercase text-slate-500 block">Confidence</span>
            <span className="text-xs text-blue-400 font-bold">{confidence}%</span>
          </div>
        </div>

        {/* Clean Horizontal Confidence Bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-[11px] font-mono">
            <span className="text-slate-400">Agent Confidence Bar</span>
            <span className="text-slate-200 font-bold">{confidence}%</span>
          </div>
          <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isFraud ? 'bg-red-500' : 'bg-blue-500'
              }`}
              style={{ width: `${confidence}%` }}
            ></div>
          </div>
        </div>

        {/* Key Findings Checklist */}
        <div className="space-y-2 pt-2 border-t border-slate-800/80">
          <span className="text-[10px] uppercase font-bold text-slate-400 block font-mono">
            KEY FINDINGS
          </span>
          <div className="space-y-1.5 text-xs">
            {keyFindings.map((finding, idx) => (
              <div key={idx} className="flex items-start gap-2 text-slate-300">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <span className="leading-snug text-[11px]">{finding}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Current Uncertainty */}
        <div className="bg-slate-950/90 border border-slate-800 p-2.5 rounded-md space-y-1">
          <div className="flex items-center gap-1.5 text-[10px] font-bold font-mono uppercase text-slate-400">
            <HelpCircle className="w-3 h-3 text-amber-400" />
            <span>CURRENT UNCERTAINTY</span>
          </div>
          <p className="text-[11px] text-slate-300">
            {isEvidenceProvided
              ? 'Resolved: Customer confirmed denial of transaction under validation loop.'
              : 'Customer authorization was initially unknown. Resolved via out-of-band verification.'}
          </p>
        </div>
      </div>

      {/* 2. NEXT BEST ACTION CARD */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3.5 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
          <span className="text-xs font-black uppercase tracking-wider text-slate-100 font-mono">
            Next Best Action
          </span>

          <span
            className={`text-[9px] px-2 py-0.5 rounded font-mono font-bold uppercase ${
              isHumanApprovalRequired
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
            }`}
          >
            {isHumanApprovalRequired ? 'REQUIRES APPROVAL' : 'AUTO-EXECUTABLE'}
          </span>
        </div>

        {/* Action Title & Rationale */}
        <div className="space-y-1 bg-slate-950 p-3 rounded-lg border border-slate-800">
          <div className="flex items-center justify-between">
            <div className="text-base font-black text-slate-100 font-mono tracking-tight flex items-center gap-2">
              <Lock className="w-4 h-4 text-red-400" />
              <span>{primaryAction.action}</span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
              {primaryAction.approval_route || primaryAction.route || 'L1'}
            </span>
          </div>

          <p className="text-xs text-slate-300 pt-1 leading-snug">
            {primaryAction.reason || 'Customer denial + shared device + rapid transactions.'}
          </p>
        </div>

        {/* Governance Routing */}
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 px-1">
          <span>Governance Route:</span>
          <span className="text-slate-200 font-bold">
            {primaryAction.approval_route === 'L1' || primaryAction.route === 'L1'
              ? 'L1 — Team Lead'
              : primaryAction.approval_route === 'L2' || primaryAction.route === 'L2'
              ? 'L2 — Fraud Manager'
              : 'Auto-Executed Policy'}
          </span>
        </div>

        {/* Action Execution Buttons */}
        {isApproved ? (
          <div className="bg-emerald-950/40 border border-emerald-800/80 text-emerald-300 p-2.5 rounded-lg text-xs flex items-center justify-between font-mono">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="font-bold">ACTION EXECUTED & COMMITTED</span>
            </div>
            <span className="text-[10px] text-emerald-400">01:15:00</span>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2 pt-1">
            <button
              onClick={() => onApproveAction(primaryAction)}
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-black rounded-lg text-xs tracking-wider uppercase flex items-center justify-center gap-1.5 shadow transition"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>APPROVE</span>
            </button>

            <button
              onClick={() => onRejectAction(primaryAction)}
              className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-lg text-xs tracking-wider uppercase flex items-center justify-center gap-1.5 border border-slate-700 transition"
            >
              <XCircle className="w-3.5 h-3.5 text-red-400" />
              <span>REJECT</span>
            </button>
          </div>
        )}

        {/* Secondary Action Links */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-xs">
          <button
            onClick={onRequestEvidence}
            className="text-slate-400 hover:text-slate-200 text-[11px] underline"
          >
            Request More Evidence
          </button>

          <button
            onClick={onOpenPolicyModal}
            className="text-blue-400 hover:text-blue-300 text-[11px] flex items-center gap-1 font-mono"
          >
            <span>View Policy Details</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* 3. CASE MEMORY & SAR QUICK LINKS */}
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={onOpenCaseMemory}
          className="p-3 bg-slate-900 hover:bg-slate-850 border border-slate-800 rounded-lg text-left transition group space-y-1"
        >
          <div className="flex items-center gap-1.5 text-teal-400 text-xs font-mono font-bold">
            <History className="w-3.5 h-3.5" />
            <span>Case Memory</span>
          </div>
          <div className="text-[11px] text-slate-300">
            4 historical cases found
          </div>
          <div className="text-[10px] text-teal-400 flex items-center gap-1 group-hover:underline">
            <span>View cases</span>
            <ArrowRight className="w-2.5 h-2.5" />
          </div>
        </button>

        <button
          onClick={onOpenSAR}
          className="p-3 bg-slate-900 hover:bg-slate-850 border border-slate-800 rounded-lg text-left transition group space-y-1"
        >
          <div className="flex items-center gap-1.5 text-purple-400 text-xs font-mono font-bold">
            <FileBadge className="w-3.5 h-3.5" />
            <span>SAR Filing</span>
          </div>
          <div className="text-[11px] text-slate-300">
            Mandatory L2 Review
          </div>
          <div className="text-[10px] text-purple-400 flex items-center gap-1 group-hover:underline">
            <span>View SAR filing</span>
            <ArrowRight className="w-2.5 h-2.5" />
          </div>
        </button>
      </div>
    </div>
  );
}
