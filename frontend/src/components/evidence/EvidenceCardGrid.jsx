import React, { useState } from 'react';
import {
  FileText,
  Database,
  UserCheck,
  Globe,
  Smartphone,
  CreditCard,
  History,
  Layers,
  Tag
} from 'lucide-react';
import { EvidenceItem } from '../../types/investigation';

export default function EvidenceCardGrid({ evidence }) {
  const [selectedCategory, setSelectedCategory] = useState('ALL');

  if (!evidence || evidence.length === 0) return null;

  // Derive categories if not explicitly set
  const categorized = evidence.map((item) => {
    let cat = item.category;
    if (!cat) {
      if (item.source === 'customer') cat = 'CUSTOMER';
      else if (item.ref.includes('device')) cat = 'DEVICE';
      else if (item.ref.includes('card_window')) cat = 'TRANSACTION';
      else if (item.ref.includes('prior_cases')) cat = 'HISTORICAL CASE';
      else cat = 'NETWORK';
    }
    return { ...item, category: cat };
  });

  const categories = ['ALL', 'TRANSACTION', 'DEVICE', 'CUSTOMER', 'NETWORK', 'HISTORICAL CASE'];

  const filtered =
    selectedCategory === 'ALL'
      ? categorized
      : categorized.filter((item) => item.category === selectedCategory);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      {/* Section Header & Category Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Grounded Evidence Registry ({evidence.length})
          </h3>
        </div>

        {/* Category Pills */}
        <div className="flex flex-wrap items-center gap-1 text-[10px]">
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setSelectedCategory(c)}
              className={`px-2 py-0.5 rounded font-mono font-semibold transition ${
                selectedCategory === c
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-slate-200'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Grid of Structured Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {filtered.map((item, idx) => (
          <div
            key={idx}
            className="bg-slate-950/70 border border-slate-800/80 hover:border-slate-700/80 rounded-lg p-3.5 space-y-2 text-xs transition"
          >
            {/* Card Header: Category, Source & Ref */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] bg-slate-900 text-slate-300 font-mono font-bold px-1.5 py-0.5 rounded border border-slate-800 uppercase">
                  {item.category}
                </span>

                <span
                  className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase flex items-center gap-1 ${
                    item.source === 'graph'
                      ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                      : item.source === 'customer'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                  }`}
                >
                  {item.source === 'graph' && <Database className="w-2.5 h-2.5" />}
                  {item.source === 'customer' && <UserCheck className="w-2.5 h-2.5" />}
                  {item.source === 'document' && <FileText className="w-2.5 h-2.5" />}
                  {item.source}
                </span>
              </div>

              <span className="text-[10px] font-mono text-slate-500 truncate max-w-[130px]" title={item.ref}>
                {item.ref}
              </span>
            </div>

            {/* Evidence Claim / What was discovered */}
            <p className="text-slate-200 leading-relaxed font-sans text-[11px]">{item.claim}</p>

            {/* Why It Matters / Analytical Interpretation */}
            {item.why_it_matters && (
              <div className="bg-slate-900/80 border border-slate-800/80 rounded px-2.5 py-1.5 text-[10px] text-amber-200/90 leading-snug">
                <span className="font-bold text-amber-400 mr-1 uppercase font-mono">Significance:</span>
                {item.why_it_matters}
              </div>
            )}

            {/* Footer: Entity IDs & Timestamp */}
            <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-[10px]">
              <div className="flex flex-wrap items-center gap-1">
                {item.entity_ids &&
                  item.entity_ids.map((id, idIdx) => (
                    <span
                      key={idIdx}
                      className="bg-slate-900 text-slate-400 px-1.5 py-0.2 rounded font-mono border border-slate-800"
                    >
                      {id}
                    </span>
                  ))}
              </div>

              {item.timestamp && (
                <span className="text-slate-500 font-mono text-[9px]">{item.timestamp}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
