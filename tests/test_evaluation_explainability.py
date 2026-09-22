"""Tests for Phase P3 — Evaluation & Explainability.

Verifies:
1. P3.1 Independent Evaluation Harness produces objective, untampered benchmark summaries.
2. P3.2 Evidence Compass EVOI trace exposure and candidate Net Decision Values.
3. P3.3 Grounded SAR generation and 3-way citation verification audit.
4. P3.4 Human analyst governance and controlled graph pivot workflow.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.graph.connection import get_tigergraph_connection
from evaluation.harness import EvaluationHarness, get_git_commit_sha


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


@pytest.fixture(scope="module")
def tg_conn():
    conn = get_tigergraph_connection()
    if conn is None:
        pytest.skip("TigerGraph Cloud connection unavailable.")
    return conn


def test_independent_evaluation_harness(tg_conn):
    """Verifies that EvaluationHarness executes cases and produces objective metrics without assumed outcomes."""
    harness = EvaluationHarness(tg_conn=tg_conn)

    # Evaluate 2 diverse benchmark cases with real ground truths
    sample_cases = [
        {
            "case_id": "HHG-001",
            "opened_at": "2016-12-05 01:55:28",
            "trigger_type": "risk_score",
            "trigger_text": "Real-time fraud score: 0.61",
            "flagged_txn_id": "3514030",
            "card_id": "C12382-K1",
            "customer_id": "C12382",
            "risk_score": 0.61,
            "expected_primary_action": "MONITOR_CARD"
        },
        {
            "case_id": "HHG-003",
            "opened_at": "2016-12-07 14:15:32",
            "trigger_type": "customer_report",
            "trigger_text": "Customer reported fraudulent charge of $49.00",
            "flagged_txn_id": "3530164",
            "card_id": "C12049-K1",
            "customer_id": "C12049",
            "risk_score": None,
            "expected_primary_action": "BLOCK_CARD"
        }
    ]

    result = harness.run_benchmark(cases_input=sample_cases, benchmark_name="Harness-Verification-Test")
    assert result.total_cases == 2
    assert result.commit_sha == get_git_commit_sha()
    assert result.nba_agreement_count == 2
    assert result.nba_agreement_pct == 100.0
    assert len(result.mismatches) == 0
    assert len(result.tool_distribution) > 0


def test_evoi_trace_endpoint(api_client, tg_conn):
    """Verifies that GET /api/investigations/{id}/evoi-trace exposes candidate EVOI and MCP telemetry."""
    # First ensure case is run
    run_resp = api_client.post("/api/investigations/HHG-001/run")
    assert run_resp.status_code == 200

    resp = api_client.get("/api/investigations/HHG-001/evoi-trace")
    assert resp.status_code == 200

    data = resp.json()
    assert data["investigation_id"] == "HHG-001"
    assert data["step_count"] >= 1

    trace0 = data["traces"][0]
    assert "candidate_net_decision_values" in trace0
    assert isinstance(trace0["candidate_net_decision_values"], dict)
    assert len(trace0["candidate_net_decision_values"]) > 0
    assert "mcp_telemetry" in trace0
    assert trace0["mcp_telemetry"] is not None
    assert "duration_ms" in trace0["mcp_telemetry"]


def test_grounded_sar_endpoint(api_client, tg_conn):
    """Verifies that GET /api/investigations/{id}/sar exposes the 7-section SAR with verified citations."""
    resp = api_client.get("/api/investigations/HHG-001/sar")
    assert resp.status_code == 200

    data = resp.json()
    assert data["investigation_id"] == "HHG-001"
    assert data["filing_ready"] is True
    assert "31 CFR § 1020.320" in data["regulatory_framework"]
    assert len(data["sar_narrative"]) > 200

    citations = data["verified_citations"]
    assert len(citations["evidence_citations"]) >= 1
    assert any("EVD-" in cit for cit in citations["evidence_citations"])


def test_analyst_decision_governance(api_client, tg_conn):
    """Verifies human analyst approval lifecycle and event generation."""
    # Run an investigation requiring review
    api_client.post("/api/investigations/HHG-003/run")

    # Analyst approves recommendation
    payload = {
        "decision": "APPROVE",
        "analyst_id": "CHIEF_RISK_OFFICER",
        "rationale": "Verified customer phone outreach match."
    }
    resp = api_client.post("/api/investigations/HHG-003/decision", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"
    assert resp.json()["case_status"] == "CLOSED"

    # Events must reflect analyst action
    events_resp = api_client.get("/api/investigations/HHG-003/events")
    events = events_resp.json()
    event_types = [e["type"] for e in events]
    assert "ACTION_APPROVED" in event_types


def test_analyst_controlled_pivot(api_client, tg_conn):
    """Verifies analyst-initiated controlled graph pivot executes through dispatcher."""
    api_client.post("/api/investigations/HHG-001/run")

    pivot_payload = {
        "entity_type": "Card",
        "entity_id": "C12382-K1",
        "pivot_intent": "ANALYZE_CARD_SEQUENCE",
        "analyst_id": "SENIOR_ANALYST_07",
        "reason": "Deep sequence check on card account."
    }
    resp = api_client.post("/api/investigations/HHG-001/pivot", json=pivot_payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["dispatched_action"] in ["QUERY_CARD_SEQUENCE", "ANALYZE_CARD_SEQUENCE"]
    assert "result" in data


def test_benchmark_summary_endpoint(api_client):
    """Verifies GET /api/benchmark/summary returns authoritative immutable evaluation artifact."""
    resp = api_client.get("/api/benchmark/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["total_cases"] == 20
    assert "commit_sha" in summary
    assert "nba_agreement_pct" in summary
    assert "gate_pass_pct" in summary
    assert "tool_distribution" in summary
    assert summary["nba_agreement_pct"] > 90.0

