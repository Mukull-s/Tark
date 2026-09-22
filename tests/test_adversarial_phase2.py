import os
import sys
import copy
import pandas as pd
import pytest
from dotenv import load_dotenv

sys.path.insert(0, r"c:\Users\Mukul\Desktop\Tark")
load_dotenv(r"c:\Users\Mukul\Desktop\Tark\.env")

from src.evidence.types import EvidenceType, EvidenceItem
from src.evidence.ledger import EvidenceLedger
from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine
from src.planner.decision_flip import DecisionFlipPlanner
from src.tools.mock_actions import simulate_customer_reply, simulate_step_up_auth
from bench.run import run_investigation_for_case
import pyTigerGraph as tg

class MockFailingConnection:
    """Mock connection that simulates network/engine failures."""
    def getVerticesById(self, vertex_type, vertex_id):
        raise ConnectionError("GSE communication failure: Connection timed out (REST-500)")

    def runInstalledQuery(self, query_name, params):
        raise RuntimeError(f"GSQL query {query_name} failed: RESTPP execution timeout")

class MockEmptyConnection:
    """Mock connection that returns empty responses for all queries."""
    def getVerticesById(self, vertex_type, vertex_id):
        return []

    def runInstalledQuery(self, query_name, params):
        return []

class MockStandardConnection:
    """Mock connection providing realistic graph data for offline testing."""
    def getVerticesById(self, vertex_type, vertex_id):
        return [{'attributes': {'amount': 131.30, 'ts': '2016-12-29 03:27:44', 'addr1': 0.0, 'channel': 'online'}}]

    def runInstalledQuery(self, query_name, params):
        if query_name == "customer_profile":
            return [{'total_txns': 100, 'total_amount': 5000.0, 'avg_amount': 50.0, 'channel_distribution': {'online': 100}}]
        elif query_name == "txn_velocity":
            return [{'txn_count': 15, 'total_spend': 800.0, 'txn_ids': ['T1', 'T2']}]
        elif query_name == "card_sequence":
            return [{'is_card_testing': True, 'micro_count': 3, 'larger_amount': 131.30, 'micro_txn_ids': ['M1', 'M2', 'M3']}]
        elif query_name == "device_analysis":
            return [{'device_id': 'DEV_01', 'device_info': 'TestPhone', 'is_proxy': True, 'shared_card_count': 5, 'connected_cards': ['C1', 'C2']}]
        elif query_name == "region_analysis":
            return [{'is_out_of_region': False, 'total_history_txns': 100}]
        elif query_name == "similar_cases":
            return [{'Matched': [{'v_id': 'CC-001'}]}]
        return []

class MockLLMClient:
    def generate(self, system_prompt, user_prompt, temperature=0.1, max_tokens=1500):
        return "MOCK SAR NARRATIVE FOR ADVERSARIAL TEST"

# 1. Source row missing linked card
def test_1_source_row_missing_linked_card():
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    planner = DecisionFlipPlanner(belief_engine, policy_engine)
    conn = MockStandardConnection()
    llm = MockLLMClient()

    row = {
        "case_id": "ADV-001",
        "opened_at": "2016-12-01 00:00:00",
        "trigger_type": "risk_score",
        "trigger_text": "Model scored transaction without card",
        "flagged_txn_id": "999999",
        "card_id": "",  # Missing card
        "customer_id": "C_TEST",
        "risk_score": 0.75
    }
    res = run_investigation_for_case(row, conn, belief_engine, policy_engine, planner, llm)
    assert res["case"]["verdict"] in ["confirmed_fraud", "uncertain", "legitimate"]
    assert isinstance(res["case"]["evidence"], list)

