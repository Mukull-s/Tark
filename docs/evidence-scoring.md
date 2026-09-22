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

---

## 7. Trigger-Conditioned Prior Resolution (v3.1)

The `ALERT_CONDITIONED` prior is only statistically valid for cases that arrived through an
inbound cardholder dispute. Applying $P(\text{Fraud})=0.8383$ indiscriminately to thin,
low-confidence model alerts caused systematic over-classification (auto-fraud of
uninformative cases). `src/belief/calibration.py::resolve_trigger_prior` therefore resolves
the prior explicitly from the trigger channel:

| Trigger channel | Prior profile | Rationale |
|---|---|---|
| `customer_report` | `ALERT_CONDITIONED` (0.8383) | Inbound dispute is itself alert-conditioned evidence. |
| `analyst_request` | `UNIFORM` (0.50) | Human referral carries no calibrated statistical prior. |
| `risk_score < 0.65` | `UNIFORM` (0.50) | Below-threshold model alert; maximum-entropy baseline. |
| `risk_score >= 0.65` | `ALERT_CONDITIONED` (0.8383) | Confirmed high-risk alert. |
| unknown | `UNIFORM` (0.50) | Defensive maximum-entropy default. |

The resolved profile, with its audit rationale, is threaded through
`BeliefEngine.evaluate_investigation`, `bench/run.py`, and `evaluation/harness.py`.

## 8. Corroboration Contract for Positive Fraud Determinations (v3.1)

A high posterior ($P \ge 0.70$) is **not** sufficient by itself for an automated
`confirmed_fraud` gate pass. The Decision Gate additionally requires corroboration:

$$\text{corroborated} \;=\; \text{conclusive dispute} \;\lor\; \#\{\text{informative families}\} \ge 2$$

where an *informative family* is a semantic evidence family contributing a non-zero
effective log-LR after family discounting and ceilings. This prevents the prior from
auto-frauding cases whose posterior rests on a single uncorroborated dimension
(e.g. the model risk score alone). Non-corroborated high-posterior cases remain in
`INSUFFICIENT_EVIDENCE` and receive a monitoring / verification posture rather than a
terminal fraud disposition.

`CUSTOMER_COMMUNICATION_UNAVAILABLE` (LR = 1.0) contributes zero log-odds, emits an
explicit `MissingInfoItem`, and never unlocks the gate on its own.

## 9. Likelihood-Ratio Recalibration Audit (Honest Non-Identifiability Note)

The closed-case population (`closed_cases_history.csv`, 4,665 confirmed fraud / 900
cleared) supports exactly one empirical quantity: the **alert-conditioned prior**
$4665/5565 = 0.8383$. It does **not** identify evidence-conditioned likelihood ratios,
because every historically `cleared` case carries the sentinel typology `none` (no
observed fraud pattern), so $P(E_{\text{typology}} \mid \text{cleared}) = 0$ for all
fraud typologies and every candidate LR is degenerate (infinite/undefined).

The `PROVISIONAL` classifications in the LR registry are therefore intentionally
**retained** rather than promoted to `EMPIRICAL`; promoting them would misrepresent the
identifiability of the data. Evidence-conditioned ratios remain anchored on operational
IEEE-CIS statistics with explicit governance tiers, and the specificity benchmark
(`bench/eval_specificity.py`) provides the empirical false-positive evidence that the
cleared population can actually support.

## 10. Probed Dimensions & Per-Trigger Coverage Denominator (v3.2)

**Coverage denominator is trigger-specific.** Evidence coverage is no longer a fixed
$1/5$ ratio. The denominator is the set of dimensions that are resolvable and
decision-relevant for the trigger channel (`BeliefEngine.resolve_applicable_families`):

| Trigger channel | Applicable checklist | Denominator |
|---|---|---|
| `risk_score` | device, velocity, behavioral, dispute, model score | 5 |
| `customer_report` | device, velocity, behavioral, dispute | 4 |
| `analyst_request` | device, velocity, behavioral | 3 |
| unknown | canonical superset | 5 |

$$\text{evidence\_coverage} = \frac{|\text{observed} \cap \text{applicable}|}{|\text{applicable}|}$$

This is why the benchmark shows genuine coverage variance (0.20 / 0.40 / 0.50 / 0.67)
rather than a single value, and why `applicable_dimensions` is emitted per case.

A graph query that executes and returns `NO_MATCH` is recorded as a **probed** dimension
(`UncertaintyState.probed_dimensions` / `probed_coverage`). Probed dimensions are
reported for explainability but deliberately do **not** count toward `evidence_coverage`
and do **not** reduce the epistemic gate: absence of an observed pattern is not proof,
and letting ruled-out dimensions unlock a gate would contradict the `NO_MATCH` neutrality
contract (Required Change 4). This keeps coverage a measure of *informative* dimensions
while still crediting the investigation for work performed.

## 11. R6-Syndicate Exception (v3.2)

A shared-device ring spanning $\ge 10$ independent card accounts (`SYNDICATE_CARD_THRESHOLD`)
is a large-scale syndicate. When the Decision Gate is locked, the policy engine routes
the case to `ESCALATE_TO_ANALYST` at approval route `L2` and **defers** automatic
`FILE_REPORT` until a human authorizes the filing. This removes the
"locked gate + auto-filed SAR" tension: the multi-account graph corroboration justifies
escalation, and the SAR is not filed by an unresolved automated gate.

## 12. Independent NBA Evaluation (v3.2)

`evaluation/harness.py` no longer derives expected actions from `cases/*.json` (which
would be circular). Expectations come only from the case pack column
(`expected_primary_action`, if present) or the human-authored, policy-grounded rubric
`analysis/expected_nba.json`. The harness additionally computes an independent
**policy-invariant conformance** rate by re-checking emitted results against policy
invariants (locked gate must not punish; cardholder reports must be contained; a
`legitimate` disposition must not be punitive).


