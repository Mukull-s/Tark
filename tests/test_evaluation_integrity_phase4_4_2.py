import pytest
from typing import Dict, Any, List

from src.evidence.types import EvidenceItem, EvidenceType, EvidenceDirection
from src.evidence.ledger import EvidenceLedger
from src.belief.engine import BeliefEngine
from src.belief.state import InvestigationState, DecisionState
from src.policy.engine import PolicyEngine
from src.compass.evoi import EvidenceCompass
from src.tools.dispatcher import EvidenceToolDispatcher
from src.agent.orchestrator import InvestigationOrchestrator

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
def knowledge_base():
    return InvestigationKnowledgeBase()


@pytest.fixture
def graphrag_retriever(knowledge_base):
    return PolicyGraphRAGRetriever(knowledge_base)


@pytest.fixture
def synthesizer():
    return GroundedInvestigationSynthesizer(llm_client=None)


# ==============================================================================
# 1. Benchmark Memory Snapshot Isolation & Temporal Cutoff
# ==============================================================================

def test_pre_cutoff_historical_case_allowed(tmp_path):
    """Verifies that a case closed before the evaluation cutoff timestamp is eligible."""
    store = CaseMemoryStore(writeback_path=str(tmp_path / "wb.jsonl"))
    rec_pre = CaseMemoryRecord(
        case_id="CC-HIST-PRE",
        card_id="C9999-K1",
        customer_id="C9999",
        closed_at="2016-07-01 12:00:00",
        historical_outcome="confirmed_fraud",
        pattern="out_of_region_use",
        exposure_usd=200.0,
        provenance=MemoryProvenanceType.HISTORICAL_CSV.value
    )
    store.add_case(rec_pre, persist=False)
    retriever = SimilarCaseRetriever(store)

    # Cutoff is 2016-07-02 -> rec_pre (closed 2016-07-01) MUST be eligible
    matches = retriever.retrieve_similar_cases(
        target_entities={"card_id": "C9999-K1", "customer_id": "C9999"},
        pattern="out_of_region_use",
        effective_timestamp="2016-07-02 00:00:00"
    )
    assert len(matches) > 0
    matched_ids = [m.case_record.case_id for m in matches]
    assert "CC-HIST-PRE" in matched_ids


def test_post_cutoff_historical_case_blocked(tmp_path):
    """Verifies that a case closed after the evaluation cutoff timestamp is strictly excluded."""
    store = CaseMemoryStore(writeback_path=str(tmp_path / "wb.jsonl"))
    rec_post = CaseMemoryRecord(
        case_id="CC-HIST-POST",
        card_id="C8888-K1",
        customer_id="C8888",
        closed_at="2016-07-15 12:00:00",
        historical_outcome="confirmed_fraud",
        pattern="out_of_region_use",
        exposure_usd=300.0,
        provenance=MemoryProvenanceType.HISTORICAL_CSV.value
    )
    store.add_case(rec_post, persist=False)
    retriever = SimilarCaseRetriever(store)

    # Cutoff is 2016-07-05 -> rec_post (closed 2016-07-15) MUST be excluded
    matches = retriever.retrieve_similar_cases(
        target_entities={"card_id": "C8888-K1", "customer_id": "C8888"},
        pattern="out_of_region_use",
        effective_timestamp="2016-07-05 00:00:00"
    )
    matched_ids = [m.case_record.case_id for m in matches]
    assert "CC-HIST-POST" not in matched_ids


def test_benchmark_frozen_memory_snapshot_blocks_writeback(tmp_path):
    """Verifies that frozen memory snapshots block writebacks and eliminate cross-case contamination."""
    store = CaseMemoryStore(writeback_path=str(tmp_path / "wb.jsonl"))
    initial_count = store.count()

    # Create frozen benchmark snapshot
    snapshot = store.create_snapshot(effective_timestamp="2016-07-05 00:00:00")
    assert snapshot.is_frozen is True

    # Attempt to write-back into frozen snapshot
    new_rec = CaseMemoryRecord(
        case_id="INV-BENCHMARK-001",
        card_id="C1111-K1",
        customer_id="C1111",
        closed_at="2016-07-06 00:00:00",
        historical_outcome="fraud",
        pattern="card_testing",
        exposure_usd=100.0
    )
    success = snapshot.add_case(new_rec)
    assert success is False
    assert snapshot.get_case("INV-BENCHMARK-001") is None

    # Verify subsequent benchmark retrieval cannot see INV-BENCHMARK-001
    retriever = SimilarCaseRetriever(snapshot)
    matches = retriever.retrieve_similar_cases(
        target_entities={"card_id": "C1111-K1", "customer_id": "C1111"},
        pattern="card_testing"
    )
    matched_ids = [m.case_record.case_id for m in matches]
    assert "INV-BENCHMARK-001" not in matched_ids


