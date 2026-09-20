import { SSEEvent, SSEEventType, InvestigationStep } from '../types/investigation';
import { ApiConfig } from './api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface SSEListenerOptions {
  onEvent: (event: SSEEvent) => void;
  onComplete?: () => void;
  onError?: (err: any) => void;
}

// Canonical sequence of investigation steps
export const CANONICAL_STEPS: Array<{
  event: SSEEventType;
  title: string;
  desc: string;
  tool?: string;
  status: "COMPLETED" | "ACTIVE" | "WAITING FOR EVIDENCE" | "FAILED" | "PENDING";
}> = [
  {
    event: "TRIGGER_RECEIVED",
    title: "Alert Trigger Received",
    desc: "Real-time fraud detection alert ingested into investigation queue.",
    status: "COMPLETED"
  },
  {
    event: "GSQL_TRAVERSAL",
    title: "TigerGraph Window Traversal",
    desc: "Executing card_window(window_hours=1)... Found 3 sub-$3 micro-authorizations.",
    tool: "tigergraph:card_window()",
    status: "COMPLETED"
  },
  {
    event: "GRAPH_CLUSTER",
    title: "Multi-Hop Hardware Linkage",
    desc: "Executing device_neighbors()... Device profile shared with card C00877-K1 and closed case CC-0141.",
    tool: "tigergraph:device_neighbors()",
    status: "COMPLETED"
  },
  {
    event: "POLICY_EVALUATION",
    title: "Policy Firewall Evaluation",
    desc: "Evaluating bank policy Rule R1: single weak pattern requires identity/transaction verification.",
    tool: "policy_firewall:evaluate()",
    status: "COMPLETED"
  },
  {
    event: "UNCERTAINTY_LOOP",
    title: "Adaptive Evidence Requested",
    desc: "Agent paused execution: dispatching customer_validation inquiry.",
    status: "WAITING FOR EVIDENCE"
  },
  {
    event: "EVIDENCE_INJECTED",
    title: "Additional Evidence Received",
    desc: "Customer denied purchases. Investigation confidence escalated from 0.72 to 0.86.",
    status: "COMPLETED"
  },
  {
    event: "NBA_FORMULATED",
    title: "Next Best Action Formulated",
    desc: "Final actions: BLOCK_CARD (L1), CREATE_CASE (auto), FILE_REPORT (L2).",
    status: "COMPLETED"
  },
  {
    event: "GRAPH_PERSISTED",
    title: "Case Persisted to Savanna",
    desc: "Investigation written to TigerGraph Savanna as CASE-2016-1187 (Case Memory).",
    tool: "tigergraph:persist_case()",
    status: "COMPLETED"
  }
];

export function subscribeToInvestigationStream(
  caseId: string,
  options: SSEListenerOptions
): () => void {
  // If mock mode is explicitly on, run client-side simulation
  if (ApiConfig.isMockMode()) {
    return simulateStream(caseId, options);
  }

  let eventSource: EventSource | null = null;
  let hasReceivedEvents = false;

  try {
    eventSource = new EventSource(`${API_BASE_URL}/api/cases/${caseId}/stream`);

    eventSource.onmessage = (event) => {
      try {
        hasReceivedEvents = true;
        const parsed = JSON.parse(event.data);
        const sseEvent: SSEEvent = {
          event: parsed.event as SSEEventType,
          data: parsed.data,
          timestamp: new Date().toISOString().substring(11, 19),
          status: parsed.event === 'UNCERTAINTY_LOOP' ? 'WAITING FOR EVIDENCE' : 'COMPLETED'
        };
        options.onEvent(sseEvent);

        if (parsed.event === 'GRAPH_PERSISTED') {
          eventSource?.close();
          options.onComplete?.();
        }
      } catch (err) {
        console.error('[Tark SSE] Failed to parse SSE message:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.warn('[Tark SSE] Connection error, switching to simulation fallback:', err);
      eventSource?.close();
      if (!hasReceivedEvents) {
        // Fallback to simulation if backend SSE did not emit
        simulateStream(caseId, options);
      } else {
        options.onError?.(err);
      }
    };
  } catch (err) {
    console.warn('[Tark SSE] Could not open EventSource, falling back to simulation:', err);
    return simulateStream(caseId, options);
  }

  return () => {
    if (eventSource) {
      eventSource.close();
    }
  };
}

// Fallback client simulation for offline demo reliability
function simulateStream(caseId: string, options: SSEListenerOptions): () => void {
  let isCancelled = false;
  let currentIdx = 0;

  const interval = setInterval(() => {
    if (isCancelled) {
      clearInterval(interval);
      return;
    }

    if (currentIdx < CANONICAL_STEPS.length) {
      const step = CANONICAL_STEPS[currentIdx];
      const sseEvent: SSEEvent = {
        event: step.event,
        data: step.desc,
        timestamp: new Date().toISOString().substring(11, 19),
        step: currentIdx + 1,
        status: step.status,
        tool: step.tool
      };
      options.onEvent(sseEvent);
      currentIdx++;
    } else {
      clearInterval(interval);
      options.onComplete?.();
    }
  }, 750);

  return () => {
    isCancelled = true;
    clearInterval(interval);
  };
}

// Helper to construct full replay steps from stream events or canonical defaults
export function buildInvestigationSteps(events: SSEEvent[]): InvestigationStep[] {
  return CANONICAL_STEPS.map((canonical, idx) => {
    const liveMatch = events.find((e) => e.event === canonical.event);
    return {
      stepNumber: idx + 1,
      totalSteps: CANONICAL_STEPS.length,
      title: canonical.title,
      eventType: canonical.event,
      description: liveMatch ? liveMatch.data : canonical.desc,
      toolCall: canonical.tool,
      status: liveMatch ? (liveMatch.status || "COMPLETED") : (idx === 0 ? "COMPLETED" : "PENDING"),
      timestamp: liveMatch?.timestamp || `00:0${idx + 1}:15`
    };
  });
}
