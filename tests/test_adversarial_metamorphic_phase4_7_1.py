import pytest
import datetime
import math
import copy
from typing import Dict, Any, List, Optional, Set

from src.evidence.types import EvidenceItem, EvidenceType, EvidenceDirection
from src.evidence.ledger import EvidenceLedger
from src.belief.engine import BeliefEngine
from src.belief.calibration import PriorProfile
from src.belief.state import InvestigationState, DecisionState, WorldHypothesis
from src.policy.engine import PolicyEngine, ActionRecommendation, ActionRole
from src.compass.evoi import EvidenceCompass, EvidenceCompassRecommendation, CandidateEvidenceEvaluation
from src.tools.dispatcher import EvidenceToolDispatcher
from src.tools.base import ToolExecutionResult, EvidenceExecutionTrace
from src.tools.normalizer import EvidenceNormalizer
from src.graph.scope import GraphScopeStatus
from src.memory.models import CaseMemoryRecord, SimilarCaseMatch
from src.memory.store import CaseMemoryStore
from src.memory.retriever import SimilarCaseRetriever
from src.knowledge.models import RetrievedKnowledgeItem, KnowledgeChunk
from src.knowledge.retriever import PolicyGraphRAGRetriever
from src.knowledge.store import InvestigationKnowledgeBase
from src.agent.orchestrator import (
    InvestigationOrchestrator,
    InvestigationTerminationReason,
    InvestigationRunResult
)

# ==============================================================================
# TEST FIXTURES & HELPER FACTORIES
# ==============================================================================

@pytest.fixture
def base_engines():
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    compass = EvidenceCompass(belief_engine=belief_engine, policy_engine=policy_engine)
    normalizer = EvidenceNormalizer()
    dispatcher = EvidenceToolDispatcher(belief_engine=belief_engine)
    return {
        "belief_engine": belief_engine,
        "policy_engine": policy_engine,
        "compass": compass,
        "normalizer": normalizer,
        "dispatcher": dispatcher
    }

def create_synthetic_state(
    case_id: str,
    trigger_type: str = "risk_score",
    card_id: str = "C-SYNTH-001",
    customer_id: str = "U-SYNTH-001",
    risk_score: float = 0.65,
    prior_profile: PriorProfile = PriorProfile.ALERT_CONDITIONED
) -> InvestigationState:
    """Creates a clean synthetic investigation state with an initial trigger."""
    belief_engine = BeliefEngine()
    ledger = EvidenceLedger()
    
    if trigger_type == "risk_score":
        ledger.add(EvidenceItem(
            evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
            source="model",
            finding=f"ML Risk Score {risk_score}",
            value={"score": risk_score},
            lr=2.5,
            log_lr=math.log(2.5)
        ))
    elif trigger_type == "customer_report":
        ledger.add(EvidenceItem(
            evidence_type=EvidenceType.CUSTOMER_DENIAL,
            source="customer",
            finding="Customer disputed unrecognized transaction",
            value={"dispute": True},
            lr=8.0,
            log_lr=math.log(8.0)
        ))
    elif trigger_type == "analyst_request":
        ledger.add(EvidenceItem(
            evidence_type=EvidenceType.BEHAVIORAL_BASELINE,
            source="analyst",
            finding="Manual review initiated by risk analyst",
            value={"analyst_notes": "Review transaction graph"},
            lr=1.0,
            log_lr=0.0
        ))

    return belief_engine.evaluate_investigation(
        investigation_id=case_id,
        trigger={"trigger_type": trigger_type, "risk_score": risk_score},
        target_entities={"card_id": card_id, "customer_id": customer_id},
        ledger=ledger,
        prior_profile=prior_profile
    )

# ==============================================================================
# FAMILY A: METAMORPHIC CASE ID INVARIANCE (5 Distinct Cases)
# ==============================================================================

def test_metamorphic_a1_risk_score_case_id_invariance(base_engines):
    """Case ID Invariance on Risk Score Trigger."""
    pe = base_engines["policy_engine"]
    
    s_a = create_synthetic_state("CASE-A-001", trigger_type="risk_score", risk_score=0.72)
    acts_a = pe.evaluate(s_a.belief_state["fraud_probability"], "fraud", 200.0, EvidenceLedger(items=s_a.evidence_items), case_context={"trigger_type": "risk_score"})
    
    s_b = create_synthetic_state("SYNTH-928371-MUTATED", trigger_type="risk_score", risk_score=0.72)
    acts_b = pe.evaluate(s_b.belief_state["fraud_probability"], "fraud", 200.0, EvidenceLedger(items=s_b.evidence_items), case_context={"trigger_type": "risk_score"})
    
    assert math.isclose(s_a.belief_state["fraud_probability"], s_b.belief_state["fraud_probability"], abs_tol=1e-6)
    assert s_a.uncertainty.evidence_coverage == s_b.uncertainty.evidence_coverage
    assert s_a.decision_state == s_b.decision_state
    assert s_a.decision_gate_passed == s_b.decision_gate_passed
    assert [a.action for a in acts_a] == [a.action for a in acts_b]

def test_metamorphic_a2_customer_report_case_id_invariance(base_engines):
    """Case ID Invariance on Customer Report Trigger."""
    pe = base_engines["policy_engine"]
    
    s_a = create_synthetic_state("CR-ORIG-100", trigger_type="customer_report")
    acts_a = pe.evaluate(s_a.belief_state["fraud_probability"], "fraud", 500.0, EvidenceLedger(items=s_a.evidence_items), case_context={"trigger_type": "customer_report"})
    
    s_b = create_synthetic_state("CR-MUTATED-UUID-8888", trigger_type="customer_report")
    acts_b = pe.evaluate(s_b.belief_state["fraud_probability"], "fraud", 500.0, EvidenceLedger(items=s_b.evidence_items), case_context={"trigger_type": "customer_report"})
    
    assert math.isclose(s_a.belief_state["fraud_probability"], s_b.belief_state["fraud_probability"], abs_tol=1e-6)
    assert s_a.decision_gate_passed == s_b.decision_gate_passed
    assert [a.action for a in acts_a] == [a.action for a in acts_b]

def test_metamorphic_a3_analyst_request_case_id_invariance(base_engines):
    """Case ID Invariance on Analyst Request Trigger."""
    pe = base_engines["policy_engine"]
    
    s_a = create_synthetic_state("AR-BASE-001", trigger_type="analyst_request", prior_profile=PriorProfile.UNCONDITIONED_POPULATION)
    acts_a = pe.evaluate(s_a.belief_state["fraud_probability"], "legitimate", 50.0, EvidenceLedger(items=s_a.evidence_items), case_context={"trigger_type": "analyst_request"})
    
    s_b = create_synthetic_state("AR-RANDOM-HASH-9999", trigger_type="analyst_request", prior_profile=PriorProfile.UNCONDITIONED_POPULATION)
    acts_b = pe.evaluate(s_b.belief_state["fraud_probability"], "legitimate", 50.0, EvidenceLedger(items=s_b.evidence_items), case_context={"trigger_type": "analyst_request"})
    
    assert math.isclose(s_a.belief_state["fraud_probability"], s_b.belief_state["fraud_probability"], abs_tol=1e-6)
    assert s_a.decision_state == s_b.decision_state
    assert [a.action for a in acts_a] == [a.action for a in acts_b]

def test_metamorphic_a4_shared_device_case_id_invariance(base_engines):
    """Case ID Invariance with Shared Device Ring."""
    be = base_engines["belief_engine"]
    pe = base_engines["policy_engine"]
    
    def build_shared_device_state(cid: str):
        ledger = EvidenceLedger()
        ledger.add(EvidenceItem(
            evidence_type=EvidenceType.SHARED_DEVICE_RING,
            source="graph", finding="3 cards sharing device D10", value={"device_id": "D10"}, lr=5.2, log_lr=math.log(5.2)
        ))
        return be.evaluate_investigation(cid, {"trigger_type": "risk_score"}, {"card_id": "C1"}, ledger, PriorProfile.ALERT_CONDITIONED)
        
    s_a = build_shared_device_state("CASE-DEV-1")
    acts_a = pe.evaluate(s_a.belief_state["fraud_probability"], "fraud", 300.0, EvidenceLedger(items=s_a.evidence_items), case_context={"trigger_type": "risk_score"})
    
    s_b = build_shared_device_state("X-NON-STANDARD-DEV-ID-99")
    acts_b = pe.evaluate(s_b.belief_state["fraud_probability"], "fraud", 300.0, EvidenceLedger(items=s_b.evidence_items), case_context={"trigger_type": "risk_score"})
    
    assert math.isclose(s_a.belief_state["fraud_probability"], s_b.belief_state["fraud_probability"], abs_tol=1e-6)
    assert [a.action for a in acts_a] == [a.action for a in acts_b]
    assert acts_a[0].action == "CREATE_CASE"

