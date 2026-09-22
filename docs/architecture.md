# Tark: Canonical System Architecture
## Integrity, Graph Evidence, and Agentic Decisioning

**Author:** Antigravity (Lead Systems Architect)  
**Status:** Canonical Architecture Specification (Phase 2.5 Hardened)  
**Applicability:** Hacker House Goa 2026 — TigerGraph Agentic Fraud Investigation  

---

## 1. Canonical End-to-End Architecture

Tark executes an autonomous, evidence-grounded fraud investigation workflow. Every decision must be mathematically traceable to observable graph topology or verified out-of-band communication.

```
                  ┌───────────────────────────────┐
                  │     Investigation Trigger     │
                  │ (Risk Alert / Customer Report)│
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │        Agent / Planner        │
                  │   (Hypothesis Formulation)    │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │        Tool Selection         │
                  │ (Targeted Investigation Plan) │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │       TigerGraph / GSQL       │
                  │ (Real Graph Neighborhood Exec)│
                  └───────────────┬───────────────┘
                                  │ Real Graph Return Payloads
                                  ▼
                  ┌───────────────────────────────┐
                  │        Evidence Ledger        │
                  │ (Canonical Provenance Records)│
                  └───────────────┬───────────────┘
                                  │ Quantified LRs & Directions
                                  ▼
                  ┌───────────────────────────────┐
                  │      Belief / Reasoning       │
                  │ (Log-Odds Posterior Inference)│
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                     [ Enough Evidence Gathered? ]
                                  │
                 ┌────────────────┴────────────────┐
                 │ NO                              │ YES
                 ▼                                 ▼
   ┌───────────────────────────┐     ┌───────────────────────────┐
   │     Evidence Compass      │     │      Final Decision       │
   │ (Expected Value of Info)  │     │ (Confirmed / Legitimate)  │
   └─────────────┬─────────────┘     └─────────────┬─────────────┘
                 │                                 │
                 ▼                                 ▼
   ┌───────────────────────────┐     ┌───────────────────────────┐
   │      Approved Action      │     │       Policy Engine       │
   │ (Targeted Out-of-Band Act)│     │  (Tiered Action Execution)│
   └─────────────┬─────────────┘     └─────────────┬─────────────┘
                 │                                 │
                 ▼                                 ▼
   ┌───────────────────────────┐     ┌───────────────────────────┐
   │       New Evidence        │     │      Human Approval       │
   │ (Ground-Truth Ingestion)  │     │  (Auto, L1, L2 Workflows) │
   └─────────────┬─────────────┘     └─────────────┬─────────────┘
                 │                                 │
                 └────────────────┬────────────────┘
                                  ▼
                  ┌───────────────────────────────┐
                  │          Case Memory          │
                  │ (Graph Precedents & GraphRAG) │
                  └───────────────────────────────┘
```

---

## 2. Ingestion vs. Investigation Boundary

A foundational architectural flaw in naive implementations is conflating **ETL ingestion** with **investigation reasoning**. Tark strictly enforces an architectural firewall between these layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA INGESTION LAYER                             │
│                                                                             │
│ - Raw Datasets: transactions.csv (708 MB), identity.csv (26 MB),            │
│   closed_cases_history.csv (2.7 MB).                                        │
│ - Responsibilities:                                                         │
│   1. Schema conformant bulk upsert to TigerGraph Cloud.                     │
│   2. Unsupervised device profile digital fingerprint hashing (MD5).         │
│   3. Bidirectional edge population (Card_MADE_Txn, Txn_FROM_Device).        │
│ - CRITICAL CONSTRAINT:                                                      │
│   * The ETL layer NEVER evaluates fraud likelihood.                         │
│   * The ETL layer NEVER assigns case outcomes.                              │
│   * The ETL layer NEVER checks benchmark case IDs (e.g. HHG-014).           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Populated Knowledge Graph
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    INVESTIGATION-TIME EXPLORATION LAYER                     │
│                                                                             │
│ - Trigger Intake: Receives an alert or customer dispute.                    │
│ - Targeted Neighborhood Traversal:                                          │
│   * Evaluates GraphScope: DATA_AVAILABLE vs DATA_OUT_OF_SCOPE.              │
│   * Executes installed GSQL queries against target entities.                │
│   * Translates topology metrics into canonical EvidenceItems.               │
│ - Decoupled Reasoning Engine:                                               │
│   * BeliefEngine calculates Bayesian posterior log-odds.                    │
│   * PolicyEngine maps posterior & exposure to Next Best Actions (NBAs).     │
│   * DecisionFlipPlanner evaluates if information value justifies inquiry.   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Current Cohort Ingestion Strategy & Scope Contract

