# Tark Reasoning Model — Mathematical & Architectural Specification
## Phase 3.1 Hardened: Decision Semantics, World Hypotheses, and Gating Integrity

## 1. Architectural Pipeline & Separation of Concerns

In the Tark investigation engine, evidence collection is strictly decoupled from belief formation and decision execution:

```
[Trigger / Event]
        ↓
[TigerGraph GSQL Queries & External Tools]
        ↓
[EvidenceLedger (List of EvidenceItem)]
        ↓
[BeliefEngine / ScoringService]
        ├── Prior Selection (Alert-Conditioned vs Population vs Uniform)
        ├── Deduplication & Collision Defense
        ├── Evidence Family Grouping & Diminishing Returns
        ├── Family Log-LR Ceilings
        ├── Contradiction Tracking & Conflict Metric
        ├── Scope Boundary Handling (DATA_OUT_OF_SCOPE vs GRAPH_QUERY_FAILURE vs NO_MATCH)
        └── Deterministic Decision Gating Contract
        ↓
[InvestigationState]
        ├── World Hypotheses (FRAUD and LEGITIMATE only; sum = 1.0)
        ├── Belief State (Posterior Probability, Net Log-LR)
        ├── Multi-Dimensional Uncertainty State (Epistemic, Aleatoric, Coverage)
        ├── Decision Gate Result (Passed / Blocked, Specific Contract Blocks)
        ├── Decision State (DECIDED, INSUFFICIENT_EVIDENCE, REQUIRES_HUMAN_APPROVAL)
        └── Machine-Readable Reasoning Trace (ReasoningStep[])
```

**Core Invariant:** Raw evidence items do NOT mutate final actions. A query finding (e.g. `CARD_TESTING_SEQUENCE`) produces an `EvidenceItem`, which is evaluated against hypotheses via Likelihood Ratios (LRs) within semantic families, updating belief and uncertainty before any candidate action or policy rule is considered.

---

## 2. World Hypotheses vs Epistemic Decision States

A critical conceptual correction in Phase 3.1 is the separation of **World Hypotheses** from **Epistemic Decision States**:

### World Hypotheses (States of Nature)
There are exactly two mutually exclusive states of the world:
1. **`FRAUD`**: The activity was unauthorized or syndicate-operated.
2. **`LEGITIMATE`**: The activity was authorized customer behavior.

The posterior probabilities of these world states sum strictly to 1.0:
$$P(\text{FRAUD}) + P(\text{LEGITIMATE}) = 1.0$$
**`INSUFFICIENT_EVIDENCE` is NOT a third world hypothesis**; it is an epistemic property of the investigation. The system never calculates $P(\text{INSUFFICIENT\_EVIDENCE})$ as a competing state of nature.

### Epistemic Decision States
The operational state of the investigation is tracked in `decision_state`:
- **`DECIDED`**: Evidence satisfies all automated decision contract criteria; automated verdict is admissible.
- **`INSUFFICIENT_EVIDENCE`**: Evidence is too sparse, uncorroborated, or uncertain to justify an automated determination.
- **`REQUIRES_HUMAN_APPROVAL`**: Evidentiary conflict is severe; automated determination is blocked and escalated to human compliance.
- **`PENDING`**: Investigation in progress.

---

## 3. Deterministic Decision Gating Contract

A high posterior probability alone ($P(\text{Fraud}) \ge 0.70$) CANNOT produce a final automated decision if evidence is materially insufficient. Tark enforces an explicit, deterministic 5-condition contract:

```python
# Condition 1: Aleatoric Conflict Gate
if aleatoric_uncertainty >= 0.40:
    decision_gate_passed = False
    decision_state = DecisionState.REQUIRES_HUMAN_APPROVAL
    approval_requirements = ["HUMAN_RISK_ANALYST"]

# Condition 2: Material Evidence Coverage Gate (MIN_DECISION_COVERAGE = 0.40)
elif evidence_coverage < 0.40 and not has_conclusive_dispute:
    decision_gate_passed = False
    decision_state = DecisionState.INSUFFICIENT_EVIDENCE

# Condition 3: Epistemic Uncertainty Gate
elif epistemic_uncertainty > 0.60:
    decision_gate_passed = False
    decision_state = DecisionState.INSUFFICIENT_EVIDENCE

# Condition 4: Intermediate Probability Band Gate
elif 0.30 < fraud_prob < 0.70:
    decision_gate_passed = False
    decision_state = DecisionState.INSUFFICIENT_EVIDENCE

# Condition 5: Admissible Determination
else:
    decision_gate_passed = True
    decision_state = DecisionState.DECIDED
```

