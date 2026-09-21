import pytest
from unittest.mock import MagicMock
from src.graph.resolver import TransactionResolver, TransactionNotFoundError, ResolvedTransactionContext
from src.graph.connection import get_tigergraph_connection


def test_transaction_resolver_with_live_tigergraph():
    """Tests dynamic entity resolution against live TigerGraph Cloud for a real transaction."""
    conn = get_tigergraph_connection()
    if conn is None:
        pytest.skip("Live TigerGraph Cloud connection unavailable.")

    resolver = TransactionResolver(conn)
    # Test on transaction 3583368
    ctx = resolver.resolve("3583368")

    assert ctx.txn_id == "3583368"
    assert ctx.card_id == "C11923-K2"
    assert ctx.customer_id == "C11923"
    assert ctx.device_id == "DEV_d339a8c89ee2"
    assert ctx.amount == 131.3
    assert ctx.timestamp == "2016-12-29 03:27:44"
    assert ctx.channel == "online"
    assert ctx.risk_score == 0.39


def test_transaction_resolver_nonexistent_transaction_raises_404():
    """Verifies that an unknown transaction ID cleanly raises TransactionNotFoundError."""
    mock_conn = MagicMock()
    mock_conn.getVerticesById.return_value = []  # No vertex found

    resolver = TransactionResolver(mock_conn)
    with pytest.raises(TransactionNotFoundError) as exc_info:
        resolver.resolve("TXN_UNKNOWN_99999999")

    assert "TXN_UNKNOWN_99999999" in str(exc_info.value)


def test_transaction_resolver_handles_missing_device_gracefully():
    """Verifies that transaction without device edge resolves cleanly without crashing."""
    mock_conn = MagicMock()
    mock_conn.getVerticesById.side_effect = lambda v_type, v_id: (
        [{"attributes": {"amount": 50.0, "ts": "2016-11-15 12:00:00", "risk_score": 0.45}}]
        if v_type == "Transaction" else
        [{"attributes": {"customer_id": "CUST_MOCK_1"}}]
        if v_type == "Card" else []
    )
    mock_conn.getEdges.return_value = [
        {"e_type": "Transaction_MADE_BY_Card", "to_type": "Card", "to_id": "CARD_MOCK_1"}
    ]

    resolver = TransactionResolver(mock_conn)
    ctx = resolver.resolve("TXN_NO_DEVICE")

    assert ctx.txn_id == "TXN_NO_DEVICE"
    assert ctx.card_id == "CARD_MOCK_1"
    assert ctx.customer_id == "CUST_MOCK_1"
    assert ctx.device_id is None
    assert ctx.amount == 50.0
