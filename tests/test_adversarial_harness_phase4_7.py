import os
import re
import pytest
from typing import Dict, Any, List

from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine, ActionRole, ActionScope
from src.compass.evoi import EvidenceCompass
from src.tools.dispatcher import EvidenceToolDispatcher
from src.agent.orchestrator import InvestigationOrchestrator, InvestigationTerminationReason
from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceType, EvidenceItem, EvidenceDirection
from src.belief.calibration import PriorProfile, EvidenceFamily
from src.belief.state import DecisionState, WorldHypothesis
from src.graph.scope import GraphScope, GraphScopeStatus
from src.knowledge.retriever import PolicyGraphRAGRetriever
from src.memory.store import CaseMemoryStore
from src.memory.retriever import SimilarCaseRetriever

@pytest.fixture
def harness():
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    compass = EvidenceCompass(belief_engine, policy_engine)
    dispatcher = EvidenceToolDispatcher(belief_engine)
    orchestrator = InvestigationOrchestrator(
        compass=compass,
        dispatcher=dispatcher,
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        max_steps=5,
        consecutive_failure_limit=2
    )
    return {
        "belief_engine": belief_engine,
        "policy_engine": policy_engine,
        "compass": compass,
        "dispatcher": dispatcher,
        "orchestrator": orchestrator
    }

# ==============================================================================
# FAMILY A: CONTRADICTORY EVIDENCE
# ==============================================================================

def test_scenario_a1_high_risk_score_with_clean_graph(harness):
    """A1: High risk score (0.90) + clean device + normal velocity + normal region."""
    belief_engine = harness["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model", finding="Score 0.90", lr=12.0, log_lr=2.485
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device", finding="No ring observed", lr=1.0, log_lr=0.0,
        details={"scope_status": "NO_MATCH"}
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.HIGH_VELOCITY,
        source="velocity", finding="Normal velocity", lr=1.0, log_lr=0.0,
        details={"scope_status": "NO_MATCH"}
    ))
    state = belief_engine.evaluate_investigation(
        "ADV-A1", {"trigger_type": "risk_score"}, {"card_id": "C-ADV-1"}, ledger, PriorProfile.ALERT_CONDITIONED
    )
    # Neutral NO_MATCH does not destroy high risk score, but does not add false corroboration
    assert state.belief_state["fraud_probability"] > 0.90
    assert len(state.evidence_items) == 3

def test_scenario_a2_high_risk_score_shared_device_normal_sequence(harness):
    """A2: High risk score + shared device ring + clean card sequence."""
    belief_engine = harness["belief_engine"]
    policy_engine = harness["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model", finding="Score 0.85", lr=8.0, log_lr=2.079
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device", finding="Shared ring across 20 cards", lr=14.2, log_lr=2.653
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="sequence", finding="No card testing sequence", lr=1.0, log_lr=0.0,
        details={"scope_status": "NO_MATCH"}
    ))
    state = belief_engine.evaluate_investigation(
        "ADV-A2", {"trigger_type": "risk_score"}, {"card_id": "C-ADV-2"}, ledger, PriorProfile.ALERT_CONDITIONED
    )
    assert state.belief_state["fraud_probability"] > 0.98
    actions = policy_engine.evaluate(
        fraud_probability=state.belief_state["fraud_probability"],
        verdict="confirmed_fraud",
        exposure_usd=100.0,
        ledger=ledger,
        case_context={"case_id": "ADV-A2"}
    )
    # Should trigger R6 (device ring) rather than R5 (card testing)
    assert actions[0].action == "CREATE_CASE"
    assert "R6" in actions[0].reason

def test_scenario_a3_customer_denial_with_clean_device(harness):
    """A3: Customer denial + clean device + normal txn history."""
    belief_engine = harness["belief_engine"]
    policy_engine = harness["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_DENIAL,
        source="dispute", finding="I did not make this charge", lr=18.5, log_lr=2.918
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device", finding="Device clean", lr=1.0, log_lr=0.0,
        details={"scope_status": "NO_MATCH"}
    ))
    state = belief_engine.evaluate_investigation(
        "ADV-A3", {"trigger_type": "customer_report"}, {"card_id": "C-ADV-3"}, ledger, PriorProfile.ALERT_CONDITIONED
    )
    actions = policy_engine.evaluate(
        fraud_probability=state.belief_state["fraud_probability"],
        verdict="confirmed_fraud",
        exposure_usd=50.0,
        ledger=ledger,
        case_context={"case_id": "ADV-A3", "trigger_type": "customer_report"}
    )
    # Under dispute without card testing, R2 mandates BLOCK_CARD
    assert actions[0].action == "BLOCK_CARD"