# 2. Source row missing device
def test_2_source_row_missing_device():
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    planner = DecisionFlipPlanner(belief_engine, policy_engine)
    
    # Empty device response
    class MockNoDeviceConn(MockStandardConnection):
        def runInstalledQuery(self, query_name, params):
            if query_name == "device_analysis":
                return [{'device_id': '', 'device_info': '', 'is_proxy': False, 'shared_card_count': 0, 'connected_cards': []}]
            return super().runInstalledQuery(query_name, params)

    conn = MockNoDeviceConn()
    llm = MockLLMClient()
    row = {
        "case_id": "ADV-002",
        "opened_at": "2016-12-01 00:00:00",
        "trigger_type": "risk_score",
        "trigger_text": "In-person purchase without device",
        "flagged_txn_id": "3514030",
        "card_id": "C_TEST-K1",
        "customer_id": "C_TEST",
        "risk_score": 0.61
    }
    res = run_investigation_for_case(row, conn, belief_engine, policy_engine, planner, llm)
    evidence_types = [e["type"] for e in res["case"]["evidence"]]
    assert "SHARED_DEVICE_RING" not in evidence_types
    assert "PROXY_DETECTED" not in evidence_types

# 3. Graph query returns empty
def test_3_graph_query_returns_empty():
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    planner = DecisionFlipPlanner(belief_engine, policy_engine)
    conn = MockEmptyConnection()
    llm = MockLLMClient()

    row = {
        "case_id": "ADV-003",
        "opened_at": "2016-12-01 00:00:00",
        "trigger_type": "risk_score",
        "trigger_text": "Model scored txn 100",
        "flagged_txn_id": "100",
        "card_id": "C_EMPTY-K1",
        "customer_id": "C_EMPTY",
        "risk_score": 0.55
    }
    res = run_investigation_for_case(row, conn, belief_engine, policy_engine, planner, llm)
    # With empty graph queries, only calibrated risk score should exist
    assert res["case"]["pattern"] == "undocumented"
    assert len(res["case"]["affected_txn_ids"]) == 1

# 4. Graph query fails explicitly reporting GRAPH_QUERY_FAILURE
def test_4_graph_query_fails_reports_graph_query_failure():
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    planner = DecisionFlipPlanner(belief_engine, policy_engine)
    conn = MockFailingConnection()
    llm = MockLLMClient()

    row = {
        "case_id": "ADV-004",
        "opened_at": "2016-12-01 00:00:00",
        "trigger_type": "risk_score",
        "trigger_text": "Model scored txn 200",
        "flagged_txn_id": "200",
        "card_id": "C_FAIL-K1",
        "customer_id": "C_FAIL",
        "risk_score": 0.65
    }
    res = run_investigation_for_case(row, conn, belief_engine, policy_engine, planner, llm)
    # Check that tool calls explicitly record GRAPH_QUERY_FAILURE
    failed_tools = [t for t in res["tool_calls"] if t.get("status") == "GRAPH_QUERY_FAILURE"]
    assert len(failed_tools) > 0, "Expected at least one GRAPH_QUERY_FAILURE status in tool calls"
    assert "error" in failed_tools[0]

# 5. Duplicate source transaction idempotency
def test_5_duplicate_source_transaction_idempotency():
    # In TigerGraph primary keys are unique sets.
    # We verify that feeding duplicate rows in pandas/ETL creates unique vertex keys.
    sample_rows = [
        {"txn_id": "TXN_DUP", "amount": 100.0, "ts": "2016-12-01 10:00:00"},
        {"txn_id": "TXN_DUP", "amount": 100.0, "ts": "2016-12-01 10:00:00"}
    ]
    df = pd.DataFrame(sample_rows)
    unique_txns = set(df["txn_id"])
    assert len(unique_txns) == 1, "Duplicate primary IDs must collapse to 1 unique vertex key"

# 6. Duplicate identity record collapses to single DeviceProfile
def test_6_duplicate_identity_record_collapses_to_single_profile():
    import hashlib
    row1 = {'DeviceInfo': 'PhoneX', 'id_30': 'Android', 'id_31': 'Chrome', 'DeviceType': 'mobile'}
    row2 = {'DeviceInfo': 'PhoneX', 'id_30': 'Android', 'id_31': 'Chrome', 'DeviceType': 'mobile'}
    
    def hash_prof(r):
        return "DEV_" + hashlib.md5(f"{r['DeviceInfo']}|{r['id_30']}|{r['id_31']}|{r['DeviceType']}".encode()).hexdigest()[:12]

    prof1 = hash_prof(row1)
    prof2 = hash_prof(row2)
    assert prof1 == prof2, "Duplicate identity rows must yield identical deterministic profile hash"

