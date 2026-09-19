from typing import List, Dict, Any, Optional, Tuple

from src.belief.state import InvestigationState
from src.memory.models import CaseMemoryRecord, SimilarCaseMatch, CaseSimilarityDimensions
from src.memory.store import CaseMemoryStore


class SimilarCaseRetriever:
    """Contextual historical case memory retriever for active investigations.
    
    Computes multi-attribute structural similarity between an active investigation
    and closed cases from memory.
    
    CRITICAL NON-NEGOTIABLE GUARANTEES:
    - Similarity matches are CONTEXTUAL PRECEDENT ONLY.
    - Never generates EvidenceItems.
    - Never assigns or scales Likelihood Ratios (LR).
    - Never mutates fraud probability or uncertainty.
    - Never counts toward the five core evidence families.
    """

    def __init__(self, store: CaseMemoryStore):
        self.store = store

    def retrieve_similar_cases(
        self,
        state: Optional[InvestigationState] = None,
        target_entities: Optional[Dict[str, Any]] = None,
        pattern: Optional[str] = None,
        exposure_usd: Optional[float] = None,
        top_k: int = 3,
        effective_timestamp: Optional[str] = None
    ) -> List[SimilarCaseMatch]:
        """Retrieves ranked top-k contextual precedent cases with structural similarity explanations."""
        entities = target_entities or (state.target_entities if state else {})
        curr_card = str(entities.get("card_id") or "")
        curr_cust = str(entities.get("customer_id") or "")
        curr_pattern = (pattern or (state.secondary_typology if state else "") or "").lower().strip()
        curr_exposure = float(exposure_usd if exposure_usd is not None else 0.0)

        # Collect candidate cases from store
        candidates: Dict[str, CaseMemoryRecord] = {}

        # 1. Match on same card or same customer
        if curr_card:
            for c in self.store.get_by_card(curr_card):
                candidates[c.case_id] = c
        if curr_cust:
            for c in self.store.get_by_customer(curr_cust):
                candidates[c.case_id] = c

        # 2. Match on pattern
        if curr_pattern and curr_pattern != "unknown":
            for c in self.store.get_by_pattern(curr_pattern):
                candidates[c.case_id] = c
            # Also check normalized pattern variants
            normalized_variants = {
                "card_testing": ["card_testing", "card_not_present_fraud"],
                "shared_device": ["card_not_present_new_device", "account_takeover"],
                "out_of_region": ["out_of_region_use"],
                "account_takeover": ["account_takeover", "card_not_present_new_device"],
            }
            for key, variants in normalized_variants.items():
                if key in curr_pattern:
                    for v in variants:
                        for c in self.store.get_by_pattern(v):
                            candidates[c.case_id] = c

        # If candidates are too few, sample relevant cases across all
        if len(candidates) < top_k:
            for c in self.store.all_cases()[:50]:
                candidates[c.case_id] = c

        # Filter & score candidates
        active_id = state.investigation_id if state else str(entities.get("investigation_id") or entities.get("case_id") or "")
        active_txn = str(entities.get("flagged_txn_id") or (state.trigger.get("flagged_txn_id") if state and state.trigger else "") or "")
        cutoff = effective_timestamp or (state.trigger.get("timestamp") if state and state.trigger else None)

        curr_evidence_fams = [item.evidence_type.value for item in state.evidence_items] if state and hasattr(state, "evidence_items") else []
        curr_has_device_ring = any(
            t in curr_evidence_fams for t in ["SHARED_DEVICE_RING", "PROXY_DETECTED", "CNP_NEW_DEVICE"]
        )

        matches: List[SimilarCaseMatch] = []
        for c in candidates.values():
            # 1. Never retrieve current ongoing case as its own precedent (zero case-memory contamination)
            if active_id and c.case_id == active_id:
                continue

            # 2. Never retrieve a historical record matching the exact transaction currently being investigated (zero label leakage)
            if active_txn and (c.first_fraud_txn_id == active_txn or active_txn in c.txn_ids):
                continue

            # 3. Deterministic temporal boundary: Exclude cases created/closed after the effective cutoff timestamp
            if cutoff:
                ts = c.closed_at or c.opened_at
                if not ts or not CaseMemoryStore._is_timestamp_on_or_before(ts, cutoff):
                    continue

            sim_score, dims, shared_feats, explanation = self._score_case_similarity(
                curr_card=curr_card,
                curr_cust=curr_cust,
                curr_pattern=curr_pattern,
                curr_exposure=curr_exposure,
                case=c,
                curr_evidence_families=curr_evidence_fams,
                curr_has_device_ring=curr_has_device_ring
            )

            elig_reason = (
                f"Historical case closed at {c.closed_at or 'historical baseline'}"
                + (f" on/before evaluation cutoff {cutoff}" if cutoff else "")
                + f"; matched on {len(shared_feats)} active scoring dimensions."
            )

            matches.append(SimilarCaseMatch(
                case_record=c,
                similarity_score=sim_score,
                dimensions=dims,
                shared_features=shared_feats,
                explanation=explanation,
                historical_timestamp=c.closed_at,
                eligibility_reason=elig_reason
            ))

        # Sort by composite similarity descending
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches[:top_k]

    def _score_case_similarity(
        self,
        curr_card: str,
        curr_cust: str,
        curr_pattern: str,
        curr_exposure: float,
        case: CaseMemoryRecord,
        curr_evidence_families: Optional[List[str]] = None,
        curr_has_device_ring: bool = False
    ) -> Tuple[float, CaseSimilarityDimensions, List[str], str]:
        """Evaluates dimensional similarity between current investigation and historical record.
        
        CRITICAL INTEGRITY INVARIANT:
        Every feature mentioned in the shared list and explanation corresponds 1-to-1 with a
        non-zero active scoring component in the deterministic formula.
        """
        same_card = bool(curr_card and case.card_id and curr_card.lower() == case.card_id.lower())
        same_cust = bool(curr_cust and case.customer_id and curr_cust.lower() == case.customer_id.lower())
        
        # Pattern match logic
        case_pat = case.pattern.lower().strip()
        same_pat = False
        if curr_pattern and case_pat:
            if curr_pattern in case_pat or case_pat in curr_pattern:
                same_pat = True
            elif "device" in curr_pattern and "device" in case_pat:
                same_pat = True
            elif "region" in curr_pattern and "region" in case_pat:
                same_pat = True
            elif "testing" in curr_pattern and "testing" in case_pat:
                same_pat = True

        # Exposure proximity [0.0 - 1.0]
        max_exp = max(curr_exposure, case.exposure_usd, 1.0)
        exp_diff = abs(curr_exposure - case.exposure_usd)
        exp_prox = max(0.0, 1.0 - (exp_diff / max_exp))

        # Shared device relationship
        shared_device = False
        if (curr_has_device_ring or "device" in curr_pattern) and (bool(case.connected_card_ids) or "device" in case_pat):
            shared_device = True
        elif bool(case.connected_card_ids):
            shared_device = True

        # Evidence families overlap
        curr_fams_set = set(curr_evidence_families or [])
        case_fams_set = set(case.evidence_families_observed or [])
        overlapping_fams = sorted(list(curr_fams_set.intersection(case_fams_set)))

        # Composite score weighting & 1-to-1 feature tracking
        # Each feature in shared MUST correspond directly to a non-zero scoring input!
        score = 0.0
        shared = []

        if same_card:
            score += 0.30
            shared.append(f"Identical card ID ({case.card_id})")

        if same_cust:
            score += 0.20
            shared.append(f"Identical customer ID ({case.customer_id})")

        if same_pat:
            score += 0.25
            shared.append(f"Matching fraud typology pattern ('{case.pattern}')")

        if exp_prox >= 0.50:
            exp_contrib = 0.15 * exp_prox
            score += exp_contrib
            shared.append(f"Comparable dollar exposure (${case.exposure_usd:.2f} vs ${curr_exposure:.2f}, proximity {exp_prox*100:.0f}%)")

        if shared_device:
            score += 0.05
            shared.append("Shared device infrastructure / multi-card ring topology")

        if overlapping_fams:
            fam_ratio = len(overlapping_fams) / max(len(curr_fams_set), 1)
            score += 0.05 * fam_ratio
            shared.append(f"Overlapping evidence families ({', '.join(overlapping_fams)})")

        # Bounded [0.05 - 1.0]
        final_score = round(min(1.0, max(0.05, score)), 4)

        dims = CaseSimilarityDimensions(
            same_customer=same_cust,
            same_card=same_card,
            same_pattern=same_pat,
            connected_card_overlap=bool(case.connected_card_ids),
            exposure_proximity=round(exp_prox, 4),
            velocity_similarity=round(min(1.0, 1.0 / max(case.n_txns, 1)), 4),
            textual_similarity=0.5 if same_pat else 0.1
        )

        actions_str = ", ".join(case.actions_taken) if case.actions_taken else "None"
        decisive_str = f" Historically decisive evidence: {case.decisive_evidence}." if case.decisive_evidence else ""
        explanation = (
            f"Precedent Case {case.case_id} ({case.historical_outcome.upper()}): "
            f"Shares [{'; '.join(shared) if shared else 'baseline topology'}]. "
            f"Historical disposition resulted in [{actions_str}].{decisive_str} "
            f"Role: Contextual precedent only (LR=1.0, non-evidential)."
        )

        return final_score, dims, shared, explanation
