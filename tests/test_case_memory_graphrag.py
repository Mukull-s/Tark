import os
import pytest
from typing import Dict, Any, List

from src.evidence.types import EvidenceItem, EvidenceType, EvidenceDirection
from src.evidence.ledger import EvidenceLedger
from src.belief.engine import BeliefEngine, MIN_DECISION_COVERAGE
from src.belief.state import InvestigationState, DecisionState
from src.policy.engine import PolicyEngine
from src.compass.evoi import EvidenceCompass
from src.tools.dispatcher import EvidenceToolDispatcher
from src.tools.base import EvidenceTool, ToolExecutionResult
from src.agent.orchestrator import InvestigationOrchestrator, InvestigationTerminationReason

from src.memory.models import CaseMemoryRecord, SimilarCaseMatch, MemoryProvenanceType
from src.memory.store import CaseMemoryStore
from src.memory.retriever import SimilarCaseRetriever
from src.knowledge.models import KnowledgeChunk, KnowledgeCategory, RetrievedKnowledgeItem
from src.knowledge.store import InvestigationKnowledgeBase
from src.knowledge.retriever import PolicyGraphRAGRetriever
from src.synthesis.context import InvestigationContext, InvestigationContextAssembler
from src.synthesis.synthesizer import GroundedInvestigationSynthesizer


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
def case_memory(tmp_path):
    wb_file = str(tmp_path / "memory_writebacks.jsonl")
    return CaseMemoryStore(writeback_path=wb_file)


@pytest.fixture
def case_retriever(case_memory):
    return SimilarCaseRetriever(case_memory)


@pytest.fixture
def knowledge_base():
    return InvestigationKnowledgeBase()


@pytest.fixture
def graphrag_retriever(knowledge_base):
    return PolicyGraphRAGRetriever(knowledge_base)


@pytest.fixture
def synthesizer():
    return GroundedInvestigationSynthesizer(llm_client=None)


# ==============================================================================
# 1. Historical Case Retrieval
# ==============================================================================

def test_historical_case_retrieval(case_retriever):
    """Verifies that historical cases can be retrieved matching target card and pattern."""
    target_entities = {"card_id": "C00259-K1", "customer_id": "C00259"}
    matches = case_retriever.retrieve_similar_cases(
        target_entities=target_entities,
        pattern="card_not_present_fraud",
        exposure_usd=150.0,
        top_k=3
    )
    assert len(matches) > 0
    top_match = matches[0]
    assert isinstance(top_match, SimilarCaseMatch)
    assert top_match.case_record.case_id == "CC-0001"
    assert top_match.similarity_score > 0.50
    assert "Identical card ID" in top_match.shared_features[0]


# ==============================================================================
# 2. Similar-Case Provenance
# ==============================================================================

def test_similar_case_provenance(case_retriever):
    """Verifies that retrieved similar cases carry explicit historical data provenance."""
    matches = case_retriever.retrieve_similar_cases(
        target_entities={"card_id": "C06403-K2"},
        pattern="out_of_region_use",
        top_k=1
    )
    assert len(matches) == 1
    match = matches[0]
    assert match.case_record.provenance == MemoryProvenanceType.HISTORICAL_CSV.value
    assert len(match.case_record.analyst_notes) > 0
    assert "Case CC-0002" in match.case_record.analyst_notes
    assert match.role == "CONTEXTUAL_PRECEDENT_ONLY"


# ==============================================================================
# 3. Similar-Case Does Not Alter Fraud Probability
# ==============================================================================