### Resolution of the Completeness Contradiction
In Phase 3, documentation stated `completeness < 0.25 -> insufficient evidence`, while an ablation table displayed `completeness = 0.20 -> DECIDED`. 

Phase 3.1 resolves this contradiction definitively:
- **Unified Rule:** `MIN_DECISION_COVERAGE = 0.40` (at least 2 out of 5 core dimensions must be observed, or an explicit conclusive customer dispute event must exist).
- In Ablation B (Single family: Transaction Velocity, coverage = 0.20):
  - $P(\text{Fraud}) = 0.9717$ (High posterior).
  - Decision Gate evaluates coverage $0.20 < 0.40 \implies$ **BLOCKED**.
  - `decision_state = DecisionState.INSUFFICIENT_EVIDENCE`.
  - Rationale: *"I have evidence of suspicious behavior, but insufficient evidence to make a fraud determination (evidence coverage: 0.20 < 0.40)."*
- Both code, tests, and documentation now strictly agree.

---

## 4. Prior Semantics & Population Distinctions

| Profile | Prior $P(\text{Fraud})$ | Log-Odds $\ln\frac{p}{1-p}$ | Classification | Valid Population & Usage |
| :--- | :--- | :--- | :--- | :--- |
| **`ALERT_CONDITIONED`** | **0.8383** | **+1.6454** | **EMPIRICAL** | Calculated from `closed_cases_history.csv` (4,665 fraud out of 5,565 closed alert cases). Valid **only** when investigating transactions already flagged by anomaly models or inbound disputes. |
| **`UNCONDITIONED_POPULATION`** | **0.0050** | **-5.2933** | **PROVISIONAL** | Industry benchmark baseline (~0.5% fraud rate across unselected card transaction streams). Used for transaction stream monitoring. |
| **`UNIFORM_NON_INFORMATIVE`** | **0.5000** | **0.0000** | **HEURISTIC** | Maximum entropy neutral baseline ($p=0.5$). Zero prior bias; belief updates are driven purely by observed evidence. |

---

## 5. Likelihood Ratio Calibration Classifications

All provisional and heuristic values remain explicitly labeled; heuristic parameters are never presented as empirical facts.

| Evidence Type | Empirical LR | $\ln(\text{LR})$ | Classification | Semantic Family | Family Ceiling $\ln(\text{LR})$ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `CARD_TESTING_SEQUENCE` | 34.3 | +3.535 | **PROVISIONAL** | `TRANSACTION_VELOCITY` | 4.5 |
| `HIGH_VELOCITY` | 2.5 | +0.916 | **PROVISIONAL** | `TRANSACTION_VELOCITY` | 4.5 |
| `SHARED_DEVICE_RING` | 14.2 | +2.653 | **PROVISIONAL** | `DEVICE_INFRASTRUCTURE` | 4.0 |
| `PROXY_DETECTED` | 3.8 | +1.335 | **PROVISIONAL** | `DEVICE_INFRASTRUCTURE` | 4.0 |
| `CNP_NEW_DEVICE` | 1.31 | +0.273 | **PROVISIONAL** | `DEVICE_INFRASTRUCTURE` | 4.0 |
| `CUSTOMER_DENIAL` | 18.5 | +2.918 | **POLICY_DEFINED** | `CUSTOMER_DISPUTE` | 5.0 |
| `CUSTOMER_CONFIRMATION` | 0.05 | -2.996 | **POLICY_DEFINED** | `CUSTOMER_DISPUTE` | 5.0 |
| `OUT_OF_REGION` | 0.26 | -1.357 | **EMPIRICAL** | `GEOGRAPHIC_LOCATION` | 2.5 |
| `RECURRING_CHARGE_MATCH`| 0.08 | -2.526 | **POLICY_DEFINED** | `BEHAVIORAL_BASELINE` | 3.5 |
| `BEHAVIORAL_BASELINE` | 1.0 | 0.000 | **EMPIRICAL** | `BEHAVIORAL_BASELINE` | 0.0 |
| Score Bin $[0.0, 0.3)$ | 0.15 | -1.897 | **EMPIRICAL** | `MODEL_SCORE` | 3.0 |
| Score Bin $[0.3, 0.6)$ | 0.85 | -0.163 | **EMPIRICAL** | `MODEL_SCORE` | 3.0 |
| Score Bin $[0.6, 0.8)$ | 2.40 | +0.875 | **EMPIRICAL** | `MODEL_SCORE` | 3.0 |
| Score Bin $[0.8, 1.0]$ | 6.80 | +1.917 | **EMPIRICAL** | `MODEL_SCORE` | 3.0 |

---

## 6. Correlated Evidence Strategy & Damping

