from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.evidence.types import EvidenceType
from src.evidence.ledger import EvidenceLedger

class ActionRole(str, Enum):
    """Semantic role of policy action recommendations."""
    PRIMARY = "PRIMARY"                  # Governing Decision / Next-Best-Action
    SECONDARY = "SECONDARY"              # Parallel operational action
    CONSEQUENTIAL = "CONSEQUENTIAL"      # Operational consequence of governing action

class ActionScope(str, Enum):
    """Operational intervention scope of policy recommendations."""
    TRANSACTION = "TRANSACTION"          # Transaction-level intervention (DECLINE, ALLOW, STEP_UP)
    CARD_ACCOUNT = "CARD_ACCOUNT"        # Account/Card-level intervention (BLOCK, MONITOR)
    CASE_MANAGEMENT = "CASE_MANAGEMENT"  # Case management & regulatory (CREATE_CASE, CLOSE_NO_FRAUD, FILE_REPORT)
    CUSTOMER = "CUSTOMER"                # Customer interaction (VERIFY, WARN)
    ESCALATION = "ESCALATION"            # Escalation to analyst


# A shared-device ring spanning at least this many distinct card accounts is a
# large-scale syndicate. Per the R6-syndicate exception, the scale of the
# multi-account graph corroboration (not a single evidence family) requires
# Level-2 human authorization before any SAR filing.
SYNDICATE_CARD_THRESHOLD = 10

class ActionRecommendation(BaseModel):
    action: str
    approval_route: str
    reason: str
    role: ActionRole = Field(default=ActionRole.PRIMARY)
    scope: Optional[ActionScope] = Field(default=None)

