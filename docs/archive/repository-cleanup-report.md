# Tark Phase 4.1.5: Repository Forensic Cleanup & Git Preparation Report

**Phase:** Phase 4.1.5 (Forensic Cleanup & Git History Preparation)  
**System:** Tark Repository Infrastructure & Audit Gate  
**Status:** Audit Completed; Cleanup Verified; Awaiting User Approval Before Git Commits  
**Baseline Tests:** 46 passed (100%)  
**Final Tests:** 46 passed (100%)  

---

## 1. Executive Summary

As Tark transitioned through rapid development from Phase 0 to Phase 4.1, the workspace accumulated temporary files, bytecode caches, missing package initializers, and untracked artifacts. In accordance with Phase 4.1.5 instructions, a comprehensive forensic inventory of all 78 repository files was conducted.

- **No architecture was redesigned.**
- **No working code or tests were broken.**
- **No benchmark data or GSQL queries were altered.**
- **Baseline test suite remained 100% green (46 / 46 passed).**
- **All git commits are held in a staged proposal awaiting user approval.**

---

## 2. Complete File Classification Table

Every file in the repository has been evaluated against the 12 Phase 1 forensic classifications:

| File Path | Classification | Role / Dependency Analysis |
| :--- | :--- | :--- |
| `.env` | `CONFIG_CURRENT` | Local environment credentials for TigerGraph and LLM gateway. Excluded by `.gitignore`. |
| `.env.example` | `CONFIG_CURRENT` | Sanitized configuration template for public cloning. |
| `.gitignore` | `CONFIG_CURRENT` | Repository ignore rules (extended in this phase to cover `.pytest_cache/` and test logs). |
| `requirements.txt` | `CONFIG_CURRENT` | Core Python dependencies (pydantic, pyTigerGraph, fastapi, pytest, etc.). |
| `README.md` | `DOC_CURRENT` | Official IEEE-CIS dataset specifications, Task 4 rules, and R1–R10 policy definitions. |
| `HHGoa26_Selection_Criteria.pdf` | `DOC_CURRENT` | Official Hacker House Goa selection criteria PDF. |
| `TigerGraph Agentic Fraud Investigation HHGOA.pdf` | `DOC_CURRENT` | Official Task 4 problem statement and constraints PDF. |
| `transactions.csv` | `DATA_CURRENT` | 590,742 raw transactions (708 MB); local source data loaded into TigerGraph. Excluded by `.gitignore`. |
| `identity.csv` | `DATA_CURRENT` | 144,432 digital device identity records; source data. Excluded by `.gitignore`. |
| `closed_cases_history.csv` | `DATA_CURRENT` | 5,565 historical closed investigations; source data. Excluded by `.gitignore`. |
| `case_pack.csv` | `DATA_CURRENT` | 20 exam benchmark alert triggers; source data. Excluded by `.gitignore`. |
| `implementphase&plan` | `EXPERIMENTAL_UNUSED` | Early unformatted hackathon notes; replaced by `docs/tark-recovery-plan.md`. **Removed**. |
| `analysis/estimate_lrs.py` | `CORE_CURRENT` | Empirical likelihood ratio calibration script derived from IEEE-CIS data. |
| `analysis/lr_table.json` | `DATA_CURRENT` | Calibrated empirical log-LR lookup table loaded by `BeliefEngine`. |
| `bench/run.py` | `CORE_CURRENT` / `PHASE_FUTURE` | Benchmark case runner executing 20 exam cases; preserves case memory. |
| `cases/HHG-001.json` ... `HHG-020.json` (20 files) | `TEST_CURRENT` / `DATA_CURRENT` | Canonical case answer records; verified by `tests/test_submission.py`. |
| `docs/architecture.md` | `DOC_CURRENT` | Canonical system boundary locked during Phase 2.5. |
| `docs/evidence-scoring.md` | `DOC_CURRENT` | Mathematical formulation of evidence scoring and Bayes factors. |
| `docs/image.png` | `HISTORICAL` / `DOC_CURRENT` | Savanna cluster commit audit screenshot embedded in Phase 2 report. |
| `docs/phase2-reconciliation-report.md` | `HISTORICAL` | Forensic reconciliation of TigerGraph data lineage. |
| `docs/phase2.5-report.md` | `HISTORICAL` | Architectural hardening audit report. |
| `docs/phase3-reasoning.md` | `DOC_CURRENT` | Phase 3 probabilistic reasoning specification. |
| `docs/phase3.1-report.md` | `HISTORICAL` | Phase 3.1 decision semantics audit report. |
| `docs/phase3.2-evidence-compass-design.md` | `DOC_CURRENT` | Phase 3.2 Evidence Compass EVOI specification and worked example. |
| `docs/phase4.1-evoi-implementation-report.md` | `DOC_CURRENT` | Phase 4.1 EVOI implementation verification report. |
| `docs/reasoning-model.md` | `DOC_CURRENT` | Mathematical specification of belief engine. |
| `docs/roadmap.md` | `DOC_CURRENT` | Phase roadmap and milestone tracker. |
| `docs/tark-recovery-plan.md` | `DOC_CURRENT` | Master engineering recovery and audit plan. |
| `etl/load_data.py` | `CORE_CURRENT` | TigerGraph batch ingest pipeline with digital device fingerprinting. |
| `queries/card_sequence.gsql` | `CORE_CURRENT` | GSQL query: micro-auth testing sequence detection. |
| `queries/customer_profile.gsql` | `CORE_CURRENT` | GSQL query: customer baseline spending profile. |
| `queries/device_analysis.gsql` | `CORE_CURRENT` | GSQL query: multi-card shared device ring detection. |
| `queries/region_analysis.gsql` | `CORE_CURRENT` | GSQL query: billing region geographic anomaly detection. |
| `queries/similar_cases.gsql` | `CORE_CURRENT` | GSQL query: precedent closed-case retrieval. |
| `queries/txn_velocity.gsql` | `CORE_CURRENT` | GSQL query: 24h card velocity aggregation. |
| `schema/schema.gsql` | `CORE_CURRENT` | TigerGraph vertex, edge, and graph schema definition. |
| `src/__init__.py` | `CORE_CURRENT` | Package root initializer (**Created**). |
| `src/agent/__init__.py` | `CORE_CURRENT` | Agent package initializer (**Created**). |
| `src/agent/prompts/__init__.py` | `CORE_CURRENT` | Prompts package initializer (**Created**). |
| `src/agent/prompts/system.py` | `PHASE_FUTURE` / `CORE_CURRENT` | System and SAR prompt templates; imported by `bench/run.py`. |
| `src/api/__init__.py` | `CORE_CURRENT` | API package initializer (**Created**). |
| `src/api/main.py` | `PHASE_FUTURE` | FastAPI case console and dashboard server. |
| `src/belief/__init__.py` | `CORE_CURRENT` | Belief package initializer (**Created**). |
| `src/belief/calibration.py` | `CORE_CURRENT` | Prior profiles and evidence family correlation definitions. |
| `src/belief/engine.py` | `CORE_CURRENT` | Probabilistic belief engine with Decision Gate contract. |
| `src/belief/state.py` | `CORE_CURRENT` | InvestigationState and hypothesis models. |
| `src/compass/__init__.py` | `CORE_CURRENT` | Evidence Compass package export. |
| `src/compass/evoi.py` | `CORE_CURRENT` | Deterministic EVOI calculation engine and loss matrix. |
| `src/evidence/__init__.py` | `CORE_CURRENT` | Evidence package initializer (**Created**). |
| `src/evidence/ledger.py` | `CORE_CURRENT` | Evidence ledger container and provenance tracking. |
| `src/evidence/types.py` | `CORE_CURRENT` | EvidenceType enum and EvidenceItem contract. |
| `src/graph/__init__.py` | `CORE_CURRENT` | Graph package initializer (**Created**). |
| `src/graph/scope.py` | `CORE_CURRENT` | Temporal and entity graph scope validation guards. |
| `src/planner/__init__.py` | `CORE_CURRENT` | Planner package initializer (**Created**). |
| `src/planner/decision_flip.py` | `CORE_CURRENT` | Legacy decision flip planner; imported by tests and `bench/run.py`. |
| `src/policy/__init__.py` | `CORE_CURRENT` | Policy package initializer (**Created**). |
| `src/policy/engine.py` | `CORE_CURRENT` | Policy rules engine (R1–R10) and SAR threshold logic. |
| `src/policy/rules.yaml` | `CORE_CURRENT` | Policy rules definition in YAML. |
| `src/tools/__init__.py` | `CORE_CURRENT` | Tools package initializer (**Created**). |
| `src/tools/llm_client.py` | `PHASE_FUTURE` / `CORE_CURRENT` | Merge Gateway LLM client with regulatory fallback; imported by tests and `bench/run.py`. |
| `src/tools/mock_actions.py` | `CORE_CURRENT` | Independent webhook simulators for disputes and MFA. |
| `tests/test_adversarial_phase2.py` | `TEST_CURRENT` | 10 adversarial data lineage tests. |
| `tests/test_architecture_hardening.py` | `TEST_CURRENT` | 5 architecture boundary tests. |
| `tests/test_evidence_compass.py` | `TEST_CURRENT` | 8 Evidence Compass EVOI calculation tests. |
| `tests/test_integrity.py` | `TEST_CURRENT` | 2 benchmark anti-hardcoding tests. |
| `tests/test_reasoning_phase3.py` | `TEST_CURRENT` | 13 probabilistic belief and Decision Gate tests. |
| `tests/test_submission.py` | `TEST_CURRENT` | 2 case answer schema tests. |
| `tests/test_tigergraph_evidence.py` | `TEST_CURRENT` | 6 live TigerGraph GSQL query tests. |
| `web/index.html` | `PHASE_FUTURE` | Single-page HTML/CSS investigation console dashboard. |

