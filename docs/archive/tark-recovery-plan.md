# Tark: Integrity & Agentic Recovery
## Master Engineering Plan & Forensic Reconnaissance (Phase 0)

**Author:** Antigravity (Lead Systems Architect & Forensic Auditor)  
**Date:** September 19, 2026  
**Status:** COMPLETE (Ready for Phase 1 Execution)  
**Scope:** Forensic deconstruction of current prototype and concrete blueprint for rigorous, competition-grade recovery.

---

## 1. Current Architecture (What Actually Happens Today)

The current implementation in `bench/run.py` is an imperative, procedural pipeline wrapped in heuristic decision rules, with an LLM invoked strictly as a peripheral text generator:

```
[case_pack.csv] (Row 1..20)
       │
       ▼
[bench/run.py: Ingest Trigger]
       │
       ├─► Extract risk_score ──► Hardcoded Bin Lookup (Score -> Log-LR)
       │
       ├─► Extract trigger_text ──► REGEX dollar amount
       │                          ──► Substring checks ("device", "several cards", "444.0", "264.0")
       │                          ──► Hardcoded Pattern Assignment & Hardcoded Evidence Injection
       │
       ├─► Execute TigerGraph Queries ──► customer_profile(cust_id) ──► Output IGNORED
       │                              ──► device_analysis(txn_id)  ──► Output IGNORED
       │                              ──► similar_cases(pattern)   ──► Saved for JSON display only
       │
       ▼
[src/belief/engine.py] ──► Sum of Log-LRs + 83.8% Prior ──► Posterior Probability
       │
       ▼
[src/policy/engine.py] ──► Rule Table (R1..R10) ──► Initial Actions (Auto, L1, L2)
       │
       ▼
[src/planner/decision_flip.py] ──► Test: Does hypothetical Customer Confirmation flip action?
       │                         ──► Yes: Request customer verification (Simulated)
       │                         ──► Update belief & re-evaluate policy
       ▼
[src/tools/llm_client.py] ──► If FILE_REPORT in actions: Merge Gateway DeepSeek V4 Flash drafts SAR Narrative
       │
       ▼
[cases/HHG-xxx.json] ──► Serialized to disk & Upserted to TigerGraph as InvestigationCase
```

### Reality Breakdown:
- **Graph Participation:** Decorative. Queries are executed across network to Savanna Cloud, but their return values are completely discarded.
- **Reasoning Engine:** Pure Python heuristics parsing strings out of `trigger_text`.
- **LLM Participation:** Exclusively markdown text formatting for SAR narratives. Zero tool selection, zero hypothesis formation, zero investigation planning.

---

## 2. Official Task Requirements vs. Implementation Reality

| Official Task Requirement (HHGOA Task 4) | Status in Current Tark | Forensic Evidence & Reality |
|---|---|---|
| **1. Trigger Intake** (model score, report, analyst) | **PARTIALLY IMPLEMENTED** | Parses trigger type and score, but relies on regex substring matching rather than entity resolution. |
| **2. Connected Graph Evidence** | **INCORRECT / FAKE** | Graph schema exists, but `Transaction` and `DeviceProfile` tables have **0 vertices**. Queries return empty structures. |
| **3. Risk & Pattern Identification** | **INCORRECT** | Inferred via substring searches in `trigger_text` rather than graph topology. |
| **4. Case Creation & Graph Memory Write** | **IMPLEMENTED** | `InvestigationCase` vertices and edges are written back to TigerGraph Savanna in real time. |
| **5. Case Memory Informs Investigation** | **FAKE / COSMETIC** | `similar_cases` retrieves 5 records matching pattern enum, but results never enter the belief engine or affect decisions. |
| **6. Evidence Gathering Under Policy** | **PARTIALLY IMPLEMENTED** | Simulates customer verification and step-up auth, but only along hardcoded paths. |
| **7. Next Best Action & Routing** | **IMPLEMENTED** | Actions and approval routes (`auto`, `L1`, `L2`) strictly adhere to policy thresholds. |
| **8. Policy Compliance (R1–R10)** | **IMPLEMENTED** | All 10 rules are explicitly modeled in `PolicyEngine`. |
| **9. Defensible Stopping Condition** | **PARTIALLY IMPLEMENTED** | Stops after single Evidence Compass check; lacks multi-turn uncertainty loop. |
| **10. Explainability & SAR Narrative** | **IMPLEMENTED** | DeepSeek V4 Flash generates compliant FinCEN narrative with What-Changed reasoning. |
| **11. TigerGraph MCP Integration** | **NOT IMPLEMENTED** | Mentions exist in README/plan, but zero MCP code exists. Uses raw `pyTigerGraph`. |
| **12. GraphRAG Grounding** | **NOT IMPLEMENTED** | No vector store, no embeddings, no document retrieval. Regulatory PDFs sit unindexed on disk. |
| **13. Agentic Design & Engineering** | **INCORRECT** | A deterministic Python script is labeled an "Agent". No state machine, no ReAct loop. |

