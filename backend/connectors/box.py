"""
Box Connector

Connects to Box Content API to fetch and sync files.
Supports both Personal and Enterprise/Business accounts.

Uses raw HTTP requests for full control over timeouts, streaming, and rate limiting.

API Reference:
- https://developer.box.com/reference/
- Authentication: https://developer.box.com/guides/authentication/oauth2/

ID Formats:
- Folder: Numeric string (e.g., "0" for root, "123456789" for subfolder)
- File: Numeric string (e.g., "987654321")

Token Lifecycle:
- Access tokens expire after 60 minutes
- Refresh tokens are SINGLE-USE and rotate on each refresh (60-day lifetime)

PRODUCTION SAFEGUARDS:
- Deterministic source IDs: Uses box://{file_id} format for delete reconciliation
- Robust pagination: BFS traversal with visited set to prevent loops
- Rate limit handling: Respects Retry-After header with exponential backoff
- Graceful 403 handling: Skips restricted folders without failing entire sync
- Resumable downloads: Chunked streaming with size limits
"""

from __future__ import annotations

import io
import logging
import mimetypes
import time
from collections import deque
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from connectors.base import (
    BaseConnector,
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorTransientError,
    RemoteFile,
)
from connectors.enhanced import (
    EnhancedConnector,
    FileTooLargeError,
    ItemNotFoundError,
    SourceDocument,
    SourceType,
)
from connectors.limits import connector_fetch_limit
from connectors.utils import build_config_from_kwargs, load_integration
from core.config import settings
from core.scopes import build_scope_uri
from services.oauth_token_manager import OAuthTokenManager, TokenRefreshError

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

BOX_API_BASE = "https://api.box.com/2.0"
ROOT_FOLDER_ID = "0"

DEFAULT_TIMEOUT_SECONDS = 30
DOWNLOAD_TIMEOUT_SECONDS = 120
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1
PAGE_SIZE = 1000  # Box maximum
LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50 MB - use chunked download
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB chunks for large files

# Minimal fields for efficient listing (bandwidth optimization)
ITEM_FIELDS = "id,name,type,size,sha1,modified_at,parent"

COMMON_MIME_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".md": "text/markdown",
}