def test_similar_case_does_not_alter_fraud_probability(belief_engine, case_retriever):
    """CRITICAL: Verifies that retrieving similar cases cannot alter belief state probability."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model",
        finding="Risk score 0.50",
        lr=2.4,
        log_lr=0.875
    ))
    state = belief_engine.evaluate_investigation(
        "INV-SIM-PROB", {}, {"card_id": "C00259-K1"}, ledger
    )
    p_before = state.belief_state["fraud_probability"]

    # Retrieve similar cases
    matches = case_retriever.retrieve_similar_cases(state=state, top_k=5)
    assert len(matches) > 0

    # Ensure belief remains mathematically identical
    state_after = belief_engine.evaluate_investigation(
        "INV-SIM-PROB", {}, {"card_id": "C00259-K1"}, ledger
    )
    assert state_after.belief_state["fraud_probability"] == pytest.approx(p_before, abs=1e-6)


# ==============================================================================
# 4. Similar-Case Does Not Increase Evidence Coverage
# ==============================================================================

def test_similar_case_does_not_increase_evidence_coverage(belief_engine, case_retriever):
    """CRITICAL: Verifies that similar cases do not count toward core investigative coverage."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model",
        finding="Risk score 0.50",
        lr=2.4,
        log_lr=0.875
    ))
    state = belief_engine.evaluate_investigation(
        "INV-SIM-COV", {}, {"card_id": "C00259-K1"}, ledger
    )
    assert state.uncertainty.evidence_coverage == 0.20  # 1/5 core families

    matches = case_retriever.retrieve_similar_cases(state=state, top_k=5)
    assert len(matches) > 0

    # Re-evaluate: coverage must remain strictly 0.20
    state_rechecked = belief_engine.evaluate_investigation(
        "INV-SIM-COV", {}, {"card_id": "C00259-K1"}, ledger
    )
    assert state_rechecked.uncertainty.evidence_coverage == 0.20
    assert state_rechecked.decision_gate_passed is False


# ==============================================================================
# 5. Historical Outcome Cannot Become an EvidenceItem
# ==============================================================================

def test_historical_outcome_cannot_become_evidence_item(case_retriever):
    """Verifies that case similarity results are not EvidenceItems and have no likelihood ratios."""
    matches = case_retriever.retrieve_similar_cases(
        target_entities={"card_id": "C00259-K1"},
        pattern="card_not_present_fraud"
    )
    match = matches[0]
    assert not isinstance(match, EvidenceItem)
    assert not hasattr(match, "lr")
    assert not hasattr(match, "log_lr")
    assert not hasattr(match, "direction")
    assert match.role == "CONTEXTUAL_PRECEDENT_ONLY"


# ==============================================================================
# 6. Policy Retrieval Provenance
# ==============================================================================

def test_policy_retrieval_provenance(belief_engine, graphrag_retriever):
    """Verifies that GraphRAG retrieves authoritative policy rules with full statutory lineage."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="card_sequence",
        finding="Card testing sequence observed",
        lr=34.3,
        log_lr=3.535
    ))
    state = belief_engine.evaluate_investigation(
        "INV-POL-PROV", {}, {"card_id": "C1"}, ledger
    )
    items = graphrag_retriever.retrieve_grounded_context(state=state, exposure_usd=250.0)
    assert len(items) > 0
    rule5_items = [k for k in items if k.chunk.chunk_id == "KNOW-POLICY-R5"]
    assert len(rule5_items) == 1
    r5 = rule5_items[0]
    assert r5.chunk.section_reference == "Policy Manual § 4.5 (Rule R5)"
    assert r5.chunk.governing_body == "Bank Risk Governance"
    assert "DECLINE_TRANSACTION" in r5.chunk.text


# ==============================================================================
# 7. Policy Text Cannot Alter Fraud Probability
# ==============================================================================

def test_policy_text_cannot_alter_fraud_probability(belief_engine, graphrag_retriever):
    """CRITICAL: Verifies that retrieved policy passages do not mutate belief probabilities."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="m",
        finding="m",
        lr=2.4,
        log_lr=0.875
    ))
    state = belief_engine.evaluate_investigation(
        "INV-POL-PROB", {}, {"card_id": "C1"}, ledger
    )
    p_before = state.belief_state["fraud_probability"]

    # Retrieve policy knowledge
    items = graphrag_retriever.retrieve_grounded_context(state=state, exposure_usd=1500.0)
    assert len(items) > 0

    # Ensure state remains unchanged
    assert state.belief_state["fraud_probability"] == pytest.approx(p_before, abs=1e-6)


# ==============================================================================
# 8. Policy Text Cannot Bypass Decision Gate
# ==============================================================================

