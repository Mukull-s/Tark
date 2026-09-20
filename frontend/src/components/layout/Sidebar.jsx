import React, { useState, useMemo } from 'react';
import {
  Shield,
  FolderOpen,
  Activity,
  CheckSquare,
  History,
  Share2,
  FileText,
  Settings,
  Database,
  Search,
  CheckCircle2,
  Wifi,
  WifiOff
} from '../common/Icons';

export default function Sidebar({
  cases = [],
  selectedCaseId,
  onSelectCase,
  investigatedCases = [],
  activeNav,
  onSelectNav,
  isMockMode,
  onToggleMockMode
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');

  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      const matchesSearch =
        c.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (c.card_id && c.card_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (c.desc && c.desc.toLowerCase().includes(searchTerm.toLowerCase()));

      const matchesType = filterType === 'all' || c.type === filterType;
      return matchesSearch && matchesType;
    });
  }, [cases, searchTerm, filterType]);

  const navItems = [
    { id: 'cases', label: 'Cases', icon: FolderOpen, count: cases.length },
    { id: 'investigations', label: 'Investigations', icon: Activity, count: investigatedCases.length },
    { id: 'approvals', label: 'Approvals', icon: CheckSquare, count: 1 },
    { id: 'memory', label: 'Case Memory', icon: History },
    { id: 'graph', label: 'Graph Explorer', icon: Share2 },
    { id: 'reports', label: 'Reports (SAR)', icon: FileText }
  ];

  return (
    <aside className="w-58 border-r border-slate-800 bg-slate-950 flex flex-col h-full select-none shrink-0 text-slate-300">
      {/* Brand Header */}
      <div className="p-3.5 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded bg-blue-600/20 border border-blue-500/40 text-blue-400 flex items-center justify-center font-bold">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <span className="font-mono font-black text-sm text-slate-100 tracking-wider block">
              TARK
            </span>
            <span className="text-[9px] text-slate-400 font-mono tracking-wider uppercase block">
              Fraud Workstation
            </span>
          </div>
        </div>

        <button
          onClick={onToggleMockMode}
          title={isMockMode ? "Switch to Live FastAPI API (:8000)" : "Switch to Mock Fixtures"}
          className={`p-1 rounded text-[10px] border transition ${
            isMockMode
              ? 'bg-amber-950/40 border-amber-800/60 text-amber-400'
              : 'bg-emerald-950/40 border-emerald-800/60 text-emerald-400'
          }`}
        >
          {isMockMode ? <WifiOff className="w-3 h-3" /> : <Wifi className="w-3 h-3" />}
        </button>
      </div>

      {/* Navigation Links */}
      <div className="p-2 space-y-0.5 border-b border-slate-800/60 text-xs">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeNav === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onSelectNav(item.id)}
              className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs transition ${
                isActive
                  ? 'bg-slate-800 text-slate-100 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
              }`}
            >
              <div className="flex items-center gap-2">
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-blue-400' : 'text-slate-500'}`} />
                <span>{item.label}</span>
              </div>
              {item.count !== undefined && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                    isActive ? 'bg-blue-600/30 text-blue-300' : 'bg-slate-900 text-slate-500'
                  }`}
                >
                  {item.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Case List Header & Search */}
      <div className="p-2.5 space-y-1.5 border-b border-slate-800/60">
        <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase font-mono">
          <span>Benchmark Exam (20)</span>
          <span className="text-slate-500">M5–M6</span>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search cases..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-900/80 border border-slate-800 rounded pl-7 pr-2 py-1 text-[11px] text-slate-200 placeholder-slate-500 focus:outline-none focus:border-slate-600 transition font-mono"
          />
        </div>
      </div>

      {/* Scrollable Cases List */}
      <div className="flex-1 overflow-y-auto p-1.5 space-y-1 scrollbar-thin scrollbar-thumb-slate-800">
        {filteredCases.map((bCase) => {
          const isSelected = selectedCaseId === bCase.id;
          const isDone = investigatedCases.includes(bCase.id);

          return (
            <button
              key={bCase.id}
              onClick={() => onSelectCase(bCase.id)}
              className={`w-full text-left p-2 rounded text-xs transition border ${
                isSelected
                  ? 'bg-slate-800 border-slate-700 text-slate-100 shadow-sm'
                  : 'bg-slate-950 border-slate-900 hover:bg-slate-900/80 text-slate-400 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center justify-between mb-0.5">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono font-bold text-[11px] text-slate-200">{bCase.id}</span>
                  {bCase.id === 'HHG-017' && (
                    <span className="text-[8px] bg-amber-500/20 text-amber-300 px-1 py-0.2 rounded font-mono font-bold">
                      DEMO
                    </span>
                  )}
                </div>

                {isDone && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
              </div>

              <div className="text-[10px] text-slate-500 line-clamp-1 leading-snug">
                {bCase.desc}
              </div>
            </button>
          );
        })}
      </div>

      {/* System Status Footer */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950 text-[10px] space-y-1.5">
        <div className="flex items-center justify-between text-slate-400">
          <span className="flex items-center gap-1.5">
            <Database className="w-3 h-3 text-emerald-400" />
            <span>TigerGraph Savanna</span>
          </span>
          <span className="text-emerald-400 font-mono font-semibold">ONLINE</span>
        </div>
        <div className="flex items-center justify-between text-slate-500">
          <span>Mode: {isMockMode ? 'Mock Fixtures' : 'FastAPI (:8000)'}</span>
          <span className="font-mono">v1.0.0</span>
        </div>
      </div>
    </aside>
  );
}
