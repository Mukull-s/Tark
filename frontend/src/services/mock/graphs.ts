import { GraphData } from '../../types/investigation';

export const MOCK_GRAPH_HHG017: GraphData = {
  case_id: "HHG-017",
  nodes: [
    {
      id: "cust_C04570",
      label: "Customer C04570",
      type: "customer",
      properties: {
        customer_id: "C04570",
        tenure_months: 28,
        risk_tier: "LOW",
        total_cards: 1,
        billing_region: "444.0"
      }
    },
    {
      id: "card_C04570_K1",
      label: "Card C04570-K1",
      type: "card",
      properties: {
        card_id: "C04570-K1",
        brand: "Visa",
        type: "Credit",
        issued_date: "2015-06-14",
        status: "ACTIVE_INVESTIGATION"
      }
    },
    {
      id: "card_C00877_K1",
      label: "Card C00877-K1 (Compromised)",
      type: "card_compromised",
      properties: {
        card_id: "C00877-K1",
        brand: "Mastercard",
        type: "Credit",
        status: "BLOCKED",
        compromised_date: "2016-11-04",
        reason: "Shared Device Fraud Ring"
      }
    },
    {
      id: "dev_samsung",
      label: "Samsung SM-G892A (New Device)",
      type: "device",
      properties: {
        profile_id: "SAMSUNG SM-G892A Build/NRD90M",
        os: "Android 7.0",
        browser: "Samsung Browser 6.2",
        screen: "2220x1080",
        is_new: "true",
        proxy_flag: "false",
        linked_cards_count: 2
      }
    },
    {
      id: "tx_3450620",
      label: "Tx 3450620 ($1.25)",
      type: "txn_testing",
      properties: {
        transaction_id: "3450620",
        amount: 1.25,
        channel: "online",
        timestamp: "2016-11-12 00:05:12",
        product_cd: "C",
        risk_score: 0.21,
        description: "Micro-authorization / Card Testing"
      }
    },
    {
      id: "tx_3450621",
      label: "Tx 3450621 ($2.10)",
      type: "txn_testing",
      properties: {
        transaction_id: "3450621",
        amount: 2.10,
        channel: "online",
        timestamp: "2016-11-12 00:18:44",
        product_cd: "C",
        risk_score: 0.28,
        description: "Micro-authorization / Card Testing"
      }
    },
    {
      id: "tx_3450622",
      label: "Tx 3450622 ($0.95)",
      type: "txn_testing",
      properties: {
        transaction_id: "3450622",
        amount: 0.95,
        channel: "online",
        timestamp: "2016-11-12 00:32:01",
        product_cd: "C",
        risk_score: 0.31,
        description: "Micro-authorization / Card Testing"
      }
    },
    {
      id: "tx_3450629",
      label: "Tx 3450629 ($100.09) [FLAGGED]",
      type: "txn_flagged",
      properties: {
        transaction_id: "3450629",
        amount: 100.09,
        channel: "online",
        timestamp: "2016-11-12 00:46:24",
        product_cd: "R",
        risk_score: 0.57,
        anomaly: "New product category + High velocity jump"
      }
    },
    {
      id: "case_CC0141",
      label: "Closed Case CC-0141",
      type: "closed_case",
      properties: {
        case_id: "CC-0141",
        outcome: "confirmed_fraud",
        pattern: "card_testing",
        exposure_usd: 312.50,
        closed_at: "2016-08-22",
        analyst_notes: "Card testing sequence on same Samsung hardware signature."
      }
    }
  ],
  edges: [
    { source: "cust_C04570", target: "card_C04570_K1", label: "OWNS" },
    { source: "card_C04570_K1", target: "tx_3450620", label: "MADE" },
    { source: "card_C04570_K1", target: "tx_3450621", label: "MADE" },
    { source: "card_C04570_K1", target: "tx_3450622", label: "MADE" },
    { source: "card_C04570_K1", target: "tx_3450629", label: "MADE" },
    { source: "tx_3450620", target: "dev_samsung", label: "FROM_DEVICE" },
    { source: "tx_3450621", target: "dev_samsung", label: "FROM_DEVICE" },
    { source: "tx_3450622", target: "dev_samsung", label: "FROM_DEVICE" },
    { source: "tx_3450629", target: "dev_samsung", label: "FROM_DEVICE" },
    { source: "card_C00877_K1", target: "dev_samsung", label: "SHARED_DEVICE" },
    { source: "case_CC0141", target: "dev_samsung", label: "INVOLVES_DEVICE" }
  ]
};

export function getMockGraph(caseId: string): GraphData {
  if (caseId === "HHG-017") {
    return MOCK_GRAPH_HHG017;
  }

  // Generate generic connected graph for other cases
  return {
    case_id: caseId,
    nodes: [
      {
        id: `cust_${caseId}`,
        label: `Customer ${caseId}`,
        type: "customer",
        properties: { status: "ACTIVE", registered_region: "US-EAST" }
      },
      {
        id: `card_${caseId}`,
        label: `Card for ${caseId}`,
        type: "card",
        properties: { network: "Visa", brand: "Classic" }
      },
      {
        id: `tx_flagged_${caseId}`,
        label: `Flagged Txn (${caseId})`,
        type: "txn_flagged",
        properties: { amount: 150.00, risk_score: 0.74, channel: "online" }
      },
      {
        id: `dev_${caseId}`,
        label: `Device Profile`,
        type: "device",
        properties: { os: "Windows 10", browser: "Chrome 54", screen: "1920x1080" }
      }
    ],
    edges: [
      { source: `cust_${caseId}`, target: `card_${caseId}`, label: "OWNS" },
      { source: `card_${caseId}`, target: `tx_flagged_${caseId}`, label: "MADE" },
      { source: `tx_flagged_${caseId}`, target: `dev_${caseId}`, label: "FROM_DEVICE" }
    ]
  };
}
