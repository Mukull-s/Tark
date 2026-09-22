"""TigerGraph Model Context Protocol (MCP) Server.

Defines the MCP standard tool execution boundary for Tark.
Guarantees:
1. Controlled Agent / LLM can only invoke registered, schema-validated tools.
2. Arbitrary GSQL execution, shell commands, or unvetted queries are strictly rejected.
3. All executions route through the authoritative EvidenceToolDispatcher.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from src.tools.dispatcher import EvidenceToolDispatcher
from src.tools.base import ToolExecutionResult
from src.graph.scope import GraphScopeStatus

logger = logging.getLogger("tark.mcp.server")

# Protocol versions this server understands. The active version is negotiated
# during `initialize` (client's requested version if supported, else the latest).
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2024-11-05")
SERVER_NAME = "tark-tigergraph-mcp"
SERVER_VERSION = "1.1.0"


class MCPToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]
    action_id: str
    # MCP behavioural hints (official tigergraph-mcp contract).
    annotations: Dict[str, Any] = Field(default_factory=dict)


class MCPCallToolResult(BaseModel):
    content: List[Dict[str, Any]]
    isError: bool = False
    structured_result: Optional[Dict[str, Any]] = None
    duration_ms: float = 0.0


class TigerGraphMCPServer:
    """MCP-compliant Tool Server exposing authorized TigerGraph and External Evidence Tools.
    
    Acts as the strict protocol boundary between cognitive agents and deterministic execution.

    Contract compatibility: this server speaks the same JSON-RPC 2.0 / MCP tool
    surface as the official ``tigergraph-mcp`` server (`initialize`, `tools/list`,
    `tools/call`), exposes ``tigergraph__``-prefixed aliases for graph-native tools,
    attaches MCP ``annotations`` to every tool, and returns the structured
    ``{success, operation, summary, data, suggestions, metadata}`` envelope.
    """

    def __init__(self, dispatcher: Optional[EvidenceToolDispatcher] = None):
        self.dispatcher = dispatcher or EvidenceToolDispatcher()
        self._tools: Dict[str, MCPToolDefinition] = {}
        self.client_protocol_version: Optional[str] = None
        self._register_schemas()

    def _register_schemas(self):
        """Registers canonical MCP tool schemas for financial fraud investigation."""
        tools = [
            MCPToolDefinition(
                name="device_analysis",
                action_id="QUERY_DEVICE_ANALYSIS",
                description="Analyzes device sharing across accounts, device fingerprinting, and proxy detection on TigerGraph.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device identifier to inspect"},
                        "t_id": {"type": "string", "description": "Optional transaction ID context"}
                    }
                }
            ),
            MCPToolDefinition(
                name="card_sequence",
                action_id="QUERY_CARD_SEQUENCE",
                description="Detects rapid micro-authorization sequences and card-testing probing bursts on TigerGraph.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "c_id": {"type": "string", "description": "Card account identifier"},
                        "anchor_ts": {"type": "string", "description": "Timestamp anchor for temporal sequence analysis"}
                    },
                    "required": ["c_id"]
                }
            ),
            MCPToolDefinition(
                name="transaction_velocity",
                action_id="QUERY_TXN_VELOCITY",
                description="Calculates rolling transaction velocity, burst rate, and velocity spikes on TigerGraph.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "c_id": {"type": "string", "description": "Card account identifier"},
                        "target_ts": {"type": "string", "description": "Transaction timestamp anchor"}
                    },
                    "required": ["c_id"]
                }
            ),
            MCPToolDefinition(
                name="region_analysis",
                action_id="QUERY_REGION_ANALYSIS",
                description="Evaluates geographical distance and billing region anomalies on TigerGraph.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cust_id": {"type": "string", "description": "Customer account ID"},
                        "txn_addr1": {"type": "number", "description": "Billing zip / region code from transaction"}
                    },
                    "required": ["cust_id"]
                }
            ),
            MCPToolDefinition(
                name="customer_profile",
                action_id="INQUIRE_CUSTOMER_PROFILE",
                description="Queries historical baseline volume, tenure, and normal spending patterns on TigerGraph.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cust_id": {"type": "string", "description": "Customer account identifier"}
                    },
                    "required": ["cust_id"]
                }
            ),
            MCPToolDefinition(
                name="similar_cases",
                action_id="RETRIEVE_SIMILAR_CASES",
                description="Retrieves historical closed investigation precedents matching graph topology and typology.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target_pattern": {"type": "string", "description": "Fraud typology or graph motif"}
                    }
                }
            ),
            MCPToolDefinition(
                name="verify_customer",
                action_id="VERIFY_WITH_CUSTOMER",
                description="Dispatches external cardholder verification challenge via out-of-band communication adapter.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "case_id": {"type": "string", "description": "Investigation case ID"},
                        "prompt": {"type": "string", "description": "Verification question prompt"}
                    }
                }
            ),
            MCPToolDefinition(
                name="step_up_auth",
                action_id="STEP_UP_AUTH",
                description="Executes in-flight cryptographic MFA challenge via external authentication adapter.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "case_id": {"type": "string", "description": "Investigation case ID"}
                    }
                }
            )
        ]

        for t in tools:
            self._tools[t.name] = t
            self._tools[t.action_id] = t

        # Map implementation names and compass action IDs to canonical definitions
        aliases = {
            "txn_velocity": "transaction_velocity",
            "simulate_customer_reply": "verify_customer",
            "simulate_step_up_auth": "step_up_auth",
            "QUERY_DEVICE_ANALYSIS": "device_analysis",
            "QUERY_CARD_SEQUENCE": "card_sequence",
            "QUERY_TXN_VELOCITY": "transaction_velocity",
            "QUERY_REGION_ANALYSIS": "region_analysis",
            "INQUIRE_CUSTOMER_PROFILE": "customer_profile",
            "RETRIEVE_SIMILAR_CASES": "similar_cases",
            "VERIFY_WITH_CUSTOMER": "verify_customer",
            "STEP_UP_AUTH": "step_up_auth",
        }
        for alias, target in aliases.items():
            if target in self._tools:
                self._tools[alias] = self._tools[target]

        # Attach MCP behavioural annotations (official tigergraph-mcp contract).
        for t in self._tools.values():
            if not t.annotations:
                t.annotations = {
                    "title": t.name.replace("_", " ").title(),
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                }

        # Register ``tigergraph__``-prefixed aliases matching the official server's
        # naming convention for graph-native tools, so an agent configured against
        # tigergraph-mcp can call the equivalent Tark tools without re-plumbing.
        for t in list(self._tools.values()):
            prefixed = f"tigergraph__{t.name}"
            if prefixed not in self._tools:
                self._tools[prefixed] = t

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns standard MCP tool declarations for LLM agent discovery."""
        unique_tools = {}
        for t in self._tools.values():
            unique_tools[t.name] = {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema,
                "annotations": t.annotations,
            }
        # Derive prefixed aliases from the canonical set.
        for name, decl in list(unique_tools.items()):
            prefixed = f"tigergraph__{name}"
            unique_tools[prefixed] = {**decl, "name": prefixed}
        return list(unique_tools.values())

    # ------------------------------------------------------------------
    # JSON-RPC (MCP transport) compatibility layer
    # ------------------------------------------------------------------
    def list_tools_rpc(self) -> Dict[str, Any]:
        """JSON-RPC ``tools/list`` result payload (no pagination)."""
        return {"tools": self.list_tools(), "nextCursor": None}

    def call_tool_rpc(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """JSON-RPC ``tools/call`` result payload.

        Returns the standard MCP content envelope plus the official tigergraph-mcp
        structured envelope ``{success, operation, summary, data, suggestions, metadata}``.
        """
        res = self.call_tool(name=name, arguments=arguments, context=context)
        structured = res.structured_result or {}
        operation = structured.get("tool_name") or name
        success = not res.isError
        text = res.content[0]["text"] if res.content else ""

        envelope = {
            "success": success,
            "operation": operation,
            "summary": text,
            "data": structured.get("evidence_item") or structured.get("raw_data"),
            "suggestions": [],
            "metadata": {
                "action_id": structured.get("action_id"),
                "status": structured.get("status"),
                "scope_status": structured.get("scope_status"),
                "duration_ms": structured.get("duration_ms", res.duration_ms),
            },
        }
        if not success:
            envelope["error"] = text
            envelope["suggestions"] = ["Verify the tool name and arguments against tools/list."]

        return {
            "content": res.content,
            "isError": res.isError,
            "structuredContent": envelope,
        }

    def handle_jsonrpc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handles a single MCP JSON-RPC 2.0 request envelope.

        Supported methods: ``initialize``, ``notifications/initialized``, ``ping``,
        ``tools/list``, ``tools/call``.
        """
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        if method == "initialize":
            requested = params.get("protocolVersion")
            self.client_protocol_version = requested
            negotiated = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else PROTOCOL_VERSION
            result: Dict[str, Any] = {
                "protocolVersion": negotiated,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "Tark fraud-investigation tool server. Tools execute through the "
                    "authoritative EvidenceToolDispatcher; arbitrary GSQL is rejected."
                ),
            }
        elif method in ("notifications/initialized", "initialized"):
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}
        elif method == "ping":
            result = {}
        elif method in ("tools/list", "list_tools"):
            result = self.list_tools_rpc()
        elif method in ("tools/call", "call_tool"):
            result = self.call_tool_rpc(
                name=params.get("name", ""),
                arguments=params.get("arguments"),
                context=params.get("context"),
            )
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> MCPCallToolResult:
        """Executes a tool call under strict authorization governance.
        
        Security checks:
        1. Tool must be registered in MCP server definitions.
        2. Tool must resolve to an authorized EvidenceTool registered in EvidenceToolDispatcher.
        3. No arbitrary query execution allowed.
        """
        start = time.perf_counter()
        args = arguments or {}
        ctx = context or {}

        # 1. Look up tool definition
        tool_def = self._tools.get(name)
        if not tool_def:
            duration = round((time.perf_counter() - start) * 1000, 2)
            logger.warning(f"MCP invocation rejected: tool '{name}' is not registered.")
            return MCPCallToolResult(
                content=[{"type": "text", "text": f"Error: Tool '{name}' is not an authorized MCP tool."}],
                isError=True,
                duration_ms=duration
            )

        # 2. Look up dispatcher tool
        evidence_tool = self.dispatcher.get_tool(tool_def.action_id) or self.dispatcher.get_tool(tool_def.name)
        if not evidence_tool:
            duration = round((time.perf_counter() - start) * 1000, 2)
            logger.warning(f"MCP invocation rejected: action '{tool_def.action_id}' missing in EvidenceToolDispatcher.")
            return MCPCallToolResult(
                content=[{"type": "text", "text": f"Security Error: Tool '{name}' has no authorized implementation."}],
                isError=True,
                duration_ms=duration
            )

        # 3. Authoritative execution
        try:
            res: ToolExecutionResult = evidence_tool.execute(params=args, context=ctx)
            duration = round((time.perf_counter() - start) * 1000, 2)

            text_summary = res.message
            if res.evidence_item:
                text_summary += f" [Evidence: {res.evidence_item.finding}, LR: {res.evidence_item.lr:.2f}]"

            structured = {
                "action_id": res.action_id,
                "tool_name": res.tool_name,
                "status": res.status,
                "scope_status": res.scope_status.value if hasattr(res.scope_status, "value") else str(res.scope_status),
                "duration_ms": duration,
                "evidence_item": {
                    "evidence_id": res.evidence_item.evidence_id,
                    "evidence_type": res.evidence_item.evidence_type.value if hasattr(res.evidence_item.evidence_type, "value") else str(res.evidence_item.evidence_type),
                    "finding": res.evidence_item.finding,
                    "lr": res.evidence_item.lr,
                    "log_lr": res.evidence_item.log_lr,
                    "is_exculpatory": res.evidence_item.is_exculpatory,
                    "provenance": res.evidence_item.provenance
                } if res.evidence_item else None,
                "raw_data": res.raw_data
            }

            return MCPCallToolResult(
                content=[{"type": "text", "text": text_summary}],
                isError=res.status == "FAILED",
                structured_result=structured,
                duration_ms=duration
            )

        except Exception as e:
            duration = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(f"MCP execution error for {name}: {str(e)}")
            return MCPCallToolResult(
                content=[{"type": "text", "text": f"Internal MCP execution failure: {str(e)}"}],
                isError=True,
                duration_ms=duration
            )