def test_policy_text_cannot_bypass_decision_gate(belief_engine, graphrag_retriever):
    """Verifies that high-relevance policy text cannot unlock a locked Decision Gate."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="m",
        finding="m",
        lr=100.0,
        log_lr=4.605
    ))
    # Coverage is only 0.20 < 0.40 -> Decision Gate MUST be locked
    state = belief_engine.evaluate_investigation(
        "INV-GATE-LOCK", {}, {"card_id": "C1"}, ledger
    )
    assert state.decision_gate_passed is False
    assert state.decision_state == DecisionState.INSUFFICIENT_EVIDENCE

    # Retrieve policy text
    items = graphrag_retriever.retrieve_grounded_context(state=state, exposure_usd=5000.0)
    assert len(items) > 0

    # State decision gate must remain locked
    assert state.decision_gate_passed is False
    assert state.decision_state == DecisionState.INSUFFICIENT_EVIDENCE


# ==============================================================================
# 9. LLM Cannot Mutate Belief
# ==============================================================================

def test_llm_cannot_mutate_belief(belief_engine, synthesizer):
    """Verifies that LLM narrative generation cannot mutate numeric fraud probability."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="m",
        finding="m",
        lr=2.4,
        log_lr=0.875
    ))
    state = belief_engine.evaluate_investigation(
        "INV-LLM-BELIEF", {}, {"card_id": "C1"}, ledger
    )
    p_original = state.belief_state["fraud_probability"]

    context = InvestigationContextAssembler.assemble(state=state, exposure_usd=200.0)
    synthesis = synthesizer.synthesize(context=context, use_llm=False)
    assert len(synthesis) > 0

    # Numeric belief in state must remain strictly equal
    assert state.belief_state["fraud_probability"] == pytest.approx(p_original, abs=1e-6)


# ==============================================================================
# 10. LLM Cannot Mutate Coverage
# ==============================================================================

