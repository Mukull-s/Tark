"""Integration tests for vector retrieval, evidence request tracking,
R6-syndicate policy routing, and independent next-best-action evaluation.
"""

import json
import pathlib

import pytest

from src.evidence.types import EvidenceItem, EvidenceType
from src.evidence.ledger import EvidenceLedger
from src.belief.engine import BeliefEngine
from src.belief.calibration import PriorProfile
from src.policy.engine import PolicyEngine
from src.tools.dispatcher import EvidenceToolDispatcher
from src.knowledge.vector_index import HashingVectorIndex, get_default_vector_index
from src.knowledge.store import InvestigationKnowledgeBase

from bench.run import _serialize_evidence_requests, _attempt_external_resolution
from evaluation.harness import evaluate_policy_invariants, load_expected_nba_rubric
from src.api.main import _build_graph_from_run

WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fix 1: evidence requests
# ---------------------------------------------------------------------------

def _gateway_item(evidence_type, finding="verification timed out"):
    return EvidenceItem(
        evidence_id="EVD-GW-TEST",
        evidence_type=evidence_type,
        source="gateway:simulate_customer_reply",
        finding=finding,
        provenance="external_gateway_timeout",
        lr=1.0,
        log_lr=0.0,
        is_exculpatory=False,
    )


def test_serialize_evidence_requests_from_gateway_items():
    items = [
        _gateway_item(EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE),
    ]
    reqs = _serialize_evidence_requests(items)
    assert len(reqs) == 1
    assert reqs[0]["type"] == "VERIFY_WITH_CUSTOMER"
    assert reqs[0]["status"] == "UNAVAILABLE"
    assert reqs[0]["zero_belief_shift"] is True


def test_serialize_evidence_requests_deduplicates_by_type_and_status():
    items = [_gateway_item(EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE)]
    extra = [{
        "type": "VERIFY_WITH_CUSTOMER",
        "status": "UNAVAILABLE",
        "response": "duplicate",
        "provenance": "post_loop",
    }]
    reqs = _serialize_evidence_requests(items, extra_requests=extra)
    assert len(reqs) == 1


class _OrchestratorStub:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher


def _unresolved_state():
    engine = BeliefEngine()
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="bank_detection_model",
        finding="Risk score 0.61",
        lr=2.4,
        log_lr=0.875,
    ))
    return engine.evaluate_investigation(
        investigation_id="INV-EXTREQ-TEST",
        trigger={"trigger_type": "risk_score", "flagged_txn_id": "T1"},
        target_entities={"card_id": "C1", "customer_id": "CU1", "flagged_txn_id": "T1"},
        ledger=ledger,
        prior_profile=PriorProfile.UNIFORM_NON_INFORMATIVE,
    )


def test_external_resolution_attempt_records_request_with_zero_belief_shift():
    state = _unresolved_state()
    assert state.decision_gate_passed is False
    p_before = state.belief_state["fraud_probability"]

    stub = _OrchestratorStub(EvidenceToolDispatcher())
    updated, trace, request = _attempt_external_resolution(stub, state, {"trigger_type": "risk_score"}, "risk_score")

    assert trace is not None
    assert request is not None
    assert request["type"] == "VERIFY_WITH_CUSTOMER"
    # UNAVAILABLE must not move belief and must record missing information.
    assert updated.belief_state["fraud_probability"] == pytest.approx(p_before, abs=1e-9)
    assert request["zero_belief_shift"] is True
    assert any(m.reason == "CUSTOMER_COMMUNICATION_UNAVAILABLE" for m in updated.missing_information)


def test_external_resolution_attempt_none_when_customer_report():
    state = _unresolved_state()
    stub = _OrchestratorStub(EvidenceToolDispatcher())
    _, trace, request = _attempt_external_resolution(stub, state, {"trigger_type": "customer_report"}, "customer_report")
    assert trace is None and request is None


def test_external_resolution_attempt_none_when_already_interacted():
    state = _unresolved_state()
    state.evidence_items.append(_gateway_item(EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE))
    stub = _OrchestratorStub(EvidenceToolDispatcher())
    _, trace, request = _attempt_external_resolution(stub, state, {"trigger_type": "risk_score"}, "risk_score")
    assert trace is None and request is None


# ---------------------------------------------------------------------------
# Fix 2: R6-syndicate escalation
# ---------------------------------------------------------------------------

def _syndicate_ledger(ring_size):
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.SHARED_DEVICE_RING,
        source="tigergraph_query:device_analysis",
        finding=f"Device shared across {ring_size} distinct cards",
        value={"shared_card_count": ring_size},
        supporting_entities=[f"C{i}-K1" for i in range(ring_size)],
        lr=14.2,
        log_lr=2.653,
    ))
    return ledger


