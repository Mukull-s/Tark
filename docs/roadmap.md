# Tark: Canonical Engineering Roadmap
## Hacker House Goa 2026 — Task 4: TigerGraph Agentic Fraud Investigation

**Project:** Tark (Integrity, Agentic Decisioning & Graph Forensics)  
**Governance:** Strict Phased Execution with Verification Gates  
**Status:** Phase 2.5 (Architecture Hardening Gate)  

---

## Canonical Phase Breakdown

```
[Phase 0: Forensic Audit] ─────────► [Phase 1: Benchmark Integrity]
         │ (DONE)                                     │ (DONE)
         ▼                                            ▼
[Phase 2: Real TigerGraph Investigation] ──► [Phase 2.5: Architecture Hardening]
         │ (DONE)                                     │ (CURRENT GATE)
         ▼                                            ▼
[Phase 3: Evidence & Belief Reasoning] ─────► [Phase 4: Evidence Compass & EVOI]
         │ (UPCOMING)                                 │
         ▼                                            ▼
[Phase 5: Real Agentic Loop] ──────────────► [Phase 6: Case Memory & GraphRAG]
         │                                            │
         ▼                                            ▼
[Phase 7: TigerGraph MCP] ─────────────────► [Phase 8: Adversarial Evaluation]
         │                                            │
         ▼                                            ▼
[Phase 9: Final Hostile Audit & Demo] ──────► [Official Submission]
```

---

### Phase Details & Acceptance Criteria

| Phase | Phase Name | Status | Key Deliverables & Hard Boundaries |
|---|---|---|---|
| **Phase 0** | Forensic Audit | **DONE** | Deconstruct existing prototype; identify trust boundaries; establish recovery blueprint in `docs/tark-recovery-plan.md`. |
| **Phase 1** | Benchmark Integrity | **DONE** | Remove benchmark-specific branches (`case_id == "HHG-..."`), hardcoded cards, and fabricated confirmation. Implement static code inspection test (`test_integrity.py`). |
| **Phase 2** | Real TigerGraph Investigation | **DONE** | Ingest real transactions (26,754), device profiles (1,835), and closed cases (5,565). Verify live GSQL queries directly populate `EvidenceLedger` with real provenance. |
| **Phase 2.5** | Architecture Hardening Gate | **ACTIVE GATE** | Lock canonical architecture in `docs/architecture.md`; implement `GraphScope` contract; harden `EvidenceItem` contract; catalog scoring LRs in `docs/evidence-scoring.md`; lock roadmap in `docs/roadmap.md`. |
| **Phase 3** | Evidence & Belief Reasoning Hardening | *Upcoming* | Mathematically ground Bayesian log-odds update; verify family damping; recalibrate empirical likelihood ratios; eliminate hardcoded LR lookups. |
| **Phase 4** | Evidence Compass & Decision Value | *Upcoming* | Formalize Expected Value of Information (EVOI) and decision-flip boundary; select optimal evidence-gathering interventions; preserve customer simulator independence. |
| **Phase 5** | Real Agentic Investigation Loop | *Upcoming* | Implement dynamic agent loop (ReAct / autonomous tool orchestration); enable multi-turn hypothesis formulation, sub-query refinement, and dynamic stopping criteria. **MUST NOT BE OMITTED.** |
| **Phase 6** | Case Memory & GraphRAG | *Upcoming* | Dynamic multi-hop subgraph extraction; community detection / Louvain clustering in TigerGraph; vector/graph grounding for regulatory SAR generation. |
| **Phase 7** | TigerGraph MCP Integration | *Upcoming* | Expose TigerGraph GSQL queries, investigation tools, and case memory as standardized Model Context Protocol (MCP) servers. |
| **Phase 8** | Adversarial Evaluation & Ablation | *Upcoming* | Stress-test with corrupted records, high-volume stress, edge-case perturbations, and ablation matrices comparing with/without graph evidence. |
| **Phase 9** | Final Hostile Audit & Submission | *Upcoming* | Independent peer-review audit; defense against hostile judging criteria; live end-to-end demo execution; documentation finalization. |

---

## Strict Development Invariants

1. **No Out-of-Order Execution:** Do not begin Phase 3, 4, 5, 6, 7, 8, or 9 until the preceding phase has been reviewed, tested, and approved.
2. **Zero Fabrication:** The graph and all outputs must derive strictly from authentic datasets (`transactions.csv`, `identity.csv`, `closed_cases_history.csv`).
3. **No Benchmark Hardcoding:** Case IDs must remain purely diagnostic labels. Re-labeling any case to a synthetic identifier must produce identical reasoning and actions.
4. **Honest Evaluation:** Never claim benchmark accuracy without ground truth. Evaluate engineering correctness, mathematical soundness, and graph provenance.
