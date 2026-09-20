import pytest
from typing import Dict, Any, Optional

from src.evidence.ledger import EvidenceLedger, EvidenceItem
from src.evidence.types import EvidenceType, EvidenceDirection
from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine, ActionRole
from src.compass.evoi import EvidenceCompass
from src.tools.dispatcher import EvidenceToolDispatcher
from src.tools.graph_tools import CardSequenceTool, TxnVelocityTool
from src.graph.scope import GraphScopeStatus
from src.graph.connection import get_tigergraph_connection


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


# ==============================================================================
# 1. CardSequenceTool receives correct anchor_ts
# ==============================================================================

def test_card_sequence_tool_receives_correct_anchor_ts(dispatcher, tg_conn):
    """Verifies CardSequenceTool correctly executes when provided an anchor timestamp."""
    state = dispatcher.belief_engine.evaluate_investigation(
        investigation_id="TEST-SEQ-1",
        trigger={"timestamp": "2016-12-29 03:27:44", "flagged_txn_id": "3583368"},
        target_entities={"card_id": "C11923-K2"},
        ledger=EvidenceLedger()
    )

    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state,
        candidate_action="QUERY_CARD_SEQUENCE",
        parameters={"c_id": "C11923-K2", "anchor_ts": "2016-12-29 03:27:44", "window_hours": 24},
        context={"tg_conn": tg_conn}
    )

    assert res.status in ["SUCCESS", "DATA_AVAILABLE"]
    assert res.parameters["anchor_ts"] == "2016-12-29 03:27:44"
    assert res.evidence_item is not None
    assert res.evidence_item.evidence_type == EvidenceType.CARD_TESTING_SEQUENCE


# ==============================================================================
# 2. TxnVelocityTool receives correct target_ts
# ==============================================================================

def test_txn_velocity_tool_receives_correct_target_ts(dispatcher, tg_conn):
    """Verifies TxnVelocityTool correctly executes when provided a target timestamp."""
    state = dispatcher.belief_engine.evaluate_investigation(
        investigation_id="TEST-VEL-1",
        trigger={"timestamp": "2016-12-29 03:27:44", "flagged_txn_id": "3583368"},
        target_entities={"card_id": "C11923-K2"},
        ledger=EvidenceLedger()
    )

    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state,
        candidate_action="QUERY_TXN_VELOCITY",
        parameters={"c_id": "C11923-K2", "target_ts": "2016-12-29 03:27:44", "window_hours": 24},
        context={"tg_conn": tg_conn}
    )

    assert res.status in ["SUCCESS", "DATA_AVAILABLE"]
    assert res.parameters["target_ts"] == "2016-12-29 03:27:44"
    assert res.evidence_item is not None


# ==============================================================================
# 3. EvidenceCompass candidate templates contain temporal parameters
# ==============================================================================

def test_evidence_compass_candidate_template_contains_temporal_parameters(compass, belief_engine):
    """Verifies EvidenceCompass generates candidate templates with anchor_ts and target_ts from trigger state."""
    state = belief_engine.evaluate_investigation(
        investigation_id="TEST-TEMPLATES",
        trigger={"timestamp": "2016-12-29 03:27:44", "flagged_txn_id": "3583368"},
        target_entities={"card_id": "C11923-K2"},
        ledger=EvidenceLedger()
    )

    templates = compass.get_candidate_action_templates(
        state=state,
        target_entities=state.target_entities,
        flagged_txn_id="3583368"
    )

    seq_tmpl = [t for t in templates if t["action_id"] == "QUERY_CARD_SEQUENCE"][0]
    assert seq_tmpl["parameters"]["anchor_ts"] == "2016-12-29 03:27:44"
    assert seq_tmpl["parameters"]["c_id"] == "C11923-K2"

    vel_tmpl = [t for t in templates if t["action_id"] == "QUERY_TXN_VELOCITY"][0]
    assert vel_tmpl["parameters"]["target_ts"] == "2016-12-29 03:27:44"
    assert vel_tmpl["parameters"]["c_id"] == "C11923-K2"


# ==============================================================================
# 4. HHG-011 Equivalent Detects Micro-Authorizations with Valid Anchor Timestamp
# ==============================================================================

def test_hhg011_detects_card_testing_with_live_tigergraph(dispatcher, tg_conn, policy_engine):
    """Verifies that with temporal propagation, card_sequence finds micro-authorizations and outputs DECLINE_TRANSACTION."""
    state = dispatcher.belief_engine.evaluate_investigation(
        investigation_id="HHG-011",
        trigger={
            "trigger_type": "customer_report",
            "trigger_text": "Customer C11923 message: 'I never made this $131.30 purchase.'",
            "timestamp": "2016-12-29 03:27:44",
            "flagged_txn_id": "3583368"
        },
        target_entities={"card_id": "C11923-K2", "customer_id": "C11923"},
        ledger=EvidenceLedger()
    )

    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state,
        candidate_action="QUERY_CARD_SEQUENCE",
        context={"tg_conn": tg_conn}
    )

    assert res.status in ["SUCCESS", "DATA_AVAILABLE"]
    assert res.evidence_item is not None
    assert res.evidence_item.evidence_type == EvidenceType.CARD_TESTING_SEQUENCE
    assert res.evidence_item.lr == 34.3
    assert len(res.evidence_item.supporting_transaction_ids) >= 3

    # Policy evaluation
    actions = policy_engine.evaluate(
        fraud_probability=updated_state.belief_state["fraud_probability"],
        verdict="fraud",
        exposure_usd=131.30,
        ledger=EvidenceLedger(items=updated_state.evidence_items),
        case_context={"trigger_type": "customer_report"}
    )
    primary = PolicyEngine.get_primary_action(actions)
    assert primary is not None
    assert primary.action == "DECLINE_TRANSACTION"
    assert primary.role == ActionRole.PRIMARY
    assert any(a.action == "BLOCK_CARD" for a in actions)


