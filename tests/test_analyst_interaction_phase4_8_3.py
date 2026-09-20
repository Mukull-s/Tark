import pytest
from fastapi.testclient import TestClient
from src.api.main import app, INVESTIGATION_RUNS, load_cases_from_csv


@pytest.fixture
def client():
    return TestClient(app)


def test_analyst_approval_workflow(client):
    """Test that human analyst approval correctly mutates case status and records an audit event."""
    # 1. Run investigation for HHG-011 (which requires L1 analyst approval)
    run_resp = client.post("/api/investigations/HHG-011/run")
    assert run_resp.status_code == 200
    res_data = run_resp.json()
    assert res_data["status"] == "COMPLETED"

    # 2. Post formal approval
    decision_resp = client.post(
        "/api/investigations/HHG-011/decision",
        json={
            "decision": "APPROVE",
            "analyst_id": "ANALYST_MUKUL",
            "rationale": "Micro-auth sequence validated against cardholder report."
        }
    )
    assert decision_resp.status_code == 200
    dec_data = decision_resp.json()
    assert dec_data["case_status"] == "CLOSED"
    assert dec_data["event"]["type"] == "ACTION_APPROVED"
    assert "ANALYST_MUKUL" in dec_data["event"]["summary"]

    # 3. Check events stream contains ACTION_APPROVED
    events_resp = client.get("/api/investigations/HHG-011/events")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert any(e["type"] == "ACTION_APPROVED" for e in events)


def test_analyst_rejection_workflow(client):
    """Test that human analyst rejection correctly mutates case status and records an audit event."""
    run_resp = client.post("/api/investigations/HHG-005/run")
    assert run_resp.status_code == 200

    decision_resp = client.post(
        "/api/investigations/HHG-005/decision",
        json={
            "decision": "REJECT",
            "analyst_id": "ANALYST_LEAD",
            "rationale": "Known authorized business partner."
        }
    )
    assert decision_resp.status_code == 200
    dec_data = decision_resp.json()
    assert dec_data["case_status"] == "REJECTED"
    assert dec_data["event"]["type"] == "ACTION_REJECTED"

    events_resp = client.get("/api/investigations/HHG-005/events")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert any(e["type"] == "ACTION_REJECTED" for e in events)


def test_controlled_evidence_pivot_device(client):
    """Test controlled evidence pivot on Device entity executes authorized tool and updates belief."""
    # Run HHG-014
    run_resp = client.post("/api/investigations/HHG-014/run")
    assert run_resp.status_code == 200
    initial_p = run_resp.json()["result"]["run_result"]["final_state"]["fraud_probability"]

    # Pivot on device DEV_c5a193fe0d03
    pivot_resp = client.post(
        "/api/investigations/HHG-014/pivot",
        json={
            "entity_type": "Device",
            "entity_id": "DEV_c5a193fe0d03",
            "pivot_intent": "INVESTIGATE_DEVICE_RING",
            "analyst_id": "ANALYST_MUKUL",
            "reason": "Verify multi-card syndicate device cluster."
        }
    )
    assert pivot_resp.status_code == 200
    piv_data = pivot_resp.json()
    assert piv_data["status"] == "COMPLETED"
    assert piv_data["dispatched_action"] == "QUERY_DEVICE_ANALYSIS"
    assert "shared across" in piv_data["evidence_observed"]

    # Verify audit events sequence
    events = piv_data["result"]["events"]
    event_types = [e["type"] for e in events]
    assert "ANALYST_REQUEST" in event_types
    assert "EVIDENCE_REQUESTED" in event_types
    assert "EVIDENCE_RETURNED" in event_types
    assert "BELIEF_UPDATED" in event_types
    assert "DECISION_UPDATED" in event_types


def test_controlled_evidence_pivot_card(client):
    """Test controlled evidence pivot on Card entity."""
    run_resp = client.post("/api/investigations/HHG-011/run")
    assert run_resp.status_code == 200

    pivot_resp = client.post(
        "/api/investigations/HHG-011/pivot",
        json={
            "entity_type": "Card",
            "entity_id": "C11923-K2",
            "pivot_intent": "ANALYZE_CARD_SEQUENCE",
            "analyst_id": "ANALYST_01",
            "reason": "Deep sequence check"
        }
    )
    assert pivot_resp.status_code == 200
    piv_data = pivot_resp.json()
    assert piv_data["dispatched_action"] == "QUERY_CARD_SEQUENCE"
    assert "micro-authorizations" in piv_data["evidence_observed"]


def test_invalid_pivot_entity_rejected(client):
    """Test that unauthorized entity types are strictly rejected at the backend boundary."""
    run_resp = client.post("/api/investigations/HHG-011/run")
    assert run_resp.status_code == 200

    pivot_resp = client.post(
        "/api/investigations/HHG-011/pivot",
        json={
            "entity_type": "ArbitraryNonExistentEntity",
            "entity_id": "FAKE_123",
            "analyst_id": "ANALYST_01"
        }
    )
    assert pivot_resp.status_code == 400
    assert "Invalid entity type" in pivot_resp.json()["detail"]


def test_invalid_decision_rejected(client):
    """Test that invalid decision verbs are rejected."""
    run_resp = client.post("/api/investigations/HHG-011/run")
    assert run_resp.status_code == 200

    dec_resp = client.post(
        "/api/investigations/HHG-011/decision",
        json={
            "decision": "INVALID_DECISION_VERB",
            "analyst_id": "ANALYST_01"
        }
    )
    assert dec_resp.status_code == 400
    assert "Invalid analyst decision" in dec_resp.json()["detail"]
