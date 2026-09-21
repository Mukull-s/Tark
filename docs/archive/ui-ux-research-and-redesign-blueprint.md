# Tark — Comprehensive UI/UX Research, Forensic Roast & Redesign Blueprint

**Scope:** In-Depth Industry UI/UX Research (TigerGraph, Palantir Foundry, Unit21, Sardine) + Hackathon Winning Criteria + Complete Modernization Blueprint  
**Date:** September 2026  
**Target Standard:** Tier-1 Enterprise Fintech Fraud Analyst Workstation  

---

## 1. Industry Research: What Tier-1 Fraud Platforms Look Like

Based on in-depth forensic analysis of production fraud systems (**Palantir Foundry, Unit21, Sardine, Chainalysis, and TigerGraph Insights**), here is how real fraud operations consoles are built:

### 1.1 The Two-Phase Analyst Lifecycle
1. **Phase 1: Alert Triage Queue (The Inbox / Command Center)**
   - Fraud analysts manage a high-velocity stream of alerts.
   - The queue displays:
     - Incident ID (`HHG-011`, `HHG-014`, etc.)
     - Ingestion Timestamp (`2016-12-29 06:27:44`)
     - Trigger Category (`Customer Dispute`, `Velocity Burst`, `Analyst Referral`, `Risk Score Spike`)
     - Exposure Amount (`$131.30`, `$74.96`)
     - Initial Risk Tier (`CRITICAL`, `HIGH`, `MEDIUM`)
     - Lifecycle Status (`OPEN`, `INVESTIGATING`, `DECISION_REACHED`, `REQUIRES_HUMAN_APPROVAL`, `CLOSED`)
   - **Clicking any alert row opens the Deep Investigation Workspace.**

2. **Phase 2: Deep Investigation Workspace (The Workbench)**
   - **Top:** Case Profile & Exposure Overview.
   - **Left:** Autonomous Agent Investigation Stream & Decision-Theoretic Trail (EVOI).
   - **Right:** Interactive TigerGraph Topology Graph (Multi-Hop Entity Linkage).
   - **Bottom Left:** Empirical Evidence Ledger (Likelihood Ratios, Log-LR, Findings).
   - **Bottom Right:** Policy Next-Best-Action, Human Governance Controls & FinCEN SAR Generator.

---

## 2. Forensic Roast & Gap Analysis of Our Current UI

| UI Element | Current Flaw | What Judges & Analysts Expect | Severity |
|---|---|---|:---:|
| **Raw JSON Dumps** | In the Investigation Stream, we dump raw JSON strings (`"evidence_observed": ...`, `"candidate_rankings": ...`). | Formatted visual cards with clear labels, metric pills, and natural language finding callouts. No raw JSON in the analyst UI. | 🔴 **CRITICAL** |
| **Case Selection Workflow** | A single `<select>` dropdown at the very top of the screen. | A dedicated **Inbound Alerts & Incident Queue View** (switchable tab or split screen) where analysts triage cases like a real bank operations team. | 🔴 **HIGH** |
| **Graph Visual Overlap** | Node pills and edge labels overlap on certain cases; text truncates awkwardly. | High-contrast nodes with distinct entity icons (Card, Device, Customer, Txn), ample canvas padding, and clean hover cards. | 🔴 **HIGH** |
| **Color Palette & Contrast** | Pale beige background (`#FBF9F5`) feels muted and low-contrast. | Modern enterprise dark-mode or crisp slate/white theme with bold status accents (Emerald for Approved, Amber for Review, Crimson for Fraud, Indigo for Graph). | 🟡 **MEDIUM** |
| **Regulatory SAR Export** | SAR narrative is buried in text cards at the bottom without a formal export modal. | A dedicated **"Export FinCEN SAR"** button that pops open a formatted compliance report ready for download/copy. | 🟡 **MEDIUM** |

---

## 3. The 4-Tab / Split Workstation Layout Blueprint

```text
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ❖ TARK FRAUD WORKSTATION                 [● TigerGraph Live: 5,565 Cases]  [👤 Mukul (L1 Analyst)] │
├──────────────┬────────────────────────────────────────────────────────────────────────────────────┤
│ ⊞ Alerts (20)│ ┌─ INBOUND ALERT QUEUE ──────────────────────────────────────────────────────────┐ │
│ ⇄ Workbench  │ │ Case ID  │ Opened At        │ Trigger Type       │ Flagged Txn │ Amount  │ Risk │ │
│ ☊ Topology   │ │ HHG-011  │ 2016-12-29 06:27 │ Customer Report    │ #3583368    │ $131.30 │ 🔴  │ │
│ 📋 SAR Filing│ │ HHG-014  │ 2016-11-22 20:11 │ Analyst Request    │ #3478561    │ $74.96  │ 🟠  │ │
│              │ └──────────┴──────────────────┴────────────────────┴─────────────┴─────────┴──────┘ │
│              ├────────────────────────────────────┬───────────────────────────────────────────────┤
│              │ INVESTIGATION EVENT STREAM         │ INTERACTIVE RELATIONSHIP TOPOLOGY             │
│              │ • Initial Prior: 83.8%             │        [Txn #3583368] ($131.30)               │
│              │ • Step 1: Device Query (LR=1.0)    │               │                               │
│              │ • Step 2: Card Sequence (LR=34.3)  │        [Card C11923-K2]                       │
│              │ • Decision: 99.97% P(Fraud)        │         /     |     \                         │
│              │                                    │    [Micro-1][Micro-2][Micro-3]                │
│              ├────────────────────────────────────┴───────────────────────────────────────────────┤
│              │ NEXT-BEST-ACTION & GOVERNANCE                                                      │
│              │ Primary: DECLINE_TRANSACTION [L1]  | Consequential: BLOCK_CARD [AUTO]              │
│              │ [ ✓ Approve Recommendation ]   [ ✕ Reject Action ]   [ 🔍 Request More Evidence ]  │
└──────────────┴────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Specific Modernization Changes to Execute

1. **Alert Queue Tab / View**:
   - Add a toggle between **"Alerts Queue" (All 20 Ingested Incidents)** and **"Active Investigation"**.
   - Analysts can see all cases at a glance and click any case to jump straight into deep investigation.
2. **Investigation Stream Polish (No More Raw JSON)**:
   - Clean badges for `QUERY_DEVICE_ANALYSIS`, `QUERY_CARD_SEQUENCE`, etc.
   - Formatted cards for evidence findings with likelihood ratios and rule citations.
3. **Graph Topology Polish**:
   - Crisp SVG node cards with colored badges:
     - `Transaction`: Slate / Green (with $ Amount)
     - `Card`: Indigo / Blue
     - `Device`: Amber / Orange (with proxy / ring badge)
     - `Customer`: Purple / Violet
   - Enhanced spacing and clear relationship labels.
4. **FinCEN SAR Report Exporter**:
   - Add a header button `[ 📄 Export FinCEN SAR ]` that opens a clean modal with the structured SAR narrative, statutes, and evidence trail ready for export.
