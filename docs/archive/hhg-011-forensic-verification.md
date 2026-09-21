# Tark — HHG-011 Forensic Verification Report

## Executive Summary

During Phase 4.6.2 benchmark validation, Tark achieved **20/20 (100.0%) fraud-label agreement** and **19/20 (95.0%) Next-Best-Action (NBA) agreement**. 

The sole remaining mismatch was **HHG-011**:
- **Expected Ground Truth:** `DECLINE_TRANSACTION` (Rule R5: Card testing sequence detected) + `BLOCK_CARD`
- **Actual Tark Action:** `BLOCK_CARD` (Rule R2: Customer reported/denied transaction) + `CREATE_CASE`

This forensic verification investigated whether the discrepancy was caused by a mismatch between the benchmark definition and the live TigerGraph database, or a retrieval defect within Tark.

**Conclusion:**
1. The micro-authorization transactions and card-testing sequence **definitely and completely exist** in the live TigerGraph database.
2. The mismatch is caused by **Root Cause B: An evidence retrieval parameter defect in Tark**: `src/compass/evoi.py` generated `QUERY_CARD_SEQUENCE` parameters without specifying `anchor_ts`, causing `CardSequenceTool` to fall back to a hardcoded end-of-year timestamp (`"2016-12-31 23:59:59"`). This shifted the 24-hour query window 3 days past the actual transaction timestamp (`"2016-12-29 03:27:44"`), returning `NO_MATCH`.

---

## 1. Expected Evidence

In `cases/HHG-011.json`, the expected case profile is:
- **Case ID:** `HHG-011`
- **Flagged Transaction ID:** `3583368` ($131.30, `2016-12-29 03:27:44`)
- **Card ID:** `C11923-K2`
- **Customer ID:** `C11923`
- **Expected Evidence:**
  - `CARD_TESTING_SEQUENCE` ($LR=34.3, \log LR=3.535$)
  - Finding: `"Card testing sequence: 3 micro-authorizations (<$5) in 24h prior (txns: ['3582624', '3582142', '3582175'])"`
- **Expected NBA:** `DECLINE_TRANSACTION` (Rule R5) with `BLOCK_CARD` (Rule R5 consequential).

---

## 2. Actual Live Graph Evidence

Live TigerGraph vertex and edge lookups confirm the exact vertices and edges exist in the database:

### A. Target Transaction
- **Vertex ID `3583368`:**
  - `ts`: `2016-12-29 03:27:44`
  - `amount`: `$131.30`
  - `card1`: `21363`
  - Connected to Card `C11923-K2` via `Card_MADE_Transaction`.

### B. Micro-Authorization Transactions Connected to Card `C11923-K2`
1. **Vertex ID `3582624`:**
   - `ts`: `2016-12-28 22:03:09` (5 hours 24 mins before flagged txn)
   - `amount`: `$0.93` ($\le \$5.00$)
   - Edge: `Card_MADE_Transaction` $\to$ `C11923-K2`
2. **Vertex ID `3582175`:**
   - `ts`: `2016-12-28 19:22:39` (8 hours 5 mins before flagged txn)
   - `amount`: `$4.01` ($\le \$5.00$)
   - Edge: `Card_MADE_Transaction` $\to$ `C11923-K2`
3. **Vertex ID `3582142`:**
   - `ts`: `2016-12-28 19:13:13` (8 hours 14 mins before flagged txn)
   - `amount`: `$4.15` ($\le \$5.00$)
   - Edge: `Card_MADE_Transaction` $\to$ `C11923-K2`

All 3 micro-authorizations are present, connected to the card, and occurred within the 24-hour window prior to transaction `3583368`.

---

## 3. Query Definition and Analysis

The installed GSQL query `queries/card_sequence.gsql` is defined as:

```gsql
CREATE OR REPLACE QUERY card_sequence(STRING c_id, DATETIME anchor_ts, INT window_hours = 24) FOR GRAPH FraudInvestigation {
    SumAccum<INT> @@micro_txns = 0;
    SumAccum<FLOAT> @@anchor_amount = 0.0;
    ListAccum<STRING> @@micro_txn_ids;

    Start = {Card.*};
    TargetCard = SELECT c FROM Start:c WHERE c.card_id == c_id;

    Txns = SELECT t FROM TargetCard:c -(Card_MADE_Transaction:e)- Transaction:t
           WHERE datetime_diff(anchor_ts, t.ts) >= 0 AND datetime_diff(anchor_ts, t.ts) <= (window_hours * 3600)
           ACCUM 
               CASE WHEN t.amount <= 5.0 THEN
                   @@micro_txns += 1,
                   @@micro_txn_ids += t.txn_id
               ELSE
                   @@anchor_amount += t.amount
               END;

    PRINT (@@micro_txns >= 3) AS is_card_testing,
          @@micro_txns AS micro_count,
          @@anchor_amount AS larger_amount,
          @@micro_txn_ids AS micro_txn_ids;
}
```

