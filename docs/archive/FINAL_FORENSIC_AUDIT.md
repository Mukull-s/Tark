# TARK — FULL FORENSIC SYSTEM AUDIT
**Authoritative Forensic Audit for Hacker House Goa 2026 (TigerGraph Track 4)**
**Audit Date:** September 20, 2026
**Audit Mode:** READ-ONLY / STRICT EXECUTION PATH FORENSICS
**Scope:** Entire Codebase (`src/`, `bench/`, `queries/`, `tests/`, `web/`, `docs/`, `cases/`)

---

## 1. Executive Summary

### The Core Question
> **"Is Tark currently a real general-purpose agentic fraud investigation system, or is it partially benchmark/demo optimized?"**

### The Brutally Honest Assessment
**Tark is an asymmetric hybrid:** It possesses an **exceptionally rigorous, mathematically genuine Bayesian-graph reasoning core** at its foundation, wrapped in an **incomplete, benchmark-coupled outer shell** that contains several **fabricated frontend displays, a completely disabled LLM pipeline, zero Model Context Protocol (MCP) implementation, and an inability to ingest arbitrary unseen transactions.**

1. **What is Genuinely Real and Technically Impressive:**
   - **TigerGraph GSQL Execution:** Real GSQL queries (`device_analysis.gsql`, `card_sequence.gsql`, `txn_velocity.gsql`, `customer_profile.gsql`, `region_analysis.gsql`) execute against a live TigerGraph Cloud cluster (`tg-3242c55c...i.tgcloud.io`). Parameters propagate dynamically, and vertex/edge topologies are genuinely traversed.
   - **Bayesian Belief Engine:** Unlike standard LLM "agents" that hallucinate probabilities, Tark's `BeliefEngine` (`src/belief/engine.py`) uses formal log-likelihood ratios ($\log \mathcal{LR}$), calibrated likelihood registries, and Bayesian log-odds updates. Probability updates are mathematically derived from empirical evidence.
   - **Decision-Theoretic EVOI Planner:** The Evidence Compass (`src/compass/evoi.py`) genuinely calculates the Expected Value of Information ($\text{EVOI}$) and Net Decision Value ($\text{EVOI} - \text{cost}$) to rank candidate queries before dispatch.
   - **Policy Engine (R1–R10):** Deterministic institutional policy rules genuinely govern actions, role precedence (`PRIMARY` vs `CONSEQUENTIAL`), and multi-level human approval routing (`L1`, `L2`, `L3`).
   - **Case Memory Snapshot Isolation:** Historical case retrieval strictly preserves temporal barriers and enforces snapshot isolation, preventing target-case leakage or posterior contamination.

2. **What is Fake, Superficial, or Broken:**
   - **Zero MCP Implementation:** There is **NO** Model Context Protocol (MCP) server or client in the codebase. In `tests/test_architecture_hardening.py` line 150, `src/mcp` is explicitly listed under `forbidden_future_files`. The claims in frontend navigation and documentation ("MCP Tools: 50+ loaded") are **100% cosmetic**.
   - **LLM is 100% Disabled in Live Execution & Benchmarks:** In `src/api/main.py` line 338 and `bench/run_phase4_6_2_validation.py` line 165, `enable_llm_synthesis=False` is hardcoded. `orchestrator` is initialized with `llm_client=None` (`src/api/main.py:62`). The system makes **zero LLM calls** during live demo or benchmark runs. All narratives are deterministic template strings.
   - **Unseen Transactions Cannot Run:** The API (`POST /api/investigations/{case_id}/run`, `src/api/main.py:720`) strictly validates `case_id` against `case_pack.csv`. Any unseen case immediately returns `HTTP 404 Case not found in case pack`. There is no transaction ingestion endpoint, no case creation endpoint, and no automated entity-resolution pipeline to discover `card_id` or `customer_id` from a bare `transaction_id`.
   - **The "20/20 PASS" Benchmark Claim is Misleading:**
     - The true Next-Best-Action (NBA) accuracy on live TigerGraph was **19/20 (95.0%)**, not 20/20. `HHG-011` was a mismatch (`BLOCK_CARD` produced vs `DECLINE_TRANSACTION` expected).
     - The Decision Gate passed in only **11/20 (55.0%)** cases (9 cases terminated before the gate due to negative EVOI or max steps).
     - The benchmark exhibits **100% fraud class imbalance** (all 20 cases are fraud; zero legitimate negative control cases exist). A 20/20 fraud verdict tests zero false-alarm discrimination.
     - The frontend (`BenchmarkView.tsx`, `OverviewView.tsx`) unconditionally hardcodes `"Action Accuracy: 100%"` and static `✓ PASS` badges for all 20 cases.
   - **Graph Algorithms are 100% Simulated in Frontend:** Louvain community detection, Weakly Connected Components (WCC), and PageRank do not exist in GSQL or backend code. They exist only as an enum in `GlobalGraphExplorer.tsx` toggling a static SVG diagram with hardcoded coordinates.
   - **GraphRAG is a Hardcoded Dictionary Lookup:** `PolicyGraphRAGRetriever` (`src/knowledge/retriever.py`) uses an `if/elif` check on `EvidenceType` mapping to an in-memory dictionary of static knowledge chunks (`KNOW-POLICY-R1`..`R10`). No vector embeddings, vector search, or graph traversal are performed.
   - **Frontend Evidence Compass is Hardcoded Fixture Data:** `EvidenceCompassView.tsx` accepts `result: _result`, completely ignores the parameter, and renders a static array of candidates with hardcoded Net EVOI values (`+0.41`, `+0.34`, `-0.12`).
   - **SAR Narrative is Hardcoded in React:** `ExplanationSarView.tsx` renders a static template string hardcoded with citations to `"Policy rule R5: Micro-authorization detection sequence"` regardless of the case typology.

---

## 2. Architecture Reality: Claimed vs. Actual

| Architectural Component | Claimed Architecture | Actual Codebase Reality | Status |
|---|---|---|---|
| **Orchestrator** | Dynamic autonomous LLM-driven ReAct agent loop | Deterministic while-loop driven by EVOI rankings (`orchestrator.py:164`) | **DETERMINISTIC RULE ENGINE** |
| **LLM Reasoning** | DeepSeek/Claude dynamically reasoning over evidence & generating SAR | LLM is disabled (`enable_llm_synthesis=False`). `llm_client=None` passed to API orchestrator | **DISABLED / DEAD CODE** |
| **Tool Protocol (MCP)** | Model Context Protocol exposing TigerGraph & external tools | Native Python classes in `dispatcher.py` calling `pyTigerGraph` RESTPP. No MCP server/client | **MISSING / FICTIONAL CLAIM** |
| **TigerGraph GSQL** | Parameterized queries running on live cluster | 6 real GSQL queries compiled on TigerGraph Cloud; real RESTPP execution | **GENUINELY IMPLEMENTED** |
| **Graph Algorithms** | Louvain, WCC, PageRank detecting fraud syndicates | Static SVG geometry in `GlobalGraphExplorer.tsx`. Zero GSQL algorithm queries | **100% FRONTEND SIMULATION** |
| **GraphRAG** | Vector + Graph multi-hop retrieval over banking regulations | Hardcoded `if/elif` dictionary lookup keyed by `EvidenceType` in `retriever.py` | **HARDCODED DICTIONARY** |
| **Belief Engine** | Mathematical Bayesian updates via likelihood ratios | Exact log-odds additions ($\log \mathcal{LR}$), damping, prior profiles in `engine.py` | **GENUINELY IMPLEMENTED** |
| **Evidence Compass** | Dynamic EVOI calculation ranking next-best evidence query | Exact EVOI math ($EDV - \text{cost}$) in `evoi.py`; live ranking during loop | **GENUINELY IMPLEMENTED** |
| **Case Memory** | Temporal snapshot-isolated precedent retrieval | CSV/JSONL-backed memory store with timestamp cutoffs and strict isolation in `store.py` | **GENUINELY IMPLEMENTED** |
| **External Tools** | Out-of-band SMS/IVR challenge & Step-up MFA gateways | Mock functions in `mock_actions.py` with static timeouts & trigger mappings | **MOCKED / SIMULATED** |
| **Policy Engine** | Institutional rules R1–R10 determining NBA & approval routes | Deterministic evaluation of thresholds, action roles, and approval tiers (`policy/engine.py`) | **GENUINELY IMPLEMENTED** |
| **Transaction Ingestion**| Production pipeline ingesting arbitrary credit/debit transactions | API strictly requires `case_id` in `case_pack.csv`; 404s on any unseen case | **BENCHMARK-COUPLED ONLY** |
| **Frontend Live State** | Real-time reactive stream of backend agent activity | Synchronous single-shot POST returning full trace; frontend formats returned JSON | **SYNCHRONOUS PRESENTATION** |

