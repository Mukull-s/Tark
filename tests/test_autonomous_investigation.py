import pytest
import time
from typing import Dict, Any, Optional

from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceItem, EvidenceType, EvidenceDirection
from src.belief.calibration import PriorProfile, EvidenceFamily
from src.belief.state import InvestigationState, DecisionState, WorldHypothesis
from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine
from src.compass.evoi import EvidenceCompass
from src.graph.connection import get_tigergraph_connection
from src.tools.base import EvidenceTool, ToolExecutionResult
from src.tools.dispatcher import EvidenceToolDispatcher
from src.agent.orchestrator import (
    InvestigationOrchestrator,
    InvestigationTerminationReason,
    InvestigationIterationTrace,
    InvestigationRunResult
)
from src.tools.llm_client import LLMClient

# ------------------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------------------

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

@pytest.fixture
def generic_initial_state(belief_engine):
    """Generic initial state with calibrated model score (coverage = 0.20, P = 0.65)."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="realtime_model",
        finding="Model scored transaction at 0.61",
        lr=2.4,
        log_lr=0.875,
        details={"risk_score": 0.61}
    ))
    
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-GENERIC-AUTO-01",
        trigger={
            "trigger_type": "risk_score",
            "flagged_txn_id": "3478561",
            "txn_addr1": 299.0
        },
        target_entities={
            "card_id": "C11923-K2",
            "customer_id": "C12382",
            "flagged_txn_id": "3478561"
        },
        ledger=ledger,
        prior_p=0.43634  # Initial fraud probability ~0.6500
    )
    return state


# ==============================================================================
# 1. Single-Step Investigation to Terminal State
# ==============================================================================

def test_single_step_investigation_reaches_terminal_state(belief_engine, policy_engine, compass, dispatcher, generic_initial_state, tg_conn):
    """Verifies that an initial state executes top EVOI tool (device_analysis), unlocks Decision Gate, and terminates."""
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=5
    )
    
    result = orchestrator.run_investigation(
        initial_state=generic_initial_state,
        exposure_usd=100.0,
        context={"tg_conn": tg_conn}
    )
    
    assert isinstance(result, InvestigationRunResult)
    assert result.total_steps >= 1
    assert result.final_state.decision_gate_passed is True
    assert result.termination_reason == InvestigationTerminationReason.DECISION_REACHED
    assert len(result.iteration_traces) == result.total_steps
    assert result.iteration_traces[0].selected_action == "QUERY_DEVICE_ANALYSIS"
    assert result.iteration_traces[0].belief_after > 0.90


# ==============================================================================
# 2. Multi-Step Investigation
# ==============================================================================

def test_multi_step_investigation_progression(belief_engine, policy_engine, compass, dispatcher, tg_conn):
    """Verifies multi-step loop: Step 1 gathers device analysis, Step 2 gathers card sequence to saturation."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="realtime_model",
        finding="Model scored transaction at 0.50",
        lr=0.85,
        log_lr=-0.163,
        details={"risk_score": 0.50}
    ))
    # Borderline alert where post-step-1 probability still warrants refinement
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-MULTI-STEP-01",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "3478561", "txn_addr1": 299.0},
        target_entities={"card_id": "C11923-K2", "customer_id": "C12382", "flagged_txn_id": "3478561"},
        ledger=ledger,
        prior_p=0.45
    )
    
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=3
    )
    
    result = orchestrator.run_investigation(
        initial_state=state,
        exposure_usd=100.0,
        context={"tg_conn": tg_conn}
    )
    
    assert result.total_steps == 2
    assert result.termination_reason == InvestigationTerminationReason.DECISION_REACHED
    assert [t.selected_action for t in result.iteration_traces] == ["QUERY_DEVICE_ANALYSIS", "QUERY_CARD_SEQUENCE"]
    assert result.iteration_traces[0].termination_check == "CONTINUE"
    assert result.iteration_traces[1].termination_check == "TERMINATE"


# ==============================================================================
# 3. Decision Gate Stops Loop When Terminal Policy Action is Valid
# ==============================================================================

