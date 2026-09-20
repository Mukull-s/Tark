import {
  CaseAnswerFile,
  GraphData,
  BenchmarkCaseSummary,
  ApprovalRequest,
  ApprovalResponse,
  CaseMemoryItem
} from '../types/investigation';
import { BENCHMARK_CASES, getMockCase } from './mock/cases';
import { getMockGraph } from './mock/graphs';
import { getMockCaseMemory } from './mock/memory';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Global state / configuration for Mock vs Live Backend
let isMockMode = false;

export const ApiConfig = {
  isMockMode: () => isMockMode,
  setMockMode: (mock: boolean) => {
    isMockMode = mock;
    localStorage.setItem('tark_mock_mode', mock ? 'true' : 'false');
  },
  toggleMockMode: () => {
    ApiConfig.setMockMode(!isMockMode);
    return isMockMode;
  },
  init: () => {
    const saved = localStorage.getItem('tark_mock_mode');
    if (saved !== null) {
      isMockMode = saved === 'true';
    } else {
      // Default to false (try live backend first), fallback automatically on error
      isMockMode = false;
    }
  }
};

// Initialize config on load
ApiConfig.init();

export async function fetchBenchmarkCases(): Promise<BenchmarkCaseSummary[]> {
  if (isMockMode) {
    return BENCHMARK_CASES;
  }
  try {
    const res = await fetch(`${API_BASE_URL}/api/cases`, { signal: AbortSignal.timeout(2500) });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    return data && Array.isArray(data) && data.length > 0 ? data : BENCHMARK_CASES;
  } catch (err) {
    console.warn('[Tark API] Falling back to mock benchmark cases:', err);
    return BENCHMARK_CASES;
  }
}

export async function fetchCaseDetails(caseId: string): Promise<CaseAnswerFile> {
  if (isMockMode) {
    return getMockCase(caseId);
  }
  try {
    const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`[Tark API] Falling back to mock case for ${caseId}:`, err);
    return getMockCase(caseId);
  }
}

export async function fetchGraphData(caseId: string): Promise<GraphData> {
  if (isMockMode) {
    return getMockGraph(caseId);
  }
  try {
    const res = await fetch(`${API_BASE_URL}/api/graph/${caseId}`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    if (data && data.nodes && data.nodes.length > 0) {
      return data;
    }
    return getMockGraph(caseId);
  } catch (err) {
    console.warn(`[Tark API] Falling back to mock graph for ${caseId}:`, err);
    return getMockGraph(caseId);
  }
}

export async function fetchCaseMemory(caseId: string): Promise<CaseMemoryItem[]> {
  if (isMockMode) {
    return getMockCaseMemory(caseId);
  }
  try {
    const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/memory`, { signal: AbortSignal.timeout(2500) });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    return getMockCaseMemory(caseId);
  }
}

export async function triggerInvestigation(caseId: string): Promise<{ status: string; case_id: string }> {
  if (isMockMode) {
    return { status: "INVESTIGATING", case_id: caseId };
  }
  try {
    const res = await fetch(`${API_BASE_URL}/api/investigate/${caseId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('[Tark API] Mock trigger investigation:', err);
    return { status: "INVESTIGATING", case_id: caseId };
  }
}

export async function approvePolicyAction(req: ApprovalRequest): Promise<ApprovalResponse> {
  if (isMockMode) {
    return {
      status: "APPROVED",
      case_id: req.case_id,
      action: req.action,
      executed_at: new Date().toISOString().replace('T', ' ').substring(0, 19),
      message: `Action ${req.action} approved by human analyst (${req.route}) and executed.`
    };
  }
  try {
    const res = await fetch(`${API_BASE_URL}/api/actions/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req)
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('[Tark API] Falling back to mock action approval:', err);
    return {
      status: "APPROVED",
      case_id: req.case_id,
      action: req.action,
      executed_at: new Date().toISOString().replace('T', ' ').substring(0, 19),
      message: `Action ${req.action} approved by human analyst (${req.route}) and executed.`
    };
  }
}