---

## 3. Hardcoding Audit

### A. Direct Benchmark Case Mappings
1. **`web/src/components/PolicyPatternsView.tsx` (Lines 23, 33, 43, 53, 63, 72, 82):**
   - The policy patterns view explicitly maps each policy rule to hardcoded benchmark case IDs:
     - Rule R2: `citedCases: ["HHG-003", "HHG-004", "HHG-006", "HHG-008"]`
     - Rule R3: `citedCases: ["HHG-014", "HHG-019"]`
     - Rule R4: `citedCases: ["HHG-002", "HHG-010"]`
     - Rule R5: `citedCases: ["HHG-011"]`
     - Rule R6: `citedCases: ["HHG-007", "HHG-012"]`
     - Rule R7: `citedCases: ["HHG-001", "HHG-015"]`
     - Rule R8: `citedCases: ["HHG-005", "HHG-013", "HHG-017", "HHG-020"]`
   - Classification: `[BENCHMARK-SPECIFIC]`

2. **`web/src/components/BenchmarkView.tsx` (Lines 13–55, 231, 291):**
   - Baseline table hardcodes static comparison values:
     - `B0: Static Rules Baseline: acc: 55.0%`
     - `B1: Raw LLM Zero-Shot: acc: 60.0%`
     - `B2: TigerGraph + Standard GraphRAG: acc: 70.0%`
     - `B3: Agentic without Decision-Flip Engine: acc: 75.0%`
     - `TARK: Decision-Theoretic EVOI (Ours): acc: 100.0%`
   - Line 231 hardcodes badge: `"20 / 20 PASSING (100%)"`
   - Line 291 unconditionally renders `✓ PASS` for every case in `cases.map(...)`.
   - Classification: `[HARDCODED]`

3. **`web/src/components/OverviewView.tsx` (Lines 16–47):**
   - KPI cards hardcode static strings:
     - `Action Accuracy: "100%", sub: "20/20 NBA agreement"`
     - `Decision-Flip Precision: "100%", sub: "0 false action flips"`
     - `Wasted Requests: "0%", sub: "EVOI filtered"`
     - `Policy Compliance: "100%", sub: "10/10 rules enforced"`
   - Classification: `[HARDCODED]`

4. **`web/src/components/EvidenceCompassView.tsx` (Lines 8–93):**
   - The component signature is `({ result: _result })`. It discards the live investigation result entirely.
   - It renders a static array with hardcoded values:
     - `card_sequence`: `netEvoi: "+0.41"`
     - `device_analysis`: `netEvoi: "+0.34"`
     - `verify_with_customer`: `netEvoi: "-0.12"`
     - `txn_velocity`: `netEvoi: "-0.05"`
   - Classification: `[MOCK / FIXTURE]`

5. **`web/src/components/ExplanationSarView.tsx` (Lines 149–175):**
   - Discards backend `grounded_synthesis` and renders hardcoded JSX text:
     ```tsx
     <p>Tark initiated an autonomous investigation on case <strong>{caseId}</strong>...</p>
     <p>Empirical evidence established a decisive likelihood ratio surpassing the decision threshold...</p>
     <p><sup>[2]</sup> Policy rule R5: Micro-authorization detection sequence.</p>
     ```
   - Classification: `[HARDCODED]`

6. **`web/src/components/GlobalGraphExplorer.tsx` (Lines 218–272):**
   - Renders a hardcoded SVG diagram of "Community #14 (Syndicate Ring)" with a central device circle at `(0,0)` and card circles at angles `[-40, -20, 0, 20, 40]`. Selecting Louvain, WCC, or PageRank only updates the text header `algorithm.toUpperCase()`.
   - Classification: `[SIMULATED]`

### B. Synthetic Node Generation in Workspace Graph
- **`src/api/main.py` (Lines 594–600, 624, 651):**
  - When constructing the interactive graph from tool evidence:
    - If connected cards are missing: `supporting_cards = [f"CARD_RING_{i+1}" for i in range(min(4, shared_count - 1))]`
    - If sequence transactions are missing: `seq_txns = details.get("supporting_transactions") or ["TXN_MICRO_1", "TXN_MICRO_2", "TXN_MICRO_3"]`
    - If velocity transactions are missing: `vel_txns = details.get("burst_txns") or ["TXN_VEL_1", "TXN_VEL_2"]`
  - Classification: `[SYNTHESIZED / FALLBACK]`

### C. Where the System is NOT Hardcoded (Clean Dynamic Code)
- `src/belief/engine.py`: Dynamic Bayesian computation based on received EvidenceItems.
- `src/compass/evoi.py`: Dynamic expected utility and EVOI math based on current state.
- `src/policy/engine.py`: Clean conditional rule evaluation against state and ledger.
- `src/tools/graph_tools.py`: Queries execute with dynamic parameters against live TigerGraph RESTPP endpoints.

---

## 4. "20/20 PASS" Forensic Benchmark Audit

### Detailed Answers to the 20 Benchmark Questions

1. **Where are the 20 cases defined?**
   In `case_pack.csv` at the repository root and mirrored in `cases/HHG-001.json` through `cases/HHG-020.json`.
2. **Where are expected answers defined?**
   In `cases/HHG-001.json` through `cases/HHG-020.json` under `ground_truth.expected_nba`, `ground_truth.expected_verdict`, and `ground_truth.policy_rules`.
3. **How are results compared?**
   In `bench/run_phase4_6_2_validation.py` lines 175–180 and evaluated in `docs/phase4.6.2-benchmark-validation.md`.
4. **Is the comparison performed independently?**
   Yes. The validation script runs the pipeline and outputs raw JSON (`analysis/phase4.6.2_validation_raw_results.json`), which is compared against the case JSON files.
5. **Can the system see expected answers at runtime?**
   **No.** `orchestrator.run_investigation()` does not receive ground truth labels or expected actions.
6. **Can expected answers influence runtime?**
   **No.** Runtime components (`BeliefEngine`, `EvidenceCompass`, `PolicyEngine`) do not inspect the ground truth keys.
7. **Can benchmark fixtures influence runtime?**
   **Yes, for external tools.** In `src/tools/mock_actions.py` lines 13–19, if `trigger_type == "customer_report"`, `simulate_customer_reply` automatically returns `customer_denied=True`.
8. **Are benchmark cases executed through exactly the same production pipeline?**
   **Yes.** Both `_execute_investigation_sync()` in `src/api/main.py` and `run_phase4_6_2_validation()` in `bench/` call `orchestrator.run_investigation(initial_state, exposure_usd, context={"tg_conn": tg_conn}, enable_llm_synthesis=False)`.
9. **Does the benchmark runner bypass any production component?**
   No, it executes the identical orchestrator. However, both bypass the LLM (`enable_llm_synthesis=False`).
10. **Does it inject evidence?**
    It ingests the case trigger as initial evidence: calibrated risk score ($LR$ from `get_model_score_lr()`) or customer report ($LR=18.5$).
11. **Does it inject graph state?**
    No. Graph state is queried live from TigerGraph Cloud.
12. **Does it inject LLM responses?**
    No LLM responses are used.
13. **Does it inject tool results?**
    For graph tools, results come from live TigerGraph queries. For customer verification / MFA, results come from `mock_actions.py`.
14. **Does it inject expected actions?**
    No. Actions are derived by `PolicyEngine.evaluate()`.
15. **Does it alter time/temporal context?**
    Yes. It passes `anchor_ts=opened_at` to queries to enforce historical temporal windows (preventing future transaction leakage).
16. **Does it alter policy?**
    No.
17. **Does it alter memory?**
    No. `frozen_memory` snapshot isolation is active with zero writebacks during benchmarks.
18. **Does it use test-only mocks?**
    In unit tests (`tests/`), mocked connections are used. In `run_phase4_6_2_validation.py`, it connects to live TigerGraph.
