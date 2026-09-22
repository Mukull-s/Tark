import json
import os
import uuid
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Set

from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceItem, EvidenceType, EvidenceDirection
from src.belief.calibration import (
    CalibrationClassification,
    EvidenceFamily,
    LikelihoodRatioMetadata,
    PriorProfile,
    PRIOR_REGISTRY,
    LIKELIHOOD_REGISTRY,
    get_calibrated_lr,
    get_model_score_lr
)
from src.belief.state import (
    WorldHypothesis,
    HypothesisType,
    HypothesisStatus,
    HypothesisState,
    ContradictionItem,
    MissingInfoItem,
    UncertaintyState,
    ReasoningStep,
    DecisionState,
    InvestigationState
)

# Minimum evidence coverage threshold for automated final decision (applicable dimensions ratio)
MIN_DECISION_COVERAGE = 0.40

# Core investigative dimensions (canonical superset across all trigger channels)
CORE_INVESTIGATIVE_FAMILIES = [
    EvidenceFamily.DEVICE_INFRASTRUCTURE,
    EvidenceFamily.TRANSACTION_VELOCITY,
    EvidenceFamily.BEHAVIORAL_BASELINE,
    EvidenceFamily.CUSTOMER_DISPUTE,
    EvidenceFamily.MODEL_SCORE
]

# ---------------------------------------------------------------------------
# Per-trigger applicable investigative checklist
# ---------------------------------------------------------------------------
# The coverage denominator is NOT a fixed 5. It is the set of dimensions that are
# actually resolvable and decision-relevant for the trigger channel that opened
# the case:
#   * risk_score        -> all core dimensions incl. model score + customer dispute
#   * customer_report   -> dispute is already established, so the applicable set is
#                          device / velocity / baseline / dispute (4)
#   * analyst_request   -> human referral with no model score or dispute; the
#                          applicable corroboration set is device / velocity /
#                          baseline (3)
# Unknown/missing trigger types fall back to the canonical superset of 5 to
# preserve backward compatibility.
TRIGGER_APPLICABLE_FAMILIES: Dict[str, List[EvidenceFamily]] = {
    "risk_score": [
        EvidenceFamily.DEVICE_INFRASTRUCTURE,
        EvidenceFamily.TRANSACTION_VELOCITY,
        EvidenceFamily.BEHAVIORAL_BASELINE,
        EvidenceFamily.CUSTOMER_DISPUTE,
        EvidenceFamily.MODEL_SCORE,
    ],
    "customer_report": [
        EvidenceFamily.DEVICE_INFRASTRUCTURE,
        EvidenceFamily.TRANSACTION_VELOCITY,
        EvidenceFamily.BEHAVIORAL_BASELINE,
        EvidenceFamily.CUSTOMER_DISPUTE,
    ],
    "analyst_request": [
        EvidenceFamily.DEVICE_INFRASTRUCTURE,
        EvidenceFamily.TRANSACTION_VELOCITY,
        EvidenceFamily.BEHAVIORAL_BASELINE,
    ],
}

TRIGGER_TYPE_ALIASES = {
    "inbound_dispute": "customer_report",
    "cardholder_report": "customer_report",
    "analyst_referral": "analyst_request",
    "manual_review": "analyst_request",
    "in_flight_auth": "risk_score",
    "realtime_checkout": "risk_score",
}


def resolve_applicable_families(trigger_type: Optional[str]) -> List[EvidenceFamily]:
    """Resolves the per-trigger applicable investigative dimension checklist."""
    key = (trigger_type or "").strip().lower()
    key = TRIGGER_TYPE_ALIASES.get(key, key)
    return list(TRIGGER_APPLICABLE_FAMILIES.get(key, CORE_INVESTIGATIVE_FAMILIES))