def test_decision_gate_stops_loop(belief_engine, policy_engine, compass, dispatcher, generic_initial_state, tg_conn):
    """Verifies that once Decision Gate passes and terminal action is valid, the orchestrator terminates."""
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=10
    )
    
    result = orchestrator.run_investigation(
        initial_state=generic_initial_state,
        exposure_usd=100.0,
        context={"tg_conn": tg_conn}
    )
    
    assert result.termination_reason == InvestigationTerminationReason.DECISION_REACHED
    assert result.final_state.decision_gate_passed is True
    # Does not endlessly gather every single tool up to max_steps=10
    assert result.total_steps < 10


# ==============================================================================
# 4. Insufficient Evidence Continues Investigation When Positive EVOI Exists
# ==============================================================================

def test_insufficient_evidence_continues_investigation(belief_engine, policy_engine, compass, dispatcher, tg_conn):
    """Verifies that when evidence coverage is insufficient (coverage < 0.40), the loop does not stop prematurely."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="realtime_model",
        finding="Model scored transaction at 0.50",
        lr=0.85,
        log_lr=-0.163,
        details={"risk_score": 0.50}
    ))
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-INSUFF-01",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "3478561", "txn_addr1": 299.0},
        target_entities={"card_id": "C11923-K2", "customer_id": "C12382", "flagged_txn_id": "3478561"},
        ledger=ledger,
        prior_p=0.45
    )
    assert state.decision_gate_passed is False
    assert state.decision_state == DecisionState.INSUFFICIENT_EVIDENCE
    
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=5
    )
    
    result = orchestrator.run_investigation(
        initial_state=state,
        exposure_usd=100.0,
        context={"tg_conn": tg_conn}
    )
    
    # Must have executed at least one action
    assert result.total_steps >= 1


# ==============================================================================
# 5. Human Approval Immediately Stops Autonomous Execution
# ==============================================================================

def test_human_approval_immediately_stops_loop(belief_engine, policy_engine, compass, dispatcher):
    """Verifies that REQUIRES_HUMAN_APPROVAL immediately halts autonomous execution without tool execution."""
    ledger = EvidenceLedger()
    # Inculpatory evidence
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="device",
        finding="Ring detected",
        lr=14.2,
        log_lr=2.653
    ))
    # Exculpatory confirmation
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CUSTOMER_CONFIRMATION,
        source="customer",
        finding="Customer confirmed purchase",
        lr=0.05,
        log_lr=-2.996,
        is_exculpatory=True
    ))
    
    # State with severe contradiction (aleatoric conflict >= 0.40)
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-HUMAN-STOP-01",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "3478561"},
        target_entities={"card_id": "C11923-K2"},
        ledger=ledger,
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE
    )
    assert state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL
    
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=5
    )
    
    result = orchestrator.run_investigation(initial_state=state, exposure_usd=100.0)
    
    # Must stop immediately: 0 steps executed
    assert result.total_steps == 0
    assert result.termination_reason == InvestigationTerminationReason.HUMAN_APPROVAL_REQUIRED


# ==============================================================================
# 6. Negative EVOI Stops Investigation
# ==============================================================================

def test_negative_evoi_stops_investigation(belief_engine, policy_engine, compass, dispatcher):
    """Verifies that when all candidates have negative Net Decision Value, the loop stops with NEGATIVE_EVOI."""
    # Saturated state where all key tools have already been executed
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="dev", finding="f1", lr=14.2, log_lr=2.653))
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CARD_TESTING_SEQUENCE, source="seq", finding="f2", lr=34.3, log_lr=3.535))
    ledger.add(EvidenceItem(evidence_type=EvidenceType.HIGH_VELOCITY, source="vel", finding="f3", lr=2.5, log_lr=0.916))
    
    # Very small exposure ($1.00) means information value is much less than operational burden cost ($5 - $20)
    state = belief_engine.evaluate_investigation(
        investigation_id="INV-NEG-EVOI-01",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "3478561"},
        target_entities={"card_id": "C11923-K2", "customer_id": "C12382", "flagged_txn_id": "3478561"},
        ledger=ledger,
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE
    )
    
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=5
    )
    
    result = orchestrator.run_investigation(initial_state=state, exposure_usd=0.50)
    
    # Must terminate due to DECISION_REACHED or NEGATIVE_EVOI
    assert result.termination_reason in [
        InvestigationTerminationReason.DECISION_REACHED,
        InvestigationTerminationReason.NEGATIVE_EVOI
    ]


# ==============================================================================
# 7. Maximum Step Budget is Enforced
# ==============================================================================

def test_max_steps_budget_enforced(belief_engine, policy_engine, compass, dispatcher, generic_initial_state, tg_conn):
    """Verifies that the orchestrator strictly enforces max_steps budget."""
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=1  # Strict limit: exactly 1 step
    )
    
    result = orchestrator.run_investigation(
        initial_state=generic_initial_state,
        exposure_usd=100.0,
        context={"tg_conn": tg_conn}
    )
    
    # Total steps cannot exceed max_steps
    assert result.total_steps <= 1


# ==============================================================================
# 8. Duplicate Evidence Action Prevention
# ==============================================================================

def test_duplicate_action_prevention(belief_engine, policy_engine, compass, dispatcher, generic_initial_state, tg_conn):
    """Verifies that an action cannot be selected or executed twice in the same loop."""
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=5
    )
    
    result = orchestrator.run_investigation(
        initial_state=generic_initial_state,
        exposure_usd=100.0,
        context={"tg_conn": tg_conn}
    )
    
    actions_executed = [t.selected_action for t in result.iteration_traces]
    # All executed actions must be strictly unique
    assert len(actions_executed) == len(set(actions_executed))


# ==============================================================================
# 9. Repeated Actionable Tool Failures Terminate Safely
# ==============================================================================

class MockFailingTool(EvidenceTool):
    @property
    def action_id(self) -> str:
        return "QUERY_DEVICE_ANALYSIS"
    @property
    def action_type(self) -> str:
        return "GSQL_QUERY"
    @property
    def tool_name(self) -> str:
        return "device_analysis"
    @property
    def required_parameters(self) -> list:
        return []
    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
        return ToolExecutionResult(
            action_id=self.action_id,
            tool_name=self.tool_name,
            parameters=params,
            scope_status="GRAPH_QUERY_FAILURE",
            status="FAILED",
            message="Simulated repeated hardware network timeout."
        )

def test_repeated_tool_failures_terminate_safely(belief_engine, policy_engine, compass, generic_initial_state):
    """Verifies that consecutive tool failures trigger TOOL_FAILURE_LIMIT."""
    failing_dispatcher = EvidenceToolDispatcher(belief_engine)
    failing_dispatcher.register_tool(MockFailingTool())
    
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=failing_dispatcher,
        consecutive_failure_limit=1,  # 1 failure terminates
        max_steps=5
    )
    
    result = orchestrator.run_investigation(
        initial_state=generic_initial_state,
        exposure_usd=100.0
    )
    
    assert result.termination_reason == InvestigationTerminationReason.TOOL_FAILURE_LIMIT


# ==============================================================================
# 10. No Admissible Evidence Terminates Safely
# ==============================================================================

def test_no_admissible_evidence_terminates_safely(belief_engine, policy_engine, generic_initial_state, dispatcher):
    """Verifies safe termination when Compass returns no admissible candidates."""
    class EmptyCompass:
        def evaluate_evidence_compass(self, state, exposure_usd=100.0):
            from src.compass.evoi import EvidenceCompassRecommendation
            return EvidenceCompassRecommendation(
                investigation_id=state.investigation_id,
                current_fraud_prob=0.5,
                current_primary_action="MONITOR_CARD",
                current_decision_state="INSUFFICIENT_EVIDENCE",
                top_recommendation=None,
                ranked_candidates=[],
                should_stop_gathering=True,
                stopping_reason="No candidates available."
            )
    
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=EmptyCompass(),
        dispatcher=dispatcher,
        max_steps=5
    )
    
    result = orchestrator.run_investigation(initial_state=generic_initial_state)
    assert result.termination_reason == InvestigationTerminationReason.NO_ADMISSIBLE_EVIDENCE


# ==============================================================================
# 11. Unregistered Action Cannot Execute
# ==============================================================================

def test_unregistered_action_cannot_execute(dispatcher, generic_initial_state):
    """Verifies that dispatcher strictly rejects arbitrary/unregistered actions."""
    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=generic_initial_state,
        candidate_action="ARBITRARY_UNREGISTERED_TOOL_CALL",
        parameters={"hack": True}
    )
    assert res.status == "REJECTED"
    assert "not a registered approved evidence tool" in res.message
    assert len(updated_state.evidence_items) == len(generic_initial_state.evidence_items)


# ==============================================================================
# 12. All Execution Flows Through EvidenceToolDispatcher
# ==============================================================================

def test_all_execution_flows_through_dispatcher(belief_engine, policy_engine, compass, dispatcher, generic_initial_state, tg_conn):
    """Verifies that the orchestrator cannot execute any tool outside the EvidenceToolDispatcher."""
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=1
    )
    res = orchestrator.run_investigation(generic_initial_state, context={"tg_conn": tg_conn})
    assert len(res.iteration_traces) == 1
    # Trace must have a valid dispatcher execution trace
    assert res.iteration_traces[0].dispatcher_execution_trace is not None
    assert res.iteration_traces[0].dispatcher_execution_trace.execution_status in ["DATA_AVAILABLE", "SUCCESS"]


# ==============================================================================
# 13. LLM Cannot Modify Belief Probability
# ==============================================================================

def test_llm_cannot_modify_belief(belief_engine, policy_engine, compass, dispatcher, generic_initial_state):
    """Verifies that LLM text generation cannot alter numeric fraud belief probability."""
    class FakeLLM:
        def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.1, max_tokens: int = 300) -> str:
            return "FRAUD PROBABILITY: 0.0001 (OVERRIDDEN BY LLM)"

    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        llm_client=FakeLLM(),
        max_steps=1
    )
    res = orchestrator.run_investigation(generic_initial_state, enable_llm_synthesis=True)
    assert res.final_state.belief_state["fraud_probability"] != 0.0001
    assert res.final_state.belief_state["fraud_probability"] == generic_initial_state.belief_state["fraud_probability"] or res.final_state.belief_state["fraud_probability"] > 0.8


# ==============================================================================
# 14. LLM Cannot Modify Evidence Coverage
# ==============================================================================

def test_llm_cannot_modify_coverage(belief_engine, policy_engine, compass, dispatcher, generic_initial_state):
    """Verifies that LLM text generation cannot fabricate or alter multi-dimensional coverage."""
    class FakeLLM:
        def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.1, max_tokens: int = 300) -> str:
            return "COVERAGE IS 100%. ALL DIMENSIONS OBSERVED."

    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        llm_client=FakeLLM(),
        max_steps=1
    )
    res = orchestrator.run_investigation(generic_initial_state, enable_llm_synthesis=True)
    assert res.final_state.uncertainty.evidence_coverage != 1.0
    assert res.final_state.uncertainty.evidence_coverage in [0.20, 0.40]


# ==============================================================================
# 15. LLM Cannot Bypass Decision Gate
# ==============================================================================

def test_llm_cannot_bypass_decision_gate(belief_engine, policy_engine, compass, dispatcher):
    """Verifies that LLM text generation cannot unlock the Decision Gate when coverage is insufficient."""
    ledger = EvidenceLedger()
    state = belief_engine.evaluate_investigation("INV-GATE-TEST", {}, {}, ledger, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE)
    assert state.decision_gate_passed is False

    class FakeLLM:
        def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.1, max_tokens: int = 300) -> str:
            return "DECISION GATE: PASSED. CONFIRMED UNLOCKED."

    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        llm_client=FakeLLM(),
        max_steps=1
    )
    res = orchestrator.run_investigation(state, enable_llm_synthesis=True)
    assert res.final_state.decision_gate_passed is False
    assert res.final_state.decision_state == DecisionState.INSUFFICIENT_EVIDENCE


# ==============================================================================
# 16. Contradictory Evidence Escalation
# ==============================================================================

def test_contradictory_evidence_causes_human_escalation(belief_engine, policy_engine, compass, dispatcher):
    """Verifies that severe evidentiary conflict immediately halts autonomous loop under HUMAN_APPROVAL_REQUIRED."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.SHARED_DEVICE_RING, source="dev", finding="f1", lr=14.2, log_lr=2.653))
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CUSTOMER_CONFIRMATION, source="cust", finding="f2", lr=0.05, log_lr=-2.996, is_exculpatory=True))
    
    state = belief_engine.evaluate_investigation(
        "INV-CONTRAD-01", {}, {}, ledger, prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE
    )
    assert state.uncertainty.aleatoric_uncertainty >= 0.40
    
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher
    )
    res = orchestrator.run_investigation(state)
    assert res.termination_reason == InvestigationTerminationReason.HUMAN_APPROVAL_REQUIRED
    assert res.total_steps == 0


