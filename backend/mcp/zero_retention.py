"""
MCP Zero-Retention Enforcement

Ghost Protocol implementation for MCP responses.
Ensures all agent responses are marked as ephemeral and not cached.
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MCPZeroRetention:
    """
    Ghost Protocol enforcement for MCP responses.

    All responses from MCP tools are:
    1. Marked as ephemeral (not to be cached)
    2. Include zero-retention metadata
    3. Logged for audit (without content)
    """

    @staticmethod
    def wrap_response(content: Any, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Wrap MCP response with Ghost Protocol markers.

        These markers signal to AI agents that:
        - Content should not be persisted
        - Content should not be used for training
        - Content is ephemeral and may change

        Args:
            content: The response content to wrap
            metadata: Optional additional metadata

        Returns:
            Wrapped response with Ghost Protocol markers
        """
        wrapped = {
            "content": content,
            "_ghost_protocol": {
                "ephemeral": True,
                "retention_policy": "zero",
                "cache_control": "no-store",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        if metadata:
            wrapped["_ghost_protocol"]["metadata"] = metadata

        return wrapped

    @staticmethod
    def audit_access(
        organization_id: str,
        agent_id: str,
        method: str,
        tool_name: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """
        Log MCP access for audit trail.

        IMPORTANT: This logs access metadata only, NEVER content.
        Content is ephemeral and should not be persisted in logs.

        Args:
            organization_id: Organization context
            agent_id: ID of the agent/API key
            method: MCP method called
            tool_name: Name of tool if tools/call
            resource_id: ID of resource if resources/read
        """
        try:
            from services.audit import audit_logger

            # Build details (no content!)
            details = {
                "method": method,
            }
            if tool_name:
                details["tool"] = tool_name
            if resource_id:
                details["resource_id"] = resource_id

            # Use sync logging (MCP calls are already async)
            audit_logger.log_sync(
                user_id=None,  # Agent access, not user
                action=f"mcp.{method.replace('/', '_')}",
                resource_type="mcp",
                resource_id=agent_id,
                details=details,
            )

        except Exception as e:
            # Never let audit logging break the main flow
            logger.warning(f"[MCP Audit] Failed to log access: {e}")

    @staticmethod
    def get_response_headers() -> Dict[str, str]:
        """
        Get HTTP headers for Ghost Protocol compliance.

        These headers should be set on all MCP responses.
        """
        return {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Ghost-Protocol": "zero-retention",
            "X-Content-Type-Options": "nosniff",
        }

    @staticmethod
    def validate_request_intent(
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> bool:
        """
        Validate that a tool request doesn't attempt to bypass Ghost Protocol.

        Checks for suspicious patterns like:
        - Requests to export/download raw content
        - Attempts to enumerate all documents
        - Unusual query patterns

        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments

        Returns:
            True if request is valid, False if suspicious
        """
        # Check for excessive data requests
        if tool_name == "search_documents":
            limit = arguments.get("limit", 10)
            if limit > 50:
                logger.warning(
                    f"[MCP ZeroRetention] Excessive search limit requested: {limit}"
                )
                return False

        # Check for enumeration attempts
        if tool_name == "list_scopes":
            # list_scopes is fine, just returns metadata
            pass

        # Check for suspicious query patterns
        query = arguments.get("query", "")
        if query and len(query) > 2000:
            logger.warning(
                f"[MCP ZeroRetention] Unusually long query: {len(query)} chars"
            )
            return False

        return True