---

## 3. Files Removed

| Path | Classification | Reason for Deletion | Proof of Redundancy |
| :--- | :--- | :--- | :--- |
| `implementphase&plan` | `EXPERIMENTAL_UNUSED` | Informal, unformatted scratchpad text file from kickoff. | Content superseded by `docs/tark-recovery-plan.md` and `docs/roadmap.md`. Zero import or test references. |
| `*__pycache__/*` | `GENERATED_ARTIFACT` | Compiled Python bytecode (`.pyc`). | Regenerated automatically; covered by `.gitignore`. |
| `.pytest_cache/*` | `GENERATED_ARTIFACT` | Local pytest state and cache. | Test runner artifact; added to `.gitignore`. |

---

## 4. Duplicate Architecture Analysis

| Subsystem | Implementations Discovered | Canonical File | Status & Handling |
| :--- | :--- | :--- | :--- |
| **Evidence Selection** | 1. `src/planner/decision_flip.py` (naive 1-sided heuristic)<br>2. `src/compass/evoi.py` (deterministic EVOI) | `src/compass/evoi.py` | **Retained both.** `decision_flip.py` is actively imported by Phase 2/3 test suites (`test_integrity.py`, `test_adversarial_phase2.py`, `test_architecture_hardening.py`) and `bench/run.py`. Removing it now would break passing tests. It will be gracefully deprecated in Phase 4.2 when the orchestrator wires `EvidenceCompass` into the execution loop. |
| **Belief Engine** | `src/belief/engine.py` | `src/belief/engine.py` | Single implementation. Zero duplicates. |
| **Decision Gate** | `src/belief/engine.py` (lines 416–470) | `src/belief/engine.py` | Single implementation. Zero duplicates. |
| **Evidence Contracts** | `src/evidence/types.py`, `src/evidence/ledger.py` | `src/evidence/` | Single implementation. Zero duplicates. |
| **Policy Engine** | `src/policy/engine.py`, `src/policy/rules.yaml` | `src/policy/` | Single implementation. Zero duplicates. |
| **GSQL Queries** | `queries/*.gsql` | `queries/` | Single implementation. Zero duplicates. |