def test_scenario_a4_shared_device_with_exculpatory_customer_confirmation(harness):
    """A4: Shared device ring + strong customer confirmation of authorization (aleatoric conflict)."""
    belief_engine = harness["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device", finding="Shared ring across 30 cards", lr=14.2, log_lr=2.653
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_CONFIRMATION,
        source="verification", finding="Cardholder verified authorization", lr=0.05, log_lr=-2.996, is_exculpatory=True
    ))
    state = belief_engine.evaluate_investigation(
        "ADV-A4", {"trigger_type": "risk_score"}, {"card_id": "C-ADV-4"}, ledger, PriorProfile.ALERT_CONDITIONED
    )
    # Strong contradiction must be detected
    assert len(state.contradictions) >= 1
    assert state.uncertainty.aleatoric_uncertainty >= 0.40
    assert state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL

def test_scenario_a5_card_testing_with_contradicting_exculpatory_confirmation(harness):
    """A5: Card testing sequence + customer confirmation."""
    belief_engine = harness["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="sequence", finding="3 micro-authorizations detected", lr=34.3, log_lr=3.535
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_CONFIRMATION,
        source="verification", finding="Customer says they authorized all 4 charges", lr=0.05, log_lr=-2.996, is_exculpatory=True
    ))
    state = belief_engine.evaluate_investigation(
        "ADV-A5", {"trigger_type": "risk_score"}, {"card_id": "C-ADV-5"}, ledger, PriorProfile.ALERT_CONDITIONED
    )
    assert state.uncertainty.aleatoric_uncertainty >= 0.40
    assert state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL

# ==============================================================================
# FAMILY B: MISLEADING SHARED DEVICE
# ==============================================================================

def test_scenario_b1_shared_device_with_unconditioned_low_prior(harness):
    """B1: Shared device on unconditioned transaction stream without prior alert."""
    belief_engine = harness["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device", finding="Device shared across 5 cards", lr=14.2, log_lr=2.653
    ))
    # Unconditioned population prior: p = 0.005 (log-odds = -5.293)
    state = belief_engine.evaluate_investigation(
        "ADV-B1", {"trigger_type": "routine_scan"}, {"card_id": "C-ADV-B1"}, ledger, PriorProfile.UNCONDITIONED_POPULATION
    )
    # Posterior log-odds: -5.293 + 2.653 = -2.640 -> p ~ 0.066
    assert state.belief_state["fraud_probability"] < 0.15
    # Does not falsely conclude confirmed fraud from device sharing alone on unconditioned base rate
    assert state.primary_hypothesis == WorldHypothesis.LEGITIMATE

def test_scenario_b2_shared_device_alone_does_not_trigger_r5(harness):
    """B2: Shared device alone does NOT trigger card testing decline rule (R5)."""
    policy_engine = harness["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device", finding="Shared ring across 15 cards", lr=14.2, log_lr=2.653
    ))
    actions = policy_engine.evaluate(
        fraud_probability=0.95,
        verdict="confirmed_fraud",
        exposure_usd=150.0,
        ledger=ledger,
        case_context={"case_id": "ADV-B2"}
    )
    # Must trigger R6 (CREATE_CASE / MONITOR_CONNECTED_CARDS), not R5
    assert actions[0].action == "CREATE_CASE"
    assert not any(a.action == "DECLINE_TRANSACTION" for a in actions)

# ==============================================================================
# FAMILY C: CARD TESTING FALSE POSITIVES
# ==============================================================================

def test_scenario_c1_missing_temporal_scope_cannot_trigger_r5(harness):
    """C1: Missing temporal scope returns GRAPH_QUERY_FAILURE with LR=1.0 and cannot trigger R5."""
    policy_engine = harness["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="tigergraph_query:card_sequence",
        finding="Missing required parameter anchor_ts",
        lr=1.0, log_lr=0.0,
        value="GRAPH_QUERY_FAILURE",
        details={"scope_status": "GRAPH_QUERY_FAILURE"}
    ))
    actions = policy_engine.evaluate(
        fraud_probability=0.90,
        verdict="confirmed_fraud",
        exposure_usd=120.0,
        ledger=ledger,
        case_context={"case_id": "ADV-C1"}
    )
    # Must NOT trigger R5
    assert not any("R5" in a.reason for a in actions)
    assert actions[0].action != "DECLINE_TRANSACTION"