Intra-family diminishing returns are applied to prevent redundant evidence inflation:
$$w_1 = 1.0, \quad w_2 = 0.50, \quad w_{k \ge 3} = 0.25$$
Constrained by family cumulative ceilings $C_f$. Redundant device or velocity signals cannot drive log-odds to infinity without corroboration from other domains.

---

## 7. Data Scope Semantics: Scope Boundary, Query Failures, and Pattern Absences

Tark enforces a strict 4-way semantic distinction:

1. **Observed Exculpatory Evidence:**
   - Affirmative observation of legitimate customer behavior (e.g., `CUSTOMER_CONFIRMATION` LR=0.05, `RECURRING_CHARGE_MATCH` LR=0.08). Shifts log-odds toward legitimate.
2. **`NO_MATCH` (Absence of a Pattern):**
   - The graph query executed successfully within valid scope, and the specific fraud signature (e.g., card testing sequence) was not found.
   - **Default Semantics:** Neutral baseline ($\text{LR}=1.0, \ln(\text{LR})=0.0$). Does NOT constitute exculpatory proof of innocence.
3. **`DATA_OUT_OF_SCOPE` (Horizon Boundary):**
   - The query entity or date range is outside ingested graph horizons.
   - $\Delta \text{log-odds} = 0.0$. Recorded in `missing_information` as `reason="DATA_OUT_OF_SCOPE"`, increments `epistemic_uncertainty`.
4. **`GRAPH_QUERY_FAILURE` (Operational Error):**
   - Infrastructure timeout or connection failure.
   - $\Delta \text{log-odds} = 0.0$. Recorded in `missing_information` as `reason="GRAPH_QUERY_FAILURE"`, impact severity `"HIGH"`, increments `epistemic_uncertainty`.

---

## 8. Multi-Dimensional Uncertainty & Coverage

The five core investigative dimensions are:
- `DEVICE_INFRASTRUCTURE`
- `TRANSACTION_VELOCITY`
- `BEHAVIORAL_BASELINE`
- `CUSTOMER_DISPUTE`
- `MODEL_SCORE`

`UncertaintyState` explicitly tracks:
- `evidence_coverage`: observed dimensions / 5.
- `observed_dimensions`: list of observed core families.
- `missing_dimensions`: list of unobserved core families.
- `unavailable_dimensions`: list of dimensions that returned `DATA_OUT_OF_SCOPE` or `GRAPH_QUERY_FAILURE`.
- `aleatoric_uncertainty`: contradiction conflict metric $2 \cdot \min(L^+, L^-) / (L^+ + L^-)$.
- `epistemic_uncertainty`: unobserved and unavailable data horizons.
- `confidence_score`: composite trustworthiness metric.
- `uncertainty_reasons`: human- and machine-readable qualitative explanations.

---

## 9. Full Machine-Readable Reasoning Trace

Every decision step, including the decision gate evaluation, is logged:
```json
{
  "step": 3,
  "event": "DECISION_GATE_EVALUATED",
  "prior_log_odds": 3.535,
  "posterior_log_odds": 3.535,
  "posterior_prob": 0.9717,
  "rationale": "Decision Gate: Passed=False. State=INSUFFICIENT_EVIDENCE. Blocks=['Evidence coverage (0.20) is below minimum threshold (0.40). Corroborating investigative dimensions required.']. Rationale: I have evidence of suspicious behavior, but insufficient evidence to make a fraud determination (evidence coverage: 0.20 < 0.40, epistemic uncertainty: 0.80)."
}
```

---

## Appendix A — Trigger-Conditioned Prior Resolution (v3.1)

Prior selection is now an explicit, auditable function of the trigger channel rather than a
single global default (`src/belief/calibration.py::resolve_trigger_prior`):

- `customer_report` → `ALERT_CONDITIONED` (0.8383): the inbound dispute is itself evidence.
- `analyst_request` → `UNIFORM` (0.50): no calibrated statistical prior.
- `risk_score < 0.65` → `UNIFORM` (0.50): below-threshold alert, maximum-entropy baseline.
- `risk_score >= 0.65` → `ALERT_CONDITIONED` (0.8383): confirmed high-risk alert.

The rationale string is retained in the `InvestigationState.belief_state` audit trail and in
each benchmark answer (`case.prior_rationale`).

## Appendix B — Corroboration Gate (v3.1)

After the coverage, epistemic, and probability-band gates, a positive fraud determination
($P \ge 0.70$) additionally requires corroboration: a conclusive cardholder dispute, or
$\ge 2$ informative evidence families, or at least one non-model informative family. This
ensures a single uncorroborated dimension (e.g. the model risk score) can never produce an
automated `confirmed_fraud` disposition. Non-corroborated cases remain
`INSUFFICIENT_EVIDENCE` with a monitoring / verification posture.

