import pytest
from typing import Dict, Any

from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceItem, EvidenceType
from src.belief.calibration import PriorProfile, EvidenceFamily
from src.belief.state import (
    InvestigationState,
    DecisionState,
    WorldHypothesis,
    MissingInfoItem
)
from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine
from src.compass.evoi import (
    EvidenceCompass,
    EvidenceActionType,
    CandidateEvidenceEvaluation,
    EvidenceCompassRecommendation,
    calculate_operational_loss
)

@pytest.fixture
def belief_engine():
    return BeliefEngine()

@pytest.fixture
def policy_engine():
    return PolicyEngine()

@pytest.fixture
def compass(belief_engine, policy_engine):
    return EvidenceCompass(belief_engine, policy_engine)

# 1. Reproduce the Phase 3.2 Worked EVOI Example
def test_reproduce_phase3_2_worked_example(compass, belief_engine):
    # Setup initial state matching Phase 3.2 Section 8:
    # Flagged transaction: $100 exposure, initial P(Fraud) = 0.65
    ledger = EvidenceLedger()
    # Add an initial model score evidence item to give coverage 0.20 and P(Fraud) = 0.65
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="realtime_model",
        finding="Model scored transaction at 0.61",
        lr=2.4,
        log_lr=0.875,
        details={"risk_score": 0.61}
    ))
    
    state = belief_engine.evaluate_investigation(
        investigation_id="WORKED-EXAMPLE-001",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "TXN-100"},
        target_entities={"card_id": "CARD-TEST", "customer_id": "CUST-TEST"},
        ledger=ledger,
        prior_p=0.43634  # Chosen so logit(0.43634) + 0.875 = 0.6190 -> p = 0.6500
    )
    
    assert abs(state.belief_state["fraud_probability"] - 0.6500) < 1e-3
    assert state.uncertainty.evidence_coverage == 0.20
    assert state.decision_gate_passed is False
    assert state.decision_state == DecisionState.INSUFFICIENT_EVIDENCE
    
    rec = compass.evaluate_evidence_compass(
        state,
        exposure_usd=100.0,
        candidate_action_ids=["QUERY_DEVICE_ANALYSIS", "VERIFY_WITH_CUSTOMER", "QUERY_CARD_SEQUENCE"]
    )
    
    # Verify baseline loss under MONITOR_CARD: 0.65 * $70 + 0.35 * $2 = $46.20
    assert rec.current_primary_action == "MONITOR_CARD"
    cands_by_id = {c.action_id: c for c in rec.ranked_candidates}
    
    # Candidate A: card_sequence
    cand_a = cands_by_id["QUERY_CARD_SEQUENCE"]
    assert abs(cand_a.baseline_expected_loss - 46.20) < 0.10
    assert abs(cand_a.expected_decision_value - 11.96) < 0.30
    assert cand_a.operational_burden_cost == 1.0
    assert abs(cand_a.net_decision_value - 10.96) < 0.30
    
    # Candidate B: device_analysis
    cand_b = cands_by_id["QUERY_DEVICE_ANALYSIS"]
    assert abs(cand_b.expected_decision_value - 14.84) < 0.30
    assert cand_b.operational_burden_cost == 1.0
    assert abs(cand_b.net_decision_value - 13.84) < 0.30
    
    # Candidate C: VERIFY_WITH_CUSTOMER
    cand_c = cands_by_id["VERIFY_WITH_CUSTOMER"]
    assert abs(cand_c.expected_decision_value - 31.41) < 0.50
    assert cand_c.operational_burden_cost == 20.0
    assert abs(cand_c.net_decision_value - 11.41) < 0.50
    
    # Verify exact ranking:
    # 1. QUERY_DEVICE_ANALYSIS (Net ~ 13.84)
    # 2. VERIFY_WITH_CUSTOMER (Net ~ 11.41)
    # 3. QUERY_CARD_SEQUENCE (Net ~ 10.96)
    assert rec.ranked_candidates[0].action_id == "QUERY_DEVICE_ANALYSIS"
    assert rec.ranked_candidates[1].action_id == "VERIFY_WITH_CUSTOMER"
    assert rec.ranked_candidates[2].action_id == "QUERY_CARD_SEQUENCE"
    assert rec.top_recommendation.action_id == "QUERY_DEVICE_ANALYSIS"
    assert rec.should_stop_gathering is False

