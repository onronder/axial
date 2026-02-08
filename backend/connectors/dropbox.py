"""
Dropbox Connector

Connects to Dropbox API v2 to fetch and sync files.
Supports both Personal and Business/Team accounts via Path Root header.

Uses raw HTTP requests for full control over timeouts, streaming, and rate limiting.

API Reference:
- RPC endpoints: https://api.dropboxapi.com/2/...
- Content endpoints: https://content.dropboxapi.com/2/...

Team/Business Support:
- Automatically detects Team accounts via root_info in /users/get_current_account
- Injects Dropbox-API-Path-Root header for Team Space access
"""

from __future__ import annotations

import io
import json
import logging
import mimetypes
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional, AsyncIterator

import requests

from connectors.base import (
    BaseConnector,
    RemoteFile,
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorTransientError,
)
from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType, ItemNotFoundError
from connectors.limits import connector_fetch_limit
from connectors.utils import load_integration
from core.config import settings
from core.scopes import build_scope_uri
from core.resilience import dropbox_breaker
from services.oauth_token_manager import OAuthTokenManager, TokenRefreshError

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

DROPBOX_API_BASE = "https://api.dropboxapi.com/2"
DROPBOX_CONTENT_BASE = "https://content.dropboxapi.com/2"
DEFAULT_TIMEOUT_SECONDS = 30
DOWNLOAD_TIMEOUT_SECONDS = 120
MAX_RETRIES = 3


