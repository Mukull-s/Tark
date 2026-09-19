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
    get_calibrated_lr
)
from src.belief.state import (
    WorldHypothesis,
    HypothesisType,
    HypothesisStatus,
    DecisionState,
    InvestigationState
)
from src.belief.engine import BeliefEngine, MIN_DECISION_COVERAGE

@pytest.fixture
def belief_engine():
    return BeliefEngine()

# 1. Clean EvidenceLedger -> InvestigationState serialization with World Hypotheses
def test_investigation_state_generation_and_serialization(belief_engine):
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device_analysis",
        finding="Device shared across 3 cards",
        lr=14.2,
        log_lr=2.653,
        supporting_transaction_ids=["TXN-101", "TXN-102"]
    ))
    
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-TEST-001",
        trigger={"trigger_type": "risk_score", "risk_score": 0.72},
        target_entities={"card_id": "CARD-999", "customer_id": "CUST-111"},
        ledger=ledger
    )
    
    assert isinstance(state, InvestigationState)
    assert state.investigation_id == "INV-TEST-001"
    assert state.hypotheses[WorldHypothesis.FRAUD].probability > 0.8
    assert len(state.evidence_items) == 1
    assert len(state.reasoning_history) >= 2
    
    # Verify complete JSON serializability
    dumped = state.model_dump()
    assert dumped["investigation_id"] == "INV-TEST-001"
    assert "uncertainty" in dumped
    assert "hypotheses" in dumped
    assert "reasoning_history" in dumped

