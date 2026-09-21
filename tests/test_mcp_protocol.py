"""Tests for TigerGraph MCP Protocol Layer (P2.1).

Verifies:
1. Standard MCP tool discovery and JSON schema compliance.
2. Boundary enforcement: Unauthorized tools or arbitrary queries are strictly rejected.
3. Authorized tools execute through the deterministic dispatcher.
4. Telemetry and session history integrity.
"""

import pytest
from src.mcp.server import TigerGraphMCPServer, PROTOCOL_VERSION
from src.mcp.client import TigerGraphMCPClient
from src.tools.dispatcher import EvidenceToolDispatcher


def test_mcp_server_lists_tools():
    server = TigerGraphMCPServer()
    tools = server.list_tools()
    tool_names = {t["name"] for t in tools}

    expected_tools = {
        "device_analysis",
        "card_sequence",
        "transaction_velocity",
        "region_analysis",
        "customer_profile",
        "similar_cases",
        "verify_customer",
        "step_up_auth"
    }
    assert expected_tools.issubset(tool_names), f"Missing tools in MCP server: {expected_tools - tool_names}"

    for t in tools:
        assert "name" in t
        assert "description" in t
        assert "inputSchema" in t
        assert t["inputSchema"].get("type") == "object"


def test_mcp_rejects_unauthorized_tool_call():
    server = TigerGraphMCPServer()
    client = TigerGraphMCPClient(server)

    # Attempting to call an unauthorized / arbitrary tool
    res = client.call_tool("arbitrary_gsql_executor", {"query": "DROP GRAPH Fraud"})
    assert res.isError is True
    assert "not an authorized MCP tool" in res.content[0]["text"]


def test_mcp_client_telemetry_tracking():
    server = TigerGraphMCPServer()
    client = TigerGraphMCPClient(server)

    assert client.get_protocol_version() == PROTOCOL_VERSION
    assert len(client.call_history) == 0

    # Call a valid mock/adapter tool
    res = client.call_tool("verify_customer", {"case_id": "TEST-001", "prompt": "Did you make this purchase?"})
    assert len(client.call_history) == 1

    entry = client.call_history[0]
    assert entry["tool_name"] == "verify_customer"
    assert entry["session_id"].startswith("mcp-session-")
    assert entry["request_id"].startswith("mcp-req-")
    assert entry["duration_ms"] >= 0.0
    assert entry["is_error"] is False


def test_mcp_boundary_preserves_dispatcher_authority():
    dispatcher = EvidenceToolDispatcher()
    server = TigerGraphMCPServer(dispatcher=dispatcher)
    client = TigerGraphMCPClient(server)

    res = client.call_tool("verify_customer", {"case_id": "CASE-123"})
    assert res.isError is False
    assert res.structured_result is not None
    assert res.structured_result["action_id"] == "VERIFY_WITH_CUSTOMER"
    assert res.structured_result["tool_name"] == "simulate_customer_reply"
