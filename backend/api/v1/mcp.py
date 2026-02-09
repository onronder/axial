"""
MCP API Router

JSON-RPC 2.0 endpoint for Model Context Protocol access.
Provides AI agent access to the Axio Hub knowledge base.
"""

import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)

from api.v1.dependencies import get_user_organization_id, require_admin
from core.rate_limit import limiter
from mcp.auth import (
    MCPApiKey,
    MCPApiKeyCreate,
    MCPApiKeyResponse,
    MCPApiKeyRotateRequest,
    MCPApiKeyRotateResponse,
    create_mcp_api_key,
    list_mcp_api_keys,
    revoke_mcp_api_key,
    rotate_mcp_api_key,
    verify_mcp_api_key,
)
from mcp.server import JSONRPCRequest, JSONRPCResponse, MCPServer
from mcp.zero_retention import MCPZeroRetention

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


@router.get("/mcp/api-keys", response_model=list[MCPApiKey])
@limiter.limit("30/minute")
async def list_api_keys(
    request: Request,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
) -> list[MCPApiKey]:
    """
    List all MCP API keys for the organization.

    Only organization admins can list API keys.
    Returns metadata only - keys are not retrievable after creation.
    """
    return await list_mcp_api_keys(organization_id)


@router.get("/mcp/api-keys/{key_id}", response_model=MCPApiKey)
@limiter.limit("30/minute")
async def get_api_key(
    key_id: str,
    request: Request,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
) -> MCPApiKey:
    """
    Get details of a specific MCP API key.

    Only organization admins can view API key details.
    Returns metadata only - the actual key is not retrievable after creation.
    """
    from core.db import get_supabase

    supabase = get_supabase()

    result = supabase.table("mcp_api_keys")\
        .select("id, agent_name, scopes, created_at, expires_at, revoked_at")\
        .eq("id", key_id)\
        .eq("organization_id", organization_id)\
        .maybe_single()\
        .execute()

    if not result or not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    data = result.data
    return MCPApiKey(
        id=data["id"],
        organization_id=organization_id,
        agent_name=data["agent_name"],
        scopes=data.get("scopes") or ["*"],
        created_at=data["created_at"],
        expires_at=data.get("expires_at"),
        revoked_at=data.get("revoked_at"),
    )


@router.post("/mcp/api-keys/{key_id}/rotate", response_model=MCPApiKeyRotateResponse)
@limiter.limit("10/minute")
async def rotate_api_key(
    key_id: str,
    request: Request,
    payload: MCPApiKeyRotateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
) -> MCPApiKeyRotateResponse:
    """
    Rotate an MCP API key.

    Creates a new key with the same agent name and scopes, and sets the
    old key to expire after a configurable grace period (default: 24 hours).
    Both keys remain valid during the grace window.

    Args:
        key_id: ID of the key to rotate
        payload: Rotation parameters (grace_period_hours)
    """
    from services.audit import audit_logger

    result = await rotate_mcp_api_key(
        key_id=key_id,
        organization_id=organization_id,
        grace_period_hours=payload.grace_period_hours,
    )

    audit_logger.log(
        background_tasks,
        user_id=user_id,
        action="mcp.api_key.rotate",
        resource_type="mcp_api_key",
        resource_id=key_id,
        details={
            "new_key_id": result.new_key.id,
            "grace_period_hours": payload.grace_period_hours,
        },
        request=request,
    )

    return result


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
