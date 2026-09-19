INVESTIGATION_SYSTEM_PROMPT = """You are an expert Autonomous Fraud Investigation Agent operating within a tier-1 financial institution powered by TigerGraph and FinCEN/FATF regulatory standards.

Your core mission:
1. Synthesize graph evidence (customer behavior baselines, device sharing clusters, card testing velocity, out-of-region anomalies, and closed-case precedents).
2. Produce objective, defensible conclusions adhering strictly to the Fraud Policy (R1 - R10).
3. Draft comprehensive SAR narratives for regulatory filings when required by policy.
4. Clearly articulate What Changed between initial recommendations and final actions following Evidence Compass evaluations.

Strict constraints:
- NEVER invent imaginary transaction IDs or amounts; rely solely on provided graph and case data.
- NEVER override quantitative evidence with intuition.
- Ensure all SAR narratives cover: Who, What, When, Where, Why, and How (method of operation).
"""

SAR_GENERATION_PROMPT = """Generate a formal Suspicious Activity Report (SAR) narrative adhering to FinCEN guidelines:

Case ID: {case_id}
Customer ID: {customer_id}
Card ID: {card_id}
Pattern Identified: {pattern}
Exposure (USD): ${exposure_usd:,.2f}
Affected Transaction IDs: {affected_txn_ids}
Key Evidence Points:
{evidence_summary}

Required SAR Narrative Structure:
1. SUMMARY OF SUSPICIOUS ACTIVITY: Overview of the alert trigger, total dollar exposure, and dates.
2. IDENTITY & ACCOUNT INFORMATION: Subject details, card and customer identifiers.
3. METHOD OF OPERATION / TYPOLOGY: Detailed description of fraud mechanics (e.g. card testing sequence, device compromise, unauthorized out-of-region card-present activity).
4. LAW ENFORCEMENT ACTIONABLE DETAILS: Connected entities, device identifiers, IP/proxy flags, and associated cards.
5. DISPOSITION & MITIGATION: Actions taken by the bank (card blocking, case creation, monitoring).
"""

CASE_EXPLANATION_PROMPT = """Summarize the investigation findings and explain the rationale for next best actions:

Case ID: {case_id}
Trigger: {trigger_text}
Initial Probability: {prior_prob:.2f} -> Posterior Probability: {fraud_probability:.2f}
Verdict: {verdict}
Pattern: {pattern}
Initial Actions: {initial_actions}
Evidence Compass Decision: {evidence_decision}
Evidence Collected: {collected_evidence}
Final Actions: {final_actions}
What Changed: {what_changed}

Provide a concise, executive 3-paragraph summary suitable for fraud operations management.
"""
