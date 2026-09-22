"""Breadth proof: STEP_UP_AUTH wins over VERIFY_WITH_CUSTOMER for in-flight fraud.

Demonstrates that the Evidence Compass is genuinely decision-theoretic and not a
fixed query ordering: for an in-flight authorization trigger, interactive step-up
authentication has strictly higher Net Decision Value than out-of-band customer
verification (lower operational burden, higher P(denial|fraud)), the compass
selects it as the top recommendation, and the orchestrator fires it with a full
execution trace.
"""

import pytest

from src.evidence.ledger import EvidenceLedger
from src.belief.engine import BeliefEngine
from src.belief.calibration import PriorProfile
from src.policy.engine import PolicyEngine
from src.compass.evoi import EvidenceCompass
from src.tools.dispatcher import EvidenceToolDispatcher
from src.agent.orchestrator import InvestigationOrchestrator, InvestigationTerminationReason


@pytest.fixture
def belief_engine():
    return BeliefEngine()


@pytest.fixture
def policy_engine():
    return PolicyEngine()


@pytest.fixture
def compass(belief_engine, policy_engine):
    return EvidenceCompass(belief_engine, policy_engine)


def _in_flight_state(belief_engine, prior_p=0.50):
    return belief_engine.evaluate_investigation(
        investigation_id="INV-INFLIGHT-STEPUP",
        trigger={
            "trigger_type": "in_flight_auth",
            "is_in_flight": True,
            "flagged_txn_id": "TXN-INFLIGHT-01",
            "timestamp": "2016-12-01 10:00:00",
        },
        target_entities={
            "card_id": "C-INFLIGHT-01",
            "customer_id": "CUST-INFLIGHT-01",
            "flagged_txn_id": "TXN-INFLIGHT-01",
        },
        ledger=EvidenceLedger(),
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE,
        prior_p=prior_p,
    )


def test_stepup_net_value_beats_verify_in_flight(compass, belief_engine):
    """STEP_UP_AUTH strictly dominates VERIFY_WITH_CUSTOMER in an in-flight context."""
    state = _in_flight_state(belief_engine)
    rec = compass.evaluate_evidence_compass(state, exposure_usd=50.0)
    by_id = {c.action_id: c for c in rec.ranked_candidates}

    assert "STEP_UP_AUTH" in by_id, "In-flight context must expose STEP_UP_AUTH as a candidate"
    assert "VERIFY_WITH_CUSTOMER" in by_id

    step_up = by_id["STEP_UP_AUTH"]
    verify = by_id["VERIFY_WITH_CUSTOMER"]

    assert step_up.net_decision_value > verify.net_decision_value
    # STEP_UP is cheaper and has higher decision value -> it must be the top recommendation.
    assert rec.top_recommendation is not None
    assert rec.top_recommendation.action_id == "STEP_UP_AUTH"

    # Cost structure sanity: step-up is materially cheaper than out-of-band verification.
    assert step_up.operational_burden_cost < verify.operational_burden_cost
    # Decision value must exceed the operational cost (positive net value).
    assert step_up.net_decision_value > 0.0


def test_stepup_fires_and_records_execution_trace(belief_engine, policy_engine, compass):
    """The orchestrator dispatches STEP_UP_AUTH and records a full auditable trace."""
    dispatcher = EvidenceToolDispatcher(belief_engine)
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=3,
    )

    state = _in_flight_state(belief_engine)
    result = orchestrator.run_investigation(
        initial_state=state,
        exposure_usd=50.0,
        context={"fixture_result": False},  # deterministic AUTH_FAILED outcome
    )

    assert result.total_steps >= 1
    first = result.iteration_traces[0]
    assert first.selected_action == "STEP_UP_AUTH"

    trace = first.dispatcher_execution_trace
    assert trace is not None
    assert trace.selected_action == "STEP_UP_AUTH"
    assert trace.tool_name == "simulate_step_up_auth"
    assert trace.execution_status == "COMPLETED"
    assert result.termination_reason in list(InvestigationTerminationReason)


def test_stepup_not_offered_without_in_flight_context(compass, belief_engine):
    """STEP_UP_AUTH is context-gated: it is absent for a non-in-flight risk alert."""
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-RISK-NO-STEPUP",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "TXN-RISK-01"},
        target_entities={"card_id": "C-RISK", "customer_id": "CUST-RISK", "flagged_txn_id": "TXN-RISK-01"},
        ledger=EvidenceLedger(),
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE,
        prior_p=0.50,
    )
    rec = compass.evaluate_evidence_compass(state, exposure_usd=50.0)
    ids = {c.action_id for c in rec.ranked_candidates}
    assert "STEP_UP_AUTH" not in ids
    assert "VERIFY_WITH_CUSTOMER" in ids
