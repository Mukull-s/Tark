import React, { useState } from 'react';
import { FileBadge, Copy, Check, ExternalLink, ShieldCheck, DollarSign } from 'lucide-react';
import { SARRecord } from '../../types/investigation';

export default function SARViewer({ sar, pattern }) {
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);

  if (!sar) return null;

  const handleCopy = () => {
    if (sar.narrative) {
      navigator.clipboard.writeText(sar.narrative);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <FileBadge className="w-4 h-4 text-purple-400" />
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              FinCEN Suspicious Activity Report (SAR) Filing
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">
              31 CFR § 1020.320 Regulatory Compliance
            </span>
          </div>
        </div>

        {/* Filing Requirement Badge */}
        <span
          className={`text-xs px-2.5 py-0.5 rounded font-bold font-mono uppercase tracking-wider ${
            sar.file
              ? 'bg-red-500/20 text-red-400 border border-red-500/30 ring-1 ring-red-500/20'
              : 'bg-slate-800 text-slate-400 border border-slate-700'
          }`}
        >
          {sar.file ? 'MANDATORY FILING (L2 APPROVAL)' : 'NO FILING REQUIRED'}
        </span>
      </div>

      {/* Metadata Overview Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-slate-950/70 p-3 rounded-lg border border-slate-800 text-xs">
        <div>
          <span className="text-slate-400 block text-[10px] uppercase font-semibold font-mono">
            Regulatory Reason
          </span>
          <span className="text-slate-200 font-medium leading-snug line-clamp-2" title={sar.reason}>
            {sar.reason}
          </span>
        </div>

        <div>
          <span className="text-slate-400 block text-[10px] uppercase font-semibold font-mono">
            Total Suspicious Amount
          </span>
          <span className="text-red-400 font-bold font-mono text-sm">
            ${sar.total_amount_usd.toFixed(2)} USD
          </span>
        </div>

        <div>
          <span className="text-slate-400 block text-[10px] uppercase font-semibold font-mono">
            Activity Dates
          </span>
          <span className="text-slate-300 font-mono">
            {sar.activity_dates && sar.activity_dates.length > 0
              ? sar.activity_dates.join(' to ')
              : '2016-11-12'}
          </span>
        </div>

        <div>
          <span className="text-slate-400 block text-[10px] uppercase font-semibold font-mono">
            Identified Subjects
          </span>
          <div className="flex flex-wrap gap-1 mt-0.5">
            {sar.subjects &&
              sar.subjects.map((s, idx) => (
                <span
                  key={idx}
                  className="bg-purple-950 text-purple-300 px-1.5 py-0.2 rounded text-[10px] font-mono border border-purple-800/40"
                >
                  {s}
                </span>
              ))}
          </div>
        </div>
      </div>

      {/* Regulatory Narrative */}
      {sar.file && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider font-mono">
              Official FinCEN Narrative:
            </span>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 px-2 py-0.5 rounded transition"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Copied!' : 'Copy Narrative'}</span>
              </button>

              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-[10px] text-blue-400 hover:text-blue-300"
              >
                {isExpanded ? 'Collapse' : 'Expand'}
              </button>
            </div>
          </div>

          {isExpanded && (
            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-slate-300 leading-relaxed font-mono text-[11px] shadow-inner whitespace-pre-wrap select-text">
              {sar.narrative}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
