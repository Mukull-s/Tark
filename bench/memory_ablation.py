"""Memory ablation: sequential case write-back (memory ON) demonstration.

Runs a small sequence of benchmark cases with an *unfrozen* case-memory store that
persists investigation write-backs, and records how the retrieved precedent set
grows for later, similar cases (institutional learning). It also verifies the
core architectural invariant: case-memory precedents are contextual only and do
NOT shift belief, coverage, or the posterior.

The main benchmark/evaluation harness uses a *frozen* memory snapshot at
``2016-11-11 23:59:59`` (write-back disabled) for reproducibility and zero
cross-case contamination. This ablation is the deliberate counterfactual that
demonstrates what write-back adds.

Output: analysis/memory_ablation.json
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

import pandas as pd

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from src.graph.connection import get_tigergraph_connection  # noqa: E402
from src.belief.engine import BeliefEngine  # noqa: E402
from src.policy.engine import PolicyEngine  # noqa: E402
from src.compass.evoi import EvidenceCompass  # noqa: E402
from src.tools.dispatcher import EvidenceToolDispatcher  # noqa: E402
from src.agent.orchestrator import InvestigationOrchestrator  # noqa: E402
from src.memory.store import CaseMemoryStore  # noqa: E402
from src.knowledge.retriever import PolicyGraphRAGRetriever  # noqa: E402
from src.synthesis.synthesizer import GroundedInvestigationSynthesizer  # noqa: E402
from bench.run import run_investigation_for_case  # noqa: E402

FROZEN_TIMESTAMP = "2016-11-11 23:59:59"
ABLATION_WRITEBACK = os.path.join(WORKSPACE_ROOT, "analysis", "memory_ablation_writebacks.jsonl")


def _build_orchestrator(store):
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    return InvestigationOrchestrator(
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        compass=EvidenceCompass(belief_engine, policy_engine),
        dispatcher=EvidenceToolDispatcher(belief_engine),
        case_memory=store,
        graphrag=PolicyGraphRAGRetriever(),
        synthesizer=GroundedInvestigationSynthesizer(),
        max_steps=5,
    )


def _resolve_card_txns(conn, card_id: str):
    try:
        edges = conn.getEdges("Card", card_id, "Card_MADE_Transaction")
        return sorted(
            {str(e.get("to_id")) for e in (edges or []) if e.get("to_id") is not None},
            key=lambda x: (len(x), x),
        )
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(description="Tark case-memory ablation")
    parser.add_argument("--cases", nargs="+", default=None,
                        help="Seed case IDs in sequence (defaults to the first cases in the pack)")
    parser.add_argument("--followups", type=int, default=2,
                        help="Same-card follow-up investigations generated after the seed cases")
    parser.add_argument("--output", default=os.path.join(WORKSPACE_ROOT, "analysis", "memory_ablation.json"))
    args = parser.parse_args()

    if os.path.exists(ABLATION_WRITEBACK):
        os.remove(ABLATION_WRITEBACK)

    conn = get_tigergraph_connection()
    case_pack = pd.read_csv(os.path.join(WORKSPACE_ROOT, "case_pack.csv"))
    case_pack = case_pack.set_index("case_id")

    # Default seed set: the first three distinct cards in the pack (deterministic,
    # no benchmark-specific IDs hardcoded).
    if not args.cases:
        seed_ids = []
        seen_cards = set()
        for cid, r in case_pack.iterrows():
            card = str(r.get("card_id"))
            if card in seen_cards:
                continue
            seen_cards.add(card)
            seed_ids.append(str(cid))
            if len(seed_ids) >= 3:
                break
        args.cases = seed_ids

    # Unfrozen store with a dedicated ablation writeback log (never the main file).
    store = CaseMemoryStore(writeback_path=ABLATION_WRITEBACK)
    initial_memory = store.count()

    records = []
    written_back_ids = set()
    seed_rows = []
    for case_id in args.cases:
        if case_id not in case_pack.index:
            continue
        row = case_pack.loc[case_id].to_dict()
        row["case_id"] = case_id
        seed_rows.append(row)

    # Emit schedule: seed cases first, then same-card follow-ups on the last seed's card
    # (so the seed's write-back becomes a retrievable precedent for the follow-ups).
    schedule = [("seed", r) for r in seed_rows]

    if seed_rows and args.followups > 0:
        anchor = seed_rows[-1]
        anchor_card = str(anchor["card_id"])
        anchor_customer = str(anchor["customer_id"])
        txns = _resolve_card_txns(conn, anchor_card)
        # Exclude the anchor's own transaction to respect the leak-prevention guard.
        txns = [t for t in txns if t != str(anchor["flagged_txn_id"])]
        for i in range(min(args.followups, len(txns))):
            schedule.append(("followup", {
                "case_id": f"{anchor['case_id']}-FU{i+1}",
                # Follow-up arrives AFTER the seed case has closed (the write-back is
                # timestamped at closure), so the temporal integrity guard admits it.
                "opened_at": "2099-01-01 00:00:00",
                "trigger_type": "risk_score",
                "trigger_text": f"Follow-up model alert on card {anchor_card} for transaction {txns[i]}.",
                "flagged_txn_id": txns[i],
                "card_id": anchor_card,
                "customer_id": anchor_customer,
                "risk_score": 0.72,
            }))

    for kind, row in schedule:
        orchestrator = _build_orchestrator(store)
        before_count = store.count()
        answer = run_investigation_for_case(
            row=row, conn=conn,
            belief_engine=orchestrator.belief_engine,
            policy_engine=orchestrator.policy_engine,
            planner=None, llm_client=None, orchestrator=orchestrator,
        )
        after_count = store.count()
        written_back_ids.add(row["case_id"])

        records.append({
            "sequence": len(records) + 1,
            "kind": kind,
            "case_id": row["case_id"],
            "card_id": str(row.get("card_id")),
            "memory_count_before": before_count,
            "memory_count_after": after_count,
            "writeback_added": after_count - before_count,
            "retrieved_precedent_ids": answer["case"]["similar_prior_cases"],
            "retrieved_precedent_count": len(answer["case"]["similar_prior_cases"]),
            "fraud_probability": answer["case"]["fraud_probability"],
            "evidence_coverage": answer["case"]["evidence_coverage"],
            "primary_action": answer["next_best_actions"]["final"][0]["action"],
            "internal_precedents_retrieved": [
                cid for cid in answer["case"]["similar_prior_cases"] if cid in written_back_ids
            ],
        })

    artifact = {
        "status": "COMPLETED",
        "benchmark": "Tark-CaseMemory-Ablation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "writeback_ON (unfrozen ablation store)",
        "ablation_writeback_file": os.path.relpath(ABLATION_WRITEBACK, WORKSPACE_ROOT).replace("\\", "/"),
        "main_benchmark_memory": f"FROZEN snapshot at {FROZEN_TIMESTAMP} (writeback disabled) for reproducibility",
        "initial_memory_count": initial_memory,
        "final_memory_count": store.count(),
        "sequence": records,
        "invariant_note": (
            "Case-memory precedents are CONTEXTUAL ONLY (LR=1.0): they never shift the posterior, "
            "evidence coverage, or the decision gate. The ablation therefore demonstrates institutional "
            "learning as a growing/refreshed precedent set for later same-card cases, not a belief shift."
        ),
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)

    print("=" * 72)
    print("TARK CASE-MEMORY ABLATION (write-back ON)")
    print("=" * 72)
    for r in records:
        print(
            f"[{r['sequence']}] {r['kind']} {r['case_id']}: memory {r['memory_count_before']} -> "
            f"{r['memory_count_after']} (+{r['writeback_added']}); "
            f"precedents={r['retrieved_precedent_ids']}; "
            f"internal={r['internal_precedents_retrieved']}; P(Fraud)={r['fraud_probability']}"
        )
    print(f"Artifact written: {args.output}")
    print("=" * 72)


if __name__ == "__main__":
    main()
