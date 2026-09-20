import math
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field

from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceItem, EvidenceType, EvidenceDirection
from src.belief.calibration import EvidenceFamily, PriorProfile
from src.belief.state import (
    InvestigationState,
    DecisionState,
    WorldHypothesis,
    HypothesisStatus
)
from src.belief.engine import BeliefEngine, MIN_DECISION_COVERAGE
from src.policy.engine import PolicyEngine

class EvidenceActionType(str, Enum):
    GSQL_QUERY = "GSQL_QUERY"
    CUSTOMER_INTERACTION = "CUSTOMER_INTERACTION"
    STEP_UP_AUTHENTICATION = "STEP_UP_AUTHENTICATION"

class OutcomeHypothesis(BaseModel):
    outcome_label: str
    expected_probability: float = Field(description="P(Outcome | Current Belief)")
    simulated_posterior: float
    resulting_action: str
    action_flipped: bool
    decision_gate_unlocked: bool
    expected_operational_loss: float

class CandidateEvidenceEvaluation(BaseModel):
    action_id: str
    action_type: EvidenceActionType
    tool_name: str
    parameters: Dict[str, Any]
    
    # Rigorous Decision-Theoretic Metrics
    baseline_expected_loss: float
    expected_posterior_loss: float
    expected_decision_value: float  # Baseline Loss - Expected Posterior Loss
    operational_burden_cost: float  # $1.00 (LOW), $5.00 (MED), $20.00 (HIGH)
    net_decision_value: float       # EDV - Cost
    
    # Governance & Explainability
    gate_unlock_probability: float
    rationale: str
    possible_outcomes: List[OutcomeHypothesis]

class EvidenceCompassRecommendation(BaseModel):
    investigation_id: str
    current_decision_state: str
    current_primary_action: str
    
    # Ranked Candidate Evidence Actions (Sorted by net_decision_value descending)
    ranked_candidates: List[CandidateEvidenceEvaluation]
    top_recommendation: Optional[CandidateEvidenceEvaluation] = None
    
    # Stopping Governance
    should_stop_gathering: bool
    stopping_reason: str

def calculate_operational_loss(action: str, p_fraud: float, exposure_usd: float) -> float:
    """Calculates operational expected loss under the decision-theoretic loss matrix.
    
    Payoff structure:
    - Fraud state:
      * ALLOW/CLOSE: unmitigated fraud loss = exposure_usd
      * BLOCK/DECLINE: fraud stopped = $0.0
      * MONITOR/CREATE_CASE: liquidation slippage = 0.70 * exposure_usd
      * STEP_UP_AUTH: fraud challenge stopped = $0.0
      * ESCALATE_TO_ANALYST: rapid freeze slippage = 0.10 * exposure_usd
    - Legitimate state:
      * ALLOW/CLOSE: satisfied customer = $0.0
      * BLOCK: false positive insult, card reissuance, churn = $60.0
      * DECLINE: checkout decline friction = $25.0
      * MONITOR/CREATE_CASE: background monitoring compute overhead = $2.0
      * STEP_UP_AUTH: challenge friction = $5.0
      * ESCALATE_TO_ANALYST: analyst labor review cost = $15.0
    """
    p_legit = max(0.0, 1.0 - p_fraud)
    act = action.upper()
    
    if act in ["BLOCK_CARD", "BLOCK_ALL_CARDS", "CREATE_CASE"]:
        # Terminal/containment action: Loss if Fraud = $0.0 (fraud arrested)
        # Loss if Legit = $60.0 (false positive insult, reissuance, churn risk)
        return p_legit * 60.0
    elif act == "DECLINE_TRANSACTION":
        return p_legit * 25.0
    elif act in ["ALLOW_TRANSACTION", "CLOSE_NO_FRAUD"]:
        return p_fraud * exposure_usd
    elif act in ["MONITOR_CARD", "MONITOR_CONNECTED_CARDS", "WARN_CUSTOMER"]:
        return p_fraud * (0.70 * exposure_usd) + p_legit * 2.0
    elif act == "STEP_UP_AUTH":
        return p_legit * 5.0
    elif act == "ESCALATE_TO_ANALYST":
        return p_fraud * (0.10 * exposure_usd) + p_legit * 15.0
    else:
        return p_fraud * (0.70 * exposure_usd) + p_legit * 2.0

