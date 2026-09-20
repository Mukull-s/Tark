import React, { useState } from 'react';
import { HelpCircle, AlertCircle, CheckCircle2, UserCheck, ShieldQuestion } from 'lucide-react';
import { EvidenceRequestItem } from '../../types/investigation';

export default function EvidenceRequestBanner({
  evidenceRequests,
  onProvideEvidence,
  isEvidenceProvided
}) {
  if (!evidenceRequests || evidenceRequests.length === 0) return null;

  const req = evidenceRequests[0];

  return (
    <div className="bg-amber-950/20 border border-amber-500/40 rounded-xl p-5 shadow-sm space-y-3.5 relative overflow-hidden">
      {/* Subtle indicator accent */}
      <div className="absolute -right-6 -bottom-6 w-24 h-24 bg-amber-500/5 rounded-full blur-xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between border-b border-amber-500/20 pb-2.5">
        <div className="flex items-center gap-2">
          <ShieldQuestion className="w-5 h-5 text-amber-400" />
          <h3 className="text-sm font-black uppercase tracking-wider text-amber-300">
            Additional Evidence Required (Uncertainty Loop)
          </h3>
        </div>

        <span className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded font-mono font-bold uppercase">
          {isEvidenceProvided ? 'EVIDENCE APPLIED' : 'PAUSED FOR EVIDENCE'}
        </span>
      </div>

      {/* Explanation & Request description */}
      <div className="space-y-2 text-xs">
        <p className="text-slate-300 leading-relaxed">
          The investigation agent reached a decision threshold where graph signals alone have
          residual ambiguity. Additional evidence was requested before finalizing the Next Best
          Action.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 bg-slate-950/80 p-3 rounded-lg border border-slate-800">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block font-mono">
              Requested Evidence Type:
            </span>
            <span className="text-amber-300 font-mono font-semibold text-xs">
              {req.type.toUpperCase()}
            </span>
          </div>

          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block font-mono">
              Hypothesis / Uncertainty:
            </span>
            <span className="text-slate-300 text-[11px]">
              {req.reason ||
                'Current evidence cannot distinguish between authorized customer travel and account takeover.'}
            </span>
          </div>
        </div>

        {/* Customer Validation Injected Content */}
        <div className="bg-slate-900 border border-slate-800 p-3 rounded-lg text-[11px] space-y-1">
          <span className="text-slate-400 font-bold uppercase block text-[10px]">
            Injected Customer Validation Response:
          </span>
          <p className="text-emerald-400 font-mono italic">
            "{req.assumed_response}"
          </p>
        </div>
      </div>

      {/* Action Buttons for Interactive Simulation */}
      <div className="flex items-center justify-between pt-1">
        <span className="text-[11px] text-slate-400">
          Simulate Analyst / Customer Dispatch in Demo:
        </span>

        <div className="flex items-center gap-2">
          {!isEvidenceProvided ? (
            <>
              <button
                onClick={() => onProvideEvidence('DENIAL')}
                className="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded transition shadow flex items-center gap-1.5"
              >
                <UserCheck className="w-3.5 h-3.5" />
                Inject: Customer Denied Purchases
              </button>
              <button
                onClick={() => onProvideEvidence('CONFIRM')}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded border border-slate-700 transition"
              >
                Inject: Customer Confirmed
              </button>
            </>
          ) : (
            <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold bg-emerald-950/40 border border-emerald-800/60 px-3 py-1.5 rounded">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Evidence Accepted • Risk Assessment Escalated
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