19. **Does it use live TigerGraph?**
    **Yes.** `tg_conn = get_tigergraph_connection()` connects to the live tgcloud instance.
20. **Does "20/20" measure fraud classification, NBA correctness, or merely workflow completion?**
    - **Fraud classification:** 20/20 cases had $P(\text{Fraud}) \ge 0.70$. **However, 100% of benchmark cases are fraud.** There are ZERO legitimate or non-fraud cases in the benchmark. Achieving 20/20 fraud classification is trivial when prior probabilities and trigger risk scores are already elevated.
    - **NBA correctness:** **Actual NBA accuracy is 19/20 (95.0%), NOT 20/20.** `HHG-011` failed because live TigerGraph lacked the card testing sequence present in synthetic ground truth, resulting in `BLOCK_CARD` instead of `DECLINE_TRANSACTION`.
    - **Decision Gate pass rate:** Only **11/20 (55.0%)**. In 9 cases, the gate remained locked because the investigation terminated early due to negative EVOI or max steps.

### Forensic Truth of "20/20 PASS"
The "20/20 PASS (100%)" displayed on the frontend is an **aspirational marketing claim that conceals a real 19/20 benchmark result and an 11/20 decision gate pass rate.**

---

## 5. Unseen Transaction Test: Generalization Audit

### Can Tark Investigate an Unseen Transaction?
> **Answer: NO. The production system cannot accept an arbitrary transaction without code or dataset modifications.**

### The Execution Path & Failure Points

```
[UNSEEN TRANSACTION INPUT]
        ↓
1. API Endpoint Call: POST /api/investigations/{case_id}/run
   ↳ BLOCKER #1: Endpoint expects a case_id, not a transaction payload.
   ↳ In src/api/main.py:722-725:
     cases = load_cases_from_csv()
     case = next((c for c in cases if c["case_id"] == case_id), None)
     if not case:
         raise HTTPException(status_code=404, detail=f"Case {case_id} not found in case pack.")
   ↳ FATAL RESULT: HTTP 404 Case not found.
        ↓
2. Case Creation & Target Resolution
   ↳ BLOCKER #2: Tark lacks a transaction-to-case ingestion endpoint (e.g. POST /api/cases).
   ↳ BLOCKER #3: In src/api/main.py:266-268, case execution requires pre-resolved entities:
     flagged_txn_id = case["flagged_txn_id"]
     card_id = case["card_id"]
     customer_id = case["customer_id"]
     If an arbitrary transaction ID is provided, Tark has NO pre-investigation step to query TigerGraph:
     MATCH (t:Transaction {id: t_id})-[r:PERFORMED_WITH_CARD]->(c:Card)-[r2:BELONGS_TO_CUSTOMER]->(u:Customer)
   ↳ FATAL RESULT: If card_id or customer_id are missing, 4 of 6 EvidenceTools fail or run with empty strings ("").
        ↓
3. Frontend Ingestion
   ↳ BLOCKER #4: In web/src/components/NewInvestigationModal.tsx:87-93, the UI only renders a <select> dropdown of the existing 20 cases from case_pack.csv. There is no input field to enter an arbitrary transaction ID.
```

### Can Python Core Code Run an Unseen Transaction?
If invoked directly via Python scripts (bypassing `src/api/main.py`), `orchestrator.run_investigation()` **can** execute on an arbitrary transaction **provided that**:
1. The transaction already exists in the TigerGraph `FraudInvestigation` graph database.
2. The caller manually constructs an `InvestigationState` with `card_id`, `customer_id`, and `flagged_txn_id` populated in `target_entities`.
3. If the transaction vertex does not exist in TigerGraph, queries return empty sets (`status: NO_MATCH`), resulting in $LR=1.0$, and the system terminates under `NO_ADMISSIBLE_EVIDENCE` or `NEGATIVE_EVOI`.

---

## 6. Agentic Requirements Audit (Hacker House Task 4)

| Requirement | Implementation Status | Evidence / Code Location | Architectural Reality |
|---|---|---|---|
| **1. Agentic Fraud Investigation** | **PARTIALLY IMPLEMENTED** | `src/agent/orchestrator.py:164` | Autonomous loop exists, but tool selection is driven by deterministic EVOI math, not an LLM agent. |
| **2. TigerGraph** | **IMPLEMENTED** | `src/graph/connection.py`, `tgcloud` | Real connection to TigerGraph Cloud cluster with active vertex and edge schemas. |
| **3. GSQL Queries** | **IMPLEMENTED** | `queries/*.gsql` (6 files) | Queries compiled and installed on `FraudInvestigation` graph; executed via RESTPP. |
| **4. Graph Algorithms** | **SIMULATED** | `web/src/components/GlobalGraphExplorer.tsx:218` | Louvain, WCC, and PageRank do not exist in backend. Rendered as static SVG geometry in React. |
| **5. Model Context Protocol (MCP)** | **MISSING** | `tests/test_architecture_hardening.py:150` | `src/mcp` is explicitly forbidden in tests. Zero MCP server/client code in repository. |
| **6. GraphRAG** | **HARDCODED DICTIONARY** | `src/knowledge/retriever.py:51-110` | Hardcoded `if/elif` mapping from `EvidenceType` to static in-memory policy chunks. No vector/graph search. |
| **7. LLM Reasoning** | **DISABLED / DEAD CODE** | `src/api/main.py:338`, `bench/run_...:165` | `enable_llm_synthesis=False` is hardcoded. `orchestrator` initialized with `llm_client=None`. |
| **8. Evidence Gathering** | **IMPLEMENTED** | `src/tools/normalizer.py`, `src/evidence/ledger.py` | Query outputs normalized into structured `EvidenceItem` objects with provenance and $LR$ scores. |
| **9. Dynamic Evidence Selection** | **IMPLEMENTED** | `src/compass/evoi.py:149-350` | Evidence Compass dynamically ranks candidate tools based on expected decision flip value. |
| **10. Additional Evidence When Uncertain** | **IMPLEMENTED** | `src/agent/orchestrator.py:176` | Loop continues gathering evidence while epistemic uncertainty is high and $\text{Net EVOI} > 0$. |
| **11. Case Memory** | **IMPLEMENTED** | `src/memory/store.py`, `src/memory/retriever.py` | Historical cases stored and retrieved with snapshot isolation and zero benchmark leakage. |
| **12. External Data** | **MOCKED / SIMULATED** | `src/tools/mock_actions.py:8-66` | Simulated SMS/IVR replies and MFA challenges using static keyword parsing and timeouts. |
| **13. Policy-Aware Next-Best-Action** | **IMPLEMENTED** | `src/policy/engine.py:40-250` | Rules R1–R10 determine `PRIMARY` vs `CONSEQUENTIAL` actions and L1/L2/L3 approval tiers. |
| **14. Human Approval Governance** | **IMPLEMENTED** | `src/api/main.py:788`, `web/src/components/AnalystDecision.tsx` | Analyst can approve, reject, or request more evidence; records audit trail. |
| **15. Grounded Explanation / SAR** | **HARDCODED IN UI / DETERMINISTIC IN BACKEND** | `src/synthesis/synthesizer.py:180`, `ExplanationSarView.tsx:149` | Backend has deterministic template generator; frontend ignores it and renders a hardcoded string. |
| **16. Case Management** | **PARTIALLY IMPLEMENTED** | `src/api/main.py:117`, `InvestigationQueue.tsx` | View existing cases and pivot on graph entities, but cannot create or ingest new cases. |

---

## 7. LLM Forensic Audit

### LLM Call Inventory

| # | File & Line | Method / Prompt | Input | Output | System Influence | Production API Path? | Benchmark Path? | Real / Fallback / Mock |
|---|---|---|---|---|---|---|---|---|
| **1** | `src/tools/llm_client.py:13` | `generate(system_prompt, user_prompt)` | System + user prompt | Raw completion text | None (returns string) | **NO** (`llm_client=None`) | **NO** (`enable_llm_synthesis=False`) | Real DeepSeek endpoint with hardcoded FinCEN fallback |
| **2** | `src/synthesis/synthesizer.py:126` | Grounded investigation synthesis | `InvestigationContextDocument` | 2-paragraph SAR summary | Narrative text only (never touches belief/policy) | **NO** (`use_llm=False`) | **NO** (`use_llm=False`) | Deterministic fallback template (`synthesizer.py:180`) |
| **3** | `src/agent/orchestrator.py:517` | Executive summary refinement | State + traces summary | Refined summary | Narrative text only | **NO** (`enable_llm_synthesis=False`) | **NO** (`enable_llm_synthesis=False`) | Deterministic template (`orchestrator.py:488`) |

