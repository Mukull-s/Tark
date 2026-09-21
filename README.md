# Tark (तर्क)
### Autonomous Agentic Fraud Investigation System with TigerGraph & Deterministic Reasoning Boundaries

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-61dafb.svg)](https://reactjs.org/)
[![TigerGraph Cloud](https://img.shields.io/badge/TigerGraph-Savanna%20Cloud-orange.svg)](https://www.tigergraph.com/)
[![Tests](https://img.shields.io/badge/tests-357%20passed-brightgreen.svg)](#testing--evaluation)

Tark is an autonomous fraud investigation workstation and reasoning engine built on **TigerGraph** for the Hacker House Goa 2026 challenge. It investigates credit card fraud alerts by combining graph topological queries, deterministic Bayesian belief updating, an information-theoretic Evidence Compass, deterministic policy gating, and grounded regulatory SAR generation.

Unlike standard autonomous agent architectures that delegate execution decisions to probabilistic Large Language Models, Tark enforces strict **non-interference boundaries**: the graph query dispatcher, likelihood ratio updates, decision gates, and regulatory policy actions are deterministic and auditable. The LLM functions exclusively as a grounded synthesis and explanation engine.

---

## The Problem

Traditional fraud operations face two compounding failure modes:
1. **Rule & Score Overload:** Monolithic ML risk scores (e.g., IEEE-CIS scores) flag millions of transactions without contextual explanation, generating excessive false alarms and alert fatigue.
2. **Uncontrolled Agentic "Hallucination":** Giving LLM agents direct tool-calling authority over financial and compliance actions (e.g., blocking cards, filing SARs) introduces non-deterministic execution, ungrounded justifications, and lack of mathematical auditability.

Tark resolves this tension by decoupling **evidence gathering & deterministic reasoning** from **natural language synthesis**.

---

## System Architecture

```
                                  ┌──────────────────────────────────────────────┐
                                  │           Tark Investigation Engine          │
                                  └──────────────────────────────────────────────┘
                                                          │
          ┌───────────────────────────────────────────────┴──────────────────────────────────────────────┐
          ▼                                               ▼                                              ▼
┌───────────────────┐                         ┌───────────────────────────────┐              ┌────────────────────────┐
│  Evidence Compass │                         │     Controlled Dispatcher     │              │    Bayesian Belief     │
│   (EVOI Engine)   │                         │     & TigerGraph Protocol     │              │         Engine         │
└─────────┬─────────┘                         └───────────────┬───────────────┘              └───────────┬────────────┘
          │                                                   │                                          │
          │ Evaluates candidate tool value                    │ Executes authorized graph queries        │ Updates P(Fraud)
          │ against Shannon entropy                           │ via TigerGraph REST / MCP                │ via likelihood ratios
          ▼                                                   ▼                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                   EVIDENCE LEDGER                                                      │
│                         Immutable, cryptographically referenced trace of all collected facts                           │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                              │
          ┌───────────────────────────────────────────────────┼──────────────────────────────────────────────────┐
          ▼                                                   ▼                                                  ▼
┌───────────────────┐                             ┌───────────────────────┐                          ┌───────────────────┐
│   Decision Gate   │                             │     Policy Engine     │                          │ Grounded Synthesis│
│  & Flip Analysis  │                             │   (Rules R1-R6 Yaml)  │                          │    & FinCEN SAR   │
└─────────┬─────────┘                             └───────────┬───────────┘                          └───────────┬───────┘
          │ Gating checks:                                    │ Statutory thresholds:                            │ LLM strictly cites
          │ - Evidence coverage >= 60%                        │ - Freeze Card (P>=0.85)                          │ Evidence Ledger &
          │ - Entropy <= 0.40                                 │ - FinCEN SAR Filing                              │ GraphRAG Precedents
          │ - Stability verified                              │ - Human Approval Routes                          │ No hallucinated facts
          ▼                                                   ▼                                                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                            ANALYST INVESTIGATION WORKSTATION                                           │
│                       Real-time queue, Evidence Compass telemetry, interactive graph topology,                         │
│                                    human approval workflows, and one-click SAR export                                  │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Non-Interference Architectural Boundary
To guarantee regulatory auditability and financial safety:
- **Zero LLM Mutation:** The LLM cannot mutate `P(Fraud)`, modify evidence items, bypass the Decision Gate, or change policy recommendations.
- **Strict Citation Grounding:** Every claim in generated SAR narratives must cite an immutable evidence item `[EVD-...]` or historical case precedent `[CC-...]`.
- **Deterministic Action Evaluation:** Policy actions (`BLOCK_CARD`, `FILE_SAR`, `CLEAR_ALERT`, etc.) are computed by a deterministic rule engine (`src/policy/engine.py`) based on audited thresholds.

---

## Core Components

### 1. TigerGraph Graph Queries & Topology
Tark models customers, cards, transactions, devices, IP domains, billing regions, and historical closed cases as a native graph in TigerGraph. Five core parameterized GSQL queries power topological analysis:
- `customer_profile`: Account tenure, transaction velocity, baseline behaviors.
- `txn_velocity`: Burst transaction patterns and short-interval frequency spikes.
- `device_analysis`: Shared device fingerprints and coordinated fraud rings.
- `region_analysis`: Billing vs. IP country mismatches and impossible travel.
- `similar_cases`: Topological neighborhood similarity across 5,565 historical closed cases.

### 2. Evidence Compass & Expected Value of Information (EVOI)
Instead of executing tools haphazardly or relying on an unconstrained LLM agent:
- The **Evidence Compass** ranks candidate queries by their **Expected Value of Information (EVOI)**:
  $$\text{EVOI}(Q) = H(\text{Current Belief}) - \mathbb{E}[H(\text{Posterior Belief} \mid Q)] - \text{ExecutionCost}(Q)$$
- Investigations prioritize queries that have high expected entropy reduction while penalizing redundant or expensive actions.

### 3. Bayesian Belief Engine
- Initialized with alert-conditioned base priors calibrated on empirical data ($P_0 \approx 0.838$).
- Updates belief state through calibrated **Likelihood Ratios (LR)** for each verified evidence item.
- Applies **family correlation discounting** to prevent overconfidence from correlated graph signals (e.g., discounting multiple velocity signals from the same card cluster).

### 4. Decision Gate & Policy Engine
An investigation cannot recommend terminal action until passing explicit deterministic gates:
- **Evidence Coverage:** At least 60% of required signal categories explored.
- **Belief Stability:** Posterior entropy below target decision threshold ($\le 0.40$).
- **Statutory Policy Rules:** Evaluates codified rules (R1 through R6) determining primary actions, secondary escalations, and whether human analyst approval is legally mandated.

### 5. Human-in-the-Loop & Controlled Analyst Pivot
When automated policy triggers a mandatory approval requirement (or when an analyst overrides a preliminary recommendation):
- Analysts can **Approve**, **Reject**, or execute a **Controlled Evidence Pivot**.
- A pivot dynamically injects analyst observations into the Evidence Ledger and re-evaluates the Bayesian state and policy rules without corrupting the audit trail.

---

## Analyst Investigation Workstation

Built with **React 18**, **TypeScript**, and **Tailwind CSS**, the frontend provides an analyst-centric workstation:
- **Investigation Queue:** Responsive grid/list view with alert badges, risk indicators, and case filters.
- **Evidence Compass:** Real-time EVOI candidate scoring, execution traces, and entropy reduction charts.
- **Interactive Topology Inspector:** Live schema topology, vertex/edge counts, and neighborhood relationship explorer.
- **Decision Gate Telemetry:** Explicit pass/fail constraint checklist showing exact mathematical criteria.
- **FinCEN SAR Narrative:** Side-by-side view with verified evidence cross-references and statutory copy/export options.

---

## Quickstart

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- TigerGraph Cloud instance (Savanna) with `FraudInvestigation` graph loaded
- Merge Gateway API Key (or OpenAI / DeepSeek API compatible endpoint)

### 1. Clone & Configure Environment
```bash
git clone https://github.com/Mukull-s/Tark.git
cd Tark

# Copy and configure environment variables
cp .env.example .env
```

Edit `.env`:
```ini
MERGE_GATEWAY_API_KEY=your_key_here
LLM_BASE_URL=https://api-gateway.merge.dev/v1
LLM_MODEL=deepseek/deepseek-v4-flash
TG_HOST=https://your-instance.i.tgcloud.io
TG_USERNAME=tigergraph
TG_PASSWORD=your_password
TG_SECRET=your_secret
TG_GRAPHNAME=FraudInvestigation
```

### 2. Backend Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Start FastAPI backend
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd web
npm install
npm run dev
```
Workstation will be available at `http://localhost:5173` (proxied to API on `http://localhost:8000`).

---

## Testing & Evaluation

Tark includes a test suite verifying both mathematical invariants and UI behavior:

```bash
# Run all 291 backend tests
python -m pytest tests/

# Run all 66 frontend workstation tests
cd web
npm test -- --run

# Run full TypeScript & Vite production build
npm run build
```

### Authoritative Benchmark Runner
To run the automated 20-case benchmark evaluation:
```bash
python bench/run.py
```
Outputs are written to `analysis/phase_a_after/` and served via `/api/benchmark/summary`.

---

## Repository Structure

```
Tark/
├── src/                                # Core Python Production Source
│   ├── agent/                          # Orchestrator and agent loop
│   ├── api/                            # FastAPI endpoints and telemetry
│   ├── belief/                         # Bayesian BeliefEngine & calibration
│   ├── compass/                        # Evidence Compass & EVOI math
│   ├── evidence/                       # EvidenceLedger & typing
│   ├── graph/                          # TigerGraph connection & resolver
│   ├── knowledge/                      # Policy rule models & store
│   ├── mcp/                            # TigerGraph MCP server & client
│   ├── memory/                         # CaseMemoryStore (closed cases)
│   ├── planner/                        # Decision flip analysis
│   ├── policy/                         # Deterministic PolicyEngine (rules.yaml)
│   ├── synthesis/                      # Grounded SAR generator
│   └── tools/                          # Controlled dispatcher & graph tools
├── web/                                # Analyst Workstation Frontend
│   ├── src/
│   │   ├── components/                 # Workstation views & components
│   │   ├── api/                        # Typed API client
│   │   └── test/                       # 15 Vitest test suites (66 tests)
│   ├── package.json
│   └── vite.config.ts
├── docs/                               # System Documentation
│   ├── architecture.md                 # Architectural design
│   ├── reasoning-model.md              # Mathematical Bayesian formulation
│   ├── evidence-scoring.md             # EVOI and likelihood ratio formulas
│   ├── frontend-backend-contract.md    # API schemas and contracts
│   ├── roadmap.md                      # Production deployment roadmap
│   ├── CHALLENGE_SPECIFICATION.md      # HHG Track 4 problem statement & glossary
│   ├── FINAL_FORENSIC_AUDIT_REPORT.md  # Comprehensive forensic verification audit
│   ├── reference/                      # Original competition challenge PDFs
│   └── archive/                        # Historical phase development reports
├── cases/                              # Benchmark answer files (HHG-001..020)
├── queries/                            # Parameterized GSQL queries for TigerGraph
├── schema/                             # GSQL graph schema definition
├── bench/                              # Benchmark runners (run.py)
├── analysis/                           # Runtime calibration (lr_table.json) & benchmark logs
├── case_pack.csv                       # Benchmark 20-case test pack
├── closed_cases_history.csv            # 5,565 historical closed case records
├── requirements.txt                    # Python dependencies
└── README.md                           # This document
```

---

## Operational Truthfulness & System Boundaries

In accordance with strict engineering integrity standards:
1. **Deterministic Core:** The LLM does not choose tools, execute arbitrary graph queries, or modify `P(Fraud)`. Tool selection is guided deterministically by the Evidence Compass (EVOI).
2. **External Adapters:** Synthetic mock adapters (`CustomerVerificationTool`, `ExternalIntelligenceTool`) demonstrate cross-system interoperability without connecting to real live credit bureaus.
3. **Graph Algorithms:** Graph queries run directly on live TigerGraph instances via REST/MCP protocols against the schema defined in `schema/schema.gsql`.
4. **Autonomous Limits:** High-impact mitigation actions (e.g., blocking active customer cards or issuing regulatory filings) enforce explicit human-in-the-loop approval routes as codified in bank compliance policy.
