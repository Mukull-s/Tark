import pytest
from typing import Dict, Any

from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceItem, EvidenceType, EvidenceDirection
from src.belief.calibration import (
    EvidenceFamily,
    PriorProfile,
    get_calibrated_lr
)
from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine
from src.graph.scope import GraphScopeStatus
from src.tools.external_tools import CustomerVerificationTool, StepUpAuthTool
from src.tools.mock_actions import simulate_customer_reply, simulate_step_up_auth
from src.tools.normalizer import EvidenceNormalizer

@pytest.fixture
def belief_engine():
    return BeliefEngine()

@pytest.fixture
def policy_engine():
    return PolicyEngine()

@pytest.fixture
def base_context():
    return {
        "investigation_id": "INV-TEST-CUST-001",
        "case_id": "CASE-TEST-001",
        "customer_id": "CUST_999",
        "card_id": "CARD_888",
        "flagged_txn_id": "TXN_777",
        "trigger_type": "risk_score",
        "exposure_usd": 1500.0
    }

# ==============================================================================
# Test 1 & 2: Customer Unavailable and Timeout
# ==============================================================================

def test_1_customer_unavailable_does_not_produce_customer_confirmation(base_context):
    """VERIFY_WITH_CUSTOMER when customer is UNAVAILABLE must produce
    CUSTOMER_COMMUNICATION_UNAVAILABLE, NOT CUSTOMER_CONFIRMATION.
    """
    tool = CustomerVerificationTool()
    # Default execution without response fixture yields UNAVAILABLE
    res = tool.execute(params={"case_id": base_context["case_id"]}, context=base_context)
    
    assert res.status == "UNAVAILABLE"
    item = res.evidence_item
    assert item is not None
    assert item.evidence_type == EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE
    assert item.evidence_type != EvidenceType.CUSTOMER_CONFIRMATION
    assert item.lr == 1.0
    assert item.log_lr == 0.0
    assert item.direction == EvidenceDirection.NEUTRAL
    assert item.is_exculpatory is False
    assert item.value == "NO_MATCH"


def test_2_customer_timeout_does_not_produce_customer_confirmation(base_context):
    """VERIFY_WITH_CUSTOMER when tool times out must produce
    CUSTOMER_COMMUNICATION_UNAVAILABLE, NOT CUSTOMER_CONFIRMATION.
    """
    # Normalizing a raw TIMEOUT gateway response
    raw_timeout = {
        "status": "TIMEOUT",
        "reply": "Gateway timed out waiting for IVR response",
        "customer_denied": None,
        "provenance": "external_gateway_timeout"
    }
    item = EvidenceNormalizer.normalize(
        action_id="VERIFY_WITH_CUSTOMER",
        tool_name="simulate_customer_reply",
        scope_status=GraphScopeStatus.NO_MATCH,
        raw_data=raw_timeout,
        target_entities={"customer_id": base_context["customer_id"], "flagged_txn_id": base_context["flagged_txn_id"]},
        context=base_context
    )
    
    assert item.evidence_type == EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE
    assert item.evidence_type != EvidenceType.CUSTOMER_CONFIRMATION
    assert item.lr == 1.0
    assert item.log_lr == 0.0
    assert item.direction == EvidenceDirection.NEUTRAL
    assert item.is_exculpatory is False


def test_2b_step_up_auth_expired_does_not_produce_customer_confirmation(base_context):
    """STEP_UP_AUTH when challenge expires must produce
    CUSTOMER_COMMUNICATION_UNAVAILABLE, NOT CUSTOMER_CONFIRMATION.
    """
    tool = StepUpAuthTool()
    res = tool.execute(params={"case_id": base_context["case_id"]}, context=base_context)
    
    assert res.status == "TIMEOUT"
    item = res.evidence_item
    assert item is not None
    assert item.evidence_type == EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE
    assert item.evidence_type != EvidenceType.CUSTOMER_CONFIRMATION
    assert item.lr == 1.0
    assert item.log_lr == 0.0
    assert item.direction == EvidenceDirection.NEUTRAL
    assert item.is_exculpatory is False


# ==============================================================================
# Test 3: Actual Customer Responses (Confirmation & Denial) Continue Working
# ==============================================================================

