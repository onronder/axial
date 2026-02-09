"""
MCP Resource Handlers

Handles resource listing and reading for the MCP protocol.
Resources in Axio Hub represent scopes (document collections).
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Resource Listing
# =============================================================================

async def list_resources(
    organization_id: str,
    allowed_scopes: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    List available resources (scopes) for the organization.

    Resources are exposed as MCP resources with URIs like:
    - axio://scope/{scope_id}

    Args:
        organization_id: The organization context
        allowed_scopes: Optional scope whitelist

    Returns:
        List of MCP resource objects
    """
    from core.db import get_supabase

    supabase = get_supabase()

    # Get distinct scopes with document counts
    result = supabase.table("documents")\
        .select("scope_id, source_type")\
        .eq("organization_id", organization_id)\
        .neq("source_type", "identity")\
        .neq("source_type", "scope_identity")\
        .execute()

    # Aggregate by scope
    scope_data: dict[str, dict[str, Any]] = {}
    for row in result.data or []:
        scope_id = row.get("scope_id") or "default"

        # Filter by allowed scopes
        if allowed_scopes and not _scope_allowed(scope_id, allowed_scopes):
            continue

        if scope_id not in scope_data:
            scope_data[scope_id] = {
                "source_type": row.get("source_type"),
                "count": 0,
            }
        scope_data[scope_id]["count"] += 1

    # Format as MCP resources
    resources = []
    for scope_id, data in scope_data.items():
        resources.append({
            "uri": f"axio://scope/{scope_id}",
            "name": scope_id,
            "description": f"{data['source_type']} scope with {data['count']} document(s)",
            "mimeType": "application/json",
        })

    return resources


# =============================================================================
# Resource Reading
# =============================================================================

async def read_resource(
    uri: str,
    organization_id: str,
    allowed_scopes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Read content from a resource URI.

    Supported URI schemes:
    - axio://scope/{scope_id} - Returns scope metadata and document list
    - axio://document/{document_id} - Returns document metadata and chunk summary

    Args:
        uri: The resource URI to read
        organization_id: The organization context
        allowed_scopes: Optional scope whitelist

    Returns:
        Resource content as a dictionary

    Raises:
        ValueError: If URI is invalid or resource not found
        PermissionError: If access is denied
    """
    if not uri.startswith("axio://"):
        raise ValueError(f"Invalid URI scheme: {uri}")

    # Parse URI
    path = uri[7:]  # Remove "axio://"
    parts = path.split("/", 1)

    if len(parts) < 2:
        raise ValueError(f"Invalid URI format: {uri}")

    resource_type = parts[0]
    resource_id = parts[1]

    if resource_type == "scope":
        return await _read_scope_resource(
            resource_id, organization_id, allowed_scopes
        )
    elif resource_type == "document":
        return await _read_document_resource(
            resource_id, organization_id, allowed_scopes
        )
    else:
        raise ValueError(f"Unknown resource type: {resource_type}")


async def _read_scope_resource(
    scope_id: str,
    organization_id: str,
    allowed_scopes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Read scope resource - returns metadata and document list.
    """
    from core.db import get_supabase

    # Check access
    if allowed_scopes and not _scope_allowed(scope_id, allowed_scopes):
        raise PermissionError(f"Access denied to scope: {scope_id}")

    supabase = get_supabase()

    # Get documents in scope
    result = supabase.table("documents")\
        .select("id, title, source_type, created_at")\
        .eq("organization_id", organization_id)\
        .eq("scope_id", scope_id)\
        .neq("source_type", "identity")\
        .neq("source_type", "scope_identity")\
        .order("created_at", desc=True)\
        .limit(100)\
        .execute()

    documents = [
        {
            "id": doc["id"],
            "title": doc.get("title", "Unknown"),
            "source_type": doc.get("source_type"),
            "created_at": doc.get("created_at"),
        }
        for doc in result.data or []
    ]

    return {
        "uri": f"axio://scope/{scope_id}",
        "scope_id": scope_id,
        "document_count": len(documents),
        "documents": documents,
    }


async def _read_document_resource(
    document_id: str,
    organization_id: str,
    allowed_scopes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Read document resource - returns metadata and chunk info.

    Note: Full chunk content is NOT returned here for Ghost Protocol compliance.
    Use the search_documents or ask_question tools to access content.
    """
    from core.db import get_supabase

    supabase = get_supabase()

    # Get document
    doc_result = supabase.table("documents")\
        .select("id, title, source_type, scope_id, created_at, metadata")\
        .eq("id", document_id)\
        .eq("organization_id", organization_id)\
        .maybe_single()\
        .execute()

    if not doc_result.data:
        raise ValueError(f"Document not found: {document_id}")

    doc = doc_result.data

    # Check scope access
    scope_id = doc.get("scope_id") or "default"
    if allowed_scopes and not _scope_allowed(scope_id, allowed_scopes):
        raise PermissionError(f"Access denied to document in scope: {scope_id}")

    # Get chunk count (no content for zero-retention)
    chunk_result = supabase.table("document_chunks")\
        .select("id", count="exact")\
        .eq("document_id", document_id)\
        .execute()

    chunk_count = chunk_result.count or 0

    return {
        "uri": f"axio://document/{document_id}",
        "document_id": doc["id"],
        "title": doc.get("title", "Unknown"),
        "source_type": doc.get("source_type"),
        "scope_id": scope_id,
        "created_at": doc.get("created_at"),
        "chunk_count": chunk_count,
        "metadata": doc.get("metadata", {}),
        # Note: Content not included - use tools/call with search_documents
        "_note": "Use search_documents or ask_question tools to access content",
    }


# =============================================================================
# Helpers
# =============================================================================

def _scope_allowed(scope_id: str, allowed_scopes: list[str]) -> bool:
    """Check if a scope ID matches the allowed scope patterns."""
    if not allowed_scopes:
        return True

    for pattern in allowed_scopes:
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            if scope_id.startswith(prefix):
                return True
        elif pattern == scope_id:
            return True

    return False
