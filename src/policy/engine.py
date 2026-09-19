from typing import List, Dict, Any
from pydantic import BaseModel, Field
from src.evidence.types import EvidenceType
from src.evidence.ledger import EvidenceLedger

class ActionRecommendation(BaseModel):
    action: str
    approval_route: str
    reason: str

class PolicyEngine:
    def determine_block_card_route(self, exposure_usd: float) -> str:
        """Rule 2: L1 if <= 2500, L2 if > 2500."""
        return "L1" if exposure_usd <= 2500.0 else "L2"

    def evaluate(
        self,
        fraud_probability: float,
        verdict: str,
        exposure_usd: float,
        ledger: EvidenceLedger,
        case_context: Dict[str, Any]
    ) -> List[ActionRecommendation]:
        """Evaluates all 10 policy rules and returns ordered list of recommendations."""
        actions: List[ActionRecommendation] = []
        applied_rules = []

        # Check triggers and flags
        evidence_types = {item.evidence_type for item in ledger.items}
        trigger_type = case_context.get("trigger_type", "")
        customer_denied = (EvidenceType.CUSTOMER_DENIAL in evidence_types) or (trigger_type == "customer_report")
        customer_confirmed = EvidenceType.CUSTOMER_CONFIRMATION in evidence_types
        recurring_matched = EvidenceType.RECURRING_CHARGE_MATCH in evidence_types
        is_card_testing = EvidenceType.CARD_TESTING_SEQUENCE in evidence_types
        is_shared_ring = EvidenceType.SHARED_DEVICE_RING in evidence_types
        is_undocumented = case_context.get("pattern") == "undocumented"
        is_single_signal = len(ledger.items) <= 1

        # Rule R3: Customer confirms transaction
        if customer_confirmed:
            actions.append(ActionRecommendation(
                action="CLOSE_NO_FRAUD",
                approval_route="auto",
                reason="R3: Customer confirmed transaction as legitimate."
            ))
            return actions

        # Rule R7: Disputed but matches recurring pattern
        if recurring_matched and customer_denied:
            actions.append(ActionRecommendation(
                action="CREATE_CASE",
                approval_route="auto",
                reason="R7: Charge disputed but matches recurring billing profile."
            ))
            actions.append(ActionRecommendation(
                action="VERIFY_WITH_CUSTOMER",
                approval_route="auto",
                reason="R7: Re-verify recurring subscription with customer."
            ))
            actions.append(ActionRecommendation(
                action="WARN_CUSTOMER",
                approval_route="auto",
                reason="R7: Notify customer regarding recurring charge policy."
            ))
            return actions

        # Rule R5: Card testing pattern
        if is_card_testing:
            actions.append(ActionRecommendation(
                action="DECLINE_TRANSACTION",
                approval_route="L1",
                reason="R5: Card testing sequence detected (micro-authorizations followed by purchase)."
            ))
            if exposure_usd > 100.0:
                actions.append(ActionRecommendation(
                    action="BLOCK_CARD",
                    approval_route=self.determine_block_card_route(exposure_usd),
                    reason="R5: Card testing sequence cleared a charge over $100."
                ))
            else:
                actions.append(ActionRecommendation(
                    action="STEP_UP_AUTH",
                    approval_route="auto",
                    reason="R5: Step-up authentication required following testing attempts."
                ))
            return actions

        # Rule R2: Customer denies transaction
        if customer_denied:
            actions.append(ActionRecommendation(
                action="BLOCK_CARD",
                approval_route=self.determine_block_card_route(exposure_usd),
                reason="R2: Customer reported/denied transaction."
            ))
            actions.append(ActionRecommendation(
                action="CREATE_CASE",
                approval_route="auto",
                reason="R2: Internal case created for customer dispute/denial."
            ))
            if exposure_usd > 1000.0 or is_shared_ring:
                actions.append(ActionRecommendation(
                    action="FILE_REPORT",
                    approval_route="L2",
                    reason="R2: Regulatory SAR filing required (exposure > $1,000 or shared ring)."
                ))
            if is_shared_ring:
                actions.append(ActionRecommendation(
                    action="MONITOR_CONNECTED_CARDS",
                    approval_route="auto",
                    reason="R6: Shared device or infrastructure links to other cards."
                ))
            return actions

        # Rule R6: Shared origin across multiple cards
        if is_shared_ring:
            actions.append(ActionRecommendation(
                action="CREATE_CASE",
                approval_route="auto",
                reason="R6: Coordinated fraud ring detected across shared device/region."
            ))
            actions.append(ActionRecommendation(
                action="FILE_REPORT",
                approval_route="L2",
                reason="R6: Suspicious activity report filing for syndicate fraud ring."
            ))
            actions.append(ActionRecommendation(
                action="MONITOR_CONNECTED_CARDS",
                approval_route="auto",
                reason="R6: Place all connected cards on elevated monitoring."
            ))
            return actions

        # Rule R9: Undocumented pattern with evidence of abuse
        if is_undocumented and fraud_probability >= 0.70:
            actions.append(ActionRecommendation(
                action="CREATE_CASE",
                approval_route="auto",
                reason="R9: Coordinated anomalous activity fitting no standard typology."
            ))
            actions.append(ActionRecommendation(
                action="FILE_REPORT",
                approval_route="L2",
                reason="R9: Regulatory report for novel/undocumented fraud scheme."
            ))
            actions.append(ActionRecommendation(
                action="ESCALATE_TO_ANALYST",
                approval_route="auto",
                reason="R9: Hand off novel pattern to senior fraud analyst."
            ))
            return actions

        # Rule R1: Verify before block on weak signal
        if is_single_signal and fraud_probability < 0.70:
            actions.append(ActionRecommendation(
                action="VERIFY_WITH_CUSTOMER",
                approval_route="auto",
                reason="R1: Weak single signal (fraud prob < 0.70); verify before punitive action."
            ))
            actions.append(ActionRecommendation(
                action="MONITOR_CARD",
                approval_route="auto",
                reason="R1: Monitor card while awaiting customer verification."
            ))
            return actions

        # Rule R8: Uncertain and exposed
        if verdict == "uncertain" and exposure_usd > 500.0:
            actions.append(ActionRecommendation(
                action="ESCALATE_TO_ANALYST",
                approval_route="auto",
                reason="R8: Uncertain verdict with exposure exceeding $500 threshold."
            ))
            actions.append(ActionRecommendation(
                action="MONITOR_CARD",
                approval_route="auto",
                reason="R8: Maintain card monitoring pending analyst review."
            ))
            return actions

        # General High Confidence Fraud (>= 0.70)
        if fraud_probability >= 0.70:
            actions.append(ActionRecommendation(
                action="BLOCK_CARD",
                approval_route=self.determine_block_card_route(exposure_usd),
                reason=f"High assessed fraud probability ({fraud_probability:.2f})."
            ))
            actions.append(ActionRecommendation(
                action="CREATE_CASE",
                approval_route="auto",
                reason="Internal fraud case opened with evidence."
            ))
            if exposure_usd >= 1000.0:
                actions.append(ActionRecommendation(
                    action="FILE_REPORT",
                    approval_route="L2",
                    reason="Exposure >= $1,000 mandates regulatory SAR filing."
                ))
            return actions

        # General Low Confidence / Legitimate (<= 0.30)
        if fraud_probability <= 0.30:
            actions.append(ActionRecommendation(
                action="ALLOW_TRANSACTION",
                approval_route="auto",
                reason=f"Low fraud probability ({fraud_probability:.2f}) consistent with normal usage."
            ))
            actions.append(ActionRecommendation(
                action="CLOSE_NO_FRAUD",
                approval_route="auto",
                reason="Alert cleared as legitimate cardholder activity."
            ))
            return actions

        # Default fallback: Monitor & Verify
        actions.append(ActionRecommendation(
            action="MONITOR_CARD",
            approval_route="auto",
            reason="Ambiguous signals warrant 72-hour elevated monitoring."
        ))
        actions.append(ActionRecommendation(
            action="VERIFY_WITH_CUSTOMER",
            approval_route="auto",
            reason="Request cardholder confirmation to resolve ambiguity."
        ))
        return actions