def test_r6_large_syndicate_locked_gate_escalates_without_auto_file():
    engine = PolicyEngine()
    actions = engine.evaluate(
        fraud_probability=0.93,
        verdict="confirmed_fraud",
        exposure_usd=74.96,
        ledger=_syndicate_ledger(52),
        case_context={"pattern": "card_not_present_fraud_new_device", "decision_gate_passed": False},
    )
    names = [a.action for a in actions]
    assert names[0] == "ESCALATE_TO_ANALYST"
    assert actions[0].approval_route == "L2"
    assert "FILE_REPORT" not in names  # deferred pending L2 human authorization
    assert "CREATE_CASE" in names and "MONITOR_CONNECTED_CARDS" in names


def test_r6_small_ring_gate_passed_files_report():
    engine = PolicyEngine()
    actions = engine.evaluate(
        fraud_probability=0.93,
        verdict="confirmed_fraud",
        exposure_usd=74.96,
        ledger=_syndicate_ledger(5),
        case_context={"pattern": "card_not_present_fraud_new_device", "decision_gate_passed": True},
    )
    names = [a.action for a in actions]
    assert names[0] == "CREATE_CASE"
    assert "FILE_REPORT" in names


# ---------------------------------------------------------------------------
# Fix 5: probed-coverage transparency (does not inflate coverage / belief)
# ---------------------------------------------------------------------------

def test_no_match_probe_tracked_without_inflating_coverage():
    engine = BeliefEngine()
    ledger = EvidenceLedger()
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
        source="bank_detection_model",
        finding="Risk 0.61",
        lr=2.4,
        log_lr=0.875,
    ))
    ledger.add(EvidenceItem(
        evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
        value="NO_MATCH",
        source="tigergraph_query:card_sequence",
        graph_query="card_sequence",
        finding="No micro-authorization sequence observed",
        lr=1.0,
        log_lr=0.0,
    ))
    state = engine.evaluate_investigation("INV-PROBE", {}, {}, ledger)
    assert state.uncertainty.evidence_coverage == 0.20
    assert state.uncertainty.probed_coverage == 0.40
    assert "TRANSACTION_VELOCITY" in state.uncertainty.probed_dimensions


# ---------------------------------------------------------------------------
# Fix 7: vector retrieval + retrieval paths + MCP JSON-RPC
# ---------------------------------------------------------------------------

def test_vector_index_retrieves_relevant_policy_chunk():
    index = get_default_vector_index(InvestigationKnowledgeBase())
    assert index.size() > 5
    results = index.search("card testing micro authorizations velocity burst", top_k=3)
    ids = [cid for cid, _ in results]
    assert any(cid in ids for cid in ["KNOW-TYPO-CARDTESTING", "KNOW-POLICY-R5"])


def test_vector_index_is_deterministic():
    idx_a = HashingVectorIndex().build(InvestigationKnowledgeBase().all_chunks())
    idx_b = HashingVectorIndex().build(InvestigationKnowledgeBase().all_chunks())
    assert idx_a.search("shared device syndicate ring") == idx_b.search("shared device syndicate ring")


def test_mcp_jsonrpc_list_and_call():
    from src.mcp.server import TigerGraphMCPServer, PROTOCOL_VERSION

    server = TigerGraphMCPServer()
    init = server.handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert init["result"]["protocolVersion"] == PROTOCOL_VERSION

    listing = server.handle_jsonrpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {t["name"] for t in listing["result"]["tools"]}
    assert "device_analysis" in names and "verify_customer" in names

    call = server.handle_jsonrpc({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "verify_customer", "arguments": {"case_id": "CASE-X"}},
    })
    assert call["result"]["isError"] is False


def test_mcp_official_contract_alignment():
    """Tark MCP surface matches the official tigergraph-mcp contract shape."""
    from src.mcp.server import TigerGraphMCPServer

    server = TigerGraphMCPServer()

    # 1. Protocol negotiation echoes a supported client version.
    init = server.handle_jsonrpc({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"},
    })
    assert init["result"]["protocolVersion"] == "2025-06-18"
    assert init["result"]["serverInfo"]["name"] == "tark-tigergraph-mcp"

    # 2. tools/list exposes annotations + tigergraph__-prefixed graph-native tools.
    listing = server.handle_jsonrpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = {t["name"]: t for t in listing["result"]["tools"]}
    assert "tigergraph__device_analysis" in tools
    assert tools["tigergraph__device_analysis"]["annotations"]["readOnlyHint"] is True
    assert listing["result"]["nextCursor"] is None

    # 3. tools/call returns the structured success envelope.
    call = server.handle_jsonrpc({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "tigergraph__verify_customer", "arguments": {"case_id": "CASE-Y"}},
    })
    sc = call["result"]["structuredContent"]
    assert sc["success"] is True
    assert sc["operation"] == "simulate_customer_reply"
    assert "metadata" in sc

    # 4. notifications/initialized and ping are accepted.
    assert server.handle_jsonrpc({"jsonrpc": "2.0", "id": 4, "method": "notifications/initialized"})["result"] == {}
    assert server.handle_jsonrpc({"jsonrpc": "2.0", "id": 5, "method": "ping"})["result"] == {}