# 2. Required Change 1: World Hypotheses vs Epistemic State
def test_world_hypotheses_and_no_insufficient_evidence_probability(belief_engine):
    ledger = EvidenceLedger()
    state = belief_engine.evaluate_investigation("INV-WORLD", {}, {}, ledger, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    
    # 1. Only FRAUD and LEGITIMATE exist in hypotheses dictionary
    assert set(state.hypotheses.keys()) == {WorldHypothesis.FRAUD, WorldHypothesis.LEGITIMATE}
    assert "INSUFFICIENT_EVIDENCE" not in state.hypotheses
    
    # 2. World probabilities sum strictly to 1.0
    p_fraud = state.hypotheses[WorldHypothesis.FRAUD].probability
    p_legit = state.hypotheses[WorldHypothesis.LEGITIMATE].probability
    assert abs(p_fraud + p_legit - 1.0) < 1e-6
    
    # 3. INSUFFICIENT_EVIDENCE is exclusively an epistemic decision state
    assert state.decision_state == DecisionState.INSUFFICIENT_EVIDENCE
    assert state.decision_gate_passed is False

# 3. Required Change 2 & 3: High Posterior Alone Cannot Bypass Material Coverage Gate
def test_high_posterior_with_insufficient_coverage_is_gated(belief_engine):
    # A single extreme signal (CARD_TESTING_SEQUENCE, LR=34.3) gives P(Fraud) = 0.9717
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="pattern_analysis",
        finding="Card testing sequence observed",
        lr=34.3,
        log_lr=3.535
    ))
    
    state = belief_engine.evaluate_investigation("INV-GATE-1", {}, {}, ledger, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    
    # Posterior is high (> 0.95)
    assert state.belief_state["fraud_probability"] > 0.95
    assert state.primary_hypothesis == WorldHypothesis.FRAUD
    
    # But coverage is only 1/5 = 0.20 < 0.40
    assert state.uncertainty.evidence_coverage == 0.20
    assert state.decision_gate_passed is False
    assert state.decision_state == DecisionState.INSUFFICIENT_EVIDENCE
    assert any("below minimum threshold" in block for block in state.decision_gate_blocks)
    assert "insufficient evidence to make a fraud determination" in state.decision_rationale.lower()

# 4. Required Change 2 & 3: Corroborated Evidence Across Two Dimensions Passes Gate
def test_corroborated_coverage_passes_decision_gate(belief_engine):
    # Two distinct families: Velocity (CARD_TESTING) + Device (SHARED_DEVICE_RING)
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="pattern_analysis",
        finding="Card testing sequence",
        lr=34.3,
        log_lr=3.535
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device_analysis",
        finding="Shared device ring",
        lr=14.2,
        log_lr=2.653
    ))
    
    state = belief_engine.evaluate_investigation("INV-GATE-PASS", {}, {}, ledger, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    
    # Coverage is 2/5 = 0.40 >= MIN_DECISION_COVERAGE
    assert state.uncertainty.evidence_coverage == 0.40
    assert state.uncertainty.aleatoric_uncertainty == 0.0
    assert state.uncertainty.epistemic_uncertainty <= 0.60
    assert state.belief_state["fraud_probability"] >= 0.70
    
    # Decision gate passes!
    assert state.decision_gate_passed is True
    assert state.decision_state == DecisionState.DECIDED
    assert len(state.decision_gate_blocks) == 0

# 5. Required Change 4: NO_MATCH Does Not Automatically Create Exculpatory Evidence
def test_no_match_neutral_semantics(belief_engine):
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        value="NO_MATCH",
        source="pattern_analysis",
        finding="No micro-auth testing pattern observed in 24h window",
        lr=1.0,
        log_lr=0.0
    ))
    
    state = belief_engine.evaluate_investigation("INV-NOMATCH", {}, {}, ledger, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    
    # NO_MATCH must NOT reduce log-odds (must stay neutral)
    assert state.belief_state["net_log_lr"] == 0.0
    assert state.belief_state["posterior_log_odds"] == 0.0
    assert state.belief_state["fraud_probability"] == 0.50
    
    # Check trace record
    nomatch_step = next(s for s in state.reasoning_history if s.event == "NO_MATCH_NEUTRAL_RECORDED")
    assert nomatch_step.effective_log_lr == 0.0
    assert "neutral absence of pattern" in nomatch_step.rationale

# 6. Required Change 4: DATA_OUT_OF_SCOPE vs GRAPH_QUERY_FAILURE Distinct Semantics
def test_data_out_of_scope_vs_graph_query_failure_distinction(belief_engine):
    # Test DATA_OUT_OF_SCOPE
    l_oos = EvidenceLedger()
    l_oos.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        value="DATA_OUT_OF_SCOPE",
        source="device_analysis",
        finding="Data out of scope (unobserved region)"
    ))
    s_oos = belief_engine.evaluate_investigation("INV-OOS", {}, {}, l_oos, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    assert s_oos.belief_state["net_log_lr"] == 0.0
    assert s_oos.missing_information[0].reason == "DATA_OUT_OF_SCOPE"
    assert s_oos.missing_information[0].impact_severity == "MEDIUM"

    # Test GRAPH_QUERY_FAILURE
    l_fail = EvidenceLedger()
    l_fail.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        value="GRAPH_QUERY_FAILURE",
        source="device_analysis",
        finding="TigerGraph GSQL timeout after 15s"
    ))
    s_fail = belief_engine.evaluate_investigation("INV-FAIL", {}, {}, l_fail, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    assert s_fail.belief_state["net_log_lr"] == 0.0
    assert s_fail.missing_information[0].reason == "GRAPH_QUERY_FAILURE"
    assert s_fail.missing_information[0].impact_severity == "HIGH"
    
    # Both are recorded in unavailable_dimensions
    assert "SHARED_DEVICE_RING" in s_fail.uncertainty.unavailable_dimensions

# 7. Required Change 7: Complete Reasoning Trace with Decision Gate Step
def test_reasoning_trace_includes_decision_gate_step(belief_engine):
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="pattern_analysis",
        finding="Card testing sequence",
        lr=34.3,
        log_lr=3.535
    ))
    
    state = belief_engine.evaluate_investigation("INV-TRACE", {}, {}, ledger)
    
    events = [s.event for s in state.reasoning_history]
    assert "PRIOR_INITIALIZED" in events
    assert "EVIDENCE_EVALUATED" in events
    assert "DECISION_GATE_EVALUATED" in events
    
    gate_step = next(s for s in state.reasoning_history if s.event == "DECISION_GATE_EVALUATED")
    assert "Decision Gate:" in gate_step.rationale

