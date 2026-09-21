from typing import List, Dict, Any, Optional

from src.belief.state import InvestigationState
from src.evidence.types import EvidenceType
from src.policy.engine import ActionRecommendation
from src.knowledge.models import KnowledgeChunk, RetrievedKnowledgeItem
from src.knowledge.store import InvestigationKnowledgeBase


class PolicyGraphRAGRetriever:
    """Investigation GraphRAG Knowledge Retriever.
    
    Traverses from observed graph entities and evidence signals into the authoritative
    policy, typology, and regulatory knowledge graph:
    
    Target Entities & Graph Evidence
                 ↓
      Typology Classification
                 ↓
      Policy Rules (R1 - R10)
                 ↓
      Regulatory Statutes (FinCEN / Reg E / FATF)
    
    CRITICAL NON-NEGOTIABLE GUARANTEES:
    - Retrieved passages are CONTEXTUAL GUIDANCE ONLY.
    - Never mutates numeric fraud probability or epistemic uncertainty.
    - Never increments evidence coverage.
    - Never bypasses Decision Gate blocks.
    - Preserves verbatim provenance citations for all retrieved text.
    """

    def __init__(self, kb: Optional[InvestigationKnowledgeBase] = None):
        self.kb = kb or InvestigationKnowledgeBase()

    def retrieve_grounded_context(
        self,
        state: InvestigationState,
        exposure_usd: float = 0.0,
        policy_actions: Optional[List[ActionRecommendation]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedKnowledgeItem]:
        """Performs multi-hop GraphRAG retrieval connecting graph observations to policy rules and regulations."""
        evidence_types = {item.evidence_type for item in state.evidence_items}
        trigger_type = state.trigger.get("trigger_type", "")
        actions = policy_actions or []
        action_names = {a.action for a in actions}

        retrieved: Dict[str, RetrievedKnowledgeItem] = {}

        # 1. Hop: Evidence Signals -> Typology Knowledge
        if EvidenceType.CARD_TESTING_SEQUENCE in evidence_types or EvidenceType.HIGH_VELOCITY in evidence_types:
            chunk = self.kb.get_chunk("KNOW-TYPO-CARDTESTING")
            if chunk:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.95,
                    match_rationale="Observed CARD_TESTING_SEQUENCE or HIGH_VELOCITY in graph evidence directly matches card testing attack typology.",
                    applicable_statute_or_rule="Rule R5",
                    retrieval_path="GraphEvidence -> CARD_TESTING_SEQUENCE -> Typology:CardTesting"
                )

        if EvidenceType.SHARED_DEVICE_RING in evidence_types or EvidenceType.PROXY_DETECTED in evidence_types:
            chunk = self.kb.get_chunk("KNOW-TYPO-SHARED-DEVICE")
            if chunk:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.95,
                    match_rationale="Observed SHARED_DEVICE_RING or PROXY_DETECTED indicates multi-card hardware sharing syndicate.",
                    applicable_statute_or_rule="Rule R6",
                    retrieval_path="GraphEvidence -> SHARED_DEVICE_RING -> Typology:DeviceSyndicate"
                )

        if EvidenceType.OUT_OF_REGION in evidence_types:
            chunk = self.kb.get_chunk("KNOW-TYPO-OUT-OF-REGION")
            if chunk:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.90,
                    match_rationale="Observed OUT_OF_REGION evidence indicates geographic displacement without registered travel profile.",
                    applicable_statute_or_rule="Rule R4",
                    retrieval_path="GraphEvidence -> OUT_OF_REGION -> Typology:GeographicDisplacement"
                )

        if EvidenceType.CNP_NEW_DEVICE in evidence_types or EvidenceType.ACCOUNT_TAKEOVER in evidence_types:
            chunk = self.kb.get_chunk("KNOW-TYPO-ATO")
            if chunk:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.90,
                    match_rationale="Observed CNP_NEW_DEVICE indicates potential account takeover / credential stuffing signature.",
                    applicable_statute_or_rule="Rule R2/R6",
                    retrieval_path="GraphEvidence -> CNP_NEW_DEVICE -> Typology:AccountTakeover"
                )

        # 2. Hop: Graph Evidence -> Policy Rules (R1 - R10)
        # Rule R5: Card Testing
        if EvidenceType.CARD_TESTING_SEQUENCE in evidence_types or any("R5" in a.reason for a in actions):
            chunk = self.kb.get_chunk("KNOW-POLICY-R5")
            if chunk and chunk.chunk_id not in retrieved:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.98,
                    match_rationale="Card testing sequence requires mandatory transaction decline under L1 authorization review.",
                    applicable_statute_or_rule="Rule R5",
                    retrieval_path="GraphEvidence -> CARD_TESTING_SEQUENCE -> Policy:Rule R5"
                )

        # Rule R6: Shared Device Ring
        if EvidenceType.SHARED_DEVICE_RING in evidence_types or any("R6" in a.reason for a in actions):
            chunk = self.kb.get_chunk("KNOW-POLICY-R6")
            if chunk and chunk.chunk_id not in retrieved:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.98,
                    match_rationale="Shared device ring requires case creation, connected card monitoring, and L2 syndicate reporting.",
                    applicable_statute_or_rule="Rule R6",
                    retrieval_path="GraphEvidence -> SHARED_DEVICE_RING -> Policy:Rule R6"
                )

        # Rule R4: Out-of-Region Activity
        if EvidenceType.OUT_OF_REGION in evidence_types or any("R4" in a.reason for a in actions):
            chunk = self.kb.get_chunk("KNOW-POLICY-R4")
            if chunk and chunk.chunk_id not in retrieved:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.92,
                    match_rationale="Out-of-region card-present transaction requires transaction decline and customer verification under Rule R4.",
                    applicable_statute_or_rule="Rule R4",
                    retrieval_path="GraphEvidence -> OUT_OF_REGION -> Policy:Rule R4"
                )

        # Rule R2: Customer Denial / Dispute
        if EvidenceType.CUSTOMER_DENIAL in evidence_types or trigger_type == "customer_report":
            chunk = self.kb.get_chunk("KNOW-POLICY-R2")
            if chunk and chunk.chunk_id not in retrieved:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.98,
                    match_rationale="Direct cardholder denial mandates card block and investigation under Regulation E.",
                    applicable_statute_or_rule="Rule R2",
                    retrieval_path="GraphEvidence -> CUSTOMER_DENIAL -> Policy:Rule R2"
                )

        # Rule R3: Customer Confirmation
        if EvidenceType.CUSTOMER_CONFIRMATION in evidence_types:
            chunk = self.kb.get_chunk("KNOW-POLICY-R3")
            if chunk and chunk.chunk_id not in retrieved:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.98,
                    match_rationale="Cardholder confirmation warrants immediate closure without punitive action.",
                    applicable_statute_or_rule="Rule R3",
                    retrieval_path="GraphEvidence -> CUSTOMER_CONFIRMATION -> Policy:Rule R3"
                )

        # Rule R7: Recurring Charge Dispute
        if EvidenceType.RECURRING_CHARGE_MATCH in evidence_types and EvidenceType.CUSTOMER_DENIAL in evidence_types:
            chunk = self.kb.get_chunk("KNOW-POLICY-R7")
            if chunk and chunk.chunk_id not in retrieved:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.95,
                    match_rationale="Disputed transaction matches verified recurring subscription cadence.",
                    applicable_statute_or_rule="Rule R7",
                    retrieval_path="GraphEvidence -> RECURRING_CHARGE_MATCH -> Policy:Rule R7"
                )

        p_fraud = state.belief_state.get("fraud_probability", 0.5)

        # Rule R9: Undocumented Pattern with Clear Evidence of Abuse
        is_undocumented = False
        if context and context.get("pattern") == "undocumented":
            is_undocumented = True
        if hasattr(state, "context") and isinstance(state.context, dict) and state.context.get("pattern") == "undocumented":
            is_undocumented = True
        if (is_undocumented and p_fraud >= 0.70) or any("R9" in a.reason for a in actions):
            chunk = self.kb.get_chunk("KNOW-POLICY-R9")
            if chunk and chunk.chunk_id not in retrieved:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.94,
                    match_rationale="High assessed fraud probability on undocumented pattern requires case creation and L2 reporting under Rule R9.",
                    applicable_statute_or_rule="Rule R9",
                    retrieval_path="GraphEvidence -> HighBeliefUndocumented -> Policy:Rule R9"
                )

        # Rule R8: Uncertain with Exposure > $500
        if 0.30 < p_fraud < 0.70 and exposure_usd > 500.0:
            chunk = self.kb.get_chunk("KNOW-POLICY-R8")
            if chunk and chunk.chunk_id not in retrieved:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.92,
                    match_rationale=f"Belief is unresolved ({p_fraud:.2f}) with exposure ${exposure_usd:,.2f} > $500 threshold.",
                    applicable_statute_or_rule="Rule R8",
                    retrieval_path="GraphEvidence -> HighExposureUncertain -> Policy:Rule R8"
                )

        # Rule R1: Single Signal Weak Warning
        if len(state.evidence_items) <= 1 and p_fraud < 0.70:
            chunk = self.kb.get_chunk("KNOW-POLICY-R1")
            if chunk and chunk.chunk_id not in retrieved:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.85,
                    match_rationale="Weak uncorroborated single signal; punitive blocking is restricted pending customer outreach.",
                    applicable_statute_or_rule="Rule R1",
                    retrieval_path="GraphEvidence -> SingleSignalWeak -> Policy:Rule R1"
                )

        # Bidirectional Rule Mapping: Ensure any explicitly applied policy rules in actions are present
        for a in actions:
            for rule_num in range(1, 10):
                rule_tag = f"R{rule_num}"
                if rule_tag in a.reason:
                    chunk_key = f"KNOW-POLICY-{rule_tag}"
                    if chunk_key not in retrieved:
                        c = self.kb.get_chunk(chunk_key)
                        if c:
                            retrieved[c.chunk_id] = RetrievedKnowledgeItem(
                                chunk=c,
                                relevance_score=0.92,
                                match_rationale=f"Authoritative governing rule for mandated action {a.action}: {a.reason}",
                                applicable_statute_or_rule=f"Rule {rule_tag}",
                                retrieval_path=f"PolicyAction -> {a.action} -> Policy:Rule {rule_tag}"
                            )

        # Rule R10: General Dispositions
        chunk_r10 = self.kb.get_chunk("KNOW-POLICY-R10")
        if chunk_r10 and chunk_r10.chunk_id not in retrieved:
            retrieved[chunk_r10.chunk_id] = RetrievedKnowledgeItem(
                chunk=chunk_r10,
                relevance_score=0.80,
                match_rationale="General bank disposition thresholds and calibrated belief gating governance.",
                applicable_statute_or_rule="Rule R10",
                retrieval_path="BeliefState -> CalibratedGate -> Policy:Rule R10"
            )

        # 3. Hop: Actions & Exposure -> Regulatory Statutes
        # FinCEN SAR Filing (31 CFR 1020.320)
        has_file_report = "FILE_REPORT" in action_names
        is_syndicate = EvidenceType.SHARED_DEVICE_RING in evidence_types
        if has_file_report or exposure_usd >= 1000.0 or (p_fraud >= 0.70 and (is_syndicate or exposure_usd >= 1000.0)):
            chunk = self.kb.get_chunk("KNOW-REG-FINCEN-SAR")
            if chunk and chunk.chunk_id not in retrieved:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.96,
                    match_rationale=f"Exposure (${exposure_usd:,.2f}) or syndicate ring flags mandatory FinCEN SAR filing within 30 days under 31 CFR 1020.320.",
                    applicable_statute_or_rule="31 CFR § 1020.320",
                    retrieval_path="PolicyAction / ExposureThreshold -> Regulation:31 CFR § 1020.320"
                )

        # Regulation E Consumer Protection (12 CFR 1005)
        if EvidenceType.CUSTOMER_DENIAL in evidence_types or trigger_type == "customer_report":
            chunk = self.kb.get_chunk("KNOW-REG-REGE")
            if chunk and chunk.chunk_id not in retrieved:
                retrieved[chunk.chunk_id] = RetrievedKnowledgeItem(
                    chunk=chunk,
                    relevance_score=0.94,
                    match_rationale="Customer reported unauthorized debit triggering Regulation E error resolution statutory protections.",
                    applicable_statute_or_rule="12 CFR §§ 1005.6, 1005.11",
                    retrieval_path="CustomerReport / Denial -> Regulation:12 CFR §§ 1005.6, 1005.11"
                )

        # Sort by relevance descending
        items = list(retrieved.values())
        items.sort(key=lambda x: x.relevance_score, reverse=True)
        return items
