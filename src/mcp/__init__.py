"""Model Context Protocol (MCP) tool integration layer for Tark.

Establishes an open-standard MCP protocol boundary between the LLM / Controlled Agent
and the deterministic EvidenceToolDispatcher.
"""

from src.mcp.server import TigerGraphMCPServer
from src.mcp.client import TigerGraphMCPClient

__all__ = ["TigerGraphMCPServer", "TigerGraphMCPClient"]
