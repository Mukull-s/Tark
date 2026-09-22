from typing import Dict, List, Optional
from src.knowledge.models import KnowledgeChunk, KnowledgeCategory


class InvestigationKnowledgeBase:
    """In-memory authoritative knowledge base containing Bank Fraud Policies (R1-R10),
    Core Fraud Typology Mechanics, and Regulatory Statutes (FinCEN, FATF, Regulation E).
    """

    def __init__(self):
        self._chunks: Dict[str, KnowledgeChunk] = {}
        self._populate_corpus()

    def _add(self, chunk: KnowledgeChunk):
        self._chunks[chunk.chunk_id] = chunk

    def _populate_corpus(self):
        # ----------------------------------------------------------------------
        # 1. Bank Fraud Policy Rules (R1 - R10)
        # ----------------------------------------------------------------------
        self._add(KnowledgeChunk(
            chunk_id="KNOW-POLICY-R1",
            title="Rule R1: Verification Before Action on Weak Single Signal",
            category=KnowledgeCategory.POLICY_RULE,
            text="When fraud probability is below 0.70 and supported by only a single uncorroborated evidence signal, "
                 "punitive account or card blocking is prohibited. The system must issue VERIFY_WITH_CUSTOMER and place "
                 "the card under elevated MONITOR_CARD for 72 hours. Approval route: auto.",
            applicable_rules=["R1"],
            applicable_typologies=["single_signal", "borderline_alert"],
            governing_body="Bank Risk Governance",
            section_reference="Policy Manual § 4.1 (Rule R1)",
            version="2026.1",
            provenance="Risk Policy Manual v4.2"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-POLICY-R2",
            title="Rule R2: Customer Direct Dispute / Transaction Denial",
            category=KnowledgeCategory.POLICY_RULE,
            text="If a cardholder reports or formally denies a transaction (CUSTOMER_DENIAL), the card must be blocked "
                 "(BLOCK_CARD) and an internal fraud case opened (CREATE_CASE). If total exposure exceeds $1,000 or the card "
                 "is linked to a shared device ring, a formal Suspicious Activity Report (FILE_REPORT) must be routed to Level 2 (L2) "
                 "compliance for filing under 31 CFR 1020.320. Approval route: L1 if exposure <= $2,500; L2 if exposure > $2,500.",
            applicable_rules=["R2"],
            applicable_typologies=["customer_dispute", "unauthorized_transaction"],
            governing_body="Bank Risk Governance & FinCEN",
            section_reference="Policy Manual § 4.2 (Rule R2)",
            version="2026.1",
            provenance="Risk Policy Manual v4.2"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-POLICY-R3",
            title="Rule R3: Cardholder Legitimate Transaction Confirmation",
            category=KnowledgeCategory.POLICY_RULE,
            text="If the cardholder explicitly confirms the transaction as legitimate and authorized (CUSTOMER_CONFIRMATION), "
                 "the alert is cleared with CLOSE_NO_FRAUD. If an emulator or new device was involved, the device profile is added "
                 "to the customer's recognized baseline to suppress future false alarms. Approval route: auto.",
            applicable_rules=["R3"],
            applicable_typologies=["confirmed_legitimate", "travel_notice"],
            governing_body="Bank Risk Governance",
            section_reference="Policy Manual § 4.3 (Rule R3)",
            version="2026.1",
            provenance="Risk Policy Manual v4.2"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-POLICY-R4",
            title="Rule R4: Out-of-Region Card-Present Activity Without Travel Notice",
            category=KnowledgeCategory.POLICY_RULE,
            text="When a card-present transaction occurs in a billing region with zero prior customer transaction history and no "
                 "active travel notification on file, DECLINE_TRANSACTION must be executed. The system initiates VERIFY_WITH_CUSTOMER "
                 "via registered mobile channel and monitors the account for further geographic anomalies. Approval route: auto.",
            applicable_rules=["R4"],
            applicable_typologies=["out_of_region_use", "geographic_anomaly"],
            governing_body="Bank Risk Governance",
            section_reference="Policy Manual § 4.4 (Rule R4)",
            version="2026.1",
            provenance="Risk Policy Manual v4.2"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-POLICY-R5",
            title="Rule R5: Card Testing and Micro-Authorization Sequences",
            category=KnowledgeCategory.POLICY_RULE,
            text="Upon detection of a rapid sequence of low-value micro-authorizations followed by a high-value purchase attempt "
                 "(CARD_TESTING_SEQUENCE), DECLINE_TRANSACTION must be executed immediately under Level 1 (L1) review. If exposure exceeds $100, "
                 "the card must be blocked (BLOCK_CARD). If exposure is <= $100, step-up multi-factor authentication (STEP_UP_AUTH) is mandated.",
            applicable_rules=["R5"],
            applicable_typologies=["card_testing", "micro_authorization"],
            governing_body="Bank Risk Governance",
            section_reference="Policy Manual § 4.5 (Rule R5)",
            version="2026.1",
            provenance="Risk Policy Manual v4.2"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-POLICY-R6",
            title="Rule R6: Shared Origin and Syndicate Device Rings",
            category=KnowledgeCategory.POLICY_RULE,
            text="When graph traversal reveals shared device infrastructure (SHARED_DEVICE_RING) or IP/proxy masking linking multiple "
                 "unrelated card accounts, CREATE_CASE is required, all connected cards must be placed under MONITOR_CONNECTED_CARDS, "
                 "and a syndicate fraud report (FILE_REPORT) must be routed to Level 2 (L2) AML/Fraud compliance. "
                 "R6-syndicate exception: when the ring spans 10 or more independent card accounts, the scale of the multi-account "
                 "graph corroboration mandates Level-2 human authorization (ESCALATE_TO_ANALYST) BEFORE any SAR filing; automatic "
                 "FILE_REPORT is deferred until that authorization is granted.",
            applicable_rules=["R6"],
            applicable_typologies=["shared_device", "fraud_ring", "syndicate"],
            governing_body="Bank Risk Governance",
            section_reference="Policy Manual § 4.6 (Rule R6)",
            version="2026.2",
            provenance="Risk Policy Manual v4.3"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-POLICY-R7",
            title="Rule R7: Disputed Charge Matching Recurring Billing Profile",
            category=KnowledgeCategory.POLICY_RULE,
            text="If a cardholder disputes a charge that matches an established recurring subscription interval and merchant baseline "
                 "(RECURRING_CHARGE_MATCH), CREATE_CASE is opened, but card blocking is withheld. The customer is issued a WARN_CUSTOMER "
                 "advisory regarding merchant cancellation procedures, and re-verification is requested. Approval route: auto.",
            applicable_rules=["R7"],
            applicable_typologies=["recurring_charge", "subscription_dispute"],
            governing_body="Bank Risk Governance",
            section_reference="Policy Manual § 4.7 (Rule R7)",
            version="2026.1",
            provenance="Risk Policy Manual v4.2"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-POLICY-R8",
            title="Rule R8: Uncertain Verdict with High Financial Exposure",
            category=KnowledgeCategory.POLICY_RULE,
            text="If posterior belief remains in the uncertain zone (0.30 < P(Fraud) < 0.70) or Decision Gate remains locked due to "
                 "epistemic uncertainty, and transaction exposure exceeds $500, the system must invoke ESCALATE_TO_ANALYST for manual "
                 "investigation while keeping the card on active MONITOR_CARD. Approval route: auto.",
            applicable_rules=["R8"],
            applicable_typologies=["uncertain_high_exposure", "borderline_alert"],
            governing_body="Bank Risk Governance",
            section_reference="Policy Manual § 4.8 (Rule R8)",
            version="2026.1",
            provenance="Risk Policy Manual v4.2"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-POLICY-R9",
            title="Rule R9: Undocumented Pattern with Clear Evidence of Abuse",
            category=KnowledgeCategory.POLICY_RULE,
            text="If activity exhibits high assessed fraud probability (P(Fraud) >= 0.70) but does not fit standard defined typologies, "
                 "CREATE_CASE is mandated, the card is blocked (BLOCK_CARD), and a special investigation report (FILE_REPORT) is routed to L2 "
                 "for pattern classification. Approval route: L2.",
            applicable_rules=["R9"],
            applicable_typologies=["undocumented", "novel_pattern"],
            governing_body="Bank Risk Governance",
            section_reference="Policy Manual § 4.9 (Rule R9)",
            version="2026.1",
            provenance="Risk Policy Manual v4.2"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-POLICY-R10",
            title="Rule R10: General Disposition Thresholds and Governance",
            category=KnowledgeCategory.POLICY_RULE,
            text="Final automated dispositions are governed strictly by calibrated posteriors: P(Fraud) >= 0.70 requires BLOCK_CARD and "
                 "CREATE_CASE (with FILE_REPORT if exposure >= $1,000); P(Fraud) <= 0.30 warrants ALLOW_TRANSACTION and CLOSE_NO_FRAUD; "
                 "intermediate values require MONITOR_CARD and VERIFY_WITH_CUSTOMER.",
            applicable_rules=["R10"],
            applicable_typologies=["general_thresholds"],
            governing_body="Bank Risk Governance",
            section_reference="Policy Manual § 4.10 (Rule R10)",
            version="2026.1",
            provenance="Risk Policy Manual v4.2"
        ))

        # ----------------------------------------------------------------------
        # 2. Core Fraud Typologies
        # ----------------------------------------------------------------------
        self._add(KnowledgeChunk(
            chunk_id="KNOW-TYPO-CARDTESTING",
            title="Fraud Typology: Card Testing / BIN Attacks",
            category=KnowledgeCategory.FRAUD_TYPOLOGY,
            text="Card testing involves automated scripts testing stolen card credentials against merchant portals with nominal authorization "
                 "amounts ($0.01 - $2.00) to confirm card validity before executing large fraudulent purchases. Key graph indicators: "
                 "high transaction velocity within 60 minutes, rapid merchant cycling, and micro-authorization sequences.",
            applicable_rules=["R5"],
            applicable_typologies=["card_testing", "micro_authorization", "velocity"],
            governing_body="FATF / Card Network Security",
            section_reference="Typology Catalog § 2.1",
            version="2026.1",
            provenance="Fraud Typology Catalog v3.0"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-TYPO-SHARED-DEVICE",
            title="Fraud Typology: Shared Device & Syndicate Mule Rings",
            category=KnowledgeCategory.FRAUD_TYPOLOGY,
            text="Organized fraud syndicates utilize shared device infrastructure (emulators, rooted mobile devices, proxy services) "
                 "to operate dozens of compromised or synthetic cardholder accounts from a single hardware footprint. Key graph indicators: "
                 "device vertex connected to > 5 distinct card accounts, anonymous proxy flags, and cross-account velocity.",
            applicable_rules=["R6"],
            applicable_typologies=["shared_device", "fraud_ring", "proxy_detected"],
            governing_body="FinCEN / Interpol Cybercrime",
            section_reference="Typology Catalog § 2.4",
            version="2026.1",
            provenance="Fraud Typology Catalog v3.0"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-TYPO-ATO",
            title="Fraud Typology: Account Takeover (ATO) and Credential Stuffing",
            category=KnowledgeCategory.FRAUD_TYPOLOGY,
            text="Account Takeover occurs when unauthorized third parties obtain legitimate customer credentials through phishing or dark web leaks. "
                 "The fraudster shifts channels (e.g. mobile to web or desktop Trident browser), updates contact metadata, and attempts high-value "
                 "CNP transactions from unrecognized devices. Key graph indicators: CNP_NEW_DEVICE, profile discrepancy, velocity burst.",
            applicable_rules=["R2", "R6"],
            applicable_typologies=["account_takeover", "cnp_new_device"],
            governing_body="FATF / Card Network Security",
            section_reference="Typology Catalog § 2.3",
            version="2026.1",
            provenance="Fraud Typology Catalog v3.0"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-TYPO-OUT-OF-REGION",
            title="Fraud Typology: Geographic Anomaly & Clone Counterfeiting",
            category=KnowledgeCategory.FRAUD_TYPOLOGY,
            text="Magnetic stripe skim or physical card counterfeiting is evidenced by physical card-present transactions occurring in foreign "
                 "or geographically distant billing regions while the legitimate cardholder retains custody of their authentic card. Key graph "
                 "indicators: billing region discrepancy, impossible travel velocity, and lack of prior regional transaction history.",
            applicable_rules=["R4"],
            applicable_typologies=["out_of_region_use", "clone_fraud"],
            governing_body="FATF Card Fraud Red Flags",
            section_reference="Typology Catalog § 2.2",
            version="2026.1",
            provenance="Fraud Typology Catalog v3.0"
        ))

        # ----------------------------------------------------------------------
        # 3. Regulatory Statutes (FinCEN, FATF, Reg E)
        # ----------------------------------------------------------------------
        self._add(KnowledgeChunk(
            chunk_id="KNOW-REG-FINCEN-SAR",
            title="Regulatory Statute: FinCEN Suspicious Activity Report (SAR) Requirements",
            category=KnowledgeCategory.REGULATORY_STATUTE,
            text="Under 31 CFR § 1020.320(a)(2), covered financial institutions must file a Suspicious Activity Report (SAR) "
                 "within 30 calendar days of initial detection for any transaction involving $5,000 or more where a suspect is identified "
                 "($25,000 or more for unidentified suspects, or any amount for insider abuse) if the bank knows, suspects, or has reason to "
                 "suspect illicit funds, regulatory evasion, or lack of lawful purpose. In accordance with Bank Risk Governance, Tark enforces "
                 "a heightened internal compliance threshold requiring Level 2 (L2) SAR filing review (FILE_REPORT) at exposure >= $1,000 or "
                 "upon detection of multi-card syndicate infrastructure (Rules R2, R6, R10).",
            applicable_rules=["R2", "R6", "R9", "R10"],
            applicable_typologies=["all_fraud", "shared_device", "syndicate"],
            governing_body="Financial Crimes Enforcement Network (FinCEN)",
            section_reference="31 CFR § 1020.320",
            version="2026.1",
            provenance="Federal Register / FinCEN Regulations"
        ))

        self._add(KnowledgeChunk(
            chunk_id="KNOW-REG-REGE",
            title="Regulatory Statute: Regulation E Electronic Fund Transfer Consumer Protection",
            category=KnowledgeCategory.REGULATORY_STATUTE,
            text="Under 12 CFR Part 1005 (Regulation E, implementing the Electronic Fund Transfer Act), financial institutions "
                 "must comply with strict error resolution procedures and consumer liability caps. Under 12 CFR § 1005.11(c)(1), "
                 "the general statutory timeline mandates investigating and resolving an alleged error within 10 business days of notice. "
                 "Under 12 CFR § 1005.11(c)(2), the institution may extend the investigation period up to 45 calendar days only on the "
                 "condition that it provisionally credits the consumer's account (with full access to funds) within 10 business days of notice "
                 "while the investigation continues; provisional credit is not an automatic unconditional grant but a statutory prerequisite "
                 "for utilizing the extended 45-day resolution window. Under § 1005.11(c)(3), the investigation window is extendable up to "
                 "90 calendar days for point-of-sale (POS) debit card transactions, foreign transactions, or new accounts within 30 days of opening. "
                 "Under 12 CFR § 1005.6, consumer liability for unauthorized transfers is strictly tiered based on notification timing "
                 "($50 if reported within 2 business days; $500 if reported within 60 calendar days of periodic statement), and zero consumer liability "
                 "attaches to any transactions occurring after the consumer notifies the institution (CUSTOMER_DENIAL).",
            applicable_rules=["R2", "R7"],
            applicable_typologies=["customer_dispute", "unauthorized_transaction"],
            governing_body="Consumer Financial Protection Bureau (CFPB)",
            section_reference="12 CFR §§ 1005.6, 1005.11",
            version="2026.1",
            provenance="Electronic Fund Transfer Act (Reg E)"
        ))

    def get_chunk(self, chunk_id: str) -> Optional[KnowledgeChunk]:
        return self._chunks.get(chunk_id)

    def all_chunks(self) -> List[KnowledgeChunk]:
        return list(self._chunks.values())

    def get_by_category(self, cat: KnowledgeCategory) -> List[KnowledgeChunk]:
        return [c for c in self._chunks.values() if c.category == cat]

    def get_by_rule(self, rule: str) -> List[KnowledgeChunk]:
        r_upper = rule.upper().strip()
        return [c for c in self._chunks.values() if r_upper in c.applicable_rules]

    def count(self) -> int:
        return len(self._chunks)