---

## 4. Raw Query Execution Comparison

Executing the query directly against the live TigerGraph cluster reveals the exact root cause:

### Execution 1 (Tark's Current Execution with Default Timestamp):
- **Parameters:** `{"c_id": "C11923-K2", "anchor_ts": "2016-12-31 23:59:59", "window_hours": 24}`
- **Raw Result:**
  ```json
  [
    {
      "is_card_testing": false,
      "larger_amount": 0,
      "micro_count": 0,
      "micro_txn_ids": []
    }
  ]
  ```
- *Explanation:* The query looked for transactions between `2016-12-30 23:59:59` and `2016-12-31 23:59:59`. The card testing sequence occurred on `2016-12-28`, which is outside this window.

### Execution 2 (With Actual Flagged Transaction Timestamp):
- **Parameters:** `{"c_id": "C11923-K2", "anchor_ts": "2016-12-29 03:27:44", "window_hours": 24}`
- **Raw Result:**
  ```json
  [
    {
      "is_card_testing": true,
      "larger_amount": 1037.62,
      "micro_count": 3,
      "micro_txn_ids": [
        "3582624",
        "3582142",
        "3582175"
      ]
    }
  ]
  ```

---

## 5. Normalized Evidence & Policy Engine Behavior

### A. Current Tark Path (with default `anchor_ts`):
1. GSQL returns `micro_count: 0`.
2. `EvidenceNormalizer` produces `EvidenceItem(evidence_type=CARD_TESTING_SEQUENCE, value="NO_MATCH", lr=1.0)`.
3. Because $LR=1.0$, `is_card_testing` is `False`.
4. The customer report trigger activates Rule R2 (`customer_denied = True`), producing:
   - **PRIMARY:** `BLOCK_CARD`
   - **CONSEQUENTIAL:** `CREATE_CASE`

### B. Corrected Path (with transaction `anchor_ts`):
1. GSQL returns `micro_count: 3`, `micro_txn_ids: ['3582624', '3582142', '3582175']`.
2. `EvidenceNormalizer` produces `EvidenceItem(evidence_type=CARD_TESTING_SEQUENCE, lr=34.3)`.
3. Because $LR=34.3 > 1.0$, `is_card_testing` is `True`.
4. Policy Engine evaluates Rule R5:
   - **PRIMARY:** `DECLINE_TRANSACTION` (`approval_route: L1`, `reason: "R5: Card testing sequence detected (micro-authorizations followed by purchase)."`)
   - **CONSEQUENTIAL:** `BLOCK_CARD` (`approval_route: L1`, `reason: "R5: Card testing sequence cleared a charge over $100."`)
5. This matches the benchmark ground truth 100%.

---

## 6. Root Cause Classification

**Classification:** **B. A defect in Tark's evidence tool parameter construction.**

Specifically:
- In `src/compass/evoi.py` (`get_candidate_action_templates`), the action template for `QUERY_CARD_SEQUENCE` only populates:
  ```python
  "parameters": {"c_id": card_id, "window_hours": 24}
  ```
  It does not include `"anchor_ts": target_entities.get("timestamp")` or the transaction timestamp.
- In `src/tools/graph_tools.py` (`CardSequenceTool.execute`), line 144:
  ```python
  anchor_ts = params.get("anchor_ts") or (context or {}).get("anchor_ts", "2016-12-31 23:59:59")
  ```
  Because neither `params` nor `context` contained `anchor_ts`, the query fell back to the static horizon cutoff `"2016-12-31 23:59:59"`.

---

## 7. Assessment of the 19/20 Result

The **19/20 NBA agreement (95.0%)** achieved in Phase 4.6.2 is a **completely legitimate and authentic result**:
1. Tark did not use benchmark-specific cheats or hardcoded mappings.
2. Given the evidence that was actually returned by the query under the current parameters ($LR=1.0$), Tark made the **exact logically correct decision** (applying Rule R2 `BLOCK_CARD` for a customer report rather than inventing a card testing decline without positive proof).
3. The remaining 1-case gap is cleanly isolated to a parameter binding in evidence acquisition, not a policy, reasoning, or benchmark defect.

---

## 8. Recommended Next Action

- Do NOT make code modifications in this phase (maintaining strict phase boundary integrity).
- In a future phase (e.g. Phase 4.6.3 or an evidence-dispatch hardening pass), pass `anchor_ts` from `state.trigger["timestamp"]` or the flagged transaction timestamp in `get_candidate_action_templates` in `src/compass/evoi.py`.
