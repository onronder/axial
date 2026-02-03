"""
MCP (Model Context Protocol) Server Implementation

Provides JSON-RPC 2.0 interface for AI agent access to the Axio Hub knowledge base.
Implements Ghost Protocol zero-retention for all responses.

Components:
- server.py: JSON-RPC 2.0 request handler
- tools.py: MCP tool definitions (search, ask, list_scopes)
- resources.py: Resource handlers for scope/document access
- auth.py: API key authentication for agents
- zero_retention.py: Ghost Protocol enforcement for MCP responses
"""

from mcp.server import MCPServer, JSONRPCRequest, JSONRPCResponse
from mcp.auth import MCPApiKey, verify_mcp_api_key
from mcp.tools import MCP_TOOLS, execute_tool

__all__ = [
    'MCPServer',
    'JSONRPCRequest',
    'JSONRPCResponse',
    'MCPApiKey',
    'verify_mcp_api_key',
    'MCP_TOOLS',
    'execute_tool',
]
