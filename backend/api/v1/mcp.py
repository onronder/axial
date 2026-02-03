"""
MCP API Router

JSON-RPC 2.0 endpoint for Model Context Protocol access.
Provides AI agent access to the Axio Hub knowledge base.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status, BackgroundTasks
from pydantic import BaseModel

from mcp.server import MCPServer, JSONRPCRequest, JSONRPCResponse
from mcp.auth import (
    MCPApiKey,
    MCPApiKeyCreate,
    MCPApiKeyResponse,
    verify_mcp_api_key,
    create_mcp_api_key,
    revoke_mcp_api_key,
    list_mcp_api_keys,
)
from mcp.zero_retention import MCPZeroRetention
from api.v1.dependencies import require_admin, get_user_organization_id
from core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# MCP JSON-RPC Endpoint
# =============================================================================

@router.post("/mcp/v1/rpc")
@limiter.limit("100/minute")
async def mcp_rpc_endpoint(
    request: Request,
    body: JSONRPCRequest,
    api_key: MCPApiKey = Depends(verify_mcp_api_key),
) -> Response:
    """
    JSON-RPC 2.0 endpoint for MCP agents.

    Handles all MCP protocol methods:
    - initialize: Initialize MCP session
    - tools/list: List available tools
    - tools/call: Execute a tool
    - resources/list: List available resources
    - resources/read: Read a resource

    Authentication: Requires valid MCP API key in X-API-Key header.

    Ghost Protocol: All responses include zero-retention headers.
    """
    # Validate request intent for zero-retention compliance
    if body.method == "tools/call" and body.params:
        tool_name = body.params.get("name", "")
        arguments = body.params.get("arguments", {})
        if not MCPZeroRetention.validate_request_intent(tool_name, arguments):
            return Response(
                content=JSONRPCResponse(
                    id=body.id,
                    error={
                        "code": -32003,
                        "message": "Request denied: suspicious access pattern",
                    }
                ).model_dump_json(),
                media_type="application/json",
                headers=MCPZeroRetention.get_response_headers(),
            )

    # Execute request
    server = MCPServer()
    response = await server.handle_request(
        request=body,
        organization_id=api_key.organization_id,
        agent_id=api_key.id,
        allowed_scopes=api_key.scopes,
    )

    # Return with Ghost Protocol headers
    return Response(
        content=response.model_dump_json(),
        media_type="application/json",
        headers=MCPZeroRetention.get_response_headers(),
    )


# =============================================================================
# API Key Management Endpoints
# =============================================================================

@router.post("/mcp/api-keys", response_model=MCPApiKeyResponse)
@limiter.limit("10/minute")
async def create_api_key(
    request: Request,
    payload: MCPApiKeyCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
) -> MCPApiKeyResponse:
    """
    Create a new MCP API key.

    Only organization admins can create API keys.

    The plaintext key is only returned once at creation time.
    Store it securely - it cannot be retrieved later.

    Args:
        payload: Key creation parameters
            - agent_name: Human-readable name for the agent
            - scopes: List of scope patterns to allow (default: ["*"])
            - expires_in_days: Optional expiration in days

    Returns:
        API key details including the plaintext key
    """
    from services.audit import audit_logger

    key_response = await create_mcp_api_key(
        organization_id=organization_id,
        agent_name=payload.agent_name,
        scopes=payload.scopes,
        expires_in_days=payload.expires_in_days,
    )

    # Audit log (no key content)
    audit_logger.log(
        background_tasks,
        user_id=user_id,
        action="mcp.api_key.create",
        resource_type="mcp_api_key",
        resource_id=key_response.id,
        details={
            "agent_name": payload.agent_name,
            "scopes": payload.scopes,
            "expires_in_days": payload.expires_in_days,
        },
        request=request,
    )

    return key_response


@router.get("/mcp/api-keys", response_model=List[MCPApiKey])
@limiter.limit("30/minute")
async def list_api_keys(
    request: Request,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
) -> List[MCPApiKey]:
    """
    List all MCP API keys for the organization.

    Only organization admins can list API keys.
    Returns metadata only - keys are not retrievable after creation.
    """
    return await list_mcp_api_keys(organization_id)


@router.delete("/mcp/api-keys/{key_id}")
@limiter.limit("10/minute")
async def revoke_api_key(
    key_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Revoke an MCP API key.

    Only organization admins can revoke API keys.
    Revoked keys immediately become invalid.
    """
    from services.audit import audit_logger

    success = await revoke_mcp_api_key(key_id, organization_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Audit log
    audit_logger.log(
        background_tasks,
        user_id=user_id,
        action="mcp.api_key.revoke",
        resource_type="mcp_api_key",
        resource_id=key_id,
        details={},
        request=request,
    )

    return {"status": "success", "id": key_id}


# =============================================================================
# MCP Info Endpoint (Public)
# =============================================================================

@router.get("/mcp/info")
async def mcp_info():
    """
    Get MCP server information.

    Public endpoint for discovering MCP capabilities.
    """
    return {
        "name": "axio-hub-mcp",
        "version": "1.0.0",
        "protocol_version": "2024-11-05",
        "capabilities": {
            "tools": True,
            "resources": True,
        },
        "authentication": {
            "type": "api_key",
            "header": "X-API-Key",
        },
        "endpoints": {
            "rpc": "/api/v1/mcp/v1/rpc",
            "api_keys": "/api/v1/mcp/api-keys",
        },
        "ghost_protocol": {
            "enabled": True,
            "retention_policy": "zero",
        },
    }
