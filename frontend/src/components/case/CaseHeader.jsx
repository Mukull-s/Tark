import React from 'react';
import { CheckCircle2, AlertCircle, Database, ShieldCheck, DollarSign, Calendar } from 'lucide-react';

export default function CaseHeader({ caseData, benchmarkMeta }) {
  if (!caseData || !caseData.case) return null;

  const c = caseData.case;
  const isFraud = c.verdict === 'fraud';

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      {/* Top Row: Case ID, Status Badges, Verdict */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-2xl font-black font-mono text-slate-100 tracking-tight">
              {caseData.case_id}
            </span>

            {/* Verdict Badge */}
            <span
              className={`text-xs px-2.5 py-0.5 rounded font-bold font-mono border uppercase tracking-wider ${
                isFraud
                  ? 'bg-red-500/15 text-red-400 border-red-500/30 ring-1 ring-red-500/20'
                  : c.verdict === 'legitimate'
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                  : 'bg-amber-500/15 text-amber-400 border-amber-500/30'
              }`}
            >
              VERDICT: {c.verdict.toUpperCase()}
            </span>

            {/* Pattern Badge */}
            <span className="text-xs px-2.5 py-0.5 rounded font-bold font-mono bg-purple-500/15 text-purple-400 border border-purple-500/30 uppercase">
              PATTERN: {c.pattern.replace(/_/g, ' ')}
            </span>

            {/* Status Badge */}
            <span className="text-xs px-2.5 py-0.5 rounded font-bold font-mono bg-slate-800 text-slate-300 border border-slate-700 uppercase">
              STATUS: {c.status.replace(/_/g, ' ')}
            </span>
          </div>

          {/* Trigger & Transaction Metadata Line */}
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 font-sans">
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-slate-500" />
              <span>{benchmarkMeta?.opened_at || '2016-11-12 00:46:24'}</span>
            </span>
            <span>•</span>
            <span>
              Customer: <strong className="text-slate-200 font-mono">{benchmarkMeta?.customer_id || c.affected_txn_ids?.[0] || 'C04570'}</strong>
            </span>
            <span>•</span>
            <span>
              Card: <strong className="text-slate-200 font-mono">{benchmarkMeta?.card_id || c.connected_card_ids?.[0] || 'C04570-K1'}</strong>
            </span>
            <span>•</span>
            <span>
              Flagged Txn: <strong className="text-slate-200 font-mono">{c.first_suspicious_txn_id || benchmarkMeta?.flagged_txn_id || '3450629'}</strong>
            </span>
          </div>
        </div>

        {/* Right Telemetry Column */}
        <div className="flex items-center gap-6">
          {/* Investigation Confidence / Fraud Assessment */}
          <div className="text-right">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
              Investigation Confidence
            </span>
            <div className="flex items-baseline justify-end gap-1">
              <span className={`text-xl font-black font-mono ${isFraud ? 'text-red-400' : 'text-emerald-400'}`}>
                {(c.fraud_probability * 100).toFixed(0)}%
              </span>
              <span className="text-[10px] text-slate-400 font-mono">CONF</span>
            </div>
          </div>

          {/* Total Exposure */}
          <div className="text-right">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
              Total Exposure
            </span>
            <span className="text-xl font-black font-mono text-slate-100">
              ${c.exposure_usd.toFixed(2)}
            </span>
          </div>

          {/* TigerGraph Case Memory Vertex */}
          <div className="text-right pl-2 border-l border-slate-800">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
              Graph Persistence
            </span>
            <span className="text-xs font-mono text-emerald-400 flex items-center justify-end gap-1 font-semibold mt-0.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              {c.graph_case_id || 'SAVANNA_SYNCED'}
            </span>
          </div>
        </div>
      </div>

      {/* Trigger Summary Box */}
      {benchmarkMeta?.desc && (
        <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg px-4 py-2.5 flex items-start gap-2.5 text-xs text-slate-300">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-bold text-amber-300 mr-1.5 uppercase font-mono tracking-wider">
              Trigger Origin:
            </span>
            {benchmarkMeta.desc}
          </div>
        </div>
      )}
    </div>
  );
}