# ==============================================================================
# 17. Benchmark Case Neutrality
# ==============================================================================

def test_benchmark_case_neutrality(belief_engine, policy_engine, compass, dispatcher, tg_conn):
    """Verifies that benchmark IDs (e.g. HHG-014) follow the EXACT same logic as generic IDs."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="bank_model",
        finding="Risk score 0.61",
        lr=2.4,
        log_lr=0.875
    ))
    
    state_hhg = belief_engine.evaluate_investigation(
        investigation_id="HHG-014",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "3478561"},
        target_entities={"card_id": "C11923-K2", "customer_id": "C12382", "flagged_txn_id": "3478561"},
        ledger=ledger,
        prior_p=0.43634
    )
    state_gen = belief_engine.evaluate_investigation(
        investigation_id="GENERIC-RANDOM-999",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "3478561"},
        target_entities={"card_id": "C11923-K2", "customer_id": "C12382", "flagged_txn_id": "3478561"},
        ledger=ledger,
        prior_p=0.43634
    )
    
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=2
    )
    
    res_hhg = orchestrator.run_investigation(state_hhg, context={"tg_conn": tg_conn})
    res_gen = orchestrator.run_investigation(state_gen, context={"tg_conn": tg_conn})
    
    assert res_hhg.termination_reason == res_gen.termination_reason
    assert res_hhg.total_steps == res_gen.total_steps
    assert [t.selected_action for t in res_hhg.iteration_traces] == [t.selected_action for t in res_gen.iteration_traces]


# ==============================================================================
# 18. Generic Non-Benchmark Trigger Handling
# ==============================================================================

def test_generic_non_benchmark_trigger(belief_engine, policy_engine, compass, dispatcher, tg_conn):
    """Verifies that generic production alerts without benchmark schema operate seamlessly."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="realtime_api_gateway",
        finding="Online transaction scored high risk",
        lr=2.4,
        log_lr=0.875
    ))
    generic_state = belief_engine.evaluate_investigation(
        investigation_id="PROD-LIVE-ALERT-771",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "3478561", "txn_addr1": 299.0},
        target_entities={"card_id": "C11923-K2", "customer_id": "C12382", "flagged_txn_id": "3478561"},
        ledger=ledger,
        prior_p=0.45
    )
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine, policy_engine=policy_engine, compass=compass, dispatcher=dispatcher, max_steps=2
    )
    res = orchestrator.run_investigation(generic_state, context={"tg_conn": tg_conn})
    assert res.total_steps >= 1
    assert res.termination_reason == InvestigationTerminationReason.DECISION_REACHED


