import os
import sys
import pytest

sys.path.insert(0, r"c:\Users\Mukul\Desktop\Tark")

from src.graph.scope import GraphScope, GraphScopeStatus, ScopeResponse
from src.evidence.types import EvidenceType, EvidenceItem, EvidenceDirection
from src.evidence.ledger import EvidenceLedger
from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine
from src.planner.decision_flip import DecisionFlipPlanner
from bench.run import run_investigation_for_case

class MockScopeConnection:
    def __init__(self, mode="success"):
        self.mode = mode

    def getVerticesById(self, v_type, v_id):
        if self.mode == "fail":
            raise ConnectionError("RESTPP timeout")
        return [{'attributes': {'amount': 100.0, 'ts': '2016-12-01 00:00:00', 'addr1': 200.0, 'channel': 'online'}}]

    def runInstalledQuery(self, query_name, params):
        if self.mode == "fail":
            raise RuntimeError("GSQL execution error")
        elif self.mode == "empty":
            return []
        elif self.mode == "no_match_dict":
            return [{'Matched': []}]
        return [{'total_txns': 50, 'total_amount': 2500.0, 'avg_amount': 50.0}]

class MockLLM:
    def generate(self, system_prompt, user_prompt, temperature=0.1, max_tokens=1500):
        return "MOCK SAR"

# 1. GraphScope distinguishes all 4 statuses
def test_graph_scope_distinguishes_all_statuses():
    scope = GraphScope(in_scope_customers={"C_KNOWN_1", "C_KNOWN_2"})

    # Test DATA_OUT_OF_SCOPE
    res_out = scope.query_with_scope(
        conn=MockScopeConnection("success"),
        query_name="customer_profile",
        params={"cust_id": "C_UNKNOWN_999"},
        target_entity_type="Customer",
        target_entity_id="C_UNKNOWN_999"
    )
    assert res_out.status == GraphScopeStatus.DATA_OUT_OF_SCOPE
    assert "outside the currently ingested graph slice" in res_out.message

    # Test DATA_AVAILABLE
    res_avail = scope.query_with_scope(
        conn=MockScopeConnection("success"),
        query_name="customer_profile",
        params={"cust_id": "C_KNOWN_1"},
        target_entity_type="Customer",
        target_entity_id="C_KNOWN_1"
    )
    assert res_avail.status == GraphScopeStatus.DATA_AVAILABLE
    assert res_avail.data is not None

    # Test NO_MATCH
    res_empty = scope.query_with_scope(
        conn=MockScopeConnection("empty"),
        query_name="similar_cases",
        params={"target_pattern": "card_testing"},
        target_entity_type="Customer",
        target_entity_id="C_KNOWN_1"
    )
    assert res_empty.status == GraphScopeStatus.NO_MATCH

    # Test GRAPH_QUERY_FAILURE
    res_fail = scope.query_with_scope(
        conn=MockScopeConnection("fail"),
        query_name="customer_profile",
        params={"cust_id": "C_KNOWN_1"},
        target_entity_type="Customer",
        target_entity_id="C_KNOWN_1"
    )
    assert res_fail.status == GraphScopeStatus.GRAPH_QUERY_FAILURE
    assert "GSQL execution error" in res_fail.error_details

# 2. EvidenceLedger preserves provenance and attribution
def test_evidence_ledger_preserves_provenance():
    ledger = EvidenceLedger()
    item = EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        value=3,
        source="card_sequence",
        finding="Card testing detected: 3 micro-txns",
        provenance="transactions.csv:lines:3582142,3582175,3582624",
        source_entity="Card:C11923-K2",
        target_entity="Transaction:3583368",
        supporting_transaction_ids=["3582142", "3582175", "3582624"],
        supporting_entities=["C11923-K2"],
        lr=34.3,
        log_lr=3.535
    )
    ledger.add(item)

    assert len(ledger.items) == 1
    stored = ledger.items[0]
    assert stored.evidence_id.startswith("EVD-")
    assert stored.provenance == "transactions.csv:lines:3582142,3582175,3582624"
    assert stored.source_entity == "Card:C11923-K2"
    assert len(stored.supporting_transaction_ids) == 3

# 3. Evidence objects distinguish SUPPORTS, CONTRADICTS, and NEUTRAL
def test_evidence_directions():
    inculpatory = EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device_analysis",
        finding="Device shared across 52 cards",
        lr=14.2,
        log_lr=2.653
    )
    assert inculpatory.direction == EvidenceDirection.SUPPORTS
    assert inculpatory.is_exculpatory is False

    exculpatory = EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_CONFIRMATION,
        source="customer_verification_response",
        finding="Customer confirmed authorized charge",
        lr=0.05,
        log_lr=-2.996
    )
    assert exculpatory.direction == EvidenceDirection.CONTRADICTS
    assert exculpatory.is_exculpatory is True

    neutral = EvidenceItem(
        evidence_type=EvidenceType.BEHAVIORAL_BASELINE,
        source="customer_profile",
        finding="Customer has 100 historical txns",
        lr=1.0,
        log_lr=0.0
    )
    assert neutral.direction == EvidenceDirection.NEUTRAL
    assert neutral.is_exculpatory is False

# 4. No future-phase behavior introduced (Phase 3/4/5 gating)
def test_no_future_phase_behavior_present():
    import inspect
    from src.planner import decision_flip
    from src.tools import llm_client

    # Verify MCP server / GraphRAG / multi-agent components are not implemented prematurely
    tark_root = r"c:\Users\Mukul\Desktop\Tark"
    forbidden_future_files = [
        os.path.join(tark_root, "src", "agent", "react_loop.py")
    ]
    for p in forbidden_future_files:
        assert not os.path.exists(p), f"Future phase file {p} found before authorized phase"

# 5. Case IDs remain strictly invariant in behavior
def test_case_id_behavioral_invariance():
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    planner = DecisionFlipPlanner(belief_engine, policy_engine)
    conn = MockScopeConnection("success")
    llm = MockLLM()

    row_a = {
        "case_id": "HHG-001",
        "opened_at": "2016-12-05 01:55:28",
        "trigger_type": "risk_score",
        "trigger_text": "Model scored txn at 0.61",
        "flagged_txn_id": "3514030",
        "card_id": "C12382-K1",
        "customer_id": "C12382",
        "risk_score": 0.61
    }
    row_b = dict(row_a)
    row_b["case_id"] = "SYNTHETIC-999"

    res_a = run_investigation_for_case(row_a, conn, belief_engine, policy_engine, planner, llm)
    res_b = run_investigation_for_case(row_b, conn, belief_engine, policy_engine, planner, llm)

    assert res_a["case"]["verdict"] == res_b["case"]["verdict"]
    assert res_a["case"]["fraud_probability"] == res_b["case"]["fraud_probability"]
    assert str(res_a["next_best_actions"]) == str(res_b["next_best_actions"])
