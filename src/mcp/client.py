"""TigerGraph Model Context Protocol (MCP) Client.

Client-side interface used by the controlled cognitive/agent layers to interact
with the MCP tool server under strict telemetry, logging, and provenance tracking.
"""

import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from src.mcp.server import TigerGraphMCPServer, MCPCallToolResult, PROTOCOL_VERSION

logger = logging.getLogger("tark.mcp.client")


class TigerGraphMCPClient:
    """Client for invoking authorized tools through the MCP protocol boundary."""

    def __init__(self, server: Optional[TigerGraphMCPServer] = None):
        self.server = server or TigerGraphMCPServer()
        self.session_id = f"mcp-session-{uuid.uuid4().hex[:8]}"
        self.call_history: List[Dict[str, Any]] = []

    def get_protocol_version(self) -> str:
        return PROTOCOL_VERSION

    def list_available_tools(self) -> List[Dict[str, Any]]:
        """Queries available tools exposed through the MCP protocol."""
        return self.server.list_tools()

    def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> MCPCallToolResult:
        """Invokes a tool via the MCP protocol boundary with full telemetry capture."""
        req_id = f"mcp-req-{uuid.uuid4().hex[:8]}"
        start_time = time.perf_counter()

        logger.info(f"[{self.session_id}][{req_id}] MCP Request -> tool='{name}' args={arguments}")

        # Dispatch via MCP Server protocol boundary
        result = self.server.call_tool(name=name, arguments=arguments, context=context)

        total_latency = round((time.perf_counter() - start_time) * 1000, 2)

        telemetry_entry = {
            "session_id": self.session_id,
            "request_id": req_id,
            "tool_name": name,
            "arguments": arguments,
            "is_error": result.isError,
            "duration_ms": total_latency,
            "structured_status": result.structured_result.get("status") if result.structured_result else None
        }
        self.call_history.append(telemetry_entry)

        logger.info(f"[{self.session_id}][{req_id}] MCP Response <- status={'ERROR' if result.isError else 'OK'} latency={total_latency}ms")
        return result