def test_scenario_c2_no_match_cannot_trigger_r5(harness):
    """C2: Valid scoped query with NO_MATCH cannot trigger R5."""
    policy_engine = harness["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="tigergraph_query:card_sequence",
        finding="No micro-authorizations within 24h window",
        lr=1.0, log_lr=0.0,
        value="NO_MATCH",
        details={"scope_status": "NO_MATCH"}
    ))
    actions = policy_engine.evaluate(
        fraud_probability=0.90,
        verdict="confirmed_fraud",
        exposure_usd=120.0,
        ledger=ledger,
        case_context={"case_id": "ADV-C2"}
    )
    assert not any("R5" in a.reason for a in actions)

# ==============================================================================
# FAMILY D & E: TEMPORAL CONFUSION & NEGATIVE EVIDENCE
# ==============================================================================

def test_scenario_e1_multiple_no_match_do_not_drive_p_fraud_down(harness):
    """E1: Multiple NO_MATCH findings do not artificially drive fraud probability down."""
    belief_engine = harness["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model", finding="Score 0.75", lr=5.0, log_lr=1.609
    ))
    state_initial = belief_engine.evaluate_investigation(
        "ADV-E1", {"trigger_type": "risk_score"}, {"card_id": "C-ADV-E1"}, ledger, PriorProfile.ALERT_CONDITIONED
    )
    p_initial = state_initial.belief_state["fraud_probability"]
    
    # Add 3 NO_MATCH items across different tools
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device", finding="No ring", lr=1.0, log_lr=0.0, details={"scope_status": "NO_MATCH"}
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="sequence", finding="No card testing", lr=1.0, log_lr=0.0, details={"scope_status": "NO_MATCH"}
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.HIGH_VELOCITY,
        source="velocity", finding="Normal velocity", lr=1.0, log_lr=0.0, details={"scope_status": "NO_MATCH"}
    ))
    state_after = belief_engine.evaluate_investigation(
        "ADV-E1", {"trigger_type": "risk_score"}, {"card_id": "C-ADV-E1"}, ledger, PriorProfile.ALERT_CONDITIONED
    )
    p_after = state_after.belief_state["fraud_probability"]
    
    # Neutral absence of pattern must preserve exact log-odds and probability
    assert abs(p_initial - p_after) < 1e-4

# ==============================================================================
# FAMILY F: DUPLICATE / REPEATED EVIDENCE
# ==============================================================================

def test_scenario_f1_duplicate_evidence_deduplication(harness):
    """F1: Identical evidence item ingested twice is deduplicated without belief inflation."""
    belief_engine = harness["belief_engine"]
    item = EvidenceItem(
        evidence_id="EVD-UNIQUE-001",
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device", finding="Shared ring across 12 cards", lr=14.2, log_lr=2.653
    )
    ledger = EvidenceLedger(items=[item, item])
    state = belief_engine.evaluate_investigation(
        "ADV-F1", {"trigger_type": "risk_score"}, {"card_id": "C-ADV-F1"}, ledger, PriorProfile.ALERT_CONDITIONED
    )
    # Applied only once
    eval_steps = [s for s in state.reasoning_history if s.event == "EVIDENCE_EVALUATED"]
    dedup_steps = [s for s in state.reasoning_history if s.event == "DUPLICATE_EVIDENCE_IGNORED"]
    assert len(eval_steps) == 1
    assert len(dedup_steps) == 1

def test_scenario_f2_same_family_correlation_damping(harness):
    """F2: Two distinct items from same family receive correlation damping (w=1.0 then w=0.5)."""
    belief_engine = harness["belief_engine"]
    item1 = EvidenceItem(
        evidence_id="EVD-DEV-001",
        evidence_type=EvidenceType.PROXY_DETECTED,
        source="device", finding="Proxy IP detected", lr=3.8, log_lr=1.335
    )
    item2 = EvidenceItem(
        evidence_id="EVD-DEV-002",
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device", finding="Shared ring across 10 cards", lr=14.2, log_lr=2.653
    )
    ledger = EvidenceLedger(items=[item1, item2])
    state = belief_engine.evaluate_investigation(
        "ADV-F2", {"trigger_type": "risk_score"}, {"card_id": "C-ADV-F2"}, ledger, PriorProfile.ALERT_CONDITIONED
    )
    steps = [s for s in state.reasoning_history if s.event == "EVIDENCE_EVALUATED"]
    assert steps[0].discount_factor == 1.0
    assert steps[1].discount_factor == 0.5
    assert steps[1].effective_log_lr == round(2.653 * 0.5, 4)