class BoxConnector(EnhancedConnector, BaseConnector):
    """
    Box connector for unified ingestion pipeline.

    Features:
    - OAuth token refresh with rotating refresh tokens (CRITICAL: single-use)
    - Recursive folder traversal with offset pagination
    - Streaming file downloads
    - Rate limit handling with Retry-After support
    - Enterprise and Personal account support

    Security:
    - Uses root_readonly scope (minimum required)
    - Gracefully handles 403 on restricted folders
    """

    def __init__(self) -> None:
        super().__init__()
        self._folder_name_cache: dict[str, str] = {}

    @property
    def connector_type(self) -> SourceType:
        return SourceType.BOX

    @property
    def supports_incremental_sync(self) -> bool:
        return True

    @property
    def supports_batch_fetch(self) -> bool:
        return False  # Box doesn't support batch downloads

    # =========================================================================
    # Configuration & Validation
    # =========================================================================

    def validate_config(self, config: dict) -> bool:
        """
        Validate Box configuration.

        Validation Strategy:
        - Call GET /users/me to verify token validity

        Accepts:
        - access_token: Direct token
        - integration_id: Lookup from user_integrations table
        - user_id: Lookup user's Box integration
        """
        if not isinstance(config, dict):
            return False

        access_token = config.get("access_token")
        integration_id = config.get("integration_id")
        user_id = config.get("user_id")

        if not access_token and not integration_id and not user_id:
            return False

        if access_token:
            try:
                self._verify_token(access_token)
                return True
            except ConnectorAuthError:
                return False
            except Exception:
                return True  # Network errors = config might be OK

        return True  # Defer resolution to operation time

    def _verify_token(self, access_token: str) -> dict:
        """
        Verify token by calling GET /users/me.

        Returns:
            User info dict

        Raises:
            ConnectorAuthError: Invalid/expired token
        """
        url = f"{BOX_API_BASE}/users/me"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 401:
                raise ConnectorAuthError("Box token invalid or expired")

            if response.status_code == 403:
                raise ConnectorAuthError("Box access denied - insufficient permissions")

            if response.status_code != 200:
                raise ConnectorTransientError(f"Box API error: {response.text[:200]}")

            return response.json()
        except requests.RequestException as exc:
            raise ConnectorTransientError(f"Box connection error: {exc}") from exc

    # =========================================================================
    # HTTP Layer - Core Request Methods
    # =========================================================================

    def _get_headers(self, config: dict) -> dict:
        """Build request headers with authentication."""
        return {
            "Authorization": f"Bearer {config.get('access_token')}",
        }

    def _request(
        self,
        config: dict,
        endpoint: str,
        params: dict | None = None,
    ) -> dict:
        """
        Make a GET request to Box API.

        Args:
            config: Configuration with credentials
            endpoint: API endpoint path (e.g., "/folders/0/items")
            params: Query parameters

        Returns:
            Parsed JSON response
        """
        url = f"{BOX_API_BASE}{endpoint}"
        headers = self._get_headers(config)

        with connector_fetch_limit("box"):
            response = self._request_with_retry(
                "GET",
                url,
                headers=headers,
                params=params,
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )

        try:
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            raise ConnectorTransientError(f"Box API error: {exc}") from exc

    def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
        stream: bool = False,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> requests.Response:
        """
        Execute HTTP request with intelligent retry logic.

        Rate Limit Handling:
        - Respects Retry-After header from Box
        - Falls back to exponential backoff if header missing
        - Maximum 3 retries before raising ConnectorRateLimitError

        Error Handling:
        - 401: Raise ConnectorAuthError (no retry)
        - 403: Raise ConnectorAuthError (no retry)
        - 404: Raise ItemNotFoundError (no retry)
        - 429: Backoff and retry
        - 5xx: Raise ConnectorTransientError (no retry)
        """
        headers = headers or {}
        attempt = 0

        while True:
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    timeout=timeout,
                    stream=stream,
                )
            except requests.RequestException as exc:
                raise ConnectorTransientError(f"Box network error: {exc}") from exc

            # Rate limit handling
            if response.status_code == 429:
                if attempt >= MAX_RETRIES:
                    raise ConnectorRateLimitError("Box rate limit exceeded after retries")

                # Respect Retry-After header
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = int(retry_after)
                    except ValueError:
                        delay = BASE_BACKOFF_SECONDS * (2 ** attempt)
                else:
                    # Exponential backoff fallback
                    delay = BASE_BACKOFF_SECONDS * (2 ** attempt)

                logger.warning(f"⏳ [Box] Rate limited, retrying in {delay}s (attempt {attempt + 1})")
                response.close()
                time.sleep(delay)
                attempt += 1
                continue

            # Auth errors - no retry
            if response.status_code == 401:
                response.close()
                raise ConnectorAuthError("Box token invalid or expired")

            if response.status_code == 403:
                response.close()
                raise ConnectorAuthError("Box access denied - insufficient permissions")

            # Not found - no retry
            if response.status_code == 404:
                response.close()
                raise ItemNotFoundError("Box item not found")

            # Server errors - no retry
            if response.status_code >= 500:
                detail = response.text[:500] if response.text else "No details"
                response.close()
                raise ConnectorTransientError(f"Box server error: {detail}")

            return response

    # =========================================================================
    # File Discovery - list_files()
    # =========================================================================

    def list_files(
        self,
        config: dict,
        since: datetime | None = None,
    ) -> Iterator[RemoteFile]:
        """
        List files from Box with folder tree navigation.

        Behavior:
        - If parent_id is None/"root"/empty: List root folder
        - If parent_id is set: List that specific folder
        - If recursive=True: Traverse entire subtree

        Filtering:
        - If since is provided, only yield files with modified_at >= since
        """
        resolved = self._resolve_config(config)

        parent_id = resolved.get("parent_id")
        folder_id = self._normalize_folder_id(parent_id)
        recursive = resolved.get("recursive", parent_id is None)
        include_folders = resolved.get("include_folders", True)

        if recursive:
            # Full recursive traversal
            yield from self._traverse_recursive(resolved, folder_id, since, include_folders)
        else:
            # Single folder listing
            yield from self._list_single_folder(resolved, folder_id, since, include_folders)

    def _list_folder_items(
        self,
        config: dict,
        folder_id: str,
    ) -> Iterator[dict]:
        """
        List all items in a folder with automatic pagination.

        Uses offset-based pagination with limit=1000 for efficiency.
        """
        offset = 0

        while True:
            try:
                response = self._request(
                    config,
                    f"/folders/{folder_id}/items",
                    params={
                        "limit": PAGE_SIZE,
                        "offset": offset,
                        "fields": ITEM_FIELDS,
                    }
                )
            except ItemNotFoundError:
                logger.warning(f"⚠️ [Box] Folder not found: {folder_id}")
                return
            except ConnectorAuthError as e:
                # 403 on specific folder - log and skip
                if "access denied" in str(e).lower():
                    logger.warning(f"⚠️ [Box] Access denied to folder {folder_id}, skipping")
                    return
                raise

            entries = response.get("entries", [])
            yield from entries

            total_count = response.get("total_count", 0)
            offset += len(entries)

            if offset >= total_count or not entries:
                break

    def _traverse_recursive(
        self,
        config: dict,
        root_folder_id: str,
        since: datetime | None = None,
        include_folders: bool = True,
    ) -> Iterator[RemoteFile]:
        """
        Recursively traverse folder tree using iterative BFS.

        Uses a queue to avoid stack overflow for deep folder structures.
        Gracefully handles 403 errors on restricted folders.
        """
        queue: deque[str] = deque([root_folder_id])
        visited: set[str] = set()

        while queue:
            folder_id = queue.popleft()

            if folder_id in visited:
                continue
            visited.add(folder_id)

            try:
                for item in self._list_folder_items(config, folder_id):
                    item_type = item.get("type")

                    if item_type == "folder":
                        # Add subfolder to queue
                        queue.append(item["id"])

                        if include_folders:
                            remote_file = self._item_to_remote_file(item, since, is_folder=True)
                            if remote_file:
                                yield remote_file

                    elif item_type == "file":
                        remote_file = self._item_to_remote_file(item, since, is_folder=False)
                        if remote_file:
                            yield remote_file

            except ConnectorAuthError as e:
                # 403 on specific folder - skip but continue with others
                if "access denied" in str(e).lower():
                    logger.warning(f"⚠️ [Box] Access denied to folder {folder_id}, skipping")
                    continue
                raise

    def _list_single_folder(
        self,
        config: dict,
        folder_id: str,
        since: datetime | None = None,
        include_folders: bool = True,
    ) -> Iterator[RemoteFile]:
        """List contents of a single folder (non-recursive)."""
        for item in self._list_folder_items(config, folder_id):
            item_type = item.get("type")

            if item_type == "folder" and not include_folders:
                continue

            remote_file = self._item_to_remote_file(
                item,
                since,
                is_folder=(item_type == "folder"),
            )
            if remote_file:
                yield remote_file

    def _item_to_remote_file(
        self,
        item: dict,
        since: datetime | None = None,
        is_folder: bool = False,
    ) -> RemoteFile | None:
        """
        Convert Box item to RemoteFile with deterministic ID.

        CRITICAL: Uses box://{file_id} format for delete reconciliation.
        This ensures IDs are stable across syncs for ghost file detection.

        Returns None for:
        - Files modified before 'since' timestamp
        """
        item_id = item.get("id")
        name = item.get("name")

        if is_folder:
            return RemoteFile(
                id=self._build_canonical_source_id(item_id, is_folder=True),
                name=name,
                mime_type="inode/directory",
                size=None,
                modified_at=None,
                parent_id=self._get_parent_id(item),
                web_view_url=f"https://app.box.com/folder/{item_id}",
            )

        # Parse modification time
        modified_str = item.get("modified_at")
        modified_at = self._parse_datetime(modified_str)

        # Apply 'since' filter for incremental sync
        if since and modified_at and modified_at < since:
            return None

        return RemoteFile(
            id=self._build_canonical_source_id(item_id, is_folder=False),
            name=name,
            mime_type=self._guess_mime_type(name),
            size=item.get("size"),
            modified_at=modified_at,
            parent_id=self._get_parent_id(item),
            web_view_url=f"https://app.box.com/file/{item_id}",
        )

    def _build_canonical_source_id(self, box_id: str, is_folder: bool = False) -> str:
        """
        Build deterministic source ID for delete reconciliation.

        Format: box://file/{file_id} or box://folder/{folder_id}

        This ID MUST be:
        - Deterministic (same input = same output)
        - Unique across all sources
        - Stable (doesn't change on re-sync)
        """
        item_type = "folder" if is_folder else "file"
        return f"box://{item_type}/{box_id}"

    def _extract_box_id_from_source_id(self, source_id: str) -> str:
        """
        Extract Box file ID from canonical source ID.

        Handles both formats:
        - Canonical: box://file/123456789
        - Raw Box ID: 123456789
        """
        if source_id.startswith("box://"):
            # Extract ID from canonical format
            parts = source_id.split("/")
            return parts[-1] if parts else source_id
        return source_id

    # =========================================================================
    # Content Fetching - fetch_file_content() & fetch_documents()
    # =========================================================================

    def fetch_file_content(self, file_id: str, config: dict) -> bytes:
        """
        Fetch raw file bytes from Box.

        Args:
            file_id: Box file ID
            config: Configuration with credentials

        Returns:
            Raw file content as bytes
        """
        resolved = self._resolve_config(config)
        return self._download_file_content(resolved, file_id)

    async def fetch_documents(
        self,
        item_ids: list[str],
        credentials: dict[str, Any] | None = None,
        **kwargs,
    ) -> AsyncIterator[SourceDocument]:
        """Async wrapper for fetch_documents_sync."""
        for doc in self.fetch_documents_sync(item_ids, credentials, **kwargs):
            yield doc

    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: dict[str, Any] | None = None,
        **kwargs,
    ) -> Iterator[SourceDocument]:
        """
        Fetch documents from Box for ingestion pipeline.

        PRODUCTION SAFEGUARDS:
        - Handles canonical IDs (box://file/{id}) and raw Box IDs
        - Continues on individual file errors (doesn't fail entire job)
        - Deduplicates items to prevent double processing

        Handles:
        - Single files: Download directly
        - Folders: Recursive traversal and download all files

        Args:
            item_ids: List of Box file/folder IDs (raw or canonical format)
            credentials: Optional credentials dict
            **kwargs: Additional params including user_id, integration_id
        """
        if not item_ids:
            return

        # Build config from credentials and kwargs
        config = self._build_config(credentials, **kwargs)
        resolved = self._resolve_config(config)

        logger.info(f"📥 [BoxConnector] Fetching {len(item_ids)} item(s)")

        processed_ids: set[str] = set()  # Deduplication by raw Box ID
        failed_count = 0

        for item_id in item_ids:
            # Extract raw Box ID from canonical format if needed
            raw_box_id = self._extract_box_id_from_source_id(item_id)

            try:
                # Get item metadata to determine type
                metadata = self._get_item_metadata(resolved, raw_box_id)
                item_type = metadata.get("type")

                if item_type == "folder":
                    # Expand folder to all files
                    logger.info(f"📁 [Box] Expanding folder: {metadata.get('name')}")
                    yield from self._fetch_folder_documents(resolved, raw_box_id, processed_ids)
                elif item_type == "file":
                    # Single file
                    if raw_box_id not in processed_ids:
                        processed_ids.add(raw_box_id)
                        yield self._build_source_document(resolved, metadata)

            except ItemNotFoundError:
                logger.warning(f"⚠️ [Box] Not found: {item_id}")
                continue
            except ConnectorAuthError:
                raise  # Re-raise auth errors
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ [Box] Failed to fetch {item_id}: {e}")
                continue

        logger.info(
            f"📥 [BoxConnector] Fetched {len(processed_ids)} files "
            f"({failed_count} failed)"
        )

    def _get_item_metadata(self, config: dict, item_id: str) -> dict:
        """
        Get metadata for a file or folder.

        Tries file endpoint first, then folder endpoint.
        """
        # Try as file first (most common case)
        try:
            return self._request(
                config,
                f"/files/{item_id}",
                params={"fields": ITEM_FIELDS},
            )
        except ItemNotFoundError:
            pass

        # Try as folder
        try:
            result = self._request(
                config,
                f"/folders/{item_id}",
                params={"fields": ITEM_FIELDS},
            )
            result["type"] = "folder"  # Ensure type is set
            return result
        except ItemNotFoundError:
            raise ItemNotFoundError(f"Box item not found: {item_id}")

    def _download_file_content(
        self,
        config: dict,
        file_id: str,
        file_size: int | None = None,
    ) -> bytes:
        """
        Download file content with streaming and resilience.

        Production Safeguards:
        - Uses streaming to avoid loading full file into memory
        - Large files (>50MB) use Range requests for resilience
        - Chunks of 1MB for efficient memory usage
        - Enforces MAX_FILE_SIZE limit
        - Box may return 302 redirect to CDN - requests follows automatically

        Args:
            config: Configuration with credentials
            file_id: Box file ID
            file_size: Optional known file size (avoids extra HEAD request)
        """
        # Use chunked download for large files
        if file_size and file_size >= LARGE_FILE_THRESHOLD:
            return self._download_large_file_chunked(config, file_id, file_size)

        # Standard streaming download for smaller files
        url = f"{BOX_API_BASE}/files/{file_id}/content"
        headers = self._get_headers(config)

        with connector_fetch_limit("box"):
            response = self._request_with_retry(
                "GET",
                url,
                headers=headers,
                stream=True,
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            response.close()
            raise ConnectorTransientError(f"Box download error: {exc}") from exc

        # Stream to buffer with size limit check
        buffer = io.BytesIO()
        total_size = 0

        for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
            if chunk:
                total_size += len(chunk)
                if total_size > settings.MAX_FILE_SIZE:
                    response.close()
                    raise FileTooLargeError(
                        f"File exceeds {settings.MAX_FILE_SIZE} byte limit"
                    )
                buffer.write(chunk)

        response.close()
        return buffer.getvalue()

    def _download_large_file_chunked(
        self,
        config: dict,
        file_id: str,
        content_length: int,
    ) -> bytes:
        """
        Download large file using Range requests for resilience.

        If a chunk fails, we retry that specific chunk, not the whole file.
        This prevents wasting bandwidth on partial downloads.
        """
        buffer = io.BytesIO()
        downloaded = 0

        logger.info(
            f"📦 [Box] Large file download ({content_length:,} bytes) "
            f"using Range requests: file_id={file_id}"
        )

        url = f"{BOX_API_BASE}/files/{file_id}/content"

        while downloaded < content_length:
            end = min(downloaded + CHUNK_SIZE - 1, content_length - 1)
            range_header = f"bytes={downloaded}-{end}"

            for attempt in range(MAX_RETRIES):
                try:
                    headers = self._get_headers(config)
                    headers["Range"] = range_header

                    with connector_fetch_limit("box"):
                        response = self._request_with_retry(
                            "GET",
                            url,
                            headers=headers,
                            stream=True,
                            timeout=DOWNLOAD_TIMEOUT_SECONDS,
                        )

                    chunk_data = response.content
                    response.close()

                    buffer.write(chunk_data)
                    downloaded += len(chunk_data)
                    break

                except (ConnectorTransientError, ConnectorRateLimitError) as e:
                    if attempt == MAX_RETRIES - 1:  # Final attempt
                        raise ConnectorTransientError(
                            f"Failed to download chunk {range_header} after {MAX_RETRIES} attempts: {e}"
                        )

                    delay = BASE_BACKOFF_SECONDS * (2 ** attempt)
                    logger.warning(
                        f"⏳ [Box] Chunk download failed, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES})"
                    )
                    time.sleep(delay)

        logger.info(f"✅ [Box] Large file download complete: file_id={file_id}")
        return buffer.getvalue()

    def _fetch_folder_documents(
        self,
        config: dict,
        folder_id: str,
        processed_ids: set[str],
    ) -> Iterator[SourceDocument]:
        """
        Recursively fetch all documents in a folder.

        PRODUCTION SAFEGUARDS:
        - Continues on individual file errors
        - Deduplicates by raw Box ID
        - Logs progress for monitoring
        """
        # Use recursive traversal to get all files
        folder_config = {
            **config,
            "parent_id": folder_id,
            "recursive": True,
            "include_folders": False,
        }

        file_count = 0
        failed_count = 0

        for remote_file in self.list_files(folder_config):
            # Extract raw Box ID from canonical source ID
            raw_box_id = self._extract_box_id_from_source_id(remote_file.id)

            if raw_box_id in processed_ids:
                continue

            try:
                # Get full metadata
                metadata = self._request(
                    config,
                    f"/files/{raw_box_id}",
                    params={"fields": ITEM_FIELDS},
                )

                processed_ids.add(raw_box_id)
                file_count += 1
                yield self._build_source_document(config, metadata)

            except Exception as e:
                failed_count += 1
                logger.error(f"❌ [Box] Failed to fetch {remote_file.name}: {e}")
                continue

        logger.info(
            f"📂 [Box] Expanded folder to {file_count} files "
            f"({failed_count} failed)"
        )

    def _build_source_document(
        self,
        config: dict,
        metadata: dict,
    ) -> SourceDocument:
        """
        Build SourceDocument from Box metadata with deterministic source_id.

        CRITICAL: Uses box://file/{id} format for delete reconciliation.
        """
        file_id = metadata.get("id")
        name = metadata.get("name")
        file_size = metadata.get("size", 0)
        parent_folder_id = self._normalize_folder_id(self._get_parent_id(metadata))
        folder_name = self._get_folder_name(config, parent_folder_id)

        # Download content with appropriate strategy
        content = self._download_file_content(config, file_id, file_size)

        doc_metadata = {
            "source": "box",
            "box_id": file_id,
            "folder_id": parent_folder_id,
            "folder_name": folder_name,
            "sha1": metadata.get("sha1"),
            "modified_at": metadata.get("modified_at"),
            "size": metadata.get("size"),
            "parent_id": self._get_parent_id(metadata),
        }
        doc_metadata["scope_id"] = build_scope_uri("box", doc_metadata)

        return SourceDocument(
            content=content,
            metadata=doc_metadata,
            source_type=SourceType.BOX,
            source_id=self._build_canonical_source_id(file_id, is_folder=False),  # DETERMINISTIC!
            filename=name,
            mime_type=self._guess_mime_type(name),
            size_bytes=len(content),
            parent_id=self._get_parent_id(metadata),
        )

    # =========================================================================
    # Configuration Resolution
    # =========================================================================

    def _build_config(
        self,
        credentials: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Build configuration dict by merging credentials with kwargs."""
        return build_config_from_kwargs(credentials, **kwargs)

    def _resolve_config(self, config: dict) -> dict:
        """
        Resolve configuration, fetching tokens from database if needed.
        """
        resolved = dict(config or {})

        # If access_token already provided, return as-is
        if resolved.get("access_token"):
            return resolved

        # Load integration from database
        integration = self._load_integration(resolved)

        # Check if integration needs reconnection
        if integration.get("status") == "reconnection_required":
            raise ConnectorAuthError(
                integration.get("status_message", "Please reconnect your Box account.")
            )

        try:
            creds = OAuthTokenManager.get_valid_credentials(integration, "box")
        except TokenRefreshError as exc:
            raise ConnectorAuthError("Box integration requires reconnection") from exc

        resolved["access_token"] = creds.get("access_token")
        resolved["refresh_token"] = creds.get("refresh_token")
        resolved["expires_at"] = creds.get("expires_at")
        resolved["integration_id"] = creds.get("integration_id") or integration.get("id")

        return resolved

    def _load_integration(self, config: dict) -> dict[str, Any]:
        """Load integration record from database using shared utility."""
        return load_integration(
            "box",
            integration_id=config.get("integration_id"),
            user_id=config.get("user_id"),
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _normalize_folder_id(self, folder_id: str | None) -> str:
        """Normalize folder ID, treating None/empty/"root" as root folder."""
        if not folder_id or folder_id.lower() in ("root", ""):
            return ROOT_FOLDER_ID
        return folder_id

    def _get_parent_id(self, item: dict) -> str | None:
        """Extract parent folder ID from item."""
        parent = item.get("parent")
        if parent and isinstance(parent, dict):
            return parent.get("id")
        return None

    def _get_folder_name(self, config: dict, folder_id: str) -> str:
        """
        Resolve folder name for canonical scope URI generation.
        """
        folder_id = self._normalize_folder_id(folder_id)
        cached = self._folder_name_cache.get(folder_id)
        if cached:
            return cached
        try:
            result = self._request(
                config,
                f"/folders/{folder_id}",
                params={"fields": "id,name"},
            )
            name = result.get("name") or "root"
        except Exception as exc:
            logger.warning("⚠️ [Box] Failed to resolve folder name for %s: %s", folder_id, exc)
            name = "root"
        self._folder_name_cache[folder_id] = name
        return name

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Parse Box ISO 8601 timestamp."""
        if not value:
            return None
        try:
            # Box format: 2012-12-12T10:53:43-08:00
            if value.endswith("Z"):
                value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _guess_mime_type(filename: str | None) -> str:
        """Guess MIME type from filename."""
        if not filename:
            return "application/octet-stream"
        guessed, _ = mimetypes.guess_type(filename)
        if guessed:
            return guessed
        return COMMON_MIME_TYPES.get(Path(filename).suffix.lower(), "application/octet-stream")


# =============================================================================
# Module-level Connector Instance (for registry patterns)
# =============================================================================

def get_box_connector() -> BoxConnector:
    """Factory function to get a BoxConnector instance."""
    return BoxConnector()
