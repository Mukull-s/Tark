import React, { useState } from 'react';
import { Share2, ShieldAlert, CreditCard, User, Laptop, Info } from 'lucide-react';

export default function GraphNetwork({ caseData, selectedCaseId }) {
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);

  // Extract graph entity details dynamically from caseData
  const caseDetail = caseData?.case || {};
  const affectedTxns = caseDetail.affected_txn_ids || ['TXN-89021'];
  const connectedCards = caseDetail.connected_card_ids || ['CARD-4412'];
  const similarCases = caseDetail.similar_prior_cases || [];

  // Extract customer ID from tool_calls if available
  let customerId = 'C-10928';
  if (caseData?.tool_calls) {
    const custCall = caseData.tool_calls.find((t) => t.params?.cust_id);
    if (custCall?.params?.cust_id) {
      customerId = custCall.params.cust_id;
    }
  }

  const deviceId = `DEV-${selectedCaseId.replace('HHG-', '')}92`;

  // Layout Node Positioning (Width: 620, Height: 340)
  const nodes = [
    {
      id: customerId,
      label: `Customer ${customerId}`,
      type: 'customer',
      x: 90,
      y: 170,
      r: 22,
      gradient: 'emeraldGrad',
      icon: User,
      details: { role: 'Account Holder', risk: 'Medium', history: '422 txns' }
    },
    {
      id: connectedCards[0] || `CARD-${selectedCaseId}`,
      label: `Card ${connectedCards[0] || 'PAN-9012'}`,
      type: 'card',
      x: 230,
      y: 100,
      r: 20,
      gradient: 'emeraldGrad',
      icon: CreditCard,
      details: { type: 'Visa Corporate', status: 'Blocked', limit: '$15,000' }
    },
    ...affectedTxns.map((txnId, idx) => ({
      id: txnId,
      label: `Txn #${txnId}`,
      type: 'transaction',
      x: 380 + idx * 40,
      y: 170 + idx * 30,
      r: 24,
      gradient: 'crimsonGrad',
      isFraud: true,
      icon: ShieldAlert,
      details: {
        amount: `$${caseDetail.exposure_usd || '120.00'}`,
        status: 'Unauthorized',
        pattern: caseDetail.pattern || 'Card Testing'
      }
    })),
    {
      id: deviceId,
      label: `Device ${deviceId}`,
      type: 'device',
      x: 520,
      y: 110,
      r: 20,
      gradient: 'cyanGrad',
      icon: Laptop,
      details: { fp: 'fp_9018x392', ip: '194.26.29.11', geo: 'Bucharest, RO' }
    }
  ];

  if (similarCases.length > 0) {
    nodes.push({
      id: similarCases[0],
      label: `Ring Case ${similarCases[0]}`,
      type: 'ring',
      x: 320,
      y: 260,
      r: 18,
      gradient: 'crimsonGrad',
      isFraud: true,
      icon: Share2,
      details: { type: 'Prior Fraud Cluster', match: '96.4% Vector Similarity' }
    });
  }

  // Links connecting Customer -> Card -> Txn -> Device -> Shared Ring
  const links = [
    { source: nodes[0], target: nodes[1], shared: false, label: 'OWNS' },
    { source: nodes[1], target: nodes[2], shared: true, label: 'ON_CARD' },
    { source: nodes[2], target: nodes[3], shared: true, label: 'FROM_DEVICE' }
  ];

  if (nodes[4]) {
    links.push({ source: nodes[1], target: nodes[4], shared: true, label: 'SHARED_CARD' });
    links.push({ source: nodes[4], target: nodes[3], shared: true, label: 'LINKED_HW' });
  }

  const activeNode = selectedNode || hoveredNode;

  return (
    <div className="bg-[#0F0F0F] border border-[#222222] rounded-none p-4 flex flex-col h-full relative overflow-hidden">
      {/* Header & Graph Description */}
      <div className="flex items-center justify-between pb-3 border-b border-[#222222] mb-2">
        <div className="flex items-center gap-2">
          <Share2 className="w-4 h-4 text-[#FFFFFF]" />
          <div>
            <span className="font-mono text-xs font-bold text-[#FFFFFF] tracking-wider uppercase block">
              TIGERGRAPH MULTI-HOP GRAPH NETWORK // {selectedCaseId}
            </span>
            <span className="font-mono text-[10px] text-[#777777]">
              Customer ➔ Card ➔ Txn ➔ Device Hardware Linkage
            </span>
          </div>
        </div>

        {/* Legend Pills */}
        <div className="flex items-center gap-3 text-[10px] font-mono text-[#777777]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[#10B981]"></span> Cust/Card
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[#06B6D4]"></span> Device
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[#FF3366]"></span> Shared Ring Edge
          </span>
        </div>
      </div>

      {/* Graph Render Canvas */}
      <div className="flex-1 relative flex items-center justify-center min-h-[300px]">
        <svg viewBox="0 0 620 340" className="w-full h-full max-h-[360px]">
          <defs>
            <radialGradient id="emeraldGrad" cx="35%" cy="35%" r="65%">
              <stop offset="0%" stopColor="#6EE7B7" />
              <stop offset="40%" stopColor="#10B981" />
              <stop offset="100%" stopColor="#044E35" />
            </radialGradient>

            <radialGradient id="cyanGrad" cx="35%" cy="35%" r="65%">
              <stop offset="0%" stopColor="#A5F3FC" />
              <stop offset="40%" stopColor="#06B6D4" />
              <stop offset="100%" stopColor="#164E63" />
            </radialGradient>

            <radialGradient id="crimsonGrad" cx="35%" cy="35%" r="65%">
              <stop offset="0%" stopColor="#FFAAC1" />
              <stop offset="40%" stopColor="#FF3366" />
              <stop offset="100%" stopColor="#66001A" />
            </radialGradient>

            <filter id="crimsonGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background Grid Pattern */}
          <g opacity="0.12" pointerEvents="none">
            <line x1="0" y1="80" x2="620" y2="80" stroke="#444444" strokeDasharray="2 4" />
            <line x1="0" y1="170" x2="620" y2="170" stroke="#444444" strokeDasharray="2 4" />
            <line x1="0" y1="260" x2="620" y2="260" stroke="#444444" strokeDasharray="2 4" />
            <line x1="150" y1="0" x2="150" y2="340" stroke="#444444" strokeDasharray="2 4" />
            <line x1="310" y1="0" x2="310" y2="340" stroke="#444444" strokeDasharray="2 4" />
            <line x1="470" y1="0" x2="470" y2="340" stroke="#444444" strokeDasharray="2 4" />
          </g>

          {/* Render Links */}
          {links.map((link, i) => (
            <g key={i} pointerEvents="none">
              <line
                x1={link.source.x}
                y1={link.source.y}
                x2={link.target.x}
                y2={link.target.y}
                stroke={link.shared ? '#FF3366' : '#333333'}
                strokeWidth={link.shared ? '2' : '1.5'}
                filter={link.shared ? 'url(#crimsonGlow)' : undefined}
                opacity={link.shared ? '0.7' : '0.4'}
              />
              {link.shared && (
                <line
                  x1={link.source.x}
                  y1={link.source.y}
                  x2={link.target.x}
                  y2={link.target.y}
                  stroke="#FF3366"
                  strokeWidth="2"
                  className="animate-dash"
                  filter="url(#crimsonGlow)"
                />
              )}
            </g>
          ))}

          {/* Render Nodes */}
          {nodes.map((node) => {
            const isHovered = hoveredNode?.id === node.id;
            const isSelected = selectedNode?.id === node.id;
            return (
              <g
                key={node.id}
                className="cursor-pointer transition-transform duration-200"
                style={{
                  transformOrigin: `${node.x}px ${node.y}px`,
                  transform: isHovered || isSelected ? 'scale(1.15)' : 'scale(1.0)'
                }}
                onMouseEnter={() => setHoveredNode(node)}
                onMouseLeave={() => setHoveredNode(null)}
                onClick={() => setSelectedNode(node)}
              >
                {/* Outer Glow Ring for Fraud Nodes (pointer-events-none prevents hover stutter) */}
                {node.isFraud && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={node.r + 6}
                    fill="none"
                    stroke="#FF3366"
                    strokeWidth="1"
                    opacity="0.5"
                    className="animate-pulse"
                    pointerEvents="none"
                  />
                )}

                {/* Main 3D Sphere Node */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.r}
                  fill={`url(#${node.gradient})`}
                  stroke={isSelected || isHovered ? '#FFFFFF' : '#000000'}
                  strokeWidth={isSelected || isHovered ? '2' : '1'}
                />

                {/* Node Label Text */}
                <text
                  x={node.x}
                  y={node.y + node.r + 13}
                  textAnchor="middle"
                  fill={isSelected || isHovered ? '#FFFFFF' : '#777777'}
                  className="font-mono text-[9px] font-medium tracking-tight select-none pointer-events-none"
                >
                  {node.label}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover / Click Detail Card Footer */}
        {activeNode && (
          <div className="absolute bottom-2 left-2 right-2 bg-[#050505] border border-[#222222] p-2 flex items-center justify-between text-[11px] font-mono shadow-xl transition-all">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${activeNode.isFraud ? 'bg-[#FF3366]' : 'bg-[#10B981]'}`} />
              <span className="text-[#FFFFFF] font-bold">{activeNode.label}</span>
            </div>
            <div className="flex items-center gap-3 text-[#777777]">
              {Object.entries(activeNode.details).map(([k, v]) => (
                <span key={k}>
                  <span className="text-[#777777] uppercase">{k}:</span>{' '}
                  <span className="text-[#FFFFFF] font-medium">{v}</span>
                </span>
              ))}
            </div>
            {selectedNode && (
              <button
                onClick={() => setSelectedNode(null)}
                className="text-[#777777] hover:text-[#FFFFFF] ml-2 text-[10px]"
              >
                [DESELECT]
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
