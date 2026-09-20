import os
import pytest
from typing import Dict, Any

from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceItem, EvidenceType, EvidenceDirection
from src.belief.calibration import PriorProfile
from src.belief.state import InvestigationState, DecisionState
from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine
from src.compass.evoi import EvidenceCompass
from src.graph.scope import GraphScope, GraphScopeStatus
from src.graph.connection import get_tigergraph_connection
from src.tools.base import EvidenceTool, ToolExecutionResult, EvidenceExecutionTrace
from src.tools.dispatcher import EvidenceToolDispatcher
from src.tools.normalizer import EvidenceNormalizer

@pytest.fixture
def belief_engine():
    return BeliefEngine()

@pytest.fixture
def policy_engine():
    return PolicyEngine()

@pytest.fixture
def compass(belief_engine, policy_engine):
    return EvidenceCompass(belief_engine, policy_engine)

@pytest.fixture
def dispatcher(belief_engine):
    return EvidenceToolDispatcher(belief_engine)

@pytest.fixture
def tg_conn():
    return get_tigergraph_connection()

@pytest.fixture
def generic_initial_state(belief_engine):
    """Generic initial investigation state with only model score observed."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="realtime_model",
        finding="Model scored transaction at 0.61",
        lr=2.4,
        log_lr=0.875,
        details={"risk_score": 0.61}
    ))
    
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-GENERIC-001",
        trigger={
            "trigger_type": "risk_score",
            "flagged_txn_id": "3478561",
            "txn_addr1": 299.0,
            "timestamp": "2016-11-22 20:11:00"
        },
        target_entities={
            "card_id": "C11923-K2",
            "customer_id": "C12382",
            "flagged_txn_id": "3478561"
        },
        ledger=ledger,
        prior_p=0.43634  # Initial fraud probability 0.6500
    )
    return state

# 1. Device Query Execution Test
def test_device_query_execution(compass, dispatcher, generic_initial_state, tg_conn):
    state = generic_initial_state
    assert state.uncertainty.evidence_coverage == 0.20
    assert state.decision_gate_passed is False
    
    # 1. Compass evaluates and recommends action
    rec = compass.evaluate_evidence_compass(state, exposure_usd=100.0)
    assert rec.top_recommendation is not None
    action_id = rec.top_recommendation.action_id  # QUERY_DEVICE_ANALYSIS
    assert action_id == "QUERY_DEVICE_ANALYSIS"
    
    # 2. Dispatcher executes real tool
    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state,
        candidate_action=rec.top_recommendation,
        context={"tg_conn": tg_conn}
    )
    
    # 3. Verify tool execution result
    assert res.status in ["SUCCESS", "DATA_AVAILABLE"]
    assert res.evidence_item is not None
    assert res.evidence_item.evidence_type == EvidenceType.SHARED_DEVICE_RING
    assert res.evidence_item.lr == 14.2
    assert res.evidence_item.graph_query == "device_analysis"
    
    # 4. Verify Evidence Ledger and InvestigationState updated
    assert len(updated_state.evidence_items) == 2
    assert updated_state.uncertainty.evidence_coverage >= 0.40
    assert updated_state.belief_state["fraud_probability"] > 0.90
    assert updated_state.decision_gate_passed is True
    
    # 5. Verify Execution Trace
    assert trace.execution_status in ["SUCCESS", "DATA_AVAILABLE"]
    assert trace.belief_before == 0.65
    assert trace.belief_after > 0.90
    assert trace.coverage_before == 0.20
    assert trace.coverage_after >= 0.40
    assert trace.gate_passed_before is False
    assert trace.gate_passed_after is True

# 2. Card Sequence Execution Test
def test_card_sequence_execution(dispatcher, generic_initial_state, tg_conn):
    state = generic_initial_state
    
    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state,
        candidate_action="QUERY_CARD_SEQUENCE",
        parameters={
            "c_id": "C11923-K2",
            "anchor_ts": "2016-12-29 03:27:44",
            "window_hours": 24
        },
        context={"tg_conn": tg_conn}
    )
    
    assert res.status in ["SUCCESS", "DATA_AVAILABLE"]
    assert res.evidence_item is not None
    assert res.evidence_item.evidence_type == EvidenceType.CARD_TESTING_SEQUENCE
    assert res.evidence_item.lr == 34.3
    assert len(res.evidence_item.supporting_transaction_ids) >= 3
    assert updated_state.belief_state["fraud_probability"] > 0.95
    assert updated_state.decision_gate_passed is True

# 3. NO_MATCH Semantics Test
def test_no_match_semantics(dispatcher, generic_initial_state):
    state = generic_initial_state
    initial_prob = state.belief_state["fraud_probability"]
    
    # Mock a clean query result: single clean device
    clean_raw_data = [{
        "device_id": "DEV_CLEAN_12345",
        "is_proxy": False,
        "shared_card_count": 1,
        "connected_cards": ["C11923-K2"]
    }]
    
    item = EvidenceNormalizer.normalize(
        action_id="QUERY_DEVICE_ANALYSIS",
        tool_name="device_analysis",
        scope_status=GraphScopeStatus.NO_MATCH,
        raw_data=clean_raw_data,
        target_entities=state.target_entities
    )
    
    assert item.value == "NO_MATCH"
    assert item.lr == 1.0
    assert item.log_lr == 0.0
    assert item.direction == EvidenceDirection.NEUTRAL
    assert item.details.get("scope_status") == "NO_MATCH"
    
    # Ingesting NO_MATCH does not shift belief probability
    ledger = EvidenceLedger(items=list(state.evidence_items) + [item])
    new_state = dispatcher.belief_engine.evaluate_investigation(
        investigation_id=state.investigation_id,
        trigger=state.trigger,
        target_entities=state.target_entities,
        ledger=ledger,
        prior_p=state.belief_state.get("prior_prob")
    )
    assert abs(new_state.belief_state["fraud_probability"] - initial_prob) < 1e-3

# 4. DATA_OUT_OF_SCOPE Execution Test
def test_data_out_of_scope_execution(dispatcher, generic_initial_state, tg_conn):
    state = generic_initial_state
    initial_prob = state.belief_state["fraud_probability"]
    
    # Restrict graph scope to non-existent portfolio
    restricted_scope = GraphScope(in_scope_cards={"CARD-NON-EXISTENT"})
    
    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state,
        candidate_action="QUERY_CARD_SEQUENCE",
        parameters={"c_id": "C11923-K2"},
        context={"tg_conn": tg_conn, "graph_scope": restricted_scope}
    )
    
    assert res.scope_status == GraphScopeStatus.DATA_OUT_OF_SCOPE
    assert res.evidence_item is not None
    assert res.evidence_item.value == "DATA_OUT_OF_SCOPE"
    assert res.evidence_item.lr == 1.0
    assert res.evidence_item.log_lr == 0.0
    
    # Probability remains unshifted
    assert abs(updated_state.belief_state["fraud_probability"] - initial_prob) < 1e-3
    # Epistemic uncertainty increases and missing info is recorded
    assert updated_state.uncertainty.epistemic_uncertainty > 0.0
    assert any(m.reason == "DATA_OUT_OF_SCOPE" for m in updated_state.missing_information)

# 5. GRAPH_QUERY_FAILURE Handling Test
def test_graph_query_failure_handling(dispatcher, generic_initial_state):
    state = generic_initial_state
    initial_prob = state.belief_state["fraud_probability"]
    
    # Pass conn=None to force connection failure
    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state,
        candidate_action="QUERY_DEVICE_ANALYSIS",
        parameters={"t_id": "3478561"},
        context={"tg_conn": None}
    )
    
    assert res.scope_status == GraphScopeStatus.GRAPH_QUERY_FAILURE
    assert res.evidence_item is not None
    assert res.evidence_item.value == "GRAPH_QUERY_FAILURE"
    assert res.evidence_item.lr == 1.0
    assert res.evidence_item.log_lr == 0.0
    
    # Coherent state preserved with zero log-odds shift
    assert abs(updated_state.belief_state["fraud_probability"] - initial_prob) < 1e-3
    assert trace.execution_status == "GRAPH_QUERY_FAILURE"
    assert any(m.reason == "GRAPH_QUERY_FAILURE" for m in updated_state.missing_information)

# 6. Provenance Tracking Test
def test_provenance_tracking(dispatcher, generic_initial_state, tg_conn):
    state = generic_initial_state
    
    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state,
        candidate_action="QUERY_DEVICE_ANALYSIS",
        parameters={"t_id": "3478561"},
        context={"tg_conn": tg_conn}
    )
    
    item = res.evidence_item
    assert item is not None
    assert item.source == "tigergraph_query:device_analysis"
    assert item.graph_query == "device_analysis"
    assert item.provenance == "TigerGraph GSQL device_analysis"
    assert item.target_entity == "3478561"
    assert item.timestamp is not None
    assert "shared_count" in item.details

# 7. Duplicate Execution Prevention (Idempotency)
def test_duplicate_execution_prevention(dispatcher, generic_initial_state, tg_conn):
    state = generic_initial_state
    
    # First execution
    state_after_1, res_1, trace_1 = dispatcher.dispatch_and_update(
        state=state,
        candidate_action="QUERY_DEVICE_ANALYSIS",
        parameters={"t_id": "3478561"},
        context={"tg_conn": tg_conn}
    )
    count_after_1 = len(state_after_1.evidence_items)
    assert count_after_1 == 2
    assert res_1.status in ["SUCCESS", "DATA_AVAILABLE"]
    
    # Second execution of the exact same action and parameters
    state_after_2, res_2, trace_2 = dispatcher.dispatch_and_update(
        state=state_after_1,
        candidate_action="QUERY_DEVICE_ANALYSIS",
        parameters={"t_id": "3478561"},
        context={"tg_conn": tg_conn}
    )
    count_after_2 = len(state_after_2.evidence_items)
    
    # Duplicate suppressed
    assert count_after_2 == count_after_1
    assert res_2.status == "DUPLICATE"
    assert trace_2.execution_status == "DUPLICATE"
    assert "Suppressed duplicate" in trace_2.message

# 8. Invalid / Unregistered Tool Rejection
def test_invalid_unregistered_tool(dispatcher, generic_initial_state):
    state = generic_initial_state
    
    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state,
        candidate_action="UNREGISTERED_DANGEROUS_TOOL",
        parameters={"cmd": "drop database"}
    )
    
    assert res.status == "REJECTED"
    assert trace.execution_status == "REJECTED"
    assert "not a registered approved evidence tool" in res.message
    # State remains unmodified
    assert len(updated_state.evidence_items) == len(state.evidence_items)

# 9. Zero Benchmark Leakage Test
def test_zero_benchmark_leakage():
    tools_dir = os.path.dirname(os.path.dirname(__file__))
    src_tools = os.path.join(tools_dir, "src", "tools")
    
    prohibited_tokens = ["HHG-", "HHGOA", "benchmark_answer", "case_pack_key"]
    for root, _, files in os.walk(src_tools):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as fp:
                    content = fp.read()
                    for token in prohibited_tokens:
                        assert token not in content, f"Leakage: prohibited token '{token}' in {f}"

# 10. End-to-End Evidence Compass Execution Bridge (STEP 13 Integration Test)
def test_end_to_end_evidence_compass_execution_bridge(compass, dispatcher, belief_engine, tg_conn):
    """Complete E2E integration test:
    InvestigationState -> Evidence Compass -> Select Top Action -> Dispatcher ->
    Real TigerGraph -> Normalize -> Ledger -> State Update -> Decision Gate Reevaluation.
    """
    # 1. Initialize generic investigation
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="realtime_model",
        finding="Model score 0.61",
        lr=2.4,
        log_lr=0.875
    ))
    
    initial_state = belief_engine.evaluate_investigation(
        investigation_id="INV-E2E-TEST-001",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "3478561"},
        target_entities={"card_id": "C11923-K2", "customer_id": "C12382", "flagged_txn_id": "3478561"},
        ledger=ledger,
        prior_p=0.43634
    )
    
    assert initial_state.belief_state["fraud_probability"] == 0.65
    assert initial_state.uncertainty.evidence_coverage == 0.20
    assert initial_state.decision_gate_passed is False
    assert initial_state.decision_state == DecisionState.INSUFFICIENT_EVIDENCE
    
    # 2. Compass evaluates all candidates and ranks by Net Decision Value
    rec = compass.evaluate_evidence_compass(initial_state, exposure_usd=100.0)
    assert rec.top_recommendation is not None
    top_cand = rec.top_recommendation
    assert top_cand.action_id == "QUERY_DEVICE_ANALYSIS"
    assert top_cand.net_decision_value > 0.0
    
    # 3. Dispatcher executes top candidate against real TigerGraph
    final_state, res, trace = dispatcher.dispatch_and_update(
        state=initial_state,
        candidate_action=top_cand,
        context={"tg_conn": tg_conn}
    )
    
    # 4. Validate complete state transition
    assert res.status in ["SUCCESS", "DATA_AVAILABLE"]
    assert res.evidence_item is not None
    assert res.evidence_item.evidence_type == EvidenceType.SHARED_DEVICE_RING
    
    # 5. Validate Decision Gate passed and terminal determination enabled
    assert final_state.decision_gate_passed is True
    assert final_state.uncertainty.evidence_coverage >= 0.40
    assert final_state.belief_state["fraud_probability"] > 0.90
    assert final_state.decision_state == DecisionState.DECIDED
    
    # 6. Compass evaluated again on updated state
    rec_after = compass.evaluate_evidence_compass(final_state, exposure_usd=100.0)
    assert rec_after.current_decision_state == "DECIDED"
    assert rec_after.current_primary_action in ["CREATE_CASE", "BLOCK_CARD"]
    
    # If a refinement action remains with marginal value (e.g. card sequence), execute it to reach full saturation
    if not rec_after.should_stop_gathering:
        final_state_2, res_2, trace_2 = dispatcher.dispatch_and_update(
            state=final_state,
            candidate_action=rec_after.top_recommendation,
            context={"tg_conn": tg_conn}
        )
        assert res_2.status in ["SUCCESS", "DATA_AVAILABLE"]
        rec_after_2 = compass.evaluate_evidence_compass(final_state_2, exposure_usd=100.0)
        assert rec_after_2.should_stop_gathering is True