### Forensic Finding: Is Tark Agentic via LLM?
**No.** Tark's decision-making, tool selection, evidence gathering, policy routing, and narrative generation are **100% independent of any LLM**. The LLM is completely turned off in production and benchmarks. When enabled in unit tests, it only provides cosmetic natural language summaries of decisions that were already deterministically reached.

---

## 8. MCP (Model Context Protocol) Forensic Audit

### Forensic Findings
1. **MCP Does Not Exist:** A comprehensive search across the repository reveals **zero** MCP server definitions (`FastMCP`, `@server.tool()`, stdio transport, SSE transport).
2. **Explicitly Guarded Against MCP:** In `tests/test_architecture_hardening.py` lines 149–156:
   ```python
   forbidden_future_files = [
       os.path.join(tark_root, "src", "mcp"),
       os.path.join(tark_root, "src", "graphrag"),
       os.path.join(tark_root, "src", "agent", "react_loop.py")
   ]
   for p in forbidden_future_files:
       assert not os.path.exists(p), f"Future phase file {p} found before authorized phase"
   ```
   The test explicitly asserts that `src/mcp` does **NOT** exist!
3. **Cosmetic Claims:** The claim in frontend navigation and phase reports that "MCP Tools: 50+ loaded" is a **fictional marketing assertion**.
4. **Actual Dispatch Mechanism:** Tools are dispatched via `EvidenceToolDispatcher` (`src/tools/dispatcher.py`), which maintains a Python dictionary of `EvidenceTool` instances.

---

## 9. TigerGraph Forensic Audit

### Connection & Execution Integrity
- **Live Connection:** Configured in `src/graph/connection.py` using `pyTigerGraph.TigerGraphConnection` pointing to `https://tg-3242c55c...i.tgcloud.io:443`.
- **Graph Name:** `FraudInvestigation`.
- **Installed Queries:**
  1. `device_analysis(STRING t_id)`
  2. `card_sequence(STRING c_id, INT window_hours, STRING anchor_ts)`
  3. `txn_velocity(STRING c_id, INT window_hours, STRING target_ts)`
  4. `region_analysis(STRING c_id, DOUBLE txn_addr1)`
  5. `customer_profile(STRING cust_id)`
  6. `similar_cases(STRING target_pattern, STRING c_id)`

### Parameter Propagation & Temporal Integrity
- In `src/tools/dispatcher.py` lines 133–151:
  - `t_id` correctly propagates from `state.trigger["flagged_txn_id"]`.
  - `c_id` correctly propagates from `state.target_entities["card_id"]`.
  - `cust_id` correctly propagates from `state.target_entities["customer_id"]`.
  - `anchor_ts` and `target_ts` correctly propagate from `state.trigger["timestamp"]`.
- **Temporal Integrity:** Queries correctly bound temporal lookups to $t \le \text{opened\_at}$, preventing future information leakage.

---

## 10. Graph Algorithm Audit

### Algorithm Classification Matrix

| Capability | Claimed in Docs/UI | Implemented in Code? | Evidence |
|---|---|---|---|
| **Graph Storage** | Yes | **YES** | TigerGraph Cloud cluster storing vertices (Transaction, Card, Customer, DeviceProfile) |
| **Graph Query** | Yes | **YES** | 6 parameterized GSQL queries executing via RESTPP |
| **Graph Traversal** | Yes | **YES** | Multi-hop traversal in `device_analysis.gsql`: `Transaction -> DeviceProfile -> Transaction -> Card` |
| **Graph Reasoning** | Yes | **YES** | Bayesian likelihood ratios calculated from graph traversal findings (e.g. shared card count $\ge 3 \implies LR=85.7$) |
| **Graph Algorithms** | Yes (Louvain, WCC, PageRank) | **NO (100% SIMULATED)** | Zero GSQL algorithm queries. `GlobalGraphExplorer.tsx:218` renders hardcoded SVG |
| **Graph Visualization** | Yes | **YES (PARTIALLY DERIVED)** | `_build_graph_from_run()` dynamically maps run evidence into graph nodes/edges |

---

## 11. GraphRAG Audit

### Implementation Reality
- **Class:** `PolicyGraphRAGRetriever` (`src/knowledge/retriever.py`).
- **Method:** `retrieve_grounded_context()`.
- **Retrieval Mechanism:**
  ```python
  if EvidenceType.CARD_TESTING_SEQUENCE in evidence_types or EvidenceType.HIGH_VELOCITY in evidence_types:
      chunk = self.kb.get_chunk("KNOW-TYPO-CARDTESTING")
  if EvidenceType.SHARED_DEVICE_RING in evidence_types or EvidenceType.PROXY_DETECTED in evidence_types:
      chunk = self.kb.get_chunk("KNOW-TYPO-SHARED-DEVICE")
  if EvidenceType.OUT_OF_REGION in evidence_types:
      chunk = self.kb.get_chunk("KNOW-TYPO-OUT-OF-REGION")
  ```
- **Finding:** GraphRAG is **not** a vector retrieval or graph-traversal RAG system. It is a **deterministic rule-based lookup table** mapping observed `EvidenceType` enums to static text chunks in `InvestigationKnowledgeBase`.
- **Safety Guarantee:** The retriever strictly adheres to the rule that retrieved knowledge **never** mutates $P(\text{Fraud})$, never alters uncertainty, and never counts as empirical evidence.

---

## 12. Case Memory Audit

### Memory Architecture & Leakage Analysis
- **Storage:** `CaseMemoryStore` (`src/memory/store.py`) backed by `closed_cases_history.csv`.
- **Retrieval:** `CaseMemoryRetriever` (`src/memory/retriever.py`).
- **Snapshot Isolation:** In `src/api/main.py:58` and benchmark runs, `create_snapshot(effective_timestamp="2016-11-11 23:59:59")` creates an immutable in-memory view. Writebacks are disabled (`writeback_path=None`).
- **Contamination Check:**
  - `active_id` isolation check (`retriever.py:87`) ensures the case being investigated is never retrieved as a precedent.
  - Zero memory writeback occurred during benchmark runs (asserted in `run_phase4_6_2_validation.py:170`).
- **Verdict:** Case memory is **cleanly isolated** and does not leak benchmark answers or contaminate subsequent cases.

---

## 13. Evidence System Audit

### Evidence Processing Pipeline
```
TigerGraph GSQL Query / External Tool
                 ↓ Raw JSON
      EvidenceNormalizer.normalize()
                 ↓ Typed EvidenceItem (LR, Log_LR, Finding, Provenance)
        EvidenceLedger.add()
                 ↓ Duplicate Damping & Family Tracking
       BeliefEngine.evaluate_investigation()
```

### Empirical Integrity
- Evidence generated by `DeviceAnalysisTool`, `CardSequenceTool`, and `TxnVelocityTool` is **empirical**: it parses actual JSON records from TigerGraph RESTPP responses.
- If TigerGraph returns an empty set, `EvidenceNormalizer` correctly produces a neutral finding (`NO_MATCH`, $LR=1.0, \log \mathcal{LR}=0.0$).
- **Cosmetic Fallback:** In `_build_graph_from_run()` (`src/api/main.py:596`), if transaction details lack connected IDs, placeholder strings like `CARD_RING_1` or `TXN_MICRO_1` are generated for visualization only; they do not enter the `EvidenceLedger`.

---

## 14. Belief / Probability Engine Audit

### Mathematical Formula
- Initial Prior: $\text{Odds}_0 = \frac{P_0}{1 - P_0}$, $\text{LogOdds}_0 = \ln(\text{Odds}_0)$.
- Update Formula:
  $$\text{LogOdds}_k = \text{LogOdds}_{k-1} + \sum_{i} \text{damping}_i \cdot \log \mathcal{LR}_i$$
  $$P(\text{Fraud}) = \frac{1}{1 + e^{-\text{LogOdds}_k}}$$
