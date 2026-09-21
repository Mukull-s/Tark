import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.graph.connection import get_tigergraph_connection

@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)

@pytest.fixture(scope="module")
def tg_conn():
    conn = get_tigergraph_connection()
    assert conn is not None
    return conn

def test_golden_demo_flow_hhg014_cold_start(api_client, tg_conn):
    """Verifies Golden Demo Flow 1: HHG-014 Cold Start Syndicate Investigation."""
    # 1. Start investigation for HHG-014
    resp = api_client.post("/api/investigations/HHG-014/run")
    assert resp.status_code == 200, f"Run failed: {resp.text}"
    payload = resp.json()
    result = payload.get("result", payload)

    assert payload["investigation_id"] == "HHG-014"
    assert result["case"]["case_id"] == "HHG-014"
    assert result["case"]["trigger_type"] == "analyst_request"

    run_result = result["run_result"]
    assert "final_state" in run_result
    final_state = run_result["final_state"]
    assert final_state["fraud_probability"] > 0.0

    # 2. Verify EVOI trace endpoint exposure
    evoi_resp = api_client.get("/api/investigations/HHG-014/evoi-trace")
    assert evoi_resp.status_code == 200
    evoi_data = evoi_resp.json()
    assert evoi_data["investigation_id"] == "HHG-014"
    assert "traces" in evoi_data

    # 3. Verify SAR narrative and citation verification
    sar_resp = api_client.get("/api/investigations/HHG-014/sar")
    assert sar_resp.status_code == 200
    sar_data = sar_resp.json()
    assert "sar_narrative" in sar_data
    assert len(sar_data["sar_narrative"]) > 100
    assert "verified_citations" in sar_data

    # 4. Verify Analyst Sign-Off
    decision_resp = api_client.post(
        "/api/investigations/HHG-014/decision",
        json={"decision": "APPROVE", "analyst_id": "DEMO_ANALYST", "rationale": "Verified by lead investigator."}
    )
    assert decision_resp.status_code == 200
    assert decision_resp.json()["status"] == "SUCCESS"

def test_golden_demo_flow_unseen_transaction(api_client, tg_conn):
    """Verifies Golden Demo Flow 2: Arbitrary Unseen Transaction (3047878) dynamically resolved on TigerGraph."""
    # 1. Start investigation on arbitrary transaction 3047878
    resp = api_client.post("/api/investigations/transaction/3047878/run")
    assert resp.status_code == 200, f"Run failed: {resp.text}"
    payload = resp.json()
    result = payload.get("result", payload)

    assert result["case"]["flagged_txn_id"] == "3047878"
    assert result["case"]["card_id"] != ""
    assert result["case"]["customer_id"] != ""

    run_result = result["run_result"]
    assert run_result["step_count"] >= 0
    assert "final_state" in run_result
    assert run_result["primary_action"] is not None

    inv_id = payload["investigation_id"]

    # 2. Verify EVOI trace
    evoi_resp = api_client.get(f"/api/investigations/{inv_id}/evoi-trace")
    assert evoi_resp.status_code == 200

    # 3. Verify Grounded SAR
    sar_resp = api_client.get(f"/api/investigations/{inv_id}/sar")
    assert sar_resp.status_code == 200
    sar_data = sar_resp.json()
    assert sar_data["investigation_id"] == inv_id
    assert "sar_narrative" in sar_data

    # 4. Verify Controlled Pivot
    pivot_resp = api_client.post(
        f"/api/investigations/{inv_id}/pivot",
        json={
            "entity_type": "Card",
            "entity_id": result["case"]["card_id"],
            "pivot_intent": "ANALYZE_CARD_SEQUENCE",
            "analyst_id": "DEMO_ANALYST",
            "reason": "Live pivot verification"
        }
    )
    assert pivot_resp.status_code == 200
    assert pivot_resp.json()["status"] == "COMPLETED"