---

## 5. Modifications to `.gitignore`

Added standard testing and coverage patterns to prevent future working directory pollution:
```gitignore
# Testing & Quality
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
*.log
```

---

## 6. Verification & Test Stability

- **Baseline Pre-Cleanup:** 46 passed in 3.25s
- **Post-Cleanup Full Suite:** 46 passed in 3.61s
- **Zero regressions observed across all 7 test suites.**

```
tests/test_adversarial_phase2.py ..........                              [ 21%]
tests/test_architecture_hardening.py .....                               [ 32%]
tests/test_evidence_compass.py ........                                  [ 50%]
tests/test_integrity.py ..                                               [ 54%]
tests/test_reasoning_phase3.py .............                             [ 82%]
tests/test_submission.py ..                                              [ 86%]
tests/test_tigergraph_evidence.py ......                                 [100%]
======================= 46 passed, 19 warnings in 3.61s =======================
```

---

## 7. Proposed Atomic Commit Progression (46 Commits)

To establish a clear, defensible, chronological Git progression on GitHub, the following 46-commit plan is prepared:

### Family 1: FOUNDATION & CONFIGURATION (Commits 1–4)
1. `chore: initialize repository with .gitignore and dependency manifest`
2. `docs: add official problem specification and evaluation criteria PDFs`
3. `docs: add dataset specifications and task readme`
4. `config: add environment variable configuration templates`

