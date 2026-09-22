from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.belief.state import InvestigationState
from src.memory.models import SimilarCaseMatch
from src.knowledge.models import RetrievedKnowledgeItem
from src.policy.engine import ActionRecommendation


class InvestigationContext(BaseModel):
    """Strictly partitioned investigation context separating:
    - OBSERVED EVIDENCE (Empirical Graph Queries)
    - HISTORICAL PRECEDENT (Case Memory)
    - GOVERNING POLICY & REGULATIONS (Authoritative Standards)
    - DECISION STATE & ACTIONS (Deterministic Gating)
    
    Guarantees that context layers cannot be conflated into an undifferentiated blob.
    """
    investigation_id: str
    target_entities: Dict[str, Any] = Field(default_factory=dict)
    exposure_usd: float = 0.0

    # Section A: Observed Empirical Evidence
    observed_evidence_summary: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_coverage: float = 0.0
    epistemic_uncertainty: float = 0.0
    aleatoric_uncertainty: float = 0.0
    decision_gate_passed: bool = False
    decision_state: str = "INSUFFICIENT_EVIDENCE"

    # Section B: Historical Case Memory Precedents
    historical_precedents: List[SimilarCaseMatch] = Field(default_factory=list)

    # Section C: Policy & Regulatory Knowledge
    retrieved_knowledge: List[RetrievedKnowledgeItem] = Field(default_factory=list)

    # Section D: Deterministic Belief & Policy Output
    prior_prob: float = 0.5
    posterior_prob: float = 0.5
    policy_recommendations: List[ActionRecommendation] = Field(default_factory=list)

    def render_context_document(self) -> str:
        """Formats the multi-partitioned context with explicit delimiters and citation anchors."""
        sections = []

        # Header
        sections.append(f"# INVESTIGATION GROUNDED CONTEXT DOSSIER: {self.investigation_id}")
        sections.append(f"Target Entities: Card={self.target_entities.get('card_id')}, "
                        f"Customer={self.target_entities.get('customer_id')}, "
                        f"Txn={self.target_entities.get('flagged_txn_id')}")
        sections.append(f"Financial Exposure: ${self.exposure_usd:,.2f}")
        sections.append(f"Posterior Probability: P(Fraud) = {self.posterior_prob:.4f} | Gate: {'PASSED' if self.decision_gate_passed else 'LOCKED'}")
        sections.append("")

        # Section A: Observed Empirical Evidence
        sections.append("=" * 70)
        sections.append("SECTION A: OBSERVED GRAPH & TOOL EVIDENCE (AUTHORITATIVE EMPIRICAL DATA)")
        sections.append("=" * 70)
        sections.append("CRITICAL: The items below represent empirical observations from real tool and graph executions.")
        sections.append(f"Coverage: {self.evidence_coverage * 100:.0f}% | Epistemic Uncertainty: {self.epistemic_uncertainty:.2f} | Aleatoric Conflict: {self.aleatoric_uncertainty:.2f}")
        sections.append("")
        if not self.observed_evidence_summary:
            sections.append("No active evidence items observed.")
        else:
            for ev in self.observed_evidence_summary:
                sections.append(
                    f"- [{ev['evidence_id']}] Type: {ev['type']} | Source: {ev['source']} | "
                    f"LR: {ev['lr']:.2f} (log-LR: {ev['log_lr']:.3f}) | Direction: {ev['direction']}\n"
                    f"  Finding: {ev['finding']}\n"
                    f"  Provenance: {ev['provenance']}"
                )
        sections.append("")

        # Section B: Historical Case Memory Precedents
        sections.append("=" * 70)
        sections.append("SECTION B: HISTORICAL CASE PRECEDENT (CONTEXTUAL MEMORY ONLY — NON-EVIDENTIAL)")
        sections.append("=" * 70)
        sections.append("CRITICAL: Historical cases provide qualitative precedent. They have LR=1.0 and do not alter belief or coverage.")
        sections.append("")
        if not self.historical_precedents:
            sections.append("No relevant historical precedent cases retrieved.")
        else:
            for m in self.historical_precedents:
                c = m.case_record
                acts = ", ".join(c.actions_taken) if c.actions_taken else "None"
                sections.append(
                    f"- [{c.case_id}] (Similarity: {m.similarity_score:.2f}) Outcome: {c.historical_outcome.upper()} | Typology: {c.pattern}\n"
                    f"  Actions Taken: {acts} | Exposure: ${c.exposure_usd:,.2f}\n"
                    f"  Rationale: {m.explanation}\n"
                    f"  Analyst Notes: {c.analyst_notes}\n"
                    f"  Provenance: {c.provenance}"
                )
        sections.append("")

        # Section C: Policy & Regulatory Knowledge
        sections.append("=" * 70)
        sections.append("SECTION C: GOVERNING POLICY & REGULATORY KNOWLEDGE (AUTHORITATIVE STANDARDS)")
        sections.append("=" * 70)
        sections.append("CRITICAL: Operational and statutory requirements governing banking actions.")
        sections.append("")
        if not self.retrieved_knowledge:
            sections.append("No explicit regulatory statutes retrieved.")
        else:
            for k in self.retrieved_knowledge:
                c = k.chunk
                sections.append(
                    f"- [{c.chunk_id}] {c.title} ({c.section_reference})\n"
                    f"  Authority: {c.governing_body} | Version: {c.version}\n"
                    f"  Grounded Rule Text: \"{c.text}\"\n"
                    f"  GraphRAG Match Rationale: {k.match_rationale}\n"
                    f"  Retrieval Path: {getattr(k, 'retrieval_path', '') or 'PolicyMapper'}"
                )
        sections.append("")

        # Section D: Decision State & Actions
        sections.append("=" * 70)
        sections.append("SECTION D: OPERATIONAL POLICY DISPOSITION")
        sections.append("=" * 70)
        sections.append(f"Decision State: {self.decision_state} (Gate Passed: {self.decision_gate_passed})")
        if not self.policy_recommendations:
            sections.append("Recommended Actions: MONITOR_CARD (auto)")
        else:
            for act in self.policy_recommendations:
                sections.append(f"- Action: {act.action} | Route: {act.approval_route} | Rationale: {act.reason}")

        return "\n".join(sections)