# ==============================================================================
# 19. Investigation Trace Completeness
# ==============================================================================

def test_investigation_trace_completeness(belief_engine, policy_engine, compass, dispatcher, generic_initial_state, tg_conn):
    """Verifies that every iteration contains a complete before/after audit trace."""
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine, policy_engine=policy_engine, compass=compass, dispatcher=dispatcher, max_steps=2
    )
    res = orchestrator.run_investigation(generic_initial_state, context={"tg_conn": tg_conn})
    assert len(res.iteration_traces) >= 1
    for trace in res.iteration_traces:
        assert trace.iteration >= 1
        assert 0.0 <= trace.belief_before <= 1.0
        assert 0.0 <= trace.belief_after <= 1.0
        assert 0.0 <= trace.coverage_before <= 1.0
        assert 0.0 <= trace.coverage_after <= 1.0
        assert trace.selected_action != ""
        assert trace.termination_check in ["CONTINUE", "TERMINATE"]


# ==============================================================================
# 20. Explicit Termination Reason on Every Run
# ==============================================================================

def test_explicit_termination_reason_on_every_run(belief_engine, policy_engine, compass, dispatcher, generic_initial_state, tg_conn):
    """Verifies that every run produces an explicit, non-null InvestigationTerminationReason enum."""
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine, policy_engine=policy_engine, compass=compass, dispatcher=dispatcher, max_steps=1
    )
    res = orchestrator.run_investigation(generic_initial_state, context={"tg_conn": tg_conn})
    assert isinstance(res.termination_reason, InvestigationTerminationReason)
    assert res.termination_reason.value in [r.value for r in InvestigationTerminationReason]


