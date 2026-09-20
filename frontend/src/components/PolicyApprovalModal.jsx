import React, { useState } from 'react';
import { ShieldAlert, Check, X, Lock, DollarSign, UserCheck, AlertTriangle } from './common/Icons';

export default function PolicyApprovalModal({
  actionItem,
  caseId,
  exposureUsd = 268.43,
  onApprove,
  onReject,
  onClose
}) {
  const [analystNotes, setAnalystNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!actionItem) return null;

  const handleExecute = async () => {
    setIsSubmitting(true);
    try {
      await onApprove(actionItem.action, actionItem.route, analystNotes);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  const isL2 = actionItem.route === 'L2';

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in duration-150">
        {/* Modal Header */}
        <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
          <div
            className={`p-2.5 rounded-lg ${
              isL2
                ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
            }`}
          >
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-black text-slate-100 uppercase tracking-wider">
              Policy Firewall Approval Gate
            </h3>
            <span
              className={`text-xs font-mono font-bold ${
                isL2 ? 'text-red-400' : 'text-amber-400'
              }`}
            >
              Action Requires {actionItem.route} Sign-Off ({isL2 ? 'Fraud Manager' : 'Team Lead'})
            </span>
          </div>
        </div>

        {/* Operational Context Box */}
        <div className="space-y-3 text-xs text-slate-300">
          <div className="grid grid-cols-2 gap-2 bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono">
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Case ID</span>
              <span className="text-slate-100 font-bold">{caseId}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">
                Intervention Exposure
              </span>
              <span className="text-red-400 font-bold">${exposureUsd.toFixed(2)} USD</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">
                Proposed Action
              </span>
              <span className="text-amber-300 font-bold">{actionItem.action}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">
                Required Role
              </span>
              <span className="text-slate-200 font-bold">{actionItem.route} Approved Operator</span>
            </div>
          </div>

          {/* Policy Justification */}
          <div>
            <span className="text-slate-400 font-semibold block text-[10px] uppercase font-mono mb-1">
              Policy Firewall Justification & Rule Reference:
            </span>
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-slate-300 text-[11px] leading-relaxed">
              {actionItem.reason}
            </div>
          </div>

          {/* Analyst Operational Sign-Off Notes */}
          <div>
            <label className="text-slate-400 font-semibold block text-[10px] uppercase font-mono mb-1">
              Analyst Verification Notes (Recorded to TigerGraph Audit Trail):
            </label>
            <textarea
              value={analystNotes}
              onChange={(e) => setAnalystNotes(e.target.value)}
              placeholder="e.g., Reviewed card testing frequency and confirmed customer phone denial..."
              rows={2}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-500 transition font-sans"
            />
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-800">
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="px-3.5 py-1.5 text-xs text-slate-400 hover:text-slate-200 border border-slate-800 hover:border-slate-700 rounded transition"
          >
            Cancel
          </button>

          <button
            onClick={() => {
              onReject && onReject(actionItem.action);
              onClose();
            }}
            disabled={isSubmitting}
            className="px-3.5 py-1.5 text-xs bg-red-500/15 hover:bg-red-500/25 text-red-400 border border-red-500/30 rounded font-semibold flex items-center gap-1.5 transition"
          >
            <X className="w-3.5 h-3.5" />
            Override / Deny Action
          </button>

          <button
            onClick={handleExecute}
            disabled={isSubmitting}
            className="px-4 py-1.5 text-xs bg-amber-500 hover:bg-amber-400 text-slate-950 rounded font-bold flex items-center gap-1.5 shadow transition"
          >
            <Check className="w-3.5 h-3.5" />
            {isSubmitting ? 'Executing...' : 'Approve & Execute'}
          </button>
        </div>
      </div>
    </div>
  );
}