class InvestigationContextAssembler:
    """Constructs the canonical InvestigationContext from active state and retrieved knowledge."""

    @staticmethod
    def assemble(
        state: InvestigationState,
        similar_cases: Optional[List[SimilarCaseMatch]] = None,
        retrieved_knowledge: Optional[List[RetrievedKnowledgeItem]] = None,
        policy_actions: Optional[List[ActionRecommendation]] = None,
        exposure_usd: float = 0.0
    ) -> InvestigationContext:
        """Assembles segregated context while strictly preserving evidence boundaries."""
        ev_summaries = []
        for item in state.evidence_items:
            ev_summaries.append({
                "evidence_id": item.evidence_id,
                "type": item.evidence_type.value,
                "source": item.source,
                "finding": item.finding,
                "lr": item.lr,
                "log_lr": item.log_lr,
                "direction": item.direction.value,
                "provenance": item.provenance or "Graph GSQL Execution"
            })

        return InvestigationContext(
            investigation_id=state.investigation_id,
            target_entities=dict(state.target_entities),
            exposure_usd=round(exposure_usd, 2),
            observed_evidence_summary=ev_summaries,
            evidence_coverage=state.uncertainty.evidence_coverage,
            epistemic_uncertainty=state.uncertainty.epistemic_uncertainty,
            aleatoric_uncertainty=state.uncertainty.aleatoric_uncertainty,
            decision_gate_passed=state.decision_gate_passed,
            decision_state=state.decision_state.value,
            historical_precedents=similar_cases or [],
            retrieved_knowledge=retrieved_knowledge or [],
            prior_prob=round(state.belief_state.get("prior_prob", 0.5), 4),
            posterior_prob=round(state.belief_state.get("fraud_probability", 0.5), 4),
            policy_recommendations=policy_actions or []
        )
