import React from 'react';
import { Shield, Database, Cpu, Lock, Play, RotateCcw, Wifi, WifiOff } from 'lucide-react';
import { ApiConfig } from '../../services/api';

export default function Header({
  isLiveStreaming,
  onStartInvestigation,
  onResetInvestigation,
  isMockMode,
  onToggleMockMode
}) {
  return (
    <header className="border-b border-slate-800 bg-slate-950/95 backdrop-blur px-6 py-3 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-40">
      {/* Brand & System Title */}
      <div className="flex items-center gap-3.5">
        <div className="p-2 bg-blue-600/15 text-blue-400 border border-blue-500/30 rounded-lg shadow-inner">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-black tracking-widest uppercase bg-gradient-to-r from-blue-400 via-indigo-200 to-purple-400 bg-clip-text text-transparent">
              TARK
            </h1>
            <span className="text-[10px] bg-blue-950/80 text-blue-300 font-mono font-bold px-2 py-0.5 rounded border border-blue-800/60">
              ANALYST WORKSTATION
            </span>
          </div>
          <p className="text-[10px] text-slate-400 tracking-wider uppercase font-mono">
            TigerGraph Savanna • Agentic Fraud Investigation • HHGOA
          </p>
        </div>
      </div>

      {/* Engine & Telemetry Badges */}
      <div className="flex flex-wrap items-center gap-2.5 text-xs">
        {/* TigerGraph Engine Status */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-md">
          <Database className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-slate-400 font-medium">TigerGraph:</span>
          <span className="text-emerald-400 font-mono font-bold text-[11px]">SAVANNA (GSQL)</span>
        </div>

        {/* LangGraph Agent Engine */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-md">
          <Cpu className="w-3.5 h-3.5 text-purple-400" />
          <span className="text-slate-400 font-medium">Agent:</span>
          <span className="text-purple-400 font-mono font-bold text-[11px]">LANGGRAPH STATE</span>
        </div>

        {/* Policy Firewall Routing */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-md">
          <Lock className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-slate-400 font-medium">Policy Firewall:</span>
          <span className="text-amber-400 font-mono font-bold text-[11px]">DETERMINISTIC L1/L2</span>
        </div>

        {/* Mode Toggle (Live Backend vs Mock Offline) */}
        <button
          onClick={onToggleMockMode}
          title="Toggle between Live FastAPI Backend and Offline Mock Fixtures"
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-xs font-semibold transition ${
            isMockMode
              ? 'bg-amber-950/40 border-amber-800/80 text-amber-300 hover:bg-amber-900/50'
              : 'bg-emerald-950/40 border-emerald-800/80 text-emerald-300 hover:bg-emerald-900/50'
          }`}
        >
          {isMockMode ? <WifiOff className="w-3.5 h-3.5 text-amber-400" /> : <Wifi className="w-3.5 h-3.5 text-emerald-400" />}
          <span>{isMockMode ? 'MOCK MODE' : 'LIVE API (:8000)'}</span>
        </button>

        {/* Investigation Stream Trigger */}
        <div className="flex items-center gap-1.5 ml-1">
          <button
            onClick={onStartInvestigation}
            disabled={isLiveStreaming}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md font-bold text-xs shadow transition ${
              isLiveStreaming
                ? 'bg-blue-900/50 text-blue-300 border border-blue-700/50 cursor-wait animate-pulse'
                : 'bg-blue-600 hover:bg-blue-500 text-slate-950'
            }`}
          >
            <Play className="w-3.5 h-3.5" />
            <span>{isLiveStreaming ? 'INVESTIGATING...' : 'RUN INVESTIGATION'}</span>
          </button>

          <button
            onClick={onResetInvestigation}
            title="Reset Timeline & Stream"
            className="p-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-md text-slate-400 hover:text-slate-200 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
}