# 2. Cheap Graph Query Beats Expensive Customer Verification
def test_cheap_graph_beats_expensive_customer_verification(compass, belief_engine):
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model",
        finding="Score 0.61",
        lr=2.4,
        log_lr=0.875
    ))
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-CHEAP-GRAPH",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "TXN-200"},
        target_entities={"card_id": "CARD-1", "customer_id": "CUST-1"},
        ledger=ledger,
        prior_p=0.43634
    )
    
    rec = compass.evaluate_evidence_compass(state, exposure_usd=100.0)
    cands = {c.action_id: c for c in rec.ranked_candidates}
    
    # Raw EDV of customer verification is higher
    assert cands["VERIFY_WITH_CUSTOMER"].expected_decision_value > cands["QUERY_DEVICE_ANALYSIS"].expected_decision_value
    # BUT Net Decision Value of device analysis is higher due to low operational burden ($1 vs $20)
    assert cands["QUERY_DEVICE_ANALYSIS"].net_decision_value > cands["VERIFY_WITH_CUSTOMER"].net_decision_value
    assert rec.top_recommendation.action_id == "QUERY_DEVICE_ANALYSIS"

# 3. High-Probability / No-Action-Change Saturation Stoppage
def test_high_probability_saturation_stopping(compass, belief_engine):
    # A case already confirmed with card testing, device ring, and exposure $2,000
    # Posterior is 0.999, coverage is 0.40, Gate passed, Action is BLOCK_CARD + FILE_REPORT
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="card_sequence",
        finding="3 micro-authorizations followed by charge",
        lr=34.3,
        log_lr=3.535
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device_analysis",
        finding="Device shared with 5 cards",
        lr=14.2,
        log_lr=2.653
    ))
    
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-SATURATED",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "TXN-SAT"},
        target_entities={"card_id": "CARD-SAT", "customer_id": "CUST-SAT"},
        ledger=ledger,
        prior_p=0.50
    )
    
    assert state.decision_gate_passed is True
    assert state.belief_state["fraud_probability"] > 0.99
    
    rec = compass.evaluate_evidence_compass(state, exposure_usd=2000.0)
    
    # Since action is already maximal severity (BLOCK_CARD + FILE_REPORT), further evidence cannot change the action
    # All remaining candidates must have EDV == 0.0 and Net <= 0
    assert rec.should_stop_gathering is True
    assert "saturated" in rec.stopping_reason.lower() or "exhausted" in rec.stopping_reason.lower()
    for c in rec.ranked_candidates:
        assert c.expected_decision_value == 0.0
        assert c.net_decision_value <= 0.0

# 4. Decision-Boundary Crossing Preference
def test_decision_boundary_crossing(compass, belief_engine):
    # Case with P(Fraud) = 0.68 and exposure $1,200
    # Under policy rule R8, P in (0.30, 0.70) with exposure > $500 -> ESCALATE_TO_ANALYST
    # Evidence that pushes P >= 0.70 crosses the regulatory boundary into mandatory BLOCK_CARD + FILE_REPORT (L2 SAR)
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model",
        finding="Score 0.68",
        lr=2.4,
        log_lr=0.875
    ))
    
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-BOUNDARY",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "TXN-BND"},
        target_entities={"card_id": "CARD-BND", "customer_id": "CUST-BND"},
        ledger=ledger,
        prior_p=0.48
    )
    
    rec = compass.evaluate_evidence_compass(state, exposure_usd=1200.0)
    
    # Top candidates must have high positive EDV because they cross the boundary into decisive SAR filing
    assert rec.top_recommendation is not None
    assert rec.top_recommendation.expected_decision_value > 50.0
    assert rec.top_recommendation.net_decision_value > 0.0

# 5. Contradiction Escalation Halts Automated Evidence Acquisition
def test_contradiction_escalation_halts_compass(compass, belief_engine):
    # Strong inculpatory (device ring) + strong exculpatory (customer confirmation)
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device",
        finding="Device ring",
        lr=14.2,
        log_lr=2.653
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_CONFIRMATION,
        source="cust",
        finding="Customer confirmed authorized",
        lr=0.05,
        log_lr=-2.996,
        is_exculpatory=True
    ))
    
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-CONTR-COMPASS",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "TXN-CONTR"},
        target_entities={"card_id": "CARD-C", "customer_id": "CUST-C"},
        ledger=ledger,
        prior_p=0.50
    )
    
    assert state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL
    assert state.uncertainty.aleatoric_uncertainty >= 0.40
    
    rec = compass.evaluate_evidence_compass(state, exposure_usd=500.0)
    
    # Compass MUST NOT bypass human review or propose automated resolution
    assert rec.should_stop_gathering is True
    assert "mandatory human review required" in rec.stopping_reason.lower()
    assert rec.top_recommendation is None

