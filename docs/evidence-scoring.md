# Tark: Evidence Scoring & Likelihood Ratio Inventory
## Parameter Catalog, Provenance, and Justification Audit

**Author:** Antigravity (Forensic Code & Systems Recovery)  
**Status:** Canonical Parameter Inventory (Phase 3 Hardened)  
**Version:** 3.0.0  

---

## 1. Executive Summary

In Bayesian forensic evidence reasoning, evidence updates prior belief via the Likelihood Ratio (LR):

$$\text{LR} = \frac{P(E \mid \text{Fraud})}{P(E \mid \text{Legitimate})}, \quad \ln(\text{Posterior Odds}) = \ln(\text{Prior Odds}) + \sum_{i} w_i \ln(\text{LR}_i)$$

Phase 3 establishes a rigorous, uncertainty-aware reasoning layer that consumes `EvidenceItem`s, prevents correlated evidence inflation via semantic family discounting and log-LR ceilings, handles `DATA_OUT_OF_SCOPE` as epistemic uncertainty, detects contradictions, and exposes an auditable, machine-readable `ReasoningStep` trace.

Every parameter in Tark is strictly classified under one of four governance tiers:
- **`EMPIRICAL`**: Derived statistically from historical training partitions.
- **`POLICY_DEFINED`**: Mandated by bank risk governance or financial regulatory standards.
- **`HEURISTIC`**: Domain-informed typologies requiring ongoing verification.
- **`PROVISIONAL`**: Uncalibrated parameters explicitly flagged for offline re-estimation.

---

## 2. Global Prior Parameters & Semantics

A critical failure in fraud reasoning is conflating the population base rate with alert-conditioned rates. Tark explicitly models three prior profiles in `src/belief/calibration.py`:

| Prior Profile | Value $P(\text{Fraud})$ | Log-Odds $\ln\frac{p}{1-p}$ | Classification | Population Provenance & Usage |
|---|---|---|---|---|
| **`ALERT_CONDITIONED`** | **0.8383** | **+1.6454** | **EMPIRICAL** | Derived from `closed_cases_history.csv` (4,665 confirmed fraud out of 5,565 historical closed alert triage cases). **Valid ONLY for alerted or escalated cases.** Must NOT be applied to general transactions. |
| **`UNCONDITIONED_POPULATION`** | **0.0050** | **-5.2933** | **PROVISIONAL** | Industry benchmark baseline (~0.5% fraud rate across unselected card volume). Provisional base rate for continuous transaction stream monitoring. |
| **`UNIFORM_NON_INFORMATIVE`** | **0.5000** | **0.0000** | **HEURISTIC** | Maximum entropy neutral baseline ($p=0.5$). Zero prior bias; belief updates are driven purely by observed evidence. |

---

## 3. Likelihood Ratio (LR) Catalog & Semantic Families

To prevent independent multiplication of correlated signals, every evidence type is bound to a **Semantic Evidence Family** with a defined **Family Log-LR Ceiling**:

| Evidence Type | LR Value | Log-LR ($\ln$) | Classification | Semantic Family | Family Ceiling $\ln(\text{LR})$ | Source & Justification |
|---|---|---|---|---|---|---|
| `CARD_TESTING_SEQUENCE` | `34.3` | `+3.535` | **PROVISIONAL** | `TRANSACTION_VELOCITY` | 4.5 | $\ge 3$ micro-authorizations ($\le \$5$) followed by larger transaction within 24h. |
| `HIGH_VELOCITY` | `2.5` | `+0.916` | **PROVISIONAL** | `TRANSACTION_VELOCITY` | 4.5 | $10+$ transactions within 24h window. Rapid card liquidation indicator. |
| `SHARED_DEVICE_RING` | `14.2` | `+2.653` | **PROVISIONAL** | `DEVICE_INFRASTRUCTURE` | 4.0 | Device profile shared across $\ge 2$ distinct cardholders in graph. |
| `PROXY_DETECTED` | `3.8` | `+1.335` | **PROVISIONAL** | `DEVICE_INFRASTRUCTURE` | 4.0 | Transaction routed through anonymous or hidden proxy. |
| `CNP_NEW_DEVICE` | `1.31` | `+0.273` | **PROVISIONAL** | `DEVICE_INFRASTRUCTURE` | 4.0 | Card-not-present transaction on previously unseen device. |
| `CUSTOMER_DENIAL` | `18.5` | `+2.918` | **POLICY_DEFINED** | `CUSTOMER_DISPUTE` | 5.0 | Cardholder disputes or explicitly denies transaction authorization. |
| `CUSTOMER_CONFIRMATION` | `0.05` | `-2.996` | **POLICY_DEFINED** | `CUSTOMER_DISPUTE` | 5.0 | Cardholder confirms authorized transaction (strongly exculpatory). |
| `OUT_OF_REGION` | `0.26` | `-1.357` | **EMPIRICAL** | `GEOGRAPHIC_LOCATION` | 2.5 | Transaction in unobserved billing region (correlated with travel in IEEE-CIS data). |
| `RECURRING_CHARGE_MATCH` | `0.08` | `-2.526` | **POLICY_DEFINED** | `BEHAVIORAL_BASELINE` | 3.5 | Transaction matches monthly recurring billing cadence and amount. |
| `BEHAVIORAL_BASELINE` | `1.0` | `0.000` | **EMPIRICAL** | `BEHAVIORAL_BASELINE` | 0.0 | Normal customer historical activity baseline (neutral). |
| `ACCOUNT_TAKEOVER` | `2583.07` | `+7.857` | **PROVISIONAL** | `DEVICE_INFRASTRUCTURE` | 4.0 | Historical extreme LR; clamped by family ceiling to prevent posterior saturation. |

---

## 4. Real-Time Model Score Calibration Bins

Model scores are binned and calibrated to avoid raw probability miscalibration:

| Score Range | Calibrated LR | Log-LR ($\ln$) | Classification | Semantic Family | Rationale |
|---|---|---|---|---|---|
| `[0.0, 0.3)` | `0.15` | `-1.897` | **EMPIRICAL** | `MODEL_SCORE` | Low model score; exculpatory shift ($LR < 1.0$). |
| `[0.3, 0.6)` | `0.85` | `-0.163` | **EMPIRICAL** | `MODEL_SCORE` | Near neutral; slight exculpatory tendency. |
| `[0.6, 0.8)` | `2.40` | `+0.875` | **EMPIRICAL** | `MODEL_SCORE` | Elevated model score; moderate inculpatory shift. |
| `[0.8, 1.0]` | `6.80` | `+1.917` | **EMPIRICAL** | `MODEL_SCORE` | High model score; strong inculpatory shift. |

---

## 5. Correlated Evidence Aggregation & Diminishing Returns

Naive independent multiplication of co-occurring signals (e.g. `SHARED_DEVICE_RING` + `PROXY_DETECTED` + `52 connected cards`) produces mathematically absurd posterior probabilities.

Tark applies **Defensible Intra-Family Diminishing Returns**:
- $w_1 = 1.0$ for the first observation in an evidence family.
- $w_2 = 0.5$ for the second observation.
- $w_{k \ge 3} = 0.25$ for subsequent observations.

Furthermore, cumulative log-LR within any family cannot exceed that family's defined ceiling:
$$\text{cumulative\_family\_log\_lr} \le C_f$$

This ensures that redundant signals from the same infrastructure or sequence cannot drive belief to 0.99999 without independent confirmation from other investigative dimensions.

---

## 6. Scope & Uncertainty Governance

1. **`DATA_OUT_OF_SCOPE` vs `NO_MATCH`**:
   - `DATA_OUT_OF_SCOPE`: Zero log-odds shift ($\Delta \text{log-odds} = 0.0$). Generates `MissingInfoItem`, increments `epistemic_uncertainty`. Never treated as absence of fraud.
   - `NO_MATCH`: Confirms absence of pattern within observed scope.
2. **Contradictions**:
   - Tracked separately ($L^+$ vs $L^-$). When both are strong ($\ge 1.5$), generates `ContradictionItem` and escalates to `DecisionState.REQUIRES_HUMAN_APPROVAL`.
