import React, { useState } from 'react';
import { FileBadge, X, Copy, Check } from '../common/Icons';

export default function SARModal({ isOpen, onClose, sar }) {
  const [copied, setCopied] = useState(false);

  if (!isOpen || !sar) return null;

  const handleCopy = () => {
    if (sar.narrative) {
      navigator.clipboard.writeText(sar.narrative);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-lg max-w-2xl w-full p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <FileBadge className="w-5 h-5 text-purple-400" />
            <div>
              <h3 className="text-sm font-black text-slate-100 uppercase font-mono">
                FinCEN Suspicious Activity Report (SAR) Filing
              </h3>
              <p className="text-[11px] text-slate-400">
                31 CFR § 1020.320 Regulatory Filing Compliance
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

        {/* Metadata Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs font-mono">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Status</span>
            <span className={sar.file ? 'text-red-400 font-bold' : 'text-slate-400'}>
              {sar.file ? 'MANDATORY (L2)' : 'NOT REQUIRED'}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Amount</span>
            <span className="text-slate-200 font-bold">${sar.total_amount_usd.toFixed(2)} USD</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Date</span>
            <span className="text-slate-300">
              {sar.activity_dates && sar.activity_dates.length > 0
                ? sar.activity_dates.join(' to ')
                : '2016-11-12'}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Subjects</span>
            <span className="text-purple-300">{sar.subjects?.join(', ') || 'C04570'}</span>
          </div>
        </div>

        {/* Regulatory Reason */}
        <div className="space-y-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase font-mono">
            Filing Reason:
          </span>
          <p className="text-xs text-slate-300 bg-slate-950 p-2.5 rounded border border-slate-800">
            {sar.reason}
          </p>
        </div>

        {/* Official Narrative */}
        {sar.file && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase font-mono">
                Regulatory Narrative:
              </span>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 font-mono"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <div className="bg-slate-950 p-3.5 rounded border border-slate-800 text-slate-300 font-mono text-[11px] leading-relaxed max-h-[180px] overflow-y-auto whitespace-pre-wrap select-text">
              {sar.narrative}
            </div>
          </div>
        )}

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
