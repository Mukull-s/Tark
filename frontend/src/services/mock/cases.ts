import { CaseAnswerFile, BenchmarkCaseSummary } from '../../types/investigation';

// 20 Official Benchmark Cases from case_pack.csv
export const BENCHMARK_CASES: BenchmarkCaseSummary[] = [
  { id: 'HHG-001', opened_at: '2016-12-05 01:55:28', type: 'risk_score', desc: 'Score 0.61 ($77.07, region 444.0)', flagged_txn_id: '3514030', card_id: 'C12382-K1', customer_id: 'C12382', risk_score: 0.61 },
  { id: 'HHG-002', opened_at: '2016-11-22 23:27:07', type: 'risk_score', desc: 'Score 0.79 ($292.36, online)', flagged_txn_id: '3478782', card_id: 'C11891-K1', customer_id: 'C11891', risk_score: 0.79 },
  { id: 'HHG-003', opened_at: '2016-12-10 15:01:21', type: 'customer_report', desc: 'Dispute $49.00 purchase (ref 3530164)', flagged_txn_id: '3530164', card_id: 'C08623-K2', customer_id: 'C08623' },
  { id: 'HHG-004', opened_at: '2016-12-29 07:53:54', type: 'customer_report', desc: 'Dispute $128.33 purchase (ref 3583227)', flagged_txn_id: '3583227', card_id: 'C08106-K1', customer_id: 'C08106' },
  { id: 'HHG-005', opened_at: '2016-12-08 03:38:37', type: 'risk_score', desc: 'Score 0.54 ($100.07, online)', flagged_txn_id: '3523199', card_id: 'C02923-K1', customer_id: 'C02923', risk_score: 0.54 },
  { id: 'HHG-006', opened_at: '2016-11-22 02:30:00', type: 'customer_report', desc: 'Dispute $482.12 purchase (ref 3476682)', flagged_txn_id: '3476682', card_id: 'C07297-K1', customer_id: 'C07297' },
  { id: 'HHG-007', opened_at: '2016-12-05 03:46:14', type: 'risk_score', desc: 'Score 0.87 ($111.92, region 264.0)', flagged_txn_id: '3514948', card_id: 'C09933-K2', customer_id: 'C09933', risk_score: 0.87 },
  { id: 'HHG-008', opened_at: '2016-12-20 03:08:56', type: 'customer_report', desc: 'Dispute $55.68 purchase (ref 3558054)', flagged_txn_id: '3558054', card_id: 'C13171-K2', customer_id: 'C13171' },
  { id: 'HHG-009', opened_at: '2016-12-28 17:10:53', type: 'customer_report', desc: 'Dispute $30.02 purchase (ref 3581141)', flagged_txn_id: '3581141', card_id: 'C08299-K1', customer_id: 'C08299' },
  { id: 'HHG-010', opened_at: '2016-12-02 18:18:27', type: 'risk_score', desc: 'Score 0.90 ($1,000.03, online)', flagged_txn_id: '3506725', card_id: 'C10434-K1', customer_id: 'C10434', risk_score: 0.90 },
  { id: 'HHG-011', opened_at: '2016-12-29 06:27:44', type: 'customer_report', desc: 'Dispute $131.30 purchase (ref 3583368)', flagged_txn_id: '3583368', card_id: 'C11923-K2', customer_id: 'C11923' },
  { id: 'HHG-012', opened_at: '2016-12-18 05:00:31', type: 'risk_score', desc: 'Score 0.55 ($30.91, region 494.0)', flagged_txn_id: '3553342', card_id: 'C05876-K2', customer_id: 'C05876', risk_score: 0.55 },
  { id: 'HHG-013', opened_at: '2016-12-09 05:39:29', type: 'risk_score', desc: 'Score 0.76 ($35.66, online)', flagged_txn_id: '3526826', card_id: 'C07671-K2', customer_id: 'C07671', risk_score: 0.76 },
  { id: 'HHG-014', opened_at: '2016-11-22 20:11:00', type: 'analyst_request', desc: 'Shared device review (ref 3478561)', flagged_txn_id: '3478561', card_id: 'C13487-K1', customer_id: 'C13487' },
  { id: 'HHG-015', opened_at: '2016-11-17 19:03:36', type: 'risk_score', desc: 'Score 0.77 ($599.94, online)', flagged_txn_id: '3464869', card_id: 'C03042-K1', customer_id: 'C03042', risk_score: 0.77 },
  { id: 'HHG-016', opened_at: '2016-12-12 01:39:08', type: 'customer_report', desc: 'Dispute $59.67 purchase (ref 3534820)', flagged_txn_id: '3534820', card_id: 'C09988-K1', customer_id: 'C09988' },
  { id: 'HHG-017', opened_at: '2016-11-12 00:46:24', type: 'risk_score', desc: 'Score 0.57 ($100.09, online) [ACTIVE DEMO]', flagged_txn_id: '3450629', card_id: 'C04570-K1', customer_id: 'C04570', risk_score: 0.57 },
  { id: 'HHG-018', opened_at: '2016-11-27 14:41:26', type: 'customer_report', desc: 'Dispute $39.08 purchase (ref 3491361)', flagged_txn_id: '3491361', card_id: 'C02354-K2', customer_id: 'C02354' },
  { id: 'HHG-019', opened_at: '2016-12-01 22:28:53', type: 'risk_score', desc: 'Score 0.90 ($99.92, online)', flagged_txn_id: '3503878', card_id: 'C07987-K2', customer_id: 'C07987', risk_score: 0.90 },
  { id: 'HHG-020', opened_at: '2016-12-03 12:04:26', type: 'risk_score', desc: 'Score 0.52 ($125.08, online)', flagged_txn_id: '3509359', card_id: 'C12265-K2', customer_id: 'C12265', risk_score: 0.52 }
];