class EvidenceCompass:
    """Tark Phase 4.1 Expected Value of Information (EVOI) Engine.
    
    Consumes InvestigationState, evaluates all plausible outcomes for candidate evidence actions,
    respects the Decision Gate as a hard constraint, applies family correlation damping,
    computes Expected Decision Value (EDV) minus operational cost, and ranks candidates.
    """

    def __init__(self, belief_engine: BeliefEngine, policy_engine: PolicyEngine):
        self.belief_engine = belief_engine
        self.policy_engine = policy_engine

    def resolve_admissible_action(
        self,
        state: InvestigationState,
        exposure_usd: float,
        ledger: EvidenceLedger,
        case_context: Dict[str, Any]
    ) -> str:
        """Determines the current admissible operational action respecting Decision Gate constraints."""
        # 1. Contradiction / Human Review Gate
        if state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL:
            return "ESCALATE_TO_ANALYST"
        
        # 2. Blocked Decision Gate: Terminal actions (BLOCK_CARD, ALLOW_TRANSACTION) are inadmissible
        if not state.decision_gate_passed:
            return "MONITOR_CARD"
        
        # 3. Decision Gate Passed: Policy Engine evaluates terminal recommendation
        p_fraud = state.belief_state.get("fraud_probability", 0.5)
        if p_fraud >= 0.70:
            verdict = "confirmed_fraud"
        elif p_fraud <= 0.30:
            verdict = "legitimate"
        else:
            verdict = "uncertain"

        actions = self.policy_engine.evaluate(
            fraud_probability=p_fraud,
            verdict=verdict,
            exposure_usd=exposure_usd,
            ledger=ledger,
            case_context=case_context
        )
        if actions:
            return actions[0].action
        return "MONITOR_CARD"

    def get_candidate_action_templates(
        self,
        state: InvestigationState,
        target_entities: Dict[str, str],
        flagged_txn_id: str
    ) -> List[Dict[str, Any]]:
        """Registers the canonical candidate evidence actions from Phase 3.2 inventory."""
        card_id = target_entities.get("card_id", "")
        customer_id = target_entities.get("customer_id", "")
        txn_addr1 = state.trigger.get("txn_addr1", 0.0)
        txn_ts = (
            state.trigger.get("timestamp")
            or state.trigger.get("ts")
            or target_entities.get("timestamp")
            or target_entities.get("ts")
        )

        # Check existing evidence to prevent redundant re-querying of identical tools
        executed_types = {e.evidence_type for e in state.evidence_items}
        
        # Check out of scope dimensions
        out_of_scope_dimensions = {
            m.dimension for m in state.missing_information if m.reason == "DATA_OUT_OF_SCOPE"
        }

        candidates = []

        # 1. card_sequence
        if EvidenceType.CARD_TESTING_SEQUENCE not in executed_types and "CARD_TESTING_SEQUENCE" not in out_of_scope_dimensions:
            seq_params = {"c_id": card_id, "window_hours": 24}
            if txn_ts:
                seq_params["anchor_ts"] = txn_ts
            candidates.append({
                "action_id": "QUERY_CARD_SEQUENCE",
                "action_type": EvidenceActionType.GSQL_QUERY,
                "tool_name": "card_sequence",
                "parameters": seq_params,
                "family": EvidenceFamily.TRANSACTION_VELOCITY,
                "operational_burden_cost": 1.0,
                "outcomes": [
                    {
                        "outcome_label": "CARD_TESTING_SEQUENCE",
                        "evidence_type": EvidenceType.CARD_TESTING_SEQUENCE,
                        "source": "card_sequence",
                        "finding": "Card testing sequence: 3 micro-authorizations (<$5) followed by larger charge",
                        "lr": 34.3,
                        "log_lr": 3.535,
                        "tpr": 0.40,
                        "fpr": 0.40 / 34.3,  # ~0.01166
                        "is_exculpatory": False
                    },
                    {
                        "outcome_label": "NO_MATCH",
                        "evidence_type": EvidenceType.CARD_TESTING_SEQUENCE,
                        "source": "card_sequence",
                        "finding": "No micro-authorization testing sequence observed within 24h window",
                        "lr": 1.0,
                        "log_lr": 0.0,
                        "tpr": 0.60,
                        "fpr": 1.0 - (0.40 / 34.3),  # ~0.98834
                        "is_exculpatory": False
                    }
                ]
            })

        # 2. device_analysis
        if EvidenceType.SHARED_DEVICE_RING not in executed_types and "SHARED_DEVICE_RING" not in out_of_scope_dimensions:
            candidates.append({
                "action_id": "QUERY_DEVICE_ANALYSIS",
                "action_type": EvidenceActionType.GSQL_QUERY,
                "tool_name": "device_analysis",
                "parameters": {"t_id": flagged_txn_id},
                "family": EvidenceFamily.DEVICE_INFRASTRUCTURE,
                "operational_burden_cost": 1.0,
                "outcomes": [
                    {
                        "outcome_label": "SHARED_DEVICE_RING",
                        "evidence_type": EvidenceType.SHARED_DEVICE_RING,
                        "source": "device_analysis",
                        "finding": "Device profile is shared across multiple distinct cards",
                        "lr": 14.2,
                        "log_lr": 2.653,
                        "tpr": 0.50,
                        "fpr": 0.50 / 14.2,  # ~0.03521
                        "is_exculpatory": False
                    },
                    {
                        "outcome_label": "NO_MATCH",
                        "evidence_type": EvidenceType.SHARED_DEVICE_RING,
                        "source": "device_analysis",
                        "finding": "Device profile clean; no multi-card sharing observed",
                        "lr": 1.0,
                        "log_lr": 0.0,
                        "tpr": 0.50,
                        "fpr": 1.0 - (0.50 / 14.2),  # ~0.96479
                        "is_exculpatory": False
                    }
                ]
            })

        # 3. txn_velocity
        if EvidenceType.HIGH_VELOCITY not in executed_types and "HIGH_VELOCITY" not in out_of_scope_dimensions:
            vel_params = {"c_id": card_id, "window_hours": 24}
            if txn_ts:
                vel_params["target_ts"] = txn_ts
            candidates.append({
                "action_id": "QUERY_TXN_VELOCITY",
                "action_type": EvidenceActionType.GSQL_QUERY,
                "tool_name": "txn_velocity",
                "parameters": vel_params,
                "family": EvidenceFamily.TRANSACTION_VELOCITY,
                "operational_burden_cost": 1.0,
                "outcomes": [
                    {
                        "outcome_label": "HIGH_VELOCITY",
                        "evidence_type": EvidenceType.HIGH_VELOCITY,
                        "source": "txn_velocity",
                        "finding": "High 24h velocity: 10+ transactions within 24h window",
                        "lr": 2.5,
                        "log_lr": 0.916,
                        "tpr": 0.45,
                        "fpr": 0.45 / 2.5,  # 0.18
                        "is_exculpatory": False
                    },
                    {
                        "outcome_label": "NO_MATCH",
                        "evidence_type": EvidenceType.HIGH_VELOCITY,
                        "source": "txn_velocity",
                        "finding": "Transaction velocity within normal bounds",
                        "lr": 1.0,
                        "log_lr": 0.0,
                        "tpr": 0.55,
                        "fpr": 0.82,
                        "is_exculpatory": False
                    }
                ]
            })

        # 4. region_analysis
        if EvidenceType.OUT_OF_REGION not in executed_types and "OUT_OF_REGION" not in out_of_scope_dimensions:
            candidates.append({
                "action_id": "QUERY_REGION_ANALYSIS",
                "action_type": EvidenceActionType.GSQL_QUERY,
                "tool_name": "region_analysis",
                "parameters": {"cust_id": customer_id, "txn_addr1": txn_addr1},
                "family": EvidenceFamily.GEOGRAPHIC_LOCATION,
                "operational_burden_cost": 1.0,
                "outcomes": [
                    {
                        "outcome_label": "OUT_OF_REGION",
                        "evidence_type": EvidenceType.OUT_OF_REGION,
                        "source": "region_analysis",
                        "finding": f"Billing region {txn_addr1} has no precedence in historical spend",
                        "lr": 0.26,
                        "log_lr": -1.357,
                        "tpr": 0.10,
                        "fpr": 0.10 / 0.26,  # ~0.3846
                        "is_exculpatory": False
                    },
                    {
                        "outcome_label": "NO_MATCH",
                        "evidence_type": EvidenceType.OUT_OF_REGION,
                        "source": "region_analysis",
                        "finding": "Transaction in customer historical billing region",
                        "lr": 1.0,
                        "log_lr": 0.0,
                        "tpr": 0.90,
                        "fpr": 1.0 - (0.10 / 0.26),
                        "is_exculpatory": False
                    }
                ]
            })

        # 5. VERIFY_WITH_CUSTOMER (External Out-of-band communication)
        # Skip only if customer has already directly confirmed or reported
        has_direct_dispute = any(
            e.evidence_type in [EvidenceType.CUSTOMER_CONFIRMATION, EvidenceType.CUSTOMER_DENIAL]
            for e in state.evidence_items
        ) or state.trigger.get("trigger_type") == "customer_report"
        
        if not has_direct_dispute:
            candidates.append({
                "action_id": "VERIFY_WITH_CUSTOMER",
                "action_type": EvidenceActionType.CUSTOMER_INTERACTION,
                "tool_name": "simulate_customer_reply",
                "parameters": {"prompt": "Did you authorize this transaction?"},
                "family": EvidenceFamily.CUSTOMER_DISPUTE,
                "operational_burden_cost": 20.0,
                "outcomes": [
                    {
                        "outcome_label": "CUSTOMER_DENIAL",
                        "evidence_type": EvidenceType.CUSTOMER_DENIAL,
                        "source": "customer_verification",
                        "finding": "Customer explicitly denied and disputed transaction authorization",
                        "lr": 18.5,
                        "log_lr": 2.918,
                        "tpr": 0.70,
                        "fpr": 0.05,
                        "is_exculpatory": False
                    },
                    {
                        "outcome_label": "CUSTOMER_CONFIRMATION",
                        "evidence_type": EvidenceType.CUSTOMER_CONFIRMATION,
                        "source": "customer_verification",
                        "finding": "Customer confirmed transaction was authorized",
                        "lr": 0.05,
                        "log_lr": -2.996,
                        "tpr": 0.02,
                        "fpr": 0.75,
                        "is_exculpatory": True
                    },
                    {
                        "outcome_label": "TIMEOUT",
                        "evidence_type": EvidenceType.CUSTOMER_CONFIRMATION,  # neutral placeholder
                        "source": "customer_verification",
                        "finding": "Customer verification timed out; no out-of-band response",
                        "lr": 1.0,
                        "log_lr": 0.0,
                        "tpr": 0.28,
                        "fpr": 0.20,
                        "is_exculpatory": False
                    }
                ]
            })

        # 6. STEP_UP_AUTH (Interactive MFA / OTP for in-flight transactions)
        is_in_flight = state.trigger.get("is_in_flight", False) or state.trigger.get("trigger_type") in ["in_flight_auth", "realtime_checkout"]
        if is_in_flight and not has_direct_dispute:
            candidates.append({
                "action_id": "STEP_UP_AUTH",
                "action_type": EvidenceActionType.STEP_UP_AUTHENTICATION,
                "tool_name": "simulate_step_up_auth",
                "parameters": {"challenge_type": "MFA_OTP"},
                "family": EvidenceFamily.CUSTOMER_DISPUTE,
                "operational_burden_cost": 5.0,
                "outcomes": [
                    {
                        "outcome_label": "AUTH_FAILED",
                        "evidence_type": EvidenceType.CUSTOMER_DENIAL,
                        "source": "step_up_auth",
                        "finding": "Cardholder step-up authentication failed",
                        "lr": 15.0,
                        "log_lr": 2.708,
                        "tpr": 0.75,
                        "fpr": 0.05,
                        "is_exculpatory": False
                    },
                    {
                        "outcome_label": "AUTH_PASSED",
                        "evidence_type": EvidenceType.CUSTOMER_CONFIRMATION,
                        "source": "step_up_auth",
                        "finding": "Cardholder successfully completed cryptographic step-up MFA",
                        "lr": 0.10,
                        "log_lr": -2.302,
                        "tpr": 0.05,
                        "fpr": 0.85,
                        "is_exculpatory": True
                    },
                    {
                        "outcome_label": "EXPIRED",
                        "evidence_type": EvidenceType.CUSTOMER_CONFIRMATION,
                        "source": "step_up_auth",
                        "finding": "Step-up authentication challenge expired without interaction",
                        "lr": 1.0,
                        "log_lr": 0.0,
                        "tpr": 0.20,
                        "fpr": 0.10,
                        "is_exculpatory": False
                    }
                ]
            })

        return candidates

    def evaluate_evidence_compass(
        self,
        state: InvestigationState,
        exposure_usd: float,
        case_context: Optional[Dict[str, Any]] = None,
        candidate_action_ids: Optional[List[str]] = None
    ) -> EvidenceCompassRecommendation:
        """Evaluates all candidate evidence actions and produces ranked EVOI recommendations."""
        case_ctx = case_context or {
            "case_id": state.investigation_id,
            "pattern": state.secondary_typology,
            "trigger_type": state.trigger.get("trigger_type", "risk_score")
        }
        
        current_ledger = EvidenceLedger(items=list(state.evidence_items))
        p_current = state.belief_state.get("fraud_probability", 0.5)
        
        # Determine current primary admissible action and baseline expected loss
        current_primary_action = self.resolve_admissible_action(
            state=state,
            exposure_usd=exposure_usd,
            ledger=current_ledger,
            case_context=case_ctx
        )
        baseline_loss = round(calculate_operational_loss(current_primary_action, p_current, exposure_usd), 2)

        # 1. Check Hard Stopping Governance: Aleatoric Contradiction
        if state.decision_state == DecisionState.REQUIRES_HUMAN_APPROVAL:
            return EvidenceCompassRecommendation(
                investigation_id=state.investigation_id,
                current_decision_state=state.decision_state.value,
                current_primary_action=current_primary_action,
                ranked_candidates=[],
                top_recommendation=None,
                should_stop_gathering=True,
                stopping_reason=(
                    "Mandatory human review required: severe evidentiary contradiction "
                    f"(aleatoric conflict {state.uncertainty.aleatoric_uncertainty:.2f} >= 0.40). "
                    "Automated evidence acquisition halted."
                )
            )

        # Retrieve candidate action templates
        target_entities = state.target_entities
        flagged_txn_id = state.trigger.get("flagged_txn_id", "")
        templates = self.get_candidate_action_templates(state, target_entities, flagged_txn_id)
        if candidate_action_ids is not None:
            templates = [t for t in templates if t["action_id"] in candidate_action_ids]

        evaluated_candidates: List[CandidateEvidenceEvaluation] = []

        # 2. Evaluate Each Candidate Evidence Action
        for tmpl in templates:
            action_id = tmpl["action_id"]
            action_type = tmpl["action_type"]
            tool_name = tmpl["tool_name"]
            params = tmpl["parameters"]
            cost = tmpl["operational_burden_cost"]
            outcomes_data = tmpl["outcomes"]

            outcome_hypotheses: List[OutcomeHypothesis] = []
            expected_posterior_loss = 0.0
            gate_unlock_count = 0.0
            total_outcome_prob = 0.0

            # Derive marginal outcome probabilities: P(outcome) = TPR * p + FPR * (1 - p)
            raw_probs = [
                (o["tpr"] * p_current + o["fpr"] * (1.0 - p_current))
                for o in outcomes_data
            ]
            prob_sum = sum(raw_probs)
            # Normalize to guarantee exact sum to 1.0
            norm_probs = [p / prob_sum for p in raw_probs] if prob_sum > 0 else [1.0 / len(raw_probs)] * len(raw_probs)

            for idx, o in enumerate(outcomes_data):
                outcome_prob = norm_probs[idx]
                total_outcome_prob += outcome_prob
                
                # Construct hypothetical evidence item
                hypo_item = EvidenceItem(
                    evidence_type=o["evidence_type"],
                    source=o["source"],
                    finding=o["finding"],
                    lr=o["lr"],
                    log_lr=o["log_lr"],
                    is_exculpatory=o.get("is_exculpatory", False),
                    details={"simulated": True, "outcome_label": o["outcome_label"]}
                )

                # Simulate hypothetical state through complete BeliefEngine
                hypo_ledger = EvidenceLedger(items=list(state.evidence_items) + [hypo_item])
                hypo_state = self.belief_engine.evaluate_investigation(
                    investigation_id=f"SIM-{state.investigation_id}",
                    trigger=state.trigger,
                    target_entities=state.target_entities,
                    ledger=hypo_ledger,
                    prior_profile=PriorProfile(state.belief_state.get("prior_profile", PriorProfile.ALERT_CONDITIONED.value)),
                    prior_p=state.belief_state.get("prior_prob")
                )

                sim_p = hypo_state.belief_state["fraud_probability"]
                gate_unlocked = (not state.decision_gate_passed) and hypo_state.decision_gate_passed
                if gate_unlocked:
                    gate_unlock_count += outcome_prob

                # Determine operational action supported by hypothetical state
                verdict = "confirmed_fraud" if sim_p >= 0.70 else ("legitimate" if sim_p <= 0.30 else "uncertain")
                policy_actions = self.policy_engine.evaluate(
                    fraud_probability=sim_p,
                    verdict=verdict,
                    exposure_usd=exposure_usd,
                    ledger=hypo_ledger,
                    case_context=case_ctx
                )
                resulting_action = policy_actions[0].action if policy_actions else "MONITOR_CARD"
                action_flipped = (resulting_action != current_primary_action)

                # Calculate operational expected loss for this outcome
                outcome_loss = calculate_operational_loss(resulting_action, sim_p, exposure_usd)
                expected_posterior_loss += outcome_prob * outcome_loss

                outcome_hypotheses.append(OutcomeHypothesis(
                    outcome_label=o["outcome_label"],
                    expected_probability=round(outcome_prob, 4),
                    simulated_posterior=round(sim_p, 4),
                    resulting_action=resulting_action,
                    action_flipped=action_flipped,
                    decision_gate_unlocked=gate_unlocked,
                    expected_operational_loss=round(outcome_loss, 2)
                ))

            # Rigorous EVOI Metrics
            expected_posterior_loss = round(expected_posterior_loss, 2)
            # Decision-Theoretic Principle: If no outcome changes the operational decision or unlocks the gate,
            # information has zero decision value by definition.
            if not any(oh.action_flipped or oh.decision_gate_unlocked for oh in outcome_hypotheses):
                raw_edv = 0.0
            else:
                raw_edv = max(0.0, round(baseline_loss - expected_posterior_loss, 2))
            net_value = round(raw_edv - cost, 2)

            flip_prob = sum(
                oh.expected_probability for oh in outcome_hypotheses if oh.action_flipped
            )

            rationale = (
                f"Evaluated {len(outcome_hypotheses)} outcomes. Baseline loss ${baseline_loss:.2f} -> "
                f"expected loss ${expected_posterior_loss:.2f} (EDV: ${raw_edv:.2f}, Cost: ${cost:.2f}, Net: ${net_value:.2f}). "
                f"Flip probability: {flip_prob * 100:.1f}%, Gate unlock probability: {gate_unlock_count * 100:.1f}%."
            )

            evaluated_candidates.append(CandidateEvidenceEvaluation(
                action_id=action_id,
                action_type=action_type,
                tool_name=tool_name,
                parameters=params,
                baseline_expected_loss=baseline_loss,
                expected_posterior_loss=expected_posterior_loss,
                expected_decision_value=raw_edv,
                operational_burden_cost=cost,
                net_decision_value=net_value,
                gate_unlock_probability=round(gate_unlock_count, 4),
                rationale=rationale,
                possible_outcomes=outcome_hypotheses
            ))

        # 3. Rank Candidates by Net Decision Value (descending)
        ranked_candidates = sorted(
            evaluated_candidates,
            key=lambda c: c.net_decision_value,
            reverse=True
        )

        top_candidate = ranked_candidates[0] if ranked_candidates else None

        # 4. Stopping Conditions Evaluation
        # Stopping Condition A: Already Decided with Saturation
        if state.decision_state == DecisionState.DECIDED and (not top_candidate or top_candidate.net_decision_value <= 0):
            return EvidenceCompassRecommendation(
                investigation_id=state.investigation_id,
                current_decision_state=state.decision_state.value,
                current_primary_action=current_primary_action,
                ranked_candidates=ranked_candidates,
                top_recommendation=None,
                should_stop_gathering=True,
                stopping_reason="Decision sufficiently supported and action saturated. Remaining candidate evidence has net decision value <= 0."
            )

        # Stopping Condition B: Net Value Exhaustion (Max EDV <= Cost)
        if not top_candidate or top_candidate.net_decision_value <= 0:
            return EvidenceCompassRecommendation(
                investigation_id=state.investigation_id,
                current_decision_state=state.decision_state.value,
                current_primary_action=current_primary_action,
                ranked_candidates=ranked_candidates,
                top_recommendation=None,
                should_stop_gathering=True,
                stopping_reason="Net decision value exhausted. No candidate evidence action has expected decision value exceeding acquisition cost."
            )

        # Stopping Condition C: Actionable recommendation found
        return EvidenceCompassRecommendation(
            investigation_id=state.investigation_id,
            current_decision_state=state.decision_state.value,
            current_primary_action=current_primary_action,
            ranked_candidates=ranked_candidates,
            top_recommendation=top_candidate,
            should_stop_gathering=False,
            stopping_reason=f"Top candidate '{top_candidate.action_id}' offers positive net decision value (+${top_candidate.net_decision_value:.2f})."
        )
