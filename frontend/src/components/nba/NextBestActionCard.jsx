import React from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Lock,
  ArrowRight,
  ShieldCheck,
  FileBadge
} from 'lucide-react';
import { ActionItem } from '../../types/investigation';

export default function NextBestActionCard({
  actions,
  approvedActions = [],
  onApproveAction,
  onRejectAction,
  onRequestEvidence
}) {
  if (!actions || actions.length === 0) return null;

  // Find primary non-auto action (or first final action)
  const primaryAction =
    actions.find((a) => a.route !== 'auto' && !approvedActions.includes(a.action)) ||
    actions[0];

  const isApproved = approvedActions.includes(primaryAction.action);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-amber-400" />
          <div>
            <h3 className="text-sm font-black uppercase tracking-wider text-slate-100">
              Next Best Action Recommendation
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">
              Policy Firewall Deterministic Enforcement
            </span>
          </div>
        </div>

        {/* Route Badge */}
        <span
          className={`text-xs px-2.5 py-1 rounded-md font-bold font-mono uppercase tracking-wider flex items-center gap-1.5 ${
            primaryAction.route === 'auto'
              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
              : primaryAction.route === 'L1'
              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40 ring-1 ring-amber-500/20'
              : 'bg-red-500/20 text-red-400 border border-red-500/40 ring-1 ring-red-500/20'
          }`}
        >
          <Lock className="w-3.5 h-3.5" />
          {primaryAction.route === 'auto'
            ? 'AUTO EXECUTION'
            : primaryAction.route === 'L1'
            ? 'HUMAN APPROVAL REQUIRED — L1'
            : 'HUMAN APPROVAL REQUIRED — L2'}
        </span>
      </div>

      {/* Primary Recommended Action Card */}
      <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block font-mono">
              Recommended Bank Intervention
            </span>
            <h2 className="text-xl font-black font-mono text-slate-100 tracking-tight">
              {primaryAction.action}
            </h2>
          </div>

          {isApproved ? (
            <span className="text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-3 py-1 rounded-md font-bold flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              EXECUTED BY ANALYST
            </span>
          ) : (
            <span className="text-xs text-amber-400 font-mono font-bold bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
              PENDING SIGN-OFF
            </span>
          )}
        </div>

        {/* Policy Justification */}
        <div className="bg-slate-900 border border-slate-800 p-3 rounded text-xs text-slate-300 leading-relaxed">
          <span className="font-bold text-slate-200 font-mono block mb-0.5 uppercase text-[10px]">
            Policy Firewall Justification:
          </span>
          {primaryAction.reason}
        </div>

        {/* Supporting Grounded Evidence Checkmarks */}
        <div className="space-y-1.5 pt-1">
          <span className="text-[10px] uppercase font-bold text-slate-400 block font-mono">
            Supporting Evidence Rationale:
          </span>
          <div className="space-y-1">
            {(primaryAction.supporting_evidence || [
              'Customer explicitly denied transaction via validation loop',
              'Multiple rapid online authorizations under $3 (card testing pattern)',
              'Shared device hardware profile links to compromised card C00877-K1',
              'Historical pattern matched closed confirmed fraud case CC-0141'
            ]).map((ev, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs text-slate-200">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <span>{ev}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Action Decision Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        <div className="text-[11px] text-slate-400">
          Route: <strong className="text-slate-200 font-mono">{primaryAction.route}</strong> •
          Analyst Decision Required
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onRejectAction && onRejectAction(primaryAction.action)}
            className="px-3 py-1.5 text-xs text-slate-300 hover:text-red-400 border border-slate-800 hover:border-red-500/40 rounded font-semibold transition flex items-center gap-1"
          >
            <XCircle className="w-3.5 h-3.5" />
            Override / Deny
          </button>

          <button
            onClick={() => onRequestEvidence && onRequestEvidence()}
            className="px-3 py-1.5 text-xs text-slate-300 hover:text-amber-400 border border-slate-800 hover:border-amber-500/40 rounded font-semibold transition flex items-center gap-1"
          >
            <HelpCircle className="w-3.5 h-3.5" />
            Request More Evidence
          </button>

          <button
            onClick={() =>
              onApproveAction &&
              onApproveAction(primaryAction.action, primaryAction.route, primaryAction.reason)
            }
            disabled={isApproved}
            className={`px-4 py-1.5 text-xs rounded font-bold transition flex items-center gap-1.5 shadow ${
              isApproved
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-amber-500 hover:bg-amber-400 text-slate-950 ring-1 ring-amber-400/40'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            {isApproved ? 'Action Executed' : 'Approve & Execute'}
          </button>
        </div>
      </div>
    </div>
  );
}
