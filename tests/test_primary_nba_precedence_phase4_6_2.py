import pytest
from typing import Dict, Any, List

from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceItem, EvidenceType, EvidenceDirection
from src.policy.engine import PolicyEngine, ActionRecommendation, ActionRole, ActionScope

@pytest.fixture
def policy_engine():
    return PolicyEngine()

# ==============================================================================
# Test A: Create Case vs Transaction Decline
# ==============================================================================

def test_a_create_case_vs_transaction_decline_precedence(policy_engine):
    """When an investigation establishes an organized syndicate / shared device ring
    or novel undocumented scheme (requiring case management), CREATE_CASE must be the
    governing PRIMARY action, and any operational interventions must be marked CONSEQUENTIAL.
    """
    # Case with genuine shared device ring
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="tigergraph_query:device_analysis",
        finding="Device DEV_01 shared across 4 distinct cards in graph ring.",
        lr=14.2,
        log_lr=2.653,
        value={"shared_card_count": 4}
    ))
    # Uninformative card testing check (NO_MATCH) must NOT hijack the case
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="tigergraph_query:card_sequence",
        finding="No micro-authorization sequence observed.",
        lr=1.0,
        log_lr=0.0,
        value="NO_MATCH"
    ))

    actions = policy_engine.evaluate(
        fraud_probability=0.98,
        verdict="fraud",
        exposure_usd=1200.0,
        ledger=ledger,
        case_context={"pattern": "shared_device_ring"}
    )

    primary = policy_engine.get_primary_action(actions)
    assert primary is not None
    assert primary.action == "CREATE_CASE"
    assert primary.role == ActionRole.PRIMARY
    assert primary.scope == ActionScope.CASE_MANAGEMENT

    # Verify consequential actions are tagged and preserved
    consequential = policy_engine.get_consequential_actions(actions)
    consequential_actions = [a.action for a in consequential]
    assert "FILE_REPORT" in consequential_actions
    assert "MONITOR_CONNECTED_CARDS" in consequential_actions
    for ca in consequential:
        assert ca.role == ActionRole.CONSEQUENTIAL


# ==============================================================================
# Test B: Block Card vs Transaction Decline
# ==============================================================================

def test_b_block_card_vs_transaction_decline_on_customer_dispute(policy_engine):
    """When a cardholder reports or disputes a transaction (CUSTOMER_DENIAL),
    the governing regulatory/statutory action is BLOCK_CARD (account-level freeze),
    with CREATE_CASE as a consequential case-management requirement.
    A negative card-testing query (NO_MATCH) must NOT override customer denial with DECLINE_TRANSACTION.
    """
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_DENIAL,
        source="customer_report_trigger",
        finding="Cardholder reports unauthorized transaction.",
        lr=18.5,
        log_lr=2.918,
        value="I never authorized this purchase."
    ))
    # Routine card_sequence executed by orchestrator reports NO_MATCH
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="tigergraph_query:card_sequence",
        finding="No card testing sequence observed.",
        lr=1.0,
        log_lr=0.0,
        value="NO_MATCH"
    ))

    actions = policy_engine.evaluate(
        fraud_probability=0.98,
        verdict="fraud",
        exposure_usd=49.0,
        ledger=ledger,
        case_context={"trigger_type": "customer_report"}
    )

    primary = policy_engine.get_primary_action(actions)
    assert primary is not None
    assert primary.action == "BLOCK_CARD"
    assert primary.role == ActionRole.PRIMARY
    assert primary.scope == ActionScope.CARD_ACCOUNT

    action_names = [a.action for a in actions]
    assert action_names[0] == "BLOCK_CARD"
    assert "CREATE_CASE" in action_names


# ==============================================================================
# Test C: Transaction-Only Scenario
# ==============================================================================

