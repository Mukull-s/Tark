import React from 'react';
import {
  FolderOpen,
  Activity,
  CheckSquare,
  History,
  Share2,
  FileText,
  Settings,
  Database,
  Wifi,
  WifiOff,
  Layers,
  Shield
} from '../common/Icons';

export default function Sidebar({
  activeNav = 'cases',
  onSelectNav,
  casesCount = 20,
  investigatedCount = 1,
  approvalsCount = 1,
  isMockMode = false,
  onToggleMockMode
}) {
  const sections = [
    {
      title: 'WORKSPACE',
      items: [
        { id: 'cases', label: 'Cases', icon: FolderOpen, count: casesCount },
        { id: 'investigations', label: 'Investigations', icon: Activity, count: investigatedCount },
        { id: 'approvals', label: 'Approvals', icon: CheckSquare, count: approvalsCount, badgeColor: 'text-amber-400 bg-amber-500/10' },
        { id: 'memory', label: 'Case Memory', icon: History }
      ]
    },
    {
      title: 'ANALYSIS',
      items: [
        { id: 'graph', label: 'Graph Explorer', icon: Share2 },
        { id: 'evidence', label: 'Evidence', icon: Layers }
      ]
    },
    {
      title: 'REPORTING',
      items: [
        { id: 'reports', label: 'Reports (SAR)', icon: FileText }
      ]
    }
  ];

  return (
    <aside className="w-56 border-r border-slate-800 bg-slate-950 flex flex-col justify-between h-full select-none shrink-0 text-slate-300">
      {/* Top Navigation Sections */}
      <div className="py-4 space-y-6 overflow-y-auto">
        {sections.map((section, sIdx) => (
          <div key={sIdx} className="space-y-1">
            <div className="px-4 text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
              {section.title}
            </div>

            <nav className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeNav === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectNav(item.id)}
                    className={`w-full flex items-center justify-between px-4 py-2 text-xs transition font-medium ${
                      isActive
                        ? 'bg-blue-950/40 text-white border-l-2 border-blue-500 font-semibold pl-[14px]'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 border-l-2 border-transparent pl-[14px]'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                      <span>{item.label}</span>
                    </div>

                    {item.count !== undefined && (
                      <span
                        className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded ${
                          item.badgeColor || (isActive ? 'bg-blue-900/50 text-blue-300' : 'bg-slate-900 text-slate-400')
                        }`}
                      >
                        {item.count}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* SYSTEM Section at bottom */}
      <div className="border-t border-slate-800/80 p-3.5 space-y-3 bg-slate-950/90">
        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
          SYSTEM
        </div>

        <div className="space-y-2 text-[11px] font-mono">
          {/* API Health */}
          <div className="flex items-center justify-between text-slate-400">
            <div className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full ${isMockMode ? 'bg-amber-400' : 'bg-emerald-400 animate-pulse'}`}></span>
              <span>FastAPI Gateway</span>
            </div>
            <span className={isMockMode ? 'text-amber-400' : 'text-emerald-400 font-semibold'}>
              {isMockMode ? 'MOCK' : 'ONLINE'}
            </span>
          </div>

          {/* TigerGraph Health */}
          <div className="flex items-center justify-between text-slate-400">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>TigerGraph Savanna</span>
            </div>
            <span className="text-emerald-400 font-semibold">CONNECTED</span>
          </div>
        </div>

        {/* Settings Button */}
        <button
          onClick={onToggleMockMode}
          className="w-full flex items-center justify-between px-2.5 py-1.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-[11px] transition"
        >
          <div className="flex items-center gap-2">
            <Settings className="w-3.5 h-3.5 text-slate-400" />
            <span>DataSource Mode</span>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            {isMockMode ? 'FIXTURE' : 'LIVE'}
          </span>
        </button>
      </div>
    </aside>
  );
}
