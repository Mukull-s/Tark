import React, { useState } from 'react';
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  Database,
  Terminal,
  ChevronDown,
  ChevronUp,
  Cpu,
  UserCheck,
  ShieldAlert
} from 'lucide-react';
import { InvestigationStep } from '../../types/investigation';

export default function AgentTimeline({ steps, activeStepIndex, stopReason, summary }) {
  const [expandedSteps, setExpandedSteps] = useState({});

  const toggleExpand = (idx) => {
    setExpandedSteps((prev) => ({
      ...prev,
      [idx]: !prev[idx]
    }));
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Agent Reasoning & Investigation Timeline
          </h3>
        </div>
        <span className="text-xs text-emerald-400 font-mono font-semibold">
          Live Agent State Machine
        </span>
      </div>

      {/* Case Investigation Narrative Summary */}
      {summary && (
        <div className="bg-slate-950/70 border border-slate-800 p-3.5 rounded-lg text-xs leading-relaxed text-slate-300">
          <span className="font-bold text-slate-100 block mb-1">
            Investigation Narrative Summary:
          </span>
          {summary}
        </div>
      )}

      {/* Timeline Steps */}
      <div className="space-y-3 relative before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
        {steps &&
          steps.map((step, idx) => {
            const isCurrent = idx === activeStepIndex;
            const isExpanded = !!expandedSteps[idx] || isCurrent;

            // Status styling
            const statusColor =
              step.status === 'COMPLETED'
                ? 'text-emerald-400 bg-emerald-950/60 border-emerald-500/40'
                : step.status === 'WAITING FOR EVIDENCE'
                ? 'text-amber-400 bg-amber-950/60 border-amber-500/40 animate-pulse'
                : step.status === 'ACTIVE'
                ? 'text-blue-400 bg-blue-950/60 border-blue-500/40'
                : step.status === 'FAILED'
                ? 'text-red-400 bg-red-950/60 border-red-500/40'
                : 'text-slate-500 bg-slate-900 border-slate-800';

            const iconBadge =
              step.status === 'COMPLETED' ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              ) : step.status === 'WAITING FOR EVIDENCE' ? (
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              ) : step.status === 'ACTIVE' ? (
                <Cpu className="w-3.5 h-3.5 text-blue-400" />
              ) : (
                <Clock className="w-3.5 h-3.5 text-slate-500" />
              );

            return (
              <div
                key={idx}
                className={`relative pl-8 transition-all ${
                  isCurrent ? 'opacity-100' : 'opacity-85 hover:opacity-100'
                }`}
              >
                {/* Node icon in vertical line */}
                <div
                  className={`absolute left-1.5 top-2.5 -translate-x-1/2 w-4 h-4 rounded-full flex items-center justify-center border z-10 ${statusColor}`}
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-current" />
                </div>

                {/* Step Card */}
                <div
                  className={`border rounded-lg p-3 text-xs transition ${
                    isCurrent
                      ? 'bg-slate-950 border-blue-500/50 shadow-sm ring-1 ring-blue-500/20'
                      : 'bg-slate-950/50 border-slate-800/80 hover:bg-slate-950'
                  }`}
                >
                  {/* Step Header */}
                  <div
                    onClick={() => toggleExpand(idx)}
                    className="flex items-center justify-between cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-slate-200">
                        {step.stepNumber}. {step.title}
                      </span>
                      <span
                        className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase font-mono ${
                          step.status === 'COMPLETED'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : step.status === 'WAITING FOR EVIDENCE'
                            ? 'bg-amber-500/20 text-amber-400'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {step.status}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-slate-500">{step.timestamp}</span>
                      {isExpanded ? (
                        <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                      )}
                    </div>
                  </div>

                  {/* Expanded Body */}
                  {isExpanded && (
                    <div className="mt-2.5 pt-2 border-t border-slate-800/60 space-y-2">
                      <p className="text-slate-300 leading-relaxed text-[11px]">
                        {step.description}
                      </p>

                      {step.toolCall && (
                        <div className="flex items-center gap-1.5 bg-slate-900 px-2.5 py-1 rounded text-[10px] font-mono text-emerald-400 border border-slate-800">
                          <Database className="w-3 h-3 text-blue-400" />
                          <span>Tool Call: {step.toolCall}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
      </div>

      {/* Stop Condition Banner */}
      {stopReason && (
        <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg text-xs text-slate-300 flex items-start gap-2.5">
          <ShieldAlert className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-slate-200 font-mono">
              Agent Stop Condition Satisfied:{' '}
            </span>
            <span className="text-slate-300">{stopReason}</span>
          </div>
        </div>
      )}
    </div>
  );
}