def test_c_transaction_only_scenario_remains_primary(policy_engine):
    """When card testing micro-authorizations are actively detected under $100 exposure,
    the governing action is DECLINE_TRANSACTION (transaction-level intervention),
    with STEP_UP_AUTH as consequential operational follow-up.
    """
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="tigergraph_query:card_sequence",
        finding="Card testing sequence: 3 micro-authorizations in 24h prior.",
        lr=34.3,
        log_lr=3.535,
        value={"micro_count": 3, "total_spend": 8.50}
    ))

    actions = policy_engine.evaluate(
        fraud_probability=0.85,
        verdict="fraud",
        exposure_usd=50.0,  # <= 100.0
        ledger=ledger,
        case_context={"trigger_type": "risk_score"}
    )

    primary = policy_engine.get_primary_action(actions)
    assert primary is not None
    assert primary.action == "DECLINE_TRANSACTION"
    assert primary.role == ActionRole.PRIMARY
    assert primary.scope == ActionScope.TRANSACTION

    # Verify STEP_UP_AUTH is preserved as consequential
    consequential = policy_engine.get_consequential_actions(actions)
    assert any(a.action == "STEP_UP_AUTH" for a in consequential)


# ==============================================================================
# Test D: Case-Only Scenario
# ==============================================================================

def test_d_case_only_scenario_undocumented_pattern(policy_engine):
    """In an undocumented high-confidence fraud scheme without specific device ring or card testing,
    CREATE_CASE must be the PRIMARY action, accompanied by FILE_REPORT and ESCALATE_TO_ANALYST.
    """
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="bank_detection_model",
        finding="High risk score: 0.88",
        lr=6.8,
        log_lr=1.917,
        value=0.88
    ))

    actions = policy_engine.evaluate(
        fraud_probability=0.92,
        verdict="fraud",
        exposure_usd=111.0,
        ledger=ledger,
        case_context={"pattern": "undocumented", "trigger_type": "risk_score"}
    )

    primary = policy_engine.get_primary_action(actions)
    assert primary is not None
    assert primary.action == "CREATE_CASE"
    assert primary.role == ActionRole.PRIMARY
    assert primary.scope == ActionScope.CASE_MANAGEMENT

    action_names = [a.action for a in actions]
    assert action_names == ["CREATE_CASE", "FILE_REPORT", "ESCALATE_TO_ANALYST"]


# ==============================================================================
# Test E: Existing HHG-011-Style Behavior (Card Testing Control)
# ==============================================================================

def test_e_genuine_card_testing_preserves_decline_transaction(policy_engine):
    """When genuine card testing sequence IS observed (like in HHG-011),
    DECLINE_TRANSACTION must remain the PRIMARY action under Rule R5,
    with BLOCK_CARD as consequential (when exposure > $100).
    """
    ledger = EvidenceLedger()
    # Genuine customer denial + genuine card testing
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_DENIAL,
        source="customer_report_trigger",
        finding="Customer disputes charge.",
        lr=18.5,
        log_lr=2.918,
        value="I never made this purchase."
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="tigergraph_query:card_sequence",
        finding="3 micro-authorizations in 24h prior.",
        lr=34.3,
        log_lr=3.535,
        value={"micro_count": 3, "total_spend": 4.50}
    ))

    actions = policy_engine.evaluate(
        fraud_probability=0.9998,
        verdict="fraud",
        exposure_usd=131.30,  # > 100.0
        ledger=ledger,
        case_context={"trigger_type": "customer_report", "pattern": "card_testing"}
    )

    primary = policy_engine.get_primary_action(actions)
    assert primary is not None
    assert primary.action == "DECLINE_TRANSACTION"
    assert primary.role == ActionRole.PRIMARY
    assert primary.approval_route == "L1"

    action_names = [a.action for a in actions]
    assert action_names == ["DECLINE_TRANSACTION", "BLOCK_CARD"]
    assert actions[1].role == ActionRole.CONSEQUENTIAL
    assert actions[1].scope == ActionScope.CARD_ACCOUNT


# ==============================================================================
# Test F: Multiple Actions Remained Preserved
# ==============================================================================

def test_f_multiple_operational_actions_preserved(policy_engine):
    """Verifies that determining the primary action does NOT drop or suppress
    consequential operational actions (e.g. SAR filing, card monitoring).
    """
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_DENIAL,
        source="customer_report",
        finding="Dispute reported",
        lr=18.5,
        log_lr=2.918,
        value="dispute"
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device_analysis",
        finding="Shared device ring",
        lr=14.2,
        log_lr=2.653,
        value={"shared_card_count": 5}
    ))

    actions = policy_engine.evaluate(
        fraud_probability=0.99,
        verdict="fraud",
        exposure_usd=1500.0,
        ledger=ledger,
        case_context={"trigger_type": "customer_report"}
    )

    # R2 with exposure > 1000 and shared ring produces 4 distinct actions:
    # [BLOCK_CARD, CREATE_CASE, FILE_REPORT, MONITOR_CONNECTED_CARDS]
    assert len(actions) == 4
    action_names = [a.action for a in actions]
    assert action_names[0] == "BLOCK_CARD"
    assert "CREATE_CASE" in action_names
    assert "FILE_REPORT" in action_names
    assert "MONITOR_CONNECTED_CARDS" in action_names

    # Exactly 1 primary, 3 consequential
    primaries = [a for a in actions if a.role == ActionRole.PRIMARY]
    consequentials = [a for a in actions if a.role == ActionRole.CONSEQUENTIAL]
    assert len(primaries) == 1
    assert len(consequentials) == 3


# ==============================================================================
# Test G: Determinism
# ==============================================================================

def test_g_determinism_across_multiple_evaluations(policy_engine):
    """Running policy evaluation repeatedly on identical inputs must produce
    strictly identical action recommendations, roles, and ordering every single time.
    """
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="tigergraph_query:device_analysis",
        finding="Device shared across 4 distinct cards.",
        lr=14.2,
        log_lr=2.653,
        value={"shared_card_count": 4}
    ))

    results = []
    for _ in range(10):
        actions = policy_engine.evaluate(
            fraud_probability=0.95,
            verdict="fraud",
            exposure_usd=750.0,
            ledger=ledger,
            case_context={"pattern": "shared_device_ring"}
        )
        results.append([(a.action, a.role, a.scope, a.approval_route) for a in actions])

    # All 10 runs must match run 0 exactly
    for i in range(1, 10):
        assert results[i] == results[0]


# ==============================================================================
# Test H: No Benchmark-Specific Logic
# ==============================================================================

def test_h_independence_of_case_id_and_customer_id(policy_engine):
    """Policy outcomes must depend purely on evidence, exposure, and policy conditions,
    with zero influence from case IDs, customer IDs, or synthetic benchmark tags.
    """
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_DENIAL,
        source="customer_report",
        finding="Dispute",
        lr=18.5,
        log_lr=2.918,
        value="denied"
    ))

    # Evaluate with benchmark-like context vs arbitrary context
    actions_hhg = policy_engine.evaluate(
        fraud_probability=0.98,
        verdict="fraud",
        exposure_usd=50.0,
        ledger=ledger,
        case_context={"case_id": "HHG-003", "customer_id": "C08623", "trigger_type": "customer_report"}
    )
    actions_arbitrary = policy_engine.evaluate(
        fraud_probability=0.98,
        verdict="fraud",
        exposure_usd=50.0,
        ledger=ledger,
        case_context={"case_id": "PROD-CASE-9999", "customer_id": "USER-RANDOM-ABC", "trigger_type": "customer_report"}
    )

    assert [(a.action, a.role, a.scope) for a in actions_hhg] == [(a.action, a.role, a.scope) for a in actions_arbitrary]


# ==============================================================================
# Test I: Legitimate / Low Risk Exculpatory Scenario
# ==============================================================================

def test_i_legitimate_scenario_primary_allow_transaction(policy_engine):
    """When fraud probability <= 0.30, ALLOW_TRANSACTION must be PRIMARY,
    and CLOSE_NO_FRAUD must be consequential.
    """
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.BEHAVIORAL_BASELINE,
        source="tigergraph_query:customer_profile",
        finding="Transaction matches customer normal baseline.",
        lr=1.0,
        log_lr=0.0
    ))

    actions = policy_engine.evaluate(
        fraud_probability=0.15,
        verdict="legitimate",
        exposure_usd=45.0,
        ledger=ledger,
        case_context={"trigger_type": "risk_score"}
    )

    primary = policy_engine.get_primary_action(actions)
    assert primary is not None
    assert primary.action == "ALLOW_TRANSACTION"
    assert primary.role == ActionRole.PRIMARY
    assert primary.scope == ActionScope.TRANSACTION

    action_names = [a.action for a in actions]
    assert action_names == ["ALLOW_TRANSACTION", "CLOSE_NO_FRAUD"]
    assert actions[1].role == ActionRole.CONSEQUENTIAL
    assert actions[1].scope == ActionScope.CASE_MANAGEMENT