// Complete fixture for HHG-017
export const MOCK_CASE_HHG017: CaseAnswerFile = {
  case_id: "HHG-017",
  case: {
    status: "closed_fraud",
    verdict: "fraud",
    fraud_probability: 0.86,
    pattern: "card_testing",
    pattern_description: "Card testing sequence: 3 rapid sub-$3 online authorizations followed by a larger transaction.",
    affected_txn_ids: ["3450620", "3450621", "3450622", "3450629"],
    first_suspicious_txn_id: "3450620",
    connected_card_ids: ["C00877-K1"],
    connected_device_profiles: [
      "SAMSUNG SM-G892A Build/NRD90M | Android 7.0 | samsung browser 6.2 | 2220x1080"
    ],
    exposure_usd: 268.43,
    evidence: [
      {
        claim: "Three online authorizations under $3 within 40 minutes, then a $100.09 purchase under a product code this card has never used",
        source: "graph",
        ref: "query:card_window(card_id=C04570-K1, window_hours=1)",
        entity_ids: ["3450620", "3450621", "3450622", "3450629"],
        category: "TRANSACTION",
        why_it_matters: "Micro-authorizations are the classic signature of bot-driven card testing before making large fraud purchases.",
        timestamp: "2016-11-12 00:05:12"
      },
      {
        claim: "All four came from a device profile marked New for this account (Android 7.0, Samsung Browser, 2220x1080), seen on closed case CC-0141 and on card C00877-K1 this month",
        source: "graph",
        ref: "query:device_neighbors(profile_id=SAMSUNG SM-G892A...)",
        entity_ids: ["CC-0141", "C00877-K1"],
        category: "DEVICE",
        why_it_matters: "Direct graph linkage to confirmed past fraud and another active card confirms an organized syndicate.",
        timestamp: "2016-11-12 00:46:24"
      },
      {
        claim: "Customer denied the purchases when asked via customer transaction validation",
        source: "customer",
        ref: "evidence_request:1",
        entity_ids: ["C04570"],
        category: "CUSTOMER",
        why_it_matters: "Direct customer denial eliminates false-positive merchant categorization ambiguity.",
        timestamp: "2016-11-12 01:02:18"
      },
      {
        claim: "Graph cluster links card C04570-K1 to compromised entity network via shared device profile",
        source: "graph",
        ref: "query:find_prior_cases(pattern=card_testing)",
        entity_ids: ["CC-0141"],
        category: "NETWORK",
        why_it_matters: "Shared hardware fingerprint connects multiple independent account takeover incidents.",
        timestamp: "2016-11-12 00:47:00"
      }
    ],
    similar_prior_cases: ["CC-0141"],
    summary: "Textbook card testing: three sub-$3 online authorizations in 40 minutes, then a $100.09 purchase in a category the cardholder has never used. All four share a device profile marked New for this account, which appears on a closed case from August (CC-0141) and on another card this month. Customer denied the activity. Card compromised; a second card is likely compromised through the same device.",
    written_to_graph: true,
    graph_case_id: "CASE-2016-1187"
  },
  evidence_requests: [
    {
      type: "customer_validation",
      asked_after_step: 4,
      assumed_response: "Customer states they did not make these purchases and still has the card",
      reason: "Initial pattern score is 0.72; customer confirmation is required to distinguish between authorized user testing and account takeover.",
      status: "received"
    }
  ],
  next_best_actions: {
    initial: [
      {
        action: "DECLINE_TRANSACTION",
        route: "L1",
        reason: "Policy Rule R5: testing sequence observed, flagged purchase pending clearance.",
        supporting_evidence: ["3 rapid micro-charges under $3 within 40 minutes"]
      },
      {
        action: "VERIFY_WITH_CUSTOMER",
        route: "auto",
        reason: "Policy Rule R1: investigation confidence 0.72 on pattern alone, confirm before irrevocable blocking.",
        supporting_evidence: ["New device profile without prior customer history"]
      }
    ],
    final: [
      {
        action: "BLOCK_CARD",
        route: "L1",
        reason: "Policy Rules R2 and R5: customer denied purchases; exposure $268.43 is under $2,500 threshold.",
        supporting_evidence: [
          "Customer explicitly denied transactions",
          "Confirmed card testing velocity pattern",
          "Hardware signature shared with compromised card C00877-K1"
        ]
      },
      {
        action: "CREATE_CASE",
        route: "auto",
        reason: "Policy Rule R2: internal fraud case record opened and written to TigerGraph Savanna.",
        supporting_evidence: ["Exposure $268.43 logged in Graph Case Memory"]
      },
      {
        action: "FILE_REPORT",
        route: "L2",
        reason: "Policy Rules R2 and R6: shared device links this card to another compromised card (syndicate pattern).",
        supporting_evidence: ["Organized network connection to closed fraud case CC-0141"]
      },
      {
        action: "MONITOR_CONNECTED_CARDS",
        route: "auto",
        reason: "Policy Rule R6: same device profile active on card C00877-K1 within trailing 30 days.",
        supporting_evidence: ["Shared Device Profile: SAMSUNG SM-G892A Build/NRD90M"]
      }
    ],
    what_changed: "Customer denial raised investigation confidence from 0.72 to 0.86 and confirmed the card block. Shared device profile with C00877-K1 escalated routing to trigger an L2 FinCEN SAR filing and proactive monitoring of connected cards."
  },
  sar: {
    file: true,
    reason: "Policy Rules R2 and R6: confirmed unauthorized card use linked by a shared device to a second compromised card",
    narrative: "On 2016-11-12 between 00:05 and 00:46, card C04570-K1 belonging to customer C04570 was used for three online authorizations under $3 followed at 00:46 by a $100.09 online purchase under a product code the cardholder had never used. All four transactions came from a device profile marked New for this account, previously recorded on closed case CC-0141 (confirmed fraud) and on card C00877-K1. The cardholder stated they did not make these purchases and remained in possession of the card. The sequence of small authorizations followed by a larger purchase is consistent with testing of a stolen card number prior to use. The shared device indicates a common actor across at least two cardholders. Total unauthorized amount: $268.43. Card blocked and scheduled for reissue; card C00877-K1 placed under monitoring.",
    subjects: ["C04570", "C04570-K1", "C00877-K1"],
    total_amount_usd: 268.43,
    activity_dates: ["2016-11-12", "2016-11-12"]
  },
  stop_reason: "Customer denial settled the verdict; device link identified and connected card protected. Further steps would not change the actions.",
  tool_calls: 9,
  tokens: 12480,
  latency_s: 18.7
};