# 6. Out-of-Scope Fallback Handling
def test_out_of_scope_fallback(compass, belief_engine):
    # Card is outside 120-day graph slice -> device_analysis and card_sequence are DATA_OUT_OF_SCOPE
    ledger = EvidenceLedger()
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-OOS-COMPASS",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "TXN-OOS"},
        target_entities={"card_id": "CARD-OOS", "customer_id": "CUST-OOS"},
        ledger=ledger,
        prior_p=0.50
    )
    
    # Inject out-of-scope records into missing_information
    state.missing_information.append(MissingInfoItem(
        missing_id="MIS-1",
        dimension="SHARED_DEVICE_RING",
        entity="CARD-OOS",
        reason="DATA_OUT_OF_SCOPE",
        impact_severity="MEDIUM"
    ))
    state.missing_information.append(MissingInfoItem(
        missing_id="MIS-2",
        dimension="CARD_TESTING_SEQUENCE",
        entity="CARD-OOS",
        reason="DATA_OUT_OF_SCOPE",
        impact_severity="MEDIUM"
    ))
    
    rec = compass.evaluate_evidence_compass(state, exposure_usd=100.0)
    cand_ids = [c.action_id for c in rec.ranked_candidates]
    
    # Dead graph queries must NOT be recommended
    assert "QUERY_DEVICE_ANALYSIS" not in cand_ids
    assert "QUERY_CARD_SEQUENCE" not in cand_ids
    
    # External channels must be prioritized as viable fallback
    assert "STEP_UP_AUTH" in cand_ids or "VERIFY_WITH_CUSTOMER" in cand_ids

# 7. Correlated Evidence Diminishing Value
def test_correlated_evidence_diminishing_value(compass, belief_engine):
    # State with NO prior device evidence
    ledger_clean = EvidenceLedger()
    state_clean = belief_engine.evaluate_investigation("INV-C1", {}, {}, ledger_clean, prior_p=0.50)
    rec_clean = compass.evaluate_evidence_compass(state_clean, exposure_usd=100.0)
    cand_device_clean = next(c for c in rec_clean.ranked_candidates if c.action_id == "QUERY_DEVICE_ANALYSIS")
    
    # State where PROXY_DETECTED is already observed in the same DEVICE_INFRASTRUCTURE family
    ledger_proxy = EvidenceLedger()
    ledger_proxy.add(EvidenceItem(
        evidence_type=EvidenceType.PROXY_DETECTED,
        source="device",
        finding="Proxy IP detected",
        lr=3.8,
        log_lr=1.335
    ))
    state_proxy = belief_engine.evaluate_investigation("INV-C2", {}, {}, ledger_proxy, prior_p=0.50)
    rec_proxy = compass.evaluate_evidence_compass(state_proxy, exposure_usd=100.0)
    cand_device_proxy = next(c for c in rec_proxy.ranked_candidates if c.action_id == "QUERY_DEVICE_ANALYSIS")
    
    # When proxy is already in ledger, second device observation undergoes family damping (w=0.5)
    # Its EDV should be lower than when the family was unobserved
    outcome_clean = next(o for o in cand_device_clean.possible_outcomes if o.outcome_label == "SHARED_DEVICE_RING")
    outcome_proxy = next(o for o in cand_device_proxy.possible_outcomes if o.outcome_label == "SHARED_DEVICE_RING")
    
    # The clean state gets full log_lr = 2.653; proxy state gets damped addition
    assert outcome_clean.simulated_posterior > 0.90
    assert cand_device_clean.expected_decision_value >= cand_device_proxy.expected_decision_value

# 8. Zero Benchmark Leakage Test
def test_zero_benchmark_leakage(compass, belief_engine):
    # Run across arbitrary synthetic IDs
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model",
        finding="Score 0.65",
        lr=2.4,
        log_lr=0.875
    ))
    
    # Synthetic Case A
    state_a = belief_engine.evaluate_investigation(
        investigation_id="SYNTHETIC-ALPHA",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "RANDOM-111"},
        target_entities={"card_id": "CARD-XYZ", "customer_id": "CUST-XYZ"},
        ledger=ledger,
        prior_p=0.45
    )
    rec_a = compass.evaluate_evidence_compass(state_a, exposure_usd=100.0)
    
    # Synthetic Case B (identical numerical payload, completely different IDs)
    state_b = belief_engine.evaluate_investigation(
        investigation_id="SYNTHETIC-BETA",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "RANDOM-999"},
        target_entities={"card_id": "CARD-ABC", "customer_id": "CUST-ABC"},
        ledger=ledger,
        prior_p=0.45
    )
    rec_b = compass.evaluate_evidence_compass(state_b, exposure_usd=100.0)
    
    # The EVOI engine must produce identical mathematical rankings independent of case ID
    assert rec_a.top_recommendation.action_id == rec_b.top_recommendation.action_id
    assert abs(rec_a.top_recommendation.net_decision_value - rec_b.top_recommendation.net_decision_value) < 1e-6
    assert len(rec_a.ranked_candidates) == len(rec_b.ranked_candidates)
