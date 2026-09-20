import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Layers,
  Info,
  X,
  Share2,
  ShieldAlert,
  Activity
} from './common/Icons';

export default function GraphExplorer({ graphData, caseId }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [selectedElement, setSelectedElement] = useState(null);
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [nodeCount, setNodeCount] = useState(0);
  const [edgeCount, setEdgeCount] = useState(0);

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    // Build Cytoscape elements from graphData
    const elements = [];

    // Add nodes
    if (graphData.nodes) {
      graphData.nodes.forEach((n) => {
        elements.push({
          data: {
            id: n.id,
            label: n.label,
            type: n.type,
            properties: n.properties || {}
          }
        });
      });
    }

    // Add edges
    if (graphData.edges) {
      graphData.edges.forEach((e, idx) => {
        elements.push({
          data: {
            id: `e_${idx}_${e.source}_${e.target}`,
            source: e.source,
            target: e.target,
            label: e.label,
            properties: e.properties || {}
          }
        });
      });
    }

    setNodeCount(graphData.nodes?.length || 0);
    setEdgeCount(graphData.edges?.length || 0);

    // Initialize Cytoscape
    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#334155',
            'label': 'data(label)',
            'color': '#cbd5e1',
            'font-size': '10px',
            'font-family': 'monospace',
            'text-valign': 'bottom',
            'text-margin-y': 5,
            'width': 34,
            'height': 34,
            'border-width': 2,
            'border-color': '#475569',
            'transition-property': 'background-color, border-color, width, height',
            'transition-duration': '0.2s'
          }
        },
        {
          selector: 'node[type="customer"]',
          style: {
            'background-color': '#1d4ed8',
            'border-color': '#60a5fa',
            'width': 42,
            'height': 42
          }
        },
        {
          selector: 'node[type="card"]',
          style: {
            'background-color': '#d97706',
            'border-color': '#fbbf24',
            'shape': 'round-rectangle',
            'width': 38,
            'height': 28
          }
        },
        {
          selector: 'node[type="card_compromised"]',
          style: {
            'background-color': '#b91c1c',
            'border-color': '#f87171',
            'shape': 'round-rectangle',
            'width': 38,
            'height': 28
          }
        },
        {
          selector: 'node[type="device"]',
          style: {
            'background-color': '#7e22ce',
            'border-color': '#c084fc',
            'shape': 'diamond',
            'width': 44,
            'height': 44
          }
        },
        {
          selector: 'node[type="txn_flagged"]',
          style: {
            'background-color': '#dc2626',
            'border-color': '#ef4444',
            'width': 40,
            'height': 40,
            'border-width': 3
          }
        },
        {
          selector: 'node[type="txn_testing"]',
          style: {
            'background-color': '#ea580c',
            'border-color': '#fb923c',
            'width': 26,
            'height': 26
          }
        },
        {
          selector: 'node[type="closed_case"]',
          style: {
            'background-color': '#0f766e',
            'border-color': '#2dd4bf',
            'shape': 'hexagon',
            'width': 40,
            'height': 40
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#475569',
            'target-arrow-color': '#64748b',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '8px',
            'color': '#94a3b8',
            'font-family': 'monospace',
            'text-rotation': 'autorotate',
            'text-margin-y': -6
          }
        },
        {
          selector: 'edge[label="SHARED_DEVICE"]',
          style: {
            'line-color': '#ef4444',
            'target-arrow-color': '#ef4444',
            'line-style': 'dashed',
            'width': 2.5
          }
        },
        {
          selector: 'edge[label="INVOLVES_DEVICE"]',
          style: {
            'line-color': '#a855f7',
            'target-arrow-color': '#a855f7',
            'line-style': 'dashed',
            'width': 2
          }
        },
        // Selected styles
        {
          selector: ':selected',
          style: {
            'border-width': 3,
            'border-color': '#38bdf8',
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8'
          }
        }
      ],
      layout: {
        name: 'cose',
        padding: 30,
        animate: false,
        idealEdgeLength: 90,
        nodeOverlap: 20
      }
    });

    // Handle node and edge clicks
    cyRef.current.on('tap', 'node', (evt) => {
      const node = evt.target;
      setSelectedElement({
        type: 'NODE',
        data: node.data()
      });

      // Highlight 1-hop neighborhood
      const cy = cyRef.current;
      cy.elements().removeClass('highlighted');
      node.neighborhood().add(node).addClass('highlighted');
    });

    cyRef.current.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      setSelectedElement({
        type: 'EDGE',
        data: edge.data()
      });
    });

    cyRef.current.on('tap', (evt) => {
      if (evt.target === cyRef.current) {
        setSelectedElement(null);
      }
    });

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [graphData]);

  // Toolbar Actions
  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current?.fit(null, 30);
  const handleResetLayout = () => {
    cyRef.current?.layout({ name: 'cose', padding: 30, animate: true }).run();
  };

  const handleFilter = (type) => {
    setActiveFilter(type);
    if (!cyRef.current) return;

    if (type === 'ALL') {
      cyRef.current.elements().show();
    } else {
      cyRef.current.nodes().forEach((node) => {
        if (node.data('type') === type) {
          node.show();
        } else {
          node.hide();
        }
      });
      // Show connecting edges between visible nodes
      cyRef.current.edges().forEach((edge) => {
        if (edge.source().visible() && edge.target().visible()) {
          edge.show();
        } else {
          edge.hide();
        }
      });
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3 relative">
      {/* Subgraph Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Share2 className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            TigerGraph Subgraph Explorer
          </h3>
          <span className="text-[11px] bg-slate-800 px-2 py-0.5 rounded font-mono text-slate-400">
            {nodeCount} Vertices • {edgeCount} Edges
          </span>
        </div>

        {/* Toolbar buttons */}
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={handleZoomIn}
            title="Zoom In"
            className="p-1 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded transition"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleZoomOut}
            title="Zoom Out"
            className="p-1 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded transition"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleFit}
            title="Fit to Screen"
            className="p-1 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded transition"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleResetLayout}
            title="Re-layout Graph"
            className="p-1 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Filter Chips by Node Type */}
      <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
        {[
          { id: 'ALL', label: 'All Entities' },
          { id: 'customer', label: 'Customers', color: 'text-blue-400' },
          { id: 'card', label: 'Cards', color: 'text-amber-400' },
          { id: 'device', label: 'Devices', color: 'text-purple-400' },
          { id: 'txn_flagged', label: 'Flagged Txns', color: 'text-red-400' },
          { id: 'closed_case', label: 'Closed Cases', color: 'text-teal-400' }
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => handleFilter(f.id)}
            className={`px-2 py-0.5 rounded transition font-semibold font-mono ${
              activeFilter === f.id
                ? 'bg-blue-600 text-slate-950 font-bold'
                : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Graph Canvas Container */}
      <div className="relative w-full h-84 bg-slate-950 rounded-lg border border-slate-800/80 overflow-hidden">
        <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

        {/* Node Detail Drawer / Floating Inspector */}
        {selectedElement && (
          <div className="absolute right-3 top-3 bottom-3 w-72 bg-slate-900/95 backdrop-blur border border-slate-700 rounded-lg p-3.5 shadow-2xl overflow-y-auto space-y-2.5 z-20">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-blue-400" />
                <span className="text-xs font-black uppercase tracking-wider text-slate-200">
                  {selectedElement.type === 'NODE' ? 'Entity Details' : 'Relationship'}
                </span>
              </div>
              <button
                onClick={() => setSelectedElement(null)}
                className="text-slate-400 hover:text-slate-200 p-0.5 rounded"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            {selectedElement.type === 'NODE' ? (
              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                    Identifier & Type
                  </span>
                  <p className="font-mono font-bold text-slate-100">{selectedElement.data.label}</p>
                  <span className="inline-block mt-0.5 px-1.5 py-0.2 text-[9px] font-mono rounded bg-slate-800 text-slate-300 uppercase">
                    {selectedElement.data.type}
                  </span>
                </div>

                {/* Node properties */}
                {selectedElement.data.properties && (
                  <div className="space-y-1 pt-1 border-t border-slate-800 text-[11px]">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">
                      Attributes
                    </span>
                    {Object.entries(selectedElement.data.properties).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-2 py-0.5">
                        <span className="text-slate-400 font-mono">{k}:</span>
                        <span className="text-slate-200 font-mono font-medium text-right truncate">
                          {String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                    Edge Type
                  </span>
                  <p className="font-mono font-bold text-emerald-400">
                    {selectedElement.data.label}
                  </p>
                </div>
                <div className="text-[11px] font-mono space-y-1">
                  <p>
                    <span className="text-slate-400">Source:</span> {selectedElement.data.source}
                  </p>
                  <p>
                    <span className="text-slate-400">Target:</span> {selectedElement.data.target}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