// Generates realistic case data for any of the 20 benchmark cases if not individually hardcoded
export function getMockCase(caseId: string): CaseAnswerFile {
  if (caseId === "HHG-017") {
    return MOCK_CASE_HHG017;
  }

  const meta = BENCHMARK_CASES.find((c) => c.id === caseId) || {
    id: caseId,
    opened_at: '2016-12-01 12:00:00',
    type: 'risk_score' as const,
    desc: `Benchmark case ${caseId}`,
    flagged_txn_id: '3500000',
    card_id: 'C99999-K1',
    customer_id: 'C99999',
    risk_score: 0.65
  };

  const isFraud = (meta.risk_score || 0) > 0.6 || meta.type === 'customer_report';
  const exposure = meta.risk_score ? meta.risk_score * 350 + 45 : 180.5;

  return {
    case_id: meta.id,
    case: {
      status: isFraud ? "closed_fraud" : "closed_legitimate",
      verdict: isFraud ? "fraud" : "legitimate",
      fraud_probability: meta.risk_score || (isFraud ? 0.78 : 0.22),
      pattern: isFraud ? "card_not_present_new_device" : "none",
      pattern_description: isFraud
        ? "Card not present transaction from previously unseen device profile."
        : "Legitimate customer purchase with routine travel pattern.",
      affected_txn_ids: [meta.flagged_txn_id || '3500000'],
      first_suspicious_txn_id: meta.flagged_txn_id || '3500000',
      connected_card_ids: [],
      connected_device_profiles: ["Chrome 54.0 | Windows 10 | 1920x1080"],
      exposure_usd: Number(exposure.toFixed(2)),
      evidence: [
        {
          claim: meta.desc,
          source: meta.type === 'customer_report' ? 'customer' : 'graph',
          ref: `alert:${meta.flagged_txn_id || '3500000'}`,
          entity_ids: [meta.flagged_txn_id || '3500000'],
          category: "TRANSACTION",
          why_it_matters: "Triggering event evaluated during benchmark exam period.",
          timestamp: meta.opened_at || '2016-12-01 12:00:00'
        },
        {
          claim: `Customer account ${meta.customer_id} historical baseline analyzed via TigerGraph`,
          source: "graph",
          ref: `query:card_window(card_id=${meta.card_id})`,
          entity_ids: [meta.customer_id || 'C00001', meta.card_id || 'K1'],
          category: "CUSTOMER",
          why_it_matters: "Evaluates standard volume and channel frequency for cardholder.",
          timestamp: meta.opened_at || '2016-12-01 12:05:00'
        }
      ],
      similar_prior_cases: isFraud ? ["CC-0098"] : [],
      summary: `Investigation for alert on transaction ${meta.flagged_txn_id}. ${
        isFraud
          ? 'Card compromised by third party; authorization declined and card blocked.'
          : 'Activity consistent with cardholder normal spending profile; cleared as false alarm.'
      }`,
      written_to_graph: true,
      graph_case_id: `CASE-2016-${caseId.replace('HHG-', '9')}`
    },
    evidence_requests: isFraud
      ? [
          {
            type: "customer_validation",
            asked_after_step: 3,
            assumed_response: "Customer validated transaction context",
            reason: "Verify transaction legitimacy with account holder",
            status: "received"
          }
        ]
      : [],
    next_best_actions: {
      initial: [
        {
          action: isFraud ? "DECLINE_TRANSACTION" : "ALLOW_TRANSACTION",
          route: isFraud ? "L1" : "auto",
          reason: isFraud ? "Initial risk model score above threshold." : "Low anomaly score observed."
        }
      ],
      final: [
        {
          action: isFraud ? "BLOCK_CARD" : "CLOSE_NO_FRAUD",
          route: isFraud ? "L1" : "auto",
          reason: isFraud ? "Confirmed unauthorized transaction." : "Cleared after account profile review."
        },
        {
          action: isFraud ? "CREATE_CASE" : "ALLOW_TRANSACTION",
          route: "auto",
          reason: isFraud ? "Logged to case memory." : "Transaction authorized."
        }
      ],
      what_changed: isFraud
        ? "Investigation confirmed unauthorized device linkage, elevating action to BLOCK_CARD."
        : "Customer history verification cleared suspicious flag."
    },
    sar: {
      file: isFraud && exposure > 250,
      reason: isFraud ? "Confirmed unauthorized transaction exceeding filing threshold" : "No fraud detected",
      narrative: isFraud
        ? `On ${meta.opened_at}, unauthorized transaction ${meta.flagged_txn_id} was attempted on card ${meta.card_id}. Card blocked.`
        : "Filing not required.",
      subjects: [meta.customer_id || "C00000", meta.card_id || "K1"],
      total_amount_usd: Number(exposure.toFixed(2)),
      activity_dates: [meta.opened_at?.split(' ')[0] || "2016-12-01"]
    },
    stop_reason: "Investigation completed. Evidence sufficient for definitive next best action.",
    tool_calls: 5,
    tokens: 8200,
    latency_s: 12.4
  };
}