def test_llm_cannot_mutate_coverage(belief_engine, synthesizer):
    """Verifies that LLM text generation cannot fabricate or inflate evidence coverage."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="m",
        finding="m",
        lr=2.4,
        log_lr=0.875
    ))
    state = belief_engine.evaluate_investigation(
        "INV-LLM-COV", {}, {"card_id": "C1"}, ledger
    )
    cov_original = state.uncertainty.evidence_coverage
    assert cov_original == 0.20

    context = InvestigationContextAssembler.assemble(state=state, exposure_usd=200.0)
    synthesis = synthesizer.synthesize(context=context, use_llm=False)
    assert len(synthesis) > 0

    assert state.uncertainty.evidence_coverage == 0.20


# ==============================================================================
# 11. LLM Cannot Select Arbitrary Tools
# ==============================================================================

def test_llm_cannot_select_arbitrary_tools(belief_engine, policy_engine, compass, dispatcher):
    """Verifies that tool selection authority remains solely with Evidence Compass EVOI."""
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=1
    )
    # Orchestrator does not query LLM for tool selection
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="m",
        finding="Initial risk score",
        lr=2.4,
        log_lr=0.875
    ))
    state = belief_engine.evaluate_investigation(
        "INV-TOOL-SEL", {}, {"card_id": "C1", "flagged_txn_id": "T1"}, ledger
    )
    rec = compass.evaluate_evidence_compass(state, exposure_usd=1000.0)
    top_cand = rec.top_recommendation
    assert top_cand is not None

    # LLM cannot override top_cand
    res = orchestrator.run_investigation(state)
    assert len(res.iteration_traces) == 1
    assert res.iteration_traces[0].selected_action == top_cand.action_id


# ==============================================================================
# 12. LLM Cannot Execute Tools
# ==============================================================================

def test_llm_cannot_execute_tools(dispatcher):
    """Verifies that only registered EvidenceTools in Dispatcher can be executed."""
    # Attempting to execute an arbitrary LLM tool name is rejected
    state = InvestigationState(
        investigation_id="INV-NO-EXEC",
        trigger={},
        target_entities={},
        ledger=EvidenceLedger()
    )
    updated_state, res, trace = dispatcher.dispatch_and_update(
        state=state,
        candidate_action="LLM_ARBITRARY_PYTHON_EXEC"
    )
    assert res.status == "REJECTED"
    assert "not a registered approved evidence tool" in res.message


# ==============================================================================
# 13. LLM Cannot Directly Mutate InvestigationState
# ==============================================================================

def test_llm_cannot_directly_mutate_investigation_state(belief_engine, synthesizer):
    """Verifies that InvestigationState object is immutable from synthesizer calls."""
    ledger = EvidenceLedger()
    state = belief_engine.evaluate_investigation("INV-IMMUT", {}, {"card_id": "C1"}, ledger)
    context = InvestigationContextAssembler.assemble(state=state, exposure_usd=100.0)
    
    # Synthesizer receives context, not a mutable handle to hijack state
    synthesizer.synthesize(context=context, use_llm=False)
    assert state.investigation_id == "INV-IMMUT"
    assert state.decision_gate_passed is False
    assert len(state.evidence_items) == 0


# ==============================================================================
# 14. Observed Evidence Remains Distinguishable from Memory
# ==============================================================================

def test_observed_evidence_remains_distinguishable_from_memory(belief_engine, case_retriever):
    """Verifies strict separation between empirical evidence items and case memory records."""
    ev = EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        value={"device_id": "DEV_123"},
        source="device_analysis",
        finding="Device shared across 10 cards",
        lr=14.2,
        log_lr=2.653
    )
    ledger = EvidenceLedger(items=[ev])
    state = belief_engine.evaluate_investigation("INV-SEP-A", {}, {"card_id": "C00259-K1"}, ledger)
    
    matches = case_retriever.retrieve_similar_cases(state=state, top_k=2)
    context = InvestigationContextAssembler.assemble(
        state=state, similar_cases=matches, exposure_usd=500.0
    )
    doc = context.render_context_document()

    # Section A contains observed evidence, Section B contains memory
    assert "SECTION A: OBSERVED GRAPH & TOOL EVIDENCE" in doc
    assert "SECTION B: HISTORICAL CASE PRECEDENT" in doc
    assert f"[{ev.evidence_id}]" in doc
    assert "[CC-0001]" in doc or "[CC-" in doc


# ==============================================================================
# 15. Observed Evidence Remains Distinguishable from Policy Context
# ==============================================================================

def test_observed_evidence_remains_distinguishable_from_policy_context(belief_engine, graphrag_retriever):
    """Verifies strict separation between empirical graph evidence and governing policy rules."""
    ev = EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="card_sequence",
        finding="Card testing sequence",
        lr=34.3,
        log_lr=3.535
    )
    state = belief_engine.evaluate_investigation("INV-SEP-B", {}, {"card_id": "C1"}, EvidenceLedger(items=[ev]))
    items = graphrag_retriever.retrieve_grounded_context(state=state, exposure_usd=300.0)
    context = InvestigationContextAssembler.assemble(
        state=state, retrieved_knowledge=items, exposure_usd=300.0
    )
    doc = context.render_context_document()

    assert "SECTION A: OBSERVED GRAPH & TOOL EVIDENCE" in doc
    assert "SECTION C: GOVERNING POLICY & REGULATORY KNOWLEDGE" in doc
    assert f"[{ev.evidence_id}]" in doc
    assert "[KNOW-POLICY-R5]" in doc


# ==============================================================================
# 16. Unsupported LLM Claims are Rejected or Excluded
# ==============================================================================

def test_unsupported_llm_claims_are_rejected_or_excluded(belief_engine, synthesizer):
    """Verifies citation verification audit catches hallucinated/unsupported evidence IDs."""
    state = belief_engine.evaluate_investigation("INV-HALLUC", {}, {"card_id": "C1"}, EvidenceLedger())
    context = InvestigationContextAssembler.assemble(state=state, exposure_usd=100.0)

    # Simulate an LLM text with fabricated citations
    fake_llm_text = (
        "Based on evidence [EVD-FFFFFFFF] the transaction is definitely fraudulent. "
        "Also precedent [CC-9999] was identical."
    )
    audited_text = synthesizer._validate_and_sanitize_citations(fake_llm_text, context)

    assert "Unsupported Evidence Citations Excluded:** EVD-FFFFFFFF" in audited_text
    assert "Unsupported Case Citations Excluded:** CC-9999" in audited_text


# ==============================================================================
# 17. LLM Failure Falls Back to Deterministic Summary
# ==============================================================================

def test_llm_failure_falls_back_to_deterministic_summary(belief_engine, synthesizer):
    """Verifies that when LLM fails or is disabled, a complete 7-section deterministic report is generated."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model",
        finding="Risk score 0.85",
        lr=2.4,
        log_lr=0.875
    ))
    state = belief_engine.evaluate_investigation("INV-FALLBACK", {}, {"card_id": "C1"}, ledger)
    context = InvestigationContextAssembler.assemble(state=state, exposure_usd=1000.0)

    # use_llm=True with llm_client=None triggers fallback
    narrative = synthesizer.synthesize(context=context, use_llm=True)
    assert "### 1. Executive Summary" in narrative
    assert "### 2. Graph Evidence Analysis" in narrative
    assert "### 3. Historical Precedent Analysis" in narrative
    assert "### 4. Policy & Regulatory Compliance" in narrative
    assert "### 5. Uncertainty & Conflict Assessment" in narrative
    assert "### 6. Investigation Trajectory & EVOI Rationale" in narrative
    assert "### 7. Final Operational Disposition & Remediation" in narrative


