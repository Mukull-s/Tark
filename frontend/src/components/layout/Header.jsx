import React from 'react';
import {
  Shield,
  Search,
  Database,
  Activity,
  CheckCircle2,
  Wifi,
  WifiOff,
  User,
  Settings
} from '../common/Icons';

export default function Header({
  searchTerm = '',
  onSearchChange,
  isMockMode = false,
  onToggleMockMode,
  selectedCaseId,
  isLiveStreaming = false
}) {
  return (
    <header className="h-14 border-b border-slate-800 bg-slate-950 px-5 flex items-center justify-between gap-6 shrink-0 z-40 select-none">
      {/* LEFT: TARK Brand */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="w-8 h-8 rounded bg-blue-600/20 border border-blue-500/40 text-blue-400 flex items-center justify-center font-black">
          <Shield className="w-4 h-4" />
        </div>
        <div className="leading-tight">
          <div className="flex items-center gap-2">
            <span className="text-sm font-black tracking-wider text-slate-100 uppercase font-mono">
              TARK
            </span>
            <span className="text-[10px] bg-slate-800 text-slate-300 font-mono font-semibold px-1.5 py-0.2 rounded border border-slate-700">
              v1.0
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-medium">
            Fraud Investigation Workstation
          </p>
        </div>
      </div>

      {/* CENTER: Global Search */}
      <div className="flex-1 max-w-xl">
        <div className="relative flex items-center">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
            placeholder="Search cases, customers, cards, transactions... (e.g. HHG-017, C04570)"
            className="w-full bg-slate-900 border border-slate-800 rounded-md pl-9 pr-14 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition font-sans"
          />
          <kbd className="absolute right-2.5 px-1.5 py-0.5 text-[10px] font-mono bg-slate-800 border border-slate-700 text-slate-400 rounded">
            ⌘K
          </kbd>
        </div>
      </div>

      {/* RIGHT: Telemetry & Analyst Profile */}
      <div className="flex items-center gap-4 text-xs shrink-0">
        {/* API Connection Indicator */}
        <button
          onClick={onToggleMockMode}
          title="Click to toggle between Live Backend and Offline Mock Fixtures"
          className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 transition"
        >
          {isMockMode ? (
            <>
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              <span className="text-[11px] font-mono text-amber-300">MOCK DATA</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-[11px] font-mono text-emerald-300">API CONNECTED (:8000)</span>
            </>
          )}
        </button>

        {/* TigerGraph Savanna Status */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
          <Database className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-[11px] font-mono text-slate-300">Savanna GSQL</span>
          <span className="text-[9px] bg-emerald-500/20 text-emerald-400 font-bold px-1 rounded">24ms</span>
        </div>

        {/* Active Case Badge */}
        {selectedCaseId && (
          <div className="hidden md:flex items-center gap-1.5 px-2 py-1 rounded bg-blue-950/60 border border-blue-800/80 text-blue-300 font-mono text-[11px]">
            <Activity className={`w-3 h-3 ${isLiveStreaming ? 'animate-spin text-blue-400' : ''}`} />
            <span>CASE: {selectedCaseId}</span>
          </div>
        )}

        {/* Analyst Profile */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
          <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-semibold text-xs">
            <User className="w-3.5 h-3.5" />
          </div>
          <div className="leading-none text-left hidden lg:block">
            <div className="text-[11px] font-semibold text-slate-200">Person 3</div>
            <div className="text-[9px] font-mono text-slate-400">Lead Investigator</div>
          </div>
        </div>
      </div>
    </header>
  );
}
