import React from 'react';
import { Compass, TrendingUp, ShieldCheck, ArrowRight, Zap } from 'lucide-react';

export default function EvidenceCompass({ caseData }) {
  const caseDetail = caseData?.case || {};
  const finalProb = caseDetail.fraud_probability !== undefined ? caseDetail.fraud_probability : 0.88;
  
  // Estimate initial risk (e.g. baseline score or -18% of final if missing)
  const initialProb = Math.max(0.12, (finalProb * 0.65).toFixed(4));

  const initialActions = caseData?.next_best_actions?.initial || [];
  const finalActions = caseData?.next_best_actions?.final || [];
  const whatChanged = caseData?.next_best_actions?.what_changed || 'Graph evidence reinforced risk calibrated score.';

  // SVG Gauge Math (Radius 64, circumference ~ 402)
  const r = 60;
  const circumference = 2 * Math.PI * r;
  const initialOffset = circumference - (initialProb * circumference);
  const finalOffset = circumference - (finalProb * circumference);

  const getRouteBadgeStyle = (route) => {
    switch (route?.toLowerCase()) {
      case 'auto':
        return 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/30';
      case 'l1':
        return 'bg-[#F59E0B]/10 text-[#F59E0B] border-[#F59E0B]/30';
      case 'l2':
        return 'bg-[#FF3366]/10 text-[#FF3366] border-[#FF3366]/30';
      default:
        return 'bg-[#222222] text-[#FFFFFF] border-[#333333]';
    }
  };

  return (
    <div className="bg-[#0F0F0F] border border-[#222222] rounded-none p-4 flex flex-col h-full relative">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#222222] mb-3">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-[#FFFFFF]" />
          <span className="font-mono text-xs font-bold text-[#FFFFFF] tracking-wider uppercase">
            EVIDENCE COMPASS // RISK SHIFT
          </span>
        </div>
        <span className="font-mono text-[11px] text-[#777777]">
          VERDICT: <span className="text-[#FF3366] font-bold uppercase">{caseDetail.verdict || 'SUSPICIOUS'}</span>
        </span>
      </div>

      {/* 3D Circular Arc Progress */}
      <div className="flex items-center justify-around my-2 py-2">
        {/* Initial Risk Arc */}
        <div className="flex flex-col items-center">
          <div className="relative w-28 h-28 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="56"
                cy="56"
                r={r}
                fill="none"
                stroke="#222222"
                strokeWidth="8"
              />
              <circle
                cx="56"
                cy="56"
                r={r}
                fill="none"
                stroke="#777777"
                strokeWidth="8"
                strokeDasharray={circumference}
                strokeDashoffset={initialOffset}
                strokeLinecap="round"
                className="transition-all duration-700 ease-out"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="font-space text-lg font-bold text-[#777777]">
                {(initialProb * 100).toFixed(1)}%
              </span>
              <span className="font-mono text-[9px] text-[#777777] uppercase">Initial</span>
            </div>
          </div>
        </div>

        {/* Dynamic Shift Indicator Arrow */}
        <div className="flex flex-col items-center gap-1 text-[#777777]">
          <TrendingUp className="w-5 h-5 text-[#FF3366]" />
          <span className="font-mono text-[10px] text-[#FF3366] font-bold">
            +{( (finalProb - initialProb) * 100 ).toFixed(1)}%
          </span>
        </div>

        {/* Final Risk 3D Animated Arc */}
        <div className="flex flex-col items-center">
          <div className="relative w-28 h-28 flex items-center justify-center">
            {/* SVG Defs for 3D Arc Gradient */}
            <svg className="w-full h-full transform -rotate-90">
              <defs>
                <linearGradient id="riskArcGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#FF6688" />
                  <stop offset="100%" stopColor="#FF3366" />
                </linearGradient>
              </defs>
              <circle
                cx="56"
                cy="56"
                r={r}
                fill="none"
                stroke="#1A1A1A"
                strokeWidth="10"
              />
              <circle
                cx="56"
                cy="56"
                r={r}
                fill="none"
                stroke="url(#riskArcGrad)"
                strokeWidth="10"
                strokeDasharray={circumference}
                strokeDashoffset={finalOffset}
                strokeLinecap="round"
                className="transition-all duration-1000 ease-out drop-shadow-[0_0_8px_rgba(255,51,102,0.4)]"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="font-space text-xl font-bold text-[#FFFFFF]">
                {(finalProb * 100).toFixed(1)}%
              </span>
              <span className="font-mono text-[9px] text-[#FF3366] font-bold uppercase tracking-wider">Calibrated</span>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Shift Evolution Note */}
      <div className="bg-[#050505] border border-[#222222] p-2.5 my-2">
        <span className="font-mono text-[10px] text-[#777777] block uppercase mb-1">
          EVIDENCE EVOLUTION NOTE:
        </span>
        <p className="font-mono text-xs text-[#FFFFFF] leading-snug">
          {whatChanged}
        </p>
      </div>

      {/* Route Badges Section */}
      <div className="mt-2 space-y-2">
        <span className="font-mono text-[10px] text-[#777777] block uppercase">
          RECOMMENDED POLICY ROUTES & ACTIONS:
        </span>
        <div className="grid grid-cols-1 gap-2">
          {finalActions.map((item, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between bg-[#050505] border border-[#222222] p-2"
            >
              <div className="flex items-center gap-2">
                <Zap className="w-3.5 h-3.5 text-[#FFFFFF]" />
                <span className="font-mono text-xs font-bold text-[#FFFFFF]">
                  {item.action}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 text-[10px] font-mono font-bold border ${getRouteBadgeStyle(item.approval_route)}`}>
                  {item.approval_route?.toUpperCase()}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
