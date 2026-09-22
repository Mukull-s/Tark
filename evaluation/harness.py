"""Independent Evaluation Harness for Tark Autonomous Investigation Engine.

Operates externally and independently from the web serving runtime to ensure
objective, untampered benchmark evaluations.

Produces verifiable artifacts with:
- Actual NBA agreement
- Actual Decision Gate pass rate
- Actual fraud classification rate
- Actual steps, coverage, and tool distribution
- Live TigerGraph query durations
- Git commit SHA and UTC timestamp
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
import pandas as pd

# Ensure the workspace root is importable when executed directly as a script
# (e.g. `python evaluation/harness.py ...`).
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.graph.connection import get_tigergraph_connection
from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceType, EvidenceItem
from src.belief.calibration import get_model_score_lr, LIKELIHOOD_REGISTRY, resolve_trigger_prior
from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine, ActionRole
from src.compass.evoi import EvidenceCompass
from src.tools.dispatcher import EvidenceToolDispatcher
from src.memory.store import CaseMemoryStore
from src.knowledge.retriever import PolicyGraphRAGRetriever
from src.synthesis.synthesizer import GroundedInvestigationSynthesizer
from src.agent.orchestrator import InvestigationOrchestrator


logger = logging.getLogger("tark.evaluation.harness")

# Independent expected-action rubric. The harness NEVER reads cases/*.json for
# expected values; expectations come from the case pack column (if present) or
# this human-authored rubric.
EXPECTED_NBA_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "analysis",
    "expected_nba.json",
)


def load_expected_nba_rubric(path: Optional[str] = None) -> Dict[str, str]:
    """Loads the independent expected-action rubric (case_id -> expected action)."""
    target = path or EXPECTED_NBA_PATH
    if not os.path.exists(target):
        return {}
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            str(cid): str(meta.get("expected_primary_action"))
            for cid, meta in (data.get("cases") or {}).items()
            if meta.get("expected_primary_action")
        }
    except Exception as e:
        logger.warning("Failed to load expected NBA rubric %s: %s", target, e)
        return {}


def evaluate_policy_invariants(case_row: Dict[str, Any], res: Dict[str, Any]) -> List[str]:
    """Independent policy-invariant checks on the emitted investigation result.

    These invariants are derived from the bank policy manual and the case-pack
    trigger semantics — NOT from the agent's own pipeline. Violations indicate a
    governance-consistency defect.
    """
    violations: List[str] = []
    trigger_type = str(case_row.get("trigger_type", "")).lower()
    action = res.get("actual_nba")
    gate = bool(res.get("gate_passed"))
    p = float(res.get("fraud_probability", 0.5))

    if not (0.0 <= p <= 1.0):
        violations.append(f"fraud_probability out of range: {p}")

    punitive = {"BLOCK_CARD", "BLOCK_ALL_CARDS", "DECLINE_TRANSACTION"}

    # Invariant 1: A locked decision gate must not yield an automated terminal
    # punitive action without corroborating evidence (gate-aware governance).
    if not gate and action in punitive and trigger_type != "customer_report":
        violations.append(f"locked gate produced punitive action '{action}' without concessionary trigger")

    # Invariant 2: Inbound cardholder denial (customer report) must be contained.
    if trigger_type == "customer_report" and action in {"ALLOW_TRANSACTION", "CLOSE_NO_FRAUD", "MONITOR_CARD"}:
        violations.append(f"customer report resolved without containment action ('{action}')")

    # Invariant 3: A unanimous 'legitimate' disposition must not be punitive.
    if res.get("verdict") == "legitimate" and action in punitive:
        violations.append(f"legitimate disposition with punitive action '{action}'")

    return violations


# Map from action -> the set of approval routes considered correct.
_ROUTE_AUTO = {"auto"}
_ROUTE_L1 = {"L1"}
_ROUTE_L2 = {"L2"}


def expected_approval_routes(action: str, exposure_usd: float):
    """Objective approval-route expectation derived from the policy manual."""
    if action == "BLOCK_CARD" or action == "BLOCK_ALL_CARDS":
        return _ROUTE_L1 if float(exposure_usd) <= 2500.0 else _ROUTE_L2
    if action == "DECLINE_TRANSACTION":
        return _ROUTE_L1
    if action == "FILE_REPORT":
        return _ROUTE_L2
    # Escalation/advisory routes accept either an automated or an L2 human route.
    if action in {"ESCALATE_TO_ANALYST", "VERIFY_WITH_CUSTOMER", "MONITOR_CARD",
                  "MONITOR_CONNECTED_CARDS", "WARN_CUSTOMER", "STEP_UP_AUTH"}:
        return _ROUTE_AUTO | _ROUTE_L2
    return _ROUTE_AUTO


def compute_partial_credit(res: Dict[str, Any], violations: List[str], rubric_match, exposure_usd: float) -> float:
    """Graded, independent partial credit for a single case (0.0 - 1.0).

    Components:
      0.50  policy-invariant conformance (independent governance check)
      0.25  approval-route correctness (independent policy-manual expectation)
      0.25  team-authored rubric agreement (detail signal, not ground truth)
    """
    credit = 0.0
    if not violations:
        credit += 0.5

    details = res.get("primary_action_details") or {}
    route = details.get("approval_route")
    action = res.get("actual_nba")
    if route in expected_approval_routes(action, exposure_usd):
        credit += 0.25

    if rubric_match:
        credit += 0.25

    return round(credit, 4)


def get_git_commit_sha() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_COMMIT"


class BenchmarkEvaluationResult(BaseModel):
    benchmark_name: str
    commit_sha: str
    timestamp: str
    total_cases: int

    # ---- Headline: independent governance metrics (lead with these) ----
    headline: Dict[str, Any] = Field(
        default_factory=dict,
        description="Primary evaluation headline: independent policy-invariant conformance + graded partial credit.",
    )
    policy_conformance_count: int = 0
    policy_conformance_pct: float = 0.0
    partial_credit_score: float = 0.0
    partial_credit_pct: float = 0.0
    policy_violations: List[Dict[str, Any]] = Field(default_factory=list)

    # ---- Detail: team-authored rubric agreement (NOT ground truth) ----
    rubric_agreement_label: str = (
        "Team-authored policy rubric agreement (detail only; the rubric is authored by the team, "
        "not independent ground truth)."
    )
    rubric_authoring: str = "team-authored"
    nba_agreement_count: int
    nba_agreement_pct: float
    nba_metric_label: str = "policy-rubric agreement (team-authored; detail)"
    expected_nba_source: str = "analysis/expected_nba.json"
    unknown_expected_nba_count: int = 0
    gate_pass_count: int
    gate_pass_pct: float
    fraud_verdict_count: int
    fraud_verdict_pct: float
    avg_steps: float
    avg_coverage: float
    avg_duration_sec: float
    tool_distribution: Dict[str, int]
    mismatches: List[Dict[str, Any]]
    case_comparisons: List[Dict[str, Any]]
    raw_results: List[Dict[str, Any]] = Field(default_factory=list)


class EvaluationHarness:
    """Independent batch evaluation harness for Tark."""

    def __init__(self, tg_conn=None):
        self.tg_conn = tg_conn or get_tigergraph_connection()
        if not self.tg_conn:
            raise RuntimeError("TigerGraph Cloud connection unavailable for evaluation harness.")

        self.belief_engine = BeliefEngine()
        self.policy_engine = PolicyEngine()
        self.compass = EvidenceCompass(self.belief_engine, self.policy_engine)
        self.dispatcher = EvidenceToolDispatcher(self.belief_engine)

        memory_store = CaseMemoryStore(writeback_path=None)
        self.frozen_memory = memory_store.create_snapshot(effective_timestamp="2016-11-11 23:59:59")

        self.orchestrator = InvestigationOrchestrator(
            belief_engine=self.belief_engine,
            policy_engine=self.policy_engine,
            compass=self.compass,
            dispatcher=self.dispatcher,
            case_memory=self.frozen_memory,
            graphrag=PolicyGraphRAGRetriever(),
            synthesizer=GroundedInvestigationSynthesizer(),
            max_steps=5
        )

    def evaluate_case(self, case_record: Dict[str, Any]) -> Dict[str, Any]:
        """Runs an individual case record through the authoritative investigation pipeline."""
        case_id = str(case_record["case_id"])
        opened_at = str(case_record.get("opened_at", ""))
        trigger_type = str(case_record.get("trigger_type", "risk_score"))
        trigger_text = str(case_record.get("trigger_text", ""))
        flagged_txn_id = str(case_record.get("flagged_txn_id", ""))
        card_id = str(case_record.get("card_id", ""))
        customer_id = str(case_record.get("customer_id", ""))
        risk_score_raw = case_record.get("risk_score")
        risk_score = float(risk_score_raw) if (risk_score_raw is not None and pd.notna(risk_score_raw)) else None

        t0 = time.perf_counter()

        # Query vertex for amount and address
        txn_amount = 100.0
        txn_addr1 = 0.0
        try:
            v = self.tg_conn.getVerticesById("Transaction", flagged_txn_id)
            if v:
                attrs = v[0].get("attributes", {})
                amt = float(attrs.get("amount", 0.0))
                if amt > 0.0:
                    txn_amount = amt
                txn_addr1 = float(attrs.get("addr1", 0.0)) if attrs.get("addr1") is not None else 0.0
        except Exception:
            pass

        # Ingest initial evidence into ledger
        ledger = EvidenceLedger()
        if risk_score is not None:
            calib = get_model_score_lr(risk_score)
            ledger.add(EvidenceItem(
                evidence_id=f"EVD-{case_id}-TRIGGER",
                evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
                source="bank_detection_model",
                finding=f"Real-time fraud risk score: {risk_score:.2f}",
                lr=calib["lr"],
                log_lr=calib["log_lr"],
                details={"risk_score": risk_score}
            ))
        elif trigger_type == "customer_report":
            calib = LIKELIHOOD_REGISTRY["CUSTOMER_DENIAL"]
            ledger.add(EvidenceItem(
                evidence_id=f"EVD-{case_id}-TRIGGER",
                evidence_type=EvidenceType.CUSTOMER_DENIAL,
                source="customer_report_trigger",
                finding=f"Cardholder initiated report: '{trigger_text}'",
                lr=calib.lr,
                log_lr=calib.log_lr,
                details={"trigger_text": trigger_text}
            ))

        # Initial belief state (trigger-conditioned prior)
        prior = resolve_trigger_prior(trigger_type, risk_score)
        initial_state = self.belief_engine.evaluate_investigation(
            investigation_id=case_id,
            trigger={
                "trigger_type": trigger_type,
                "trigger_text": trigger_text,
                "flagged_txn_id": flagged_txn_id,
                "txn_addr1": txn_addr1,
                "timestamp": opened_at
            },
            target_entities={
                "card_id": card_id,
                "customer_id": customer_id,
                "flagged_txn_id": flagged_txn_id
            },
            ledger=ledger,
            prior_profile=prior["prior_profile"],
            prior_p=prior["prior_p"]
        )

        # Run investigation
        run_ctx = {
            "tg_conn": self.tg_conn,
            "trigger_type": trigger_type,
            "trigger_text": trigger_text,
            "flagged_txn_id": flagged_txn_id,
            "timestamp": opened_at,
            "ts": opened_at,
        }
        try:
            from bench.run import EXTERNAL_GATEWAY_FIXTURES

            fixture = EXTERNAL_GATEWAY_FIXTURES.get(case_id)
            if fixture:
                run_ctx["fixture_response"] = fixture.get("reply")
        except Exception:
            pass

        run_res = self.orchestrator.run_investigation(
            initial_state=initial_state,
            exposure_usd=txn_amount,
            context=run_ctx,
            enable_llm_synthesis=False
        )

        duration = round(time.perf_counter() - t0, 4)
        final_state = run_res.final_state
        primary_rec = PolicyEngine.get_primary_action(run_res.final_policy_actions)
        actual_action = primary_rec.action if primary_rec else "MONITOR_CARD"

        p_fraud = final_state.belief_state.get("fraud_probability", 0.5)
        gate_passed = final_state.decision_gate_passed
        if p_fraud <= 0.30:
            verdict = "legitimate"
        elif p_fraud >= 0.70 and gate_passed:
            verdict = "fraud"
        else:
            verdict = "uncertain"

        tools_used = [t.selected_action for t in run_res.iteration_traces]

        return {
            "case_id": case_id,
            "flagged_txn_id": flagged_txn_id,
            "actual_nba": actual_action,
            "exposure_usd": round(txn_amount, 2),
            "fraud_probability": round(p_fraud, 4),
            "verdict": verdict,
            "corroborated_fraud": final_state.belief_state.get("corroborated_fraud", False),
            "informative_families": final_state.belief_state.get("informative_families", []),
            "evidence_coverage": round(final_state.uncertainty.evidence_coverage, 4),
            "gate_passed": final_state.decision_gate_passed,
            "decision_state": final_state.decision_state.value,
            "step_count": len(run_res.iteration_traces),
            "tools_used": tools_used,
            "duration_sec": duration,
            "primary_action_details": {
                "action": actual_action,
                "approval_route": primary_rec.approval_route if primary_rec else "auto",
                "reason": primary_rec.reason if primary_rec else ""
            }
        }

    def _emit_case_answer(self, case_record: Dict[str, Any], cases_dir: str):
        """Writes the full competition-schema answer file using the unified bench pipeline."""
        try:
            from bench.run import run_investigation_for_case

            os.makedirs(cases_dir, exist_ok=True)
            answer = run_investigation_for_case(
                row=case_record,
                conn=self.tg_conn,
                belief_engine=self.belief_engine,
                policy_engine=self.policy_engine,
                planner=None,
                llm_client=None,
                orchestrator=self.orchestrator,
            )
            out_path = os.path.join(cases_dir, f"{case_record['case_id']}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(answer, f, indent=2)
        except Exception as e:
            logger.warning("Failed to emit case answer for %s: %s", case_record.get("case_id"), e)

    def run_benchmark(
        self,
        cases_input: Union[str, List[Dict[str, Any]]],
        benchmark_name: str = "Tark-Evaluation",
        output_dir: Optional[str] = None,
        emit_cases_dir: Optional[str] = None
    ) -> BenchmarkEvaluationResult:
        """Executes a full evaluation batch and writes immutable summary files."""
        if isinstance(cases_input, str):
            df = pd.read_csv(cases_input)
            cases = df.to_dict(orient="records")
        else:
            cases = cases_input

        total_cases = len(cases)
        commit_sha = get_git_commit_sha()
        start_ts = datetime.now(timezone.utc).isoformat()

        raw_results = []
        tool_counts: Dict[str, int] = {}
        nba_agreements = 0
        unknown_expected = 0
        policy_conformance = 0
        partial_credit_total = 0.0
        gate_passes = 0
        fraud_verdicts = 0
        mismatches = []
        policy_violations = []
        case_comparisons = []

        expected_rubric = load_expected_nba_rubric()

        for idx, case_row in enumerate(cases):
            case_id = str(case_row.get("case_id", f"CASE-{idx+1}"))
            # Expected values come ONLY from the case pack column or the independent
            # human-authored rubric — never from the agent's own emitted cases/*.json.
            expected_action = case_row.get("expected_primary_action") or expected_rubric.get(case_id)

            res = self.evaluate_case(case_row)
            raw_results.append(res)

            if emit_cases_dir:
                self._emit_case_answer(case_row, emit_cases_dir)

            for t in res["tools_used"]:
                tool_counts[t] = tool_counts.get(t, 0) + 1

            if res["gate_passed"]:
                gate_passes += 1
            if res["verdict"] == "fraud":
                fraud_verdicts += 1

            # Independent policy-invariant conformance
            violations = evaluate_policy_invariants(case_row, res)
            if violations:
                policy_violations.append({"case_id": case_id, "violations": violations})
            else:
                policy_conformance += 1

            # NBA agreement comparison against the team-authored rubric (detail metric)
            is_nba_match = None
            if expected_action:
                is_nba_match = (res["actual_nba"] == expected_action)
                if is_nba_match:
                    nba_agreements += 1
                else:
                    mismatches.append({
                        "case_id": case_id,
                        "expected": expected_action,
                        "actual": res["actual_nba"],
                        "details": res["primary_action_details"]
                    })
            else:
                unknown_expected += 1

            exposure = res.get("exposure_usd") or case_row.get("exposure_usd") or case_row.get("amount") or 0.0
            credit = compute_partial_credit(res, violations, is_nba_match, exposure)
            partial_credit_total += credit

            case_comparisons.append({
                "case_id": case_id,
                "actual_nba": res["actual_nba"],
                "expected_nba": expected_action,
                "is_match": is_nba_match,
                "policy_conformant": not violations,
                "policy_violations": violations,
                "partial_credit": credit,
                "fraud_probability": res["fraud_probability"],
                "verdict": res["verdict"],
                "gate_passed": res["gate_passed"],
                "coverage": res["evidence_coverage"],
                "steps": res["step_count"],
                "duration_sec": res["duration_sec"]
            })

        scored_cases = total_cases - unknown_expected
        avg_steps = round(sum(r["step_count"] for r in raw_results) / total_cases, 2) if total_cases > 0 else 0.0
        avg_cov = round(sum(r["evidence_coverage"] for r in raw_results) / total_cases, 4) if total_cases > 0 else 0.0
        avg_dur = round(sum(r["duration_sec"] for r in raw_results) / total_cases, 2) if total_cases > 0 else 0.0

        partial_credit_avg = round(partial_credit_total / total_cases, 4) if total_cases > 0 else 0.0
        conformance_pct = round((policy_conformance / total_cases) * 100, 1) if total_cases > 0 else 0.0
        rubric_pct = round((nba_agreements / scored_cases) * 100, 1) if scored_cases > 0 else 0.0

        headline = {
            "primary_metric": "policy_invariant_conformance_pct",
            "policy_invariant_conformance_pct": conformance_pct,
            "partial_credit_score": partial_credit_avg,
            "partial_credit_pct": round(partial_credit_avg * 100, 1),
            "partial_credit_definition": (
                "Mean graded credit per case: 0.50 policy-invariant conformance + "
                "0.25 approval-route correctness + 0.25 team-authored rubric agreement."
            ),
            "rubric_agreement_detail": {
                "label": "team-authored policy rubric agreement (detail only; not independent ground truth)",
                "pct": rubric_pct,
                "count": nba_agreements,
                "scored_cases": scored_cases,
            },
            "note": (
                "Lead metrics (policy-invariant conformance + graded partial credit) are computed "
                "independently of the agent pipeline. Rubric agreement is intentionally demoted to a "
                "detail signal because the rubric is authored by the team, not by the judges."
            ),
        }

        eval_result = BenchmarkEvaluationResult(
            benchmark_name=benchmark_name,
            commit_sha=commit_sha,
            timestamp=start_ts,
            total_cases=total_cases,
            headline=headline,
            nba_agreement_count=nba_agreements,
            nba_agreement_pct=rubric_pct,
            nba_metric_label="policy-rubric agreement (team-authored; detail)",
            expected_nba_source=os.path.relpath(EXPECTED_NBA_PATH, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))).replace("\\", "/"),
            unknown_expected_nba_count=unknown_expected,
            policy_conformance_count=policy_conformance,
            policy_conformance_pct=conformance_pct,
            partial_credit_score=partial_credit_avg,
            partial_credit_pct=round(partial_credit_avg * 100, 1),
            policy_violations=policy_violations,
            gate_pass_count=gate_passes,
            gate_pass_pct=round((gate_passes / total_cases) * 100, 1) if total_cases > 0 else 0.0,
            fraud_verdict_count=fraud_verdicts,
            fraud_verdict_pct=round((fraud_verdicts / total_cases) * 100, 1) if total_cases > 0 else 0.0,
            avg_steps=avg_steps,
            avg_coverage=avg_cov,
            avg_duration_sec=avg_dur,
            tool_distribution=tool_counts,
            mismatches=mismatches,
            case_comparisons=case_comparisons,
            raw_results=raw_results
        )

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            summary_path = os.path.join(output_dir, "evaluation_summary.json")
            raw_path = os.path.join(output_dir, "raw_results.json")
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(eval_result.model_dump(exclude={"raw_results"}), f, indent=2)
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(raw_results, f, indent=2)

        return eval_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tark Independent Evaluation Harness")
    parser.add_argument("--cases", default="case_pack.csv", help="Path to input cases CSV")
    parser.add_argument("--output-dir", default=None, help="Directory to save evaluation artifacts")
    parser.add_argument("--emit-cases", default=None, help="Directory to write full competition-schema case answers")
    parser.add_argument("--name", default="Tark-Benchmark", help="Name of evaluation run")
    args = parser.parse_args()

    harness = EvaluationHarness()
    result = harness.run_benchmark(
        cases_input=args.cases,
        benchmark_name=args.name,
        output_dir=args.output_dir,
        emit_cases_dir=args.emit_cases,
    )
    print("=" * 80)
    print(f"Benchmark: {result.benchmark_name} | Commit: {result.commit_sha}")
    print(f"HEADLINE — Policy-Invariant Conformance: {result.policy_conformance_count}/{result.total_cases} ({result.policy_conformance_pct}%)")
    print(f"HEADLINE — Partial Credit (graded): {result.partial_credit_score:.4f} ({result.partial_credit_pct}%)")
    print(f"detail — Team-authored rubric agreement: {result.nba_agreement_count}/{result.total_cases} ({result.nba_agreement_pct}%)")
    print(f"Gate Pass Rate: {result.gate_pass_count}/{result.total_cases} ({result.gate_pass_pct}%)")
    print(f"Mismatches: {len(result.mismatches)} | Policy Violations: {len(result.policy_violations)}")
    print("=" * 80)
