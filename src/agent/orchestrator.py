import time
import uuid
import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from pydantic import BaseModel, Field

from src.evidence.types import EvidenceItem, EvidenceType
from src.evidence.ledger import EvidenceLedger
from src.belief.engine import BeliefEngine
from src.belief.state import InvestigationState, DecisionState, WorldHypothesis
from src.policy.engine import PolicyEngine, ActionRecommendation
from src.compass.evoi import EvidenceCompass, EvidenceCompassRecommendation, CandidateEvidenceEvaluation
from src.tools.base import ToolExecutionResult, EvidenceExecutionTrace
from src.tools.dispatcher import EvidenceToolDispatcher
from src.tools.llm_client import LLMClient
from src.memory.models import SimilarCaseMatch, CaseMemoryRecord, MemoryProvenanceType
from src.memory.store import CaseMemoryStore
from src.memory.retriever import SimilarCaseRetriever
from src.knowledge.models import RetrievedKnowledgeItem
from src.knowledge.retriever import PolicyGraphRAGRetriever
from src.synthesis.context import InvestigationContextAssembler
from src.synthesis.synthesizer import GroundedInvestigationSynthesizer


class InvestigationTerminationReason(str, Enum):
    """Authoritative, deterministic termination conditions for Tark investigation loop."""
    DECISION_REACHED = "DECISION_REACHED"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    NO_ADMISSIBLE_EVIDENCE = "NO_ADMISSIBLE_EVIDENCE"
    NEGATIVE_EVOI = "NEGATIVE_EVOI"
    MAX_STEPS_REACHED = "MAX_STEPS_REACHED"
    TOOL_FAILURE_LIMIT = "TOOL_FAILURE_LIMIT"
    ORCHESTRATION_ERROR = "ORCHESTRATION_ERROR"


class InvestigationIterationTrace(BaseModel):
    """First-class auditable record of a single autonomous investigation iteration."""
    investigation_id: str
    iteration: int
    
    # State before iteration
    belief_before: float
    coverage_before: float
    uncertainty_before: float
    decision_state_before: str
    gate_passed_before: bool
    
    # Evidence Compass evaluation
    admissible_candidate_actions: List[str]
    candidate_net_decision_values: Dict[str, float]
    selected_action: str
    selection_rationale: str
    
    # Tool execution & evidence
    dispatcher_execution_trace: Optional[EvidenceExecutionTrace] = None
    observed_evidence_summary: Optional[str] = None
    
    # State after iteration
    belief_after: float
    coverage_after: float
    uncertainty_after: float
    decision_state_after: str
    gate_passed_after: bool
    policy_action: Optional[str] = None
    
    # Termination status
    termination_check: str
    termination_reason: Optional[InvestigationTerminationReason] = None


class InvestigationRunResult(BaseModel):
    """Complete, auditable result of an autonomous investigation run."""
    investigation_id: str
    initial_state: InvestigationState
    final_state: InvestigationState
    termination_reason: InvestigationTerminationReason
    total_steps: int
    iteration_traces: List[InvestigationIterationTrace]
    final_policy_actions: List[ActionRecommendation]
    execution_duration_sec: float
    executive_summary: str

    # Phase 4.4 Case Memory & GraphRAG Fields
    retrieved_precedents: List[SimilarCaseMatch] = Field(default_factory=list)
    retrieved_knowledge: List[RetrievedKnowledgeItem] = Field(default_factory=list)
    grounded_synthesis: Optional[str] = None


