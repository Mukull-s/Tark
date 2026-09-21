import os
import sys
import re
import json
import time
import subprocess
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

load_dotenv(os.path.join(WORKSPACE_ROOT, ".env"))

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


def get_git_commit_sha():
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=WORKSPACE_ROOT)
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_COMMIT"


def run_benchmark(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    commit_sha = get_git_commit_sha()
    start_ts = datetime.now(timezone.utc).isoformat()

    print("=" * 80)
    print("TARK — FRESH BENCHMARK EXECUTION (ZERO ASSUMED OUTCOMES)")
    print("=" * 80)
    print(f"Commit SHA: {commit_sha}")
    print(f"Timestamp:  {start_ts}")
    print(f"Output Dir: {output_dir}")

    # 1. Connect to TigerGraph
    print("\n[1/5] Connecting to TigerGraph Cloud...")
    tg_conn = get_tigergraph_connection()
    if not tg_conn:
        raise RuntimeError("Failed to establish TigerGraph connection!")
    print("TigerGraph connection verified.")

    # 2. Initialize reasoning authorities
    print("\n[2/5] Initializing reasoning authorities...")
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    compass = EvidenceCompass(belief_engine, policy_engine)
    dispatcher = EvidenceToolDispatcher(belief_engine)

    # 3. Memory snapshot
    memory_store = CaseMemoryStore(writeback_path=None)
    frozen_memory = memory_store.create_snapshot(effective_timestamp="2016-11-11 23:59:59")
    initial_memory_count = frozen_memory.count()
    print(f"Frozen memory snapshot initialized with {initial_memory_count} cases.")

    # 4. Orchestrator
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        case_memory=frozen_memory,
        graphrag=PolicyGraphRAGRetriever(),
        synthesizer=GroundedInvestigationSynthesizer(),
        max_steps=5
    )

    # 5. Load cases
    csv_path = os.path.join(WORKSPACE_ROOT, "case_pack.csv")
    df = pd.read_csv(csv_path)
    total_cases = len(df)
    print(f"\n[3/5] Executing {total_cases} cases against live TigerGraph...")

    raw_results = []
    tool_counts = {}

    for idx, row in df.iterrows():
        case_id = str(row["case_id"])
        opened_at = str(row["opened_at"])
        trigger_type = str(row["trigger_type"])
        trigger_text = str(row["trigger_text"])
        flagged_txn_id = str(row["flagged_txn_id"])
        card_id = str(row["card_id"])
        customer_id = str(row["customer_id"])
        risk_score_raw = row["risk_score"]
        risk_score = float(risk_score_raw) if pd.notna(risk_score_raw) else None

        t0 = time.perf_counter()

        # Vertex lookup
        txn_attrs = {}
        try:
            flagged_txn_v = tg_conn.getVerticesById("Transaction", flagged_txn_id)
            if flagged_txn_v:
                txn_attrs = flagged_txn_v[0].get("attributes", {})
        except Exception as e:
            print(f"  Warning: Vertex lookup failed for {flagged_txn_id}: {e}")

        txn_amount = float(txn_attrs.get("amount", 0.0))
        if txn_amount <= 0.0:
            amt_match = re.search(r"\$([0-9,]+\.?[0-9]*)", trigger_text)
            txn_amount = float(amt_match.group(1).replace(",", "")) if amt_match else 100.0

        txn_addr1 = float(txn_attrs.get("addr1", 0.0)) if txn_attrs.get("addr1") is not None else 0.0

        # Trigger evidence
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

        initial_state = belief_engine.evaluate_investigation(
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

        initial_p_fraud = initial_state.belief_state.get("fraud_probability", 0.5)

        run_result = orchestrator.run_investigation(
            initial_state=initial_state,
            exposure_usd=txn_amount,
            context={"tg_conn": tg_conn},
            enable_llm_synthesis=False
        )

        duration = round(time.perf_counter() - t0, 4)

        # Contamination assert
        assert frozen_memory.count() == initial_memory_count, "Memory mutation detected!"

        final_state = run_result.final_state
        final_p_fraud = final_state.belief_state.get("fraud_probability", 0.5)
        final_cov = final_state.uncertainty.evidence_coverage
        final_classification = "fraud" if final_p_fraud >= 0.70 else ("legitimate" if final_p_fraud <= 0.30 else "uncertain")

        primary_rec = PolicyEngine.get_primary_action(run_result.final_policy_actions)
        primary_action = primary_rec.action if primary_rec else "MONITOR_CARD"
        approval_route = primary_rec.approval_route if primary_rec else "auto"

        for t in run_result.iteration_traces:
            act = t.selected_action
            tool_counts[act] = tool_counts.get(act, 0) + 1

        case_record = {
            "case_id": case_id,
            "flagged_txn_id": flagged_txn_id,
            "trigger_type": trigger_type,
            "exposure_usd": txn_amount,
            "initial_p_fraud": round(initial_p_fraud, 4),
            "final_p_fraud": round(final_p_fraud, 4),
            "final_classification": final_classification,
            "evidence_steps": run_result.total_steps,
            "evidence_coverage": round(final_cov, 4),
            "decision_gate_passed": final_state.decision_gate_passed,
            "decision_state": final_state.decision_state.value,
            "termination_reason": run_result.termination_reason.value,
            "primary_action": primary_action,
            "approval_route": approval_route,
            "policy_actions": [a.action for a in run_result.final_policy_actions],
            "evidence_items_count": len(final_state.evidence_items),
            "duration_sec": duration
        }
        raw_results.append(case_record)
        print(f"[{idx+1:02d}/{total_cases}] {case_id}: Steps={run_result.total_steps} | Gate={str(final_state.decision_gate_passed):<5} | P(Fraud)={final_p_fraud:.4f} | Action={primary_action:<20} | Time={duration:.2f}s")

    # Save raw results
    raw_path = os.path.join(output_dir, "raw_results.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=2)
    print(f"\n[4/5] Saved raw results to {raw_path}")

    # 6. Evaluate independently against ground truth
    print("\n[5/5] Evaluating results against case ground truths...")
    nba_agreements = 0
    gate_passes = 0
    fraud_verdicts = 0
    mismatches = []
    case_comparisons = []

    for r in raw_results:
        cid = r["case_id"]
        gt_path = os.path.join(WORKSPACE_ROOT, "cases", f"{cid}.json")
        gt_nba = "UNKNOWN"
        gt_verdict = "UNKNOWN"
        if os.path.exists(gt_path):
            with open(gt_path, "r", encoding="utf-8") as f:
                gt = json.load(f)
                gt_actions = [a.get("action") for a in gt.get("next_best_actions", {}).get("final", [])]
                gt_nba = gt_actions[0] if gt_actions else "NONE"
                gt_verdict = gt.get("case", {}).get("verdict", "unknown")

        nba_match = (r["primary_action"] == gt_nba)
        if nba_match:
            nba_agreements += 1
        else:
            mismatches.append({
                "case_id": cid,
                "actual_primary_action": r["primary_action"],
                "expected_primary_action": gt_nba,
                "final_p_fraud": r["final_p_fraud"],
                "decision_gate_passed": r["decision_gate_passed"],
                "termination_reason": r["termination_reason"]
            })

        if r["decision_gate_passed"]:
            gate_passes += 1
        if r["final_classification"] == "fraud":
            fraud_verdicts += 1

        case_comparisons.append({
            "case_id": cid,
            "actual_nba": r["primary_action"],
            "expected_nba": gt_nba,
            "nba_match": nba_match,
            "gate_passed": r["decision_gate_passed"],
            "final_p_fraud": r["final_p_fraud"],
            "steps": r["evidence_steps"],
            "coverage": r["evidence_coverage"],
            "duration_sec": r["duration_sec"]
        })

    eval_summary = {
        "benchmark_run_id": f"BENCH-{commit_sha[:8]}-{int(time.time())}",
        "commit_sha": commit_sha,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cases": total_cases,
        "nba_agreement_count": nba_agreements,
        "nba_agreement_pct": round(nba_agreements / total_cases * 100, 2),
        "gate_pass_count": gate_passes,
        "gate_pass_pct": round(gate_passes / total_cases * 100, 2),
        "fraud_verdict_count": fraud_verdicts,
        "fraud_verdict_pct": round(fraud_verdicts / total_cases * 100, 2),
        "avg_steps": round(sum(r["evidence_steps"] for r in raw_results) / total_cases, 2),
        "avg_coverage": round(sum(r["evidence_coverage"] for r in raw_results) / total_cases, 4),
        "avg_duration_sec": round(sum(r["duration_sec"] for r in raw_results) / total_cases, 2),
        "tool_distribution": tool_counts,
        "mismatches": mismatches,
        "case_comparisons": case_comparisons
    }

    summary_path = os.path.join(output_dir, "evaluation_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)

    print(f"Saved evaluation summary to {summary_path}")
    print("-" * 80)
    print(f"NBA Agreement:      {nba_agreements}/{total_cases} ({eval_summary['nba_agreement_pct']}%)")
    print(f"Decision Gate Pass: {gate_passes}/{total_cases} ({eval_summary['gate_pass_pct']}%)")
    print(f"Fraud Class:        {fraud_verdicts}/{total_cases} ({eval_summary['fraud_verdict_pct']}%)")
    print(f"Mismatches:         {len(mismatches)}")
    if mismatches:
        for m in mismatches:
            print(f"  * {m['case_id']}: Actual={m['actual_primary_action']} vs Expected={m['expected_primary_action']}")
    print("=" * 80)
    return eval_summary


if __name__ == "__main__":
    target_dir = os.path.join(WORKSPACE_ROOT, "analysis", "baseline_before_hardening")
    run_benchmark(target_dir)