### Family 2: DATA & GRAPH ENGINE (Commits 5–13)
5. `schema: define TigerGraph vertex and edge schema for fraud graph`
6. `queries: implement card testing sequence detection query in GSQL`
7. `queries: implement customer historical spending baseline query`
8. `queries: implement shared device ring clustering query`
9. `queries: implement billing region historical precedent query`
10. `queries: implement 24h card transaction velocity query`
11. `queries: implement precedent closed case retrieval query`
12. `etl: implement TigerGraph data loading pipeline with device fingerprinting`
13. `tests: add TigerGraph live query integration test suite`

### Family 3: EVIDENCE CONTRACTS & SCOPE (Commits 14–18)
14. `evidence: define core evidence types and evidence item contracts`
15. `evidence: implement immutable evidence ledger with provenance tracking`
16. `graph: implement temporal and entity scope validation guards`
17. `analysis: add empirical likelihood ratio estimation engine`
18. `analysis: export calibrated likelihood ratio lookup table`

### Family 4: BELIEF, UNCERTAINTY & DECISION GATE (Commits 19–29)
19. `belief: define world hypothesis and uncertainty state models`
20. `belief: establish prior registry and family ceiling calibrations`
21. `belief: implement core belief update engine with log-odds formulation`
22. `belief: implement semantic evidence family correlation discounting`
23. `belief: add inculpatory and exculpatory contradiction tracking`
24. `belief: implement safe zero-shift semantics for out-of-scope queries`
25. `belief: add neutral absence handling for query pattern no-match`
26. `policy: define regulatory policy rules R1-R10 configuration`
27. `policy: implement policy engine evaluating actions and SAR triggers`
28. `belief: implement deterministic multi-gate Decision Gate contract`
29. `tests: add phase 3 belief and uncertainty reasoning test suite`

### Family 5: REGRESSION & INTEGRITY TESTS (Commits 30–32)
30. `tests: add adversarial data integrity and provenance verification suite`
31. `tests: add architectural boundary and contract hardening tests`
32. `tests: add benchmark integrity and anti-hardcoding tests`

### Family 6: DECISION HEURISTICS & BENCHMARK SUITE (Commits 33–39)
33. `planner: add baseline decision flip heuristic with action simulation`
34. `tools: add simulated cardholder dispute and step-up auth fixtures`
35. `tools: add Merge Gateway DeepSeek client wrapper with fallback`
36. `agent: add system and regulatory SAR prompt templates`
37. `bench: add 20-case benchmark investigation runner`
38. `cases: add initial 20 benchmark case deliverables`
39. `tests: add submission format and schema verification tests`

### Family 7: EVIDENCE COMPASS EVOI ENGINE (Commits 40–44)
40. `compass: define Evidence Compass models and action space`
41. `compass: implement operational expected loss payoff matrix`
42. `compass: implement EVOI outcome likelihood and posterior projection`
43. `compass: implement Evidence Compass EVOI calculation engine`
44. `tests: add Evidence Compass EVOI test suite with worked example`

### Family 8: CONSOLE & DOCUMENTATION AUDIT (Commits 45–46)
45. `api: add FastAPI console backend and static frontend dashboard`
46. `docs: add comprehensive architectural specifications, audits, and cleanup reports`
