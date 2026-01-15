# Box Connector Design Specification

**Version:** 1.0  
**Author:** Principal Software Architect  
**Date:** January 2026  
**Status:** Design Review

---

## Executive Summary

This document outlines the technical design for integrating Box cloud storage into the Axio platform. The connector follows the established `EnhancedConnector` pattern, using raw HTTP requests (no SDK) for full control over authentication, rate limiting, and streaming.

---

## 1. Architectural Analysis & Decisions

### 1.A. Authentication Strategy (OAuth 2.0)

#### Token Lifecycle

| Property | Box Behavior |
|----------|-------------|
| Access Token Lifetime | **60 minutes** (3600 seconds) |
| Refresh Token Lifetime | **60 days** (single-use, rotated on each refresh) |
| Token Type | Bearer |
| Auth Server | `https://api.box.com/oauth2/token` |

#### Token Management Strategy

Box uses **rotating refresh tokens** - each refresh returns a NEW refresh token, invalidating the previous one. This requires atomic database updates to prevent race conditions.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Token Refresh Flow                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Check expires_at with 5-minute buffer                       │
│  2. If expired → POST /oauth2/token with refresh_token          │
│  3. Receive: { access_token, refresh_token, expires_in }        │
│  4. ATOMIC UPDATE in DB (both tokens + new expires_at)          │
│  5. Return new access_token to caller                           │
│                                                                 │
│  ⚠️ CRITICAL: Box refresh tokens are SINGLE-USE                 │
│     - Must update refresh_token immediately                     │
│     - Concurrent requests must be serialized                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation in `OAuthTokenManager`:**

```python
@staticmethod
def refresh_box_token(
    integration_id: str,
    access_token: str,
    refresh_token: str,
    expires_at: Optional[str] = None,
) -> tuple[str, str, Optional[str]]:
    """
    Refresh Box OAuth token.
    
    CRITICAL: Box refresh tokens are single-use and rotate on each refresh.
    Must atomically update BOTH access_token AND refresh_token.
    
    Returns:
        Tuple of (new_access_token, new_refresh_token, new_expires_at)
    """
```

#### OAuth Scopes

| Scope | Permission | Recommendation |
|-------|------------|----------------|
| `root_readonly` | Read all files/folders | ✅ **Minimum required** |
| `root_readwrite` | Read + Write + Delete | ❌ Not needed |
| `manage_managed_users` | Enterprise user management | ❌ Not needed |

**Recommendation:** Use `root_readonly` scope only. This follows the principle of least privilege.

#### Enterprise vs. Personal Accounts

| Feature | Personal | Enterprise (Business/Enterprise) |
|---------|----------|----------------------------------|
| Root Folder | Folder ID `0` | Folder ID `0` (same) |
| Shared Folders | Via collaborations | Via collaborations |
| Admin Console | No | Yes |
| User Management | No | Yes |
| API Behavior | Standard | Standard (no special handling needed) |

**Key Difference:** Enterprise accounts may have **Admin-created folders** with restricted access. The connector should gracefully handle 403 errors on specific folders without failing the entire sync.

**Implementation Note:** Unlike Dropbox (which requires namespace headers for Team accounts), Box uses the same API for both Personal and Enterprise - the user's view is automatically scoped to their accessible content.

---

### 1.B. Traversal Strategy (Folder Structure)

#### Box Folder API Overview

| Endpoint | Purpose |
|----------|---------|
| `GET /folders/0` | Get root folder metadata |
| `GET /folders/{id}` | Get folder metadata |
| `GET /folders/{id}/items` | List folder contents (paginated) |
| `GET /files/{id}` | Get file metadata |
| `GET /files/{id}/content` | Download file content |

#### Root Folder Handling

Box uses folder ID `"0"` for the root folder (not a path like Dropbox).

```python
ROOT_FOLDER_ID = "0"

def _normalize_folder_id(self, folder_id: Optional[str]) -> str:
    """Normalize folder ID, treating None/empty/"root" as root folder."""
    if not folder_id or folder_id.lower() in ("root", ""):
        return ROOT_FOLDER_ID
    return folder_id
```