class BeliefEngine:
    """Tark Phase 3.1 Belief & Uncertainty Reasoning Engine.
    
    Consumes EvidenceLedger and produces a serializable, uncertainty-aware
    InvestigationState with explicit world hypotheses (FRAUD and LEGITIMATE only),
    deterministic decision gating, family correlation discounting, and machine-readable reasoning traces.
    """
    
    def __init__(self, lr_table_path: Optional[str] = None):
        if lr_table_path is None:
            lr_table_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "analysis",
                "lr_table.json"
            )
        
        if os.path.exists(lr_table_path):
            with open(lr_table_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "prior": {"p_fraud": 0.8383, "log_odds": 1.6454},
                "evidence_likelihood_ratios": {}
            }
        
        # Default base prior from config (representing ALERT_CONDITIONED)
        self.base_prior_log_odds = self.config["prior"].get("log_odds", 1.6454)

    def log_odds_to_prob(self, log_odds: float) -> float:
        """Sigmoid function converting log-odds to probability with numerical clipping."""
        clipped = max(min(log_odds, 30.0), -30.0)
        return float(1.0 / (1.0 + np.exp(-clipped)))

    def prob_to_log_odds(self, prob: float) -> float:
        """Logit function converting probability to log-odds with clipping."""
        p = max(min(prob, 0.9999), 0.0001)
        return float(np.log(p / (1.0 - p)))

    def resolve_evidence_family(self, item: EvidenceItem) -> Tuple[EvidenceFamily, float]:
        """Resolves the semantic evidence family and maximum allowable family log-LR ceiling."""
        meta = get_calibrated_lr(item.evidence_type.value)
        if meta:
            return meta.family, meta.family_ceiling_log_lr
        
        # Fallback mapping
        type_str = item.evidence_type.value.upper()
        if "DEVICE" in type_str or "PROXY" in type_str:
            return EvidenceFamily.DEVICE_INFRASTRUCTURE, 4.0
        elif "VELOCITY" in type_str or "SEQUENCE" in type_str:
            return EvidenceFamily.TRANSACTION_VELOCITY, 4.5
        elif "CUSTOMER" in type_str or "DISPUTE" in type_str:
            return EvidenceFamily.CUSTOMER_DISPUTE, 5.0
        elif "BASELINE" in type_str or "RECURRING" in type_str:
            return EvidenceFamily.BEHAVIORAL_BASELINE, 3.5
        elif "REGION" in type_str or "LOCATION" in type_str:
            return EvidenceFamily.GEOGRAPHIC_LOCATION, 2.5
        elif "SCORE" in type_str:
            return EvidenceFamily.MODEL_SCORE, 3.0
        else:
            return EvidenceFamily.CASE_HISTORY, 3.0

    def calculate_family_weight(self, count_in_family: int) -> float:
        """Calculates defensible diminishing returns weight for intra-family evidence correlation.
        
        Mathematical Formulation:
        w_1 = 1.0   (Primary independent signal)
        w_2 = 0.5   (Secondary correlated observation of same underlying event)
        w_k = 0.25  (Further observations yield sharply diminishing informational value)
        """
        if count_in_family == 0:
            return 1.0
        elif count_in_family == 1:
            return 0.5
        else:
            return 0.25

    def evaluate_investigation(
        self,
        investigation_id: str,
        trigger: Dict[str, Any],
        target_entities: Dict[str, str],
        ledger: EvidenceLedger,
        prior_profile: PriorProfile = PriorProfile.ALERT_CONDITIONED,
        prior_p: Optional[float] = None
    ) -> InvestigationState:
        """Evaluates an investigation end-to-end, producing a complete InvestigationState.
        
        Enforces:
        1. World hypotheses: FRAUD and LEGITIMATE only (sum of probabilities = 1.0).
        2. Deduplication of identical evidence items.
        3. Semantic evidence family grouping and diminishing returns.
        4. Family log-LR ceilings to prevent correlated inflation.
        5. Contradiction tracking (inculpatory vs exculpatory).
        6. Explicit handling of DATA_OUT_OF_SCOPE and GRAPH_QUERY_FAILURE (zero log-odds shift).
        7. Neutral handling of NO_MATCH (absence of pattern != proof of legitimacy).
        8. Deterministic Decision Gating Contract preventing premature final decisions.
        9. Full machine-readable reasoning trace.
        """
        # 1. Prior Resolution
        if prior_p is not None:
            initial_log_odds = self.prob_to_log_odds(prior_p)
            prior_notes = f"Explicit override prior: {prior_p:.4f}"
        else:
            profile_data = PRIOR_REGISTRY.get(prior_profile, PRIOR_REGISTRY[PriorProfile.ALERT_CONDITIONED])
            initial_log_odds = profile_data["log_odds"]
            prior_notes = f"{prior_profile.value} ({profile_data['source']})"

        initial_prob = self.log_odds_to_prob(initial_log_odds)
        
        current_log_odds = initial_log_odds
        current_prob = initial_prob
        step_idx = 1
        reasoning_history: List[ReasoningStep] = [
            ReasoningStep(
                step=step_idx,
                event="PRIOR_INITIALIZED",
                prior_log_odds=round(initial_log_odds, 4),
                posterior_log_odds=round(initial_log_odds, 4),
                posterior_prob=round(initial_prob, 4),
                rationale=f"Initialized prior log-odds to {initial_log_odds:.4f} (p={initial_prob:.4f}) via {prior_notes}."
            )
        ]

        # 2. Tracking structures
        seen_item_keys: Set[str] = set()
        family_counts: Dict[EvidenceFamily, int] = {}
        family_cumulative_log_lr: Dict[EvidenceFamily, float] = {}
        
        inculpatory_ids: List[str] = []
        exculpatory_ids: List[str] = []
        total_positive_log_lr = 0.0
        total_negative_log_lr = 0.0
        
        missing_information: List[MissingInfoItem] = []
        dimensions_observed: Set[EvidenceFamily] = set()
        probed_families: Set[EvidenceFamily] = set()
        unavailable_dimensions: Set[str] = set()
        informative_families: Set[EvidenceFamily] = set()
        out_of_scope_count = 0
        has_conclusive_dispute = False

        # 3. Process Ledger Items
        for item in ledger.items:
            step_idx += 1
            
            # Scope check: Is this evidence reporting DATA_OUT_OF_SCOPE?
            is_out_of_scope = (
                item.value == "DATA_OUT_OF_SCOPE" or 
                "DATA_OUT_OF_SCOPE" in str(item.finding) or 
                item.details.get("scope_status") == "DATA_OUT_OF_SCOPE"
            )
            
            # Query Failure check: Did the query fail/timeout?
            is_query_failure = (
                item.value == "GRAPH_QUERY_FAILURE" or 
                "GRAPH_QUERY_FAILURE" in str(item.finding) or 
                "QUERY_FAILED" in str(item.finding) or
                item.details.get("scope_status") == "GRAPH_QUERY_FAILURE"
            )

            # Pattern No-Match check: Pattern not observed within valid scope
            is_no_match = (
                item.value == "NO_MATCH" or 
                "NO_MATCH" in str(item.finding) or
                item.details.get("scope_status") == "NO_MATCH"
            )
            
            if is_out_of_scope or is_query_failure:
                reason_code = "GRAPH_QUERY_FAILURE" if is_query_failure else "DATA_OUT_OF_SCOPE"
                severity = "HIGH" if is_query_failure else "MEDIUM"
                out_of_scope_count += 1
                
                missing_id = f"MIS-{uuid.uuid4().hex[:6].upper()}"
                dimension_name = item.evidence_type.value
                unavailable_dimensions.add(dimension_name)
                target_ent = item.target_entity or target_entities.get("card_id") or "TARGET_ENTITY"
                
                missing_item = MissingInfoItem(
                    missing_id=missing_id,
                    dimension=dimension_name,
                    entity=target_ent,
                    reason=reason_code,
                    impact_severity=severity,
                    actionable_query=item.graph_query
                )
                missing_information.append(missing_item)
                
                reasoning_history.append(ReasoningStep(
                    step=step_idx,
                    event=f"{reason_code}_RECORDED",
                    evidence_id=item.evidence_id,
                    evidence_type=item.evidence_type.value,
                    raw_lr=1.0,
                    discount_factor=0.0,
                    effective_log_lr=0.0,
                    prior_log_odds=round(current_log_odds, 4),
                    posterior_log_odds=round(current_log_odds, 4),
                    posterior_prob=round(current_prob, 4),
                    uncertainty_delta=0.1,
                    rationale=(
                        f"Query {item.graph_query or item.source} reported {reason_code}. "
                        "Treated as unobserved/unavailable data horizon; zero log-odds shift."
                    )
                ))
                continue

            if is_no_match:
                # Required Change 4: Absence of an observed fraud pattern is NOT automatically exculpatory.
                # Default to neutral baseline (LR=1.0, log-LR=0.0) unless explicitly justified.
                #
                # A graph query that executed and returned no match is a *probed*
                # dimension: the investigation has resolved that dimension (ruling
                # out that fraud pattern) even though the finding is belief-neutral.
                # Probed dimensions reduce epistemic uncertainty without inflating
                # likelihood ratios or evidence coverage.
                if (item.source or "").startswith("tigergraph_query:"):
                    probed_family, _ = self.resolve_evidence_family(item)
                    probed_families.add(probed_family)
                #
                # Customer-communication unavailability is surfaced as explicit missing information:
                # the evidence is genuinely unobserved (not exonerating), so it must keep the gate
                # conservative while contributing zero log-odds.
                if item.evidence_type == EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE:
                    missing_information.append(MissingInfoItem(
                        missing_id=f"MIS-{uuid.uuid4().hex[:6].upper()}",
                        dimension=EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE.value,
                        entity=item.target_entity or target_entities.get("customer_id") or "CARDHOLDER",
                        reason="CUSTOMER_COMMUNICATION_UNAVAILABLE",
                        impact_severity="MEDIUM",
                        actionable_query=item.graph_query
                    ))
                    unavailable_dimensions.add(EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE.value)

                reasoning_history.append(ReasoningStep(
                    step=step_idx,
                    event="NO_MATCH_NEUTRAL_RECORDED",
                    evidence_id=item.evidence_id,
                    evidence_type=item.evidence_type.value,
                    raw_lr=1.0,
                    discount_factor=1.0,
                    effective_log_lr=0.0,
                    prior_log_odds=round(current_log_odds, 4),
                    posterior_log_odds=round(current_log_odds, 4),
                    posterior_prob=round(current_prob, 4),
                    rationale=(
                        f"Queried pattern {item.evidence_type.value} was not observed within available query scope. "
                        "Treated as neutral absence of pattern (LR=1.0, log-LR=0.0); does not constitute exculpatory proof."
                    )
                ))
                continue

            # Check for Deduplication
            # Deduplicate by evidence_id or by exact (evidence_type, sorted transaction ids, finding)
            txn_key = tuple(sorted(item.supporting_transaction_ids or []))
            dedup_key = f"{item.evidence_type.value}:{txn_key}:{item.finding}"
            
            if item.evidence_id in seen_item_keys or dedup_key in seen_item_keys:
                reasoning_history.append(ReasoningStep(
                    step=step_idx,
                    event="DUPLICATE_EVIDENCE_IGNORED",
                    evidence_id=item.evidence_id,
                    evidence_type=item.evidence_type.value,
                    raw_lr=item.lr,
                    discount_factor=0.0,
                    effective_log_lr=0.0,
                    prior_log_odds=round(current_log_odds, 4),
                    posterior_log_odds=round(current_log_odds, 4),
                    posterior_prob=round(current_prob, 4),
                    rationale="Duplicate evidence item observed. Suppressed to prevent artificial belief inflation."
                ))
                continue
            
            seen_item_keys.add(item.evidence_id)
            seen_item_keys.add(dedup_key)

            # Family resolution & correlation discounting
            family, family_ceiling = self.resolve_evidence_family(item)
            dimensions_observed.add(family)
            if family == EvidenceFamily.CUSTOMER_DISPUTE and item.evidence_type in [EvidenceType.CUSTOMER_DENIAL, EvidenceType.CUSTOMER_CONFIRMATION]:
                has_conclusive_dispute = True

            current_family_count = family_counts.get(family, 0)
            current_family_log_lr = family_cumulative_log_lr.get(family, 0.0)
            
            discount = self.calculate_family_weight(current_family_count)
            desired_log_lr = item.log_lr * discount
            
            # Enforce family ceiling
            if desired_log_lr >= 0:
                available_headroom = max(0.0, family_ceiling - current_family_log_lr)
                effective_log_lr = min(desired_log_lr, available_headroom)
            else:
                available_headroom = min(0.0, -family_ceiling - current_family_log_lr)
                effective_log_lr = max(desired_log_lr, available_headroom)

            # Update family totals
            family_counts[family] = current_family_count + 1
            family_cumulative_log_lr[family] = current_family_log_lr + effective_log_lr

            # Track families that contributed a non-zero evidentiary shift.
            # These are the "informative" dimensions used by the corroboration contract.
            if abs(effective_log_lr) > 1e-9:
                informative_families.add(family)

            # Contradiction tracking
            if effective_log_lr > 0:
                inculpatory_ids.append(item.evidence_id)
                total_positive_log_lr += effective_log_lr
            elif effective_log_lr < 0:
                exculpatory_ids.append(item.evidence_id)
                total_negative_log_lr += abs(effective_log_lr)

            # Update belief state
            prior_lo = current_log_odds
            current_log_odds += effective_log_lr
            current_prob = self.log_odds_to_prob(current_log_odds)

            reasoning_history.append(ReasoningStep(
                step=step_idx,
                event="EVIDENCE_EVALUATED",
                evidence_id=item.evidence_id,
                evidence_type=item.evidence_type.value,
                family=family.value,
                raw_lr=round(item.lr, 4),
                discount_factor=discount,
                effective_log_lr=round(effective_log_lr, 4),
                prior_log_odds=round(prior_lo, 4),
                posterior_log_odds=round(current_log_odds, 4),
                posterior_prob=round(current_prob, 4),
                rationale=(
                    f"Applied {item.evidence_type.value} from family {family.value} "
                    f"(raw LR={item.lr}, discount={discount:.2f}, effective log-LR={effective_log_lr:.4f}). "
                    f"Family cumulative log-LR is now {family_cumulative_log_lr[family]:.4f}/{family_ceiling}."
                )
            ))

        # 4. Analyze Contradictions
        contradictions: List[ContradictionItem] = []
        conflict_magnitude = 0.0
        if total_positive_log_lr >= 1.5 and total_negative_log_lr >= 1.5:
            total_evidence_weight = total_positive_log_lr + total_negative_log_lr
            conflict_magnitude = round(2.0 * min(total_positive_log_lr, total_negative_log_lr) / total_evidence_weight, 4)
            contradictions.append(ContradictionItem(
                contradiction_id=f"CONTR-{uuid.uuid4().hex[:6].upper()}",
                description=(
                    f"Strong conflict detected between inculpatory (+{total_positive_log_lr:.2f}) "
                    f"and exculpatory (-{total_negative_log_lr:.2f}) evidence."
                ),
                inculpatory_evidence_ids=inculpatory_ids,
                exculpatory_evidence_ids=exculpatory_ids,
                conflict_magnitude=conflict_magnitude,
                resolution_status="UNRESOLVED"
            ))

        # 5. Compute Evidence Coverage & Multi-Dimensional Uncertainty
        # Coverage denominator is trigger-specific: the set of dimensions that are
        # resolvable and decision-relevant for the trigger channel that opened the
        # case (see TRIGGER_APPLICABLE_FAMILIES). This prevents a fixed /5 from
        # masking real differences between trigger channels.
        applicable_families = resolve_applicable_families(trigger.get("trigger_type"))
        applicable_set = set(applicable_families)
        observed_applicable = [fam for fam in applicable_families if fam in dimensions_observed]
        coverage_dict = {fam.value: (fam in dimensions_observed) for fam in applicable_families}
        observed_dim_names = [fam.value for fam in observed_applicable]
        missing_dim_names = [fam.value for fam in applicable_families if fam not in dimensions_observed]
        
        coverage_denominator = len(applicable_families) or 1
        evidence_coverage = round(len(observed_applicable) / coverage_denominator, 4)
        
        # Probed coverage: applicable dimensions actually investigated (informative
        # finding OR a graph query executed with no match). Ruling a dimension out
        # is tracked explicitly for explainability, but MUST NOT reduce the
        # epistemic gate or inflate coverage: absence of an observed pattern is not
        # proof, and using it to unlock a gate would contradict the NO_MATCH
        # neutrality contract.
        probed_core = (dimensions_observed | probed_families) & applicable_set
        probed_dim_names = sorted(fam.value for fam in probed_core)
        probed_coverage = round(len(probed_core) / coverage_denominator, 4)
        
        epistemic_uncertainty = round(max(0.0, min(1.0, (1.0 - evidence_coverage) + 0.1 * out_of_scope_count)), 4)
        aleatoric_uncertainty = conflict_magnitude
        
        # Confidence score incorporates coverage, aleatoric conflict, and epistemic gaps
        confidence_score = round(
            evidence_coverage * (1.0 - 0.7 * aleatoric_uncertainty) * (1.0 - 0.4 * epistemic_uncertainty),
            4
        )
        confidence_score = max(0.05, min(0.99, confidence_score))

        uncertainty_reasons: List[str] = []
        if evidence_coverage < MIN_DECISION_COVERAGE:
            uncertainty_reasons.append(
                f"Low evidence coverage ({evidence_coverage * 100:.0f}% of core dimensions observed; minimum {MIN_DECISION_COVERAGE * 100:.0f}% required for automated determination)."
            )
        if conflict_magnitude >= 0.40:
            uncertainty_reasons.append(f"Severe evidentiary conflict (conflict magnitude {conflict_magnitude:.2f} >= 0.40).")
        if out_of_scope_count > 0:
            uncertainty_reasons.append(f"{out_of_scope_count} graph query/queries returned DATA_OUT_OF_SCOPE or GRAPH_QUERY_FAILURE.")
        if not uncertainty_reasons:
            uncertainty_reasons.append("Evidence coverage and consistency satisfy automated decision requirements.")

        uncertainty_state = UncertaintyState(
            epistemic_uncertainty=epistemic_uncertainty,
            aleatoric_uncertainty=aleatoric_uncertainty,
            evidence_coverage=evidence_coverage,
            evidence_completeness=evidence_coverage,
            confidence_score=confidence_score,
            data_coverage=coverage_dict,
            observed_dimensions=observed_dim_names,
            applicable_dimensions=[fam.value for fam in applicable_families],
            probed_dimensions=probed_dim_names,
            probed_coverage=probed_coverage,
            missing_dimensions=missing_dim_names,
            unavailable_dimensions=list(unavailable_dimensions),
            uncertainty_reasons=uncertainty_reasons
        )

        # 6. Formalize World Hypotheses State (FRAUD and LEGITIMATE only)
        fraud_prob = round(current_prob, 4)
        legit_prob = round(1.0 - current_prob, 4)

        primary_hypothesis = WorldHypothesis.FRAUD if fraud_prob >= 0.50 else WorldHypothesis.LEGITIMATE

        # 7. Deterministic Decision Gating Contract (Required Changes 2 & 3)
        decision_gate_blocks: List[str] = []
        approval_requirements: List[str] = []

        # Corroboration contract for positive fraud determinations.
        # A high posterior driven by a single informative family (e.g. the
        # model risk score or a single graph signal alone) is not sufficient for
        # an automated confirmed_fraud decision. Require either a conclusive
        # cardholder dispute or corroboration across >=2 informative families.
        # This prevents a single overconfident signal from auto-frauding a case.
        corroborated_fraud = bool(
            has_conclusive_dispute
            or len(informative_families) >= 2
        )
        
        # Gate Rule 1: Aleatoric Conflict Gate
        if aleatoric_uncertainty >= 0.40:
            decision_gate_passed = False
            decision_gate_blocks.append(
                f"Severe evidentiary conflict (aleatoric conflict: {aleatoric_uncertainty:.2f} >= 0.40) between inculpatory and exculpatory findings."
            )
            decision_state = DecisionState.REQUIRES_HUMAN_APPROVAL
            approval_requirements.append("HUMAN_RISK_ANALYST")
            decision_rationale = (
                f"Strong fraud indicators conflict with strong exculpatory evidence "
                f"(conflict magnitude: {aleatoric_uncertainty:.2f}). Automated determination blocked; escalated for mandatory human review."
            )
        # Gate Rule 2: Material Evidence Coverage Gate
        elif evidence_coverage < MIN_DECISION_COVERAGE and not has_conclusive_dispute:
            decision_gate_passed = False
            decision_gate_blocks.append(
                f"Evidence coverage ({evidence_coverage:.2f}) is below minimum threshold ({MIN_DECISION_COVERAGE:.2f}). Corroborating investigative dimensions required."
            )
            decision_state = DecisionState.INSUFFICIENT_EVIDENCE
            decision_rationale = (
                f"I have evidence of suspicious behavior, but insufficient evidence to make a fraud determination "
                f"(evidence coverage: {evidence_coverage:.2f} < {MIN_DECISION_COVERAGE:.2f}, epistemic uncertainty: {epistemic_uncertainty:.2f})."
            )
        # Gate Rule 3: Epistemic Uncertainty Gate
        elif epistemic_uncertainty > 0.60:
            decision_gate_passed = False
            decision_gate_blocks.append(
                f"Epistemic uncertainty ({epistemic_uncertainty:.2f}) exceeds admissible limit (0.60) due to unobserved dimensions or out-of-scope queries."
            )
            decision_state = DecisionState.INSUFFICIENT_EVIDENCE
            decision_rationale = (
                f"Investigation has significant unobserved data horizons or out-of-scope queries preventing definitive determination "
                f"(epistemic uncertainty: {epistemic_uncertainty:.2f})."
            )
        # Gate Rule 4: Intermediate Probability Band Gate
        elif 0.30 < fraud_prob < 0.70:
            decision_gate_passed = False
            decision_gate_blocks.append(
                f"Posterior probability ({fraud_prob:.4f}) remains in intermediate uncertain band [0.30, 0.70]."
            )
            decision_state = DecisionState.INSUFFICIENT_EVIDENCE
            decision_rationale = f"Posterior probability ({fraud_prob:.4f}) is indeterminate."
        # Gate Rule 5: Corroboration Gate for positive fraud determinations
        elif fraud_prob >= 0.70 and not corroborated_fraud:
            decision_gate_passed = False
            informative_names = ", ".join(sorted(f.value for f in informative_families)) or "none"
            decision_gate_blocks.append(
                "Positive fraud determination is not corroborated: evidence draws on a single "
                f"informative dimension ({informative_names}) with aggregate inculpatory log-LR "
                f"{total_positive_log_lr:.2f}. At least two informative evidence families or a "
                "conclusive cardholder dispute are required before an automated confirmed_fraud disposition."
            )
            decision_state = DecisionState.INSUFFICIENT_EVIDENCE
            decision_rationale = (
                "High posterior is driven by a single uncorroborated evidence dimension; "
                "automated confirmed_fraud determination withheld pending corroboration (MONITOR / VERIFY posture)."
            )
        # Gate Rule 6: Admissible Decision
        else:
            decision_gate_passed = True
            decision_state = DecisionState.DECIDED
            if fraud_prob >= 0.70:
                decision_rationale = f"Automated decision gate passed. High posterior probability ({fraud_prob:.4f}) corroborated across multiple evidence dimensions."
            else:
                decision_rationale = f"Automated decision gate passed. Low posterior probability ({fraud_prob:.4f}) corroborated by exculpatory findings."

        # Log Decision Gate Evaluation in machine-readable reasoning history
        step_idx += 1
        reasoning_history.append(ReasoningStep(
            step=step_idx,
            event="DECISION_GATE_EVALUATED",
            prior_log_odds=round(current_log_odds, 4),
            posterior_log_odds=round(current_log_odds, 4),
            posterior_prob=fraud_prob,
            uncertainty_delta=0.0,
            rationale=(
                f"Decision Gate: Passed={decision_gate_passed}. State={decision_state.value}. "
                + (f"Blocks={decision_gate_blocks}. " if decision_gate_blocks else "")
                + f"Rationale: {decision_rationale}"
            )
        ))

        # Build World Hypothesis State (FRAUD and LEGITIMATE only)
        hypotheses_dict = {
            WorldHypothesis.FRAUD: HypothesisState(
                hypothesis=WorldHypothesis.FRAUD,
                probability=fraud_prob,
                log_odds=round(current_log_odds, 4),
                status=HypothesisStatus.CONFIRMED if (decision_state == DecisionState.DECIDED and fraud_prob >= 0.70) else HypothesisStatus.ACTIVE,
                supporting_evidence_ids=inculpatory_ids,
                contradicting_evidence_ids=exculpatory_ids,
                net_weight=round(total_positive_log_lr - total_negative_log_lr, 4)
            ),
            WorldHypothesis.LEGITIMATE: HypothesisState(
                hypothesis=WorldHypothesis.LEGITIMATE,
                probability=legit_prob,
                log_odds=round(-current_log_odds, 4),
                status=HypothesisStatus.CONFIRMED if (decision_state == DecisionState.DECIDED and fraud_prob <= 0.30) else HypothesisStatus.ACTIVE,
                supporting_evidence_ids=exculpatory_ids,
                contradicting_evidence_ids=inculpatory_ids,
                net_weight=round(total_negative_log_lr - total_positive_log_lr, 4)
            )
        }

        # Construct final serializable InvestigationState
        return InvestigationState(
            investigation_id=investigation_id,
            trigger=trigger,
            target_entities=target_entities,
            hypotheses=hypotheses_dict,
            primary_hypothesis=primary_hypothesis,
            secondary_typology=trigger.get("pattern", "undocumented"),
            evidence_items=ledger.items,
            belief_state={
                "prior_profile": prior_profile.value,
                "prior_prob": round(initial_prob, 4),
                "prior_log_odds": round(initial_log_odds, 4),
                "posterior_log_odds": round(current_log_odds, 4),
                "fraud_probability": fraud_prob,
                "net_log_lr": round(current_log_odds - initial_log_odds, 4),
                "evidence_count": len(ledger.items),
                "informative_families": sorted(f.value for f in informative_families),
                "corroborated_fraud": corroborated_fraud,
                "positive_log_lr": round(total_positive_log_lr, 4)
            },
            uncertainty=uncertainty_state,
            contradictions=contradictions,
            missing_information=missing_information,
            decision_state=decision_state,
            decision_gate_passed=decision_gate_passed,
            decision_gate_blocks=decision_gate_blocks,
            decision_rationale=decision_rationale,
            candidate_actions=[],
            policy_constraints=[],
            approval_requirements=approval_requirements,
            reasoning_history=reasoning_history
        )

    def calculate_posterior(self, ledger: EvidenceLedger, prior_p: Optional[float] = None) -> Dict[str, Any]:
        """Calculates posterior log-odds and fraud probability with family damping.
        Maintains complete backwards compatibility with existing benchmark runners and tests,
        while backed by the hardened evaluation engine.
        """
        state = self.evaluate_investigation(
            investigation_id="LEGACY-EVAL",
            trigger={},
            target_entities={},
            ledger=ledger,
            prior_profile=PriorProfile.ALERT_CONDITIONED,
            prior_p=prior_p
        )
        
        fraud_p = state.belief_state["fraud_probability"]
        
        # Standard verdict mapping
        if fraud_p >= 0.70:
            verdict = "confirmed_fraud"
        elif fraud_p <= 0.30:
            verdict = "legitimate"
        else:
            verdict = "uncertain"

        return {
            "prior_prob": state.belief_state["prior_prob"],
            "prior_log_odds": state.belief_state["prior_log_odds"],
            "posterior_log_odds": state.belief_state["posterior_log_odds"],
            "fraud_probability": fraud_p,
            "verdict": verdict,
            "net_log_lr": state.belief_state["net_log_lr"],
            "evidence_count": state.belief_state["evidence_count"],
            "uncertainty": state.uncertainty.model_dump(),
            "contradictions": [c.model_dump() for c in state.contradictions],
            "decision_state": state.decision_state.value,
            "decision_gate_passed": state.decision_gate_passed,
            "informative_families": state.belief_state.get("informative_families", []),
            "corroborated_fraud": state.belief_state.get("corroborated_fraud", False)
        }

    def hypothetical_update(self, ledger: EvidenceLedger, test_item: EvidenceItem, prior_p: Optional[float] = None) -> float:
        """Simulates how posterior probability would look if test_item is added."""
        temp_ledger = EvidenceLedger(items=list(ledger.items) + [test_item])
        res = self.calculate_posterior(temp_ledger, prior_p=prior_p)
        return res["fraud_probability"]
