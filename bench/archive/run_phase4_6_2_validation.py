import os
import sys
import re
import json
import time
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


def run_phase4_6_2_validation():
    print("=" * 80)
    print("TARK — PHASE 4.6.2: 20-CASE BENCHMARK VALIDATION EXECUTION")
    print("=" * 80)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Workspace: {WORKSPACE_ROOT}")

    # 1. Live TigerGraph connection
    print("\n[Step 1] Connecting to TigerGraph...")
    tg_conn = get_tigergraph_connection()
    print("TigerGraph connection established.")

    # 2. Reasoning and policy authorities
    print("\n[Step 2] Initializing investigation authorities...")
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    compass = EvidenceCompass(belief_engine, policy_engine)
    dispatcher = EvidenceToolDispatcher(belief_engine)

    # 3. Create frozen historical memory snapshot
    print("\n[Step 3] Freezing historical case memory snapshot...")
    memory_store = CaseMemoryStore(writeback_path=None)
    frozen_memory = memory_store.create_snapshot(effective_timestamp="2016-11-11 23:59:59")
    print(f"Frozen snapshot created with {frozen_memory.count()} historical cases. is_frozen={frozen_memory.is_frozen}")

    # 4. GraphRAG and Synthesizer
    graphrag = PolicyGraphRAGRetriever()
    synthesizer = GroundedInvestigationSynthesizer()

    # 5. Autonomous Investigation Orchestrator
    orchestrator = InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=compass,
        dispatcher=dispatcher,
        case_memory=frozen_memory,
        graphrag=graphrag,
        synthesizer=synthesizer,
        max_steps=5
    )
    print("InvestigationOrchestrator configured (max_steps=5, failure_limit=2).")

    # 6. Load Benchmark Input Dataset
    csv_path = os.path.join(WORKSPACE_ROOT, "case_pack.csv")
    print(f"\n[Step 4] Loading benchmark cases from {csv_path}...")
    df = pd.read_csv(csv_path)
    total_cases = len(df)
    print(f"Loaded {total_cases} benchmark cases.")

    raw_results = []
    initial_memory_count = frozen_memory.count()

    print("\n[Step 5] Executing 20 cases sequentially through production pipeline...")
    print("-" * 80)

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

        print(f"\n[{idx+1}/{total_cases}] Running case {case_id} (Trigger: {trigger_type}, Txn: {flagged_txn_id})...")
        case_start_time = time.perf_counter()

        # Step 5a: Fetch transaction vertex from TigerGraph
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

        # Step 5b: Ingest initial trigger evidence
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

        # Step 5c: Form initial InvestigationState
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

        # Step 5d: Run investigation through standard orchestrator
        run_result = orchestrator.run_investigation(
            initial_state=initial_state,
            exposure_usd=txn_amount,
            context={"tg_conn": tg_conn},
            enable_llm_synthesis=False
        )
        case_duration = round(time.perf_counter() - case_start_time, 4)

        # Verify zero memory writeback occurred
        assert frozen_memory.count() == initial_memory_count, "Memory contamination detected: frozen memory count changed!"

        final_state = run_result.final_state
        final_p_fraud = final_state.belief_state.get("fraud_probability", 0.5)
        final_cov = final_state.uncertainty.evidence_coverage
        final_classification = "fraud" if final_p_fraud >= 0.70 else ("legitimate" if final_p_fraud <= 0.30 else "uncertain")

        primary_rec = PolicyEngine.get_primary_action(run_result.final_policy_actions)
        primary_action = primary_rec.action if primary_rec else "MONITOR_CARD"
        approval_route = primary_rec.approval_route if primary_rec else "auto"
        primary_reason = primary_rec.reason if primary_rec else "Default monitoring"

        secondary_actions = [
            a.action for a in run_result.final_policy_actions if a.role == ActionRole.SECONDARY
        ]
        consequential_actions = [
            a.action for a in run_result.final_policy_actions if a.role == ActionRole.CONSEQUENTIAL
        ]

        iteration_summaries = []
        for t in run_result.iteration_traces:
            iteration_summaries.append({
                "iteration": t.iteration,
                "selected_action": t.selected_action,
                "candidate_net_decision_values": t.candidate_net_decision_values,
                "belief_before": t.belief_before,
                "belief_after": t.belief_after,
                "coverage_before": t.coverage_before,
                "coverage_after": t.coverage_after,
                "evidence_observed": t.observed_evidence_summary,
                "termination_check": t.termination_check,
                "termination_reason": t.termination_reason.value if t.termination_reason else None
            })

        evidence_items_summary = []
        for item in final_state.evidence_items:
            evidence_items_summary.append({
                "evidence_id": item.evidence_id,
                "evidence_type": item.evidence_type.value,
                "lr": item.lr,
                "log_lr": item.log_lr,
                "finding": item.finding,
                "source": item.source,
                "is_exculpatory": item.is_exculpatory
            })

        precedents_summary = []
        for p in run_result.retrieved_precedents:
            precedents_summary.append({
                "case_id": p.case_record.case_id,
                "similarity_score": p.similarity_score,
                "matching_features": p.matching_features,
                "historical_timestamp": p.historical_timestamp,
                "eligibility_reason": p.eligibility_reason,
                "role": p.role
            })

        knowledge_summary = []
        for k in run_result.retrieved_knowledge:
            knowledge_summary.append({
                "chunk_id": k.chunk.chunk_id,
                "category": k.chunk.category.value if hasattr(k.chunk.category, "value") else str(k.chunk.category),
                "relevance_score": k.relevance_score,
                "match_rationale": k.match_rationale,
                "applicable_statute_or_rule": k.applicable_statute_or_rule
            })

        case_record = {
            "case_id": case_id,
            "opened_at": opened_at,
            "trigger_type": trigger_type,
            "trigger_text": trigger_text,
            "flagged_txn_id": flagged_txn_id,
            "card_id": card_id,
            "customer_id": customer_id,
            "risk_score": risk_score,
            "exposure_usd": txn_amount,
            "initial_p_fraud": round(initial_p_fraud, 4),
            "final_p_fraud": round(final_p_fraud, 4),
            "final_classification": final_classification,
            "evidence_steps": run_result.total_steps,
            "evidence_coverage": round(final_cov, 4),
            "decision_gate_passed": final_state.decision_gate_passed,
            "decision_state": final_state.decision_state.value,
            "termination_reason": run_result.termination_reason.value,
            "next_best_action": primary_action,
            "primary_action": primary_action,
            "secondary_actions": secondary_actions,
            "consequential_actions": consequential_actions,
            "policy_actions": [a.action for a in run_result.final_policy_actions],
            "action_recommendations": [
                {
                    "action": a.action,
                    "approval_route": a.approval_route,
                    "reason": a.reason,
                    "role": a.role.value if hasattr(a.role, "value") else str(a.role),
                    "scope": a.scope.value if hasattr(a.scope, "value") and a.scope else (str(a.scope) if a.scope else None)
                }
                for a in run_result.final_policy_actions
            ],
            "approval_route": approval_route,
            "policy_reason": primary_reason,
            "iteration_traces": iteration_summaries,
            "evidence_items": evidence_items_summary,
            "retrieved_precedents": precedents_summary,
            "retrieved_knowledge": knowledge_summary,
            "duration_sec": case_duration,
            "investigation_status": "COMPLETED",
            "error": None
        }

        raw_results.append(case_record)
        print(f"  Result: Steps={run_result.total_steps}, Term={run_result.termination_reason.value}, Gate={final_state.decision_gate_passed}, P(Fraud)={final_p_fraud:.4f}, PrimaryAction={primary_action}, Time={case_duration}s")

    # 6. Save raw results to analysis/phase4.6.2_validation_raw_results.json
    out_dir = os.path.join(WORKSPACE_ROOT, "analysis")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "phase4.6.2_validation_raw_results.json")

    print(f"\n[Step 6] Saving complete raw validation results to {out_path}...")
    with open(out_path, mode="w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=2)

    print(f"Saved {len(raw_results)} case results successfully.")
    print("=" * 80)
    print("PHASE 4.6.2 BENCHMARK RUN COMPLETE.")
    print("=" * 80)
    return raw_results


if __name__ == "__main__":
    run_phase4_6_2_validation()