# ==============================================================================
# FAMILY G & H: MEMORY & GRAPHRAG CONTEXT ISOLATION
# ==============================================================================

def test_scenario_g1_memory_and_graphrag_do_not_alter_belief(harness):
    """G1/H1: Retrieved historical memory and GraphRAG knowledge do NOT alter P(Fraud)."""
    belief_engine = harness["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model", finding="Score 0.61", lr=2.4, log_lr=0.875
    ))
    state = belief_engine.evaluate_investigation(
        "ADV-GH1", {"trigger_type": "risk_score"}, {"card_id": "C-ADV-GH1"}, ledger, PriorProfile.ALERT_CONDITIONED
    )
    prob_before = state.belief_state["fraud_probability"]
    
    # Retrieve contextual memory and GraphRAG
    memory_store = CaseMemoryStore()
    memory_retriever = SimilarCaseRetriever(store=memory_store)
    precedents = memory_retriever.retrieve_similar_cases(
        state=state,
        pattern="shared_device_ring",
        top_k=3
    )
    graphrag = PolicyGraphRAGRetriever()
    knowledge = graphrag.retrieve_grounded_context(state=state, exposure_usd=250.0)
    
    assert len(precedents) > 0
    assert len(knowledge) > 0
    # Provenance check: all precedents must be labeled CONTEXTUAL_PRECEDENT_ONLY
    for p in precedents:
        assert p.role == "CONTEXTUAL_PRECEDENT_ONLY"
    # Belief state remains uncorrupted
    prob_after = state.belief_state["fraud_probability"]
    assert prob_before == prob_after

# ==============================================================================
# FAMILY I: TOOL FAILURE SEMANTICS
# ==============================================================================

def test_scenario_i1_tool_failure_produces_zero_log_odds_shift(harness):
    """I1: Tool failure produces GRAPH_QUERY_FAILURE with zero log-odds shift and records missing info."""
    dispatcher = harness["dispatcher"]
    belief_engine = harness["belief_engine"]
    state0 = belief_engine.evaluate_investigation(
        "ADV-I1", {"trigger_type": "risk_score"}, {"card_id": "C-ADV-I1"}, EvidenceLedger(), PriorProfile.ALERT_CONDITIONED
    )
    p0 = state0.belief_state["fraud_probability"]
    
    # Pass None connection to force failure
    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state0,
        candidate_action="QUERY_DEVICE_ANALYSIS",
        parameters={"t_id": "9999"},
        context={"tg_conn": None}
    )
    assert res.scope_status == GraphScopeStatus.GRAPH_QUERY_FAILURE
    assert res.evidence_item.lr == 1.0
    assert res.evidence_item.log_lr == 0.0
    assert abs(updated_state.belief_state["fraud_probability"] - p0) < 1e-4
    assert any(m.reason == "GRAPH_QUERY_FAILURE" for m in updated_state.missing_information)

# ==============================================================================
# FAMILY L: ANALYST REQUEST GENERALIZATION
# ==============================================================================

def test_scenario_l1_low_risk_analyst_request_economic_containment(harness):
    """L1: Analyst request on tiny $5 exposure does not execute expensive $20 customer verification."""
    compass = harness["compass"]
    belief_engine = harness["belief_engine"]
    state = belief_engine.evaluate_investigation(
        "ADV-L1",
        {"trigger_type": "analyst_request", "flagged_txn_id": "111", "timestamp": "2016-11-22 20:11:00"},
        {"card_id": "C-L1", "customer_id": "CUST-L1", "flagged_txn_id": "111", "timestamp": "2016-11-22 20:11:00"},
        EvidenceLedger(),
        PriorProfile.ALERT_CONDITIONED
    )
    rec = compass.evaluate_evidence_compass(state, exposure_usd=5.0)
    customer_verif = [c for c in rec.ranked_candidates if c.action_id == "VERIFY_WITH_CUSTOMER"]
    if customer_verif:
        assert customer_verif[0].net_decision_value <= 0.0

def test_scenario_l2_analyst_request_with_graph_anomaly(harness):
    """L2: Analyst request prioritizes high-diagnostic GSQL query."""
    compass = harness["compass"]
    belief_engine = harness["belief_engine"]
    state = belief_engine.evaluate_investigation(
        "ADV-L2",
        {"trigger_type": "analyst_request", "flagged_txn_id": "222", "timestamp": "2016-11-22 20:11:00"},
        {"card_id": "C-L2", "customer_id": "CUST-L2", "flagged_txn_id": "222", "timestamp": "2016-11-22 20:11:00"},
        EvidenceLedger(),
        PriorProfile.ALERT_CONDITIONED
    )
    rec = compass.evaluate_evidence_compass(state, exposure_usd=100.0)
    assert not rec.should_stop_gathering
    top_act = rec.top_recommendation.action_id
    assert top_act in ["QUERY_DEVICE_ANALYSIS", "QUERY_CARD_SEQUENCE", "QUERY_TXN_VELOCITY"]