# 8. Contradictory Evidence Produces REQUIRES_HUMAN_APPROVAL
def test_contradictory_evidence_requires_human_approval(belief_engine):
    ledger = EvidenceLedger()
    # Strong inculpatory (Device ring)
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device_analysis",
        finding="Device ring",
        lr=14.2,
        log_lr=2.653
    ))
    # Strong exculpatory (Customer confirmation)
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_CONFIRMATION,
        source="customer_verification",
        finding="Customer confirmed authorized purchase",
        lr=0.05,
        log_lr=-2.996,
        is_exculpatory=True
    ))
    
    state = belief_engine.evaluate_investigation("INV-CONTR", {}, {}, ledger, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    
    assert len(state.contradictions) == 1
    assert state.uncertainty.aleatoric_uncertainty >= 0.40
    assert state.decision_gate_passed is False
    assert state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL
    assert "HUMAN_RISK_ANALYST" in state.approval_requirements

# 9. Duplicate Evidence Cannot Artificially Inflate Belief
def test_duplicate_evidence_protection(belief_engine):
    ledger = EvidenceLedger()
    item = EvidenceItem(
        evidence_id="EVD-DUP-999",
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="pattern_analysis",
        finding="Card testing sequence",
        lr=34.3,
        log_lr=3.535
    )
    ledger.add(item)
    ledger.add(item)  # Duplicate
    
    state = belief_engine.evaluate_investigation("INV-DUP", {}, {}, ledger, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    
    # Second item ignored
    assert abs(state.belief_state["posterior_log_odds"] - 3.535) < 1e-3
    dup_step = state.reasoning_history[2]
    assert dup_step.event == "DUPLICATE_EVIDENCE_IGNORED"

# 10. Prior Semantics Audit & Distinction
def test_prior_semantics_distinction(belief_engine):
    p_alert = PRIOR_REGISTRY[PriorProfile.ALERT_CONDITIONED]["p_fraud"]
    assert p_alert == 0.8383
    assert PRIOR_REGISTRY[PriorProfile.ALERT_CONDITIONED]["classification"] == CalibrationClassification.EMPIRICAL
    
    p_pop = PRIOR_REGISTRY[PriorProfile.UNCONDITIONED_POPULATION]["p_fraud"]
    assert p_pop == 0.005
    assert PRIOR_REGISTRY[PriorProfile.UNCONDITIONED_POPULATION]["classification"] == CalibrationClassification.PROVISIONAL

    p_uniform = PRIOR_REGISTRY[PriorProfile.UNIFORM_NON_INFORMATIVE]["p_fraud"]
    assert p_uniform == 0.50

# 11. Honest LR Registry Classifications
def test_lr_registry_honesty():
    card_testing = LIKELIHOOD_REGISTRY["CARD_TESTING_SEQUENCE"]
    assert card_testing.classification == CalibrationClassification.PROVISIONAL
    assert card_testing.family == EvidenceFamily.TRANSACTION_VELOCITY
    
    cust_denial = LIKELIHOOD_REGISTRY["CUSTOMER_DENIAL"]
    assert cust_denial.classification == CalibrationClassification.POLICY_DEFINED
    assert cust_denial.family == EvidenceFamily.CUSTOMER_DISPUTE

    out_of_region = LIKELIHOOD_REGISTRY["OUT_OF_REGION"]
    assert out_of_region.classification == CalibrationClassification.EMPIRICAL
    assert out_of_region.family == EvidenceFamily.GEOGRAPHIC_LOCATION

# 12. Correlated Evidence Handling & Diminishing Returns
def test_correlated_evidence_diminishing_returns(belief_engine):
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="device", finding="ring", lr=14.2, log_lr=2.653))
    ledger.add(EvidenceItem(evidence_type=EvidenceType.PROXY_DETECTED, source="device", finding="proxy", lr=3.8, log_lr=1.335))
    
    res = belief_engine.evaluate_investigation("INV-CORR", {}, {}, ledger, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    step2 = res.reasoning_history[2]
    assert step2.discount_factor == 0.5
    assert abs(step2.effective_log_lr - (1.335 * 0.5)) < 1e-3

# 13. Phase 3.1 Hardened Ablation Matrix (Runs A through E)
def test_ablation_matrix_phase3_1(belief_engine):
    # Ablation A: No graph evidence
    ledger_a = EvidenceLedger()
    state_a = belief_engine.evaluate_investigation("ABL-A", {}, {}, ledger_a, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    assert state_a.belief_state["fraud_probability"] == 0.5
    assert state_a.uncertainty.evidence_coverage == 0.0
    assert state_a.decision_state == DecisionState.INSUFFICIENT_EVIDENCE
    assert state_a.decision_gate_passed is False

    # Ablation B: One graph evidence family (Transaction Velocity, coverage = 0.20)
    # Even though posterior is high (>0.95), gate blocks automated decision because coverage < 0.40!
    ledger_b = EvidenceLedger()
    ledger_b.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="pattern_analysis",
        finding="Card testing sequence",
        lr=34.3,
        log_lr=3.535
    ))
    state_b = belief_engine.evaluate_investigation("ABL-B", {}, {}, ledger_b, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    assert state_b.belief_state["fraud_probability"] > 0.95
    assert state_b.primary_hypothesis == WorldHypothesis.FRAUD
    assert state_b.uncertainty.evidence_coverage == 0.20
    assert state_b.decision_gate_passed is False
    assert state_b.decision_state == DecisionState.INSUFFICIENT_EVIDENCE

    # Ablation C: Multiple correlated graph evidence in single family (Device Infrastructure, coverage = 0.20)
    ledger_c = EvidenceLedger()
    ledger_c.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="device", finding="ring", lr=14.2, log_lr=2.653))
    ledger_c.add(EvidenceItem(evidence_type=EvidenceType.PROXY_DETECTED, source="device", finding="proxy", lr=3.8, log_lr=1.335))
    state_c = belief_engine.evaluate_investigation("ABL-C", {}, {}, ledger_c, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    assert state_c.uncertainty.evidence_coverage == 0.20
    assert state_c.decision_gate_passed is False
    assert state_c.decision_state == DecisionState.INSUFFICIENT_EVIDENCE

    # Ablation D: Contradictory evidence (Device Ring + Customer Confirmation)
    ledger_d = EvidenceLedger()
    ledger_d.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="device", finding="ring", lr=14.2, log_lr=2.653))
    ledger_d.add(EvidenceItem(evidence_type=EvidenceType.CUSTOMER_CONFIRMATION, source="cust", finding="confirmed", lr=0.05, log_lr=-2.996, is_exculpatory=True))
    state_d = belief_engine.evaluate_investigation("ABL-D", {}, {}, ledger_d, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    assert len(state_d.contradictions) == 1
    assert state_d.uncertainty.aleatoric_uncertainty >= 0.40
    assert state_d.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL

    # Ablation E: Out-of-scope evidence
    ledger_e = EvidenceLedger()
    ledger_e.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        value="DATA_OUT_OF_SCOPE",
        source="device_analysis",
        finding="Historical device data out of scope",
        graph_query="device_analysis"
    ))
    state_e = belief_engine.evaluate_investigation("ABL-E", {}, {}, ledger_e, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    assert state_e.belief_state["net_log_lr"] == 0.0
    assert len(state_e.missing_information) == 1
    assert state_e.uncertainty.epistemic_uncertainty > 0.5
    assert state_e.decision_gate_passed is False
