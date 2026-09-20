import React from 'react';
import { History, CheckCircle2, FileText, ArrowUpRight, ShieldCheck, Database } from 'lucide-react';
import { CaseMemoryItem } from '../../types/investigation';

export default function CaseMemoryCard({ cases, graphCaseId }) {
  if (!cases || cases.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-2.5">
          <History className="w-4 h-4 text-teal-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Case Memory: Similar Historical Investigations
          </h3>
        </div>
        <p className="text-xs text-slate-400">
          No prior similar cases retrieved for this pattern signature.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-teal-400" />
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              TigerGraph Case Memory: Similar Closed Cases ({cases.length})
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">
              GraphRAG retrieval over 5,565 historical investigations
            </span>
          </div>
        </div>

        {/* Persistence Confirmation */}
        <div className="flex items-center gap-1.5 bg-slate-950 border border-emerald-900/60 text-emerald-400 px-2.5 py-1 rounded text-xs font-mono">
          <Database className="w-3.5 h-3.5 text-emerald-400" />
          <span>Case Vertex: {graphCaseId || 'SAVANNA_SYNCED'}</span>
        </div>
      </div>

      {/* List of Similar Closed Cases */}
      <div className="space-y-3">
        {cases.map((c, idx) => (
          <div
            key={idx}
            className="bg-slate-950/80 border border-slate-800 hover:border-slate-700 rounded-lg p-3.5 space-y-2 text-xs transition"
          >
            {/* Top row: Case ID, similarity badge, outcome */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-slate-100 text-sm">{c.case_id}</span>
                <span
                  className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase font-mono ${
                    c.similarity === 'HIGH'
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}
                >
                  SIMILARITY: {c.similarity}
                </span>
                <span className="text-[9px] bg-slate-900 text-slate-400 px-1.5 py-0.2 rounded font-mono border border-slate-800 uppercase">
                  {c.pattern.replace(/_/g, ' ')}
                </span>
              </div>

              <span
                className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase font-mono ${
                  c.outcome === 'confirmed_fraud'
                    ? 'bg-red-500/15 text-red-400'
                    : 'bg-emerald-500/15 text-emerald-400'
                }`}
              >
                {c.outcome.replace(/_/g, ' ')}
              </span>
            </div>

            {/* Analyst Notes */}
            <p className="text-slate-300 leading-relaxed text-[11px] font-sans">
              <strong className="text-slate-400 mr-1 font-mono text-[10px] uppercase">
                Historical Notes:
              </strong>
              {c.analyst_notes}
            </p>

            {/* Actions Taken & Exposure */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-800/80 text-[11px]">
              <div className="flex items-center gap-1">
                <span className="text-slate-500 text-[10px] uppercase font-mono">
                  Actions Taken:
                </span>
                <div className="flex flex-wrap gap-1">
                  {c.actions_taken &&
                    c.actions_taken.map((act, actIdx) => (
                      <span
                        key={actIdx}
                        className="bg-slate-900 text-slate-300 px-1.5 py-0.2 rounded text-[10px] font-mono border border-slate-800"
                      >
                        {act}
                      </span>
                    ))}
                </div>
              </div>

              <div className="font-mono text-slate-400">
                Exposure: <strong className="text-slate-200">${c.exposure_usd.toFixed(2)}</strong>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
