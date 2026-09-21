"""P1.3 — Core Generalization & Unseen Transaction Investigation Test Suite.

Verifies that the autonomous Bayesian investigation pipeline:
1. Operates dynamically on arbitrary, unseen transactions directly from TigerGraph.
2. Resolves graph topology (Transaction -> Card -> Customer -> DeviceProfile) without benchmark coupling.
3. Produces fully grounded Bayesian posterior updates, policy actions, and graph visualizations.
4. Accurately flags non-existent transactions with 404 errors.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.graph.connection import get_tigergraph_connection
from src.graph.resolver import TransactionResolver, TransactionNotFoundError


# 5 Non-benchmark transactions verified on live TigerGraph
UNSEEN_TIGERGRAPH_TXNS = [
    "3047878",
    "3018431",
    "3017957",
    "3027386",
    "3015779",
]


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


@pytest.fixture(scope="module")
def tg_conn():
    conn = get_tigergraph_connection()
    if conn is None:
        pytest.skip("Live TigerGraph connection unavailable for generalization test.")
    return conn


def test_transaction_resolver_resolves_unseen_transactions(tg_conn):
    """Verifies that TransactionResolver dynamically resolves entities for unseen transactions."""
    resolver = TransactionResolver(tg_conn)
    for txn_id in UNSEEN_TIGERGRAPH_TXNS:
        ctx = resolver.resolve(txn_id)
        assert ctx.txn_id == txn_id
        assert ctx.amount > 0.0
        assert ctx.card_id != "", f"Card ID should be resolved for txn {txn_id}"
        assert ctx.customer_id != "", f"Customer ID should be resolved for txn {txn_id}"
        assert ctx.timestamp != "", f"Timestamp should be resolved for txn {txn_id}"


def test_arbitrary_transaction_investigation_pipeline(api_client, tg_conn):
    """Verifies that 5 unseen transactions execute end-to-end through the autonomous investigation loop."""
    for txn_id in UNSEEN_TIGERGRAPH_TXNS:
        resp = api_client.post(f"/api/investigations/transaction/{txn_id}/run")
        assert resp.status_code == 200, f"Investigation failed for txn {txn_id}: {resp.text}"

        data = resp.json()
        assert data["investigation_id"] == f"TXN-{txn_id}"
        assert data["status"] == "COMPLETED"

        result = data["result"]
        run_res = result["run_result"]
        final_state = run_res["final_state"]

        # Bayesian belief state integrity
        assert 0.0 <= final_state["fraud_probability"] <= 1.0
        assert 0.0 <= final_state["evidence_coverage"] <= 1.0
        assert final_state["classification"] in ["fraud", "legitimate", "uncertain"]

        # Policy decision integrity
        primary_action = run_res["primary_action"]
        assert primary_action is not None
        assert "action" in primary_action
        assert primary_action["action"] in [
            "DECLINE_TRANSACTION",
            "BLOCK_CARD",
            "VERIFY_WITH_CUSTOMER",
            "CREATE_CASE",
            "APPROVE_TRANSACTION",
            "MONITOR_CARD",
        ]
        assert primary_action["approval_route"] in ["auto", "manual", "analyst_review"]

        # Graph visualization topology integrity
        graph = result.get("graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        node_ids = {n["id"] for n in nodes}
        assert txn_id in node_ids, "Focal transaction node must be in graph"
        assert len(edges) >= 2, "Must contain at least Txn->Card and Card->Customer structural edges"


def test_arbitrary_transaction_not_found_returns_404(api_client):
    """Verifies that querying a non-existent transaction ID returns a clean 404."""
    resp = api_client.post("/api/investigations/transaction/9999999999/run")
    assert resp.status_code == 404
    assert "does not exist in graph database" in resp.json()["detail"]