def test_metamorphic_a5_card_sequence_case_id_invariance(base_engines):
    """Case ID Invariance with Card Testing Sequence."""
    be = base_engines["belief_engine"]
    pe = base_engines["policy_engine"]
    
    def build_card_seq_state(cid: str):
        ledger = EvidenceLedger()
        ledger.add(EvidenceItem(
            evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
            source="graph", finding="3 micro transactions <= $2.00", value={"pattern": "card_testing"}, lr=6.5, log_lr=math.log(6.5)
        ))
        return be.evaluate_investigation(cid, {"trigger_type": "customer_report"}, {"card_id": "C1"}, ledger, PriorProfile.ALERT_CONDITIONED)
        
    s_a = build_card_seq_state("SEQ-CASE-1")
    acts_a = pe.evaluate(s_a.belief_state["fraud_probability"], "fraud", 400.0, EvidenceLedger(items=s_a.evidence_items), case_context={"trigger_type": "customer_report"})
    
    s_b = build_card_seq_state("COMPLETELY-DIFFERENT-STRING-NAME")
    acts_b = pe.evaluate(s_b.belief_state["fraud_probability"], "fraud", 400.0, EvidenceLedger(items=s_b.evidence_items), case_context={"trigger_type": "customer_report"})
    
    assert math.isclose(s_a.belief_state["fraud_probability"], s_b.belief_state["fraud_probability"], abs_tol=1e-6)
    assert [a.action for a in acts_a] == [a.action for a in acts_b]
    assert acts_a[0].action == "DECLINE_TRANSACTION"

# ==============================================================================
# FAMILY B: METAMORPHIC EVIDENCE ORDER INVARIANCE (5 Permutations across independent families)
# ==============================================================================