- Likelihood Ratios are derived from `LIKELIHOOD_REGISTRY` in `src/belief/calibration.py`:
  - `SHARED_DEVICE_RING`: $LR = 85.7$ ($\log \mathcal{LR} = 4.451$)
  - `CARD_TESTING_SEQUENCE`: $LR = 34.3$ ($\log \mathcal{LR} = 3.535$)
  - `CUSTOMER_DENIAL`: $LR = 18.5$ ($\log \mathcal{LR} = 2.918$)
  - `HIGH_VELOCITY`: $LR = 6.2$ ($\log \mathcal{LR} = 1.825$)
  - `NO_MATCH` / `TIMEOUT`: $LR = 1.0$ ($\log \mathcal{LR} = 0.0$)
- **Guarantees Verified:**
  - LLM cannot change $P(\text{Fraud})$.
  - Benchmark ground truth cannot change $P(\text{Fraud})$.
  - Duplicate evidence within the same family is damped ($0.5\times$ for second, $0.25\times$ for third).
  - Failed queries ($LR=1.0$) do not alter probability.

---

## 15. Evidence Compass / EVOI Audit

### Decision-Theoretic Planner
- **Formulation:**
  $$\text{EVOI}(a) = \mathbb{E}[\text{Decision Value After Action } a] - \text{Current Decision Value}$$
  $$\text{Net Decision Value} = \text{EVOI}(a) - \text{Operational Burden Cost}$$
- **Candidate Evaluation:** In each iteration, `EvidenceCompass.evaluate_evidence_compass()` evaluates each unexecuted candidate tool across possible outcomes (e.g. `CARD_TESTING_SEQUENCE` vs `NO_MATCH`) weighted by transition probabilities ($P(\text{outcome} \mid \text{state})$).
- **Adaptive Execution:** If an outcome flips the optimal policy action, EVOI is high. If an action cannot change the decision, $\text{EVOI} \le 0$ and the tool is pruned.
- **Verdict:** The Evidence Compass is **genuinely mathematical and adaptive**. However, the frontend (`EvidenceCompassView.tsx`) fails to display this live data, rendering static mock numbers instead.

---

## 16. Autonomous Investigation Loop Audit

### State Machine & Loop Control
- Implemented in `src/agent/orchestrator.py` lines 164–295.
- **Termination Precedence:**
  1. `HUMAN_APPROVAL_REQUIRED` (if contradiction / conflict detected)
  2. `DECISION_REACHED` (decision gate passed and no positive EVOI remains)
  3. `NO_ADMISSIBLE_EVIDENCE` (all candidate tools exhausted)
  4. `NEGATIVE_EVOI` (remaining candidate tools have Net Decision Value $\le 0$)
  5. `TOOL_FAILURE_LIMIT` ($\ge 2$ consecutive failures)
  6. `MAX_STEPS_REACHED` (budget limit reached, default 5 steps)
- **Who Decides Next Step?** The **Evidence Compass EVOI ranking**.
- **Verdict:** The investigation loop is an **autonomous, deterministic decision-theoretic agent**. It is **not** an LLM agent, but it is genuinely autonomous.

---

## 17. Next-Best-Action (NBA) & Policy Engine Audit

### Institutional Policy Rules (R1–R10)
- Defined in `src/policy/engine.py`.
- **Action Roles:**
  - `PRIMARY`: Authoritative operational command (`BLOCK_CARD`, `DECLINE_TRANSACTION`, `CREATE_CASE`, `ALLOW_TRANSACTION`, `MONITOR_CARD`).
  - `CONSEQUENTIAL`: Mandatory downstream actions (`FILE_REPORT` / SAR, `MONITOR_CONNECTED_CARDS`).
- **Approval Tiers:**
  - `auto`: Fully automated execution.
  - `L1`: First-line fraud analyst review.
  - `L2`: Senior fraud manager / syndicate approval.
  - `L3`: Compliance / legal officer sign-off.
- **Verdict:** NBA derivation is **genuinely derived** from empirical findings and policy rules, with clear mathematical precedence.

---

## 18. Frontend ↔ Backend Forensic Audit

### Component-by-Component Reality

| Component | Displayed Element | Source in Codebase | Classification |
|---|---|---|---|
| **OverviewView** | 5 KPI Cards (Accuracy 100%, Wasted 0%) | Hardcoded in `OverviewView.tsx:16-47` | **HARDCODED FRONTEND DATA** |
| **OverviewView** | Case Queue List | Fetched via `GET /api/cases` from `case_pack.csv` | **LIVE BACKEND DATA** |
| **BenchmarkView** | Baseline Comparison Table | Hardcoded in `BenchmarkView.tsx:13-55` | **HARDCODED FRONTEND DATA** |
| **BenchmarkView** | 20-Case Matrix (`✓ PASS`) | Hardcoded badge in `BenchmarkView.tsx:231,291` | **HARDCODED FRONTEND DATA** |
| **PolicyPatternsView** | Policy Rules & Typologies | Hardcoded in `PolicyPatternsView.tsx:16-85` | **HARDCODED FRONTEND DATA** |
| **GlobalGraphExplorer** | Algorithm Projections (Louvain, WCC) | Hardcoded SVG in `GlobalGraphExplorer.tsx:218` | **100% SIMULATED IN FRONTEND** |
| **GlobalGraphExplorer** | Node/Edge Counts (40,830 / 590,000) | Hardcoded in `GlobalGraphExplorer.tsx:175` | **STATIC LABEL** |
| **EvidenceCompassView**| Candidate EVOI Table (`+0.41`, `+0.34`) | Hardcoded in `EvidenceCompassView.tsx:12-93` | **HARDCODED FIXTURE DATA** |
| **ExplanationSarView** | Investigation Narrative & SAR | Hardcoded in `ExplanationSarView.tsx:149-175` | **HARDCODED FRONTEND DATA** |
| **RunTraceConsole** | Execution Events Telemetry | Read from `result.events` (`_build_events_from_run`) | **LIVE BACKEND DATA** |
| **RiskAssessment** | Fraud Probability ($P(\text{Fraud})$) | Read from `result.run_result.final_state.fraud_probability` | **LIVE BACKEND DATA** |
| **DecisionGate** | Decision Gate Status & Passed Flag | Read from `result.run_result.final_state.decision_gate_passed` | **LIVE BACKEND DATA** |
| **NextBestAction** | Recommended Primary & Consequential Actions | Read from `result.run_result.primary_action` | **LIVE BACKEND DATA** |
| **KeyEvidenceFindings**| Empirical Evidence Items & LR Values | Read from `result.run_result.final_state.evidence_items` | **LIVE BACKEND DATA** |
| **InvestigationNetwork**| Interactive Graph Visualization | Read from `result.graph` (`_build_graph_from_run`) | **DERIVED FROM RUN RESULT** |
| **AnalystDecision** | Interactive Governance & Human Override | Submits to `POST /api/investigations/{id}/decision` | **LIVE BACKEND INTERACTION** |

---

## 19. "Frontend is Just Showing a Result" Audit

### Execution Flow Upon Clicking "Start Investigation"
1. **Frontend Action:** User clicks "Start Investigation" in `InvestigationPreStartView.tsx`.
2. **API Call:** Frontend triggers `POST /api/investigations/{case_id}/run`.
3. **Backend Execution:** The FastAPI server executes `_execute_investigation_sync(case)` **synchronously on the server thread**:
   - Queries TigerGraph vertex for transaction exposure.
   - Runs `orchestrator.run_investigation()` through the full EVOI while-loop.
   - Computes final state, policy recommendations, graph topology, and event list.
   - Caches result in `INVESTIGATION_RUNS[case_id]`.
   - Returns complete JSON payload to the frontend.
4. **Frontend Rendering:** Frontend receives the completed payload in a single response and renders all tabs.
5. **Verdict:** The investigation **is genuinely executed in real-time on the backend**, but the execution is synchronous (blocking HTTP POST) rather than streamed via SSE. The frontend does **not** simulate the run visually; it displays the completed backend trace.

---

## 20. Event / Activity Timeline Audit

- **Generation:** Events are constructed in `_build_events_from_run()` (`src/api/main.py:132–257`) from the `iteration_traces` array produced by `InvestigationOrchestrator`.
- **Accuracy:** Every event displayed in `InvestigationActivity.tsx` and `RunTraceConsole.tsx` corresponds 1-to-1 with an actual iteration executed by the backend planner, including the exact tool called, belief before/after, and coverage before/after.
- **Limitation:** Events are generated post-hoc from the trace after the synchronous run completes, rather than streamed during execution.