### Why a Bounded Slice Exists
The raw `transactions.csv` file contains 590,742 transactions across 13,553 distinct customers. Ingesting 590k transactions over remote TigerGraph Cloud REST endpoints requires dozens of hours of network transmission and exceeds cluster memory limits. 

To provide complete, mathematically sound graph traversal without fabricating data, Tark operates on an **optimized operational cohort**:

1. **Portfolio Customer Roster:** 1,896 customers and 1,917 cards with verified 6-month historical baselines in `closed_cases_history.csv`.
2. **Device Anomaly Cohort:** All device profiles in `identity.csv` exhibiting multi-card sharing ($\ge 5$ transactions) or anonymous proxy routing (`id_23` contains "proxy").
3. **Relevant Transaction Slice:** 26,754 transactions representing 100% of historical activity for the portfolio cohort and the connected anomaly clusters.

### Scope Selection Rules vs. Fraud Verdicts
- **Infrastructure Rules:** The cohort boundary is selected purely based on **data availability and account portfolio membership**. It is NOT a fraud filter.
- **Honest Negative Representation:** If a transaction in the future involves a customer not present in the ingested portfolio, the system explicitly returns `DATA_OUT_OF_SCOPE`. It does **NOT** report `NO_MATCH` or assume the customer has zero fraud risk.

### The GraphScope Contract (`src/graph/scope.py`)

