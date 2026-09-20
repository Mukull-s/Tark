# Tark: Frontend - Backend - TigerGraph Integration Contract
**Version:** 1.0.0  
**Target Event:** HackerHouse Goa — TigerGraph Agentic Fraud Challenge  
**Parties:** Person 1 (Agent / Backend), Person 2 (TigerGraph / Data), Person 3 (Frontend / Product)

---

## 1. Overview & Architecture Protocol

- **Base URL:** `http://localhost:8000` (FastAPI)
- **Data Transfer:** JSON over HTTP, UTF-8 encoded
- **Streaming:** Server-Sent Events (SSE) over `text/event-stream`
- **Constraint:** Zero Docker. Local native execution.
- **Rule:** The frontend renders decisions from the agent and policy engine; it does NOT independently compute risk scores or determine policy routes.

---

## 2. Endpoints Specification

### 2.1 Benchmark Cases Summary List
`GET /api/cases`

Returns summary triggers for the 20 benchmark exam cases.

```json
[
  {
    "case_id": "HHG-017",
    "opened_at": "2016-11-12 00:46:24",
    "trigger_type": "risk_score",
    "trigger_text": "Real-time model scored transaction 3450629 ($100.09, online) at 0.57. Review and decide.",
    "flagged_txn_id": "3450629",
    "card_id": "C04570-K1",
    "customer_id": "C04570",
    "risk_score": 0.57
  }
]
```

---

### 2.2 Case Full Investigation Detail
`GET /api/cases/{case_id}`

Returns the full investigation payload (matches the official benchmark output schema `CaseAnswerFile`).

```json
{
  "case_id": "HHG-017",
  "case": {
    "status": "closed_fraud",
    "verdict": "fraud",
    "fraud_probability": 0.86,
    "pattern": "card_testing",
    "pattern_description": "",
    "affected_txn_ids": ["3450620", "3450621", "3450622", "3450629"],
    "first_suspicious_txn_id": "3450620",
    "connected_card_ids": ["C00877-K1"],
    "connected_device_profiles": [
      "SAMSUNG SM-G892A Build/NRD90M | Android 7.0 | samsung browser 6.2 | 2220x1080"
    ],
    "exposure_usd": 268.43,
    "evidence": [
      {
        "claim": "Three online authorizations under $3 within 40 minutes, then a $100.09 purchase under a product code this card has never used",
        "source": "graph",
        "ref": "query:card_window(card_id=C04570-K1, window_hours=1)",
        "entity_ids": ["3450620", "3450621", "3450622", "3450629"]
      },
      {
        "claim": "All four came from a device profile marked New for this account, seen on closed case CC-0141 and on card C00877-K1 this month",
        "source": "graph",
        "ref": "query:device_neighbors(profile_id=...)",
        "entity_ids": ["CC-0141", "C00877-K1"]
      },
      {
        "claim": "Customer denied the purchases when asked",
        "source": "customer",
        "ref": "evidence_request:1",
        "entity_ids": []
      }
    ],
    "similar_prior_cases": ["CC-0141"],
    "summary": "Textbook card testing: three sub-$3 online authorizations in 40 minutes, then a $100.09 purchase...",
    "written_to_graph": true,
    "graph_case_id": "CASE-2016-1187"
  },
  "evidence_requests": [
    {
      "type": "customer_validation",
      "asked_after_step": 4,
      "assumed_response": "Customer states they did not make these purchases and still has the card"
    }
  ],
  "next_best_actions": {
    "initial": [
      {
        "action": "DECLINE_TRANSACTION",
        "route": "L1",
        "reason": "R5: testing sequence observed, purchase already cleared"
      },
      {
        "action": "VERIFY_WITH_CUSTOMER",
        "route": "auto",
        "reason": "R1: probability 0.72 on pattern alone, confirm before blocking"
      }
    ],
    "final": [
      {
        "action": "BLOCK_CARD",
        "route": "L1",
        "reason": "R2 and R5: customer denied; exposure $268.43 is under $2,500"
      },
      {
        "action": "CREATE_CASE",
        "route": "auto",
        "reason": "R2: internal record opened"
      },
      {
        "action": "FILE_REPORT",
        "route": "L2",
        "reason": "R2 and R6: shared device links this to another compromised card"
      },
      {
        "action": "MONITOR_CONNECTED_CARDS",
        "route": "auto",
        "reason": "R6: same device profile also used on C00877-K1"
      }
    ],
    "what_changed": "Customer denial raised probability from 0.72 to 0.86 and confirmed the block."
  },
  "sar": {
    "file": true,
    "reason": "R2 and R6: confirmed unauthorized use linked by a shared device to a second compromised card",
    "narrative": "On 2016-11-12 between 00:05 and 00:46, card C04570-K1 belonging to customer C04570 was used for three online authorizations...",
    "subjects": ["C04570", "C04570-K1", "C00877-K1"],
    "total_amount_usd": 268.43,
    "activity_dates": ["2016-11-12", "2016-11-12"]
  },
  "stop_reason": "Customer denial settled the verdict; device link identified and connected card protected.",
  "tool_calls": 9,
  "tokens": 12480,
  "latency_s": 18.7
}
```