class PolicyEngine:
    def determine_block_card_route(self, exposure_usd: float) -> str:
        """Rule 2: L1 if <= 2500, L2 if > 2500."""
        return "L1" if exposure_usd <= 2500.0 else "L2"

    @staticmethod
    def _max_syndicate_card_count(ledger: EvidenceLedger) -> int:
        """Largest observed SHARED_DEVICE_RING breadth (distinct connected cards)."""
        max_count = 0
        for item in ledger.items:
            if item.evidence_type != EvidenceType.SHARED_DEVICE_RING:
                continue
            if str(item.value) == "NO_MATCH":
                continue
            candidates = []
            if isinstance(item.value, dict):
                candidates.append(item.value.get("shared_card_count"))
            if item.details:
                candidates.append(item.details.get("shared_count"))
                candidates.append(item.details.get("shared_card_count"))
            candidates.append(len(item.supporting_entities or []))
            for c in candidates:
                if isinstance(c, (int, float)):
                    max_count = max(max_count, int(c))
        return max_count

    @staticmethod
    def get_primary_action(actions: List[ActionRecommendation]) -> Optional[ActionRecommendation]:
        """Returns the governing primary next-best-action from an evaluated action set."""
        for a in actions:
            if a.role == ActionRole.PRIMARY:
                return a
        return actions[0] if actions else None

    @staticmethod
    def get_consequential_actions(actions: List[ActionRecommendation]) -> List[ActionRecommendation]:
        """Returns all secondary and consequential operational actions."""
        return [a for a in actions if a.role != ActionRole.PRIMARY]

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

        # Check triggers and flags with genuine evidence semantics (excluding NO_MATCH / uninformative placeholders)
        trigger_type = case_context.get("trigger_type", "")
        
        customer_denied = (
            any(
                item.evidence_type == EvidenceType.CUSTOMER_DENIAL
                and item.value != "NO_MATCH"
                for item in ledger.items
            )
            or (trigger_type == "customer_report")
        )
        
        customer_confirmed = any(
            item.evidence_type == EvidenceType.CUSTOMER_CONFIRMATION
            and item.is_exculpatory
            and item.value not in ["NO_MATCH", "UNAVAILABLE", "EXPIRED", None]
            for item in ledger.items
        )
        
        recurring_matched = any(
            item.evidence_type == EvidenceType.RECURRING_CHARGE_MATCH
            and item.value != "NO_MATCH"
            and item.is_exculpatory
            for item in ledger.items
        )
        
        is_card_testing = any(
            item.evidence_type == EvidenceType.CARD_TESTING_SEQUENCE
            and item.value != "NO_MATCH"
            and item.lr > 1.0
            for item in ledger.items
        )
        
        is_shared_ring = any(
            item.evidence_type == EvidenceType.SHARED_DEVICE_RING
            and item.value != "NO_MATCH"
            and item.lr > 1.0
            for item in ledger.items
        )
        
        pattern = case_context.get("pattern") or case_context.get("secondary_typology") or ""
        is_undocumented = (pattern == "undocumented")
        coverage = case_context.get("evidence_coverage")
        
        informative_items = [
            item for item in ledger.items
            if (item.lr != 1.0 or item.is_exculpatory) and item.value != "NO_MATCH"
        ]
        is_single_signal = len(informative_items) <= 1

        # Rule R3: Customer confirms transaction
        if customer_confirmed:
            actions.append(ActionRecommendation(
                action="CLOSE_NO_FRAUD",
                approval_route="auto",
                reason="R3: Customer confirmed transaction as legitimate.",
                role=ActionRole.PRIMARY,
                scope=ActionScope.CASE_MANAGEMENT
            ))
            return actions

        # Rule R7: Disputed but matches recurring pattern
        if recurring_matched and customer_denied:
            actions.append(ActionRecommendation(
                action="CREATE_CASE",
                approval_route="auto",
                reason="R7: Charge disputed but matches recurring billing profile.",
                role=ActionRole.PRIMARY,
                scope=ActionScope.CASE_MANAGEMENT
            ))
            actions.append(ActionRecommendation(
                action="VERIFY_WITH_CUSTOMER",
                approval_route="auto",
                reason="R7: Re-verify recurring subscription with customer.",
                role=ActionRole.SECONDARY,
                scope=ActionScope.CUSTOMER
            ))
            actions.append(ActionRecommendation(
                action="WARN_CUSTOMER",
                approval_route="auto",
                reason="R7: Notify customer regarding recurring charge policy.",
                role=ActionRole.CONSEQUENTIAL,
                scope=ActionScope.CUSTOMER
            ))
            return actions

        # Rule R5: Card testing pattern
        if is_card_testing:
            actions.append(ActionRecommendation(
                action="DECLINE_TRANSACTION",
                approval_route="L1",
                reason="R5: Card testing sequence detected (micro-authorizations followed by purchase).",
                role=ActionRole.PRIMARY,
                scope=ActionScope.TRANSACTION
            ))
            if exposure_usd > 100.0:
                actions.append(ActionRecommendation(
                    action="BLOCK_CARD",
                    approval_route=self.determine_block_card_route(exposure_usd),
                    reason="R5: Card testing sequence cleared a charge over $100.",
                    role=ActionRole.CONSEQUENTIAL,
                    scope=ActionScope.CARD_ACCOUNT
                ))
            else:
                actions.append(ActionRecommendation(
                    action="STEP_UP_AUTH",
                    approval_route="auto",
                    reason="R5: Step-up authentication required following testing attempts.",
                    role=ActionRole.CONSEQUENTIAL,
                    scope=ActionScope.TRANSACTION
                ))
            return actions

        # Rule R2: Customer denies transaction
        if customer_denied:
            actions.append(ActionRecommendation(
                action="BLOCK_CARD",
                approval_route=self.determine_block_card_route(exposure_usd),
                reason="R2: Customer reported/denied transaction.",
                role=ActionRole.PRIMARY,
                scope=ActionScope.CARD_ACCOUNT
            ))
            actions.append(ActionRecommendation(
                action="CREATE_CASE",
                approval_route="auto",
                reason="R2: Internal case created for customer dispute/denial.",
                role=ActionRole.CONSEQUENTIAL,
                scope=ActionScope.CASE_MANAGEMENT
            ))
            if exposure_usd > 1000.0 or is_shared_ring:
                actions.append(ActionRecommendation(
                    action="FILE_REPORT",
                    approval_route="L2",
                    reason="R2: Regulatory SAR filing required (exposure > $1,000 or shared ring).",
                    role=ActionRole.CONSEQUENTIAL,
                    scope=ActionScope.CASE_MANAGEMENT
                ))
            if is_shared_ring:
                actions.append(ActionRecommendation(
                    action="MONITOR_CONNECTED_CARDS",
                    approval_route="auto",
                    reason="R6: Shared device or infrastructure links to other cards.",
                    role=ActionRole.CONSEQUENTIAL,
                    scope=ActionScope.CARD_ACCOUNT
                ))
            return actions

        # Rule R6: Shared origin across multiple cards
        if is_shared_ring:
            ring_size = self._max_syndicate_card_count(ledger)
            gate_explicitly_locked = case_context.get("decision_gate_passed") is False

            # R6-syndicate exception: a ring spanning >= SYNDICATE_CARD_THRESHOLD
            # independent accounts is escalated for Level-2 human authorization
            # before any SAR filing. The scale of the multi-account graph
            # corroboration is the justification; automatic SAR filing is deferred.
            if ring_size >= SYNDICATE_CARD_THRESHOLD and gate_explicitly_locked:
                actions.append(ActionRecommendation(
                    action="ESCALATE_TO_ANALYST",
                    approval_route="L2",
                    reason=(
                        f"R6-syndicate: device shared across {ring_size} independent card accounts. "
                        "Mandatory Level-2 human authorization required before SAR filing."
                    ),
                    role=ActionRole.PRIMARY,
                    scope=ActionScope.ESCALATION
                ))
                actions.append(ActionRecommendation(
                    action="CREATE_CASE",
                    approval_route="auto",
                    reason="R6-syndicate: internal syndicate case opened with graph-corroborated evidence.",
                    role=ActionRole.CONSEQUENTIAL,
                    scope=ActionScope.CASE_MANAGEMENT
                ))
                actions.append(ActionRecommendation(
                    action="MONITOR_CONNECTED_CARDS",
                    approval_route="auto",
                    reason=f"R6-syndicate: place all {ring_size} connected cards under elevated monitoring.",
                    role=ActionRole.CONSEQUENTIAL,
                    scope=ActionScope.CARD_ACCOUNT
                ))
                return actions

            actions.append(ActionRecommendation(
                action="CREATE_CASE",
                approval_route="auto",
                reason="R6: Coordinated fraud ring detected across shared device/region.",
                role=ActionRole.PRIMARY,
                scope=ActionScope.CASE_MANAGEMENT
            ))
            actions.append(ActionRecommendation(
                action="FILE_REPORT",
                approval_route="L2",
                reason="R6: Suspicious activity report filing for syndicate fraud ring.",
                role=ActionRole.CONSEQUENTIAL,
                scope=ActionScope.CASE_MANAGEMENT
            ))
            actions.append(ActionRecommendation(
                action="MONITOR_CONNECTED_CARDS",
                approval_route="auto",
                reason="R6: Place all connected cards on elevated monitoring.",
                role=ActionRole.CONSEQUENTIAL,
                scope=ActionScope.CARD_ACCOUNT
            ))
            return actions

        # Rule R9: Undocumented pattern with corroborated, high-confidence evidence of abuse
        # Governance hardening: an undocumented typology only escalates to a full
        # case + regulatory report when the posterior is very high (>= 0.85) AND the
        # investigation has material coverage (>= 0.40, aligned with the decision gate).
        # Thin/uncorroborated undocumented patterns receive a non-punitive MONITOR / VERIFY posture.
        if is_undocumented and fraud_probability >= 0.85 and (coverage is None or coverage >= 0.40) and case_context.get("decision_gate_passed") is not False:
            actions.append(ActionRecommendation(
                action="CREATE_CASE",
                approval_route="auto",
                reason="R9: Coordinated anomalous activity fitting no standard typology.",
                role=ActionRole.PRIMARY,
                scope=ActionScope.CASE_MANAGEMENT
            ))
            actions.append(ActionRecommendation(
                action="FILE_REPORT",
                approval_route="L2",
                reason="R9: Regulatory report for novel/undocumented fraud scheme.",
                role=ActionRole.CONSEQUENTIAL,
                scope=ActionScope.CASE_MANAGEMENT
            ))
            actions.append(ActionRecommendation(
                action="ESCALATE_TO_ANALYST",
                approval_route="auto",
                reason="R9: Hand off novel pattern to senior fraud analyst.",
                role=ActionRole.CONSEQUENTIAL,
                scope=ActionScope.ESCALATION
            ))
            return actions

        # Rule R9-thin: Undocumented pattern without corroboration / material coverage.
        if is_undocumented and fraud_probability >= 0.70 and (
            case_context.get("decision_gate_passed") is False
            or (coverage is not None and coverage < 0.40)
        ):
            gate_locked = case_context.get("decision_gate_passed") is False
            actions.append(ActionRecommendation(
                action="MONITOR_CARD",
                approval_route="auto",
                reason=(
                    "R9-thin: High posterior on an undocumented pattern without "
                    + ("a passed decision gate (corroboration required)." if gate_locked
                       else f"material coverage (coverage={coverage:.2f} < 0.40).")
                    + " Punitive blocking withheld; monitor and corroborate before escalation."
                ),
                role=ActionRole.PRIMARY,
                scope=ActionScope.CARD_ACCOUNT
            ))
            actions.append(ActionRecommendation(
                action="VERIFY_WITH_CUSTOMER",
                approval_route="auto",
                reason="R9-thin: Request cardholder confirmation to corroborate an undocumented pattern.",
                role=ActionRole.SECONDARY,
                scope=ActionScope.CUSTOMER
            ))
            return actions

        # Rule R1: Verify before block on weak signal
        if is_single_signal and 0.30 < fraud_probability < 0.70:
            actions.append(ActionRecommendation(
                action="VERIFY_WITH_CUSTOMER",
                approval_route="auto",
                reason="R1: Weak single signal (fraud prob < 0.70); verify before punitive action.",
                role=ActionRole.PRIMARY,
                scope=ActionScope.CUSTOMER
            ))
            actions.append(ActionRecommendation(
                action="MONITOR_CARD",
                approval_route="auto",
                reason="R1: Monitor card while awaiting customer verification.",
                role=ActionRole.CONSEQUENTIAL,
                scope=ActionScope.CARD_ACCOUNT
            ))
            return actions

        # Rule R8: Uncertain and exposed
        if verdict == "uncertain" and exposure_usd > 500.0:
            actions.append(ActionRecommendation(
                action="ESCALATE_TO_ANALYST",
                approval_route="auto",
                reason="R8: Uncertain verdict with exposure exceeding $500 threshold.",
                role=ActionRole.PRIMARY,
                scope=ActionScope.ESCALATION
            ))
            actions.append(ActionRecommendation(
                action="MONITOR_CARD",
                approval_route="auto",
                reason="R8: Maintain card monitoring pending analyst review.",
                role=ActionRole.CONSEQUENTIAL,
                scope=ActionScope.CARD_ACCOUNT
            ))
            return actions

        # General High Confidence Fraud (>= 0.70)
        if fraud_probability >= 0.70:
            # Gate-aware governance: when the decision gate is explicitly locked
            # (e.g. uncorroborated evidence), terminal punitive blocking is
            # inadmissible. Evidence-specific containment rules (R2/R5/R6) above
            # remain authoritative; the generic fallback degrades to MONITOR/VERIFY.
            if case_context.get("decision_gate_passed") is False and not customer_denied:
                actions.append(ActionRecommendation(
                    action="MONITOR_CARD",
                    approval_route="auto",
                    reason=(
                        f"High posterior ({fraud_probability:.2f}) but decision gate is LOCKED; "
                        "punitive blocking withheld pending corroboration."
                    ),
                    role=ActionRole.PRIMARY,
                    scope=ActionScope.CARD_ACCOUNT
                ))
                actions.append(ActionRecommendation(
                    action="VERIFY_WITH_CUSTOMER",
                    approval_route="auto",
                    reason="Corroborate the unresolved high-posterior signal via cardholder verification.",
                    role=ActionRole.SECONDARY,
                    scope=ActionScope.CUSTOMER
                ))
                return actions

            actions.append(ActionRecommendation(
                action="BLOCK_CARD",
                approval_route=self.determine_block_card_route(exposure_usd),
                reason=f"High assessed fraud probability ({fraud_probability:.2f}).",
                role=ActionRole.PRIMARY,
                scope=ActionScope.CARD_ACCOUNT
            ))
            actions.append(ActionRecommendation(
                action="CREATE_CASE",
                approval_route="auto",
                reason="Internal fraud case opened with evidence.",
                role=ActionRole.CONSEQUENTIAL,
                scope=ActionScope.CASE_MANAGEMENT
            ))
            if exposure_usd >= 1000.0:
                actions.append(ActionRecommendation(
                    action="FILE_REPORT",
                    approval_route="L2",
                    reason="Exposure >= $1,000 mandates regulatory SAR filing.",
                    role=ActionRole.CONSEQUENTIAL,
                    scope=ActionScope.CASE_MANAGEMENT
                ))
            return actions

        # General Low Confidence / Legitimate (<= 0.30)
        if fraud_probability <= 0.30:
            actions.append(ActionRecommendation(
                action="ALLOW_TRANSACTION",
                approval_route="auto",
                reason=f"Low fraud probability ({fraud_probability:.2f}) consistent with normal usage.",
                role=ActionRole.PRIMARY,
                scope=ActionScope.TRANSACTION
            ))
            actions.append(ActionRecommendation(
                action="CLOSE_NO_FRAUD",
                approval_route="auto",
                reason="Alert cleared as legitimate cardholder activity.",
                role=ActionRole.CONSEQUENTIAL,
                scope=ActionScope.CASE_MANAGEMENT
            ))
            return actions

        # Default fallback: Monitor & Verify
        actions.append(ActionRecommendation(
            action="MONITOR_CARD",
            approval_route="auto",
            reason="Ambiguous signals warrant 72-hour elevated monitoring.",
            role=ActionRole.PRIMARY,
            scope=ActionScope.CARD_ACCOUNT
        ))
        actions.append(ActionRecommendation(
            action="VERIFY_WITH_CUSTOMER",
            approval_route="auto",
            reason="Request cardholder confirmation to resolve ambiguity.",
            role=ActionRole.SECONDARY,
            scope=ActionScope.CUSTOMER
        ))
        return actions