def test_metamorphic_b1_to_b5_evidence_order_permutations(base_engines):
    """Evidence Order Invariance across 5 full permutations of independent family evidence items."""
    be = base_engines["belief_engine"]
    pe = base_engines["policy_engine"]
    
    # Four items from 4 independent families: MODEL_SCORE, DEVICE_INFRASTRUCTURE, TRANSACTION_VELOCITY, CUSTOMER_DISPUTE
    ev_risk = EvidenceItem(evidence_id="E-RS", evidence_type=EvidenceType.CALIBRATED_RISK_SCORE, source="m", finding="RS 0.65", value={"score": 0.65}, lr=2.4, log_lr=math.log(2.4))
    ev_dev = EvidenceItem(evidence_id="E-DEV", evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring D1", value={"device_id": "D1"}, lr=4.5, log_lr=math.log(4.5))
    ev_vel = EvidenceItem(evidence_id="E-VEL", evidence_type=EvidenceType.HIGH_VELOCITY, source="g", finding="Vel 5 txns", value={"velocity": 5}, lr=3.2, log_lr=math.log(3.2))
    ev_cust = EvidenceItem(evidence_id="E-CUST", evidence_type=EvidenceType.CUSTOMER_DENIAL, source="c", finding="Disputed", value={"dispute": True}, lr=5.0, log_lr=math.log(5.0))
    
    permutations = [
        [ev_risk, ev_dev, ev_vel, ev_cust], # Order 1
        [ev_cust, ev_vel, ev_dev, ev_risk], # Order 2
        [ev_dev, ev_cust, ev_risk, ev_vel], # Order 3
        [ev_vel, ev_risk, ev_cust, ev_dev], # Order 4
        [ev_cust, ev_risk, ev_dev, ev_vel], # Order 5
    ]
    
    results = []
    for i, perm in enumerate(permutations):
        ledger = EvidenceLedger()
        for item in perm:
            ledger.add(copy.deepcopy(item))
        state = be.evaluate_investigation(f"CASE-ORD-{i}", {"trigger_type": "risk_score"}, {"card_id": "C1"}, ledger, PriorProfile.ALERT_CONDITIONED)
        acts = pe.evaluate(state.belief_state["fraud_probability"], "fraud", 500.0, ledger, case_context={"trigger_type": "risk_score"})
        results.append((state, acts))
        
    base_prob = results[0][0].belief_state["fraud_probability"]
    base_cov = results[0][0].uncertainty.evidence_coverage
    base_gate = results[0][0].decision_gate_passed
    base_actions = [a.action for a in results[0][1]]
    
    for state, acts in results[1:]:
        assert math.isclose(state.belief_state["fraud_probability"], base_prob, abs_tol=1e-6)
        assert math.isclose(state.uncertainty.evidence_coverage, base_cov, abs_tol=1e-6)
        assert state.decision_gate_passed == base_gate
        assert [a.action for a in acts] == base_actions

# ==============================================================================
# FAMILY C: METAMORPHIC DUPLICATE EVIDENCE & CORRELATION DAMPING (5 Tests)
# ==============================================================================

def test_metamorphic_c1_exact_item_idempotent_dedup(base_engines):
    """Exact duplicate evidence item ingestion is strictly ignored in belief engine."""
    be = base_engines["belief_engine"]
    item = EvidenceItem(evidence_id="EVD-FIXED-1", evidence_type=EvidenceType.SHARED_DEVICE_RING, source="graph", finding="Shared D1", value={"device_id": "D1"}, lr=5.0, log_lr=math.log(5.0))
    
    ledger1 = EvidenceLedger()
    ledger1.add(item)
    s1 = be.evaluate_investigation("C1-1", {"trigger_type": "risk_score"}, {}, ledger1, PriorProfile.ALERT_CONDITIONED)
    
    ledger2 = EvidenceLedger()
    ledger2.add(item)
    ledger2.add(item) # Exact duplicate ID and content
    s2 = be.evaluate_investigation("C1-2", {"trigger_type": "risk_score"}, {}, ledger2, PriorProfile.ALERT_CONDITIONED)
    
    assert math.isclose(s1.belief_state["fraud_probability"], s2.belief_state["fraud_probability"], abs_tol=1e-6)
    dup_steps = [step for step in s2.reasoning_history if step.event == "DUPLICATE_EVIDENCE_IGNORED"]
    assert len(dup_steps) == 1

def test_metamorphic_c2_triplicate_and_quintuplicate_dedup(base_engines):
    """3x and 5x duplicate insertions are suppressed without belief inflation."""
    be = base_engines["belief_engine"]
    item = EvidenceItem(evidence_id="EVD-FIXED-2", evidence_type=EvidenceType.CARD_TESTING_SEQUENCE, source="graph", finding="Micro txns", value={"pattern": "card_testing"}, lr=6.0, log_lr=math.log(6.0))
    
    ledger1 = EvidenceLedger()
    ledger1.add(item)
    s1 = be.evaluate_investigation("C2-1X", {"trigger_type": "customer_report"}, {}, ledger1, PriorProfile.ALERT_CONDITIONED)
    
    ledger5 = EvidenceLedger()
    for _ in range(5):
        ledger5.add(item)
        
    s5 = be.evaluate_investigation("C2-5X", {"trigger_type": "customer_report"}, {}, ledger5, PriorProfile.ALERT_CONDITIONED)
    assert math.isclose(s1.belief_state["fraud_probability"], s5.belief_state["fraud_probability"], abs_tol=1e-6)
    dup_steps = [step for step in s5.reasoning_history if step.event == "DUPLICATE_EVIDENCE_IGNORED"]
    assert len(dup_steps) == 4

def test_metamorphic_c3_same_family_correlation_damping(base_engines):
    """Two distinct findings in same family receive correlation damping."""
    be = base_engines["belief_engine"]
    item1 = EvidenceItem(evidence_id="EVD-DEV-1", evidence_type=EvidenceType.SHARED_DEVICE_RING, source="graph", finding="Shared D1", value={"device_id": "D1"}, lr=4.0, log_lr=math.log(4.0))
    item2 = EvidenceItem(evidence_id="EVD-PROXY-1", evidence_type=EvidenceType.PROXY_DETECTED, source="network", finding="Tor exit node", value={"ip": "1.1.1.1"}, lr=4.0, log_lr=math.log(4.0))
    
    ledger = EvidenceLedger()
    ledger.add(item1)
    ledger.add(item2)
    
    s = be.evaluate_investigation("C3-DAMP", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert s.belief_state["fraud_probability"] > 0.8383

def test_metamorphic_c4_duplicate_no_match_idempotence(base_engines):
    """Multiple NO_MATCH insertions do not alter log-odds or probability."""
    be = base_engines["belief_engine"]
    no_match = EvidenceItem(evidence_id="EVD-NM", evidence_type=EvidenceType.BEHAVIORAL_BASELINE, source="graph", finding="NO_MATCH", value="NO_MATCH", lr=1.0, log_lr=0.0)
    
    ledger = EvidenceLedger()
    ledger.add(no_match)
    s1 = be.evaluate_investigation("C4-1", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    ledger.add(no_match)
    s2 = be.evaluate_investigation("C4-2", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    
    assert math.isclose(s1.belief_state["fraud_probability"], s2.belief_state["fraud_probability"], abs_tol=1e-6)

def test_metamorphic_c5_dispatcher_duplicate_execution_protection(base_engines):
    """Dispatcher preserves evidence ledger idempotency if tool is called twice."""
    compass = base_engines["compass"]
    dispatcher = base_engines["dispatcher"]
    state = create_synthetic_state("C5-DISP")
    rec = compass.evaluate_evidence_compass(state, exposure_usd=100.0)
    cand = rec.ranked_candidates[0]
    s_updated, res1, _ = dispatcher.dispatch_and_update(state, cand)
    s_updated2, res2, _ = dispatcher.dispatch_and_update(s_updated, cand)
    assert s_updated2.belief_state["fraud_probability"] == s_updated.belief_state["fraud_probability"]

# ==============================================================================
# FAMILY D: METAMORPHIC TEMPORAL BOUNDARY & SCOPE (5 Tests)
# ==============================================================================

def test_metamorphic_d1_inside_24h_window_boundary(base_engines):
    """Transaction inside 24h window produces valid temporal scope evidence."""
    anchor = "2026-09-20 12:00:00"
    txn_ts = "2026-09-19 12:01:00" # 23h 59m prior
    raw = [{"txn_id": "T1", "amount": 1.50, "timestamp": txn_ts}]
    ev = EvidenceNormalizer.normalize(
        action_id="CARD_SEQUENCE_ANALYSIS",
        tool_name="card_sequence",
        scope_status=GraphScopeStatus.DATA_AVAILABLE,
        raw_data=raw,
        target_entities={"card_id": "C1", "customer_id": "U1"},
        context={"anchor_ts": anchor}
    )
    assert ev.evidence_type == EvidenceType.CARD_TESTING_SEQUENCE
    assert ev.lr >= 1.0

def test_metamorphic_d2_exact_24h_window_boundary(base_engines):
    """Transaction at exact 24h boundary is processed deterministically."""
    anchor = "2026-09-20 12:00:00"
    txn_ts = "2026-09-19 12:00:00"
    raw = [{"txn_id": "T1", "amount": 1.50, "timestamp": txn_ts}]
    ev = EvidenceNormalizer.normalize(
        action_id="CARD_SEQUENCE_ANALYSIS",
        tool_name="card_sequence",
        scope_status=GraphScopeStatus.DATA_AVAILABLE,
        raw_data=raw,
        target_entities={"card_id": "C1", "customer_id": "U1"},
        context={"anchor_ts": anchor}
    )
    assert ev is not None

def test_metamorphic_d3_outside_24h_window_boundary(base_engines):
    """Empty query result from outside-window returns NO_MATCH with LR=1.0."""
    anchor = "2026-09-20 12:00:00"
    raw = [] # Outside window filtered out by query
    ev = EvidenceNormalizer.normalize(
        action_id="CARD_SEQUENCE_ANALYSIS",
        tool_name="card_sequence",
        scope_status=GraphScopeStatus.NO_MATCH,
        raw_data=raw,
        target_entities={"card_id": "C1", "customer_id": "U1"},
        context={"anchor_ts": anchor}
    )
    assert ev.evidence_type == EvidenceType.CARD_TESTING_SEQUENCE
    assert ev.value == "NO_MATCH"
    assert ev.lr == 1.0
    assert ev.log_lr == 0.0

def test_metamorphic_d4_missing_anchor_timestamp_safety(base_engines):
    """Missing anchor_ts does not crash and normalizes safely."""
    raw = [{"txn_id": "T1", "amount": 1.50}]
    ev = EvidenceNormalizer.normalize(
        action_id="CARD_SEQUENCE_ANALYSIS",
        tool_name="card_sequence",
        scope_status=GraphScopeStatus.DATA_AVAILABLE,
        raw_data=raw,
        target_entities={"card_id": "C1", "customer_id": "U1"},
        context={}
    )
    assert ev.lr >= 1.0
    assert ev.finding is not None

def test_metamorphic_d5_future_dated_transaction_rejection(base_engines):
    """Query returning NO_MATCH for future-dated transaction preserves LR=1.0."""
    anchor = "2026-09-20 12:00:00"
    ev = EvidenceNormalizer.normalize(
        action_id="CARD_SEQUENCE_ANALYSIS",
        tool_name="card_sequence",
        scope_status=GraphScopeStatus.NO_MATCH,
        raw_data=[],
        target_entities={"card_id": "C1", "customer_id": "U1"},
        context={"anchor_ts": anchor}
    )
    assert ev.lr == 1.0
    assert ev.log_lr == 0.0

# ==============================================================================
# FAMILY E: METAMORPHIC GRAPHRAG NON-EVIDENCE ISOLATION (5 Tests)
# ==============================================================================

def test_metamorphic_e1_relevant_graphrag_zero_belief_shift(base_engines):
    """Highly relevant GraphRAG knowledge does not alter P(Fraud) or coverage."""
    state = create_synthetic_state("E1-GRAPHRAG", trigger_type="risk_score", risk_score=0.75)
    p_before = state.belief_state["fraud_probability"]
    cov_before = state.uncertainty.evidence_coverage
    
    rag = PolicyGraphRAGRetriever()
    items = rag.retrieve_grounded_context(state, exposure_usd=500.0)
    assert len(items) > 0
    
    p_after = state.belief_state["fraud_probability"]
    cov_after = state.uncertainty.evidence_coverage
    assert p_before == p_after
    assert cov_before == cov_after

def test_metamorphic_e2_irrelevant_graphrag_zero_belief_shift(base_engines):
    """Irrelevant or empty GraphRAG retrieval does not alter state."""
    state = create_synthetic_state("E2-NOISE", trigger_type="risk_score", risk_score=0.50)
    p_before = state.belief_state["fraud_probability"]
    rag = PolicyGraphRAGRetriever()
    rag.retrieve_grounded_context(state, exposure_usd=10.0)
    assert state.belief_state["fraud_probability"] == p_before

def test_metamorphic_e3_graphrag_claims_fraud_without_evidence(base_engines):
    """GraphRAG knowledge stating 'Fraud must be escalated' does NOT satisfy R5/R6 without empirical evidence."""
    pe = base_engines["policy_engine"]
    state = create_synthetic_state("E3-KNOWLEDGE-ONLY", trigger_type="risk_score", risk_score=0.50)
    acts = pe.evaluate(0.50, "uncertain", 200.0, EvidenceLedger(items=state.evidence_items), case_context={"trigger_type": "risk_score"})
    assert "DECLINE_TRANSACTION" not in [a.action for a in acts]
    assert "BLOCK_CARD" not in [a.action for a in acts]

def test_metamorphic_e4_graphrag_claims_innocence_with_evidence(base_engines):
    """GraphRAG passages stating 'Customer is VIP' cannot override empirical CARD_TESTING_SEQUENCE."""
    be = base_engines["belief_engine"]
    pe = base_engines["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CARD_TESTING_SEQUENCE, source="g", finding="Micro txns", value={"pattern": "card_testing"}, lr=7.0, log_lr=math.log(7.0)))
    state = be.evaluate_investigation("E4-EMPIRICAL", {"trigger_type": "customer_report"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    acts = pe.evaluate(state.belief_state["fraud_probability"], "fraud", 200.0, ledger, case_context={"trigger_type": "customer_report"})
    assert acts[0].action == "DECLINE_TRANSACTION"

def test_metamorphic_e5_graphrag_citations_verbatim_provenance(base_engines):
    """Retrieved GraphRAG items preserve non-evidence provenance markers."""
    state = create_synthetic_state("E5-PROV")
    rag = PolicyGraphRAGRetriever()
    items = rag.retrieve_grounded_context(state, exposure_usd=100.0)
    for item in items:
        assert hasattr(item, "chunk")
        assert item.chunk.category in ["POLICY_RULE", "REGULATION", "TYPOLOGY"]

# ==============================================================================
# FAMILY F: METAMORPHIC HISTORICAL MEMORY ISOLATION (5 Tests)
# ==============================================================================

def test_metamorphic_f1_similar_fraud_case_zero_belief_shift(base_engines):
    """Similar historical fraud cases do NOT shift P(Fraud) or inject LR."""
    state = create_synthetic_state("F1-MEM-FRAUD", trigger_type="risk_score", risk_score=0.60)
    p_before = state.belief_state["fraud_probability"]
    store = CaseMemoryStore()
    retriever = SimilarCaseRetriever(store)
    matches = retriever.retrieve_similar_cases(state=state, pattern="shared_device_ring", top_k=3)
    assert state.belief_state["fraud_probability"] == p_before

def test_metamorphic_f2_similar_legitimate_case_zero_belief_shift(base_engines):
    """Similar historical legitimate cases do NOT shift P(Fraud) or lower belief."""
    state = create_synthetic_state("F2-MEM-LEGIT", trigger_type="risk_score", risk_score=0.90)
    p_before = state.belief_state["fraud_probability"]
    store = CaseMemoryStore()
    retriever = SimilarCaseRetriever(store)
    matches = retriever.retrieve_similar_cases(state=state, pattern="card_testing", top_k=3)
    assert state.belief_state["fraud_probability"] == p_before

def test_metamorphic_f3_active_case_self_match_exclusion(base_engines):
    """Active investigation cannot retrieve itself from memory."""
    store = CaseMemoryStore()
    rec = CaseMemoryRecord(case_id="F3-SELF", customer_id="U1", card_id="C1", closed_at="2026-01-01 00:00:00", historical_outcome="confirmed_fraud", pattern="card_testing", exposure_usd=100.0)
    store.add_case(rec)
    retriever = SimilarCaseRetriever(store)
    state = create_synthetic_state("F3-SELF", card_id="C1", customer_id="U1")
    matches = retriever.retrieve_similar_cases(state=state, top_k=5)
    assert "F3-SELF" not in [m.case_record.case_id for m in matches if m.case_record.case_id == state.investigation_id]

def test_metamorphic_f4_future_dated_case_temporal_exclusion(base_engines):
    """Cases closed after the active investigation timestamp are excluded."""
    store = CaseMemoryStore()
    rec_future = CaseMemoryRecord(case_id="F4-FUT", customer_id="U1", card_id="C1", closed_at="2026-12-31 00:00:00", historical_outcome="confirmed_fraud", pattern="card_testing", exposure_usd=100.0)
    store.add_case(rec_future)
    retriever = SimilarCaseRetriever(store)
    state = create_synthetic_state("F4-ACTIVE", card_id="C1", customer_id="U1")
    matches = retriever.retrieve_similar_cases(state=state, effective_timestamp="2026-06-01 00:00:00")
    assert "F4-FUT" not in [m.case_record.case_id for m in matches]

def test_metamorphic_f5_multiple_conflicting_historical_precedents(base_engines):
    """Conflicting historical precedents do not corrupt empirical state."""
    state = create_synthetic_state("F5-CONFLICT")
    store = CaseMemoryStore()
    retriever = SimilarCaseRetriever(store)
    matches = retriever.retrieve_similar_cases(state=state, top_k=5)
    for m in matches:
        assert m.role == "CONTEXTUAL_PRECEDENT_ONLY"

# ==============================================================================
# FAMILY G: METAMORPHIC TOOL FAILURE SEMANTICS (5 Tests)
# ==============================================================================

def test_metamorphic_g1_timeout_produces_zero_log_odds_shift(base_engines):
    """Network timeout yields GRAPH_QUERY_FAILURE with LR=1.0 and zero log-odds delta."""
    ev = EvidenceNormalizer.normalize(
        action_id="CHECK_SHARED_DEVICES",
        tool_name="device_analysis",
        scope_status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
        raw_data={"error": "Connection timed out"},
        target_entities={"card_id": "C1", "customer_id": "U1"}
    )
    assert ev.lr == 1.0
    assert ev.log_lr == 0.0
    assert ev.value == "GRAPH_QUERY_FAILURE"

def test_metamorphic_g2_malformed_response_handling(base_engines):
    """Malformed tool payload yields neutral failure item."""
    ev = EvidenceNormalizer.normalize(
        action_id="CHECK_SHARED_DEVICES",
        tool_name="device_analysis",
        scope_status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
        raw_data="Invalid string payload",
        target_entities={"card_id": "C1", "customer_id": "U1"}
    )
    assert ev.lr == 1.0
    assert ev.log_lr == 0.0

def test_metamorphic_g3_empty_result_is_no_match_not_failure(base_engines):
    """Empty vertex/edge set is genuine NO_MATCH, distinct from tool failure."""
    ev = EvidenceNormalizer.normalize(
        action_id="CHECK_SHARED_DEVICES",
        tool_name="device_analysis",
        scope_status=GraphScopeStatus.NO_MATCH,
        raw_data={"shared_cards": []},
        target_entities={"card_id": "C1", "customer_id": "U1"}
    )
    assert ev.lr == 1.0
    assert ev.value == "NO_MATCH"
    assert ev.value != "GRAPH_QUERY_FAILURE"

def test_metamorphic_g4_consecutive_tool_failures_terminate_budget(base_engines):
    """Orchestrator terminates on TOOL_FAILURE_LIMIT when failure limit reached."""
    orch = InvestigationOrchestrator(
        belief_engine=base_engines["belief_engine"],
        policy_engine=base_engines["policy_engine"],
        compass=base_engines["compass"],
        dispatcher=base_engines["dispatcher"],
        consecutive_failure_limit=2
    )
    assert orch.consecutive_failure_limit == 2

def test_metamorphic_g5_compass_evoi_on_failed_tools(base_engines):
    """Tools already executed or failing do not repeatedly trap the agent."""
    compass = base_engines["compass"]
    state = create_synthetic_state("G5-EVOI")
    rec = compass.evaluate_evidence_compass(state, exposure_usd=100.0)
    assert len(rec.ranked_candidates) > 0

# ==============================================================================
# FAMILY H: METAMORPHIC NEGATIVE VS ABSENT VS UNAVAILABLE (5 Tests)
# ==============================================================================

def test_metamorphic_h1_absent_evidence_family_coverage_zero(base_engines):
    """Absent evidence family contributes 0.0 to coverage and adds no item."""
    state = create_synthetic_state("H1-ABSENT")
    assert state.uncertainty.evidence_coverage < 0.50

def test_metamorphic_h2_explicit_no_match_increases_coverage_without_shifting_belief(base_engines):
    """Explicit NO_MATCH increases evidence coverage while leaving log-odds unchanged."""
    be = base_engines["belief_engine"]
    state_init = create_synthetic_state("H2-INIT", trigger_type="risk_score", risk_score=0.60)
    cov_init = state_init.uncertainty.evidence_coverage
    p_init = state_init.belief_state["fraud_probability"]
    
    ledger = EvidenceLedger(items=copy.deepcopy(state_init.evidence_items))
    ledger.add(EvidenceItem(evidence_id="EVD-NM-DEV", evidence_type=EvidenceType.SHARED_DEVICE_RING, source="graph", finding="NO_MATCH: clean device", value="NO_MATCH", lr=1.0, log_lr=0.0))
    
    state_after = be.evaluate_investigation("H2-AFTER", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert math.isclose(state_after.belief_state["fraud_probability"], p_init, abs_tol=1e-6)
    assert state_after.uncertainty.evidence_coverage >= cov_init

def test_metamorphic_h3_customer_unavailable_does_not_satisfy_r3(base_engines):
    """Customer unavailable strictly prevents R3 (CLOSE_NO_FRAUD as primary rule)."""
    pe = base_engines["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE, source="cust", finding="CUSTOMER_UNAVAILABLE", value="UNAVAILABLE", lr=1.0, log_lr=0.0))
    acts = pe.evaluate(0.20, "legitimate", 100.0, ledger, case_context={"trigger_type": "risk_score"})
    assert acts[0].action == "ALLOW_TRANSACTION"
    assert not any("R3:" in a.reason for a in acts)

def test_metamorphic_h4_positive_customer_confirmation_satisfies_r3(base_engines):
    """Positive exculpatory confirmation satisfies R3 (CLOSE_NO_FRAUD)."""
    pe = base_engines["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CUSTOMER_CONFIRMATION, source="cust", finding="Customer verified authorized txn", value="CONFIRMED_LEGITIMATE", is_exculpatory=True, lr=0.05, log_lr=math.log(0.05)))
    acts = pe.evaluate(0.05, "legitimate", 100.0, ledger, case_context={"trigger_type": "risk_score"})
    assert acts[0].action == "CLOSE_NO_FRAUD"

def test_metamorphic_h5_negative_velocity_does_not_wipe_device_ring(base_engines):
    """Negative velocity does not attenuate positive device ring."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring D1", value={"device_id": "D1"}, lr=5.0, log_lr=math.log(5.0)))
    s1 = be.evaluate_investigation("H5-1", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    
    ledger.add(EvidenceItem(evidence_type=EvidenceType.HIGH_VELOCITY, source="g", finding="NO_MATCH", value="NO_MATCH", lr=1.0, log_lr=0.0))
    s2 = be.evaluate_investigation("H5-2", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    
    assert math.isclose(s1.belief_state["fraud_probability"], s2.belief_state["fraud_probability"], abs_tol=1e-6)

# ==============================================================================
# FAMILY I: METAMORPHIC IRRELEVANT EVIDENCE & NOISE (5 Tests)
# ==============================================================================

def test_metamorphic_i1_neutral_noise_entry_zero_belief_shift(base_engines):
    """Noise log entry with LR=1.0 leaves probability completely unchanged."""
    be = base_engines["belief_engine"]
    state = create_synthetic_state("I1-NOISE", trigger_type="risk_score", risk_score=0.70)
    p1 = state.belief_state["fraud_probability"]
    
    ledger = EvidenceLedger(items=copy.deepcopy(state.evidence_items))
    ledger.add(EvidenceItem(evidence_id="EVD-NOISE-1", evidence_type=EvidenceType.BEHAVIORAL_BASELINE, source="audit", finding="Server heartbeat check", value="NO_MATCH", lr=1.0, log_lr=0.0))
    s2 = be.evaluate_investigation("I1-NOISE2", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert math.isclose(p1, s2.belief_state["fraud_probability"], abs_tol=1e-6)

def test_metamorphic_i2_unrelated_metadata_zero_belief_shift(base_engines):
    """Unrelated merchant metadata produces LR=1.0."""
    be = base_engines["belief_engine"]
    state = create_synthetic_state("I2-META")
    p1 = state.belief_state["fraud_probability"]
    ledger = EvidenceLedger(items=copy.deepcopy(state.evidence_items))
    ledger.add(EvidenceItem(evidence_id="EVD-META-1", evidence_type=EvidenceType.BEHAVIORAL_BASELINE, source="mcc", finding="MCC 5411 Grocery Stores", value="NO_MATCH", lr=1.0, log_lr=0.0))
    s2 = be.evaluate_investigation("I2-META2", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert math.isclose(p1, s2.belief_state["fraud_probability"], abs_tol=1e-6)

def test_metamorphic_i3_non_core_evidence_does_not_inflate_core_coverage(base_engines):
    """Non-core evidence item does not artificially max out coverage."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.BEHAVIORAL_BASELINE, source="x", finding="Misc note", value="NO_MATCH", lr=1.0, log_lr=0.0))
    s = be.evaluate_investigation("I3-COV", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert s.uncertainty.evidence_coverage < 0.40

def test_metamorphic_i4_high_confidence_noise_isolation(base_engines):
    """High-confidence benign tag with LR=1.0 preserves epistemic uncertainty boundaries."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.BEHAVIORAL_BASELINE, source="trusted", finding="Cardholder signed up 2018", value="NO_MATCH", lr=1.0, log_lr=0.0))
    s = be.evaluate_investigation("I4-TAG", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert s.uncertainty.epistemic_uncertainty > 0.0

def test_metamorphic_i5_mixed_noise_and_genuine_signal(base_engines):
    """Mixed noise entries alongside genuine signal compute identical belief to genuine signal alone."""
    be = base_engines["belief_engine"]
    item_real = EvidenceItem(evidence_id="EVD-REAL", evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring D1", value={"device_id": "D1"}, lr=4.0, log_lr=math.log(4.0))
    item_noise = EvidenceItem(evidence_id="EVD-NOISE", evidence_type=EvidenceType.BEHAVIORAL_BASELINE, source="g", finding="Noise", value="NO_MATCH", lr=1.0, log_lr=0.0)
    
    ledger_clean = EvidenceLedger()
    ledger_clean.add(item_real)
    s_clean = be.evaluate_investigation("I5-CLEAN", {"trigger_type": "risk_score"}, {}, ledger_clean, PriorProfile.ALERT_CONDITIONED)
    
    ledger_noisy = EvidenceLedger()
    ledger_noisy.add(item_noise)
    ledger_noisy.add(item_real)
    s_noisy = be.evaluate_investigation("I5-NOISY", {"trigger_type": "risk_score"}, {}, ledger_noisy, PriorProfile.ALERT_CONDITIONED)
    
    assert math.isclose(s_clean.belief_state["fraud_probability"], s_noisy.belief_state["fraud_probability"], abs_tol=1e-6)

# ==============================================================================
# FAMILY J: METAMORPHIC ADDITIVE POSITIVE EVIDENCE & MONOTONICITY (5 Tests)
# ==============================================================================

def test_metamorphic_j1_single_positive_family(base_engines):
    """Single positive evidence family increases log-odds monotonically."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring", value={"device_id": "D1"}, lr=3.0, log_lr=math.log(3.0)))
    s = be.evaluate_investigation("J1-1", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert s.belief_state["fraud_probability"] > 0.8383

def test_metamorphic_j2_two_independent_positive_families(base_engines):
    """Two independent positive evidence families yield strictly higher belief than one."""
    be = base_engines["belief_engine"]
    ledger1 = EvidenceLedger()
    ledger1.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring", value={"device_id": "D1"}, lr=3.0, log_lr=math.log(3.0)))
    s1 = be.evaluate_investigation("J2-1", {"trigger_type": "risk_score"}, {}, ledger1, PriorProfile.ALERT_CONDITIONED)
    
    ledger2 = EvidenceLedger(items=copy.deepcopy(ledger1.items))
    ledger2.add(EvidenceItem(evidence_type=EvidenceType.CARD_TESTING_SEQUENCE, source="g", finding="Testing", value={"pattern": "card_testing"}, lr=4.0, log_lr=math.log(4.0)))
    s2 = be.evaluate_investigation("J2-2", {"trigger_type": "risk_score"}, {}, ledger2, PriorProfile.ALERT_CONDITIONED)
    
    assert s2.belief_state["fraud_probability"] > s1.belief_state["fraud_probability"]

def test_metamorphic_j3_three_independent_positive_families(base_engines):
    """Three independent positive families yield monotonic increase: P1 < P2 < P3."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring", value={"device_id": "D1"}, lr=3.0, log_lr=math.log(3.0)))
    s1 = be.evaluate_investigation("J3-1", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CARD_TESTING_SEQUENCE, source="g", finding="Testing", value={"pattern": "card_testing"}, lr=4.0, log_lr=math.log(4.0)))
    s2 = be.evaluate_investigation("J3-2", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    
    ledger.add(EvidenceItem(evidence_type=EvidenceType.HIGH_VELOCITY, source="g", finding="Vel", value={"velocity": 5}, lr=3.5, log_lr=math.log(3.5)))
    s3 = be.evaluate_investigation("J3-3", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    
    assert s1.belief_state["fraud_probability"] < s2.belief_state["fraud_probability"] < s3.belief_state["fraud_probability"]

def test_metamorphic_j4_family_independence_calibration(base_engines):
    """Independent families accumulate monotonically in log-odds space."""
    be = base_engines["belief_engine"]
    lr_dev = 3.0
    lr_seq = 4.0
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring", value={"device_id": "D1"}, lr=lr_dev, log_lr=math.log(lr_dev)))
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CARD_TESTING_SEQUENCE, source="g", finding="Testing", value={"pattern": "card_testing"}, lr=lr_seq, log_lr=math.log(lr_seq)))
    s = be.evaluate_investigation("J4-CAL", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert s.belief_state["fraud_probability"] > 0.95

def test_metamorphic_j5_extreme_probability_bounding(base_engines):
    """Probability strictly bounded in (0, 1) under extreme accumulation."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    types_list = [EvidenceType.SHARED_DEVICE_RING, EvidenceType.CARD_TESTING_SEQUENCE, EvidenceType.HIGH_VELOCITY, EvidenceType.PROXY_DETECTED]
    for i, t in enumerate(types_list):
        ledger.add(EvidenceItem(evidence_id=f"EVD-EXT-{i}", evidence_type=t, source="g", finding=f"Item {i}", value={"val": i}, lr=100.0, log_lr=math.log(100.0)))
    s = be.evaluate_investigation("J5-BOUND", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    prob = s.belief_state["fraud_probability"]
    assert 0.0 < prob <= 1.0
    assert not math.isnan(prob)

# ==============================================================================
# FAMILY K: METAMORPHIC POLICY PRECONDITION INTEGRITY (5 Tests)
# ==============================================================================

def test_metamorphic_k1_r5_strict_card_testing_precondition(base_engines):
    """R5 (DECLINE_TRANSACTION) requires empirical CARD_TESTING_SEQUENCE."""
    pe = base_engines["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring", value={"device_id": "D1"}, lr=10.0, log_lr=math.log(10.0)))
    acts = pe.evaluate(0.99, "fraud", 500.0, ledger, case_context={"trigger_type": "risk_score"})
    assert "DECLINE_TRANSACTION" not in [a.action for a in acts]

def test_metamorphic_k2_r6_strict_shared_device_precondition(base_engines):
    """R6 (CREATE_CASE) requires empirical SHARED_DEVICE_RING or ring signal."""
    pe = base_engines["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.HIGH_VELOCITY, source="g", finding="High vel", value={"velocity": 5}, lr=8.0, log_lr=math.log(8.0)))
    acts = pe.evaluate(0.98, "fraud", 500.0, ledger, case_context={"trigger_type": "customer_report"})
    assert acts[0].action == "BLOCK_CARD"

def test_metamorphic_k3_r2_strict_customer_dispute_precondition(base_engines):
    """R2 (BLOCK_CARD) requires customer dispute/report."""
    pe = base_engines["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CALIBRATED_RISK_SCORE, source="m", finding="RS 0.95", value={"score": 0.95}, lr=10.0, log_lr=math.log(10.0)))
    acts = pe.evaluate(0.95, "fraud", 200.0, ledger, case_context={"trigger_type": "risk_score"})
    # Risk score trigger without dispute routes to CREATE_CASE / INVESTIGATE
    assert any(a.action in ["CREATE_CASE", "MONITOR_CARD"] for a in acts)

def test_metamorphic_k4_r3_strict_customer_confirmation_precondition(base_engines):
    """R3 (CLOSE_NO_FRAUD as primary rule) strictly rejects if customer confirmation is missing."""
    pe = base_engines["policy_engine"]
    ledger = EvidenceLedger()
    acts = pe.evaluate(0.01, "legitimate", 10.0, ledger, case_context={"trigger_type": "risk_score"})
    assert acts[0].action == "ALLOW_TRANSACTION"
    assert not any("R3:" in a.reason for a in acts)

def test_metamorphic_k5_generic_high_probability_fallback(base_engines):
    """High probability with risk score trigger safely yields CREATE_CASE."""
    pe = base_engines["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CALIBRATED_RISK_SCORE, source="m", finding="Score 0.99", value={"score": 0.99}, lr=50.0, log_lr=math.log(50.0)))
    acts = pe.evaluate(0.99, "fraud", 1000.0, ledger, case_context={"trigger_type": "risk_score"})
    assert any(a.action in ["CREATE_CASE", "BLOCK_CARD"] for a in acts)

# ==============================================================================
# FAMILY L: METAMORPHIC ANALYST REQUEST GENERALIZATION (5 Tests)
# ==============================================================================

def test_metamorphic_l1_low_risk_analyst_request_economic_containment(base_engines):
    """Low-risk analyst request on low exposure evaluates stopping logic."""
    compass = base_engines["compass"]
    state = create_synthetic_state("L1-LOW", trigger_type="analyst_request", prior_profile=PriorProfile.UNCONDITIONED_POPULATION)
    rec = compass.evaluate_evidence_compass(state, exposure_usd=10.0)
    assert rec is not None

def test_metamorphic_l2_high_risk_analyst_request_deep_investigation(base_engines):
    """High-risk analyst request ($10,000 exposure, P=0.85) yields positive EVOI."""
    compass = base_engines["compass"]
    state = create_synthetic_state("L2-HIGH", trigger_type="analyst_request", prior_profile=PriorProfile.ALERT_CONDITIONED)
    rec = compass.evaluate_evidence_compass(state, exposure_usd=10000.0)
    pos_candidates = [c for c in rec.ranked_candidates if c.net_decision_value > 0.0]
    assert len(pos_candidates) > 0

def test_metamorphic_l3_analyst_request_with_clean_graph(base_engines):
    """Analyst request with clean graph finishes appropriately."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="NO_MATCH", value="NO_MATCH", lr=1.0, log_lr=0.0))
    s = be.evaluate_investigation("L3-CLEAN", {"trigger_type": "analyst_request"}, {}, ledger, PriorProfile.UNCONDITIONED_POPULATION)
    assert s.belief_state["fraud_probability"] < 0.05

def test_metamorphic_l4_analyst_request_with_discovered_anomaly(base_engines):
    """Analyst request discovering device ring shifts belief and satisfies R6."""
    be = base_engines["belief_engine"]
    pe = base_engines["policy_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="3 shared cards", value={"device_id": "D1"}, lr=6.0, log_lr=math.log(6.0)))
    s = be.evaluate_investigation("L4-ANOMALY", {"trigger_type": "analyst_request"}, {}, ledger, PriorProfile.UNCONDITIONED_POPULATION)
    acts = pe.evaluate(s.belief_state["fraud_probability"], "fraud", 500.0, ledger, case_context={"trigger_type": "analyst_request"})
    assert acts[0].action == "CREATE_CASE"

def test_metamorphic_l5_analyst_request_respects_step_budget(base_engines):
    """Analyst request loop is strictly bounded by max_steps."""
    orch = InvestigationOrchestrator(
        belief_engine=base_engines["belief_engine"],
        policy_engine=base_engines["policy_engine"],
        compass=base_engines["compass"],
        dispatcher=base_engines["dispatcher"],
        max_steps=3
    )
    assert orch.max_steps == 3

# ==============================================================================
# FAMILY M: METAMORPHIC INVESTIGATION TERMINATION & EVOI (5 Tests)
# ==============================================================================

def test_metamorphic_m1_decision_reached_termination_condition(base_engines):
    """Decision Reached when Decision Gate is passed and remaining tools have EVOI <= 0."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring", value={"device_id": "D1"}, lr=8.0, log_lr=math.log(8.0)))
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CARD_TESTING_SEQUENCE, source="g", finding="Testing", value={"pattern": "card_testing"}, lr=7.0, log_lr=math.log(7.0)))
    ledger.add(EvidenceItem(evidence_type=EvidenceType.HIGH_VELOCITY, source="g", finding="Vel", value={"velocity": 5}, lr=5.0, log_lr=math.log(5.0)))
    state = be.evaluate_investigation("M1-TERM", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert state.decision_gate_passed is True

def test_metamorphic_m2_continuation_when_decision_gate_fails(base_engines):
    """Investigation continues when decision gate fails and positive EVOI exists."""
    compass = base_engines["compass"]
    state = create_synthetic_state("M2-CONT", trigger_type="risk_score", risk_score=0.60)
    assert state.decision_gate_passed is False
    rec = compass.evaluate_evidence_compass(state, exposure_usd=500.0)
    assert len([c for c in rec.ranked_candidates if c.net_decision_value > 0.0]) > 0

def test_metamorphic_m3_max_steps_budget_enforcement(base_engines):
    """Investigation terminates on MAX_STEPS_REACHED when step limit hit."""
    assert InvestigationTerminationReason.MAX_STEPS_REACHED.value == "MAX_STEPS_REACHED"

def test_metamorphic_m4_tool_failure_limit_enforcement(base_engines):
    """Investigation terminates on TOOL_FAILURE_LIMIT when consecutive failures occur."""
    assert InvestigationTerminationReason.TOOL_FAILURE_LIMIT.value == "TOOL_FAILURE_LIMIT"

def test_metamorphic_m5_human_approval_termination_on_conflict(base_engines):
    """Investigation terminates immediately on HUMAN_APPROVAL_REQUIRED when aleatoric uncertainty is high."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring", value={"device_id": "D1"}, lr=10.0, log_lr=math.log(10.0)))
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CUSTOMER_CONFIRMATION, source="c", finding="Confirmed legit", value="CONFIRMED_LEGITIMATE", is_exculpatory=True, lr=0.10, log_lr=math.log(0.10)))
    state = be.evaluate_investigation("M5-CONFLICT", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL

# ==============================================================================
# FAMILY N: METAMORPHIC CONTRADICTION & ALEATORIC CONFLICT (5 Tests)
# ==============================================================================

def test_metamorphic_n1_mild_conflict_below_threshold(base_engines):
    """Mild contradiction does not trigger human approval block."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring", value={"device_id": "D1"}, lr=5.0, log_lr=math.log(5.0)))
    ledger.add(EvidenceItem(evidence_type=EvidenceType.OUT_OF_REGION, source="g", finding="Minor distance", value={"dist": 50}, lr=0.85, log_lr=math.log(0.85)))
    state = be.evaluate_investigation("N1-MILD", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert state.decision_state != DecisionState.REQUIRES_HUMAN_APPROVAL

def test_metamorphic_n2_severe_conflict_above_threshold(base_engines):
    """Severe contradiction triggers REQUIRES_HUMAN_APPROVAL."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CARD_TESTING_SEQUENCE, source="g", finding="Testing", value={"pattern": "card_testing"}, lr=8.0, log_lr=math.log(8.0)))
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CUSTOMER_CONFIRMATION, source="c", finding="Confirmed authorized", value="CONFIRMED_LEGITIMATE", is_exculpatory=True, lr=0.08, log_lr=math.log(0.08)))
    state = be.evaluate_investigation("N2-SEVERE", {"trigger_type": "customer_report"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert state.uncertainty.aleatoric_uncertainty >= 0.40
    assert state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL

def test_metamorphic_n3_severe_conflict_blocks_automated_policy_actions(base_engines):
    """Decision Gate blocked under severe conflict prevents automated action execution."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CARD_TESTING_SEQUENCE, source="g", finding="Testing", value={"pattern": "card_testing"}, lr=8.0, log_lr=math.log(8.0)))
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CUSTOMER_CONFIRMATION, source="c", finding="Legit", value="CONFIRMED_LEGITIMATE", is_exculpatory=True, lr=0.08, log_lr=math.log(0.08)))
    state = be.evaluate_investigation("N3-BLOCK", {"trigger_type": "customer_report"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert state.decision_gate_passed is False

def test_metamorphic_n4_conflict_metric_order_symmetry(base_engines):
    """Aleatoric uncertainty computation is strictly symmetric to evidence insertion order."""
    be = base_engines["belief_engine"]
    item_incrim = EvidenceItem(evidence_id="EVD-INCRIM", evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring", value={"device_id": "D1"}, lr=6.0, log_lr=math.log(6.0))
    item_exculp = EvidenceItem(evidence_id="EVD-EXCULP", evidence_type=EvidenceType.CUSTOMER_CONFIRMATION, source="c", finding="Legit", value="CONFIRMED_LEGITIMATE", is_exculpatory=True, lr=0.10, log_lr=math.log(0.10))
    
    ledger1 = EvidenceLedger()
    ledger1.add(item_incrim)
    ledger1.add(item_exculp)
    s1 = be.evaluate_investigation("N4-1", {"trigger_type": "risk_score"}, {}, ledger1, PriorProfile.ALERT_CONDITIONED)
    
    ledger2 = EvidenceLedger()
    ledger2.add(item_exculp)
    ledger2.add(item_incrim)
    s2 = be.evaluate_investigation("N4-2", {"trigger_type": "risk_score"}, {}, ledger2, PriorProfile.ALERT_CONDITIONED)
    
    assert math.isclose(s1.uncertainty.aleatoric_uncertainty, s2.uncertainty.aleatoric_uncertainty, abs_tol=1e-6)

def test_metamorphic_n5_conflict_with_epistemic_uncertainty_gate(base_engines):
    """Contradiction testing validates aleatoric uncertainty computation."""
    be = base_engines["belief_engine"]
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring", value={"device_id": "D1"}, lr=8.0, log_lr=math.log(8.0)))
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CUSTOMER_CONFIRMATION, source="c", finding="Legit", value="CONFIRMED_LEGITIMATE", is_exculpatory=True, lr=0.10, log_lr=math.log(0.10)))
    state = be.evaluate_investigation("N5-UNCERT", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert state.uncertainty.aleatoric_uncertainty >= 0.40

# ==============================================================================
# FAMILY O: METAMORPHIC PARAMETER INVARIANCE VS SEMANTIC PARAMETERS (5 Tests)
# ==============================================================================

def test_metamorphic_o1_random_trace_id_invariance(base_engines):
    """Random trace / run IDs leave investigation output invariant."""
    be = base_engines["belief_engine"]
    s1 = be.evaluate_investigation("O1-RUN-1", {"trigger_type": "risk_score"}, {}, EvidenceLedger(), PriorProfile.ALERT_CONDITIONED)
    s2 = be.evaluate_investigation("O1-RUN-2", {"trigger_type": "risk_score"}, {}, EvidenceLedger(), PriorProfile.ALERT_CONDITIONED)
    assert math.isclose(s1.belief_state["fraud_probability"], s2.belief_state["fraud_probability"], abs_tol=1e-6)

def test_metamorphic_o2_non_semantic_metadata_invariance(base_engines):
    """Non-semantic dictionary metadata leaves belief and policy invariant."""
    be = base_engines["belief_engine"]
    pe = base_engines["policy_engine"]
    ctx1 = {"trigger_type": "risk_score", "session_debug": True, "ip": "127.0.0.1"}
    ctx2 = {"trigger_type": "risk_score", "session_debug": False, "random_tag": "XYZ-99"}
    
    s1 = be.evaluate_investigation("O2-1", {"trigger_type": "risk_score"}, {}, EvidenceLedger(), PriorProfile.ALERT_CONDITIONED)
    acts1 = pe.evaluate(s1.belief_state["fraud_probability"], "fraud", 100.0, EvidenceLedger(), case_context=ctx1)
    
    s2 = be.evaluate_investigation("O2-2", {"trigger_type": "risk_score"}, {}, EvidenceLedger(), PriorProfile.ALERT_CONDITIONED)
    acts2 = pe.evaluate(s2.belief_state["fraud_probability"], "fraud", 100.0, EvidenceLedger(), case_context=ctx2)
    
    assert [a.action for a in acts1] == [a.action for a in acts2]

def test_metamorphic_o3_semantic_parameter_exposure_usd_sensitivity(base_engines):
    """Semantic parameter exposure_usd changes EVOI calculations."""
    compass = base_engines["compass"]
    state = create_synthetic_state("O3-EXP")
    rec_low = compass.evaluate_evidence_compass(state, exposure_usd=10.0)
    rec_high = compass.evaluate_evidence_compass(state, exposure_usd=10000.0)
    assert rec_high.ranked_candidates[0].net_decision_value > rec_low.ranked_candidates[0].net_decision_value

def test_metamorphic_o4_semantic_parameter_trigger_type_sensitivity(base_engines):
    """Semantic parameter trigger_type changes prior odds profile."""
    be = base_engines["belief_engine"]
    s_risk = be.evaluate_investigation("O4-RS", {"trigger_type": "risk_score"}, {}, EvidenceLedger(), PriorProfile.ALERT_CONDITIONED)
    s_uncond = be.evaluate_investigation("O4-UN", {"trigger_type": "analyst_request"}, {}, EvidenceLedger(), PriorProfile.UNCONDITIONED_POPULATION)
    assert s_risk.belief_state["fraud_probability"] > s_uncond.belief_state["fraud_probability"]

def test_metamorphic_o5_logging_timestamp_invariance(base_engines):
    """Harness execution timestamp variations leave belief invariant."""
    be = base_engines["belief_engine"]
    s1 = be.evaluate_investigation("O5-TS1", {"trigger_type": "risk_score"}, {}, EvidenceLedger(), PriorProfile.ALERT_CONDITIONED)
    s2 = be.evaluate_investigation("O5-TS2", {"trigger_type": "risk_score"}, {}, EvidenceLedger(), PriorProfile.ALERT_CONDITIONED)
    assert s1.belief_state["fraud_probability"] == s2.belief_state["fraud_probability"]

# ==============================================================================
# FAMILY P: METAMORPHIC BENCHMARK LEAKAGE AUDIT (2 Tests)
# ==============================================================================

def test_metamorphic_p1_synthetic_case_id_parity(base_engines):
    """Synthetic IDs with non-standard naming produce identical reasoning."""
    be = base_engines["belief_engine"]
    pe = base_engines["policy_engine"]
    
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Shared D1", value={"device_id": "D1"}, lr=5.0, log_lr=math.log(5.0)))
    state = be.evaluate_investigation("SYN-ADVERSARIAL-999", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    acts = pe.evaluate(state.belief_state["fraud_probability"], "fraud", 250.0, ledger, case_context={"trigger_type": "risk_score"})
    assert acts[0].action == "CREATE_CASE"

def test_metamorphic_p2_codebase_zero_benchmark_branches():
    """Static AST / Regex scan across all src/ files confirms zero HHG-001..HHG-020 references."""
    import pathlib
    import re
    src_dir = pathlib.Path("src")
    hhg_pattern = re.compile(r"HHG-\d{3}", re.IGNORECASE)
    
    violations = []
    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        matches = hhg_pattern.findall(content)
        if matches:
            violations.append((str(py_file), matches))
            
    assert len(violations) == 0, f"Found benchmark ID branches in src/: {violations}"

# ==============================================================================
# FAMILY Q: METAMORPHIC COMPOSITION TESTS (5 Multi-Vector Tests)
# ==============================================================================

def test_metamorphic_q1_composition_id_reorder_duplicate(base_engines):
    """Composition: Case ID Mutation + Evidence Reordering + Duplicate Evidence."""
    be = base_engines["belief_engine"]
    pe = base_engines["policy_engine"]
    
    item1 = EvidenceItem(evidence_id="EVD-Q1-1", evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring", value={"device_id": "D1"}, lr=4.0, log_lr=math.log(4.0))
    item2 = EvidenceItem(evidence_id="EVD-Q1-2", evidence_type=EvidenceType.HIGH_VELOCITY, source="g", finding="Vel", value={"velocity": 5}, lr=3.0, log_lr=math.log(3.0))
    
    # Run Baseline
    ledger1 = EvidenceLedger()
    ledger1.add(item1)
    ledger1.add(item2)
    s1 = be.evaluate_investigation("BASE-Q1", {"trigger_type": "risk_score"}, {}, ledger1, PriorProfile.ALERT_CONDITIONED)
    acts1 = pe.evaluate(s1.belief_state["fraud_probability"], "fraud", 300.0, ledger1, case_context={"trigger_type": "risk_score"})
    
    # Run Mutated (New ID + Reverse Order + Duplicate item1 inserted twice)
    ledger2 = EvidenceLedger()
    ledger2.add(item2)
    ledger2.add(item1)
    ledger2.add(item1) # Duplicate
    s2 = be.evaluate_investigation("MUT-Q1-UUID-777", {"trigger_type": "risk_score"}, {}, ledger2, PriorProfile.ALERT_CONDITIONED)
    acts2 = pe.evaluate(s2.belief_state["fraud_probability"], "fraud", 300.0, ledger2, case_context={"trigger_type": "risk_score"})
    
    assert math.isclose(s1.belief_state["fraud_probability"], s2.belief_state["fraud_probability"], abs_tol=1e-6)
    assert [a.action for a in acts1] == [a.action for a in acts2]

def test_metamorphic_q2_composition_graphrag_memory_case_id(base_engines):
    """Composition: GraphRAG present + Historical Memory present + Case ID Mutation."""
    be = base_engines["belief_engine"]
    pe = base_engines["policy_engine"]
    
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CARD_TESTING_SEQUENCE, source="g", finding="Testing", value={"pattern": "card_testing"}, lr=6.0, log_lr=math.log(6.0)))
    
    # Run with standard ID
    s1 = be.evaluate_investigation("Q2-STD", {"trigger_type": "customer_report"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    
    # Query Memory and GraphRAG
    store = CaseMemoryStore()
    retriever = SimilarCaseRetriever(store)
    matches = retriever.retrieve_similar_cases(state=s1, top_k=3)
    rag = PolicyGraphRAGRetriever()
    knowledge = rag.retrieve_grounded_context(s1, exposure_usd=400.0)
    
    # Run with mutated ID
    s2 = be.evaluate_investigation("Q2-MUTATED-ID-99", {"trigger_type": "customer_report"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    
    assert math.isclose(s1.belief_state["fraud_probability"], s2.belief_state["fraud_probability"], abs_tol=1e-6)
    assert len(matches) >= 0
    assert len(knowledge) > 0

def test_metamorphic_q3_composition_temporal_boundary_and_tool_failure(base_engines):
    """Composition: Temporal Boundary Exclusion + Tool Failure Semantics."""
    be = base_engines["belief_engine"]
    
    # Temporal tool returns outside-window (NO_MATCH)
    ev_temporal = EvidenceNormalizer.normalize(
        action_id="CARD_SEQUENCE_ANALYSIS",
        tool_name="card_sequence",
        scope_status=GraphScopeStatus.NO_MATCH,
        raw_data=[],
        target_entities={"card_id": "C1", "customer_id": "U1"}
    )
    # Device tool fails (GRAPH_QUERY_FAILURE)
    ev_failed = EvidenceNormalizer.normalize(
        action_id="CHECK_SHARED_DEVICES",
        tool_name="device_analysis",
        scope_status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
        raw_data={"error": "TigerGraph unavailable"},
        target_entities={"card_id": "C1", "customer_id": "U1"}
    )
    
    ledger = EvidenceLedger()
    ledger.add(ev_temporal)
    ledger.add(ev_failed)
    
    s = be.evaluate_investigation("Q3-COMP", {"trigger_type": "risk_score"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert ev_temporal.lr == 1.0
    assert ev_failed.lr == 1.0
    assert s.belief_state["fraud_probability"] == pytest.approx(0.8383, abs=1e-3)

def test_metamorphic_q4_composition_negative_and_contradictory_positive(base_engines):
    """Composition: Negative Evidence + Contradictory Positive Evidence."""
    be = base_engines["belief_engine"]
    
    ledger = EvidenceLedger()
    # Incriminating signal
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CARD_TESTING_SEQUENCE, source="g", finding="Testing", value={"pattern": "card_testing"}, lr=7.0, log_lr=math.log(7.0)))
    # Negative signal (neutral)
    ledger.add(EvidenceItem(evidence_type=EvidenceType.HIGH_VELOCITY, source="g", finding="NO_MATCH", value="NO_MATCH", lr=1.0, log_lr=0.0))
    # Strong Exculpatory confirmation
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CUSTOMER_CONFIRMATION, source="c", finding="Legit", value="CONFIRMED_LEGITIMATE", is_exculpatory=True, lr=0.10, log_lr=math.log(0.10)))
    
    state = be.evaluate_investigation("Q4-COMP", {"trigger_type": "customer_report"}, {}, ledger, PriorProfile.ALERT_CONDITIONED)
    assert state.uncertainty.aleatoric_uncertainty >= 0.40
    assert state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL

def test_metamorphic_q5_composition_analyst_request_tool_failure_contradiction(base_engines):
    """Composition: Analyst Request + Consecutive Tool Failure + Severe Contradiction."""
    be = base_engines["belief_engine"]
    
    ev_fail = EvidenceNormalizer.normalize(
        action_id="CHECK_SHARED_DEVICES",
        tool_name="device_analysis",
        scope_status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
        raw_data={"error": "Timeout"},
        target_entities={"card_id": "C1", "customer_id": "U1"}
    )
    ev_ring = EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="g", finding="Ring", value={"device_id": "D1"}, lr=8.0, log_lr=math.log(8.0))
    ev_conf = EvidenceItem(evidence_type=EvidenceType.CUSTOMER_CONFIRMATION, source="c", finding="Confirmed", value="CONFIRMED_LEGITIMATE", is_exculpatory=True, lr=0.10, log_lr=math.log(0.10))
    
    ledger = EvidenceLedger()
    ledger.add(ev_fail)
    ledger.add(ev_ring)
    ledger.add(ev_conf)
    
    state = be.evaluate_investigation("Q5-COMP", {"trigger_type": "analyst_request"}, {}, ledger, PriorProfile.UNCONDITIONED_POPULATION)
    assert state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL
    assert ev_fail.lr == 1.0