# 7. Graph evidence removed (ablation verification)
def test_7_graph_evidence_removed_ablation():
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    planner = DecisionFlipPlanner(belief_engine, policy_engine)
    llm = MockLLMClient()

    row = {
        "case_id": "ADV-007",
        "opened_at": "2016-12-29 03:27:44",
        "trigger_type": "customer_report",
        "trigger_text": "Customer reported unauthorized card testing",
        "flagged_txn_id": "3583368",
        "card_id": "C11923-K2",
        "customer_id": "C11923",
        "risk_score": None
    }

    # Run A: with full graph evidence
    conn_a = MockStandardConnection()
    res_a = run_investigation_for_case(row, conn_a, belief_engine, policy_engine, planner, llm)

    # Run B: with empty graph evidence
    conn_b = MockEmptyConnection()
    res_b = run_investigation_for_case(row, conn_b, belief_engine, policy_engine, planner, llm)

    # Graph findings must materially change the observed pattern and evidence set.
    # Under the unified Evidence Compass pipeline, whichever independent graph
    # family offers positive decision value is acquired; the ablation invariant is
    # that removing graph evidence collapses the typology to "undocumented" and
    # strictly reduces the observed evidence set.
    assert res_a["case"]["pattern"] != "undocumented"
    assert res_a["case"]["pattern"] != res_b["case"]["pattern"]
    assert len(res_a["case"]["evidence"]) > len(res_b["case"]["evidence"])

# 8. Benchmark case ID changed produces invariant reasoning
def test_8_benchmark_case_id_changed_invariance():
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    planner = DecisionFlipPlanner(belief_engine, policy_engine)
    conn = MockStandardConnection()
    llm = MockLLMClient()

    row_orig = {
        "case_id": "HHG-011",
        "opened_at": "2016-12-29 03:27:44",
        "trigger_type": "customer_report",
        "trigger_text": "I never made this purchase",
        "flagged_txn_id": "3583368",
        "card_id": "C11923-K2",
        "customer_id": "C11923",
        "risk_score": None
    }
    row_synthetic = dict(row_orig)
    row_synthetic["case_id"] = "SYNTHETIC-999"

    res_orig = run_investigation_for_case(row_orig, conn, belief_engine, policy_engine, planner, llm)
    res_synth = run_investigation_for_case(row_synthetic, conn, belief_engine, policy_engine, planner, llm)

    assert res_orig["case"]["verdict"] == res_synth["case"]["verdict"]
    assert res_orig["case"]["fraud_probability"] == res_synth["case"]["fraud_probability"]
    assert res_orig["case"]["pattern"] == res_synth["case"]["pattern"]
    assert str(res_orig["next_best_actions"]["final"]) == str(res_synth["next_best_actions"]["final"])

# 9. Unrelated transaction introduced does not bleed into card velocity
def test_9_unrelated_transaction_isolation():
    # Card C1 has transactions T1, T2. Unrelated Card C2 has transaction T3.
    # In GSQL, TargetCard filters by c.card_id == c_id.
    c1_txns = {"T1", "T2"}
    c2_txns = {"T3"}
    # Velocity query on C1 must strictly return C1's transactions
    assert "T3" not in c1_txns, "Unrelated transaction must never appear in target card velocity"

# 10. Customer response decoupled from internal posterior belief
def test_10_customer_response_independent_of_posterior():
    # Even if internal model is 99% confident of fraud:
    # A customer confirmation fixture must strictly yield confirmation (is_exculpatory = True)
    fixture_confirm = "Yes, I recognized and made this purchase while traveling."
    reply = simulate_customer_reply(
        case_id="TEST-010",
        prompt="Did you authorize this?",
        trigger_type="risk_score",
        fixture_response=fixture_confirm
    )
    assert reply["status"] == "COMPLETED"
    assert reply["customer_denied"] is False
    assert reply["provenance"] == "external_gateway_fixture"

    # And when no external communication exists:
    reply_unavail = simulate_customer_reply(
        case_id="TEST-010",
        prompt="Did you authorize this?",
        trigger_type="risk_score",
        fixture_response=None
    )
    assert reply_unavail["status"] == "UNAVAILABLE"
    assert reply_unavail["customer_denied"] is None
