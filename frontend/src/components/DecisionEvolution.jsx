import React from 'react';
import { ArrowRight, ShieldAlert, CheckCircle, Clock, ArrowDown } from 'lucide-react';
import { NextBestActionsRecord } from '../../types/investigation';

export default function DecisionEvolution({ nextBestActions, onApproveAction, isEvidenceProvided }) {
  if (!nextBestActions) return null;

  const { initial, final, what_changed } = nextBestActions;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      {/* Title */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Decision Evolution: Adaptive Evidence Loop
          </h3>
        </div>
        <span className="text-xs font-mono text-slate-400">
          Policy Firewall Rules R1, R2, R5, R6
        </span>
      </div>

      {/* Before / Middle / After Flow */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 1. Pre-Evidence State */}
        <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-4 space-y-3 flex flex-col justify-between">
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-blue-400" />
                1. Before Evidence
              </span>
              <span className="text-[10px] bg-blue-500/15 text-blue-400 px-2 py-0.5 rounded border border-blue-500/30 font-mono">
                Confidence 72%
              </span>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded text-[11px] space-y-1">
              <span className="text-slate-400 font-bold block text-[10px] uppercase">
                Key Uncertainty:
              </span>
              <p className="text-slate-300">
                Customer card in possession; authorization status unverified.
              </p>
            </div>

            <div className="space-y-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">
                Preliminary Proposed Actions:
              </span>
              {initial.map((item, idx) => (
                <div
                  key={idx}
                  className="bg-slate-900 border border-slate-800 p-2 rounded text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-200 font-mono text-[11px]">
                      {item.action}
                    </span>
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase font-mono ${
                        item.route === 'auto'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : item.route === 'L1'
                          ? 'bg-amber-500/20 text-amber-400'
                          : 'bg-red-500/20 text-red-400'
                      }`}
                    >
                      {item.route}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-snug">{item.reason}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 2. Evidence Transition Injected */}
        <div className="bg-blue-950/20 border border-blue-800/40 rounded-lg p-4 space-y-3 flex flex-col justify-center items-center text-center">
          <div className="w-8 h-8 rounded-full bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center">
            <ArrowRight className="w-4 h-4 hidden lg:block" />
            <ArrowDown className="w-4 h-4 block lg:hidden" />
          </div>

          <div className="space-y-1">
            <span className="text-xs font-black uppercase tracking-wider text-blue-300">
              2. Evidence Injected
            </span>
            <p className="text-[11px] text-slate-300 max-w-[220px]">
              Customer inquiry completed: Cardholder explicitly denied all charges.
            </p>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-2 rounded text-[10px] text-emerald-400 font-mono">
            Uncertainty Resolved: True Account Takeover
          </div>
        </div>

        {/* 3. Post-Evidence State */}
        <div className="bg-slate-950/70 border border-emerald-950/60 rounded-lg p-4 space-y-3 flex flex-col justify-between">
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                3. After Evidence
              </span>
              <span className="text-[10px] bg-emerald-500/15 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/30 font-mono">
                Confidence 86%
              </span>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded text-[11px] space-y-1">
              <span className="text-emerald-400 font-bold block text-[10px] uppercase">
                Definitive Finding:
              </span>
              <p className="text-slate-200">
                Stolen card testing sequence confirmed. Cross-device syndicate connection verified.
              </p>
            </div>

            <div className="space-y-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">
                Final Formulated Actions:
              </span>
              {final.map((item, idx) => (
                <div
                  key={idx}
                  className="bg-slate-900 border border-slate-800 p-2 rounded text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-200 font-mono text-[11px]">
                      {item.action}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase font-mono ${
                          item.route === 'auto'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : item.route === 'L1'
                            ? 'bg-amber-500/20 text-amber-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}
                      >
                        {item.route}
                      </span>
                      {item.route !== 'auto' && (
                        <button
                          onClick={() => onApproveAction && onApproveAction(item.action, item.route)}
                          className="text-[10px] bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-2 py-0.5 rounded transition shadow"
                        >
                          Review
                        </button>
                      )}
                    </div>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-snug">{item.reason}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* What Changed Banner */}
      <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-xs text-amber-200 flex items-start gap-2">
        <span className="font-bold text-amber-400 font-mono shrink-0 uppercase tracking-wider">
          WHAT CHANGED:
        </span>
        <span className="leading-relaxed">{what_changed}</span>
      </div>
    </div>
  );
}