# ==============================================================================
# 18. Case Memory Write-Back Preserves Provenance
# ==============================================================================

def test_case_memory_write_back_preserves_provenance(belief_engine, policy_engine, compass, dispatcher, case_memory):
    """Verifies that completing an investigation persists an auditable record to memory."""
    initial_count = case_memory.count()
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        case_memory=case_memory,
        max_steps=1
    )
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="m",
        finding="Initial risk score",
        lr=2.4,
        log_lr=0.875
    ))
    import uuid
    test_id = f"INV-WB-{uuid.uuid4().hex[:8].upper()}"
    state = belief_engine.evaluate_investigation(
        test_id,
        {"flagged_txn_id": "TXN_7777"},
        {"card_id": "CARD_WRITEBACK", "customer_id": "CUST_WRITEBACK"},
        ledger
    )
    res = orchestrator.run_investigation(state, exposure_usd=750.0)

    # Verify write-back occurred
    assert case_memory.count() == initial_count + 1
    saved = case_memory.get_case(test_id)
    assert saved is not None
    assert saved.case_id == test_id
    assert saved.card_id == "CARD_WRITEBACK"
    assert saved.customer_id == "CUST_WRITEBACK"
    assert saved.exposure_usd == 750.0
    assert saved.provenance == MemoryProvenanceType.INVESTIGATION_WRITEBACK.value
    assert len(saved.evidence_families_observed) > 0


# ==============================================================================
# 19. Benchmark Case Cannot Act as Hidden Ground Truth Oracle
# ==============================================================================

def test_benchmark_case_cannot_act_as_hidden_oracle(case_memory):
    """Verifies that benchmark case IDs (HHG-001) do not exist as labeled answers in memory."""
    assert case_memory.get_case("HHG-001") is None
    assert case_memory.get_case("HHG-014") is None
    assert case_memory.get_case("HHG-020") is None


# ==============================================================================
# 20. Generic Non-Benchmark Investigation Can Retrieve Historical Context
# ==============================================================================

def test_generic_non_benchmark_investigation_retrieves_context(case_retriever):
    """Verifies that generic, randomized investigations seamlessly retrieve historical precedents."""
    matches = case_retriever.retrieve_similar_cases(
        target_entities={"card_id": "CARD_RANDOM_9999", "customer_id": "CUST_RANDOM_9999"},
        pattern="card_not_present_fraud",
        exposure_usd=125.0,
        top_k=3
    )
    assert len(matches) > 0
    assert matches[0].similarity_score > 0.0
    assert matches[0].role == "CONTEXTUAL_PRECEDENT_ONLY"