---

### 2.3 Cytoscape Subgraph Payload
`GET /api/cases/{case_id}/graph`

Returns nodes and edges directly formatted for Cytoscape.js rendering.

```json
{
  "case_id": "HHG-017",
  "nodes": [
    { "id": "cust_1", "label": "Customer C04570", "type": "customer", "properties": { "cards_count": 1 } },
    { "id": "card_1", "label": "Card C04570-K1", "type": "card", "properties": { "brand": "visa", "type": "credit" } },
    { "id": "card_2", "label": "Card C00877-K1", "type": "card_compromised", "properties": { "status": "flagged" } },
    { "id": "dev_1", "label": "Samsung SM-G892A", "type": "device", "properties": { "os": "Android 7.0", "screen": "2220x1080" } },
    { "id": "tx_flagged", "label": "Tx 3450629 ($100.09)", "type": "txn_flagged", "properties": { "amount": 100.09, "risk": 0.57 } },
    { "id": "case_prior", "label": "Prior Case CC-0141", "type": "closed_case", "properties": { "outcome": "confirmed_fraud" } }
  ],
  "edges": [
    { "source": "cust_1", "target": "card_1", "label": "OWNS", "properties": {} },
    { "source": "card_1", "target": "tx_flagged", "label": "MADE", "properties": {} },
    { "source": "tx_flagged", "target": "dev_1", "label": "FROM_DEVICE", "properties": {} },
    { "source": "card_2", "target": "dev_1", "label": "SHARED_DEVICE", "properties": {} },
    { "source": "case_prior", "target": "dev_1", "label": "INVOLVES_DEVICE", "properties": {} }
  ]
}
```

---

### 2.4 Case Memory (Historical Cases)
`GET /api/cases/{case_id}/memory`

```json
[
  {
    "case_id": "CC-0141",
    "similarity": "HIGH",
    "pattern": "card_testing",
    "outcome": "confirmed_fraud",
    "exposure_usd": 312.50,
    "actions_taken": ["BLOCK_CARD", "FILE_REPORT"],
    "analyst_notes": "Small micro-charges preceded large retail purchase on new Android 7 device."
  }
]
```

---

### 2.5 Live Investigation Stream (SSE)
`GET /api/cases/{case_id}/stream`

MIME: `text/event-stream`

```
data: {"event": "TRIGGER_RECEIVED", "data": "Alert triggered for case HHG-017 (Risk Score 0.57)"}

data: {"event": "GSQL_TRAVERSAL", "data": "Executing card_window(window_hours=1)... Found 3 micro-authorizations"}

data: {"event": "GRAPH_CLUSTER", "data": "Executing device_neighbors()... Shared device links to card C00877-K1"}

data: {"event": "POLICY_EVALUATION", "data": "Policy Rule R1 applies: single weak signal requires customer verification"}

data: {"event": "UNCERTAINTY_LOOP", "data": "Dispatching customer_validation request..."}

data: {"event": "EVIDENCE_INJECTED", "data": "Customer denied purchases. Probability escalated to 0.86"}

data: {"event": "NBA_FORMULATED", "data": "Final NBA: BLOCK_CARD (L1), CREATE_CASE (auto), FILE_REPORT (L2)"}

data: {"event": "GRAPH_PERSISTED", "data": "Case vertex written to TigerGraph Savanna (CASE-2016-1187)"}
```

---

### 2.6 Human Approval Action Execution
`POST /api/cases/{case_id}/approve`

**Request Payload:**
```json
{
  "action": "BLOCK_CARD",
  "route": "L1",
  "analyst_id": "analyst_arin",
  "notes": "Confirmed card testing pattern with shared device link to CC-0141"
}
```

**Response Payload:**
```json
{
  "status": "APPROVED",
  "case_id": "HHG-017",
  "action": "BLOCK_CARD",
  "executed_at": "2016-11-12 01:15:00",
  "message": "Action BLOCK_CARD approved by human analyst and executed."
}
```

---

### 2.7 Inject Evidence / Answer Uncertainty Loop
`POST /api/cases/{case_id}/inject-evidence`

**Request Payload:**
```json
{
  "evidence_type": "customer_validation",
  "response": "Customer states they did not make these purchases and still has the card"
}
```

**Response Payload:**
```json
{
  "status": "EVIDENCE_APPLIED",
  "case_id": "HHG-017",
  "new_verdict": "fraud",
  "new_fraud_probability": 0.86,
  "what_changed": "Customer denial raised probability from 0.72 to 0.86 and confirmed the block."
}
```