#### Pagination Strategy

Box uses **offset-based pagination** (NOT cursor-based like Dropbox):

| Parameter | Type | Default | Max |
|-----------|------|---------|-----|
| `limit` | int | 100 | 1000 |
| `offset` | int | 0 | - |

```
┌─────────────────────────────────────────────────────────────────┐
│                  Pagination Flow                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Page 1: GET /folders/123/items?limit=1000&offset=0             │
│          → Returns items 0-999, total_count=2500                │
│                                                                 │
│  Page 2: GET /folders/123/items?limit=1000&offset=1000          │
│          → Returns items 1000-1999                              │
│                                                                 │
│  Page 3: GET /folders/123/items?limit=1000&offset=2000          │
│          → Returns items 2000-2499                              │
│                                                                 │
│  Stop when: offset >= total_count                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation:**

```python
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
    limit = 1000  # Box maximum
    
    while True:
        response = self._request(
            config,
            f"/folders/{folder_id}/items",
            params={
                "limit": limit,
                "offset": offset,
                "fields": ITEM_FIELDS,
            }
        )
        
        entries = response.get("entries", [])
        yield from entries
        
        total_count = response.get("total_count", 0)
        offset += len(entries)
        
        if offset >= total_count or not entries:
            break
```

#### Recursive Traversal Strategy

For deep folder structures, use **iterative BFS** (Breadth-First Search) to avoid stack overflow:

```python
def _traverse_folder_recursive(
    self,
    config: dict,
    root_folder_id: str,
) -> Iterator[dict]:
    """
    Recursively traverse folder tree using iterative BFS.
    
    Yields all files found. Folders are used for traversal only.
    """
    from collections import deque
    
    queue = deque([root_folder_id])
    visited = set()
    
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
                elif item_type == "file":
                    yield item
                    
        except ConnectorAuthError:
            # 403 on specific folder - skip but continue
            logger.warning(f"⚠️ [Box] Access denied to folder {folder_id}, skipping")
            continue
```

#### Field Selection (Bandwidth Optimization)

Request only needed fields to minimize response size:

```python
# Minimal fields for file listing
ITEM_FIELDS = "id,name,type,size,sha1,modified_at,parent"

# Extended fields for metadata (when needed)
METADATA_FIELDS = "id,name,type,size,sha1,modified_at,parent,created_at,path_collection"
```

**Field Definitions:**

| Field | Type | Purpose |
|-------|------|---------|
| `id` | string | Unique item identifier |
| `name` | string | Display name |
| `type` | string | "file" or "folder" |
| `size` | int | File size in bytes |
| `sha1` | string | Content hash (for deduplication) |
| `modified_at` | datetime | Last modification time |
| `parent` | object | Parent folder info |
| `path_collection` | object | Full path breadcrumbs |

---

### 1.C. Rate Limiting (429 Handling)

#### Box Rate Limits

| Account Type | Limit |
|--------------|-------|
| Free/Personal | 10 requests/second |
| Business | 1,000 requests/minute |
| Enterprise | Higher (varies by contract) |

Box returns HTTP 429 with `Retry-After` header (in seconds).

#### Retry Strategy Implementation

```python
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1