# ==============================================================================
# 21. Retrieved Case Similarity is Contextual Only
# ==============================================================================

def test_retrieved_case_similarity_is_contextual_only(case_retriever):
    """Verifies that SimilarCaseMatch explicitly flags its role as non-evidential contextual precedent."""
    matches = case_retriever.retrieve_similar_cases(
        pattern="account_takeover",
        exposure_usd=500.0,
        top_k=1
    )
    match = matches[0]
    assert match.role == "CONTEXTUAL_PRECEDENT_ONLY"
    assert "LR=1.0, non-evidential" in match.explanation


# ==============================================================================
# 22. GraphRAG Retrieval Returns Grounded Source References
# ==============================================================================

def test_graphrag_retrieval_returns_grounded_source_references(belief_engine, graphrag_retriever):
    """Verifies that GraphRAG returns chunks with formal governing body and section citations."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        value="ring_detected",
        source="device_analysis",
        finding="Shared device ring linking cards",
        lr=14.2,
        log_lr=2.653
    ))
    state = belief_engine.evaluate_investigation("INV-GRAPHRAG-REFS", {}, {"card_id": "C1"}, ledger)
    items = graphrag_retriever.retrieve_grounded_context(state=state, exposure_usd=2500.0)

    fincen_items = [k for k in items if k.chunk.chunk_id == "KNOW-REG-FINCEN-SAR"]
    assert len(fincen_items) == 1
    sar_item = fincen_items[0]
    assert "31 CFR § 1020.320" in sar_item.chunk.section_reference
    assert "FinCEN" in sar_item.chunk.governing_body


# ==============================================================================
# 23. End-to-End Investigation with Memory + GraphRAG
# ==============================================================================

def test_end_to_end_investigation_with_memory_and_graphrag(
    belief_engine, policy_engine, compass, dispatcher, case_memory, graphrag_retriever
):
    """Verifies full autonomous investigation execution with contextual memory, GraphRAG, and writeback."""
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        case_memory=case_memory,
        graphrag=graphrag_retriever,
        max_steps=2
    )

    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="model",
        finding="Initial trigger risk score 0.50",
        lr=2.4,
        log_lr=0.875
    ))
    state = belief_engine.evaluate_investigation(
        "INV-E2E-PHASE4-4",
        {"flagged_txn_id": "3478561"},
        {"card_id": "C11923-K2", "customer_id": "C00259"},
        ledger
    )

    result = orchestrator.run_investigation(state, exposure_usd=1200.0)

    # 1. Deterministic Loop Executed
    assert result.total_steps > 0
    assert result.final_state.decision_gate_passed is True

    # 2. Case Memory Precedents Retrieved
    assert len(result.retrieved_precedents) > 0
    assert result.retrieved_precedents[0].role == "CONTEXTUAL_PRECEDENT_ONLY"

    # 3. Policy & Regulatory Knowledge Retrieved
    assert len(result.retrieved_knowledge) > 0
    know_ids = [k.chunk.chunk_id for k in result.retrieved_knowledge]
    assert any("KNOW-POLICY" in kid for kid in know_ids)

    # 4. Grounded Synthesis Generated
    assert result.grounded_synthesis is not None
    assert "### 1. Executive Summary" in result.grounded_synthesis
    assert "### 4. Policy & Regulatory Compliance" in result.grounded_synthesis

    # 5. Memory Write-Back Occurred
    saved = case_memory.get_case("INV-E2E-PHASE4-4")
    assert saved is not None
    assert saved.case_id == "INV-E2E-PHASE4-4"


# ==============================================================================
# 24. Existing Phase 4.3 Tests Remain Green
# ==============================================================================

def test_existing_orchestrator_without_graphrag_remains_intact(
    belief_engine, policy_engine, compass, dispatcher
):
    """Verifies that standard Phase 4.3 orchestrator without memory parameters remains 100% functional."""
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        max_steps=1
    )
    state = belief_engine.evaluate_investigation("INV-P43-COMPAT", {}, {"card_id": "C1"}, EvidenceLedger())
    res = orchestrator.run_investigation(state)
    assert res.investigation_id == "INV-P43-COMPAT"
    assert res.retrieved_precedents == []
    assert res.retrieved_knowledge == []
    assert res.grounded_synthesis is None
    assert len(res.executive_summary) > 0


# ==============================================================================
# 25. Audit: Evidence-to-Policy Consistency (R4, R9 & Bidirectional Action Mapping)
# ==============================================================================

def test_audit_evidence_to_policy_consistency_r4_and_r9(belief_engine, policy_engine, graphrag_retriever):
    """Verifies that OUT_OF_REGION evidence and undocumented patterns consistently retrieve R4 and R9 rules."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.OUT_OF_REGION,
        source="geo_profile",
        finding="Card-present activity in unknown billing region without travel notice",
        lr=6.8,
        log_lr=1.917
    ))
    state = belief_engine.evaluate_investigation("INV-AUDIT-R4", {}, {"card_id": "C1"}, ledger)
    
    # Retrieve grounded context
    items = graphrag_retriever.retrieve_grounded_context(state=state, exposure_usd=400.0)
    chunk_ids = {k.chunk.chunk_id for k in items}
    assert "KNOW-TYPO-OUT-OF-REGION" in chunk_ids
    assert "KNOW-POLICY-R4" in chunk_ids

    # Test Rule R9 with undocumented pattern
    ledger9 = EvidenceLedger()
    ledger9.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="m",
        finding="High risk score",
        lr=50.0,
        log_lr=3.912
    ))
    state9 = belief_engine.evaluate_investigation("INV-AUDIT-R9", {}, {"card_id": "C2"}, ledger9)
    items9 = graphrag_retriever.retrieve_grounded_context(
        state=state9,
        exposure_usd=1500.0,
        context={"pattern": "undocumented"}
    )
    chunk_ids9 = {k.chunk.chunk_id for k in items9}
    assert "KNOW-POLICY-R9" in chunk_ids9


