import { History, X, Database, CheckCircle2 } from '../common/Icons';

export default function CaseMemoryModal({ isOpen, onClose, cases = [], graphCaseId }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-lg max-w-2xl w-full p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-teal-400" />
            <div>
              <h3 className="text-sm font-black text-slate-100 uppercase font-mono">
                TigerGraph Case Memory: Similar Closed Cases
              </h3>
              <p className="text-[11px] text-slate-400">
                GraphRAG retrieval across 5,565 historical investigations
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Persistence Status */}
        <div className="bg-slate-950 p-2.5 rounded border border-slate-800 flex items-center justify-between text-xs font-mono">
          <span className="text-slate-400">Active Investigation Vertex:</span>
          <span className="text-emerald-400 flex items-center gap-1 font-semibold">
            <Database className="w-3.5 h-3.5" />
            {graphCaseId || 'CASE-2016-1187 (Savanna Synced)'}
          </span>
        </div>

        {/* Cases List */}
        <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
          {cases.map((c, idx) => (
            <div
              key={idx}
              className="bg-slate-950/80 border border-slate-800 rounded-lg p-3.5 space-y-2 text-xs"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-slate-100 text-sm">{c.case_id}</span>
                  <span
                    className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold uppercase ${
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

              <p className="text-slate-300 leading-relaxed text-[11px]">{c.analyst_notes}</p>

              <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px] font-mono text-slate-400">
                <div className="flex items-center gap-1">
                  <span>Actions Taken:</span>
                  <span className="text-slate-200">
                    {c.actions_taken ? c.actions_taken.join(', ') : 'BLOCK_CARD, FILE_REPORT'}
                  </span>
                </div>
                <div>
                  Exposure: <strong className="text-slate-200">${c.exposure_usd.toFixed(2)}</strong>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-end pt-2 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