def _request_with_retry(
    self,
    method: str,
    url: str,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
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
    - 401/403: Raise ConnectorAuthError (no retry)
    - 404: Raise ItemNotFoundError (no retry)
    - 429: Backoff and retry
    - 5xx: Raise ConnectorTransientError (no retry)
    """
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
                delay = int(retry_after)
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
        
        # Server errors - no retry (let caller handle)
        if response.status_code >= 500:
            detail = response.text[:500] if response.text else "No details"
            response.close()
            raise ConnectorTransientError(f"Box server error: {detail}")
        
        return response
```

---

### 1.D. Content Fetching

#### Download Endpoint

```
GET https://api.box.com/2.0/files/{file_id}/content
Authorization: Bearer {access_token}
```

**Response:** 302 redirect to download URL, or direct content stream.

#### Streaming Implementation

**CRITICAL:** Use `stream=True` to avoid loading entire file into memory:

```python
DOWNLOAD_TIMEOUT_SECONDS = 120
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB limit

def _download_file_content(
    self,
    config: dict,
    file_id: str,
) -> bytes:
    """
    Download file content with streaming.
    
    Memory Safety:
    - Uses streaming to avoid loading full file into memory
    - Chunks of 1MB for efficient memory usage
    - Enforces MAX_FILE_SIZE limit
    
    Redirect Handling:
    - Box may return 302 redirect to CDN
    - requests follows redirects automatically
    """
    url = f"{BOX_API_BASE}/files/{file_id}/content"
    headers = self._get_headers(config)
    
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
            if total_size > MAX_FILE_SIZE:
                response.close()
                raise FileTooLargeError(f"File exceeds {MAX_FILE_SIZE} byte limit")
            buffer.write(chunk)
    
    response.close()
    return buffer.getvalue()
```

---

## 2. Implementation Plan

### 2.1. Class Structure

```python
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
"""

from __future__ import annotations

import io
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
from connectors.enhanced import (
    EnhancedConnector,
    SourceDocument,
    SourceType,
    ItemNotFoundError,
    FileTooLargeError,
)
from connectors.limits import connector_fetch_limit
from core.db import get_supabase
from core.config import settings
from services.oauth_token_manager import OAuthTokenManager, TokenRefreshError

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

BOX_API_BASE = "https://api.box.com/2.0"
BOX_UPLOAD_BASE = "https://upload.box.com/api/2.0"  # Not used for read-only
ROOT_FOLDER_ID = "0"

DEFAULT_TIMEOUT_SECONDS = 30
DOWNLOAD_TIMEOUT_SECONDS = 120
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Minimal fields for efficient listing
ITEM_FIELDS = "id,name,type,size,sha1,modified_at,parent"


class BoxConnector(EnhancedConnector, BaseConnector):
    """
    Box connector for unified ingestion pipeline.
    
    Features:
    - OAuth token refresh with rotating refresh tokens
    - Recursive folder traversal with pagination
    - Streaming file downloads
    - Rate limit handling with Retry-After support
    - Enterprise and Personal account support
    """
    
    @property
    def connector_type(self) -> SourceType:
        return SourceType.BOX  # Add to SourceType enum
    
    @property
    def supports_incremental_sync(self) -> bool:
        return True
    
    @property
    def supports_batch_fetch(self) -> bool:
        return False  # Box doesn't support batch downloads
```

### 2.2. Key Methods Specification

#### `validate_config()`

```python
def validate_config(self, config: dict) -> bool:
    """
    Validate Box configuration.
    
    Validation Strategy:
    - Call GET /users/me to verify token validity
    - Returns user info if successful
    
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
    """Verify token by calling GET /users/me."""
    url = f"{BOX_API_BASE}/users/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 401:
            raise ConnectorAuthError("Box token invalid or expired")
        
        if response.status_code != 200:
            raise ConnectorTransientError(f"Box API error: {response.text[:200]}")
        
        return response.json()
    except requests.RequestException as exc:
        raise ConnectorTransientError(f"Box connection error: {exc}") from exc
```

#### `list_files()`

```python
def list_files(
    self,
    config: dict,
    since: Optional[datetime] = None,
) -> Iterator[RemoteFile]:
    """
    List files from Box with folder tree navigation.
    
    Behavior:
    - If parent_id is None/"root"/empty: List root folder
    - If parent_id is set: List that specific folder
    - If recursive=True: Traverse entire subtree
    
    Filtering:
    - If since is provided, only yield files with modified_at >= since
    
    Navigation:
    - Folders are yielded with mime_type="inode/directory"
    - Files are yielded with actual MIME types
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
```

#### `fetch_documents_sync()`

```python
def fetch_documents_sync(
    self,
    item_ids: list[str],
    credentials: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Iterator[SourceDocument]:
    """
    Fetch documents from Box for ingestion pipeline.
    
    Handles:
    - Single files: Download directly
    - Folders: Recursive traversal and download all files
    
    Args:
        item_ids: List of Box file/folder IDs
        credentials: Optional credentials dict
        **kwargs: Additional params including user_id, integration_id
    """
    if not item_ids:
        return
    
    # Build config from credentials and kwargs
    config = self._build_config(credentials, **kwargs)
    resolved = self._resolve_config(config)
    
    logger.info(f"📥 [BoxConnector] Fetching {len(item_ids)} item(s)")
    
    processed_ids: set[str] = set()  # Deduplication
    
    for item_id in item_ids:
        try:
            # Get item metadata to determine type
            metadata = self._get_item_metadata(resolved, item_id)
            item_type = metadata.get("type")
            
            if item_type == "folder":
                # Expand folder to all files
                logger.info(f"📁 [Box] Expanding folder: {metadata.get('name')}")
                yield from self._fetch_folder_documents(resolved, item_id, processed_ids)
            elif item_type == "file":
                # Single file
                if item_id not in processed_ids:
                    processed_ids.add(item_id)
                    yield self._build_source_document(resolved, metadata)
                    
        except ItemNotFoundError:
            logger.warning(f"⚠️ [Box] Not found: {item_id}")
            continue
        except ConnectorAuthError:
            raise  # Re-raise auth errors
        except Exception as e:
            logger.error(f"❌ [Box] Failed to fetch {item_id}: {e}")
            continue
    
    logger.info(f"📥 [BoxConnector] Fetched {len(processed_ids)} files")
```

### 2.3. File Structure

```
backend/connectors/box.py
├── Constants
│   ├── BOX_API_BASE
│   ├── ROOT_FOLDER_ID
│   ├── Timeout constants
│   └── ITEM_FIELDS
│
├── BoxConnector(EnhancedConnector, BaseConnector)
│   ├── Properties
│   │   ├── connector_type → SourceType.BOX
│   │   ├── supports_incremental_sync → True
│   │   └── supports_batch_fetch → False
│   │
│   ├── Configuration & Validation
│   │   ├── validate_config()
│   │   ├── _verify_token()
│   │   ├── _resolve_config()
│   │   ├── _load_integration()
│   │   └── _build_config()
│   │
│   ├── HTTP Layer
│   │   ├── _get_headers()
│   │   ├── _request()
│   │   ├── _request_with_retry()
│   │   └── _parse_retry_after()
│   │
│   ├── File Discovery
│   │   ├── list_files()
│   │   ├── _list_folder_items()
│   │   ├── _traverse_recursive()
│   │   ├── _list_single_folder()
│   │   └── _item_to_remote_file()
│   │
│   ├── Content Fetching
│   │   ├── fetch_file_content()
│   │   ├── fetch_documents() [async]
│   │   ├── fetch_documents_sync()
│   │   ├── _download_file_content()
│   │   ├── _fetch_folder_documents()
│   │   └── _build_source_document()
│   │
│   └── Helpers
│       ├── _normalize_folder_id()
│       ├── _get_item_metadata()
│       ├── _parse_datetime()
│       └── _guess_mime_type()
│
└── get_box_connector() - Factory function
```

---

## 3. Integration Requirements

### 3.1. Configuration Changes

**`core/config.py`:**
```python
# Box OAuth Configuration
BOX_CLIENT_ID: str = ""
BOX_CLIENT_SECRET: str = ""
BOX_REDIRECT_URI: str = ""
```

**Environment Variables:**
```bash
BOX_CLIENT_ID=your_client_id
BOX_CLIENT_SECRET=your_client_secret
BOX_REDIRECT_URI=https://app.axiohub.io/oauth/callback
```

### 3.2. SourceType Enum Extension

**`connectors/enhanced.py`:**
```python
class SourceType(str, Enum):
    # ... existing types ...
    BOX = "box"
```

### 3.3. OAuthTokenManager Extension

**`services/oauth_token_manager.py`:**
```python
@staticmethod
def refresh_box_token(
    integration_id: str,
    access_token: str,
    refresh_token: str,
    expires_at: Optional[str] = None,
) -> tuple[str, str, Optional[str]]:
    """
    Refresh Box OAuth token.
    
    CRITICAL: Box refresh tokens are SINGLE-USE.
    Each refresh returns a new refresh token that must be saved.
    """
    # Implementation as designed above
```

And in `get_valid_credentials()`:
```python
elif provider == 'box':
    new_access, new_refresh, new_expires = OAuthTokenManager.refresh_box_token(
        integration_id,
        access_token,
        refresh_token,
        expires_at,
    )
    return {
        'access_token': new_access,
        'refresh_token': new_refresh,
        'expires_at': new_expires,
        'integration_id': integration_id
    }
```

### 3.4. Connector Registry

**`connectors/registry.py`:**
```python
from connectors.box import BoxConnector

CONNECTOR_REGISTRY = {
    # ... existing connectors ...
    "box": BoxConnector,
}
```

### 3.5. API Endpoint Updates

**`api/v1/integrations.py`:**
```python
# Add 'box' to OAuth connectors list
if provider in ["google_drive", "notion", "onedrive", "sharepoint", "dropbox", "github", "box"]:
    # OAuth connectors: Pass integration_id for automatic token refresh
```

### 3.6. Database Migration

```sql
-- Add Box connector definition
INSERT INTO connector_definitions (type, name, description, category, icon_path)
VALUES (
    'box',
    'Box',
    'Connect to Box cloud storage to sync files and folders',
    'cloud',
    '/icons/box.svg'
);
```

---

## 4. Risk Assessment & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Rotating refresh token race condition | Medium | High | Use database-level locking or optimistic concurrency |
| Large folder traversal timeout | Medium | Medium | Implement pagination limits, use background jobs |
| Rate limiting during bulk sync | High | Medium | Respect Retry-After, implement request queuing |
| Enterprise folder permission errors | Medium | Low | Gracefully skip inaccessible folders, log warnings |
| Large file memory issues | Low | High | Streaming downloads with size limits |

---

## 5. Testing Strategy

### Unit Tests
- Token refresh with rotation
- Folder traversal pagination
- Rate limit retry logic
- File content streaming

### Integration Tests
- OAuth flow (manual or mocked)
- Full folder sync
- Incremental sync with `since` filter
- Error handling (404, 403, 429)

### Load Tests
- Large folder (10,000+ files)
- Deep nesting (20+ levels)
- Concurrent requests

---

## 6. Open Questions for Review

1. **Retry Token Race Condition:** Should we implement optimistic locking or database-level locking for refresh token updates?

2. **Enterprise Features:** Do we need to support Box's "As-User" header for admin impersonation?

3. **Webhooks:** Should we implement Box webhooks for real-time sync instead of polling?

4. **Shared Links:** Should we support ingesting files via Box shared links (anonymous access)?

---

## Appendix A: Box API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/oauth2/token` | POST | Token exchange/refresh |
| `/users/me` | GET | Validate token, get user info |
| `/folders/{id}` | GET | Get folder metadata |
| `/folders/{id}/items` | GET | List folder contents |
| `/files/{id}` | GET | Get file metadata |
| `/files/{id}/content` | GET | Download file content |

## Appendix B: Error Codes

| HTTP Status | Box Error | Our Exception |
|-------------|-----------|---------------|
| 401 | Invalid token | `ConnectorAuthError` |
| 403 | Forbidden | `ConnectorAuthError` |
| 404 | Not found | `ItemNotFoundError` |
| 429 | Rate limited | `ConnectorRateLimitError` (with retry) |
| 5xx | Server error | `ConnectorTransientError` |

---

**Document Status:** Ready for Architecture Review  
**Next Steps:** Upon approval, proceed to implementation phase