# ==============================================================================
# 26. Audit: Case-Memory Contamination Prevention (Active Txn & ID Exclusion)
# ==============================================================================

def test_audit_case_memory_contamination_active_txn_and_id_exclusion(case_retriever, case_memory):
    """Verifies that active transaction IDs and active investigation IDs can NEVER be retrieved as precedents."""
    # Seed a case with a specific transaction ID
    record = CaseMemoryRecord(
        case_id="CC-LEAK-TEST",
        card_id="C00259-K1",
        customer_id="C00259",
        historical_outcome="confirmed_fraud",
        pattern="card_not_present_fraud",
        first_fraud_txn_id="TXN_ACTIVE_9999",
        txn_ids=["TXN_ACTIVE_9999"],
        n_txns=1,
        exposure_usd=250.0,
        provenance=MemoryProvenanceType.HISTORICAL_CSV.value
    )
    case_memory.add_case(record, persist=False)

    # Attempt to retrieve similar cases for an investigation targeting TXN_ACTIVE_9999
    matches = case_retriever.retrieve_similar_cases(
        target_entities={"card_id": "C00259-K1", "customer_id": "C00259", "flagged_txn_id": "TXN_ACTIVE_9999"},
        pattern="card_not_present_fraud",
        top_k=5
    )
    matched_ids = [m.case_record.case_id for m in matches]
    # CC-LEAK-TEST must be excluded because it references the active transaction being evaluated
    assert "CC-LEAK-TEST" not in matched_ids

    # Attempt to retrieve similar cases with the same case ID
    matches_self = case_retriever.retrieve_similar_cases(
        target_entities={"case_id": "CC-0001", "card_id": "C00259-K1"},
        top_k=5
    )
    matched_self_ids = [m.case_record.case_id for m in matches_self]
    assert "CC-0001" not in matched_self_ids


# ==============================================================================
# 27. Audit: GraphRAG Authenticity (Multi-Hop Lineage)
# ==============================================================================

