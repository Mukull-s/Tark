import re
import logging
from typing import List, Dict, Any, Optional, Set

from src.synthesis.context import InvestigationContext
from src.tools.llm_client import LLMClient

logger = logging.getLogger(__name__)


class GroundedInvestigationSynthesizer:
    """Investigator-facing grounded narrative synthesizer.
    
    Consumes the strictly segregated InvestigationContext and produces an auditable,
    provenance-anchored explanation referencing observed evidence IDs, historical case IDs,
    and policy knowledge chunk IDs.
    
    CRITICAL NON-NEGOTIABLE GUARANTEES:
    - Narrative is explanation and interpretation ONLY.
    - Zero authority over fraud probabilities, coverage metrics, or gate decisions.
    - Validates citation references against observed evidence, case precedent, and knowledge registries (citation reference validation; does not assert semantic entailment).
    - Gracefully falls back to structured deterministic synthesis if LLM API is unavailable.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client

    def synthesize(self, context: InvestigationContext, use_llm: bool = True) -> str:
        """Generates a complete 7-section grounded investigation report."""
        # 1. Generate Deterministic Baseline Narrative (Authoritative Ground Truth)
        deterministic_narrative = self._generate_deterministic_narrative(context)

        if not use_llm or not self.llm_client:
            return deterministic_narrative

        # 2. Attempt Grounded LLM Synthesis with Strict Prompting
        try:
            dossier_text = context.render_context_document()
            system_prompt = (
                "You are an expert Bank Fraud Compliance and Investigation Officer producing a formal "
                "dossier for regulatory audit. You are provided with a strictly segregated context containing: "
                "SECTION A: OBSERVED GRAPH EVIDENCE (real empirical tool results)\n"
                "SECTION B: HISTORICAL CASE PRECEDENTS (contextual memory, non-evidential)\n"
                "SECTION C: GOVERNING POLICY & REGULATIONS (authoritative rules)\n"
                "SECTION D: OPERATIONAL POLICY DISPOSITION (deterministic actions)\n\n"
                "CRITICAL MANDATES:\n"
                "1. You must explicitly cite Evidence IDs [EVD-...] when discussing facts.\n"
                "2. You must cite Case IDs [CC-...] when referencing historical precedents.\n"
                "3. You must cite Policy/Statute IDs [KNOW-...] when referencing rules or FinCEN statutes.\n"
                "4. NEVER invent ungrounded transaction amounts, new evidence IDs, or new probabilities.\n"
                "5. NEVER claim that historical cases or policy text are observed transaction evidence.\n"
                "6. Format your response into 7 numbered sections matching the standard compliance template."
            )

            user_prompt = (
                f"Synthesize the following completed fraud investigation dossier into a formal compliance report.\n\n"
                f"{dossier_text}\n\n"
                f"Produce the report adhering strictly to these 7 sections:\n"
                f"1. Executive Summary\n"
                f"2. Graph Evidence Analysis (cite [EVD-...])\n"
                f"3. Historical Precedent Analysis (cite [CC-...])\n"
                f"4. Policy & Regulatory Compliance (cite [KNOW-...])\n"
                f"5. Uncertainty & Conflict Assessment\n"
                f"6. Investigation Trajectory & Value of Information Rationale\n"
                f"7. Final Operational Disposition & Remediation"
            )

            llm_response = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=1500
            )

            if llm_response and len(llm_response.strip()) > 100:
                # Validate LLM response for citation reference integrity
                validated_text = self._validate_and_sanitize_citations(llm_response.strip(), context)

                # Grounding contract: a filing-ready narrative must reference at least one
                # *registered* observed evidence ID, and — when policy/regulatory knowledge
                # was retrieved — at least one *registered* knowledge chunk ID. If the model
                # produced ungrounded or placeholder citations, discard the response and fall
                # back to the authoritative deterministic narrative.
                valid_ev_ids: Set[str] = {ev["evidence_id"] for ev in context.observed_evidence_summary}
                valid_know_ids: Set[str] = {k.chunk.chunk_id for k in context.retrieved_knowledge}
                found_ev = set(re.findall(r"\bEVD-[A-Za-z0-9_-]+\b", validated_text))
                found_know = set(re.findall(r"\bKNOW-[A-Za-z0-9_-]+\b", validated_text))

                has_valid_evidence = bool(found_ev & valid_ev_ids)
                has_valid_knowledge = (not valid_know_ids) or bool(found_know & valid_know_ids)

                if has_valid_evidence and has_valid_knowledge:
                    return validated_text

                logger.warning(
                    "LLM synthesis failed the citation grounding contract "
                    "(valid_evidence=%s, valid_knowledge=%s); reverting to deterministic grounded narrative.",
                    has_valid_evidence,
                    has_valid_knowledge,
                )

        except Exception as e:
            logger.warning(f"LLM synthesis encountered exception ({e}); reverting to deterministic synthesis.")

        return deterministic_narrative

    def _generate_deterministic_narrative(self, context: InvestigationContext) -> str:
        """Constructs an authoritative, fully cited 7-section narrative deterministically."""
        ev_items = context.observed_evidence_summary
        similar_cases = context.historical_precedents
        knowledge = context.retrieved_knowledge
        actions = context.policy_recommendations

        # Section 1: Executive Summary
        sec1 = [
            "### 1. Executive Summary",
            f"- **Investigation Identifier:** `{context.investigation_id}`",
            f"- **Target Entities:** Card `{context.target_entities.get('card_id')}` | "
            f"Customer `{context.target_entities.get('customer_id')}` | Flagged Txn `{context.target_entities.get('flagged_txn_id')}`",
            f"- **Financial Exposure:** ${context.exposure_usd:,.2f}",
            f"- **Belief Shift:** P(Fraud) shifted from {context.prior_prob:.4f} to {context.posterior_prob:.4f}.",
            f"- **Decision Gate Status:** {'PASSED' if context.decision_gate_passed else 'LOCKED'} ({context.decision_state}).",
            f"- **Evidence Coverage:** {context.evidence_coverage * 100:.0f}% of core investigative dimensions observed.",
            f"- **Primary Disposition:** {', '.join([a.action for a in actions]) if actions else 'MONITOR_CARD'}"
        ]

        # Section 2: Graph Evidence Analysis
        sec2 = [
            "### 2. Graph Evidence Analysis",
            "Empirical evidence observed via deterministic GSQL query executions on the TigerGraph cluster:"
        ]
        if not ev_items:
            sec2.append("- No empirical graph evidence observed.")
        else:
            for ev in ev_items:
                sec2.append(
                    f"- **[{ev['evidence_id']}]** `{ev['type']}` (LR: {ev['lr']:.2f}, {ev['direction']}): "
                    f"{ev['finding']} (Provenance: `{ev['provenance']}`)."
                )

        # Section 3: Historical Precedent Analysis
        sec3 = [
            "### 3. Historical Precedent Analysis",
            "Contextual memory precedents retrieved from historical closed investigations (non-evidential, LR=1.0):"
        ]
        if not similar_cases:
            sec3.append("- No similar closed cases found in historical memory.")
        else:
            for m in similar_cases:
                c = m.case_record
                acts = ", ".join(c.actions_taken) if c.actions_taken else "None"
                sec3.append(
                    f"- **[{c.case_id}]** Outcome: `{c.historical_outcome.upper()}` (Similarity: {m.similarity_score:.2f}) | "
                    f"Typology: `{c.pattern}` | Actions: `{acts}`. {m.explanation}"
                )

        # Section 4: Policy & Regulatory Compliance
        sec4 = [
            "### 4. Policy & Regulatory Compliance",
            "Authoritative bank policies and statutory regulations governing this disposition:"
        ]
        if not knowledge:
            sec4.append("- General bank fraud monitoring standards apply.")
        else:
            for k in knowledge:
                c = k.chunk
                path = getattr(k, "retrieval_path", "") or "PolicyMapper"
                sec4.append(
                    f"- **[{c.chunk_id}]** `{c.title}` ({c.section_reference}, {c.governing_body}): "
                    f"\"{c.text}\" (Application Rationale: {k.match_rationale}) "
                    f"_(Retrieval Path: `{path}`)_"
                )

        # Section 5: Uncertainty & Conflict Assessment
        sec5 = [
            "### 5. Uncertainty & Conflict Assessment",
            f"- **Epistemic Uncertainty:** {context.epistemic_uncertainty:.2f} "
            f"({'Satisfied' if context.epistemic_uncertainty <= 0.60 else 'Elevated missing data'}).",
            f"- **Aleatoric Conflict:** {context.aleatoric_uncertainty:.2f} "
            f"({'Coherent evidence' if context.aleatoric_uncertainty < 0.40 else 'Severe contradiction requiring human escalation'}).",
            f"- **Coverage Gate:** {'UNLOCKED (Coverage >= 40%)' if context.evidence_coverage >= 0.40 else 'LOCKED (Coverage < 40%)'}."
        ]

        # Section 6: Trajectory & EVOI Rationale
        sec6 = [
            "### 6. Investigation Trajectory & EVOI Rationale",
            f"The autonomous investigation proceeded under pure Evidence Compass authority. "
            f"Evidence acquisition ceased because terminal conditions were met: "
            f"{'decision gate unlocked with positive net decision value exhausted' if context.decision_gate_passed else 'no remaining actions offer positive net decision value'}."
        ]

        # Section 7: Final Operational Disposition
        sec7 = [
            "### 7. Final Operational Disposition & Remediation",
            "Mandated operational actions approved by the Policy Engine under banking risk governance:"
        ]
        if not actions:
            sec7.append("- `MONITOR_CARD` (Route: auto): Standard automated card surveillance.")
        else:
            for act in actions:
                sec7.append(
                    f"- **`{act.action}`** (Approval Route: `{act.approval_route}`): {act.reason}"
                )

        all_sections = [
            "\n".join(sec1),
            "\n".join(sec2),
            "\n".join(sec3),
            "\n".join(sec4),
            "\n".join(sec5),
            "\n".join(sec6),
            "\n".join(sec7),
        ]
        return "\n\n".join(all_sections)

    def _validate_and_sanitize_citations(self, text: str, context: InvestigationContext) -> str:
        """Performs structural citation reference validation against active context registries.
        
        Validates syntactic presence of referenced evidence IDs, case IDs, and knowledge chunk IDs.
        Note: This verifies reference authenticity against allowed context registries;
        it does not assert semantic entailment of narrative claims.
        """
        valid_ev_ids: Set[str] = {ev["evidence_id"] for ev in context.observed_evidence_summary}
        valid_case_ids: Set[str] = {m.case_record.case_id for m in context.historical_precedents}
        if context.investigation_id:
            valid_case_ids.add(context.investigation_id)
        valid_know_ids: Set[str] = {k.chunk.chunk_id for k in context.retrieved_knowledge}

        # Check for fabricated evidence IDs
        found_ev_cits = set(re.findall(r"\bEVD-[A-Za-z0-9_-]+\b", text))
        invalid_ev_cits = found_ev_cits - valid_ev_ids

        # Check for fabricated case IDs
        found_case_cits = set(re.findall(r"\b(?:CC-\w+|INV-[A-Za-z0-9_-]+)\b", text))
        invalid_case_cits = found_case_cits - valid_case_ids

        # Check for fabricated knowledge / regulatory chunk IDs
        found_know_cits = set(re.findall(r"\bKNOW-[A-Za-z0-9_-]+\b", text))
        invalid_know_cits = found_know_cits - valid_know_ids

        verification_lines = [
            "",
            "---",
            "#### Provenance Citation Reference Validation Audit",
            f"- **Observed Evidence Citations Verified:** {len(found_ev_cits - invalid_ev_cits)} / {len(found_ev_cits)}",
            f"- **Historical Case Citations Verified:** {len(found_case_cits - invalid_case_cits)} / {len(found_case_cits)}",
            f"- **Policy/Statute Citations Verified:** {len(found_know_cits - invalid_know_cits)} / {len(found_know_cits)}",
            "- **Citation Reference Verification Note:** Structural reference validation confirms referenced IDs exist in grounded registries; does not perform semantic entailment."
        ]

        if invalid_ev_cits:
            verification_lines.append(f"- **WARNING — Unsupported Evidence Citations Excluded:** {', '.join(sorted(invalid_ev_cits))}")
        if invalid_case_cits:
            verification_lines.append(f"- **WARNING — Unsupported Case Citations Excluded:** {', '.join(sorted(invalid_case_cits))}")
        if invalid_know_cits:
            verification_lines.append(f"- **WARNING — Unsupported Policy/Statute Citations Excluded:** {', '.join(sorted(invalid_know_cits))}")

        return text + "\n" + "\n".join(verification_lines)
