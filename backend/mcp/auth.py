"""
MCP Authentication

API key authentication for MCP agent access.
Provides secure, scoped access tokens for external AI agents.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timezone

from fastapi import Header, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# Models
# =============================================================================

class MCPApiKey(BaseModel):
    """
    API key metadata for MCP agent access.

    Attributes:
        id: Unique key identifier (UUID)
        organization_id: Organization this key belongs to
        agent_name: Human-readable name for this agent/integration
        scopes: List of scope patterns this key can access
        created_at: When the key was created
        expires_at: Optional expiration time
    """
    id: str
    organization_id: str
    agent_name: str
    scopes: list[str]
    created_at: datetime
    expires_at: datetime | None = None


class MCPApiKeyCreate(BaseModel):
    """Request model for creating a new MCP API key."""
    agent_name: str
    scopes: list[str] = ["*"]  # Default: access all scopes
    expires_in_days: int | None = None  # None = never expires


class MCPApiKeyResponse(BaseModel):
    """Response model when creating a new API key."""
    id: str
    key: str  # Only shown once at creation time
    agent_name: str
    scopes: list[str]
    created_at: datetime
    expires_at: datetime | None = None


# =============================================================================
# Key Generation
# =============================================================================

def generate_api_key() -> str:
    """
    Generate a secure API key.

    Format: axio_mcp_{random_hex}
    Length: 48 characters of randomness (192 bits of entropy)
    """
    random_part = secrets.token_hex(24)
    return f"axio_mcp_{random_part}"


def hash_api_key(key: str) -> str:
    """
    Hash an API key for storage.

    Uses SHA-256 for secure, irreversible hashing.
    """
    return hashlib.sha256(key.encode()).hexdigest()


# =============================================================================
# Key Verification
# =============================================================================

async def verify_mcp_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> MCPApiKey:
    """
    FastAPI dependency to verify MCP API key.

    Extracts the API key from the X-API-Key header, verifies it against
    the database, and returns the key metadata.

    Args:
        x_api_key: The API key from the request header

    Returns:
        MCPApiKey with organization context and allowed scopes

    Raises:
        HTTPException 401: If key is invalid, expired, or revoked
    """
    from core.db import get_supabase

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate key format
    if not x_api_key.startswith("axio_mcp_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Hash the key for lookup
    key_hash = hash_api_key(x_api_key)

    supabase = get_supabase()

    # Look up key in database
    result = supabase.table("mcp_api_keys")\
        .select("*")\
        .eq("key_hash", key_hash)\
        .is_("revoked_at", "null")\
        .maybe_single()\
        .execute()

    if not result.data:
        logger.warning("[MCP Auth] Invalid API key attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_data = result.data

    # Check expiration
    expires_at = key_data.get("expires_at")
    if expires_at:
        expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires_dt < datetime.now(timezone.utc):
            logger.warning(f"[MCP Auth] Expired API key: {key_data['id'][:8]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    logger.debug(
        f"[MCP Auth] Authenticated agent: {key_data['agent_name']} "
        f"(org: {key_data['organization_id'][:8]}...)"
    )

    return MCPApiKey(
        id=key_data["id"],
        organization_id=key_data["organization_id"],
        agent_name=key_data["agent_name"],
        scopes=key_data.get("scopes", ["*"]),
        created_at=datetime.fromisoformat(
            key_data["created_at"].replace("Z", "+00:00")
        ),
        expires_at=datetime.fromisoformat(
            expires_at.replace("Z", "+00:00")
        ) if expires_at else None,
    )


# =============================================================================
# Key Management
# =============================================================================

async def create_mcp_api_key(
    organization_id: str,
    agent_name: str,
    scopes: list[str],
    expires_in_days: int | None = None,
) -> MCPApiKeyResponse:
    """
    Create a new MCP API key.

    Args:
        organization_id: Organization to create key for
        agent_name: Human-readable name for the agent
        scopes: List of scope patterns to allow
        expires_in_days: Optional expiration in days

    Returns:
        MCPApiKeyResponse with the plaintext key (only shown once)
    """
    from datetime import timedelta

    from core.db import get_supabase

    # Generate key
    key = generate_api_key()
    key_hash = hash_api_key(key)

    # Calculate expiration
    now = datetime.now(timezone.utc)
    expires_at = None
    if expires_in_days:
        expires_at = now + timedelta(days=expires_in_days)

    supabase = get_supabase()

    # Insert key record
    result = supabase.table("mcp_api_keys").insert({
        "organization_id": organization_id,
        "key_hash": key_hash,
        "agent_name": agent_name,
        "scopes": scopes,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }).execute()

    if not result.data:
        raise Exception("Failed to create API key")

    key_record = result.data[0]

    logger.info(
        f"[MCP Auth] Created API key for agent '{agent_name}' "
        f"in org {organization_id[:8]}..."
    )

    return MCPApiKeyResponse(
        id=key_record["id"],
        key=key,  # Plaintext key - only shown once
        agent_name=agent_name,
        scopes=scopes,
        created_at=now,
        expires_at=expires_at,
    )


async def revoke_mcp_api_key(
    key_id: str,
    organization_id: str,
) -> bool:
    """
    Revoke an MCP API key.

    Args:
        key_id: ID of the key to revoke
        organization_id: Organization context (for authorization)

    Returns:
        True if revoked, False if not found
    """
    from core.db import get_supabase

    supabase = get_supabase()

    # Update key to set revoked_at
    result = supabase.table("mcp_api_keys")\
        .update({"revoked_at": datetime.now(timezone.utc).isoformat()})\
        .eq("id", key_id)\
        .eq("organization_id", organization_id)\
        .execute()

    if result.data:
        logger.info(f"[MCP Auth] Revoked API key: {key_id[:8]}...")
        return True

    return False


class MCPApiKeyRotateRequest(BaseModel):
    """Request model for rotating an MCP API key."""
    grace_period_hours: int = 24  # Keep old key valid for this long


class MCPApiKeyRotateResponse(BaseModel):
    """Response model for key rotation."""
    new_key: MCPApiKeyResponse
    old_key_id: str
    old_key_expires_at: datetime


async def rotate_mcp_api_key(
    key_id: str,
    organization_id: str,
    grace_period_hours: int = 24,
) -> MCPApiKeyRotateResponse:
    """
    Rotate an MCP API key with a grace period.

    Creates a new key with the same agent name and scopes, then sets
    the old key to expire after the grace period. Both keys are valid
    during the transition window.

    Args:
        key_id: ID of the key to rotate
        organization_id: Organization context
        grace_period_hours: Hours to keep the old key valid (default 24)

    Returns:
        MCPApiKeyRotateResponse with new key and old key expiration
    """
    from datetime import timedelta

    from core.db import get_supabase

    supabase = get_supabase()

    # Fetch the existing key
    result = supabase.table("mcp_api_keys")\
        .select("*")\
        .eq("id", key_id)\
        .eq("organization_id", organization_id)\
        .is_("revoked_at", "null")\
        .maybe_single()\
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or already revoked",
        )

    old_key = result.data

    # Create new key with same agent name and scopes
    new_key_response = await create_mcp_api_key(
        organization_id=organization_id,
        agent_name=old_key["agent_name"],
        scopes=old_key.get("scopes", ["*"]),
        expires_in_days=None,  # New key inherits no expiration (can be set separately)
    )

    # Set grace period expiration on old key
    grace_expires = datetime.now(timezone.utc) + timedelta(hours=grace_period_hours)
    supabase.table("mcp_api_keys")\
        .update({"expires_at": grace_expires.isoformat()})\
        .eq("id", key_id)\
        .eq("organization_id", organization_id)\
        .execute()

    logger.info(
        f"[MCP Auth] Rotated API key {key_id[:8]}... → {new_key_response.id[:8]}... "
        f"(grace period: {grace_period_hours}h)"
    )

    return MCPApiKeyRotateResponse(
        new_key=new_key_response,
        old_key_id=key_id,
        old_key_expires_at=grace_expires,
    )


async def list_mcp_api_keys(
    organization_id: str,
) -> list[MCPApiKey]:
    """
    List all MCP API keys for an organization.

    Returns non-revoked keys only.
    """
    from core.db import get_supabase

    supabase = get_supabase()

    result = supabase.table("mcp_api_keys")\
        .select("id, organization_id, agent_name, scopes, created_at, expires_at")\
        .eq("organization_id", organization_id)\
        .is_("revoked_at", "null")\
        .order("created_at", desc=True)\
        .execute()

    return [
        MCPApiKey(
            id=row["id"],
            organization_id=row["organization_id"],
            agent_name=row["agent_name"],
            scopes=row.get("scopes", ["*"]),
            created_at=datetime.fromisoformat(
                row["created_at"].replace("Z", "+00:00")
            ),
            expires_at=datetime.fromisoformat(
                row["expires_at"].replace("Z", "+00:00")
            ) if row.get("expires_at") else None,
        )
        for row in result.data or []
    ]