# ==============================================================================
# 21. Tool Never Executed After Terminal State
# ==============================================================================

def test_tool_never_executed_after_terminal_state(belief_engine, policy_engine, compass, dispatcher, generic_initial_state, tg_conn):
    """Verifies that the orchestrator does NOT execute additional tools once terminal state is reached."""
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=5
    )
    
    result = orchestrator.run_investigation(
        initial_state=generic_initial_state,
        context={"tg_conn": tg_conn}
    )
    
    # Verify that the last trace has termination_reason matching the run result
    assert result.iteration_traces[-1].termination_reason == result.termination_reason
    assert result.iteration_traces[-1].termination_check == "TERMINATE"


# ==============================================================================
# 22. NO_MATCH Does Not Unlock Coverage in Loop
# ==============================================================================

def test_no_match_does_not_unlock_coverage_in_loop(belief_engine, policy_engine, compass):
    """Verifies that NO_MATCH from a tool does not artificially unlock coverage or gate."""
    class MockNoMatchTool(EvidenceTool):
        @property
        def action_id(self) -> str:
            return "QUERY_DEVICE_ANALYSIS"
        @property
        def action_type(self) -> str:
            return "GSQL_QUERY"
        @property
        def tool_name(self) -> str:
            return "device_analysis"
        @property
        def required_parameters(self) -> list:
            return []
        def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
            return ToolExecutionResult(
                action_id=self.action_id,
                tool_name=self.tool_name,
                parameters=params,
                scope_status="DATA_AVAILABLE",
                status="NO_MATCH",
                raw_data=[{"device_id": "D1", "is_proxy": False, "shared_card_count": 0}],
                message="Clean device."
            )
            
    disp = EvidenceToolDispatcher(belief_engine)
    disp.register_tool(MockNoMatchTool())
    
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CALIBRATED_RISK_SCORE, source="m", finding="m", lr=2.4, log_lr=0.875))
    state = belief_engine.evaluate_investigation("INV-NM", {}, {"card_id": "C1", "flagged_txn_id": "T1"}, ledger)
    assert state.uncertainty.evidence_coverage == 0.20
    
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine, policy_engine=policy_engine, compass=compass, dispatcher=disp, max_steps=1
    )
    res = orchestrator.run_investigation(state)
    assert res.final_state.uncertainty.evidence_coverage == 0.20
    assert res.final_state.decision_gate_passed is False


