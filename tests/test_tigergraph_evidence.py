import os
import json
import pytest
from dotenv import load_dotenv

load_dotenv(r"c:\Users\Mukul\Desktop\Tark\.env")
import pyTigerGraph as tg

@pytest.fixture(scope="module")
def tg_conn():
    conn = tg.TigerGraphConnection(
        host=os.getenv("TG_HOST"),
        username=os.getenv("TG_USERNAME"),
        password=os.getenv("TG_PASSWORD"),
        graphname=os.getenv("TG_GRAPHNAME"),
        gsqlSecret=os.getenv("TG_SECRET"),
        tgCloud=True
    )
    return conn

def test_tigergraph_vertex_counts_non_zero(tg_conn):
    """Verify that TigerGraph contains substantive data derived from the actual datasets."""
    expected_min_counts = {
        "Customer": 1000,
        "Card": 1000,
        "Transaction": 20000,
        "DeviceProfile": 500,
        "BillingRegion": 50,
        "EmailDomain": 20,
        "ClosedCase": 5000
    }
    for vertex_type, min_count in expected_min_counts.items():
        count = tg_conn.getVertexCount(vertex_type)
        assert count >= min_count, f"Vertex {vertex_type} has only {count} rows, expected at least {min_count}"

def test_tigergraph_edge_counts_non_zero(tg_conn):
    """Verify that TigerGraph edges are populated linking customers, cards, transactions, and devices."""
    expected_min_edges = {
        "Customer_OWNS_Card": 1000,
        "Card_MADE_Transaction": 5000,
        "Transaction_FROM_DEVICE": 2000,
        "Transaction_BILLED_IN": 5000,
        "Transaction_PURCHASER_EMAIL": 5000,
        "ClosedCase_ON_CARD": 5000
    }
    for edge_type, min_count in expected_min_edges.items():
        count = tg_conn.getEdgeCount(edge_type)
        assert count >= min_count, f"Edge {edge_type} has only {count} instances, expected at least {min_count}"

def test_customer_profile_installed_query(tg_conn):
    """Verify customer_profile query produces substantive baseline statistics from graph."""
    res = tg_conn.runInstalledQuery("customer_profile", {"cust_id": "C12382"})
    assert res and len(res) > 0, "Query returned empty result"
    data = res[0]
    assert data["total_txns"] > 50, "Expected significant historical transactions"
    assert data["total_amount"] > 1000.0, "Expected non-zero total spend"
    assert len(data["region_distribution"]) > 10, "Expected multi-region profile"

def test_device_analysis_installed_query(tg_conn):
    """Verify device_analysis discovers real multi-card sharing blast radius and proxy detection."""
    # HHG-014 transaction
    res = tg_conn.runInstalledQuery("device_analysis", {"t_id": "3478561"})
    assert res and len(res) > 0, "Query returned empty result"
    data = res[0]
    assert data["device_id"].startswith("DEV_"), "Expected generated device profile ID"
    assert data["is_proxy"] is True, "Expected proxy flag set"
    assert data["shared_card_count"] >= 10, f"Expected multi-card ring, got {data['shared_card_count']}"
    assert len(data["connected_cards"]) >= 10, "Expected list of connected cards"

def test_card_sequence_installed_query(tg_conn):
    """Verify card_sequence detects real micro-authorization card testing patterns."""
    # HHG-011 card C11923-K2
    res = tg_conn.runInstalledQuery("card_sequence", {
        "c_id": "C11923-K2",
        "anchor_ts": "2016-12-29 03:27:44",
        "window_hours": 24
    })
    assert res and len(res) > 0, "Query returned empty result"
    data = res[0]
    assert data["is_card_testing"] is True, "Expected card testing detected"
    assert data["micro_count"] >= 3, "Expected at least 3 micro-authorizations"
    assert len(data["micro_txn_ids"]) >= 3, "Expected list of micro txn IDs"

def test_similar_cases_installed_query(tg_conn):
    """Verify similar_cases query retrieves real closed cases from history with analyst notes."""
    res = tg_conn.runInstalledQuery("similar_cases", {
        "target_pattern": "card_testing",
        "c_id": "C11923-K2"
    })
    assert res and len(res) > 0, "Query returned empty result"
    matched = res[0].get("Matched", [])
    assert len(matched) > 0, "Expected matched closed cases"
    for item in matched:
        attrs = item.get("attributes", {})
        assert attrs.get("pattern") == "card_testing", "Expected matching pattern"
        assert len(attrs.get("analyst_notes", "")) > 10, "Expected real analyst notes"