def test_audit_graphrag_authenticity_multihop_chain(belief_engine, graphrag_retriever):
    """Verifies full GraphRAG multi-hop chain: Graph Observation -> Typology -> Policy Rule -> Regulation."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.HIGH_VELOCITY,
        source="txn_velocity",
        finding="High velocity micro-authorizations",
        lr=8.5,
        log_lr=2.14
    ))
    state = belief_engine.evaluate_investigation("INV-AUDIT-GRAPHRAG", {}, {"card_id": "C1"}, ledger)
    items = graphrag_retriever.retrieve_grounded_context(state=state, exposure_usd=2000.0)

    # 1. Typology Hop
    cardtesting_typo = [k for k in items if k.chunk.chunk_id == "KNOW-TYPO-CARDTESTING"]
    assert len(cardtesting_typo) == 1
    assert "HIGH_VELOCITY" in cardtesting_typo[0].match_rationale

    # 2. Policy Rule Hop
    r10_policy = [k for k in items if k.chunk.chunk_id == "KNOW-POLICY-R10"]
    assert len(r10_policy) == 1

    # 3. Regulatory Statute Hop (exposure >= $1000)
    sar_reg = [k for k in items if k.chunk.chunk_id == "KNOW-REG-FINCEN-SAR"]
    assert len(sar_reg) == 1
    assert "31 CFR § 1020.320" in sar_reg[0].chunk.section_reference


# ==============================================================================
# 28. Audit: Provenance Integrity (Three-Way Citation Verification Audit)
# ==============================================================================

def test_audit_provenance_integrity_three_way_citation_verification(belief_engine, synthesizer, graphrag_retriever):
    """Verifies that evidence, case, and policy citations are all audited for fabrications."""
    ev = EvidenceItem(
        evidence_id="EVD-REAL0001",
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="m",
        finding="Real empirical evidence",
        lr=2.4,
        log_lr=0.875
    )
    state = belief_engine.evaluate_investigation("INV-AUDIT-PROV", {}, {"card_id": "C1"}, EvidenceLedger(items=[ev]))
    items = graphrag_retriever.retrieve_grounded_context(state=state, exposure_usd=500.0)
    context = InvestigationContextAssembler.assemble(
        state=state,
        retrieved_knowledge=items,
        exposure_usd=500.0
    )

    # Text containing 1 valid evidence, 1 fake evidence, 1 fake case, 1 fake knowledge chunk
    simulated_text = (
        "Investigation [INV-AUDIT-PROV] observed valid evidence [EVD-REAL0001], "
        "but also hallucinates fake evidence [EVD-FABRICATED], "
        "fake case precedent [CC-8888], fake writeback [INV-FAKE-01], "
        "and fake regulation [KNOW-REG-FAKE-STATUTE]."
    )
    audited = synthesizer._validate_and_sanitize_citations(simulated_text, context)

    assert "Observed Evidence Citations Verified:" in audited
    assert "Historical Case Citations Verified:" in audited
    assert "Policy/Statute Citations Verified:" in audited
    assert "EVD-FABRICATED" in audited
    assert "CC-8888" in audited
    assert "INV-FAKE-01" in audited
    assert "KNOW-REG-FAKE-STATUTE" in audited


# ==============================================================================
# 29. Audit: Regulatory-Source Correctness
# ==============================================================================

def test_audit_regulatory_source_correctness(knowledge_base):
    """Verifies that FinCEN SAR and Regulation E citations possess statutory precision and correct authority."""
    sar_chunk = knowledge_base.get_chunk("KNOW-REG-FINCEN-SAR")
    assert sar_chunk is not None
    assert sar_chunk.governing_body == "Financial Crimes Enforcement Network (FinCEN)"
    assert sar_chunk.section_reference == "31 CFR § 1020.320"
    assert "31 CFR § 1020.320(a)(2)" in sar_chunk.text
    assert "$5,000" in sar_chunk.text
    assert "$25,000" in sar_chunk.text

    rege_chunk = knowledge_base.get_chunk("KNOW-REG-REGE")
    assert rege_chunk is not None
    assert rege_chunk.governing_body == "Consumer Financial Protection Bureau (CFPB)"
    assert "1005.6" in rege_chunk.section_reference
    assert "1005.11" in rege_chunk.section_reference
    assert "10 business days" in rege_chunk.text
    assert "45 calendar days" in rege_chunk.text