---

## 21. Graph UI Audit

### Two Divergent Graph Implementations in Tark
1. **Investigation Network Tab (`InvestigationNetwork.tsx`):**
   - **Status:** **REAL DERIVED DATA.**
   - Uses `result.graph` built by `_build_graph_from_run()` (`src/api/main.py:480`).
   - Nodes represent the real focal transaction, card, customer, and evidence-discovered devices.
   - Edges represent real GSQL relationships with empirical likelihood ratios.
2. **Global Graph Explorer (`GlobalGraphExplorer.tsx`):**
   - **Status:** **100% FRONTEND SIMULATION.**
   - Static SVG canvas with hardcoded circle coordinates.
   - Toggling Louvain, WCC, or PageRank does not query TigerGraph or alter geometry.

---

## 22. Frontend UI/UX Audit: AI-Slop & Judge-Clarity Problems

1. **AI-Slop & Cosmetic Placeholders:**
   - `web/src/components/BenchmarkView.tsx`: Hardcoded comparison table claiming `TARK: 100.0%` vs synthetic baselines. Judges will immediately identify this as unvalidated promotional copy.
   - `web/src/components/OverviewView.tsx`: 5 static KPI cards claiming `100% Action Accuracy` and `0% Wasted Requests` regardless of backend health.
   - `web/src/components/PolicyPatternsView.tsx`: Static cards with hardcoded benchmark case IDs.
2. **Terminology Inconsistencies:**
   - Frontend displays "20 / 20 PASSING (100%)", but backend benchmark reports prove NBA accuracy was 19/20 and decision gate pass rate was 11/20.
3. **Dead Tabs / Disconnected Views:**
   - `EvidenceCompassView.tsx` ignores its input prop and displays static numbers.
   - `ExplanationSarView.tsx` ignores backend synthesis and renders hardcoded Rule R5 text.

---

## 23. Demo / Judge Experience Audit (5-Minute Evaluation)

If a Hacker House judge spends 5 minutes reviewing Tark:
- **Minutes 0–1 (Queue & Trigger):** The judge sees a clean fraud queue with 20 cases and clear trigger metadata. **(Strong impression)**
- **Minutes 1–2 (Execution & Live Graph):** The judge clicks "Start Investigation". The backend executes real TigerGraph GSQL queries, updates Bayesian log-odds, and renders an interactive network graph with likelihood ratios. **(Very strong impression)**
- **Minutes 2–3 (Decision Rail):** The judge inspects the Decision Gate, Next-Best-Action, and interactive Analyst Override. **(Strong impression)**
- **Minutes 3–4 (Forensic Scrutiny):** The judge clicks "Global Graph Explorer" or "Evidence Compass" and immediately notices static SVG diagrams and hardcoded candidates. The judge checks `src/mcp` and discovers zero MCP code. **(Severe credibility drop)**
- **Minutes 4–5 (Generalization Test):** The judge asks: "Can you run this other transaction from our test set?" The system returns `HTTP 404 Case not found in case pack`. **(Fatal submission failure)**

---

## 24. Competitive Differentiation Audit

| Claimed Feature | Genuine Technical Differentiator? | Why / Code Evidence |
|---|---|---|
| **Decision-Theoretic EVOI** | **GENUINE DIFFERENTIATOR** | `src/compass/evoi.py` computes real expected utility differences ($EDV - \text{cost}$) to stop investigations when further queries have no information value. Almost no hackathon competitor implements mathematical EVOI. |
| **Bayesian Belief Engine** | **GENUINE DIFFERENTIATOR** | `src/belief/engine.py` replaces non-deterministic LLM probability guessing with auditable log-likelihood ratios. |
| **Deterministic Policy Authority** | **GENUINE DIFFERENTIATOR** | Institutional policy rules (R1–R10) authoritatively control actions and approval routes; LLM cannot override policy. |
| **Live TigerGraph Integration** | **SOLID IMPLEMENTATION** | 6 compiled GSQL queries querying live tgcloud cluster. |
| **Graph Algorithms** | **NOT DIFFERENTIATED (FAKED)** | Hardcoded SVG in frontend; zero backend algorithm implementation. |
| **GraphRAG** | **STANDARD / WEAK** | Simple dictionary lookup; no vector retrieval or graph reasoning. |
| **MCP** | **NON-EXISTENT** | Zero implementation in codebase. |

---

## 25. Failure Mode Audit

1. **TigerGraph Cloud Down:**
   - In `src/tools/graph_tools.py:38`, if connection is `None`, returns `ScopeResponse(status=GRAPH_QUERY_FAILURE)`.
   - `EvidenceNormalizer` produces neutral evidence ($LR=1.0$).
   - Investigation terminates cleanly under `NO_ADMISSIBLE_EVIDENCE` or `NEGATIVE_EVOI`. **(Fails safely)**
2. **Unknown Case ID Submitted:**
   - `src/api/main.py:725` raises `HTTPException(status_code=404, detail="Case not found in case pack")`. **(Fails cleanly, but blocks generalization)**
3. **Empty Graph Result:**
   - Returns `NO_MATCH` with $LR=1.0$. Does not crash or fabricate fraud. **(Fails safely)**
4. **Customer Verification Timeout:**
   - `mock_actions.py:43` returns `status=UNAVAILABLE`, `customer_denied=None`, $LR=1.0$. Preserves prior belief without false exoneration. **(Fails safely)**

---

## 26. Test Quality Audit

- **Test Suite Stats:** 273 Python tests in `tests/`, 53 TypeScript tests in `web/src/test/`. All 326 tests pass.
- **What Tests Actually Prove:**
  - Mathematical correctness of Bayesian log-odds updates.
  - State machine transitions in `orchestrator.py`.
  - Policy Engine rule precedence (R1–R10).
  - Memory snapshot isolation and temporal boundary enforcement.
  - React component rendering and analyst interaction callbacks.
- **What Tests Do NOT Prove:**
  - They do **not** test unseen transactions.
  - They do **not** test MCP (they test that MCP is *absent*).
  - They do **not** test LLM reasoning (LLM is mocked in tests and disabled in API).
  - They do **not** test Graph Algorithms (Louvain/WCC are untested frontend SVGs).

---

## 27. Test for "Passing Because the System is Easy" (Benchmark Limitations)

1. **100% Fraud Class Imbalance:** All 20 cases in `case_pack.csv` have ground truth label `fraud`. There are **zero negative controls** (legitimate cardholders making unusual but valid purchases). A system that always predicts fraud would achieve 100% verdict accuracy!
2. **Prior Inflation:** 17 of 20 cases start with high initial risk scores ($\ge 0.70$) or customer denial reports ($LR=18.5$), meaning the Bayesian prior alone pushes $P(\text{Fraud}) \ge 0.85$ before any TigerGraph query runs.
3. **Benchmark Weakness:** The benchmark does not adequately test the system's ability to exonerate innocent transactions or detect false-positive alarms.

---

## 28. Architectural Integrity Audit

| Architectural Boundary | Rule | Enforced in Code? | Proof |
|---|---|---|---|
| **LLM Boundary** | LLM must not fabricate evidence or alter probability | **YES** | `src/agent/orchestrator.py:517` — LLM output only formats text, never mutates state. Disabled in API. |
| **Case Memory Boundary** | Memory must not become empirical evidence | **YES** | `src/memory/retriever.py` — Precedents returned as contextual metadata; zero $LR$ assigned. |
| **GraphRAG Boundary** | Retrieved regulations must not alter probability | **YES** | `src/knowledge/retriever.py:26` — Explicitly guaranteed: never mutates numeric probability. |
| **Policy Authority Boundary** | Policy engine holds exclusive authority over actions | **YES** | `src/policy/engine.py` — Strictly evaluated from final state; cannot be overridden by LLM. |
| **Benchmark Isolation** | Production paths must not know benchmark answers | **YES** | Zero ground truth imports in `src/agent/` or `src/belief/`. |

---

## 29. Data Flow Proof: End-to-End Traces