def test_3a_actual_customer_confirmation_produces_valid_exculpatory_evidence(base_context):
    """When a customer actually confirms the transaction as legitimate,
    it must produce valid CUSTOMER_CONFIRMATION evidence (LR=0.05, is_exculpatory=True).
    """
    tool = CustomerVerificationTool()
    res = tool.execute(
        params={
            "case_id": base_context["case_id"],
            "fixture_response": "Yes, I authorized this charge and made the purchase myself."
        },
        context=base_context
    )
    
    assert res.status == "COMPLETED"
    item = res.evidence_item
    assert item is not None
    assert item.evidence_type == EvidenceType.CUSTOMER_CONFIRMATION
    assert item.is_exculpatory is True
    assert item.lr == 0.05
    assert item.log_lr == -2.996
    assert item.direction == EvidenceDirection.CONTRADICTS


def test_3b_actual_customer_denial_produces_valid_inculpatory_evidence(base_context):
    """When a customer actually disputes/denies the transaction,
    it must produce valid CUSTOMER_DENIAL evidence (LR=18.5, is_exculpatory=False).
    """
    tool = CustomerVerificationTool()
    res = tool.execute(
        params={
            "case_id": base_context["case_id"],
            "fixture_response": "No, I did not make or authorize this transaction. This is fraudulent."
        },
        context=base_context
    )
    
    assert res.status == "COMPLETED"
    item = res.evidence_item
    assert item is not None
    assert item.evidence_type == EvidenceType.CUSTOMER_DENIAL
    assert item.is_exculpatory is False
    assert item.lr == 18.5
    assert item.log_lr == 2.918
    assert item.direction == EvidenceDirection.SUPPORTS


def test_3c_actual_step_up_auth_pass_and_fail(base_context):
    """Step-up auth success produces CUSTOMER_CONFIRMATION; failure produces CUSTOMER_DENIAL."""
    tool = StepUpAuthTool()
    
    # Success
    res_pass = tool.execute(params={"case_id": base_context["case_id"], "fixture_result": True}, context=base_context)
    assert res_pass.status == "COMPLETED"
    assert res_pass.evidence_item.evidence_type == EvidenceType.CUSTOMER_CONFIRMATION
    assert res_pass.evidence_item.is_exculpatory is True
    
    # Failure
    res_fail = tool.execute(params={"case_id": base_context["case_id"], "fixture_result": False}, context=base_context)
    assert res_fail.status == "COMPLETED"
    assert res_fail.evidence_item.evidence_type == EvidenceType.CUSTOMER_DENIAL
    assert res_fail.evidence_item.is_exculpatory is False


# ==============================================================================
# Test 4: R3 Policy Protection
# ==============================================================================

def test_4a_unavailable_customer_does_not_trigger_r3(policy_engine, base_context):
    """An unavailable/timeout customer verification must NOT trigger Rule R3 (CLOSE_NO_FRAUD)."""
    tool = CustomerVerificationTool()
    res = tool.execute(params={"case_id": base_context["case_id"]}, context=base_context)
    
    ledger = EvidenceLedger()
    ledger.add(res.evidence_item)
    
    # Evaluate policy under high fraud probability (0.90) and FRAUD verdict
    actions = policy_engine.evaluate(
        fraud_probability=0.90,
        verdict="FRAUD",
        exposure_usd=base_context["exposure_usd"],
        ledger=ledger,
        case_context=base_context
    )
    
    action_names = [a.action for a in actions]
    assert "CLOSE_NO_FRAUD" not in action_names, "Rule R3 must NOT trigger on unavailable customer response!"


def test_4b_actual_confirmation_does_trigger_r3(policy_engine, base_context):
    """Actual affirmative customer confirmation must trigger Rule R3 (CLOSE_NO_FRAUD)."""
    tool = CustomerVerificationTool()
    res = tool.execute(
        params={"case_id": base_context["case_id"], "fixture_response": "Yes, I made this purchase."},
        context=base_context
    )
    
    ledger = EvidenceLedger()
    ledger.add(res.evidence_item)
    
    actions = policy_engine.evaluate(
        fraud_probability=0.20,
        verdict="LEGITIMATE",
        exposure_usd=base_context["exposure_usd"],
        ledger=ledger,
        case_context=base_context
    )
    
    assert len(actions) == 1
    assert actions[0].action == "CLOSE_NO_FRAUD"
    assert "R3" in actions[0].reason


