import React, { useState } from 'react';
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  Database,
  Terminal,
  ChevronDown,
  ChevronUp,
  UserCheck,
  ShieldAlert,
  ArrowRight
} from './common/Icons';

export default function AgentTimeline({
  steps = [],
  activeStepIndex = 0,
  onStepChange,
  isLiveStreaming = false
}) {
  const [expandedIndices, setExpandedIndices] = useState(new Set());

  const toggleExpand = (idx, e) => {
    e.stopPropagation();
    const updated = new Set(expandedIndices);
    if (updated.has(idx)) {
      updated.delete(idx);
    } else {
      updated.add(idx);
    }
    setExpandedIndices(updated);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm flex flex-col h-full overflow-hidden text-xs">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3 shrink-0">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-blue-400" />
          <h3 className="text-xs font-black uppercase tracking-wider text-slate-100 font-mono">
            Investigation Timeline
          </h3>
        </div>
        {isLiveStreaming ? (
          <span className="text-[10px] font-mono text-blue-400 animate-pulse font-bold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
            STREAMING
          </span>
        ) : (
          <span className="text-[10px] font-mono text-slate-400">
            {steps.length} EVENTS
          </span>
        )}
      </div>

      {/* Events List */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 relative before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
        {steps.map((step, idx) => {
          const isCurrent = idx === activeStepIndex;
          const isExpanded = expandedIndices.has(idx) || isCurrent;
          const isPast = idx <= activeStepIndex;

          const isUncertainty = step.status === 'WAITING_FOR_EVIDENCE' || (step.title && step.title.toLowerCase().includes('uncertainty'));
          const isEvidenceReceived = step.title && step.title.toLowerCase().includes('evidence received');
          const isNBA = step.title && step.title.toLowerCase().includes('next best action');

          return (
            <div
              key={idx}
              onClick={() => onStepChange && onStepChange(idx)}
              className={`relative pl-8 cursor-pointer group transition select-none ${
                isCurrent
                  ? 'opacity-100'
                  : isPast
                  ? 'opacity-90 hover:opacity-100'
                  : 'opacity-40'
              }`}
            >
              {/* Event Marker Node */}
              <div
                className={`absolute left-1.5 top-1 w-4 h-4 rounded-full flex items-center justify-center -translate-x-1/2 border transition ${
                  isCurrent
                    ? 'bg-blue-600 border-blue-400 text-white shadow-sm ring-2 ring-blue-500/20'
                    : isUncertainty
                    ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                    : isEvidenceReceived
                    ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                    : isNBA
                    ? 'bg-purple-500/20 border-purple-500 text-purple-400'
                    : isPast
                    ? 'bg-slate-800 border-slate-600 text-slate-300'
                    : 'bg-slate-900 border-slate-800 text-slate-600'
                }`}
              >
                {isUncertainty ? (
                  <AlertTriangle className="w-2.5 h-2.5" />
                ) : isNBA ? (
                  <ArrowRight className="w-2.5 h-2.5" />
                ) : (
                  <CheckCircle2 className="w-2.5 h-2.5" />
                )}
              </div>

              {/* Event Card */}
              <div
                className={`p-2.5 rounded-lg border transition ${
                  isCurrent
                    ? 'bg-slate-950 border-blue-500/50 shadow-sm'
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                }`}
              >
                {/* Timestamp & Status Icon */}
                <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 mb-0.5">
                  <span className="font-semibold text-slate-400">
                    {step.timestamp ? step.timestamp.split(' ')[1] || step.timestamp : `19:42:${11 + idx * 3}`}
                  </span>
                  <span
                    className={`uppercase font-bold text-[9px] px-1.5 py-0.2 rounded ${
                      isUncertainty
                        ? 'bg-amber-500/20 text-amber-300'
                        : isEvidenceReceived
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : isNBA
                        ? 'bg-purple-500/20 text-purple-300'
                        : isCurrent
                        ? 'bg-blue-500/20 text-blue-300'
                        : 'text-slate-400'
                    }`}
                  >
                    {step.status || 'COMPLETED'}
                  </span>
                </div>

                {/* Event Title */}
                <div className="flex items-center justify-between">
                  <h4
                    className={`font-mono font-bold uppercase text-[11px] tracking-tight ${
                      isUncertainty
                        ? 'text-amber-300'
                        : isEvidenceReceived
                        ? 'text-emerald-300'
                        : isNBA
                        ? 'text-purple-300'
                        : isCurrent
                        ? 'text-blue-300'
                        : 'text-slate-200'
                    }`}
                  >
                    {step.title}
                  </h4>
                  {step.metadata && (
                    <button
                      onClick={(e) => toggleExpand(idx, e)}
                      className="text-slate-400 hover:text-slate-200 p-0.5"
                    >
                      {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>
                  )}
                </div>

                {/* Description */}
                <p className="text-[11px] text-slate-300 mt-1 leading-snug">
                  {step.description}
                </p>

                {/* Expandable Technical Metadata */}
                {isExpanded && step.metadata && (
                  <div className="mt-2 pt-2 border-t border-slate-800/80 text-[10px] font-mono text-slate-400 space-y-1 bg-slate-900/50 p-2 rounded">
                    {Object.entries(step.metadata).map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-slate-400">{k}:</span>
                        <span className="text-slate-300 font-semibold">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
