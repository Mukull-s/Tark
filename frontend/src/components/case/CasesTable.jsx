import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  ArrowRight,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  CreditCard,
  Smartphone,
  User,
  SlidersHorizontal,
  ExternalLink,
  RotateCcw
} from '../common/Icons';

export default function CasesTable({
  cases = [],
  selectedCaseId = 'HHG-017',
  onSelectCase,
  onOpenInvestigation,
  selectedCaseDetails
}) {
  const [activeTab, setActiveTab] = useState('ALL');
  const [triggerFilter, setTriggerFilter] = useState('ALL');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [localSearch, setLocalSearch] = useState('');
  const [selectedRowIds, setSelectedRowIds] = useState(new Set([selectedCaseId]));

  // Find currently selected case record
  const activeCase = useMemo(() => {
    return cases.find((c) => c.id === selectedCaseId) || cases[0] || null;
  }, [cases, selectedCaseId]);

  // Status counts
  const counts = useMemo(() => {
    const res = { all: cases.length, investigating: 0, review: 0, resolved: 0 };
    cases.forEach((c) => {
      const s = (c.status || '').toLowerCase();
      if (s.includes('active') || s.includes('investigat')) res.investigating++;
      else if (s.includes('review')) res.review++;
      else if (s.includes('resolved') || s.includes('closed')) res.resolved++;
    });
    return res;
  }, [cases]);

  // Filtering
  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      // Tab filter
      if (activeTab === 'INVESTIGATING') {
        const s = (c.status || '').toLowerCase();
        if (!s.includes('investigat') && !s.includes('active')) return false;
      } else if (activeTab === 'REVIEW') {
        if (!(c.status || '').toLowerCase().includes('review')) return false;
      } else if (activeTab === 'RESOLVED') {
        const s = (c.status || '').toLowerCase();
        if (!s.includes('resolved') && !s.includes('closed')) return false;
      }

      // Dropdown filters
      if (triggerFilter !== 'ALL' && c.trigger_type !== triggerFilter) return false;
      if (riskFilter !== 'ALL' && (c.risk || c.risk_level) !== riskFilter) return false;
      if (statusFilter !== 'ALL' && c.status !== statusFilter) return false;

      // Search term
      if (localSearch.trim()) {
        const q = localSearch.toLowerCase();
        const matchId = (c.id || '').toLowerCase().includes(q);
        const matchCust = (c.customer_id || '').toLowerCase().includes(q);
        const matchCard = (c.card_id || '').toLowerCase().includes(q);
        const matchDesc = (c.trigger_text || c.desc || '').toLowerCase().includes(q);
        const matchPattern = (c.pattern || '').toLowerCase().includes(q);
        if (!matchId && !matchCust && !matchCard && !matchDesc && !matchPattern) return false;
      }

      return true;
    });
  }, [cases, activeTab, triggerFilter, riskFilter, statusFilter, localSearch]);

  const toggleSelectRow = (id, e) => {
    e.stopPropagation();
    const updated = new Set(selectedRowIds);
    if (updated.has(id)) {
      updated.delete(id);
    } else {
      updated.add(id);
    }
    setSelectedRowIds(updated);
  };

  const handleRowClick = (c) => {
    onSelectCase(c.id);
  };

  const clearFilters = () => {
    setActiveTab('ALL');
    setTriggerFilter('ALL');
    setRiskFilter('ALL');
    setStatusFilter('ALL');
    setLocalSearch('');
  };

  return (
    <div className="flex-1 flex flex-col lg:flex-row overflow-hidden bg-slate-950 text-slate-100">
      {/* LEFT AREA: CASE MANAGEMENT TABLE (~68% width) */}
      <div className="flex-1 flex flex-col border-r border-slate-800 overflow-hidden">
        {/* Table Top Header */}
        <div className="p-5 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4 bg-slate-950/80">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-sans">
                Fraud Cases
              </h2>
              <span className="text-xs bg-slate-800 text-slate-300 font-mono font-bold px-2 py-0.5 rounded border border-slate-700">
                20 Benchmark Cases • Month 5–6
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Live case queue linked to TigerGraph Savanna graph clustering & real-time models
            </p>
          </div>

          {/* Local Search Input */}
          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              placeholder="Filter queue..."
              className="w-full bg-slate-900 border border-slate-800 rounded-md pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition font-sans"
            />
          </div>
        </div>

        {/* Tab & Filter Bar */}
        <div className="px-5 py-3 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 text-xs">
          {/* Status Tabs */}
          <div className="flex items-center gap-1">
            {[
              { id: 'ALL', label: `All (${counts.all})` },
              { id: 'INVESTIGATING', label: `Investigating (${counts.investigating})` },
              { id: 'REVIEW', label: `Review (${counts.review})` },
              { id: 'RESOLVED', label: `Resolved (${counts.resolved})` }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 rounded-md font-medium text-xs transition ${
                  activeTab === tab.id
                    ? 'bg-blue-900/40 text-blue-300 border border-blue-700/60 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Filter Dropdowns */}
          <div className="flex items-center gap-2">
            {/* Trigger Filter */}
            <select
              value={triggerFilter}
              onChange={(e) => setTriggerFilter(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-slate-300 focus:outline-none focus:border-blue-500 text-xs"
            >
              <option value="ALL">Trigger: All</option>
              <option value="risk_score">Trigger: Risk Score</option>
              <option value="customer_report">Trigger: Customer Report</option>
              <option value="analyst_request">Trigger: Analyst Request</option>
            </select>

            {/* Risk Filter */}
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-slate-300 focus:outline-none focus:border-blue-500 text-xs"
            >
              <option value="ALL">Risk: All</option>
              <option value="HIGH">Risk: High</option>
              <option value="MEDIUM">Risk: Medium</option>
              <option value="LOW">Risk: Low</option>
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-slate-300 focus:outline-none focus:border-blue-500 text-xs"
            >
              <option value="ALL">Status: All</option>
              <option value="Investigating">Status: Investigating</option>
              <option value="Review">Status: Review</option>
              <option value="Resolved">Status: Resolved</option>
            </select>

            {/* Clear Button */}
            {(activeTab !== 'ALL' || triggerFilter !== 'ALL' || riskFilter !== 'ALL' || statusFilter !== 'ALL' || localSearch) && (
              <button
                onClick={clearFilters}
                className="text-slate-400 hover:text-slate-200 flex items-center gap-1 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 transition"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>

        {/* Dynamic Cases Table */}
        <div className="flex-1 overflow-y-auto">
          <table className="w-full text-left border-collapse font-sans text-xs">
            <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider font-mono sticky top-0 z-10">
              <tr>
                <th className="py-2.5 pl-4 pr-2 w-8">
                  <input
                    type="checkbox"
                    className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0 cursor-pointer"
                  />
                </th>
                <th className="py-2.5 px-3">Case</th>
                <th className="py-2.5 px-3">Trigger</th>
                <th className="py-2.5 px-3 text-right">Amount</th>
                <th className="py-2.5 px-3">Customer</th>
                <th className="py-2.5 px-3">Card</th>
                <th className="py-2.5 px-3">Risk</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Pattern</th>
                <th className="py-2.5 pr-4 pl-3">Last Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {filteredCases.map((c) => {
                const isSelected = selectedCaseId === c.id;
                const isHigh = (c.risk || c.risk_level) === 'HIGH';
                const isMed = (c.risk || c.risk_level) === 'MEDIUM';

                return (
                  <tr
                    key={c.id}
                    onClick={() => handleRowClick(c)}
                    className={`cursor-pointer transition select-none group ${
                      isSelected
                        ? 'bg-blue-950/30 border-l-2 border-l-blue-500'
                        : 'hover:bg-slate-900/60 border-l-2 border-l-transparent'
                    }`}
                  >
                    {/* Checkbox */}
                    <td className="py-3 pl-4 pr-2" onClick={(e) => toggleSelectRow(c.id, e)}>
                      <input
                        type="checkbox"
                        checked={selectedRowIds.has(c.id)}
                        onChange={() => {}}
                        className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0 cursor-pointer"
                      />
                    </td>

                    {/* Case ID */}
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-1.5 font-mono font-bold text-slate-100 group-hover:text-blue-400">
                        <span>{c.id}</span>
                        {c.id === 'HHG-017' && (
                          <span className="text-[9px] bg-blue-950 text-blue-300 px-1 py-0.2 rounded border border-blue-800">
                            DEMO
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {c.opened_at ? c.opened_at.split(' ')[0] : '2016-12-05'}
                      </div>
                    </td>

                    {/* Trigger */}
                    <td className="py-3 px-3">
                      <div className="font-medium text-slate-200">
                        {c.trigger || (c.trigger_type === 'customer_report' ? 'Customer Report' : 'Risk Score')}
                      </div>
                      <div className="text-[10px] text-slate-400 truncate max-w-[140px]" title={c.trigger_text || c.desc}>
                        {c.trigger_text || c.desc}
                      </div>
                    </td>

                    {/* Amount */}
                    <td className="py-3 px-3 text-right font-mono font-bold text-slate-100">
                      ${(c.amount || c.exposure_usd || 100.09).toFixed(2)}
                    </td>

                    {/* Customer */}
                    <td className="py-3 px-3 font-mono text-slate-300">
                      {c.customer_id || 'C04570'}
                    </td>

                    {/* Card */}
                    <td className="py-3 px-3 font-mono text-slate-400 text-[11px]">
                      {c.card_id || 'C04570-K1'}
                    </td>

                    {/* Risk Badge */}
                    <td className="py-3 px-3">
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${
                          isHigh
                            ? 'bg-red-500/15 text-red-400 border-red-500/30'
                            : isMed
                            ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                            : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                        }`}
                      >
                        {c.risk || c.risk_level || (c.fraud_probability >= 0.75 ? 'HIGH' : 'MEDIUM')}
                      </span>
                    </td>

                    {/* Status Badge */}
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-1.5 text-[11px] font-medium">
                        {c.status === 'Investigating' ? (
                          <>
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
                            <span className="text-blue-300">Active</span>
                          </>
                        ) : c.status === 'Resolved' ? (
                          <>
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            <span className="text-emerald-300">Resolved</span>
                          </>
                        ) : (
                          <>
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                            <span className="text-amber-300">Review</span>
                          </>
                        )}
                      </div>
                    </td>

                    {/* Pattern */}
                    <td className="py-3 px-3 text-slate-400 text-[11px] truncate max-w-[120px]">
                      {c.pattern || 'Card Testing'}
                    </td>

                    {/* Last Action */}
                    <td className="py-3 pr-4 pl-3">
                      <span className="text-[10px] font-mono bg-slate-900 text-slate-300 px-2 py-0.5 rounded border border-slate-800">
                        {c.last_action || (c.actions && c.actions[0]) || 'BLOCK_CARD'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Footer info bar */}
        <div className="p-3 border-t border-slate-800 bg-slate-950 flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <div>
            Showing {filteredCases.length} of {cases.length} benchmark investigations
          </div>
          <div className="flex items-center gap-3">
            <span>Selected: {selectedRowIds.size} cases</span>
            <span className="text-slate-600">|</span>
            <span>Batch Actions: None</span>
          </div>
        </div>
      </div>

      {/* RIGHT AREA: SELECTED CASE DETAILS PANEL (~32% width) */}
      {activeCase && (
        <aside className="w-full lg:w-96 flex flex-col justify-between bg-slate-900/60 overflow-y-auto select-none">
          <div className="p-5 space-y-5">
            {/* Header: Case ID, Risk Badge, Trigger, Amount */}
            <div className="border-b border-slate-800 pb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xl font-black font-mono text-slate-100">
                    {activeCase.id}
                  </span>
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${
                      (activeCase.risk || activeCase.risk_level) === 'HIGH'
                        ? 'bg-red-500/20 text-red-400 border-red-500/40'
                        : 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                    }`}
                  >
                    {(activeCase.risk || activeCase.risk_level || 'HIGH')} RISK
                  </span>
                </div>
                <div className="text-right">
                  <div className="text-lg font-black font-mono text-slate-100">
                    ${(activeCase.amount || activeCase.exposure_usd || 100.09).toFixed(2)}
                  </div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Exposure</div>
                </div>
              </div>

              <div className="mt-2 text-xs text-slate-300 font-medium">
                {activeCase.trigger || 'Customer Report Dispute'}
              </div>
              <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                {activeCase.trigger_text || activeCase.desc}
              </p>
            </div>

            {/* TRANSACTION SECTION */}
            <div className="space-y-1.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
                TRANSACTION
              </div>
              <div className="bg-slate-950 p-3 rounded-md border border-slate-800 text-xs space-y-1 font-mono">
                <div className="flex justify-between items-center text-slate-100 font-bold">
                  <span>${(activeCase.amount || 100.09).toFixed(2)} USD</span>
                  <span className="text-[10px] text-slate-400 font-normal">Tx: {activeCase.flagged_txn_id || '3450629'}</span>
                </div>
                <div className="text-slate-300">DigitalServices UK</div>
                <div className="text-[10px] text-slate-400">MCC: 5815 (Digital Goods / Software)</div>
              </div>
            </div>

            {/* CUSTOMER SECTION */}
            <div className="space-y-1.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
                CUSTOMER
              </div>
              <div className="bg-slate-950 p-3 rounded-md border border-slate-800 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-mono text-slate-200 font-bold">
                    <User className="w-3.5 h-3.5 text-blue-400" />
                    <span>{activeCase.customer_id || 'CUS-45872'}</span>
                  </div>
                  <span className="text-[10px] bg-slate-900 text-slate-400 px-1.5 rounded font-mono">3 Cards</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Account Age: 18 months • 2 previous investigations
                </div>
              </div>
            </div>

            {/* CARD SECTION */}
            <div className="space-y-1.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
                CARD
              </div>
              <div className="bg-slate-950 p-3 rounded-md border border-slate-800 text-xs space-y-1">
                <div className="flex items-center justify-between font-mono">
                  <div className="flex items-center gap-1.5 text-slate-200 font-bold">
                    <CreditCard className="w-3.5 h-3.5 text-purple-400" />
                    <span>{activeCase.card_id || 'C04570-K1'}</span>
                  </div>
                  <span className="text-[10px] text-red-400 font-bold">HIGH RISK</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Status: Suspended (Pending L1 Approval)
                </div>
              </div>
            </div>

            {/* DEVICE SECTION */}
            <div className="space-y-1.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
                DEVICE
              </div>
              <div className="bg-slate-950 p-3 rounded-md border border-slate-800 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-mono text-slate-200 font-semibold">
                    <Smartphone className="w-3.5 h-3.5 text-amber-400" />
                    <span>DEV-9104 (Samsung SM-G892A)</span>
                  </div>
                </div>
                <div className="text-[11px] text-amber-300">
                  ⚠️ Shared across 3 distinct cardholder accounts
                </div>
              </div>
            </div>

            {/* CASE CONTEXT TABLE */}
            <div className="space-y-1.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
                CASE CONTEXT
              </div>
              <div className="bg-slate-950 p-3 rounded-md border border-slate-800 text-xs space-y-2 font-mono">
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-400">Initial Risk Score:</span>
                  <span className="text-slate-200 font-bold">{activeCase.risk_score !== null && activeCase.risk_score !== undefined ? activeCase.risk_score : '0.57'}</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-400">Billing Region:</span>
                  <span className="text-slate-200">UK / Region 444</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-400">Channel:</span>
                  <span className="text-slate-200">Online / CNP</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-400">Pattern Identified:</span>
                  <span className="text-amber-300 font-semibold">{activeCase.pattern || 'Card Testing'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Prominent Bottom Action: OPEN INVESTIGATION */}
          <div className="p-4 border-t border-slate-800 bg-slate-950">
            <button
              onClick={() => onOpenInvestigation(activeCase.id)}
              className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg text-xs tracking-wider uppercase flex items-center justify-center gap-2 shadow-lg shadow-blue-900/20 transition group"
            >
              <span>OPEN INVESTIGATION</span>
              <ArrowRight className="w-4 h-4 transition group-hover:translate-x-1" />
            </button>
          </div>
        </aside>
      )}
    </div>
  );
}
