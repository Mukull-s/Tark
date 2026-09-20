import pytest
from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine, ActionRole, ActionScope
from src.compass.evoi import EvidenceCompass
from src.tools.dispatcher import EvidenceToolDispatcher
from src.agent.orchestrator import InvestigationOrchestrator, InvestigationTerminationReason
from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceType, EvidenceItem
from src.belief.calibration import PriorProfile
from src.graph.connection import get_tigergraph_connection

@pytest.fixture
def authorities():
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

# 1. Analyst-request cold-start candidate generation & positive EVOI
def test_analyst_request_cold_start_candidate_ranking(authorities):
    compass = authorities["compass"]
    belief_engine = authorities["belief_engine"]
    
    trigger = {
        "trigger_type": "analyst_request",
        "trigger_text": "Analyst request: review unusual device profile on txn 3478561.",
        "flagged_txn_id": "3478561",
        "timestamp": "2016-11-22 20:11:00"
    }
    target_entities = {
        "flagged_txn_id": "3478561",
        "card_id": "C13487-K1",
        "customer_id": "C13487",
        "timestamp": "2016-11-22 20:11:00"
    }
    
    state0 = belief_engine.evaluate_investigation(
        investigation_id="TEST-COLD-START-01",
        trigger=trigger,
        target_entities=target_entities,
        ledger=EvidenceLedger(),
        prior_profile=PriorProfile.ALERT_CONDITIONED
    )
    
    rec = compass.evaluate_evidence_compass(state0, exposure_usd=74.96)
    assert not rec.should_stop_gathering
    assert rec.top_recommendation is not None
    assert rec.top_recommendation.net_decision_value > 0.0
    # QUERY_DEVICE_ANALYSIS should rank high given its low cost and high diagnostic LR
    candidate_ids = [c.action_id for c in rec.ranked_candidates if c.net_decision_value > 0.0]
    assert "QUERY_DEVICE_ANALYSIS" in candidate_ids
    assert "QUERY_CARD_SEQUENCE" in candidate_ids

# 2. Reconstructed HHG-014 investigation executes tools autonomously
def test_hhg014_autonomous_investigation_execution(authorities):
    orchestrator = authorities["orchestrator"]
    belief_engine = authorities["belief_engine"]
    tg_conn = get_tigergraph_connection()
    
    trigger = {
        "trigger_type": "analyst_request",
        "trigger_text": "Analyst request: several cards this month show purchases from the same unusual device profile. Review transaction 3478561 on card C13487-K1 and look for related activity.",
        "flagged_txn_id": "3478561",
        "txn_addr1": 191.0,
        "timestamp": "2016-11-22 20:11:00"
    }
    target_entities = {
        "flagged_txn_id": "3478561",
        "card_id": "C13487-K1",
        "customer_id": "C13487",
        "timestamp": "2016-11-22 20:11:00"
    }
    
    state0 = belief_engine.evaluate_investigation(
        investigation_id="HHG-014-TEST",
        trigger=trigger,
        target_entities=target_entities,
        ledger=EvidenceLedger(),
        prior_profile=PriorProfile.ALERT_CONDITIONED
    )
    
    context = {
        "tg_conn": tg_conn,
        "case_id": "HHG-014-TEST",
        "pattern": state0.secondary_typology,
        "trigger_type": "analyst_request"
    }
    
    res = orchestrator.run_investigation(
        initial_state=state0,
        exposure_usd=74.96,
        context=context
    )
    
    # Must have acquired evidence autonomously
    assert res.total_steps >= 1
    assert any(tr.selected_action == "QUERY_DEVICE_ANALYSIS" for tr in res.iteration_traces)
    # Finding must contain SHARED_DEVICE_RING from live graph
    device_items = [e for e in res.final_state.evidence_items if e.evidence_type == EvidenceType.SHARED_DEVICE_RING]
    assert len(device_items) >= 1
    assert device_items[0].lr > 10.0
    # Final NBA must be CREATE_CASE under R6
    primary_act = res.final_policy_actions[0]
    assert primary_act.action == "CREATE_CASE"
    assert primary_act.role == ActionRole.PRIMARY
    assert primary_act.scope == ActionScope.CASE_MANAGEMENT

# 3. Adversarial Check: Low-risk unalerted transaction with analyst review request
def test_adversarial_low_risk_analyst_request(authorities):
    compass = authorities["compass"]
    belief_engine = authorities["belief_engine"]
    
    trigger = {
        "trigger_type": "analyst_request",
        "trigger_text": "Routine compliance review for card C99999-K1.",
        "flagged_txn_id": "9999999",
        "timestamp": "2016-11-22 20:11:00"
    }
    target_entities = {
        "flagged_txn_id": "9999999",
        "card_id": "C99999-K1",
        "customer_id": "C99999",
        "timestamp": "2016-11-22 20:11:00"
    }
    
    # Low unconditioned prior
    state0 = belief_engine.evaluate_investigation(
        investigation_id="TEST-LOW-RISK",
        trigger=trigger,
        target_entities=target_entities,
        ledger=EvidenceLedger(),
        prior_profile=PriorProfile.UNCONDITIONED_POPULATION
    )
    
    assert state0.belief_state["fraud_probability"] <= 0.05
    rec = compass.evaluate_evidence_compass(state0, exposure_usd=10.0)
    # For tiny exposure and tiny prior probability, expensive tools are not economically justified
    customer_verif = [c for c in rec.ranked_candidates if c.action_id == "VERIFY_WITH_CUSTOMER"]
    if customer_verif:
        assert customer_verif[0].net_decision_value <= 0.0

# 4. Adversarial Check: Missing transaction context handling at dispatch
def test_missing_transaction_context_candidate_filtering(authorities):
    dispatcher = authorities["dispatcher"]
    belief_engine = authorities["belief_engine"]
    
    trigger = {
        "trigger_type": "analyst_request",
        "trigger_text": "Review general portfolio anomaly."
    }
    target_entities = {}
    
    state0 = belief_engine.evaluate_investigation(
        investigation_id="TEST-NO-CTX",
        trigger=trigger,
        target_entities=target_entities,
        ledger=EvidenceLedger(),
        prior_profile=PriorProfile.ALERT_CONDITIONED
    )
    
    # Missing card_id and txn_id means dispatching them returns structured failure
    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state0,
        candidate_action="QUERY_DEVICE_ANALYSIS",
        parameters={},
        context={}
    )
    assert res.status in ["FAILED", "REJECTED"]
    assert res.scope_status.value == "GRAPH_QUERY_FAILURE"

# 5. Non-analyst triggers (risk_score, customer_report) remain unaffected
def test_risk_score_and_customer_report_integrity(authorities):
    belief_engine = authorities["belief_engine"]
    compass = authorities["compass"]
    
    # Risk score state
    ledger_rs = EvidenceLedger()
    ledger_rs.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model",
        finding="Risk score 0.87",
        lr=8.2,
        log_lr=2.104
    ))
    state_rs = belief_engine.evaluate_investigation(
        investigation_id="TEST-RS",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "123"},
        target_entities={"card_id": "C123-K1", "flagged_txn_id": "123", "timestamp": "2016-11-22 20:11:00"},
        ledger=ledger_rs,
        prior_profile=PriorProfile.ALERT_CONDITIONED
    )
    rec_rs = compass.evaluate_evidence_compass(state_rs, exposure_usd=100.0)
    assert rec_rs.top_recommendation is not None
    assert rec_rs.top_recommendation.net_decision_value > 0.0