def test_active_investigation_self_retrieval_blocked(tmp_path):
    """Verifies that an active investigation cannot retrieve itself, with or without state."""
    store = CaseMemoryStore(writeback_path=str(tmp_path / "wb.jsonl"))
    retriever = SimilarCaseRetriever(store)

    # 1. State-based self retrieval blocked
    state = InvestigationState(
        investigation_id="CC-0001",
        trigger={},
        target_entities={"card_id": "C00259-K1"},
        ledger=EvidenceLedger()
    )
    matches_state = retriever.retrieve_similar_cases(state=state)
    assert all(m.case_record.case_id != "CC-0001" for m in matches_state)

    # 2. Entity-based self retrieval blocked
    matches_ent = retriever.retrieve_similar_cases(
        target_entities={"case_id": "CC-0001", "card_id": "C00259-K1"}
    )
    assert all(m.case_record.case_id != "CC-0001" for m in matches_ent)


def test_active_transaction_exclusion_blocked(tmp_path):
    """Verifies that historical records matching the active flagged transaction are strictly excluded."""
    store = CaseMemoryStore(writeback_path=str(tmp_path / "wb.jsonl"))
    # Seed a case with active transaction TXN-EXCL-1234
    rec = CaseMemoryRecord(
        case_id="CC-EXCL-TEST",
        card_id="C00259-K1",
        customer_id="C00259",
        closed_at="2016-07-01 10:00:00",
        historical_outcome="confirmed_fraud",
        pattern="card_not_present_fraud",
        first_fraud_txn_id="TXN-EXCL-1234",
        txn_ids=["TXN-EXCL-1234"],
        exposure_usd=150.0
    )
    store.add_case(rec, persist=False)
    retriever = SimilarCaseRetriever(store)

    matches = retriever.retrieve_similar_cases(
        target_entities={"card_id": "C00259-K1", "customer_id": "C00259", "flagged_txn_id": "TXN-EXCL-1234"}
    )
    matched_ids = [m.case_record.case_id for m in matches]
    assert "CC-EXCL-TEST" not in matched_ids


def test_historical_narrative_remains_contextual_cannot_become_evidence(belief_engine, tmp_path):
    """CRITICAL: Verifies that historical LLM narrative/analyst notes cannot become an EvidenceItem or alter belief."""
    store = CaseMemoryStore(writeback_path=str(tmp_path / "wb.jsonl"))
    # Seed historical case with elaborate analyst narrative
    rich_narrative = (
        "### 1. Executive Summary\n"
        "Massive fraud syndicate detected across 100 cards with probability 0.99.\n"
        "Analyst confirmed severe account takeover and organized crime ring."
    )
    rec = CaseMemoryRecord(
        case_id="CC-RICH-NARRATIVE",
        card_id="CARD-NARRATIVE-01",
        customer_id="CUST-NARRATIVE-01",
        closed_at="2016-07-01 10:00:00",
        historical_outcome="confirmed_fraud",
        pattern="account_takeover",
        analyst_notes=rich_narrative,
        exposure_usd=10000.0
    )
    store.add_case(rec, persist=False)
    retriever = SimilarCaseRetriever(store)

    # Evaluate an active investigation
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="m",
        finding="Risk score 0.50",
        lr=2.4,
        log_lr=0.875
    ))
    state = belief_engine.evaluate_investigation("INV-NARR-TEST", {}, {"card_id": "CARD-NARRATIVE-01"}, ledger)
    p_before = state.belief_state["fraud_probability"]
    cov_before = state.uncertainty.evidence_coverage
    gate_before = state.decision_gate_passed

    matches = retriever.retrieve_similar_cases(state=state, top_k=1)
    assert len(matches) == 1
    match = matches[0]
    assert match.case_record.case_id == "CC-RICH-NARRATIVE"

    # Verify structural boundaries:
    assert not isinstance(match, EvidenceItem)
    assert not hasattr(match, "lr")
    assert not hasattr(match, "log_lr")
    assert match.role == "CONTEXTUAL_PRECEDENT_ONLY"

    # State re-evaluation: must remain identical
    state_after = belief_engine.evaluate_investigation("INV-NARR-TEST", {}, {"card_id": "C00259-K1"}, ledger)
    assert state_after.belief_state["fraud_probability"] == pytest.approx(p_before, abs=1e-6)
    assert state_after.uncertainty.evidence_coverage == cov_before
    assert state_after.decision_gate_passed == gate_before


