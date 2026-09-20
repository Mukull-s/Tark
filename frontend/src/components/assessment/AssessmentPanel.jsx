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
  AlertTriangle
} from '../common/Icons';

export default function AssessmentPanel({
  caseData,
  approvedActions = [],
  onApproveAction,
  onRejectAction,
  onRequestEvidence,
  onOpenPolicyModal,
  onOpenCaseMemory,
  onOpenSAR
}) {
  if (!caseData || !caseData.case) return null;

  const c = caseData.case;
  const isFraud = c.verdict === 'fraud';
  const nba = caseData.next_best_actions?.final || [];
  const primaryAction = nba[0] || {
    action: 'BLOCK_CARD',
    route: 'L1',
    reason: 'Customer denied transaction + shared device linkage.'
  };

  const isApproved = approvedActions.includes(primaryAction.action);

  // Key findings list from case evidence
  const keyFindings = [
    'Customer denied transaction (validation loop)',
    'Shared device (Samsung SM-G892A)',
    'Rapid micro-authorizations (card testing pattern)',
    'Similar historical fraud case (CC-0141)'
  ];

  return (
    <div className="space-y-4 text-slate-200">
      {/* 1. Investigation Assessment Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
          <span className="text-[11px] font-black uppercase tracking-wider text-slate-400 font-mono">
            Investigation Assessment
          </span>

          <span
            className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold uppercase ${
              isFraud
                ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
            }`}
          >
            {isFraud ? 'HIGH RISK' : 'LOW RISK'}
          </span>
        </div>

        {/* Confidence Metric */}
        <div className="flex items-baseline justify-between pt-0.5">
          <span className="text-xs text-slate-400 font-medium">Investigation Confidence</span>
          <div className="flex items-baseline gap-1">
            <span className={`text-2xl font-black font-mono ${isFraud ? 'text-red-400' : 'text-emerald-400'}`}>
              {(c.fraud_probability * 100).toFixed(0)}%
            </span>
            <span className="text-[10px] text-slate-500 font-mono">CONF</span>
          </div>
        </div>

        {/* Key Findings List */}
        <div className="space-y-1.5 pt-2 border-t border-slate-800/60">
          <span className="text-[10px] uppercase font-bold text-slate-400 block font-mono">
            Key Findings
          </span>
          <div className="space-y-1">
            {keyFindings.map((finding, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <span className="leading-snug">{finding}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Current Uncertainty */}
        <div className="bg-slate-950/80 border border-slate-800 rounded p-2.5 text-xs text-slate-400 space-y-0.5">
          <div className="flex items-center gap-1.5 text-amber-400 font-mono text-[10px] font-bold uppercase">
            <AlertTriangle className="w-3 h-3" />
            <span>Residual Uncertainty</span>
          </div>
          <p className="text-[11px] text-slate-300 leading-snug">
            Customer authorization was initially unknown prior to verification loop.
          </p>
        </div>
      </div>

      {/* 2. Next Best Action Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
          <div className="flex items-center gap-1.5">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <span className="text-[11px] font-black uppercase tracking-wider text-slate-300 font-mono">
              Next Best Action
            </span>
          </div>

          <span
            className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold uppercase ${
              primaryAction.route === 'auto'
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
            }`}
          >
            {primaryAction.route === 'auto'
              ? 'AUTO ROUTE'
              : `APPROVAL: ${primaryAction.route} — TEAM LEAD`}
          </span>
        </div>

        {/* Primary Action Name */}
        <div className="space-y-1">
          <h3 className="text-xl font-black font-mono text-slate-100 tracking-tight">
            {primaryAction.action}
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            {primaryAction.reason ||
              'Customer denial + shared device hardware linkage + rapid testing pattern.'}
          </p>
        </div>

        {/* Action Execution Buttons */}
        <div className="space-y-2 pt-1 border-t border-slate-800/60">
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => onRejectAction && onRejectAction(primaryAction.action)}
              className="px-3 py-1.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-red-400 rounded text-xs font-semibold transition"
            >
              Reject
            </button>

            <button
              onClick={() => onApproveAction && onApproveAction(primaryAction.action, primaryAction.route)}
              disabled={isApproved}
              className={`px-3 py-1.5 rounded text-xs font-bold transition shadow ${
                isApproved
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/60 cursor-not-allowed'
                  : 'bg-amber-500 hover:bg-amber-400 text-slate-950'
              }`}
            >
              {isApproved ? 'Executed' : 'Approve'}
            </button>
          </div>

          <button
            onClick={onRequestEvidence}
            className="w-full py-1 text-center text-xs text-slate-400 hover:text-slate-200 transition"
          >
            Request More Evidence
          </button>

          <button
            onClick={onOpenPolicyModal}
            className="w-full text-center text-[11px] text-blue-400 hover:text-blue-300 transition block font-mono"
          >
            View policy details →
          </button>
        </div>
      </div>

      {/* 3. Case Memory Quick Access */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-teal-400" />
          <div>
            <span className="font-mono font-bold text-slate-200 block text-[11px]">
              SIMILAR CASES
            </span>
            <span className="text-[10px] text-slate-400">
              {c.similar_prior_cases?.length || 1} historical cases found (CC-0141)
            </span>
          </div>
        </div>

        <button
          onClick={onOpenCaseMemory}
          className="text-xs font-mono text-blue-400 hover:text-blue-300 transition"
        >
          View cases →
        </button>
      </div>

      {/* 4. SAR Regulatory Quick Access */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <FileBadge className="w-4 h-4 text-purple-400" />
          <div>
            <span className="font-mono font-bold text-slate-200 block text-[11px]">
              REPORTS (SAR)
            </span>
            <span className="text-[10px] text-slate-400">
              {caseData.sar?.file ? 'Mandatory FinCEN Filing (L2)' : 'No filing required'}
            </span>
          </div>
        </div>

        <button
          onClick={onOpenSAR}
          className="text-xs font-mono text-blue-400 hover:text-blue-300 transition"
        >
          View SAR →
        </button>
      </div>
    </div>
  );
}