class InvestigationOrchestrator:
    """Tark Phase 4.3 Autonomous Investigation Loop / Agentic Orchestration.
    
    Coordinates the autonomous investigation lifecycle:
    OBSERVE -> CHECK TERMINATION -> CONSULT COMPASS -> SELECT TOP ADMISSIBLE ACTION ->
    EXECUTE VIA DISPATCHER -> UPDATE BELIEF -> RE-EVALUATE DECISION GATE -> STOP OR REPEAT.
    
    Authoritative Guarantees:
    1. Deterministic Authority: Tool selection is governed by Evidence Compass Net Decision Value.
    2. Zero LLM Hallucination of Evidence: The LLM has zero authority over probabilities, gates,
       evidence validity, or allowed actions.
    3. Frozen Boundary: Consumes Phase 4.2 Dispatcher and Tools strictly via public interfaces.
    4. Bounded Execution: Enforces configurable step budgets and safe failure limits.
    5. No Answer Engineering: Fully benchmark-agnostic.
    """

    def __init__(
        self,
        belief_engine: BeliefEngine,
        policy_engine: PolicyEngine,
        compass: EvidenceCompass,
        dispatcher: EvidenceToolDispatcher,
        llm_client: Optional[LLMClient] = None,
        case_memory: Optional[CaseMemoryStore] = None,
        graphrag: Optional[PolicyGraphRAGRetriever] = None,
        synthesizer: Optional[GroundedInvestigationSynthesizer] = None,
        max_steps: int = 5,
        consecutive_failure_limit: int = 2
    ):
        self.belief_engine = belief_engine
        self.policy_engine = policy_engine
        self.compass = compass
        self.dispatcher = dispatcher
        self.llm_client = llm_client
        self.case_memory = case_memory
        self.case_retriever = SimilarCaseRetriever(case_memory) if case_memory else None
        self.graphrag = graphrag
        self.synthesizer = synthesizer or (GroundedInvestigationSynthesizer(llm_client) if (case_memory or graphrag) else None)
        self.max_steps = max(1, max_steps)
        self.consecutive_failure_limit = max(1, consecutive_failure_limit)

    def run_investigation(
        self,
        initial_state: InvestigationState,
        exposure_usd: float = 100.0,
        context: Optional[Dict[str, Any]] = None,
        enable_llm_synthesis: bool = False
    ) -> InvestigationRunResult:
        """Executes the autonomous investigation loop until a deterministic terminal state is reached."""
        start_perf = time.perf_counter()
        current_state = initial_state
        traces: List[InvestigationIterationTrace] = []
        step_count = 0
        consecutive_failures = 0
        executed_action_ids: Set[str] = set()
        termination_reason: Optional[InvestigationTerminationReason] = None

        try:
            # 1. Pre-loop Termination Check on Initial State
            # Precedence 1: Human Approval Required
            if current_state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL:
                termination_reason = InvestigationTerminationReason.HUMAN_APPROVAL_REQUIRED

            # Precedence 2: Decision Already Reached on Initial State
            elif current_state.decision_gate_passed:
                init_rec = self.compass.evaluate_evidence_compass(current_state, exposure_usd=exposure_usd)
                init_positive = [
                    c for c in init_rec.ranked_candidates 
                    if c.net_decision_value > 0.0
                ]
                if init_rec.should_stop_gathering or not init_positive:
                    termination_reason = InvestigationTerminationReason.DECISION_REACHED

            # 2. Autonomous Investigation Loop
            while termination_reason is None:
                # Precedence 6: Step budget limit
                if step_count >= self.max_steps:
                    termination_reason = InvestigationTerminationReason.MAX_STEPS_REACHED
                    break

                # Precedence 5: Tool failure limit
                if consecutive_failures >= self.consecutive_failure_limit:
                    termination_reason = InvestigationTerminationReason.TOOL_FAILURE_LIMIT
                    break

                # Consult Evidence Compass for decision-relevant candidate actions
                compass_rec = self.compass.evaluate_evidence_compass(current_state, exposure_usd=exposure_usd)

                # Filter unexecuted candidates
                unexecuted_candidates = [
                    c for c in compass_rec.ranked_candidates
                    if c.action_id not in executed_action_ids
                ]

                # Precedence 3: No admissible evidence
                if not unexecuted_candidates:
                    if current_state.decision_gate_passed:
                        termination_reason = InvestigationTerminationReason.DECISION_REACHED
                    else:
                        termination_reason = InvestigationTerminationReason.NO_ADMISSIBLE_EVIDENCE
                    break

                # Check for positive Net Decision Value
                positive_candidates = [c for c in unexecuted_candidates if c.net_decision_value > 0.0]

                # Precedence 4: Negative EVOI (no positive decision value remains)
                if not positive_candidates:
                    if current_state.decision_gate_passed:
                        termination_reason = InvestigationTerminationReason.DECISION_REACHED
                    else:
                        termination_reason = InvestigationTerminationReason.NEGATIVE_EVOI
                    break

                # Deterministic action selection: Candidate with highest positive Net Decision Value
                chosen_candidate = positive_candidates[0]
                executed_action_ids.add(chosen_candidate.action_id)

                # Snapshot state before tool execution
                belief_before = current_state.belief_state.get("fraud_probability", 0.5)
                coverage_before = current_state.uncertainty.evidence_coverage
                uncertainty_before = current_state.uncertainty.epistemic_uncertainty
                decision_state_before = current_state.decision_state.value
                gate_passed_before = current_state.decision_gate_passed

                admissible_ids = [c.action_id for c in unexecuted_candidates]
                net_vals = {c.action_id: round(c.net_decision_value, 4) for c in unexecuted_candidates}

                # Execute action via frozen EvidenceToolDispatcher
                updated_state, tool_res, exec_trace = self.dispatcher.dispatch_and_update(
                    state=current_state,
                    candidate_action=chosen_candidate,
                    context=context
                )

                step_count += 1

                # Track consecutive actionable tool failures
                if tool_res.status in ["FAILED", "QUERY_FAILED", "REJECTED"]:
                    consecutive_failures += 1
                else:
                    consecutive_failures = 0

                # Snapshot state after tool execution
                belief_after = updated_state.belief_state.get("fraud_probability", 0.5)
                coverage_after = updated_state.uncertainty.evidence_coverage
                uncertainty_after = updated_state.uncertainty.epistemic_uncertainty
                decision_state_after = updated_state.decision_state.value
                gate_passed_after = updated_state.decision_gate_passed

                # Evaluate current policy action
                verdict_label = "fraud" if belief_after >= 0.70 else ("legitimate" if belief_after <= 0.30 else "uncertain")
                policy_acts = self.policy_engine.evaluate(
                    fraud_probability=belief_after,
                    verdict=verdict_label,
                    exposure_usd=exposure_usd,
                    ledger=EvidenceLedger(items=updated_state.evidence_items),
                    case_context=context or {}
                )
                primary_act = policy_acts[0].action if policy_acts else "MONITOR_CARD"

                # Check Post-Step Termination Precedence
                step_term_reason: Optional[InvestigationTerminationReason] = None

                # 1. Human Approval Required (Severe Contradiction / Aleatoric Conflict >= 0.40)
                if updated_state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL:
                    step_term_reason = InvestigationTerminationReason.HUMAN_APPROVAL_REQUIRED

                # 2. Decision Reached (Decision Gate Passed and further evidence has non-positive EVOI)
                elif updated_state.decision_gate_passed:
                    compass_recheck = self.compass.evaluate_evidence_compass(updated_state, exposure_usd=exposure_usd)
                    remaining_pos = [
                        c for c in compass_recheck.ranked_candidates
                        if c.action_id not in executed_action_ids and c.net_decision_value > 0.0
                    ]
                    if compass_recheck.should_stop_gathering or not remaining_pos:
                        step_term_reason = InvestigationTerminationReason.DECISION_REACHED

                # 5. Tool Failure Limit
                elif consecutive_failures >= self.consecutive_failure_limit:
                    step_term_reason = InvestigationTerminationReason.TOOL_FAILURE_LIMIT

                # 6. Step Budget Limit
                elif step_count >= self.max_steps:
                    step_term_reason = InvestigationTerminationReason.MAX_STEPS_REACHED

                # Build observed evidence summary string
                evidence_summary = None
                if tool_res.evidence_item:
                    ev = tool_res.evidence_item
                    evidence_summary = f"{ev.evidence_type.value} (LR={ev.lr}, log_lr={ev.log_lr}): {ev.finding}"
                elif tool_res.status:
                    evidence_summary = f"Tool status: {tool_res.status} ({tool_res.message})"

                # Record Iteration Trace
                trace = InvestigationIterationTrace(
                    investigation_id=current_state.investigation_id,
                    iteration=step_count,
                    belief_before=belief_before,
                    coverage_before=coverage_before,
                    uncertainty_before=uncertainty_before,
                    decision_state_before=decision_state_before,
                    gate_passed_before=gate_passed_before,
                    admissible_candidate_actions=admissible_ids,
                    candidate_net_decision_values=net_vals,
                    selected_action=chosen_candidate.action_id,
                    selection_rationale=getattr(chosen_candidate, "rationale", ""),
                    dispatcher_execution_trace=exec_trace,
                    observed_evidence_summary=evidence_summary,
                    belief_after=belief_after,
                    coverage_after=coverage_after,
                    uncertainty_after=uncertainty_after,
                    decision_state_after=decision_state_after,
                    gate_passed_after=gate_passed_after,
                    policy_action=primary_act,
                    termination_check="TERMINATE" if step_term_reason else "CONTINUE",
                    termination_reason=step_term_reason
                )
                traces.append(trace)

                current_state = updated_state

                if step_term_reason is not None:
                    termination_reason = step_term_reason
                    break

        except Exception as e:
            # Trap fatal errors without crashing; preserve auditable state
            termination_reason = InvestigationTerminationReason.ORCHESTRATION_ERROR

        # Ensure termination reason is always set
        if termination_reason is None:
            termination_reason = InvestigationTerminationReason.DECISION_REACHED if current_state.decision_gate_passed else InvestigationTerminationReason.NO_ADMISSIBLE_EVIDENCE

        # Final Policy Evaluation
        final_verdict = "fraud" if current_state.belief_state.get("fraud_probability", 0.5) >= 0.70 else (
            "legitimate" if current_state.belief_state.get("fraud_probability", 0.5) <= 0.30 else "uncertain"
        )
        case_ctx = dict(context or {})
        case_ctx.update(current_state.trigger)
        if ("pattern" not in case_ctx or not case_ctx["pattern"]) and current_state.secondary_typology:
            case_ctx["pattern"] = current_state.secondary_typology

        final_policy_actions = self.policy_engine.evaluate(
            fraud_probability=current_state.belief_state.get("fraud_probability", 0.5),
            verdict=final_verdict,
            exposure_usd=exposure_usd,
            ledger=EvidenceLedger(items=current_state.evidence_items),
            case_context=case_ctx
        )

        duration_sec = round(time.perf_counter() - start_perf, 4)

        # Phase 4.4: Contextual Case Memory & GraphRAG Synthesis
        retrieved_precedents: List[SimilarCaseMatch] = []
        retrieved_knowledge: List[RetrievedKnowledgeItem] = []
        grounded_synthesis: Optional[str] = None

        if self.case_retriever or self.graphrag or self.synthesizer:
            if self.case_retriever:
                retrieved_precedents = self.case_retriever.retrieve_similar_cases(
                    state=current_state,
                    target_entities=current_state.target_entities,
                    pattern=current_state.secondary_typology,
                    exposure_usd=exposure_usd,
                    top_k=3
                )

            if self.graphrag:
                retrieved_knowledge = self.graphrag.retrieve_grounded_context(
                    state=current_state,
                    exposure_usd=exposure_usd,
                    policy_actions=final_policy_actions,
                    context=context
                )

            if self.synthesizer:
                context_doc = InvestigationContextAssembler.assemble(
                    state=current_state,
                    similar_cases=retrieved_precedents,
                    retrieved_knowledge=retrieved_knowledge,
                    policy_actions=final_policy_actions,
                    exposure_usd=exposure_usd
                )
                grounded_synthesis = self.synthesizer.synthesize(
                    context=context_doc,
                    use_llm=enable_llm_synthesis
                )
                executive_summary = grounded_synthesis
            else:
                executive_summary = self._generate_executive_summary(
                    initial_state=initial_state,
                    final_state=current_state,
                    traces=traces,
                    termination_reason=termination_reason,
                    final_actions=final_policy_actions,
                    enable_llm_synthesis=enable_llm_synthesis
                )

            # Phase 4.4 Case Memory Write-Back
            if self.case_memory:
                self._write_back_case_memory(
                    final_state=current_state,
                    final_actions=final_policy_actions,
                    final_verdict=final_verdict,
                    exposure_usd=exposure_usd,
                    summary=executive_summary
                )
        else:
            executive_summary = self._generate_executive_summary(
                initial_state=initial_state,
                final_state=current_state,
                traces=traces,
                termination_reason=termination_reason,
                final_actions=final_policy_actions,
                enable_llm_synthesis=enable_llm_synthesis
            )

        duration_sec = round(time.perf_counter() - start_perf, 4)

        return InvestigationRunResult(
            investigation_id=current_state.investigation_id,
            initial_state=initial_state,
            final_state=current_state,
            termination_reason=termination_reason,
            total_steps=step_count,
            iteration_traces=traces,
            final_policy_actions=final_policy_actions,
            execution_duration_sec=duration_sec,
            executive_summary=executive_summary,
            retrieved_precedents=retrieved_precedents,
            retrieved_knowledge=retrieved_knowledge,
            grounded_synthesis=grounded_synthesis
        )

    def _write_back_case_memory(
        self,
        final_state: InvestigationState,
        final_actions: List[ActionRecommendation],
        final_verdict: str,
        exposure_usd: float,
        summary: str
    ):
        """Creates and stores a historical investigation memory record at case conclusion."""
        try:
            txn_ids = []
            for ev in final_state.evidence_items:
                if ev.details.get("txn_ids"):
                    txn_ids.extend([str(t) for t in ev.details["txn_ids"]])
                if ev.target_entity and ev.target_entity.isdigit():
                    txn_ids.append(ev.target_entity)
            if final_state.trigger.get("flagged_txn_id"):
                txn_ids.append(str(final_state.trigger["flagged_txn_id"]))
            txn_ids = sorted(list(set(txn_ids)))

            fam_names = sorted(list(set(item.evidence_type.value for item in final_state.evidence_items)))

            record = CaseMemoryRecord(
                case_id=final_state.investigation_id,
                customer_id=final_state.target_entities.get("customer_id"),
                card_id=final_state.target_entities.get("card_id"),
                opened_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                closed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                historical_outcome=final_verdict,
                pattern=final_state.secondary_typology or "unknown",
                first_fraud_txn_id=str(final_state.trigger.get("flagged_txn_id") or (txn_ids[0] if txn_ids else "")),
                txn_ids=txn_ids,
                n_txns=len(txn_ids) if txn_ids else 1,
                exposure_usd=exposure_usd,
                actions_taken=[a.action for a in final_actions],
                report_filed=any(a.action == "FILE_REPORT" for a in final_actions),
                analyst_notes=summary[:1000],
                evidence_families_observed=fam_names,
                approval_route=final_actions[0].approval_route if final_actions else "auto",
                provenance=MemoryProvenanceType.INVESTIGATION_WRITEBACK.value
            )
            self.case_memory.add_case(record)
        except Exception:
            pass

    def _generate_executive_summary(
        self,
        initial_state: InvestigationState,
        final_state: InvestigationState,
        traces: List[InvestigationIterationTrace],
        termination_reason: InvestigationTerminationReason,
        final_actions: List[ActionRecommendation],
        enable_llm_synthesis: bool = False
    ) -> str:
        """Constructs an auditable executive summary.
        
        Uses deterministic synthesis as authoritative baseline, with optional LLM narrative refinement.
        """
        init_prob = initial_state.belief_state.get("fraud_probability", 0.5)
        final_prob = final_state.belief_state.get("fraud_probability", 0.5)
        init_cov = initial_state.uncertainty.evidence_coverage
        final_cov = final_state.uncertainty.evidence_coverage
        action_names = [a.action for a in final_actions] if final_actions else ["MONITOR_CARD"]

        lines = [
            f"### AUTONOMOUS INVESTIGATION SUMMARY: {final_state.investigation_id}",
            f"- **Termination Status:** {termination_reason.value}",
            f"- **Investigation Steps Executed:** {len(traces)}",
            f"- **Belief Trajectory:** P(Fraud) {init_prob:.4f} -> {final_prob:.4f}",
            f"- **Evidence Coverage:** {init_cov * 100:.0f}% -> {final_cov * 100:.0f}% of core dimensions observed",
            f"- **Decision Gate Status:** {'PASSED' if final_state.decision_gate_passed else 'LOCKED'} ({final_state.decision_state.value})",
            f"- **Authoritative Policy Disposition:** {', '.join(action_names)}",
            "",
            "#### Step-by-Step Trajectory:"
        ]

        if not traces:
            lines.append("No active tool execution required; initial evidence satisfied terminal condition.")
        else:
            for t in traces:
                lines.append(
                    f"Step {t.iteration}: Dispatched `{t.selected_action}` based on Evidence Compass EVOI. "
                    f"Result: {t.observed_evidence_summary or 'No finding'}. "
                    f"Belief shifted to P(Fraud)={t.belief_after:.4f} (coverage: {t.coverage_after * 100:.0f}%). "
                    f"Status: {t.termination_check} ({t.termination_reason.value if t.termination_reason else 'CONTINUE'})."
                )

        lines.append("")
        lines.append(f"**Stopping Rationale:** Investigation terminated under `{termination_reason.value}`.")

        deterministic_summary = "\n".join(lines)

        # Optional LLM Synthesis (if requested and client available)
        if enable_llm_synthesis and self.llm_client:
            try:
                prompt = (
                    f"Synthesize the following completed fraud investigation into an executive 2-paragraph narrative.\n"
                    f"Do NOT invent transaction numbers or change any probability or gate status.\n\n"
                    f"{deterministic_summary}"
                )
                llm_narrative = self.llm_client.generate(
                    system_prompt="You are a compliance officer summarizing a completed deterministic fraud investigation.",
                    user_prompt=prompt,
                    max_tokens=300
                )
                if llm_narrative and len(llm_narrative.strip()) > 0:
                    return f"{llm_narrative.strip()}\n\n---\n{deterministic_summary}"
            except Exception:
                pass

        return deterministic_summary