# ==============================================================================
# 2. Similar-Case Retrieval: Provenance & 1-to-1 Scoring Explanation Integrity
# ==============================================================================

def test_similar_case_match_exposes_full_provenance(tmp_path):
    """Verifies that SimilarCaseMatch exposes case_id, similarity_score, matching_features, timestamp, and eligibility."""
    store = CaseMemoryStore(writeback_path=str(tmp_path / "wb.jsonl"))
    rec = CaseMemoryRecord(
        case_id="CC-PROV-001",
        card_id="C5555-K1",
        customer_id="C5555",
        closed_at="2016-07-03 14:20:00",
        historical_outcome="confirmed_fraud",
        pattern="card_testing",
        exposure_usd=120.0
    )
    store.add_case(rec, persist=False)
    retriever = SimilarCaseRetriever(store)

    matches = retriever.retrieve_similar_cases(
        target_entities={"card_id": "C5555-K1", "customer_id": "C5555"},
        pattern="card_testing",
        exposure_usd=120.0,
        effective_timestamp="2016-07-04 00:00:00"
    )
    assert len(matches) == 1
    m = matches[0]

    # Required provenance fields
    assert m.case_id == "CC-PROV-001"
    assert m.similarity_score > 0.50
    assert len(m.matching_features) >= 3
    assert m.historical_timestamp == "2016-07-03 14:20:00"
    assert "on/before evaluation cutoff" in m.eligibility_reason
    assert m.role == "CONTEXTUAL_PRECEDENT_ONLY"


def test_similarity_score_matches_documented_features_one_to_one(tmp_path):
    """Verifies that every feature mentioned in the explanation corresponds 1-to-1 with an active scoring input."""
    store = CaseMemoryStore(writeback_path=str(tmp_path / "wb.jsonl"))
    rec = CaseMemoryRecord(
        case_id="CC-SCORE-TEST",
        card_id="C7777-K1",
        customer_id="C7777",
        closed_at="2016-07-01 10:00:00",
        historical_outcome="confirmed_fraud",
        pattern="out_of_region_use",
        exposure_usd=500.0,
        evidence_families_observed=["GEOGRAPHIC_LOCATION"],
        connected_card_ids=["C7777-K2"]
    )
    store.add_case(rec, persist=False)
    retriever = SimilarCaseRetriever(store)

    # 1. Matching card, customer, and connected card device link (pattern and exposure differ)
    matches1 = retriever.retrieve_similar_cases(
        target_entities={"card_id": "C7777-K1", "customer_id": "C7777"},
        pattern="card_testing",
        exposure_usd=10.0,
        top_k=1
    )
    assert len(matches1) == 1
    m1 = matches1[0]
    # Expected: same_card (0.30) + same_cust (0.20) + shared_device (0.05) = 0.55
    assert m1.similarity_score == pytest.approx(0.55, abs=1e-3)
    feature_str1 = "; ".join(m1.shared_features)
    assert "Identical card ID" in feature_str1
    assert "Identical customer ID" in feature_str1
    assert "Shared device infrastructure" in feature_str1
    assert "Matching fraud typology" not in feature_str1
    assert "Comparable dollar exposure" not in feature_str1

    # 2. Matching card, customer, pattern, exposure, and connected card device link
    matches2 = retriever.retrieve_similar_cases(
        target_entities={"card_id": "C7777-K1", "customer_id": "C7777"},
        pattern="out_of_region_use",
        exposure_usd=500.0,
        top_k=1
    )
    assert len(matches2) == 1
    m2 = matches2[0]
    # Expected: same_card (0.30) + same_cust (0.20) + same_pat (0.25) + exp_prox=1.0 (0.15) + shared_device (0.05) = 0.95
    assert m2.similarity_score == pytest.approx(0.95, abs=1e-3)
    feature_str2 = "; ".join(m2.shared_features)
    assert "Identical card ID" in feature_str2
    assert "Identical customer ID" in feature_str2
    assert "Matching fraud typology" in feature_str2
    assert "Comparable dollar exposure" in feature_str2
    assert "Shared device infrastructure" in feature_str2