| Scope Response Status | Technical Meaning | Investigation Layer Interpretation |
|---|---|---|
| `DATA_AVAILABLE` | Entity is in scope and query returned structural records. | Findings are translated into `EvidenceItem` records with positive or negative LRs. |
| `NO_MATCH` | Entity is in scope and was fully inspected, but the queried pattern was absent. | Pattern confirmed absent (e.g. no card testing found in customer's 400 historical transactions). |
| `DATA_OUT_OF_SCOPE` | Entity was not part of the active 6-month portfolio slice loaded in TigerGraph. | Historical baseline is **unobserved/unknown**. Investigation must reflect uncertainty rather than false certainty. |
| `GRAPH_QUERY_FAILURE` | TigerGraph Cloud RESTPP/GPE endpoint returned an error or timed out. | Investigation logs explicit query failure. **Zero silent fallbacks or invented heuristics.** |

---

## 4. Separation of Evidence from Reasoning

Tark enforces a strict 3-stage information pipeline:

$$\text{TigerGraph / GSQL Topology} \longrightarrow \text{EvidenceItem Contract} \longrightarrow \text{Belief \& Policy Reasoning}$$

### The Cardinal Rule
**GSQL queries compute topological observations, NOT legal fraud verdicts.**

- **CORRECT:**
  1. `card_sequence.gsql` reports: `{"micro_count": 3, "is_card_testing": true, "micro_txn_ids": [...]}`.
  2. Investigation layer records an `EvidenceItem` of type `CARD_TESTING_SEQUENCE` with $LR = 34.3$ and `direction: SUPPORTS`.
  3. `BeliefEngine` shifts posterior log-odds by $+3.535$.
  4. `PolicyEngine` triggers Rule R5 (`DECLINE_TRANSACTION` and `BLOCK_CARD`).
- **PROHIBITED (Architectural Violation):**
  - GSQL query returning a field called `"fraud_decision: BLOCK_CARD"`.
  - Hardcoding a policy rule inside database stored procedures.
  - Bypassing the `EvidenceLedger` to directly set case status.

---

## 5. Canonical Evidence Object Contract

Every observable finding in Tark is encapsulated in a formal `EvidenceItem` (`src/evidence/types.py`):

```python
class EvidenceItem(BaseModel):
    evidence_id: str                      # Unique traceable UUID (e.g. EVD-A1B2C3D4)
    evidence_type: EvidenceType           # Categorical evidence taxonomy enum
    value: Any                            # Raw quantitative or categorical metric observed
    source: str                           # Originating query name or communication channel
    finding: str                          # Human-readable summary of the finding
    provenance: str                       # Full data lineage trace back to source CSV/table
    
    # Entity Attribution
    source_entity: Optional[str]          # Starting graph vertex (e.g. Card C11923-K2)
    target_entity: Optional[str]          # Terminal graph vertex reached (e.g. Txn 3582142)
    graph_query: Optional[str]            # Installed GSQL query name
    
    # Provenance Graph Links
    supporting_transaction_ids: List[str] # List of specific transaction IDs verifying finding
    supporting_entities: List[str]        # List of connected cards, devices, or accounts
    timestamp: Optional[str]              # Observation timestamp
    
    # Scoring & Belief Inference
    reliability: float                    # Data source reliability [0.0 - 1.0]
    lr: float                             # Empirical Likelihood Ratio P(E|Fraud)/P(E|Legit)
    log_lr: float                         # Natural logarithm of the Likelihood Ratio
    direction: EvidenceDirection          # SUPPORTS, CONTRADICTS, or NEUTRAL
    is_exculpatory: bool                  # True if direction is CONTRADICTS (LR < 1.0)
    details: Dict[str, Any]               # Complete raw payload from TigerGraph query
```

---

## 6. Case Memory Grounding

At the conclusion of an investigation:
1. Every final case verdict, assigned pattern, exposure amount, and SAR narrative is persisted as an `InvestigationCase` vertex in TigerGraph.
2. Undirected edges (`InvestigationCase_INVOLVES_Transaction`, `InvestigationCase_ON_CARD`) connect the case to the active transaction graph.
3. Future investigations query these historical precedents via `similar_cases.gsql`, ensuring institutional knowledge accumulates directly in the graph database.

---

## 7. Agentic Execution Authority & MCP Protocol (v3.1)

### 7.1 Single Authoritative Pipeline

There is exactly one investigation execution path. The API (`src/api/main.py`), the
benchmark runner (`bench/run.py`), and the independent evaluation harness
(`evaluation/harness.py`) all delegate to:

`EvidenceLedger → BeliefEngine.evaluate_investigation → InvestigationOrchestrator.run_investigation (Evidence Compass) → PolicyEngine.evaluate → GroundedInvestigationSynthesizer`

No entrypoint contains bespoke GSQL queries, duplicated likelihood-ratio arithmetic, or
case-specific branches.

### 7.2 Model Context Protocol (MCP) Boundary

Tark exposes its authorized evidence tools through an MCP-compliant boundary
(`src/mcp/server.py`), governed by `PROTOCOL_VERSION = "2024-11-05"`.

- **Transport:** JSON-RPC 2.0 (`TigerGraphMCPServer.handle_jsonrpc`).
- **Methods:** `initialize`, `tools/list`, `tools/call`.
- **Discovery:** `GET`-style `list_tools()` / `tools/list` returns each tool's `name`,
  `description`, and JSON-Schema `inputSchema`.
- **Invocation:** `tools/call` accepts `{name, arguments}` and returns the standard MCP
  content envelope `{content, isError, structuredContent}`, with execution routed through the
  authoritative `EvidenceToolDispatcher`.
- **Security:** only registered, schema-validated tools may execute; arbitrary GSQL, shell,
  or unvetted queries are rejected. Telemetry (session id, request id, latency) is captured
  by `TigerGraphMCPClient`.

Registered tools: `device_analysis`, `card_sequence`/`transaction_velocity`,
`region_analysis`, `customer_profile`, `similar_cases`, `verify_customer`, `step_up_auth`.

### 7.3 Policy Governance Hardening

- **R9 (undocumented typology)** only escalates to `CREATE_CASE` + `FILE_REPORT` when
  the posterior is very high ($\ge 0.85$) *and* the Decision Gate has passed. Thin,
  uncorroborated undocumented patterns degrade to a non-punitive
  `MONITOR_CARD` + `VERIFY_WITH_CUSTOMER` posture ("R9-thin").
- **Gate-aware general disposition:** the generic high-posterior fallback
  (`BLOCK_CARD`) is only admissible when the Decision Gate is not explicitly locked.
  Evidence-specific containment rules (R2 dispute, R5 card-testing, R6 device ring)
  remain authoritative.
- **R6-syndicate escalation:** a shared-device ring spanning $\ge 10$ independent
  card accounts is escalated to a human analyst at Level 2 (`ESCALATE_TO_ANALYST`,
  route `L2`) and automatic SAR filing is deferred until that authorization. This
  removes the "locked gate + unfiled SAR" tension for large syndicates.
- Because all entrypoints share the same orchestrator/policy pipeline, the benchmark
  answers, the API, and the independent harness agree by construction.

### 7.4 MCP Compatibility with `tigergraph-mcp`

Tark implements the Model Context Protocol tool surface with the same JSON-RPC 2.0
contract exposed by the official
[`tigergraph-mcp`](https://github.com/tigergraph/tigergraph-mcp) server:

| Concern | Tark | `tigergraph-mcp` |
|---|---|---|
| Transport | JSON-RPC 2.0 | JSON-RPC 2.0 (stdio / SSE) |
| Discovery | `tools/list` → `{name, description, inputSchema, annotations}` | `tools/list` |
| Invocation | `tools/call` → `{content, isError, structuredContent}` | `tools/call` |
| Protocol negotiation | `initialize` echoes a supported client version (`2025-06-18` / `2024-11-05`) | negotiated in `initialize` |
| Tool naming | `tigergraph__<tool>` aliases for graph-native tools | `tigergraph__<tool>` |
| Behavioural hints | `annotations`: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint` | same |
| Response envelope | `{success, operation, summary, data, suggestions, metadata}` | same |
| Schemas | JSON-Schema `inputSchema` per tool | JSON-Schema `inputSchema` |

The registered tools (`device_analysis`, `card_sequence`/`transaction_velocity`,
`region_analysis`, `customer_profile`, `similar_cases`, `verify_customer`,
`step_up_auth`) mirror the graph-capability exposure of the official server. Tark's
server adds a hardened authorization layer: only registered tools may execute and all
execution routes through `EvidenceToolDispatcher` (no arbitrary GSQL/shell) — which is
also why the upstream package is not used directly. See `docs/blog-notes.md` for the
rationale.

### 7.5 Graph Algorithms Used

- **Ring sizing (connected-component style):** `device_analysis` performs a 2-hop
  neighbourhood expansion (`Transaction → DeviceProfile → Transactions → Cards`) and
  counts the distinct reachable card vertices — a connected-component ring size
  consumed by R6 and the R6-syndicate threshold. (See `queries/device_analysis.gsql`.)
- **Temporal velocity burst:** `txn_velocity` performs a sliding-window edge
  aggregation over the card's transaction neighbourhood, producing burst count and
  spend (`queries/txn_velocity.gsql`).
- **Geographic displacement:** `region_analysis` compares the transaction billing
  region against the customer's historical region set (set-overlap).
- **Case-memory topology similarity:** `similar_cases.gsql` traverses closed-case
  topology for precedent retrieval (contextual, non-evidential, LR = 1.0).

### 7.6 Vector Storage & Retrieval (GraphRAG Grounding)

`src/knowledge/vector_index.py` embeds every policy rule, typology, and regulatory
statute chunk into a fixed-dimension vector and retrieves them by cosine similarity to
a case query derived from observed evidence and disposition. Results are merged
(deduplicated by chunk id) with the deterministic policy mapping, and every retrieved
chunk carries an explicit `retrieval_path` (e.g. `VectorIndex -> CosineSimilarity ->
KNOW-POLICY-R5`) that is rendered in SAR §4, so a judge can trace
`GSQL finding → KNOW-POLICY-Rx → 31 CFR 1020.320` in under 30 seconds.

The embedding is a deterministic feature-hashing bag-of-words vector: reproducible,
dependency-free, and auditable. It is portable to TigerGraph vector storage — the same
vectors can be persisted as vector attributes on a `Document` vertex and queried with a
vector-search GSQL function.

**Verified capability probe (honest claim boundary).** `bench/probe_gds_vector.py`
queries the live instance and records findings in `analysis/gds_vector_probe.json`.
On release 4.2.5 the `gsql-graph-algorithms`/`gle` components are present, but
**no GDS algorithm query is resolvable on the benchmark graph** (`INSTALL QUERY tg_wcc`
fails with *"could not be resolved within the provided graph"*) and there is **no
`Document` (vector) vertex type**. Tark therefore does **not** claim live native GDS or
TigerGraph vector search; the deterministic in-process index is the offline-executable
realization of the same retrieval contract, and it is the layer actually used at
runtime.