# ==============================================================================
# 5. Wrong / Default Timestamp Is NOT Silently Substituted
# ==============================================================================

def test_wrong_or_default_timestamp_not_silently_substituted():
    """Verifies CardSequenceTool does not use hardcoded '2016-12-31 23:59:59' when anchor_ts is missing."""
    tool = CardSequenceTool()
    # Execute without anchor_ts in params or context
    res = tool.execute(params={"c_id": "C11923-K2"})
    assert res.status == "REJECTED"
    assert res.scope_status == GraphScopeStatus.GRAPH_QUERY_FAILURE
    assert "anchor_ts" in res.message


# ==============================================================================
# 6. Missing anchor_ts Returns Structured Tool Failure (NOT NO_MATCH)
# ==============================================================================

def test_missing_anchor_ts_returns_structured_failure_not_no_match():
    """Verifies missing temporal parameter returns a structured failure without manufacturing an LR=1 NO_MATCH item."""
    tool = CardSequenceTool()
    res = tool.execute(params={"c_id": "C12345"})
    assert res.status == "REJECTED"
    assert res.scope_status == GraphScopeStatus.GRAPH_QUERY_FAILURE
    assert res.evidence_item is None
    assert "Missing required parameter(s)" in res.message


# ==============================================================================
# 7. Missing target_ts Returns Structured Tool Failure (NOT NO_MATCH)
# ==============================================================================

def test_missing_target_ts_returns_structured_failure_not_no_match():
    """Verifies missing temporal parameter in TxnVelocityTool returns a structured failure."""
    tool = TxnVelocityTool()
    res = tool.execute(params={"c_id": "C12345"})
    assert res.status == "REJECTED"
    assert res.scope_status == GraphScopeStatus.GRAPH_QUERY_FAILURE
    assert res.evidence_item is None
    assert "Missing required parameter(s)" in res.message


# ==============================================================================
# 8. Valid Scoped Query Returning No Sequence Produces Genuine NO_MATCH
# ==============================================================================

def test_valid_scoped_query_returning_no_match_produces_genuine_no_match(dispatcher, tg_conn):
    """Verifies a genuinely clean card with a valid anchor_ts produces a valid NO_MATCH EvidenceItem."""
    # Query a card/timestamp where no card testing occurred
    state = dispatcher.belief_engine.evaluate_investigation(
        investigation_id="CLEAN-CARD-TEST",
        trigger={"timestamp": "2016-12-05 01:55:28", "flagged_txn_id": "3514030"},
        target_entities={"card_id": "C12382-K1"},
        ledger=EvidenceLedger()
    )

    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state,
        candidate_action="QUERY_CARD_SEQUENCE",
        parameters={"c_id": "C12382-K1", "anchor_ts": "2016-12-05 01:55:28", "window_hours": 24},
        context={"tg_conn": tg_conn}
    )

    assert res.status in ["SUCCESS", "NO_MATCH", "DATA_AVAILABLE"]
    assert res.evidence_item is not None
    assert res.evidence_item.evidence_type == EvidenceType.CARD_TESTING_SEQUENCE
    assert res.evidence_item.value == "NO_MATCH"
    assert res.evidence_item.lr == 1.0


# ==============================================================================
# 9. Case-ID Independence Verification
# ==============================================================================

def test_temporal_propagation_is_case_id_independent(dispatcher, tg_conn):
    """Verifies parameter propagation works identically for arbitrary custom case IDs."""
    custom_ids = ["CUSTOM-CASE-ALPHA", "CUSTOM-CASE-BETA", "INVESTIGATION-999"]
    for cid in custom_ids:
        state = dispatcher.belief_engine.evaluate_investigation(
            investigation_id=cid,
            trigger={"timestamp": "2016-12-29 03:27:44", "flagged_txn_id": "3583368"},
            target_entities={"card_id": "C11923-K2"},
            ledger=EvidenceLedger()
        )
        updated_state, res, trace = dispatcher.dispatch_and_update(
            state=state,
            candidate_action="QUERY_CARD_SEQUENCE",
            context={"tg_conn": tg_conn}
        )
        assert res.status in ["SUCCESS", "DATA_AVAILABLE"]
        assert res.evidence_item.lr == 34.3