### Trace 1: HHG-011 (Customer Dispute / Mismatch Case)
```
Input Case: HHG-011 (Customer report: "I never made this $131.30 purchase...")
  ↓
API: POST /api/investigations/HHG-011/run (src/api/main.py:720) [REAL]
  ↓
Trigger Ingestion: EvidenceItem(CUSTOMER_DENIAL, LR=18.5, log_lr=2.918) [REAL]
  ↓
Belief Engine: Initial P(Fraud) = 0.9487, Coverage = 0.1667 [REAL]
  ↓
Evidence Compass: Evaluates candidates; selects QUERY_DEVICE_ANALYSIS [REAL]
  ↓
TigerGraph Tool: Executes device_analysis(t_id="3583368") on tgcloud [REAL]
  ↓
Raw Result: Clean device, 1 card, is_proxy=false → LR=1.0 (NO_MATCH) [REAL]
  ↓
Belief Engine: P(Fraud) remains 0.9487, Coverage = 0.3333 [REAL]
  ↓
Evidence Compass: Evaluates remaining candidates; selects QUERY_CARD_SEQUENCE [REAL]
  ↓
TigerGraph Tool: Executes card_sequence(c_id="C11923-K2") on tgcloud [REAL]
  ↓
Raw Result: No micro-auth sequence in live graph → LR=1.0 (NO_MATCH) [REAL]
  ↓
Evidence Compass: Evaluates remaining candidates; selects QUERY_TXN_VELOCITY [REAL]
  ↓
TigerGraph Tool: Executes txn_velocity(c_id="C11923-K2") on tgcloud [REAL]
  ↓
Raw Result: Normal velocity → LR=1.0 (NO_MATCH) [REAL]
  ↓
Loop Termination: NEGATIVE_EVOI (Remaining tools have EDV <= 0) [REAL]
  ↓
Policy Engine: Rule R2 fires (Customer Denial = True) → PRIMARY: BLOCK_CARD (L1) [REAL]
  ↓
Expected GT Mismatch: GT expected DECLINE_TRANSACTION (R5). System correctly chose BLOCK_CARD because live graph lacked card testing evidence! [PROVED]
  ↓
API Response: Complete JSON payload returned [REAL]
  ↓
Frontend: Displays 94.9% Risk, BLOCK_CARD NBA, but BenchmarkView falsely claims 100% match [DISCREPANCY]
```

### Trace 2: HHG-014 (Analyst Request Cold-Start Case)
```
Input Case: HHG-014 (Analyst request: "Investigate unusual pattern on C18241")
  ↓
API: POST /api/investigations/HHG-014/run [REAL]
  ↓
Trigger Ingestion: No risk score, no customer denial. Prior = 0.50 (Uninformative) [REAL]
  ↓
Compass Evaluation: Zero initial evidence → EVOI <= 0.0 for all tools [REAL]
  ↓
Loop Termination: Terminates at Step 0 under NEGATIVE_EVOI [REAL]
  ↓
Policy Engine: Evaluates uninformative state → PRIMARY: CREATE_CASE (auto) [REAL]
  ↓
API Response: Returns 0-step trace with CREATE_CASE [REAL]
```

---

## 30. Bottleneck Analysis

### 1. Technical Bottlenecks
- **Synchronous API Execution:** `_execute_investigation_sync()` blocks the FastAPI event loop for 1.5–3.0 seconds per case while executing GSQL RESTPP calls.
- **RESTPP Latency:** Each TigerGraph query takes 150–400ms over HTTPS to TigerGraph Cloud.

### 2. Architectural Bottlenecks
- **No Transaction Ingestion Pipeline:** Case creation is coupled to `case_pack.csv`. There is no schema or service to ingest an arbitrary incoming transaction stream.
- **Missing Graph Entity Resolution:** System assumes `card_id` and `customer_id` are pre-known. It cannot traverse `Transaction -> Card -> Customer` on cold start.

### 3. Product & Demo Bottlenecks
- **Static Frontend Shells:** `GlobalGraphExplorer.tsx` and `EvidenceCompassView.tsx` display hardcoded data that destroys credibility under close inspection.
- **Overstated Marketing Copy:** Unconditional "100% Accuracy" badges raise immediate red flags for experienced judges.

---

## 31. Prioritized Findings (P0 / P1 / P2 / P3)

### P0 — Submission Disqualifiers (Must Be Addressed or Explicitly Framed)
- **P0.1: Unseen Transactions Unsupported:** API rejects any case not in `case_pack.csv` with HTTP 404.
- **P0.2: Fictional MCP Architecture:** MCP is claimed in UI and documentation, but zero MCP code exists in `src/`.
- **P0.3: LLM 100% Disabled in Production:** The system makes zero LLM calls during live demo or benchmark runs.
- **P0.4: Graph Algorithms 100% Simulated in UI:** Louvain, WCC, and PageRank are hardcoded SVG drawings in React.

### P1 — Major Credibility & Selection Risks
- **P1.1: 20/20 Accuracy is Misleading:** Actual live NBA accuracy is 19/20 (95%), Decision Gate pass rate is 11/20 (55%), and benchmark has zero negative controls.
- **P1.2: Evidence Compass UI Disconnected:** `EvidenceCompassView.tsx` ignores live run results and displays static mock candidate values.
- **P1.3: Hardcoded Policy Case IDs:** `PolicyPatternsView.tsx` contains hardcoded arrays of the 20 benchmark case IDs.
- **P1.4: SAR Narrative Hardcoded in React:** `ExplanationSarView.tsx` hardcodes citations to Rule R5 for all cases.

### P2 — Significant Technical Weaknesses
- **P2.1: GraphRAG is a Dictionary Lookup:** No vector embeddings or semantic search; simple `if/elif` mapping on `EvidenceType`.
- **P2.2: External Tools are Mocked:** Customer verification and MFA tools use keyword heuristics in `mock_actions.py`.
- **P2.3: Synthetic Graph Nodes:** Missing transaction or card IDs in graph visualizer fall back to synthetic placeholder strings (`CARD_RING_1`, `TXN_MICRO_1`).

### P3 — Polish & Aesthetic Issues
- **P3.1: Excessive Cosmetic KPI Cards:** Hardcoded "100% Accuracy" and "0% Wasted Requests" in Command Center overview.
- **P3.2: Synchronous Execution UX:** Investigation runs block synchronously instead of streaming live execution steps via SSE.

---

## 32. Evidence Table

| # | Finding | Severity | File | Function / Component | Concrete Evidence | Impact | Confidence |
|---|---|---|---|---|---|---|---|
| **1** | MCP completely missing | **P0** | `tests/test_architecture_hardening.py` | `test_no_future_phase_behavior_present:150` | `forbidden_future_files = [os.path.join(tark_root, "src", "mcp"), ...]` | UI claims "MCP Tools: 50+ loaded" are completely fictional | 100% |
| **2** | LLM disabled in live runs | **P0** | `src/api/main.py` | `_execute_investigation_sync:338` | `orchestrator.run_investigation(..., enable_llm_synthesis=False)` | Zero AI/LLM calls happen during demo or benchmark | 100% |
| **3** | Unseen transactions return 404 | **P0** | `src/api/main.py` | `run_investigation_endpoint:724-725` | `if not case: raise HTTPException(status_code=404)` | System cannot investigate any transaction outside `case_pack.csv` | 100% |
| **4** | Graph algorithms are static SVG | **P0** | `web/src/components/GlobalGraphExplorer.tsx` | `GlobalGraphExplorer:222-272` | `<circle cx="0" cy="0" r="14" fill="#ea580c" /> {[-40,-20,0,20,40].map(...)}` | Louvain/WCC/PageRank do not execute on TigerGraph | 100% |
| **5** | Actual NBA accuracy is 19/20 | **P1** | `docs/phase4.6.2-benchmark-validation.md` | Section 4: `HHG-011 Forensic Investigation` | `HHG-011: Expected DECLINE_TRANSACTION, Actual BLOCK_CARD` | Claim of 20/20 NBA accuracy is factually false | 100% |
| **6** | Evidence Compass view is mock | **P1** | `web/src/components/EvidenceCompassView.tsx` | `EvidenceCompassView:8-13` | `({ result: _result }) => { const candidates = [{ netEvoi: "+0.41", ... }] }` | Ignores live run; displays hardcoded candidate table | 100% |
| **7** | Benchmark cases hardcoded in policy view | **P1** | `web/src/components/PolicyPatternsView.tsx` | `PolicyPatternsView:23-82` | `citedCases: ["HHG-003", "HHG-004", ...]` | Directly maps benchmark IDs to policy rules | 100% |
| **8** | SAR Narrative hardcoded in UI | **P1** | `web/src/components/ExplanationSarView.tsx` | `ExplanationSarView:149-175` | `<p><sup>[2]</sup> Policy rule R5: Micro-authorization...</p>` | Always cites Rule R5 regardless of actual investigated case | 100% |
| **9** | GraphRAG is dictionary lookup | **P2** | `src/knowledge/retriever.py` | `retrieve_grounded_context:51-110` | `if EvidenceType.CARD_TESTING_SEQUENCE in evidence_types: get_chunk("KNOW-TYPO-CARDTESTING")` | No vector search, embeddings, or graph traversal in RAG | 100% |
| **10**| External tools simulated | **P2** | `src/tools/mock_actions.py` | `simulate_customer_reply:13-19` | `if trigger_type == "customer_report": return {"customer_denied": True}` | SMS/IVR responses are hardcoded mock dictionaries | 100% |
| **11**| Static KPI metrics in overview | **P3** | `web/src/components/OverviewView.tsx` | `OverviewView:16-47` | `kpis = [{ label: "Action Accuracy", value: "100%" }, ...]` | Static marketing claims in Command Center overview | 100% |

