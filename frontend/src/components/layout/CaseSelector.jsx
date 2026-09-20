import React, { useState, useMemo } from 'react';
import { Search, Filter, AlertTriangle, UserAlert, FileSearch, CheckCircle2 } from 'lucide-react';

export default function CaseSelector({
  cases,
  selectedCaseId,
  onSelectCase,
  investigatedCases = []
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');

  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      const matchesSearch =
        c.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (c.card_id && c.card_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (c.desc && c.desc.toLowerCase().includes(searchTerm.toLowerCase()));

      const matchesType = filterType === 'all' || c.type === filterType;
      return matchesSearch && matchesType;
    });
  }, [cases, searchTerm, filterType]);

  return (
    <aside className="w-72 border-r border-slate-800 bg-slate-950/80 flex flex-col h-full overflow-hidden">
      {/* Search & Header */}
      <div className="p-3.5 border-b border-slate-800 space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-black uppercase tracking-wider text-slate-300">
            Benchmark Cases ({cases.length})
          </span>
          <span className="text-[10px] bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded font-mono text-slate-400">
            Exam Set
          </span>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Filter ID, card, txn..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-md pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition font-mono"
          />
        </div>

        {/* Filter Chips */}
        <div className="flex items-center gap-1 overflow-x-auto pb-0.5 scrollbar-none text-[10px]">
          {[
            { id: 'all', label: 'All' },
            { id: 'risk_score', label: 'Risk Model' },
            { id: 'customer_report', label: 'Dispute' },
            { id: 'analyst_request', label: 'Analyst' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterType(tab.id)}
              className={`px-2 py-0.5 rounded transition whitespace-nowrap font-semibold ${
                filterType === tab.id
                  ? 'bg-blue-600/30 text-blue-300 border border-blue-500/50'
                  : 'bg-slate-900 text-slate-400 border border-slate-800/80 hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Cases List */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-1.5 scrollbar-thin scrollbar-thumb-slate-800">
        {filteredCases.map((bCase) => {
          const isSelected = selectedCaseId === bCase.id;
          const isInvestigated = investigatedCases.includes(bCase.id);

          return (
            <button
              key={bCase.id}
              onClick={() => onSelectCase(bCase.id)}
              className={`w-full text-left p-2.5 rounded-lg text-xs transition border ${
                isSelected
                  ? 'bg-blue-950/60 border-blue-500/80 text-blue-100 shadow-sm ring-1 ring-blue-500/30'
                  : 'bg-slate-900/40 border-slate-800/60 hover:bg-slate-900 text-slate-400 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono font-bold text-slate-200">{bCase.id}</span>
                  {bCase.id === 'HHG-017' && (
                    <span className="text-[9px] bg-amber-500/20 text-amber-300 px-1 py-0.2 rounded border border-amber-500/30 font-bold">
                      DEMO
                    </span>
                  )}
                </div>

                <span
                  className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                    bCase.type === 'risk_score'
                      ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                      : bCase.type === 'customer_report'
                      ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                      : 'bg-purple-500/15 text-purple-400 border border-purple-500/30'
                  }`}
                >
                  {bCase.type === 'risk_score'
                    ? 'RISK SCORE'
                    : bCase.type === 'customer_report'
                    ? 'DISPUTE'
                    : 'ANALYST'}
                </span>
              </div>

              <p className="text-[11px] text-slate-400 line-clamp-1 leading-snug">{bCase.desc}</p>

              <div className="flex items-center justify-between mt-1.5 text-[10px] text-slate-400">
                <span className="font-mono">{bCase.card_id || 'CARD N/A'}</span>
                {isInvestigated && (
                  <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                    <CheckCircle2 className="w-3 h-3" />
                    DONE
                  </span>
                )}
              </div>
            </button>
          );
        })}

        {filteredCases.length === 0 && (
          <div className="p-4 text-center text-xs text-slate-500">
            No matching benchmark cases found.
          </div>
        )}
      </div>
    </aside>
  );
}
