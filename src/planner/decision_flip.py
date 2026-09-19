from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from src.evidence.types import EvidenceType, EvidenceItem
from src.evidence.ledger import EvidenceLedger
from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine, ActionRecommendation

class EvidenceRequestDecision(BaseModel):
    should_request: bool
    evidence_type: Optional[str] = None
    prompt: Optional[str] = None
    expected_flip: Optional[str] = None
    reason: str

class DecisionFlipPlanner:
    def __init__(self, belief_engine: BeliefEngine, policy_engine: PolicyEngine):
        self.belief_engine = belief_engine
        self.policy_engine = policy_engine

    def evaluate_decision_flip(
        self,
        ledger: EvidenceLedger,
        case_context: Dict[str, Any],
        exposure_usd: float
    ) -> EvidenceRequestDecision:
        """Determines if collecting additional evidence can flip the Next Best Action."""
        current_res = self.belief_engine.calculate_posterior(ledger)
        current_prob = current_res["fraud_probability"]
        current_verdict = current_res["verdict"]

        current_actions = self.policy_engine.evaluate(
            fraud_probability=current_prob,
            verdict=current_verdict,
            exposure_usd=exposure_usd,
            ledger=ledger,
            case_context=case_context
        )
        current_primary_action = current_actions[0].action if current_actions else "MONITOR_CARD"

        # If already triggered by customer report, customer input is already known
        if case_context.get("trigger_type") == "customer_report":
            return EvidenceRequestDecision(
                should_request=False,
                reason="Customer report already provided direct testimony; action is actionable without further query."
            )

        # Candidate hypothetical test 1: Ask customer (VERIFY_WITH_CUSTOMER)
        # Outcome A: Customer confirms transaction (exculpatory)
        hypo_confirm = EvidenceItem(
            evidence_type=EvidenceType.CUSTOMER_CONFIRMATION,
            source="simulated_verification",
            finding="Customer confirmed making the transaction.",
            lr=0.05,
            log_lr=-2.996,
            is_exculpatory=True
        )
        hypo_ledger_confirm = EvidenceLedger(items=list(ledger.items) + [hypo_confirm])
        hypo_res_confirm = self.belief_engine.calculate_posterior(hypo_ledger_confirm)
        hypo_actions_confirm = self.policy_engine.evaluate(
            fraud_probability=hypo_res_confirm["fraud_probability"],
            verdict=hypo_res_confirm["verdict"],
            exposure_usd=exposure_usd,
            ledger=hypo_ledger_confirm,
            case_context=case_context
        )
        hypo_primary_confirm = hypo_actions_confirm[0].action if hypo_actions_confirm else "CLOSE_NO_FRAUD"

        # Check if the primary action flips upon customer confirmation
        if hypo_primary_confirm != current_primary_action:
            return EvidenceRequestDecision(
                should_request=True,
                evidence_type="VERIFY_WITH_CUSTOMER",
                prompt="Did you authorize this transaction?",
                expected_flip=f"Action changes from '{current_primary_action}' to '{hypo_primary_confirm}' if confirmed legitimate.",
                reason="High value of information: cardholder confirmation resolves ambiguity and prevents false positive card blocking."
            )

        # Candidate hypothetical test 2: Step-up authentication
        if current_primary_action in ["BLOCK_CARD", "DECLINE_TRANSACTION"] and current_prob < 0.85:
            return EvidenceRequestDecision(
                should_request=True,
                evidence_type="STEP_UP_AUTH",
                prompt="Require biometric / SMS OTP challenge before finalizing block.",
                expected_flip=f"Action shifts from '{current_primary_action}' to 'ALLOW_TRANSACTION' if authentication succeeds.",
                reason="Policy R1 compliance: avoid aggressive block on borderline confidence."
            )

        return EvidenceRequestDecision(
            should_request=False,
            reason=f"Evidence Compass calculation: Information value below threshold. Current evidence is sufficient for '{current_primary_action}'."
        )
