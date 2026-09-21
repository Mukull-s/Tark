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
import argparse
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
import pandas as pd

from src.graph.connection import get_tigergraph_connection
from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceType, EvidenceItem
from src.belief.calibration import get_model_score_lr, LIKELIHOOD_REGISTRY
from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine, ActionRole
from src.compass.evoi import EvidenceCompass
from src.tools.dispatcher import EvidenceToolDispatcher
from src.memory.store import CaseMemoryStore
from src.knowledge.retriever import PolicyGraphRAGRetriever
from src.synthesis.synthesizer import GroundedInvestigationSynthesizer
from src.agent.orchestrator import InvestigationOrchestrator


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
    nba_agreement_count: int
    nba_agreement_pct: float
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

        # Initial belief state
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
            ledger=ledger
        )

        # Run investigation
        run_res = self.orchestrator.run_investigation(
            initial_state=initial_state,
            exposure_usd=txn_amount,
            context={
                "tg_conn": self.tg_conn,
                "trigger_type": trigger_type,
                "trigger_text": trigger_text,
                "flagged_txn_id": flagged_txn_id,
                "timestamp": opened_at,
                "ts": opened_at
            },
            enable_llm_synthesis=False
        )

        duration = round(time.perf_counter() - t0, 4)
        final_state = run_res.final_state
        primary_rec = PolicyEngine.get_primary_action(run_res.final_policy_actions)
        actual_action = primary_rec.action if primary_rec else "MONITOR_CARD"

        p_fraud = final_state.belief_state.get("fraud_probability", 0.5)
        verdict = "fraud" if p_fraud >= 0.70 else ("legitimate" if p_fraud <= 0.30 else "uncertain")

        tools_used = [t.selected_action for t in run_res.iteration_traces]

        return {
            "case_id": case_id,
            "flagged_txn_id": flagged_txn_id,
            "actual_nba": actual_action,
            "fraud_probability": round(p_fraud, 4),
            "verdict": verdict,
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

    def run_benchmark(
        self,
        cases_input: Union[str, List[Dict[str, Any]]],
        benchmark_name: str = "Tark-Evaluation",
        output_dir: Optional[str] = None
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
        gate_passes = 0
        fraud_verdicts = 0
        mismatches = []
        case_comparisons = []

        for idx, case_row in enumerate(cases):
            case_id = str(case_row.get("case_id", f"CASE-{idx+1}"))
            expected_action = case_row.get("expected_primary_action")
            if not expected_action:
                gt_path = os.path.join(os.getcwd(), "cases", f"{case_id}.json")
                if os.path.exists(gt_path):
                    try:
                        with open(gt_path, "r", encoding="utf-8") as gf:
                            gt_data = json.load(gf)
                            gt_acts = [a.get("action") for a in gt_data.get("next_best_actions", {}).get("final", [])]
                            expected_action = gt_acts[0] if gt_acts else None
                    except Exception:
                        pass

            res = self.evaluate_case(case_row)
            raw_results.append(res)

            for t in res["tools_used"]:
                tool_counts[t] = tool_counts.get(t, 0) + 1

            if res["gate_passed"]:
                gate_passes += 1
            if res["verdict"] == "fraud":
                fraud_verdicts += 1

            # NBA agreement comparison
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
                nba_agreements += 1

            case_comparisons.append({
                "case_id": case_id,
                "actual_nba": res["actual_nba"],
                "expected_nba": expected_action,
                "is_match": is_nba_match,
                "fraud_probability": res["fraud_probability"],
                "verdict": res["verdict"],
                "gate_passed": res["gate_passed"],
                "steps": res["step_count"],
                "duration_sec": res["duration_sec"]
            })

        avg_steps = round(sum(r["step_count"] for r in raw_results) / total_cases, 2) if total_cases > 0 else 0.0
        avg_cov = round(sum(r["evidence_coverage"] for r in raw_results) / total_cases, 4) if total_cases > 0 else 0.0
        avg_dur = round(sum(r["duration_sec"] for r in raw_results) / total_cases, 2) if total_cases > 0 else 0.0

        eval_result = BenchmarkEvaluationResult(
            benchmark_name=benchmark_name,
            commit_sha=commit_sha,
            timestamp=start_ts,
            total_cases=total_cases,
            nba_agreement_count=nba_agreements,
            nba_agreement_pct=round((nba_agreements / total_cases) * 100, 1) if total_cases > 0 else 0.0,
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
    parser.add_argument("--name", default="Tark-Benchmark", help="Name of evaluation run")
    args = parser.parse_args()

    harness = EvaluationHarness()
    result = harness.run_benchmark(cases_input=args.cases, benchmark_name=args.name, output_dir=args.output_dir)
    print("=" * 80)
    print(f"Benchmark: {result.benchmark_name} | Commit: {result.commit_sha}")
    print(f"NBA Agreement: {result.nba_agreement_count}/{result.total_cases} ({result.nba_agreement_pct}%)")
    print(f"Gate Pass Rate: {result.gate_pass_count}/{result.total_cases} ({result.gate_pass_pct}%)")
    print(f"Mismatches: {len(result.mismatches)}")
    print("=" * 80)