def test_expected_nba_rubric_is_team_authored():
    rubric = json.loads((WORKSPACE_ROOT / "analysis" / "expected_nba.json").read_text(encoding="utf-8"))
    assert rubric.get("provenance") == "team-authored"
    assert "NOT independent judge ground truth" in rubric.get("disclaimer", "")


# ---------------------------------------------------------------------------
# P0: reconstructed graph-node labeling
# ---------------------------------------------------------------------------

def _run_data_with_ring_evidence(connected_cards):
    return {
        "exposure_usd": 75.0,
        "case": {
            "case_id": "HHG-TEST",
            "flagged_txn_id": "1000",
            "card_id": "C-FOCAL",
            "customer_id": "U-FOCAL",
            "opened_at": "2016-12-01 00:00:00",
            "trigger_type": "risk_score",
        },
        "run_result": {
            "final_state": {
                "evidence_items": [{
                    "evidence_id": "EVD-RING",
                    "evidence_type": "SHARED_DEVICE_RING",
                    "value": {"device_id": "DEV_1", "shared_card_count": 52, "is_proxy": True},
                    "lr": 14.2,
                    "log_lr": 2.653,
                    "is_exculpatory": False,
                    "supporting_transaction_ids": [],
                    "supporting_entities": connected_cards,
                    "details": {},
                }]
            }
        },
    }


def test_reconstructed_ring_nodes_are_flagged():
    """Aggregate-only ring evidence yields representative nodes flagged reconstructed."""
    graph = _build_graph_from_run(_run_data_with_ring_evidence(connected_cards=[]))
    nodes = {n["id"]: n for n in graph["nodes"]}

    ring_nodes = [n for n in graph["nodes"] if n["id"].startswith("CARD_RING_")]
    assert ring_nodes, "Expected representative ring nodes to be constructed"
    assert all(n["is_reconstructed"] for n in ring_nodes)
    assert graph["summary"]["has_reconstructed_nodes"] is True
    assert graph["summary"]["reconstructed_node_count"] >= len(ring_nodes)
    assert graph["summary"]["reconstruction_notice"]

    # The focal transaction and primary card are real, not reconstructed.
    assert nodes["1000"]["is_reconstructed"] is False
    assert nodes["C-FOCAL"]["is_reconstructed"] is False


def test_real_connected_cards_are_not_marked_reconstructed():
    """Concrete card ids from the graph are live nodes, not representative nodes."""
    graph = _build_graph_from_run(
        _run_data_with_ring_evidence(connected_cards=["C111-K1", "C222-K1"])
    )
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert nodes["C111-K1"]["is_reconstructed"] is False
    assert nodes["C222-K1"]["is_reconstructed"] is False
    assert not any(n["id"].startswith("CARD_RING_") for n in graph["nodes"])


# ---------------------------------------------------------------------------
# Fix 3: independent NBA rubric + policy invariants
# ---------------------------------------------------------------------------

def test_expected_nba_rubric_is_independent_and_complete():
    rubric = load_expected_nba_rubric()
    assert len(rubric) == 20
    assert rubric["HHG-001"] == "MONITOR_CARD"
    assert rubric["HHG-014"] == "ESCALATE_TO_ANALYST"


def test_harness_never_reads_cases_directory_for_expected():
    harness_src = (WORKSPACE_ROOT / "evaluation" / "harness.py").read_text(encoding="utf-8")
    assert 'os.path.join(os.getcwd(), "cases"' not in harness_src
    assert "gt_data" not in harness_src


def test_policy_invariant_flags_locked_gate_punitive_action():
    violations = evaluate_policy_invariants(
        {"trigger_type": "risk_score"},
        {"actual_nba": "BLOCK_CARD", "gate_passed": False, "fraud_probability": 0.9, "verdict": "fraud"},
    )
    assert violations


def test_policy_invariant_clean_case_has_no_violation():
    violations = evaluate_policy_invariants(
        {"trigger_type": "customer_report"},
        {"actual_nba": "BLOCK_CARD", "gate_passed": True, "fraud_probability": 0.95, "verdict": "fraud"},
    )
    assert violations == []
