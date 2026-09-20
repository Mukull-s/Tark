import React from 'react';
import { Play, RotateCcw, Activity } from '../common/Icons';

export default function CaseHeaderCompact({
  caseData,
  benchmarkMeta,
  isLiveStreaming,
  onStartInvestigation,
  onResetInvestigation,
  onOpenReplay
}) {
  if (!caseData || !caseData.case) return null;

  const c = caseData.case;
  const isFraud = c.verdict === 'fraud';

  // Format compact identifiers
  const customerId = benchmarkMeta?.customer_id || c.affected_txn_ids?.[0] || 'C04570';
  const cardId = benchmarkMeta?.card_id || c.connected_card_ids?.[0] || 'C04570-K1';
  const deviceProfile =
    c.connected_device_profiles?.[0]?.split('|')?.[0]?.trim() || 'SAMSUNG SM-G892A';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3.5 shadow-sm space-y-2">
      {/* Primary Top Row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left: Case ID, Trigger, Amount, Risk Badge */}
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="text-lg font-black font-mono text-slate-100 tracking-tight">
            {caseData.case_id}
          </span>

          <span className="text-slate-600">|</span>

          {/* Trigger Text */}
          <span className="text-xs text-slate-300 font-medium">
            {benchmarkMeta?.type === 'risk_score'
              ? 'Model Risk Alert'
              : benchmarkMeta?.type === 'customer_report'
              ? 'Customer Report / Dispute'
              : 'Analyst Inquiry'}
          </span>

          <span className="text-slate-600">|</span>

          {/* Flagged Amount */}
          <span className="text-xs font-mono font-bold text-slate-100">
            ${c.exposure_usd.toFixed(2)} USD
          </span>

          <span className="text-slate-600">|</span>

          {/* Risk Badge */}
          <span
            className={`text-[10px] px-2 py-0.5 rounded font-bold font-mono uppercase tracking-wider ${
              isFraud
                ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
            }`}
          >
            {isFraud ? 'HIGH RISK' : 'LOW RISK'}
          </span>

          {/* Status Indicator */}
          <span
            className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold flex items-center gap-1.5 ${
              isLiveStreaming
                ? 'bg-blue-500/20 text-blue-400 animate-pulse border border-blue-500/30'
                : c.status === 'closed_fraud'
                ? 'bg-slate-800 text-slate-300 border border-slate-700'
                : 'bg-amber-500/15 text-amber-300'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isLiveStreaming ? 'bg-blue-400' : 'bg-emerald-400'
              }`}
            />
            {isLiveStreaming ? 'INVESTIGATING' : c.status.replace(/_/g, ' ').toUpperCase()}
          </span>
        </div>

        {/* Right: Operational Investigation Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={onStartInvestigation}
            disabled={isLiveStreaming}
            className={`px-3 py-1 rounded text-xs font-bold font-mono transition flex items-center gap-1.5 ${
              isLiveStreaming
                ? 'bg-slate-800 text-slate-400 cursor-not-allowed border border-slate-700'
                : 'bg-blue-600 hover:bg-blue-500 text-slate-950 shadow-sm'
            }`}
          >
            <Play className="w-3 h-3" />
            <span>{isLiveStreaming ? 'Streaming...' : 'Investigate Case'}</span>
          </button>

          <button
            onClick={onOpenReplay}
            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded text-xs font-mono text-slate-300 transition flex items-center gap-1"
          >
            <Activity className="w-3 h-3 text-slate-400" />
            <span>Replay</span>
          </button>

          <button
            onClick={onResetInvestigation}
            title="Reset Case View"
            className="p-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded text-slate-400 hover:text-slate-200 transition"
          >
            <RotateCcw className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Second Line: Compact entity references */}
      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 font-mono pt-1 border-t border-slate-800/60">
        <span>
          Customer: <strong className="text-slate-200">{customerId}</strong>
        </span>
        <span className="text-slate-600">•</span>
        <span>
          Card: <strong className="text-slate-200">{cardId}</strong>
        </span>
        <span className="text-slate-600">•</span>
        <span>
          Device: <strong className="text-slate-200">{deviceProfile}</strong>
        </span>
        <span className="text-slate-600">•</span>
        <span>
          Flagged Txn: <strong className="text-slate-200">{c.first_suspicious_txn_id}</strong>
        </span>
      </div>
    </div>
  );
}