# ==============================================================================
# 23. DATA_OUT_OF_SCOPE Does Not Become Negative Evidence
# ==============================================================================

def test_data_out_of_scope_does_not_become_negative_evidence(belief_engine, policy_engine, compass):
    """Verifies that DATA_OUT_OF_SCOPE records missing information and does not reduce fraud probability."""
    class MockOosTool(EvidenceTool):
        def __init__(self, action_id="QUERY_DEVICE_ANALYSIS", tool_name="device_analysis", ev_type=EvidenceType.SHARED_DEVICE_RING):
            self._action_id = action_id
            self._tool_name = tool_name
            self._ev_type = ev_type
        @property
        def action_id(self) -> str:
            return self._action_id
        @property
        def action_type(self) -> str:
            return "GSQL_QUERY"
        @property
        def tool_name(self) -> str:
            return self._tool_name
        @property
        def required_parameters(self) -> list:
            return []
        def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
            ev = EvidenceItem(
                evidence_type=self._ev_type,
                value="DATA_OUT_OF_SCOPE",
                source=self._tool_name,
                finding=f"Historical {self._tool_name} data out of scope",
                graph_query=self._tool_name
            )
            return ToolExecutionResult(
                action_id=self.action_id,
                tool_name=self.tool_name,
                parameters=params,
                scope_status="DATA_OUT_OF_SCOPE",
                status="OUT_OF_SCOPE",
                evidence_item=ev,
                message=f"Historical {self._tool_name} data unobserved."
            )
    disp = EvidenceToolDispatcher(belief_engine)
    disp.register_tool(MockOosTool("QUERY_DEVICE_ANALYSIS", "device_analysis", EvidenceType.SHARED_DEVICE_RING))
    disp.register_tool(MockOosTool("QUERY_CARD_SEQUENCE", "card_sequence", EvidenceType.CARD_TESTING_SEQUENCE))
    
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CALIBRATED_RISK_SCORE, source="m", finding="m", lr=2.4, log_lr=0.875))
    state = belief_engine.evaluate_investigation("INV-OOS", {}, {"card_id": "C1", "flagged_txn_id": "T1"}, ledger)
    p_before = state.belief_state["fraud_probability"]
    
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine, policy_engine=policy_engine, compass=compass, dispatcher=disp, max_steps=1
    )
    res = orchestrator.run_investigation(state)
    assert res.final_state.belief_state["fraud_probability"] == pytest.approx(p_before, abs=1e-4)
    assert len(res.final_state.missing_information) == 1
    assert res.final_state.missing_information[0].reason == "DATA_OUT_OF_SCOPE"