# ==============================================================================
# 3. Negative GraphRAG Traversal Tests
# ==============================================================================

def test_negative_graphrag_traversal_out_of_region_does_not_leak_r5_or_r6(belief_engine, graphrag_retriever):
    """Verifies that OUT_OF_REGION evidence retrieves R4 but strictly DOES NOT retrieve unrelated R5 or R6."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.OUT_OF_REGION,
        source="geo_profile",
        finding="Card present in foreign region",
        lr=6.8,
        log_lr=1.917
    ))
    state = belief_engine.evaluate_investigation("INV-NEG-GEO", {}, {"card_id": "C1"}, ledger)

    items = graphrag_retriever.retrieve_grounded_context(state=state, exposure_usd=400.0)
    chunk_ids = {k.chunk.chunk_id for k in items}

    # Grounded items MUST be present
    assert "KNOW-TYPO-OUT-OF-REGION" in chunk_ids
    assert "KNOW-POLICY-R4" in chunk_ids

    # Unrelated items MUST NOT be present
    assert "KNOW-TYPO-CARDTESTING" not in chunk_ids
    assert "KNOW-TYPO-SHARED-DEVICE" not in chunk_ids
    assert "KNOW-POLICY-R5" not in chunk_ids
    assert "KNOW-POLICY-R6" not in chunk_ids


def test_negative_graphrag_traversal_velocity_does_not_leak_r4_or_r6(belief_engine, graphrag_retriever):
    """Verifies that HIGH_VELOCITY evidence retrieves card testing typology but DOES NOT retrieve R4 or R6."""
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.HIGH_VELOCITY,
        source="velocity_check",
        finding="Rapid transaction burst",
        lr=8.5,
        log_lr=2.14
    ))
    state = belief_engine.evaluate_investigation("INV-NEG-VEL", {}, {"card_id": "C1"}, ledger)

    items = graphrag_retriever.retrieve_grounded_context(state=state, exposure_usd=300.0)
    chunk_ids = {k.chunk.chunk_id for k in items}

    # Grounded typology MUST be present
    assert "KNOW-TYPO-CARDTESTING" in chunk_ids

    # Unrelated geographic and shared device policies MUST NOT be present
    assert "KNOW-TYPO-OUT-OF-REGION" not in chunk_ids
    assert "KNOW-POLICY-R4" not in chunk_ids
    assert "KNOW-POLICY-R6" not in chunk_ids


# ==============================================================================
# 4. Regulation E Precise Statutory Wording Test
# ==============================================================================

def test_regulation_e_timing_and_conditional_provisional_credit_wording(knowledge_base):
    """Verifies that KNOW-REG-REGE distinguishes 10-day timeline from conditional 45-day provisional credit."""
    chunk = knowledge_base.get_chunk("KNOW-REG-REGE")
    assert chunk is not None

    text = chunk.text
    # 1. Distinguishes general 10-business-day investigation timeline
    assert "10 business days" in text
    assert "1005.11(c)(1)" in text

    # 2. Provisional credit is conditional for 45-day extension, not an unconditional grant
    assert "1005.11(c)(2)" in text
    assert "45 calendar days" in text
    assert "statutory prerequisite" in text
    assert "not an automatic unconditional grant" in text

    # 3. 90-day exceptions for POS, foreign, new accounts
    assert "90 calendar days" in text
    assert "1005.11(c)(3)" in text

    # 4. Tiered consumer liability under 12 CFR 1005.6
    assert "1005.6" in text
    assert "$50" in text
    assert "$500" in text
    assert "zero consumer liability" in text


# ==============================================================================
# 5. Citation Reference Validation Terminology & Structural Auditing
# ==============================================================================

def test_citation_reference_validation_terminology_and_reporting(belief_engine, synthesizer, graphrag_retriever):
    """Verifies that citation validation honestly documents reference checking rather than semantic entailment."""
    ev = EvidenceItem(
        evidence_id="EVD-REAL-001",
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="m",
        finding="Real empirical finding",
        lr=2.4,
        log_lr=0.875
    )
    state = belief_engine.evaluate_investigation("INV-REF-VAL", {}, {"card_id": "C1"}, EvidenceLedger(items=[ev]))
    items = graphrag_retriever.retrieve_grounded_context(state=state, exposure_usd=200.0)
    context = InvestigationContextAssembler.assemble(state=state, retrieved_knowledge=items, exposure_usd=200.0)

    # Simulated report text
    report = (
        "Investigation [INV-REF-VAL] verified evidence [EVD-REAL-001]. "
        "Reference to ungrounded evidence [EVD-HALLUCINATED] and fake rule [KNOW-POLICY-R99]."
    )
    audited = synthesizer._validate_and_sanitize_citations(report, context)

    # Verification header & explicit disclaimer
    assert "Provenance Citation Reference Validation Audit" in audited
    assert "Citation Reference Verification Note" in audited
    assert "does not perform semantic entailment" in audited

    # Citation counts & warnings
    assert "Observed Evidence Citations Verified:** 1 / 2" in audited
    assert "EVD-HALLUCINATED" in audited
    assert "KNOW-POLICY-R99" in audited


# ==============================================================================
# 6. Final Pre-Benchmark Readiness Verification Tests
# ==============================================================================

def test_frozen_memory_deep_copy_isolation_against_store_mutation(tmp_path):
    """Proves that mutating the original writable store cannot mutate the frozen snapshot."""
    store = CaseMemoryStore(writeback_path=str(tmp_path / "wb.jsonl"))
    initial_rec = CaseMemoryRecord(
        case_id="CC-ISOL-001",
        card_id="C0001-K1",
        customer_id="C0001",
        closed_at="2016-07-01 00:00:00",
        historical_outcome="confirmed_fraud",
        pattern="card_testing",
        exposure_usd=250.0,
        connected_card_ids=["C0001-K2", "C0001-K3"]
    )
    store.add_case(initial_rec, persist=False)

    # 1. Create frozen snapshot
    snapshot = store.create_snapshot(effective_timestamp="2016-07-05 00:00:00")
    assert snapshot.is_frozen is True
    initial_snap_count = snapshot.count()
    assert initial_snap_count > 0

    # 2. Mutate original store: add a new case
    new_rec = CaseMemoryRecord(
        case_id="CC-MUTATION-NEW",
        card_id="C9999-K1",
        customer_id="C9999",
        closed_at="2016-07-02 00:00:00",
        historical_outcome="cleared",
        pattern="none"
    )
    store.add_case(new_rec, persist=False)
    assert store.get_case("CC-MUTATION-NEW") is not None
    assert snapshot.get_case("CC-MUTATION-NEW") is None  # Snapshot isolated from additions

    # 3. Mutate original store: modify existing record's nested lists and fields
    orig_rec = store.get_case("CC-ISOL-001")
    orig_rec.connected_card_ids.append("CORRUPTED-CARD")
    orig_rec.exposure_usd = 999999.99

    # 4. Prove snapshot's deep-copied record remains completely untouched
    snap_rec = snapshot.get_case("CC-ISOL-001")
    assert snap_rec is not None
    assert "CORRUPTED-CARD" not in snap_rec.connected_card_ids
    assert snap_rec.connected_card_ids == ["C0001-K2", "C0001-K3"]
    assert snap_rec.exposure_usd == 250.0

    # 5. Prove write_case() and add_case() on snapshot fail and reject writeback
    attempt1 = snapshot.write_case(new_rec, persist=False)
    attempt2 = snapshot.add_case(new_rec, persist=False)
    assert attempt1 is False
    assert attempt2 is False
    assert snapshot.get_case("CC-MUTATION-NEW") is None
    assert snapshot.count() == initial_snap_count


def test_temporal_provenance_strict_cutoff_and_missing_timestamp_exclusion(tmp_path):
    """Verifies that cutoff filtering properly handles closed_at, opened_at, and rejects untimestamped cases."""
    store = CaseMemoryStore(writeback_path=str(tmp_path / "wb.jsonl"))

    # Case A: closed before cutoff -> eligible
    rec_a = CaseMemoryRecord(
        case_id="CC-TIME-A",
        card_id="C-TIME-1",
        customer_id="C-TIME",
        closed_at="2016-07-02 00:00:00",
        historical_outcome="confirmed_fraud",
        pattern="out_of_region_use"
    )
    # Case B: closed after cutoff -> excluded
    rec_b = CaseMemoryRecord(
        case_id="CC-TIME-B",
        card_id="C-TIME-1",
        customer_id="C-TIME",
        closed_at="2016-07-10 00:00:00",
        historical_outcome="confirmed_fraud",
        pattern="out_of_region_use"
    )
    # Case C: closed_at is None, opened_at is before cutoff -> eligible
    rec_c = CaseMemoryRecord(
        case_id="CC-TIME-C",
        card_id="C-TIME-1",
        customer_id="C-TIME",
        opened_at="2016-07-01 12:00:00",
        closed_at=None,
        historical_outcome="confirmed_fraud",
        pattern="out_of_region_use"
    )
    # Case D: closed_at is None, opened_at is after cutoff -> excluded
    rec_d = CaseMemoryRecord(
        case_id="CC-TIME-D",
        card_id="C-TIME-1",
        customer_id="C-TIME",
        opened_at="2016-07-08 00:00:00",
        closed_at=None,
        historical_outcome="confirmed_fraud",
        pattern="out_of_region_use"
    )
    # Case E: both timestamps None -> strictly excluded under active cutoff
    rec_e = CaseMemoryRecord(
        case_id="CC-TIME-E",
        card_id="C-TIME-1",
        customer_id="C-TIME",
        opened_at=None,
        closed_at=None,
        historical_outcome="confirmed_fraud",
        pattern="out_of_region_use"
    )

    for r in [rec_a, rec_b, rec_c, rec_d, rec_e]:
        store.add_case(r, persist=False)

    retriever = SimilarCaseRetriever(store)
    matches = retriever.retrieve_similar_cases(
        target_entities={"card_id": "C-TIME-1", "customer_id": "C-TIME"},
        pattern="out_of_region_use",
        effective_timestamp="2016-07-05 00:00:00",
        top_k=10
    )
    matched_ids = [m.case_record.case_id for m in matches]

    assert "CC-TIME-A" in matched_ids
    assert "CC-TIME-C" in matched_ids
    assert "CC-TIME-B" not in matched_ids
    assert "CC-TIME-D" not in matched_ids
    assert "CC-TIME-E" not in matched_ids


def test_r5_r6_graphrag_action_provenance_and_non_evidential_isolation(policy_engine, graphrag_retriever, belief_engine):
    """Verifies that R5/R6 action tags require genuine observed evidence and cannot bootstrap evidential authority."""
    # 1. Without CARD_TESTING_SEQUENCE, PolicyEngine NEVER produces R5 action reasons
    ledger_clean = EvidenceLedger(items=[])
    actions_clean = policy_engine.evaluate(
        fraud_probability=0.5,
        verdict="uncertain",
        exposure_usd=500.0,
        ledger=ledger_clean,
        case_context={}
    )
    assert not any("R5" in a.reason for a in actions_clean)
    assert not any("R6" in a.reason for a in actions_clean)

    # 2. With CARD_TESTING_SEQUENCE, PolicyEngine produces R5
    ev_card_testing = EvidenceItem(
        evidence_id="EVD-TEST-001",
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        source="m",
        finding="Card testing sequence",
        lr=5.0,
        log_lr=1.609
    )
    ledger_r5 = EvidenceLedger(items=[ev_card_testing])
    actions_r5 = policy_engine.evaluate(
        fraud_probability=0.85,
        verdict="fraud",
        exposure_usd=150.0,
        ledger=ledger_r5,
        case_context={}
    )
    assert any("R5" in a.reason for a in actions_r5)

    # 3. GraphRAG retrieval conditioned on these actions retrieves KNOW-POLICY-R5
    state_r5 = belief_engine.evaluate_investigation("INV-R5-TEST", {}, {"card_id": "C1"}, ledger_r5)
    retrieved = graphrag_retriever.retrieve_grounded_context(
        state=state_r5,
        exposure_usd=150.0,
        policy_actions=actions_r5
    )
    retrieved_chunk_ids = [k.chunk.chunk_id for k in retrieved]
    assert "KNOW-POLICY-R5" in retrieved_chunk_ids

    # 4. Critical Non-Negotiable: Retrieved knowledge items cannot mutate belief, cannot alter coverage, and cannot become EvidenceItems
    initial_p = state_r5.belief_state["fraud_probability"]
    initial_cov = state_r5.uncertainty.evidence_coverage
    assert not hasattr(retrieved[0], "lr")
    assert state_r5.belief_state["fraud_probability"] == initial_p
    assert state_r5.uncertainty.evidence_coverage == initial_cov