# ==============================================================================
# FAMILY M: BELIEF UPDATE INTEGRITY
# ==============================================================================

def test_scenario_m1_extreme_lr_bounded_probability(harness):
    """M1: Extreme LR values remain strictly within [0.0001, 0.9999] without NaN or overflow."""
    belief_engine = harness["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_DENIAL,
        source="extreme", finding="Massive signal", lr=10000.0, log_lr=9.21
    ))
    state = belief_engine.evaluate_investigation(
        "ADV-M1", {"trigger_type": "risk_score"}, {"card_id": "C-M1"}, ledger, PriorProfile.ALERT_CONDITIONED
    )
    p = state.belief_state["fraud_probability"]
    assert 0.0 < p < 1.0
    assert p <= 0.9999

# ==============================================================================
# FAMILY N: POLICY PRECONDITION INTEGRITY
# ==============================================================================

def test_scenario_n1_r5_strict_precondition(harness):
    """N1: R5 DECLINE_TRANSACTION strictly requires genuine CARD_TESTING_SEQUENCE."""
    policy_engine = harness["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model", finding="High score", lr=10.0, log_lr=2.302
    ))
    actions = policy_engine.evaluate(
        fraud_probability=0.99,
        verdict="confirmed_fraud",
        exposure_usd=100.0,
        ledger=ledger,
        case_context={"case_id": "ADV-N1"}
    )
    # Without CARD_TESTING_SEQUENCE, R5 cannot fire
    assert actions[0].action != "DECLINE_TRANSACTION"
    assert not any("R5" in a.reason for a in actions)

def test_scenario_n2_r6_strict_precondition(harness):
    """N2: R6 ring actions strictly require genuine SHARED_DEVICE_RING."""
    policy_engine = harness["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model", finding="Score 0.80", lr=6.0, log_lr=1.791
    ))
    actions = policy_engine.evaluate(
        fraud_probability=0.95,
        verdict="confirmed_fraud",
        exposure_usd=100.0,
        ledger=ledger,
        case_context={"case_id": "ADV-N2"}
    )
    # R6 reason must not appear without SHARED_DEVICE_RING
    assert not any("R6" in a.reason for a in actions)
    assert not any(a.action == "MONITOR_CONNECTED_CARDS" for a in actions)

# ==============================================================================
# FAMILY O: BENCHMARK-LEAKAGE DETECTION
# ==============================================================================

def test_scenario_o1_synthetic_case_id_parity(harness):
    """O1: Synthetic Case ID produces identical evidence & policy behavior as benchmark format."""
    belief_engine = harness["belief_engine"]
    policy_engine = harness["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="sequence", finding="3 micro-authorizations detected", lr=34.3, log_lr=3.535
    ))
    state_synth = belief_engine.evaluate_investigation(
        "SYNTHETIC-999-XYZ", {"trigger_type": "risk_score"}, {"card_id": "CARD-SYNTH-999"}, ledger, PriorProfile.ALERT_CONDITIONED
    )
    actions_synth = policy_engine.evaluate(
        fraud_probability=state_synth.belief_state["fraud_probability"],
        verdict="confirmed_fraud",
        exposure_usd=150.0,
        ledger=ledger,
        case_context={"case_id": "SYNTHETIC-999-XYZ"}
    )
    assert actions_synth[0].action == "DECLINE_TRANSACTION"
    assert actions_synth[0].role == ActionRole.PRIMARY

def test_scenario_o2_codebase_zero_benchmark_branches():
    """O2: Search all python source files for benchmark ID string branches (e.g. 'HHG-011' in if statements)."""
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    suspicious_patterns = [
        r'if\s+.*["\']HHG-\d+["\']',
        r'elif\s+.*["\']HHG-\d+["\']',
        r'case_id\s*==\s*["\']HHG-\d+["\']',
        r'case_id\s+in\s+\[.*HHG-.*\]'
    ]
    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    for pat in suspicious_patterns:
                        matches = re.findall(pat, content)
                        assert len(matches) == 0, f"Found benchmark ID branch '{matches}' in {file_path}"
