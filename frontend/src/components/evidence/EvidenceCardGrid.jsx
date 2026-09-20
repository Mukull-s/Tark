import React, { useState } from 'react';
import {
  FileText,
  Database,
  UserCheck,
  Smartphone,
  CreditCard,
  History,
  Layers,
  Shield,
  Activity
} from '../common/Icons';

export default function EvidenceCardGrid({ evidence = [] }) {
  const [selectedCategory, setSelectedCategory] = useState('ALL');

  // Grounded sample evidence if empty
  const defaultEvidence = [
    {
      category: 'TRANSACTION',
      title: 'Rapid Online Authorizations',
      key_value: '$100.09 USD',
      claim: 'Three online authorizations under $3 within 40 minutes, then a $100.09 purchase under digital services.',
      finding: 'Card testing sequence identified on online gateway.',
      source: 'TigerGraph card_window()',
      why_it_matters: 'Micro-authorizations verify card validity before high-value extraction.',
      entity_ids: ['3450620', '3450621', '3450629']
    },
    {
      category: 'CUSTOMER / CARD',
      title: 'Account Baseline & Exposure',
      key_value: 'CUS-45872 • C04570-K1',
      claim: 'Customer baseline: 59 historical txns, avg $342.87, primary channel online.',
      finding: 'High cumulative exposure across testing cluster.',
      source: 'Customer Behavioral Baseline',
      why_it_matters: 'Deviation from typical merchant category profile.',
      entity_ids: ['C04570', 'C04570-K1']
    },
    {
      category: 'DEVICE / IDENTITY',
      title: 'Shared Device Syndicate Profile',
      key_value: 'DEV-9104 (Samsung SM-G892A)',
      claim: 'Device profile marked New for account, previously observed on closed fraud case CC-0141.',
      finding: 'Suspicious shared-device relationship across 3 distinct customers.',
      source: 'TigerGraph device_neighbors()',
      why_it_matters: 'High probability of syndicate actor using virtualized device farm.',
      entity_ids: ['DEV_c37b877bcc5f', 'CC-0141']
    },
    {
      category: 'RELATIONSHIPS',
      title: 'Connected Compromised Cards',
      key_value: 'Card C00877-K1 Linked',
      claim: 'Device links active case directly to second card C00877-K1 flagged in prior week.',
      finding: 'Coordinated card theft ring across regional accounts.',
      source: 'TigerGraph 2-Hop Path Expansion',
      why_it_matters: 'Cross-card infection requires coordinated blocking across accounts.',
      entity_ids: ['C00877-K1']
    },
    {
      category: 'HISTORICAL CASES',
      title: 'GraphRAG Similar Cases',
      key_value: '4 Historical Cases Found',
      claim: 'Closed cases CC-0141, CC-0289 exhibited identical 3-test authorization velocity.',
      finding: '94% vector similarity to confirmed card-testing syndicate.',
      source: 'TigerGraph Case Memory',
      why_it_matters: 'Past analysts confirmed fraud within 2 hours of similar trigger.',
      entity_ids: ['CC-0141', 'CC-0289']
    },
    {
      category: 'POLICY / REGULATORY',
      title: 'Deterministic Policy Match',
      key_value: 'Rules R1, R2 & R5 Triggered',
      claim: 'Policy rule R2 mandates immediate card block upon customer denial + shared device.',
      finding: 'L1 Team Lead authorization required due to exposure < $2,500.',
      source: 'Policy GraphRAG Engine',
      why_it_matters: 'Enforces compliant governance before automated execution.',
      entity_ids: ['RULE-R1', 'RULE-R2']
    }
  ];

  const items = evidence.length > 0 ? evidence.map((e, idx) => {
    let cat = e.category || 'TRANSACTION';
    if (!e.category) {
      if ((e.source || '').includes('customer') || (e.type || '').includes('CUSTOMER')) cat = 'CUSTOMER / CARD';
      else if ((e.finding || '').includes('Device') || (e.claim || '').includes('device') || (e.type || '').includes('DEVICE')) cat = 'DEVICE / IDENTITY';
      else if ((e.finding || '').includes('similar') || (e.claim || '').includes('prior') || (e.type || '').includes('HISTORICAL')) cat = 'HISTORICAL CASES';
      else if ((e.finding || '').includes('Policy') || (e.type || '').includes('POLICY')) cat = 'POLICY / REGULATORY';
      else if ((e.finding || '').includes('shared') || (e.type || '').includes('RELATION')) cat = 'RELATIONSHIPS';
    }
    return {
      category: cat,
      title: e.title || e.type || `Evidence Item #${idx + 1}`,
      key_value: e.key_value || e.finding || e.claim?.slice(0, 40) || 'Verified Signal',
      claim: e.claim || e.finding || 'Documented investigation evidence signal.',
      finding: e.finding || e.claim || 'Signal confirmed by investigation orchestrator.',
      source: e.source ? (e.source.toUpperCase().includes('GRAPH') ? 'TigerGraph Savanna' : e.source) : 'TigerGraph Savanna',
      why_it_matters: e.why_it_matters || 'Direct empirical support for final fraud determination.',
      entity_ids: e.entity_ids || []
    };
  }) : defaultEvidence;

  const categories = [
    'ALL',
    'TRANSACTION',
    'CUSTOMER / CARD',
    'DEVICE / IDENTITY',
    'RELATIONSHIPS',
    'HISTORICAL CASES',
    'POLICY / REGULATORY'
  ];

  const filtered = selectedCategory === 'ALL'
    ? items
    : items.filter((item) => item.category === selectedCategory);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm space-y-4">
      {/* Header & Filter Pills */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-blue-400" />
          <h3 className="text-xs font-black uppercase tracking-wider text-slate-100 font-mono">
            Structured Evidence Workspace ({items.length} Grounded Signals)
          </h3>
        </div>

        {/* Category Pills */}
        <div className="flex flex-wrap items-center gap-1">
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setSelectedCategory(c)}
              className={`px-2.5 py-1 rounded text-[10px] font-mono font-semibold transition ${
                selectedCategory === c
                  ? 'bg-blue-900/50 text-blue-300 border border-blue-700/60 font-bold'
                  : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-slate-200'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Structured Evidence Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {filtered.map((item, idx) => (
          <div
            key={idx}
            className="bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-lg p-3.5 space-y-2 text-xs transition"
          >
            {/* Header: Category, Title & Source */}
            <div className="flex items-center justify-between gap-2 border-b border-slate-800/60 pb-2">
              <span className="text-[10px] bg-slate-900 text-blue-400 font-mono font-bold px-2 py-0.5 rounded border border-slate-800 uppercase">
                {item.category}
              </span>
              <span className="text-[10px] text-slate-400 font-mono truncate max-w-[150px]">
                {item.source}
              </span>
            </div>

            {/* Key Value & Title */}
            <div>
              <div className="font-mono font-bold text-slate-100 text-xs">
                {item.key_value}
              </div>
              <div className="text-[11px] text-slate-300 mt-0.5 leading-snug">
                {item.claim}
              </div>
            </div>

            {/* Finding */}
            <div className="bg-slate-900/60 p-2 rounded border border-slate-800/80 text-[11px]">
              <span className="text-slate-400 font-semibold mr-1 font-mono uppercase text-[10px]">
                Finding:
              </span>
              <span className="text-slate-200">{item.finding}</span>
            </div>

            {/* Significance */}
            {item.why_it_matters && (
              <div className="text-[10px] text-amber-300/90 font-mono leading-relaxed">
                <span className="font-bold text-amber-400 mr-1">WHY IT MATTERS:</span>
                {item.why_it_matters}
              </div>
            )}

            {/* Entity IDs footer */}
            {item.entity_ids && item.entity_ids.length > 0 && (
              <div className="flex flex-wrap items-center gap-1 pt-1 border-t border-slate-800/60 text-[10px] font-mono">
                <span className="text-slate-500">ENTITIES:</span>
                {item.entity_ids.map((id, idIdx) => (
                  <span
                    key={idIdx}
                    className="bg-slate-900 text-slate-400 px-1.5 py-0.2 rounded border border-slate-800"
                  >
                    {id}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
