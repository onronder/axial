"""
MCP Server - JSON-RPC 2.0 Handler

Model Context Protocol server implementation for AI agent access.
Handles initialization, tool listing, tool execution, and resource access.

Spec: https://modelcontextprotocol.io/specification
"""

import logging
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from mcp.zero_retention import MCPZeroRetention

logger = logging.getLogger(__name__)


# =============================================================================
# JSON-RPC 2.0 Models
# =============================================================================

class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 Request object."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 Error object."""
    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 Response object."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None
    id: Optional[Union[str, int]] = None


# =============================================================================
# JSON-RPC Error Codes
# =============================================================================

class RPCErrorCode:
    """Standard JSON-RPC 2.0 error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Custom MCP error codes
    UNAUTHORIZED = -32001
    FORBIDDEN = -32003
    RATE_LIMITED = -32029
    RESOURCE_NOT_FOUND = -32004


# =============================================================================
# MCP Server
# =============================================================================

class MCPServer:
    """
    Model Context Protocol Server for AI agent access.

    Implements the MCP specification with Ghost Protocol enforcement
    for zero-retention responses.

    Supported Methods:
    - initialize: Initialize MCP session
    - tools/list: List available tools
    - tools/call: Execute a tool
    - resources/list: List available resources (scopes)
    - resources/read: Read a resource (document/scope content)

    Usage:
        server = MCPServer()
        response = await server.handle_request(
            request=JSONRPCRequest(method="tools/list"),
            organization_id="org-123",
            agent_id="agent-456",
        )
    """

    # Method routing table
    METHODS = {
        "initialize": "handle_initialize",
        "tools/list": "handle_tools_list",
        "tools/call": "handle_tools_call",
        "resources/list": "handle_resources_list",
        "resources/read": "handle_resources_read",
        "ping": "handle_ping",
    }

    # Server capabilities
    CAPABILITIES = {
        "tools": {"listChanged": False},
        "resources": {"subscribe": False, "listChanged": False},
    }

    # Server info
    SERVER_INFO = {
        "name": "axio-hub-mcp",
        "version": "1.0.0",
    }

    async def handle_request(
        self,
        request: JSONRPCRequest,
        organization_id: str,
        agent_id: str,
        allowed_scopes: Optional[List[str]] = None,
    ) -> JSONRPCResponse:
        """
        Route JSON-RPC request to appropriate handler.

        Args:
            request: The JSON-RPC request object
            organization_id: The organization context for this request
            agent_id: The agent/API key ID making the request
            allowed_scopes: Optional list of scope patterns this agent can access

        Returns:
            JSONRPCResponse with result or error
        """
        try:
            # Validate JSON-RPC version
            if request.jsonrpc != "2.0":
                return self._error_response(
                    request.id,
                    RPCErrorCode.INVALID_REQUEST,
                    "Invalid JSON-RPC version"
                )

            # Look up method handler
            handler_name = self.METHODS.get(request.method)
            if not handler_name:
                return self._error_response(
                    request.id,
                    RPCErrorCode.METHOD_NOT_FOUND,
                    f"Method not found: {request.method}"
                )

            # Get handler function
            handler = getattr(self, handler_name, None)
            if not handler:
                return self._error_response(
                    request.id,
                    RPCErrorCode.INTERNAL_ERROR,
                    f"Handler not implemented: {handler_name}"
                )

            # Execute handler
            result = await handler(
                params=request.params or {},
                organization_id=organization_id,
                agent_id=agent_id,
                allowed_scopes=allowed_scopes,
            )

            # Audit access (no content logged)
            MCPZeroRetention.audit_access(
                organization_id=organization_id,
                agent_id=agent_id,
                method=request.method,
                tool_name=request.params.get("name") if request.params else None,
            )

            return JSONRPCResponse(
                id=request.id,
                result=result,
            )

        except ValueError as e:
            return self._error_response(
                request.id,
                RPCErrorCode.INVALID_PARAMS,
                str(e)
            )
        except PermissionError as e:
            return self._error_response(
                request.id,
                RPCErrorCode.FORBIDDEN,
                str(e)
            )
        except Exception as e:
            logger.error(f"[MCP] Request failed: {e}", exc_info=True)
            return self._error_response(
                request.id,
                RPCErrorCode.INTERNAL_ERROR,
                "Internal server error"
            )

    def _error_response(
        self,
        request_id: Optional[Union[str, int]],
        code: int,
        message: str,
        data: Optional[Any] = None
    ) -> JSONRPCResponse:
        """Create an error response."""
        return JSONRPCResponse(
            id=request_id,
            error=JSONRPCError(
                code=code,
                message=message,
                data=data,
            ),
        )

    # =========================================================================
    # Method Handlers
    # =========================================================================

    async def handle_initialize(
        self,
        params: Dict[str, Any],
        organization_id: str,
        agent_id: str,
        allowed_scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Handle MCP initialize request.

        Returns server capabilities and info.
        """
        logger.info(f"[MCP] Initialize request from agent {agent_id[:8]}...")

        return {
            "protocolVersion": "2024-11-05",
            "capabilities": self.CAPABILITIES,
            "serverInfo": self.SERVER_INFO,
        }

    async def handle_ping(
        self,
        params: Dict[str, Any],
        organization_id: str,
        agent_id: str,
        allowed_scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Handle ping request for health check."""
        return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    async def handle_tools_list(
        self,
        params: Dict[str, Any],
        organization_id: str,
        agent_id: str,
        allowed_scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Handle tools/list request.

        Returns list of available tools for the agent.
        """
        from mcp.tools import MCP_TOOLS

        return {"tools": MCP_TOOLS}

    async def handle_tools_call(
        self,
        params: Dict[str, Any],
        organization_id: str,
        agent_id: str,
        allowed_scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Handle tools/call request.

        Executes the specified tool and returns results.
        """
        tool_name = params.get("name")
        if not tool_name:
            raise ValueError("Missing required parameter: name")

        arguments = params.get("arguments", {})

        from mcp.tools import execute_tool

        result = await execute_tool(
            tool_name=tool_name,
            arguments=arguments,
            organization_id=organization_id,
            agent_id=agent_id,
            allowed_scopes=allowed_scopes,
        )

        # Wrap result with Ghost Protocol markers
        return MCPZeroRetention.wrap_response(result)

    async def handle_resources_list(
        self,
        params: Dict[str, Any],
        organization_id: str,
        agent_id: str,
        allowed_scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Handle resources/list request.

        Returns list of available scopes/resources for the agent.
        """
        from mcp.resources import list_resources

        resources = await list_resources(
            organization_id=organization_id,
            allowed_scopes=allowed_scopes,
        )

        return {"resources": resources}

    async def handle_resources_read(
        self,
        params: Dict[str, Any],
        organization_id: str,
        agent_id: str,
        allowed_scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Handle resources/read request.

        Reads content from the specified resource (scope/document).
        """
        uri = params.get("uri")
        if not uri:
            raise ValueError("Missing required parameter: uri")

        from mcp.resources import read_resource

        content = await read_resource(
            uri=uri,
            organization_id=organization_id,
            allowed_scopes=allowed_scopes,
        )

        # Wrap content with Ghost Protocol markers
        return MCPZeroRetention.wrap_response(content)