def test_4c_corrupted_no_match_confirmation_does_not_trigger_r3(policy_engine, base_context):
    """Even if an EvidenceItem was manually created with CUSTOMER_CONFIRMATION but value='NO_MATCH',
    PolicyEngine's strict condition must reject it and NOT trigger R3.
    """
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_CONFIRMATION,
        value="NO_MATCH",
        source="test",
        finding="Timed out",
        lr=1.0,
        log_lr=0.0,
        is_exculpatory=False
    ))
    
    actions = policy_engine.evaluate(
        fraud_probability=0.85,
        verdict="FRAUD",
        exposure_usd=base_context["exposure_usd"],
        ledger=ledger,
        case_context=base_context
    )
    
    action_names = [a.action for a in actions]
    assert "CLOSE_NO_FRAUD" not in action_names


# ==============================================================================
# Test 5: No Belief Contamination
# ==============================================================================

def test_5_unavailable_customer_causes_zero_belief_contamination(belief_engine, base_context):
    """Unavailable/timeout customer response must:
    - NOT change P(Fraud)
    - NOT add an effective log-LR
    - NOT increase evidence coverage for CUSTOMER_DISPUTE
    - NOT record fraudulent or exculpatory belief shifts
    """
    from src.belief.state import WorldHypothesis
    trigger = {"trigger_type": "risk_score", "flagged_txn_id": "TXN_777"}
    target_entities = {"customer_id": "CUST_999", "card_id": "CARD_888"}
    
    # 1. Baseline state with only prior
    ledger_empty = EvidenceLedger()
    state_empty = belief_engine.evaluate_investigation(
        "INV-TEST-EMPTY", trigger, target_entities, ledger_empty,
        prior_profile=PriorProfile.ALERT_CONDITIONED
    )
    prior_prob = state_empty.hypotheses[WorldHypothesis.FRAUD].probability
    
    # 2. State after adding UNAVAILABLE customer evidence
    tool = CustomerVerificationTool()
    res_unavail = tool.execute(params={"case_id": base_context["case_id"]}, context=base_context)
    
    ledger_with_unavail = EvidenceLedger()
    ledger_with_unavail.add(res_unavail.evidence_item)
    
    state_with_unavail = belief_engine.evaluate_investigation(
        "INV-TEST-UNAVAIL", trigger, target_entities, ledger_with_unavail,
        prior_profile=PriorProfile.ALERT_CONDITIONED
    )
    
    # Verify exact probability preservation (zero delta)
    assert state_with_unavail.hypotheses[WorldHypothesis.FRAUD].probability == prior_prob
    assert state_with_unavail.hypotheses[WorldHypothesis.FRAUD].log_odds == state_empty.hypotheses[WorldHypothesis.FRAUD].log_odds
    
    # Verify no coverage inflation
    coverage = state_with_unavail.uncertainty.data_coverage
    assert coverage.get(EvidenceFamily.CUSTOMER_DISPUTE.value) is False
    assert state_with_unavail.uncertainty.evidence_coverage == 0.0
    
    # Verify reasoning trace records neutral no-match and zero effective log-lr
    step_events = [s.event for s in state_with_unavail.reasoning_history]
    assert "NO_MATCH_NEUTRAL_RECORDED" in step_events
    assert all(s.effective_log_lr == 0.0 for s in state_with_unavail.reasoning_history)


# ==============================================================================
# Test 6: Fallback Action Normalizer Integrity
# ==============================================================================

def test_6_fallback_type_for_action_integrity():
    """Verifies that _fallback_type_for_action maps customer actions to
    CUSTOMER_COMMUNICATION_UNAVAILABLE rather than CUSTOMER_CONFIRMATION.
    """
    assert EvidenceNormalizer._fallback_type_for_action("VERIFY_WITH_CUSTOMER") == EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE
    assert EvidenceNormalizer._fallback_type_for_action("CUSTOMER_INTERACTION") == EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE
    assert EvidenceNormalizer._fallback_type_for_action("STEP_UP_AUTH") == EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE
    assert EvidenceNormalizer._fallback_type_for_action("DISPUTE_VERIFICATION") == EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE
