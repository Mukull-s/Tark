import pytest
from typing import Dict, Any

from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceItem, EvidenceType, EvidenceDirection
from src.belief.calibration import (
    CalibrationClassification,
    EvidenceFamily,
    PriorProfile,
    PRIOR_REGISTRY,
    LIKELIHOOD_REGISTRY,
    SCORE_CALIBRATION_BINS,
    get_calibrated_lr
)
from src.belief.state import (
    WorldHypothesis,
    HypothesisStatus,
    DecisionState,
    InvestigationState
)
from src.belief.engine import BeliefEngine, MIN_DECISION_COVERAGE, CORE_INVESTIGATIVE_FAMILIES
from src.policy.engine import PolicyEngine
from src.compass.evoi import EvidenceCompass
from src.tools.mock_actions import simulate_customer_reply, simulate_step_up_auth
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
def base_trigger_and_entities():
    trigger = {
        "trigger_type": "risk_score",
        "flagged_txn_id": "TXN_AUDIT_01",
        "txn_addr1": 299.0
    }
    target_entities = {
        "card_id": "CARD_AUDIT_99",
        "customer_id": "CUST_AUDIT_88",
        "flagged_txn_id": "TXN_AUDIT_01"
    }
    return trigger, target_entities


# ==============================================================================
# 1. Coverage Mapping & device_analysis (0.20 -> 0.40) Verification
# ==============================================================================

def test_coverage_mapping_and_device_analysis_shift(belief_engine, base_trigger_and_entities):
    """Verifies coverage mapping math and why device_analysis transitions coverage 0.20 -> 0.40."""
    trigger, target_entities = base_trigger_and_entities
    
    # 1. Verify Core Investigative Families contract
    assert len(CORE_INVESTIGATIVE_FAMILIES) == 5
    assert EvidenceFamily.DEVICE_INFRASTRUCTURE in CORE_INVESTIGATIVE_FAMILIES
    assert EvidenceFamily.TRANSACTION_VELOCITY in CORE_INVESTIGATIVE_FAMILIES
    assert EvidenceFamily.BEHAVIORAL_BASELINE in CORE_INVESTIGATIVE_FAMILIES
    assert EvidenceFamily.CUSTOMER_DISPUTE in CORE_INVESTIGATIVE_FAMILIES
    assert EvidenceFamily.MODEL_SCORE in CORE_INVESTIGATIVE_FAMILIES

    # 2. Initial state: Model score only (1 dimension observed out of 5)
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="realtime_model",
        finding="Model scored transaction at 0.65",
        lr=2.4,
        log_lr=0.875,
        details={"risk_score": 0.65}
    ))
    
    state_init = belief_engine.evaluate_investigation(
        "INV-AUDIT-COV-1", trigger, target_entities, ledger,
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE
    )
    
    assert state_init.uncertainty.observed_dimensions == [EvidenceFamily.MODEL_SCORE.value]
    assert state_init.uncertainty.evidence_coverage == 0.20
    assert state_init.decision_gate_passed is False
    assert state_init.decision_state == DecisionState.INSUFFICIENT_EVIDENCE

    # 3. Add device_analysis finding (SHARED_DEVICE_RING)
    # This introduces EvidenceFamily.DEVICE_INFRASTRUCTURE (2nd distinct core dimension)
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device_analysis",
        finding="Device fingerprint shared across 4 cards",
        lr=14.2,
        log_lr=2.653
    ))
    
    state_updated = belief_engine.evaluate_investigation(
        "INV-AUDIT-COV-2", trigger, target_entities, ledger,
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE
    )
    
    assert set(state_updated.uncertainty.observed_dimensions) == {
        EvidenceFamily.MODEL_SCORE.value,
        EvidenceFamily.DEVICE_INFRASTRUCTURE.value
    }
    # 2 out of 5 core dimensions observed = 2 / 5 = 0.40
    assert state_updated.uncertainty.evidence_coverage == 0.40
    assert state_updated.decision_gate_passed is True
    assert state_updated.decision_state == DecisionState.DECIDED


def test_device_analysis_no_match_does_not_increase_coverage(belief_engine, base_trigger_and_entities):
    """Verifies that a NO_MATCH or DATA_OUT_OF_SCOPE device_analysis does NOT yield 0.40 coverage."""
    trigger, target_entities = base_trigger_and_entities
    
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="realtime_model",
        finding="Model scored transaction at 0.65",
        lr=2.4,
        log_lr=0.875
    ))
    # NO_MATCH from device_analysis
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        value="NO_MATCH",
        source="device_analysis",
        finding="No shared device pattern observed",
        lr=1.0,
        log_lr=0.0
    ))
    
    state = belief_engine.evaluate_investigation(
        "INV-AUDIT-NOMATCH", trigger, target_entities, ledger,
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE
    )
    
    # Coverage must remain 0.20 because NO_MATCH does not count as an observed core dimension
    assert state.uncertainty.evidence_coverage == 0.20
    assert state.decision_gate_passed is False
    assert state.decision_state == DecisionState.INSUFFICIENT_EVIDENCE


# ==============================================================================
# 2. Single Evidence Item Cannot Cover Multiple Dimensions
# ==============================================================================

def test_single_evidence_item_strictly_maps_to_one_dimension(belief_engine, base_trigger_and_entities):
    """Verifies that a single evidence item can NEVER cover multiple dimensions."""
    trigger, target_entities = base_trigger_and_entities
    
    # Attempt to create an evidence item packed with multi-dimensional keywords
    item = EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device_and_network_and_velocity_analyzer",
        finding="Device ring detected with high velocity and customer conflict",
        lr=14.2,
        log_lr=2.653,
        details={
            "device_id": "DEV-999",
            "ip_proxy": True,
            "velocity_count": 25,
            "card_testing": True,
            "customer_dispute": True
        }
    )
    
    # Check family resolution contract
    family, ceiling = belief_engine.resolve_evidence_family(item)
    assert family == EvidenceFamily.DEVICE_INFRASTRUCTURE
    assert isinstance(family, EvidenceFamily)
    
    ledger = EvidenceLedger()
    ledger.add(item)
    state = belief_engine.evaluate_investigation(
        "INV-AUDIT-SINGLE-ITEM", trigger, target_entities, ledger,
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE
    )
    
    # Must strictly contain exactly 1 observed dimension (0.20 coverage)
    assert len(state.uncertainty.observed_dimensions) == 1
    assert state.uncertainty.observed_dimensions == [EvidenceFamily.DEVICE_INFRASTRUCTURE.value]
    assert state.uncertainty.evidence_coverage == 0.20


# ==============================================================================
# 3. High LR Cannot Bypass Evidence Coverage (Adversarial Gate Integrity)
# ==============================================================================

def test_adversarial_astronomical_lr_cannot_bypass_coverage_gate(belief_engine, compass, base_trigger_and_entities):
    """Adversarial Test: An extreme astronomical LR (e.g. LR = 10^8, P > 0.99999)

    CANNOT bypass the evidence coverage gate when coverage < 0.40.
    """
    trigger, target_entities = base_trigger_and_entities
    
    # Single item with astronomical log-LR (+18.42, LR ~ 100,000,000)
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="adversarial_super_signal",
        finding="Extreme velocity pattern with theoretical maximum confidence",
        lr=100000000.0,
        log_lr=18.42
    ))
    
    state = belief_engine.evaluate_investigation(
        "INV-AUDIT-ASTRONOMICAL-LR", trigger, target_entities, ledger,
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE
    )
    
    # 1. Verify posterior probability is clamped by family ceiling (4.5 -> p = 0.9890)
    # The family ceiling itself prevents unbounded log-odds explosion!
    assert state.belief_state["fraud_probability"] >= 0.98
    assert state.hypotheses[WorldHypothesis.FRAUD].probability >= 0.98
    assert state.belief_state["net_log_lr"] <= 4.5
    
    # 2. But coverage is only 0.20 (1/5 core dimensions: TRANSACTION_VELOCITY)
    assert state.uncertainty.evidence_coverage == 0.20
    assert state.uncertainty.evidence_coverage < MIN_DECISION_COVERAGE
    
    # 3. Decision gate MUST be strictly locked
    assert state.decision_gate_passed is False
    assert state.decision_state == DecisionState.INSUFFICIENT_EVIDENCE
    assert any("below minimum threshold" in block for block in state.decision_gate_blocks)
    assert "insufficient evidence to make a fraud determination" in state.decision_rationale.lower()
    
    # 4. FRAUD hypothesis must NOT be CONFIRMED (must remain ACTIVE because gate failed)
    assert state.hypotheses[WorldHypothesis.FRAUD].status == HypothesisStatus.ACTIVE
    
    # 5. EVOI Engine must respect Decision Gate and block terminal actions (e.g., BLOCK_CARD)
    admissible_action = compass.resolve_admissible_action(
        state=state,
        exposure_usd=1000.0,
        ledger=ledger,
        case_context={"flagged_txn_id": "TXN_AUDIT_01"}
    )
    assert admissible_action == "MONITOR_CARD"
    assert admissible_action != "BLOCK_CARD"


def test_adversarial_intra_family_stacking_cannot_bypass_coverage_gate(belief_engine, base_trigger_and_entities):
    """Adversarial Test: Stacking 4 different items within the SAME family (DEVICE_INFRASTRUCTURE)

    cannot artificially inflate coverage beyond 0.20.
    """
    trigger, target_entities = base_trigger_and_entities
    
    ledger = EvidenceLedger()
    # Item 1
    ledger.add(EvidenceItem(
        evidence_id="EVD-D1",
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device_analysis",
        finding="Shared device ring",
        lr=14.2,
        log_lr=2.653
    ))
    # Item 2
    ledger.add(EvidenceItem(
        evidence_id="EVD-D2",
        evidence_type=EvidenceType.PROXY_DETECTED,
        source="device_analysis",
        finding="Proxy IP detected",
        lr=3.8,
        log_lr=1.335
    ))
    # Item 3
    ledger.add(EvidenceItem(
        evidence_id="EVD-D3",
        evidence_type=EvidenceType.CNP_NEW_DEVICE,
        source="device_analysis",
        finding="New device profile",
        lr=1.31,
        log_lr=0.273
    ))
    # Item 4
    ledger.add(EvidenceItem(
        evidence_id="EVD-D4",
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device_analysis",
        finding="Secondary cluster link",
        lr=14.2,
        log_lr=2.653,
        supporting_transaction_ids=["TXN-OTHER-01"]
    ))
    
    state = belief_engine.evaluate_investigation(
        "INV-AUDIT-FAMILY-STACK", trigger, target_entities, ledger,
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE
    )
    
    # All 4 items belong to DEVICE_INFRASTRUCTURE
    assert set(state.uncertainty.observed_dimensions) == {EvidenceFamily.DEVICE_INFRASTRUCTURE.value}
    # Coverage remains strictly 1/5 = 0.20
    assert state.uncertainty.evidence_coverage == 0.20
    assert state.decision_gate_passed is False
    assert state.decision_state == DecisionState.INSUFFICIENT_EVIDENCE


# ==============================================================================
# 4. LR Provenance Integrity (Provisional / Policy / Empirical)
# ==============================================================================

def test_lr_provenance_registry_integrity():
    """Verifies that all LR parameters retain formal, non-arbitrary provenance classifications."""
    # 1. Priors have explicit classifications
    assert PRIOR_REGISTRY[PriorProfile.ALERT_CONDITIONED]["classification"] == CalibrationClassification.EMPIRICAL
    assert PRIOR_REGISTRY[PriorProfile.UNCONDITIONED_POPULATION]["classification"] == CalibrationClassification.PROVISIONAL
    assert PRIOR_REGISTRY[PriorProfile.UNIFORM_NON_INFORMATIVE]["classification"] == CalibrationClassification.HEURISTIC
    
    # 2. Risk Score bins are EMPIRICAL
    for b in SCORE_CALIBRATION_BINS:
        assert b["classification"] == CalibrationClassification.EMPIRICAL
        assert "lr" in b and "log_lr" in b

    # 3. Every registered likelihood ratio has explicit classification and family ceiling
    for key, meta in LIKELIHOOD_REGISTRY.items():
        assert meta.classification in [
            CalibrationClassification.EMPIRICAL,
            CalibrationClassification.POLICY_DEFINED,
            CalibrationClassification.PROVISIONAL,
            CalibrationClassification.HEURISTIC
        ]
        assert meta.family_ceiling_log_lr >= 0.0
        if meta.evidence_type != "BEHAVIORAL_BASELINE":
            assert meta.family_ceiling_log_lr > 0.0
        assert meta.family in EvidenceFamily


# ==============================================================================
# 5. Customer Simulator Independence
# ==============================================================================

def test_customer_simulator_independence_of_posterior():
    """Verifies that customer simulator responses are strictly independent of posterior belief."""
    case_id = "CASE-INDEP-001"
    prompt = "Did you make transaction TXN_AUDIT_01 for $299.00?"
    
    # Calling simulator with trigger_type="risk_score" and no external fixture
    # Simulator does NOT accept posterior as an argument and returns UNAVAILABLE timeout
    resp1 = simulate_customer_reply(case_id, prompt, trigger_type="risk_score")
    assert resp1["status"] == "UNAVAILABLE"
    assert resp1["customer_denied"] is None
    assert resp1["provenance"] == "external_gateway_timeout"

    # Inbound dispute trigger yields customer denial regardless of posterior belief
    resp2 = simulate_customer_reply(case_id, prompt, trigger_type="customer_report")
    assert resp2["status"] == "COMPLETED"
    assert resp2["customer_denied"] is True
    assert resp2["provenance"] == "inbound_customer_ticket"

    # Step-up auth simulator is also independent
    auth_resp = simulate_step_up_auth(case_id)
    assert auth_resp["status"] == "TIMEOUT"
    assert auth_resp["auth_passed"] is False
    assert auth_resp["provenance"] == "mfa_challenge_expired"


# ==============================================================================
# 6. Similar-Case Precedents Cannot Masquerade as Ground Truth
# ==============================================================================

def test_similar_case_precedent_cannot_masquerade_as_ground_truth(belief_engine, base_trigger_and_entities):
    """Verifies that similar-case query results cannot shift posterior belief or satisfy coverage."""
    trigger, target_entities = base_trigger_and_entities
    
    # Initial state with Model Score
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="realtime_model",
        finding="Model score 0.65",
        lr=2.4,
        log_lr=0.875
    ))
    
    state_before = belief_engine.evaluate_investigation(
        "INV-AUDIT-SIMILAR-1", trigger, target_entities, ledger,
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE
    )
    p_before = state_before.belief_state["fraud_probability"]
    cov_before = state_before.uncertainty.evidence_coverage
    
    # Add Similar Cases precedent (e.g. 5 matching closed cases)
    sim_item = EvidenceItem(
        evidence_id="EVD-SIM-01",
        evidence_type=EvidenceType.SIMILAR_CASE_PRECEDENT,
        value={"matched_case_count": 5},
        source="tigergraph_query:similar_cases",
        finding="Retrieved 5 precedent closed cases matching investigative pattern.",
        provenance="TigerGraph GSQL similar_cases",
        lr=1.0,
        log_lr=0.0,
        direction=EvidenceDirection.NEUTRAL,
        details={"matched_case_count": 5}
    )
    ledger.add(sim_item)
    
    state_after = belief_engine.evaluate_investigation(
        "INV-AUDIT-SIMILAR-2", trigger, target_entities, ledger,
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE
    )
    
    # 1. Posterior probability MUST remain identical (LR=1.0, log-LR=0.0)
    assert abs(state_after.belief_state["fraud_probability"] - p_before) < 1e-6
    assert abs(state_after.belief_state["posterior_log_odds"] - state_before.belief_state["posterior_log_odds"]) < 1e-6
    
    # 2. Evidence coverage MUST remain unchanged (CASE_HISTORY is not in CORE_INVESTIGATIVE_FAMILIES)
    assert state_after.uncertainty.evidence_coverage == cov_before == 0.20
    assert EvidenceFamily.CASE_HISTORY.value not in state_after.uncertainty.observed_dimensions
    
    # 3. Decision gate remains strictly blocked
    assert state_after.decision_gate_passed is False
    assert state_after.decision_state == DecisionState.INSUFFICIENT_EVIDENCE


# ==============================================================================
# 7. Additional Adversarial Premature Gate Unlocking Tests
# ==============================================================================

def test_adversarial_severe_conflict_forces_human_escalation_despite_high_lr(belief_engine, base_trigger_and_entities):
    """Adversarial Test: Inculpatory evidence with high LR combined with exculpatory evidence

    cannot prematurely unlock DECIDED state — MUST enforce REQUIRES_HUMAN_APPROVAL.
    """
    trigger, target_entities = base_trigger_and_entities
    
    ledger = EvidenceLedger()
    # High inculpatory log-LR (Shared Device Ring: LR=14.2, log-LR=2.653)
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device_analysis",
        finding="Device shared across 5 cards",
        lr=14.2,
        log_lr=2.653
    ))
    # Velocity burst (High Velocity: LR=2.5, log-LR=0.916)
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.HIGH_VELOCITY,
        source="txn_velocity",
        finding="12 txns in 24h",
        lr=2.5,
        log_lr=0.916
    ))
    # Exculpatory customer confirmation (Customer Confirmation: LR=0.05, log-LR=-2.996)
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_CONFIRMATION,
        source="customer_verification",
        finding="Customer confirmed authorized purchase",
        lr=0.05,
        log_lr=-2.996,
        is_exculpatory=True
    ))
    
    state = belief_engine.evaluate_investigation(
        "INV-AUDIT-CONFLICT", trigger, target_entities, ledger,
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE
    )
    
    # Coverage is 3/5 = 0.60 >= 0.40, but conflict magnitude is high!
    assert state.uncertainty.evidence_coverage >= 0.40
    assert state.uncertainty.aleatoric_uncertainty >= 0.40
    
    # Decision gate must NOT pass as DECIDED
    assert state.decision_gate_passed is False
    assert state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL
    assert "HUMAN_RISK_ANALYST" in state.approval_requirements
    assert any("Severe evidentiary conflict" in block for block in state.decision_gate_blocks)