---

## 33. Recommended Fix Order

### MUST FIX (Before Final Submission)
1. **Unify the Presentation Narrative Around Truth:**
   - **Do NOT claim MCP.** Frame the tool execution layer as an **Authoritative Deterministic Tool Dispatcher with GraphScope Isolation**. This is technically accurate, defensible, and impressive.
   - **Do NOT claim LLM-driven decision making.** Frame the architecture as **Neuro-Symbolic / Decision-Theoretic**: deterministic Bayesian EVOI handles high-stakes banking decisions, while LLM is reserved for optional post-hoc natural language synthesis.
   - **Acknowledge the 19/20 Live Benchmark Reality:** Present the HHG-011 discrepancy as proof of system integrity: *"Tark refused to fabricate a transaction decline when live TigerGraph data proved no micro-authorizations existed, correctly applying the customer dispute containment rule instead."*
2. **Remove Fictional Frontend Displays:**
   - Remove or replace `GlobalGraphExplorer.tsx` static SVG with a live TigerGraph schema topology view.
   - Wire `EvidenceCompassView.tsx` to display the actual `iteration_traces.candidate_net_decision_values` returned in `result_payload`.
   - Wire `ExplanationSarView.tsx` to render `result.run_result.grounded_synthesis` from the backend instead of the hardcoded Rule R5 template.

### SHOULD FIX (High-Value Polish)
3. **Add an Unseen Transaction Ingestion Route:**
   - Add `POST /api/investigations/arbitrary` that accepts `{ "flagged_txn_id": "...", "card_id": "...", "customer_id": "...", "risk_score": 0.85 }` and runs the pipeline.
   - Add a "Custom Transaction" tab in `NewInvestigationModal.tsx`.
4. **Remove Hardcoded Benchmark IDs from UI:**
   - In `PolicyPatternsView.tsx`, remove the static `citedCases: ["HHG-003", ...]` arrays and replace them with typology definitions and policy criteria.

### NICE TO HAVE (Future Roadmap)
5. Implement real Vector GraphRAG using embeddings over regulatory statutes.
6. Implement a live MCP server wrapper around `EvidenceToolDispatcher`.
7. Stream investigation events via Server-Sent Events (SSE) instead of synchronous POST.

---

## 34. Final Verdict: Direct Answers to All 20 Questions

1. **Is anything hardcoded specifically for the 20 cases?**
   **Yes in the frontend, No in the backend reasoning engine.** In the frontend, `PolicyPatternsView.tsx` hardcodes case IDs (`HHG-001`..`HHG-020`) onto policy cards, and `BenchmarkView.tsx` hardcodes static `✓ PASS` badges and baseline comparison numbers. The backend `BeliefEngine`, `EvidenceCompass`, and `PolicyEngine` do NOT contain case-specific branches or cheat tables.
2. **Can an unseen transaction run?**
   **No, not through the API.** `POST /api/investigations/{case_id}/run` looks up `case_id` in `case_pack.csv` and returns a 404 for any unknown ID. Core Python functions can run an arbitrary transaction only if pre-populated in TigerGraph and passed via script.
3. **Is the LLM genuinely involved?**
   **No.** The LLM is 100% disabled in production API (`enable_llm_synthesis=False`, `llm_client=None`) and benchmark runs. All narratives are deterministic template strings.
4. **Is MCP genuinely involved?**
   **No.** Zero MCP server or client code exists. It was explicitly forbidden in architecture tests. Tool dispatch is handled via native Python classes in `dispatcher.py`.
5. **Is TigerGraph genuinely involved?**
   **Yes.** 6 real GSQL queries execute against a live TigerGraph Cloud instance (`FraudInvestigation` graph) via RESTPP.
6. **Are graph algorithms genuinely involved?**
   **No.** Louvain, WCC, and PageRank do not exist in GSQL or backend code. They are 100% simulated as a static SVG in `GlobalGraphExplorer.tsx`.
7. **Is GraphRAG genuinely involved?**
   **No.** It is a simple dictionary lookup mapping `EvidenceType` enums to static policy chunks. No vector embeddings or graph traversal are performed.
8. **Is memory genuinely involved?**
   **Yes.** `CaseMemoryStore` loads historical cases from CSV and provides snapshot-isolated precedent retrieval without leaking benchmark ground truth.
9. **Is Evidence Compass genuinely adaptive?**
   **Yes.** In the backend, `EvidenceCompass` computes real mathematical EVOI and net decision values to rank tools dynamically. However, the frontend view displays hardcoded numbers.
10. **Is the investigation loop genuinely autonomous?**
    **Yes.** `InvestigationOrchestrator` autonomously runs an iterative loop selecting tools, gathering evidence, updating belief, and checking termination criteria.
11. **Is the NBA genuinely derived?**
    **Yes.** `PolicyEngine` derives primary and consequential actions and approval tiers from final belief state and evidence using institutional rules R1–R10.
12. **Is the frontend displaying real backend state?**
    **Partially.** The main investigation workstation (Risk Assessment, Decision Gate, Next Best Action, Key Evidence Findings, Run Trace Console, and Interactive Network Graph) displays genuine live backend state.
13. **Are any frontend results fabricated/synthesized?**
    **Yes.** Command Center KPI cards, Benchmark View baseline tables, Global Graph Explorer algorithm projections, Evidence Compass candidate tables, and Explanation SAR narrative are hardcoded or simulated.
14. **Does 20/20 represent meaningful performance?**
    **No.** First, the true live NBA accuracy was 19/20 (not 20/20). Second, the Decision Gate pass rate was only 11/20. Third, 100% of benchmark cases are fraud (zero negative controls), meaning the benchmark does not evaluate false-positive discrimination.
15. **What is the single biggest technical weakness?**
    The lack of an automated transaction ingestion and graph entity-resolution pipeline to run arbitrary unseen transactions.
16. **What is the single biggest frontend weakness?**
    The presence of fabricated static views (`GlobalGraphExplorer.tsx`, `EvidenceCompassView.tsx`) that collapse under scrutiny.
17. **What is the single biggest demo/judge weakness?**
    Overstating capabilities (claiming "MCP Tools: 50+ loaded", "100% Action Accuracy", "Louvain/PageRank") that do not exist in code, which invites disqualification upon inspection.
18. **What is Tark's strongest genuine technical differentiator?**
    The combination of **live TigerGraph multi-hop queries** with a **mathematically rigorous Bayesian Belief Engine** and a **Decision-Theoretic EVOI planner**. Almost no hackathon project implements real EVOI math.
19. **What currently makes Tark look like a normal AI application?**
    Cosmetic KPI cards, buzzword labels ("MCP", "GraphRAG", "Agentic"), and static cards that look like generic AI dashboard templates.
20. **What must be fixed before submission?**
    Remove all fictional claims (MCP, simulated graph algorithms), wire the frontend views (`EvidenceCompassView`, `ExplanationSarView`) to live backend payloads, and present Tark honestly as a **Mathematically Grounded Decision-Theoretic Investigation Workstation**.
