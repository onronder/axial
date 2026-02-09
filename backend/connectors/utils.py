"""
Shared utilities for connector implementations.

Consolidates common patterns to reduce code duplication and ensure consistency.
"""

from __future__ import annotations

import logging
from typing import Any

from connectors.base import ConnectorAuthError
from core.db import get_supabase
from services.oauth_token_manager import OAuthTokenManager, TokenRefreshError

logger = logging.getLogger(__name__)


def load_integration(
    connector_type: str,
    integration_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Load integration record from database.

    This is the canonical way to load a user's integration for any connector.

    Args:
        connector_type: The connector type (e.g., 'github', 'dropbox', 'box', 's3')
        integration_id: Optional direct integration ID lookup
        user_id: Optional user ID to find their integration

    Returns:
        Full integration record from user_integrations table

    Raises:
        ConnectorAuthError: If integration not found or connector not registered

    Example:
        >>> integration = load_integration('github', user_id='abc-123')
        >>> creds = integration.get('credentials', {})
    """
    supabase = get_supabase()

    # Direct integration_id lookup (most efficient)
    if integration_id:
        result = supabase.table("user_integrations").select("*").eq(
            "id", integration_id
        ).single().execute()

        if result.data:
            return result.data
        raise ConnectorAuthError(f"Integration {integration_id} not found")

    # User ID lookup requires connector definition
    if not user_id:
        raise ConnectorAuthError(f"{connector_type} requires user_id or integration_id")

    # Find connector definition
    def_result = supabase.table("connector_definitions").select("id").eq(
        "type", connector_type
    ).single().execute()

    if not def_result.data:
        raise ConnectorAuthError(f"{connector_type} connector not registered")

    connector_def_id = def_result.data["id"]

    # Find user's integration for this connector
    int_result = supabase.table("user_integrations").select("*").eq(
        "user_id", user_id
    ).eq("connector_definition_id", connector_def_id).single().execute()

    if not int_result.data:
        raise ConnectorAuthError(f"{connector_type} not connected for this user")

    return int_result.data


def resolve_oauth_credentials(
    connector_type: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    Resolve OAuth credentials, loading from database and refreshing if needed.

    This is the standard pattern for OAuth connectors (GitHub, Dropbox, Box,
    Microsoft, Notion, Google Drive).

    Args:
        connector_type: The connector type for OAuthTokenManager
        config: Config dict that may contain access_token, integration_id, or user_id

    Returns:
        Updated config dict with resolved credentials:
        - access_token: Valid (possibly refreshed) token
        - refresh_token: Current refresh token
        - expires_at: Token expiration timestamp
        - integration_id: ID of the integration record
        - credentials: Full stored credentials dict

    Raises:
        ConnectorAuthError: If credentials cannot be resolved or require reconnection

    Example:
        >>> resolved = resolve_oauth_credentials('github', {'user_id': 'abc'})
        >>> token = resolved['access_token']
    """
    resolved = dict(config or {})

    # If access_token already provided, return as-is
    if resolved.get("access_token"):
        return resolved

    # Load integration from database
    integration = load_integration(
        connector_type,
        integration_id=resolved.get("integration_id"),
        user_id=resolved.get("user_id"),
    )

    # Check if integration needs reconnection
    if integration.get("status") == "reconnection_required":
        raise ConnectorAuthError(
            integration.get("status_message", f"Please reconnect your {connector_type} account.")
        )

    # Get valid credentials with automatic refresh
    try:
        creds = OAuthTokenManager.get_valid_credentials(integration, connector_type)
    except TokenRefreshError as exc:
        raise ConnectorAuthError(
            f"{connector_type} integration requires reconnection"
        ) from exc

    # Merge resolved credentials
    resolved["access_token"] = creds.get("access_token")
    resolved["refresh_token"] = creds.get("refresh_token")
    resolved["expires_at"] = creds.get("expires_at")
    resolved["integration_id"] = creds.get("integration_id") or integration.get("id")
    resolved["credentials"] = integration.get("credentials") or {}

    return resolved


def resolve_form_credentials(
    connector_type: str,
    config: dict[str, Any],
    required_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    """
    Resolve form-based credentials (non-OAuth) from database.

    Used by connectors that use API keys, IAM credentials, or passwords
    (e.g., S3, SFTP).

    Args:
        connector_type: The connector type
        config: Config dict that may contain credentials or user_id/integration_id
        required_fields: Tuple of required credential field names

    Returns:
        Updated config dict with credentials merged from database

    Raises:
        ConnectorAuthError: If required credentials are missing

    Example:
        >>> resolved = resolve_form_credentials(
        ...     's3',
        ...     {'user_id': 'abc'},
        ...     required_fields=('access_key_id', 'secret_access_key')
        ... )
    """
    resolved = dict(config or {})

    # Check if credentials are already fully provided
    if required_fields and all(resolved.get(f) for f in required_fields):
        return resolved

    # Load from user_integrations if user_id provided
    user_id = resolved.get("user_id")
    integration_id = resolved.get("integration_id")

    if user_id or integration_id:
        integration = load_integration(
            connector_type,
            integration_id=integration_id,
            user_id=user_id,
        )
        stored_creds = integration.get("credentials", {})

        # Merge stored credentials (don't override provided values)
        for key, value in stored_creds.items():
            if key not in resolved or resolved.get(key) is None:
                resolved[key] = value

        resolved["integration_id"] = integration.get("id")

    return resolved


def build_config_from_kwargs(
    credentials: dict[str, Any] | None = None,
    auth_keys: tuple[str, ...] = ("user_id", "integration_id"),
    **kwargs,
) -> dict[str, Any]:
    """
    Build configuration dict by merging credentials with kwargs.

    Standard pattern used by fetch_documents_sync to combine
    credentials dict with keyword arguments.

    Args:
        credentials: Optional credentials dict
        auth_keys: Keys to extract from kwargs into config
        **kwargs: Additional params (user_id, integration_id, etc.)

    Returns:
        Merged configuration dict

    Example:
        >>> config = build_config_from_kwargs(
        ...     {'access_token': 'xyz'},
        ...     user_id='abc-123'
        ... )
        >>> # config = {'access_token': 'xyz', 'user_id': 'abc-123'}
    """
    config: dict[str, Any] = dict(credentials or {})

    for key in auth_keys:
        if key in kwargs and kwargs[key] is not None:
            config[key] = kwargs[key]

    return config