# ==============================================================================
# 24. GRAPH_QUERY_FAILURE Does Not Change Probability
# ==============================================================================

def test_graph_query_failure_does_not_change_probability(belief_engine, policy_engine, compass):
    """Verifies that GRAPH_QUERY_FAILURE preserves coherent state without modifying belief."""
    class MockFailTool(EvidenceTool):
        @property
        def action_id(self) -> str:
            return "QUERY_CARD_SEQUENCE"
        @property
        def action_type(self) -> str:
            return "GSQL_QUERY"
        @property
        def tool_name(self) -> str:
            return "card_sequence"
        @property
        def required_parameters(self) -> list:
            return []
        def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
            return ToolExecutionResult(
                action_id=self.action_id,
                tool_name=self.tool_name,
                parameters=params,
                scope_status="GRAPH_QUERY_FAILURE",
                status="FAILED",
                message="RESTPP execution timeout 504."
            )
    disp = EvidenceToolDispatcher(belief_engine)
    disp.register_tool(MockFailTool())
    
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(evidence_type=EvidenceType.CALIBRATED_RISK_SCORE, source="m", finding="m", lr=2.4, log_lr=0.875))
    state = belief_engine.evaluate_investigation("INV-FAIL", {}, {"card_id": "C1", "flagged_txn_id": "T1"}, ledger)
    p_before = state.belief_state["fraud_probability"]
    
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine, policy_engine=policy_engine, compass=compass, dispatcher=disp, max_steps=1
    )
    res = orchestrator.run_investigation(state)
    assert res.final_state.belief_state["fraud_probability"] == pytest.approx(p_before, abs=1e-4)


# ==============================================================================
# 25. True End-to-End Integration Test (TigerGraph cluster)
# ==============================================================================

def test_true_end_to_end_investigation_loop(belief_engine, policy_engine, compass, dispatcher, generic_initial_state, tg_conn):
    """True End-to-End Test:

    Trigger -> InvestigationOrchestrator -> Compass -> Dispatcher ->
    TigerGraph Cluster -> Normalizer -> EvidenceItem -> BeliefEngine ->
    Decision Gate -> Terminal State.
    """
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=5
    )
    
    result = orchestrator.run_investigation(
        initial_state=generic_initial_state,
        exposure_usd=100.0,
        context={"tg_conn": tg_conn}
    )
    
    # 1. Trajectory verification
    assert result.total_steps >= 1
    assert result.termination_reason == InvestigationTerminationReason.DECISION_REACHED
    
    # 2. State verification
    assert result.final_state.decision_gate_passed is True
    assert result.final_state.belief_state["fraud_probability"] > 0.90
    assert result.final_state.uncertainty.evidence_coverage >= 0.40
    assert result.final_policy_actions[0].action in ["CREATE_CASE", "BLOCK_CARD", "DECLINE_TRANSACTION"]
    
    # 3. Trace verification
    assert len(result.iteration_traces) == result.total_steps
    assert result.execution_duration_sec > 0.0
    assert "AUTONOMOUS INVESTIGATION SUMMARY" in result.executive_summary
