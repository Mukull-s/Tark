import React, { useState, useEffect } from 'react';
import { Play, Pause, SkipBack, SkipForward, RotateCcw, Activity, Terminal } from 'lucide-react';
import { InvestigationStep } from '../../types/investigation';

export default function InvestigationReplay({
  steps,
  currentStepIndex,
  onStepChange,
  isAutoPlaying,
  onToggleAutoPlay
}) {
  if (!steps || steps.length === 0) return null;

  const currentStep = steps[currentStepIndex] || steps[0];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm space-y-3.5">
      {/* Replay Controls Header */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-400" />
          <h3 className="text-xs font-black uppercase tracking-wider text-slate-200">
            Investigation Replay & Step Scrubber
          </h3>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">
            Step <strong className="text-blue-400 font-mono">{currentStepIndex + 1}</strong> of{' '}
            <strong className="text-slate-200 font-mono">{steps.length}</strong>
          </span>
          <span
            className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase font-mono ${
              currentStep.status === 'COMPLETED'
                ? 'bg-emerald-500/20 text-emerald-400'
                : currentStep.status === 'WAITING FOR EVIDENCE'
                ? 'bg-amber-500/20 text-amber-400 animate-pulse'
                : 'bg-slate-800 text-slate-400'
            }`}
          >
            {currentStep.status}
          </span>
        </div>
      </div>

      {/* Scrubber Progress Bar */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-1">
          {steps.map((s, idx) => {
            const isPassed = idx <= currentStepIndex;
            const isCurrent = idx === currentStepIndex;

            return (
              <button
                key={idx}
                onClick={() => onStepChange(idx)}
                title={`Step ${idx + 1}: ${s.title}`}
                className={`flex-1 h-2 rounded-sm transition ${
                  isCurrent
                    ? 'bg-blue-500 ring-2 ring-blue-400/40'
                    : isPassed
                    ? 'bg-blue-700/80 hover:bg-blue-600'
                    : 'bg-slate-800 hover:bg-slate-700'
                }`}
              />
            );
          })}
        </div>

        {/* Step Dots with Labels */}
        <div className="flex justify-between text-[9px] font-mono text-slate-500">
          <span>Start (Trigger)</span>
          <span>Uncertainty Loop</span>
          <span>Final NBA</span>
        </div>
      </div>

      {/* Current Step Content Box */}
      <div className="bg-slate-950/80 border border-slate-800/80 rounded-lg p-3 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold text-blue-300">
              {currentStep.eventType}
            </span>
            <span className="text-xs text-slate-300 font-semibold">— {currentStep.title}</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">{currentStep.timestamp}</span>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">{currentStep.description}</p>

        {currentStep.toolCall && (
          <div className="flex items-center gap-1.5 bg-slate-900 px-2.5 py-1 rounded text-[11px] font-mono text-emerald-400 border border-slate-800">
            <Terminal className="w-3 h-3 text-emerald-500" />
            <span>{currentStep.toolCall}</span>
          </div>
        )}
      </div>

      {/* Scrubber Navigation Buttons */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onStepChange(Math.max(0, currentStepIndex - 1))}
            disabled={currentStepIndex === 0}
            className="flex items-center gap-1 px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300 font-semibold transition"
          >
            <SkipBack className="w-3 h-3" />
            Prev Step
          </button>

          <button
            onClick={onToggleAutoPlay}
            className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-bold transition ${
              isAutoPlaying
                ? 'bg-amber-500 text-slate-950'
                : 'bg-blue-600 hover:bg-blue-500 text-slate-950'
            }`}
          >
            {isAutoPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
            {isAutoPlaying ? 'Pause Replay' : 'Auto Play'}
          </button>

          <button
            onClick={() => onStepChange(Math.min(steps.length - 1, currentStepIndex + 1))}
            disabled={currentStepIndex === steps.length - 1}
            className="flex items-center gap-1 px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300 font-semibold transition"
          >
            Next Step
            <SkipForward className="w-3 h-3" />
          </button>
        </div>

        <button
          onClick={() => onStepChange(0)}
          className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center gap-1 transition"
        >
          <RotateCcw className="w-3 h-3" />
          Rewind
        </button>
      </div>
    </div>
  );
}