---

## 3. Detailed Audit Findings & Code Verification

### Finding A: Blatant Hardcoding in `bench/run.py`
In [`bench/run.py:112-152`](file:///c:/Users/Mukul/Desktop/Tark/bench/run.py#L112-L152):
```python
if "device" in trigger_text.lower():
    if "several cards" in trigger_text.lower() or case_id == "HHG-014":
        pattern = "account_takeover"
        ledger.add(EvidenceItem(
            evidence_type=EvidenceType.SHARED_DEVICE_RING,
            ...
        ))
        connected_cards = ["C13487-K1", "C09214-K2"]
elif "billing region" in trigger_text.lower():
    if "444.0" in trigger_text or "264.0" in trigger_text:
        pattern = "out_of_region_use"
    else:
        pattern = "none"
        ledger.add(EvidenceItem(
            evidence_type=EvidenceType.CUSTOMER_CONFIRMATION,
            ...
        ))
```
- **Proof:** `case_id == "HHG-014"` is directly checked in code.
- **Proof:** String checking for `"444.0"` (HHG-001) and `"264.0"` (HHG-007) forces `out_of_region_use`.
- **Proof:** The `else` branch directly injects `CUSTOMER_CONFIRMATION` for HHG-012 to force it to `legitimate`.

### Finding B: TigerGraph Data Void
Live query against active Savanna Cloud database (`https://tg-3242c55c...`):
- `Customer`: 20 vertices
- `Card`: 20 vertices
- `ClosedCase`: 5,565 vertices
- `InvestigationCase`: 20 vertices
- `Transaction`: **0 vertices**
- `DeviceProfile`: **0 vertices**
- `EmailDomain`: **0 vertices**
- `BillingRegion`: **0 vertices**

**Proof:**
```python
conn.runInstalledQuery("customer_profile", {"cust_id": "C12382"})
# Output: [{'total_txns': 0, 'total_amount': 0, 'avg_amount': 0, ...}]

conn.runInstalledQuery("device_analysis", {"t_id": "3514030"})
# Output: [{'device_id': '', 'device_info': '', 'shared_card_count': 0, ...}]
```

### Finding C: Case Memory Disconnect
In `bench/run.py:155-163`:
`similar_cases` is queried and saved to `similar_cases_res`. It is passed into `answer_data["case"]["similar_prior_cases"]` on line 310, but **never** passed into `BeliefEngine`. It has zero mathematical impact on the verdict or actions.

### Finding D: Fake Agent & Fake MCP
- `requirements.txt` installs `langgraph` and `langchain-core`, but they are never imported in `bench/run.py`.
- No stdio or SSE MCP server/client is configured.

---

## 4. Dependency Map

```
Input Sources
  ├── case_pack.csv (20 Benchmark Alerts)
  ├── closed_cases_history.csv (5,565 Historical Records)
  ├── transactions.csv (590k raw rows - UNLOADED)
  └── identity.csv (144k raw rows - UNLOADED)
        │
        ▼
Data Ingestion (etl/load_data.py)
  ├── ClosedCase vertices (Loaded)
  ├── Customer & Card vertices (Loaded)
  └── Transaction & Device vertices (MISSING)
        │
        ▼
TigerGraph Savanna Cloud (FraudInvestigation)
  ├── Schema: 8 Vertices, 11 Edges
  └── 6 GSQL Queries: customer_profile, txn_velocity, device_analysis,
                      card_sequence, region_analysis, similar_cases
        │
        ▼
Execution Pipeline (bench/run.py)
  ├── Query Invocations (Outputs Discarded)
  ├── Trigger Text Regex & Hardcoded Mappings
  ├── Belief Engine (Log-odds update with family damping)
  ├── Decision-Flip Heuristic (One-sided confirmation check)
  ├── Policy Engine (Rules R1-R10, Auto/L1/L2 routing)
  └── LLM Client (DeepSeek V4 Flash SAR Narrative Generation)
        │
        ▼
Deliverables
  ├── cases/HHG-001.json ... HHG-020.json
  ├── TigerGraph InvestigationCase Write-back
  └── FastAPI Dashboard (http://localhost:8000)
```

---

## 5. Data Flow & Ingestion Bottleneck

### Current Reality:
1. `etl/load_data.py` only loaded `closed_cases_history.csv` and the 20 lines of `case_pack.csv`.
2. `transactions.csv` is 708 MB and `identity.csv` is 26 MB. The developer avoided ingesting them because bulk loading 590k rows over the cloud API without a TigerGraph loading job was perceived as too slow.
3. Because the graph had no transactions, the runner had to fabricate findings by scraping the `trigger_text`.

### Required Target Data Flow:
We do not need all 590k rows for the 20 benchmark cases. We need:
1. All transactions belonging to the 20 benchmark customers and cards.
2. All transactions associated with the 5,565 closed cases.
3. The device profiles linked to those transactions from `identity.csv`.
4. Any connected cards sharing those device profiles (fraud rings).
*Total slice size:* ~15,000 to 25,000 transactions. This can be ingested in under 60 seconds over pyTigerGraph upsert, completely populating the graph for every query!

---

## 6. Trust Boundaries

```
[EXTERNAL BENCHMARK (Untrusted/Target)]
  - case_pack.csv (Trigger alert only; no labels)
        │
        ▼ (Trust Boundary 1)
[GROUND TRUTH / MEMORY (High Trust)]
  - closed_cases_history.csv (Confirmed outcomes & historical analyst notes)
  - transactions.csv (Verified raw ledger records)
  - identity.csv (Verified device and connection telemetry)
        │
        ▼ (Trust Boundary 2)
[TIGERGRAPH CLOUD (System of Record)]
  - Graph Topology (Card -> MADE -> Transaction -> FROM_DEVICE -> DeviceProfile)
  - GSQL Algorithmic Queries (Velocity, Rings, Sequences, Anomaly)
        │
        ▼ (Trust Boundary 3)
[REASONING & EVIDENCE LAYER]
  - Evidence Ledger (Item, Provenance, Likelihood Ratio, Exculpatory Flag)
  - Belief Engine (Bayesian Log-Odds, Family Damping, Calibrated Probability)
  - Evidence Compass (Candidate Evaluation, Decision-Flip Matrix)
        │
        ▼ (Trust Boundary 4)
[GOVERNANCE & ACTION LAYER]
  - Policy Matrix (Strict R1–R10 Execution, Approval Routing Guardrails)
        │
        ▼ (Trust Boundary 5)
[SYNTHESIS & REPORTING (LLM)]
  - DeepSeek V4 Flash (Grounded SAR Narrative, What-Changed Explanations)
```

---

## 7. Hardcoding Audit (Full Repository Grep)

| File | Line | Code Snippet | Verdict |
|---|---|---|---|
| `bench/run.py` | 113 | `if "several cards" in trigger_text.lower() or case_id == "HHG-014":` | **CRITICAL:** Case-specific branch. |
| `bench/run.py` | 122 | `connected_cards = ["C13487-K1", "C09214-K2"]` | **CRITICAL:** Hardcoded entity IDs. |
| `bench/run.py` | 134 | `if "444.0" in trigger_text or "264.0" in trigger_text:` | **CRITICAL:** Value-engineered trigger parsing. |
| `bench/run.py` | 144 | `pattern = "none"` | **CRITICAL:** Forcing HHG-012 to legitimate. |
| `bench/run.py` | 146 | `ledger.add(EvidenceItem(evidence_type=EvidenceType.CUSTOMER_CONFIRMATION...))` | **CRITICAL:** Fabricating customer confirmation. |
| `bench/run.py` | 163 | `similar_cases_res = ["CC-0001", "CC-0007"]` | **HIGH:** Hardcoded fallback cases. |
| `src/planner/decision_flip.py` | 41 | `if case_context.get("trigger_type") == "customer_report": return EvidenceRequestDecision(should_request=False...)` | **MEDIUM:** Shortcut heuristic. |
| `src/belief/engine.py` | 22 | `"p_fraud": 0.8383` | **MEDIUM:** Unconditional analyst alert prior applied to raw cases. |

---

## 8. Runtime Verification of Real Capabilities

We executed live runtime tests against all components without code modification:
1. **TigerGraph Connectivity:**
   - Host: `https://tg-3242c55c...` -> Ping: `Hello GSQL` (200 OK).
   - Secret auth: Token generation succeeded.
   - Graph `FraudInvestigation` active.
2. **GSQL Compilation:**
   - All 6 queries (`customer_profile`, `txn_velocity`, `device_analysis`, `card_sequence`, `region_analysis`, `similar_cases`) compiled and installed (succeeded: 6, failed: 0).
3. **Merge Gateway DeepSeek V4 Flash:**
   - Endpoint `https://api-gateway.merge.dev/v1/chat/completions` authenticated.
   - Text generation with reasoning budget (1200+ tokens) returns valid FinCEN SAR narratives.
4. **Bayesian Math & Policy Engine:**
   - Test suite in `scratch/test_core_engines.py` verified log-odds aggregation, sigmoid conversion, and approval level transitions (`auto` -> `L1` -> `L2`).
5. **Web Console:**
   - FastAPI server (`src/api/main.py`) running on `127.0.0.1:8000`, serving JSON endpoints and dashboard.

---

## 9. Proposed Target Architecture

The target architecture is the smallest, cleanest system that satisfies every requirement **honestly**:

```
                  ┌───────────────────────────────┐
                  │ Trigger Event (Case Pack / CSV)│
                  └──────────────┬────────────────┘
                                 ▼
                  ┌───────────────────────────────┐
                  │ 1. Graph Investigation Engine │
                  │  - GSQL: Customer Baseline    │
                  │  - GSQL: Card Txn Velocity    │
                  │  - GSQL: Device Blast Radius  │
                  │  - GSQL: Card Testing Sequence│
                  │  - GSQL: Region Anomaly Check │
                  └──────────────┬────────────────┘
                                 │ Real Graph Outputs
                                 ▼
                  ┌───────────────────────────────┐
                  │ 2. Evidence Extractor & Ledger│
                  │  - Quantifies findings as LRs │
                  │  - Cites exact graph source   │
                  │  - Flags exculpatory evidence │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ 3. Case Memory Grounding      │
                  │  - GSQL: Retrieve Past Cases  │
                  │  - Extracts historical outcome│
                  │  - Precedent Likelihood Shift │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ 4. Bayesian Belief Engine     │
                  │  - Dynamic trigger prior      │
                  │  - Log-odds summation        │
                  │  - Calibrated posterior P(F)  │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ 5. Policy Matrix (R1 – R10)   │
                  │  - Current Recommended Action │
                  │  - Strict Approval (Auto/L1/L2│
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ 6. Multi-Outcome Compass      │
                  │  - Evaluates candidate probes │
                  │  - Multi-outcome state shift  │
                  │  - Declines or commits probe  │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ 7. Synthesis & Reporting (LLM)│
                  │  - DeepSeek V4 Flash          │
                  │  - FinCEN Compliant SAR       │
                  │  - What-Changed Audit Trail   │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ 8. Graph Write-back & Storage │
                  │  - InvestigationCase in Graph │
                  │  - 20 Answer JSON Files       │
                  └───────────────────────────────┘
```

---

## 10. Ordered Implementation Phases

```
Phase 0: Forensic Reconnaissance (Current - Complete)
   │
   ▼
Phase 1: Benchmark Integrity
   - Purge all hardcoded case IDs and string shortcuts from bench/run.py
   - Ensure generic, uniform reasoning for all cases
   - Add regression tests proving zero case-specific branches
   │
   ▼
Phase 2: Real TigerGraph Ingestion & Query Wiring
   - Ingest real transactions and device profiles for all benchmark entities
   - Wire actual GSQL query outputs directly into the Evidence Ledger
   - Verify non-empty, live graph returns for customer_profile, device_analysis, etc.
   │
   ▼
Phase 3: Evidence & Belief Engine Hardening
   - Calibrate base priors by trigger type (customer_report vs risk_score)
   - Audit and document every Likelihood Ratio mathematically
   - Independent verification tests for numerical reproducibility
   │
   ▼
Phase 4: Multi-Outcome Evidence Compass
   - Extend Decision-Flip planner to evaluate multiple candidate evidence probes
   - Calculate expected decision shift across both confirmation and denial outcomes
   - Explicit stopping condition when information value is below cost/delay threshold
   │
   ▼
Phase 5: Adaptive Agentic State Machine
   - Implement LangGraph / stateful investigation controller
   - Dynamic query execution based on intermediate uncertainty
   - Ensure different cases take different investigation paths based on graph findings
   │
   ▼
Phase 6: Material Case Memory & Policy Grounding
   - Incorporate similar closed case outcomes into the belief update
   - Ground decisions against regulatory and policy references
   │
   ▼
Phase 7: TigerGraph MCP Integration
   - Connect and expose graph tools via TigerGraph MCP interface
   - Validate live tool invocation trace
   │
   ▼
Phase 8: Comprehensive Adversarial Evaluation
   - 10+ adversarial test cases (conflicting evidence, borderlines, spoofed signals)
   - Baseline comparison tables (Rules only vs Graph vs Tark)
   │
   ▼
Phase 9: Final Competition Audit
   - Hostile judge inspection and documentation review
```

---

## 11. Reassessment of Score against Judging Rubric

| Rubric Criterion | Weight | Previous Audit | Independent Forensic Reassessment | Justification |
|---|---|---|---|---|
| **Investigation Accuracy** | 25% | 18 / 25 | **14 / 25** | High nominal accuracy was achieved via string heuristics and hardcoded branches in `bench/run.py`. Graph was unpopulated with transactions. |
| **Next Best Action** | 25% | 24 / 25 | **22 / 25** | The Policy Matrix (R1–R10) and approval routes (`auto`, `L1`, `L2`) are correctly implemented, but currently driven by heuristic inputs. |
| **Case Summary & Explainability** | 10% | 9 / 10 | **8 / 10** | DeepSeek V4 Flash generates strong SAR narratives, but citations refer to unverified graph features. |
| **Agentic Design & Engineering** | 15% | 7 / 15 | **4 / 15** | Pipeline is linear Python code. LangGraph is in `requirements.txt` but unused. Zero autonomous tool selection. |
| **Innovation (Evidence Compass)** | 15% | 11 / 15 | **7 / 15** | The concept is strong, but the current code only tests a single hardcoded confirmation outcome. |
| **Demo Quality & UI** | 10% | 10 / 10 | **9 / 10** | Web console is responsive and visually clear, but displays static data that didn't emerge from graph analytics. |
| **TOTAL** | 100% | **79 / 100** | **64 / 100** | **A hostile judge will immediately spot the hardcoding and unpopulated graph, dropping the project into the below-passing tier.** |

---

## 12. Immediate Next Step: Phase 1 (Benchmark Integrity)

With Phase 0 complete, our immediate mandate is **Phase 1: Benchmark Integrity**:
1. **Remove every hardcoded benchmark check** in [`bench/run.py`](file:///c:/Users/Mukul/Desktop/Tark/bench/run.py):
   - Remove `case_id == "HHG-014"`
   - Remove `"444.0" in trigger_text or "264.0" in trigger_text`
   - Remove hardcoded `connected_cards = ["C13487-K1", "C09214-K2"]`
   - Remove hardcoded injection of `CUSTOMER_CONFIRMATION` for HHG-012
2. **Build a generic feature extractor** that evaluates trigger properties uniformly for any arbitrary case ID.
3. **Add automated regression tests** in `tests/test_integrity.py` asserting that zero case IDs or trigger string constants exist in the reasoning paths.

Awaiting user confirmation to execute Phase 1.
