import React from 'react';
import { Play, RotateCcw, Activity, ShieldAlert, CheckCircle2 } from '../common/Icons';

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
  const isFraud = c.verdict === 'fraud' || c.fraud_probability >= 0.75;
  const exposure = c.exposure_usd || 100.09;

  // Format compact identifiers
  const customerId = benchmarkMeta?.customer_id || (c.affected_txn_ids?.[0] ? `CUS-${c.affected_txn_ids[0].slice(-5)}` : 'CUS-45872');
  const cardId = benchmarkMeta?.card_id || c.connected_card_ids?.[0] || 'C04570-K1';
  const deviceProfile =
    c.connected_device_profiles?.[0]?.split('|')?.[0]?.trim() || 'DEV-9104 (Samsung SM-G892A)';

  const triggerLabel =
    benchmarkMeta?.trigger ||
    (benchmarkMeta?.type === 'risk_score'
      ? 'Risk Score Alert'
      : benchmarkMeta?.type === 'customer_report'
      ? 'Customer Report'
      : 'Analyst Request');

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm space-y-3">
      {/* Primary Top Row */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Left: Case ID, Trigger, Amount, Risk Badge, Status */}
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xl font-black font-mono text-slate-100 tracking-tight">
            {caseData.case_id}
          </span>

          <span className="text-slate-600">|</span>

          {/* Trigger Text */}
          <span className="text-xs text-slate-200 font-semibold bg-slate-800 px-2.5 py-1 rounded border border-slate-700">
            {triggerLabel}
          </span>

          {/* Flagged Amount */}
          <span className="text-base font-mono font-black text-slate-100">
            ${exposure.toFixed(2)} USD
          </span>

          {/* Risk Badge */}
          <span
            className={`text-xs px-2.5 py-1 rounded font-bold font-mono uppercase tracking-wider ${
              isFraud
                ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
            }`}
          >
            {isFraud ? 'HIGH RISK' : 'MEDIUM RISK'}
          </span>

          {/* Status Indicator */}
          <span
            className={`text-xs px-2.5 py-1 rounded font-mono font-bold flex items-center gap-1.5 ${
              isLiveStreaming
                ? 'bg-blue-500/20 text-blue-400 animate-pulse border border-blue-500/40'
                : 'bg-slate-800/90 text-slate-300 border border-slate-700'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isLiveStreaming ? 'bg-blue-400 animate-ping' : 'bg-emerald-400'
              }`}
            ></span>
            <span>{isLiveStreaming ? '● INVESTIGATING' : '● ACTIVE'}</span>
          </span>
        </div>

        {/* Right: Prominent Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={onStartInvestigation}
            disabled={isLiveStreaming}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider shadow-md transition ${
              isLiveStreaming
                ? 'bg-blue-900/60 text-blue-300 border border-blue-700/60 cursor-wait'
                : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-900/30'
            }`}
          >
            {isLiveStreaming ? (
              <>
                <Activity className="w-3.5 h-3.5 animate-spin text-blue-300" />
                <span>● Investigation Running...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Start Investigation</span>
              </>
            )}
          </button>

          {onOpenReplay && (
            <button
              onClick={onOpenReplay}
              title="Replay Investigation Trace"
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-400" />
              <span>Replay</span>
            </button>
          )}
        </div>
      </div>

      {/* Sub-row: Compact Entity Chips */}
      <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-slate-800/80 text-xs text-slate-300 font-mono">
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 uppercase text-[10px] font-bold">Customer</span>
          <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-slate-200 font-semibold">
            {customerId}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 uppercase text-[10px] font-bold">Card</span>
          <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-purple-300 font-semibold">
            {cardId}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 uppercase text-[10px] font-bold">Device</span>
          <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-amber-300 font-semibold truncate max-w-xs">
            {deviceProfile}
          </span>
        </div>

        <div className="flex items-center gap-1.5 ml-auto text-slate-400 text-[11px]">
          <span>Pattern:</span>
          <span className="text-slate-200 font-sans font-medium">
            {c.pattern ? c.pattern.replace(/_/g, ' ').toUpperCase() : 'CARD NOT PRESENT'}
          </span>
        </div>
      </div>
    </div>
  );
}