class DropboxConnector(EnhancedConnector, BaseConnector):
    """
    Dropbox connector for unified ingestion pipeline.
    
    Features:
    - OAuth token refresh (via OAuthTokenManager)
    - Recursive folder listing with pagination
    - Streaming file downloads
    - Rate limit handling with Retry-After support
    - Team/Business account support via Path Root header
    
    Team Support:
    - Detects Business accounts via root_info.root_namespace_id
    - Automatically injects Dropbox-API-Path-Root header
    - Enables access to Team Folders and Shared Spaces
    """

    @property
    def connector_type(self) -> SourceType:
        return SourceType.DROPBOX

    @property
    def supports_incremental_sync(self) -> bool:
        return True

    # =========================================================================
    # Configuration & Validation
    # =========================================================================

    def validate_config(self, config: dict) -> bool:
        """
        Validate Dropbox configuration.
        
        Accepts:
        - access_token: Direct token (for testing/manual use)
        - integration_id: Lookup from user_integrations table
        - user_id: Lookup user's Dropbox integration
        
        Validation:
        - Calls /users/get_current_account to verify token validity
        - Extracts root_namespace_id for Team accounts
        """
        if not isinstance(config, dict):
            return False
        
        # Must have at least one credential source
        access_token = config.get("access_token")
        integration_id = config.get("integration_id")
        user_id = config.get("user_id")
        
        if not access_token and not integration_id and not user_id:
            return False
        
        # If we have a direct token, verify it
        if access_token:
            try:
                self._verify_token(access_token)
                return True
            except ConnectorAuthError:
                return False
            except Exception:
                # Network errors during validation = config might be OK
                return True
        
        return True  # Defer token resolution to operation time

    def _verify_token(self, access_token: str) -> dict:
        """
        Verify token by calling /users/get_current_account.
        
        Returns:
            Account info dict including root_info for Team accounts
            
        Raises:
            ConnectorAuthError: Invalid/expired token
        """
        url = f"{DROPBOX_API_BASE}/users/get_current_account"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            response = requests.post(url, headers=headers, data="null", timeout=10)
            
            if response.status_code == 401:
                raise ConnectorAuthError("Dropbox token invalid or expired")
            
            if response.status_code != 200:
                raise ConnectorTransientError(f"Dropbox API error: {response.text[:200]}")
            
            return response.json()
        except requests.RequestException as exc:
            raise ConnectorTransientError(f"Dropbox connection error: {exc}") from exc

    # =========================================================================
    # HTTP Layer - Core Request Methods
    # =========================================================================

    def _get_headers(self, config: dict, content_type: str = "application/json") -> dict:
        """
        Build request headers with authentication and Team namespace support.
        
        CRITICAL for Team/Business accounts:
        - If namespace_id is present, injects Dropbox-API-Path-Root header
        - This enables access to Team Folders instead of just user's home
        
        Args:
            config: Configuration dict with access_token and optional namespace_id
            content_type: Content-Type header value
            
        Returns:
            Headers dict ready for API request
        """
        headers = {
            "Authorization": f"Bearer {config.get('access_token')}",
        }
        
        if content_type:
            headers["Content-Type"] = content_type
        
        # Inject Path Root for Team/Business accounts
        namespace_id = config.get("namespace_id")
        if namespace_id:
            # Use root namespace to access Team Space
            path_root = json.dumps({".tag": "root", "root": namespace_id})
            headers["Dropbox-API-Path-Root"] = path_root
            logger.debug(f"📁 [Dropbox] Using Team namespace: {namespace_id}")
        
        return headers

    def _rpc_request(
        self,
        config: dict,
        endpoint: str,
        body: Optional[dict] = None,
    ) -> dict:
        """
        Make an RPC-style request to Dropbox API.
        
        RPC endpoints use JSON body for parameters.
        Example: /files/list_folder, /files/get_metadata
        
        Args:
            config: Configuration with credentials
            endpoint: API endpoint path (e.g., "/files/list_folder")
            body: Request body dict
            
        Returns:
            Parsed JSON response
        """
        url = f"{DROPBOX_API_BASE}{endpoint}"
        headers = self._get_headers(config, content_type="application/json")
        
        with connector_fetch_limit("dropbox"):
            response = self._request_with_retry(
                "POST",
                url,
                headers=headers,
                json_body=body or {},
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
        
        # Handle Dropbox's 409 for path errors
        if response.status_code == 409:
            error_data = {}
            try:
                error_data = response.json() if response.content else {}
            except ValueError:
                pass
            
            tag = error_data.get("error", {}).get(".tag", "")
            summary = error_data.get("error_summary", "")
            
            if tag == "path" or "not_found" in summary.lower():
                raise ItemNotFoundError(f"Dropbox path not found: {summary}")
            raise ConnectorTransientError(f"Dropbox conflict error: {summary}")
        
        try:
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            raise ConnectorTransientError(f"Dropbox RPC error: {exc}") from exc

    def _content_download(
        self,
        config: dict,
        path: str,
    ) -> bytes:
        """
        Download file content from Dropbox Content API.
        
        Content endpoints pass parameters via Dropbox-API-Arg header.
        Uses streaming for memory efficiency.
        
        Args:
            config: Configuration with credentials
            path: File path or ID to download
            
        Returns:
            Raw file content as bytes
        """
        url = f"{DROPBOX_CONTENT_BASE}/files/download"
        headers = self._get_headers(config, content_type=None)
        headers["Dropbox-API-Arg"] = json.dumps({"path": path})
        
        with connector_fetch_limit("dropbox"):
            response = self._request_with_retry(
                "POST",
                url,
                headers=headers,
                stream=True,
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            )
        
        # 409 on download = file not found
        if response.status_code == 409:
            error_header = response.headers.get("Dropbox-API-Result", "")
            response.close()
            raise ItemNotFoundError(f"Dropbox file not found: {error_header}")
        
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            response.close()
            raise ConnectorTransientError(f"Dropbox download error: {exc}") from exc
        
        # Stream to buffer (memory-safe for large files)
        buffer = io.BytesIO()
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                buffer.write(chunk)
        response.close()
        
        return buffer.getvalue()

    def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        json_body: Optional[dict] = None,
        stream: bool = False,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> requests.Response:
        """
        Execute HTTP request with retry logic.
        
        Handles:
        - 429 Rate Limit: Parse Retry-After, backoff, retry
        - 401 Auth Error: Raise ConnectorAuthError
        - 5xx Server Error: Raise ConnectorTransientError
        - Network errors: Raise ConnectorTransientError
        """
        headers = headers or {}
        attempt = 0
        
        while True:
            try:
                with dropbox_breaker:
                    response = requests.request(
                        method,
                        url,
                        headers=headers,
                        json=json_body if json_body else None,
                        timeout=timeout,
                        stream=stream,
                    )
            except requests.RequestException as exc:
                raise ConnectorTransientError(f"Dropbox network error: {exc}") from exc
            
            # Handle rate limiting with Retry-After
            if response.status_code == 429:
                if attempt >= MAX_RETRIES:
                    raise ConnectorRateLimitError("Dropbox rate limit exceeded after retries")
                
                retry_after = response.headers.get("Retry-After")
                delay = self._parse_retry_after(retry_after, default=1)
                
                logger.warning(f"⏳ [Dropbox] Rate limited, retrying in {delay}s")
                response.close()
                time.sleep(delay)
                attempt += 1
                continue
            
            # Map auth errors to standard exception
            if response.status_code in {401, 403}:
                detail = response.text[:500] if response.text else "No details"
                response.close()
                raise ConnectorAuthError(f"Dropbox auth failed: {detail}")
            
            # Map server errors to transient exception
            if response.status_code >= 500:
                detail = response.text[:500] if response.text else "No details"
                response.close()
                raise ConnectorTransientError(f"Dropbox server error: {detail}")
            
            return response

    def _parse_retry_after(self, value: Optional[str], default: int = 1) -> int:
        """Parse Retry-After header value."""
        if not value:
            return default
        try:
            return max(1, int(value))
        except ValueError:
            return default

    # =========================================================================
    # File Discovery - list_files()
    # =========================================================================

    def list_files(
        self,
        config: dict,
        since: Optional[datetime] = None,
    ) -> Iterator[RemoteFile]:
        """
        List files from Dropbox.
        
        Behavior:
        - If parent_id is None: Recursive listing from root (for sync)
        - If parent_id is set: List that folder (can be recursive or not)
        
        Filtering:
        - If since is provided, only yield files with server_modified >= since
        
        Team Support:
        - Uses namespace_id from config to access Team Folders
        """
        resolved = self._resolve_config(config)
        
        # Determine path to list
        parent_id = resolved.get("parent_id")
        root_path = resolved.get("root_path", "")
        
        if parent_id is None:
            # Full sync from root (or configured root_path)
            path = root_path if root_path else ""
        elif parent_id == "root":
            path = root_path if root_path else ""
        else:
            path = parent_id
        
        recursive = resolved.get("recursive", parent_id is None)
        include_folders = resolved.get("include_folders", True)
        
        # Initial list_folder request
        body = {
            "path": path,
            "recursive": recursive,
            "include_deleted": False,
            "include_has_explicit_shared_members": False,
            "include_mounted_folders": True,
            "include_non_downloadable_files": False,  # Skip Paper shortcuts, etc.
        }
        
        try:
            result = self._rpc_request(resolved, "/files/list_folder", body)
        except ItemNotFoundError:
            logger.warning(f"⚠️ [Dropbox] Path not found: {path}")
            return
        
        # Yield entries from first page
        for entry in result.get("entries", []):
            remote_file = self._entry_to_remote_file(entry, since, include_folders)
            if remote_file:
                yield remote_file
        
        # Pagination via cursor
        while result.get("has_more"):
            cursor = result["cursor"]
            result = self._rpc_request(
                resolved,
                "/files/list_folder/continue",
                {"cursor": cursor},
            )
            
            for entry in result.get("entries", []):
                remote_file = self._entry_to_remote_file(entry, since, include_folders)
                if remote_file:
                    yield remote_file

    def _entry_to_remote_file(
        self,
        entry: dict,
        since: Optional[datetime] = None,
        include_folders: bool = True,
    ) -> Optional[RemoteFile]:
        """
        Convert Dropbox metadata entry to RemoteFile.
        
        Returns None for:
        - Deleted entries
        - Folders (if include_folders=False)
        - Files modified before 'since' timestamp
        """
        tag = entry.get(".tag")
        
        # Handle folders
        if tag == "folder":
            if not include_folders:
                return None
            return RemoteFile(
                id=entry.get("id") or entry.get("path_lower"),
                name=entry.get("name"),
                mime_type="inode/directory",
                size=None,
                modified_at=None,
                parent_id=self._get_parent_path(entry.get("path_display")),
                web_view_url=None,
            )
        
        # Skip non-file entries
        if tag != "file":
            return None
        
        # Parse modification time
        server_modified = entry.get("server_modified")
        modified_at = self._parse_datetime(server_modified)
        
        # Apply 'since' filter for incremental sync
        if since and modified_at and modified_at < since:
            return None
        
        return RemoteFile(
            id=entry.get("id") or entry.get("path_lower"),
            name=entry.get("name"),
            mime_type=self._guess_mime_type(entry.get("name")),
            size=entry.get("size"),
            modified_at=modified_at,
            parent_id=self._get_parent_path(entry.get("path_display")),
            web_view_url=None,
        )

    # =========================================================================
    # Content Fetching - fetch_file_content() & fetch_documents()
    # =========================================================================

    def fetch_file_content(self, file_id: str, config: dict) -> bytes:
        """
        Fetch raw file bytes from Dropbox.
        
        Args:
            file_id: Dropbox file ID (id:xxx) or path_lower
            config: Configuration with credentials
            
        Returns:
            Raw file content as bytes
        """
        resolved = self._resolve_config(config)
        
        # Normalize path/ID format
        path = self._normalize_path_id(file_id)
        
        return self._content_download(resolved, path)

    async def fetch_documents(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AsyncIterator[SourceDocument]:
        """Async wrapper for fetch_documents_sync."""
        for doc in self.fetch_documents_sync(item_ids, credentials, **kwargs):
            yield doc

    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Iterator[SourceDocument]:
        """
        Fetch documents from Dropbox for ingestion pipeline.
        
        Handles:
        - Single files: Download directly
        - Folders: Recursive traversal
        
        Scope ID Format: dropbox://{folder_id_or_path}
        """
        if not item_ids:
            return iter(())
        
        resolved = self._resolve_config(credentials or {})
        
        logger.info(f"📥 [DropboxConnector] Fetching {len(item_ids)} item(s)")
        
        for item_id in item_ids:
            try:
                # Normalize the path/ID
                path = self._normalize_path_id(item_id)
                
                # Generate scope_id using canonical URI builder
                scope_id = build_scope_uri("dropbox", {"folder_id": item_id})
                
                # Get metadata to determine if file or folder
                metadata = self._rpc_request(
                    resolved,
                    "/files/get_metadata",
                    {"path": path},
                )
                
                tag = metadata.get(".tag")
                
                if tag == "folder":
                    # Recursive folder download
                    logger.info(f"📁 [Dropbox] Expanding folder: {metadata.get('name')}")
                    yield from self._fetch_folder_documents(resolved, path, scope_id)
                else:
                    # Single file
                    yield self._build_source_document(resolved, metadata, scope_id)
                    
            except ItemNotFoundError:
                logger.warning(f"⚠️ [Dropbox] Not found: {item_id}")
                continue
            except Exception as e:
                logger.error(f"❌ [Dropbox] Failed to fetch {item_id}: {e}")
                continue
        
        logger.info("📥 [DropboxConnector] Fetch stream ended")

    def _fetch_folder_documents(
        self,
        config: dict,
        folder_path: str,
        scope_id: str,
    ) -> Iterator[SourceDocument]:
        """Recursively fetch all documents in a folder."""
        # List files in folder
        folder_config = {**config, "parent_id": folder_path, "recursive": True, "include_folders": False}
        
        for remote_file in self.list_files(folder_config):
            try:
                # Get full metadata for this file
                metadata = self._rpc_request(
                    config,
                    "/files/get_metadata",
                    {"path": remote_file.id},
                )
                yield self._build_source_document(config, metadata, scope_id)
            except Exception as e:
                logger.error(f"❌ [Dropbox] Failed to fetch {remote_file.name}: {e}")
                continue

    def _build_source_document(
        self,
        config: dict,
        metadata: dict,
        scope_id: str,
    ) -> SourceDocument:
        """Build SourceDocument from Dropbox metadata."""
        path = metadata.get("path_lower") or metadata.get("path_display")
        name = metadata.get("name")
        
        # Download content
        content = self._content_download(config, path)
        
        # Check file size limit
        if len(content) > settings.MAX_FILE_SIZE:
            raise ConnectorTransientError(
                f"File {name} exceeds size limit ({len(content)} > {settings.MAX_FILE_SIZE})"
            )
        
        return SourceDocument(
            content=content,
            metadata={
                "source": "dropbox",
                "path": metadata.get("path_display"),
                "dropbox_id": metadata.get("id"),
                "rev": metadata.get("rev"),
                "content_hash": metadata.get("content_hash"),
                "modified_at": metadata.get("server_modified"),
                "size": metadata.get("size"),
                "scope_id": scope_id,  # CRITICAL: Required for FK compliance
            },
            source_type=SourceType.DROPBOX,
            source_id=metadata.get("id") or path,
            filename=name,
            mime_type=self._guess_mime_type(name),
            size_bytes=len(content),
            parent_id=self._get_parent_path(metadata.get("path_display")),
        )

    # =========================================================================
    # Configuration Resolution
    # =========================================================================

    def _resolve_config(self, config: dict) -> dict:
        """
        Resolve configuration, fetching tokens from database if needed.
        
        Also extracts namespace_id for Team/Business accounts.
        """
        resolved = dict(config or {})
        
        # If access_token already provided, verify and extract namespace
        if resolved.get("access_token"):
            # Ensure namespace_id is set if it's a Team account
            if not resolved.get("namespace_id"):
                try:
                    account_info = self._verify_token(resolved["access_token"])
                    root_info = account_info.get("root_info", {})
                    namespace_id = root_info.get("root_namespace_id")
                    if namespace_id:
                        resolved["namespace_id"] = namespace_id
                        logger.info(f"🏢 [Dropbox] Team account detected, namespace: {namespace_id}")
                except Exception as e:
                    logger.debug(f"[Dropbox] Failed to resolve team namespace: {e}")
            return resolved
        
        # Load integration from database
        integration = self._load_integration(resolved)

        # Check if integration needs reconnection
        if integration.get("status") == "reconnection_required":
            raise ConnectorAuthError(
                integration.get("status_message", "Please reconnect your Dropbox account.")
            )

        try:
            creds = OAuthTokenManager.get_valid_credentials(integration, "dropbox")
        except TokenRefreshError as exc:
            raise ConnectorAuthError("Dropbox integration requires reconnection") from exc
        
        resolved["access_token"] = creds.get("access_token")
        resolved["refresh_token"] = creds.get("refresh_token")
        resolved["expires_at"] = creds.get("expires_at")
        resolved["integration_id"] = creds.get("integration_id") or integration.get("id")
        
        # Extract stored namespace_id from credentials
        stored_credentials = integration.get("credentials") or {}
        if stored_credentials.get("namespace_id"):
            resolved["namespace_id"] = stored_credentials["namespace_id"]
            logger.debug(f"📁 [Dropbox] Using stored namespace: {resolved['namespace_id']}")
        
        # Extract root_path if configured
        if stored_credentials.get("root_path"):
            resolved["root_path"] = stored_credentials["root_path"]
        
        return resolved

    def _load_integration(self, config: dict) -> Dict[str, Any]:
        """Load integration record from database using shared utility."""
        return load_integration(
            "dropbox",
            integration_id=config.get("integration_id"),
            user_id=config.get("user_id"),
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _normalize_path_id(self, file_id: str) -> str:
        """
        Normalize file identifier to Dropbox API format.
        
        Accepts:
        - Dropbox ID: "id:xxx" or "dbid:xxx"
        - Path: "/folder/file.pdf"
        """
        if not file_id:
            return ""
        
        # Already a proper Dropbox ID
        if file_id.startswith("id:") or file_id.startswith("dbid:"):
            return file_id
        
        # It's a path, ensure it starts with /
        if not file_id.startswith("/"):
            return f"/{file_id}"
        
        return file_id

    def _get_parent_path(self, path_display: Optional[str]) -> Optional[str]:
        """Extract parent directory from full path."""
        if not path_display:
            return None
        parts = path_display.rsplit("/", 1)
        if len(parts) < 2:
            return ""
        return parts[0] or "/"

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        """Parse Dropbox ISO 8601 timestamp."""
        if not value:
            return None
        try:
            # Dropbox format: 2015-05-12T15:50:38Z
            if value.endswith("Z"):
                value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _guess_mime_type(filename: Optional[str]) -> str:
        """Guess MIME type from filename."""
        if not filename:
            return "application/octet-stream"
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"


# =============================================================================
# Module-level Connector Instance (for registry patterns)
# =============================================================================

def get_dropbox_connector() -> DropboxConnector:
    """Factory function to get a DropboxConnector instance."""
    return DropboxConnector()

