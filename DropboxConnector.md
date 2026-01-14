# Dropbox Connector: Implementation Specification

> **Status**: ✅ IMPLEMENTED  
> **Version**: 2.0  
> **Last Updated**: 2026-01-14  
> **Author**: Architecture Team  
> **Implementation**: Complete with Team/Business Account Support

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architectural Decisions](#2-architectural-decisions)
3. [Codebase Audit Results](#3-codebase-audit-results)
4. [Gap Analysis](#4-gap-analysis)
5. [Implementation Specification](#5-implementation-specification)
6. [OAuth Flow Integration](#6-oauth-flow-integration)
7. [Database Requirements](#7-database-requirements)
8. [Testing Strategy](#8-testing-strategy)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Open Questions](#10-open-questions)

---

## 1. Executive Summary

### Objective
Design and implement a production-ready Dropbox connector within the Axial Unified Ingestion Pipeline.

### Context
- **Existing Connectors**: Google Drive, OneDrive, SharePoint, SFTP, Notion, Web
- **Foundation**: Duplicate File Detection (SHA-256) and Resilient Parsing (3-Tier Fallback) already implemented
- **Target**: Enterprise-grade integration with first-try success

### Key Decisions
| Decision | Approach | Rationale |
|----------|----------|-----------|
| SDK Usage | No official SDK | Full control over HTTP, timeouts, and rate limiting |
| API Style | Dual handling (RPC + Content) | Dropbox requires different patterns for metadata vs files |
| Sync Strategy | `server_modified` timestamp filtering | Compatible with `BaseConnector.list_files(since)` interface |

---

## 2. Architectural Decisions

### Decision A: No Official SDK

**Reason**: The official `dropbox` Python SDK is heavy (~50 dependencies) and obscures HTTP error handling.

**Strategy**: Use `requests` library directly for:
- Full control over timeouts
- Chunked streaming for large files
- Explicit "Retry-After" backoff logic for 429 responses
- Consistent error mapping to standard exceptions

**Reference Implementation**: `backend/connectors/microsoft.py` uses the same SDK-less approach.

---

### Decision B: Dual API Handling

**Technical Reality**: Dropbox uses two distinct API styles:

| API Style | Base URL | Parameters | Use Case |
|-----------|----------|------------|----------|
| **RPC** | `api.dropboxapi.com/2` | JSON body | Metadata operations (list, search, get_metadata) |
| **Content** | `content.dropboxapi.com/2` | `Dropbox-API-Arg` header | File transfer (download, upload) |

**Implementation Approach**:
```
DropboxConnector
├── _rpc_request()      → For api.dropboxapi.com endpoints
└── _content_download() → For content.dropboxapi.com endpoints
```

**Example - RPC Request**:
```http
POST https://api.dropboxapi.com/2/files/list_folder
Authorization: Bearer <token>
Content-Type: application/json

{"path": "", "recursive": true}
```

**Example - Content Request**:
```http
POST https://content.dropboxapi.com/2/files/download
Authorization: Bearer <token>
Dropbox-API-Arg: {"path": "/test.pdf"}

(empty body, response is file bytes)
```

---

### Decision C: Incremental Sync via `server_modified`

**Interface Constraint**: `BaseConnector.list_files(since: datetime | None)`

**Dropbox Options**:
1. **Cursor-based** (`/files/list_folder/continue` with delta cursor) - Requires state persistence
2. **Timestamp-based** (filter on `server_modified`) - Stateless, compatible with interface

**Chosen Approach**: Timestamp filtering during `list_folder` iteration

**Rationale**:
- Matches existing `since` parameter pattern
- No additional state management required
- Cursor-based sync can be Phase 2 enhancement

**Implementation**:
```python
def _entry_to_remote_file(self, entry: dict, since: Optional[datetime]) -> Optional[RemoteFile]:
    modified_at = self._parse_datetime(entry.get("server_modified"))
    
    # Apply incremental filter
    if since and modified_at and modified_at < since:
        return None  # Skip files not modified since last sync
    
    return RemoteFile(...)
```

---

## 3. Codebase Audit Results

### Base Interfaces Compatibility

**`BaseConnector` (backend/connectors/base.py)**:
```python
class BaseConnector(ABC):
    @abstractmethod
    def validate_config(self, config: dict) -> bool
    
    @abstractmethod
    def list_files(self, config: dict, since: datetime | None = None) -> Iterator[RemoteFile]
    
    @abstractmethod
    def fetch_file_content(self, file_id: str, config: dict) -> bytes
```
✅ **Compatible** - All methods can be implemented for Dropbox

**`EnhancedConnector` (backend/connectors/enhanced.py)**:
```python
class EnhancedConnector(BaseConnector):
    @abstractmethod
    async def fetch_documents(...) -> AsyncIterator[SourceDocument]
    
    @abstractmethod
    def fetch_documents_sync(...) -> Iterator[SourceDocument]
    
    @property
    def connector_type(self) -> SourceType
```
✅ **Compatible** - `SourceType.DROPBOX` already defined in enum

### Standard Exceptions

| Exception | Usage | Dropbox Mapping |
|-----------|-------|-----------------|
| `ConnectorAuthError` | Invalid/expired credentials | HTTP 401, 403 |
| `ConnectorRateLimitError` | Rate limit exceeded | HTTP 429 |
| `ConnectorTransientError` | Temporary failures | HTTP 5xx, network errors |
| `ItemNotFoundError` | File/folder not found | HTTP 409 with path error |

### Reference Implementation Analysis

**MicrosoftGraphConnector** demonstrates the SDK-less pattern:
- `_request_with_retry()` method with 429 handling
- Streaming downloads with `iter_content()`
- Pagination handling
- Token refresh integration

---

## 4. Gap Analysis

### A. Configuration Gaps

**File**: `backend/core/config.py`

**Required Additions**:
```python
# Dropbox OAuth
DROPBOX_CLIENT_ID: Optional[str] = None
DROPBOX_CLIENT_SECRET: Optional[str] = None
DROPBOX_REDIRECT_URI: Optional[str] = None

# Connector Concurrency
CONNECTOR_CONCURRENCY_DROPBOX: int = 2
```

---

### B. Registry Gap

**File**: `backend/connectors/registry.py`

**Required Addition**:
```python
"dropbox": {
    "id": "dropbox",
    "name": "Dropbox",
    "capabilities": ["binary_content", "incremental_sync"],
    "rate_limit_rpm": 720,  # Dropbox allows ~12 calls/sec baseline
},
```

---

### C. Concurrency Limits Gap

**File**: `backend/connectors/limits.py`

**Required Addition** to `_get_limit()`:
```python
if normalized == "dropbox":
    return settings.CONNECTOR_CONCURRENCY_DROPBOX
```

---

### D. OAuth Token Manager Gap

**File**: `backend/services/oauth_token_manager.py`

**Required**: New `refresh_dropbox_token()` method

**Dropbox Token Refresh Endpoint**:
```http
POST https://api.dropboxapi.com/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token=<REFRESH_TOKEN>
&client_id=<CLIENT_ID>
&client_secret=<CLIENT_SECRET>
```

**Response**:
```json
{
    "access_token": "sl.new_token...",
    "token_type": "bearer",
    "expires_in": 14400
}
```

---

### E. Existing Utilities to Reuse

| Utility | Location | Purpose |
|---------|----------|---------|
| `connector_fetch_limit()` | `connectors/limits.py` | Concurrency throttling |
| `RemoteFile` | `connectors/base.py` | `list_files()` return type |
| `SourceDocument` | `connectors/enhanced.py` | `fetch_documents()` return type |
| `encrypt_token()` / `decrypt_token()` | `core/security.py` | Token storage |
| `OAuthTokenManager` | `services/oauth_token_manager.py` | Token refresh orchestration |
| `with_retry_sync()` | `core/resilience.py` | Optional retry decorator |

---

## 5. Implementation Specification

### Module Structure

**File**: `backend/connectors/dropbox.py`

```
DropboxConnector (EnhancedConnector, BaseConnector)
│
├── Properties
│   ├── connector_type → SourceType.DROPBOX
│   └── supports_incremental_sync → True
│
├── Configuration & Auth
│   ├── validate_config(config: dict) → bool
│   ├── _verify_token(access_token: str) → dict
│   ├── _resolve_config(config: dict) → dict
│   └── _load_integration(config: dict) → dict
│
├── HTTP Layer (Private)
│   ├── _rpc_request(config, endpoint, body) → dict
│   ├── _content_download(config, path) → bytes
│   ├── _request_with_retry(method, url, **kwargs) → Response
│   ├── _auth_headers(config) → dict
│   └── _parse_retry_after(value, default) → int
│
├── File Discovery (BaseConnector)
│   ├── list_files(config, since) → Iterator[RemoteFile]
│   └── _entry_to_remote_file(entry, since) → Optional[RemoteFile]
│
├── Content Fetching (BaseConnector + EnhancedConnector)
│   ├── fetch_file_content(file_id, config) → bytes
│   ├── fetch_documents(item_ids, credentials, **kwargs) → AsyncIterator[SourceDocument]
│   ├── fetch_documents_sync(item_ids, credentials, **kwargs) → Iterator[SourceDocument]
│   ├── _fetch_folder_documents(config, folder_path) → Iterator[SourceDocument]
│   └── _build_source_document(config, metadata) → SourceDocument
│
└── Helpers
    ├── _get_parent_path(path_display) → Optional[str]
    ├── _parse_datetime(iso_str) → Optional[datetime]
    └── _guess_mime_type(filename) → str
```

---

### API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/users/get_current_account` | RPC | Token validation |
| `/files/list_folder` | RPC | List directory contents |
| `/files/list_folder/continue` | RPC | Pagination cursor |
| `/files/get_metadata` | RPC | Get file/folder info |
| `/files/download` | Content | Download file bytes |

---

### Error Handling Matrix

| HTTP Status | Dropbox Meaning | Mapped Exception | Action |
|-------------|-----------------|------------------|--------|
| 200 | Success | - | Return response |
| 401 | Bad/expired token | `ConnectorAuthError` | Fail, require reconnect |
| 403 | Forbidden | `ConnectorAuthError` | Fail, check permissions |
| 409 | Endpoint-specific error | `ItemNotFoundError` or `ConnectorTransientError` | Parse error tag |
| 429 | Rate limited | `ConnectorRateLimitError` | Retry with backoff |
| 5xx | Server error | `ConnectorTransientError` | Retry |

---

### Rate Limiting Strategy

**Dropbox Limits**:
- Basic: 12,000 requests/minute (200/sec burst allowed briefly)
- Per-user: Varies by endpoint

**Implementation**:
```python
def _request_with_retry(self, method, url, ...):
    attempt = 0
    while True:
        response = requests.request(method, url, ...)
        
        if response.status_code == 429:
            if attempt >= MAX_RETRIES:
                raise ConnectorRateLimitError("Dropbox rate limit exceeded")
            
            retry_after = response.headers.get("Retry-After")
            delay = self._parse_retry_after(retry_after, default=1)
            
            logger.warning(f"⏳ [Dropbox] Rate limited, retrying in {delay}s")
            time.sleep(delay)
            attempt += 1
            continue
        
        return response
```

---

## 6. OAuth Flow Integration

### Authorization URL

```
https://www.dropbox.com/oauth2/authorize
  ?client_id={DROPBOX_CLIENT_ID}
  &redirect_uri={DROPBOX_REDIRECT_URI}
  &response_type=code
  &token_access_type=offline
  &state={state_token}
```

**Important**: `token_access_type=offline` is required for refresh tokens.

### Token Exchange

```http
POST https://api.dropboxapi.com/oauth2/token
Content-Type: application/x-www-form-urlencoded

code={AUTH_CODE}
&grant_type=authorization_code
&client_id={CLIENT_ID}
&client_secret={CLIENT_SECRET}
&redirect_uri={REDIRECT_URI}
```

**Response**:
```json
{
    "access_token": "sl.access_token...",
    "token_type": "bearer",
    "expires_in": 14400,
    "refresh_token": "refresh_token...",
    "scope": "account_info.read files.content.read files.metadata.read",
    "uid": "12345",
    "account_id": "dbid:AAH..."
}
```

### Required Scopes

| Scope | Purpose |
|-------|---------|
| `account_info.read` | Validate user account |
| `files.metadata.read` | List files and folders |
| `files.content.read` | Download file content |

---

## 7. Database Requirements

### Connector Definition Migration

```sql
-- Add Dropbox connector definition
INSERT INTO connector_definitions (
    type,
    name,
    oauth_required,
    config_schema,
    created_at
) VALUES (
    'dropbox',
    'Dropbox',
    true,
    '{"type": "object", "properties": {"root_path": {"type": "string", "default": ""}}}',
    NOW()
) ON CONFLICT (type) DO NOTHING;
```

### User Integration Schema

The existing `user_integrations` table structure is compatible:

| Column | Type | Dropbox Usage |
|--------|------|---------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | User reference |
| `connector_definition_id` | UUID | → dropbox definition |
| `access_token` | TEXT | Encrypted access token |
| `refresh_token` | TEXT | Encrypted refresh token |
| `expires_at` | TIMESTAMP | Token expiry |
| `credentials` | JSONB | `{account_id, uid, root_path}` |

---

## 8. Testing Strategy

### Unit Tests

**File**: `backend/tests/unit/test_dropbox_connector.py`

| Test Case | Description |
|-----------|-------------|
| `test_validate_config_with_token` | Valid token passes validation |
| `test_validate_config_missing_creds` | Reject config without credentials |
| `test_validate_config_invalid_token` | API returns 401 → validation fails |
| `test_list_files_recursive` | Recursive listing with pagination |
| `test_list_files_since_filter` | Incremental sync filtering |
| `test_list_files_folder_browsing` | Non-recursive parent_id listing |
| `test_fetch_file_content_by_id` | Download by Dropbox ID |
| `test_fetch_file_content_by_path` | Download by path |
| `test_fetch_documents_folder` | Recursive folder ingestion |
| `test_rate_limit_retry` | 429 → backoff → retry |
| `test_rate_limit_exhausted` | 429 × MAX_RETRIES → exception |
| `test_auth_error_401` | 401 → ConnectorAuthError |
| `test_auth_error_403` | 403 → ConnectorAuthError |
| `test_not_found_409` | 409 path error → ItemNotFoundError |
| `test_server_error_5xx` | 500 → ConnectorTransientError |
| `test_content_api_header_encoding` | Dropbox-API-Arg JSON encoding |
| `test_mime_type_detection` | Filename → MIME type |

### Integration Tests

**File**: `backend/tests/integration/test_dropbox_integration.py`

| Test Scenario | Description |
|---------------|-------------|
| OAuth Flow | Full connect → callback → store flow |
| Token Refresh | Expired token → automatic refresh |
| Large Folder Sync | 10,000+ files with pagination |
| Incremental Sync | Only modified files returned |
| Rate Limit Recovery | Trigger 429, verify retry works |

### Mock Fixtures Required

```python
@pytest.fixture
def mock_dropbox_api():
    """Mock Dropbox API responses."""
    with responses.RequestsMock() as rsps:
        # /users/get_current_account
        rsps.add(
            responses.POST,
            "https://api.dropboxapi.com/2/users/get_current_account",
            json={"account_id": "dbid:AAH...", "email": "test@example.com"},
            status=200
        )
        
        # /files/list_folder
        rsps.add(
            responses.POST,
            "https://api.dropboxapi.com/2/files/list_folder",
            json={
                "entries": [...],
                "cursor": "cursor_token",
                "has_more": False
            },
            status=200
        )
        
        yield rsps
```

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Day 1)

| Task | File | Effort |
|------|------|--------|
| Add Dropbox config settings | `backend/core/config.py` | 15 min |
| Add registry entry | `backend/connectors/registry.py` | 5 min |
| Add concurrency limit | `backend/connectors/limits.py` | 5 min |
| Database migration | `supabase/migrations/XXX_dropbox.sql` | 10 min |

### Phase 2: Core Connector (Day 1-2)

| Task | File | Effort |
|------|------|--------|
| Create dropbox.py module | `backend/connectors/dropbox.py` | 3 hrs |
| Implement HTTP layer | `_rpc_request`, `_content_download` | 1 hr |
| Implement `validate_config` | Token verification | 30 min |
| Implement `list_files` | With pagination | 1 hr |
| Implement `fetch_file_content` | Streaming download | 30 min |
| Implement `fetch_documents_sync` | Full ingestion support | 1 hr |

### Phase 3: OAuth Integration (Day 2)

| Task | File | Effort |
|------|------|--------|
| Add token refresh method | `backend/services/oauth_token_manager.py` | 30 min |
| Update `get_valid_credentials` | Handle 'dropbox' provider | 15 min |
| Add OAuth callback endpoint | `backend/api/v1/integrations.py` | 1 hr |
| Add disconnect endpoint | `backend/api/v1/integrations.py` | 15 min |

### Phase 4: Testing (Day 3)

| Task | Effort |
|------|--------|
| Unit tests | 2 hrs |
| Integration tests | 1 hr |
| Manual E2E testing | 1 hr |

### Total Estimated Effort: 12-14 hours

---

## 10. Open Questions — RESOLVED ✅

> **Status**: All questions answered by Project Lead on 2026-01-14

### Q1: OAuth App Configuration ✅

**Answer**: Available
- **Scopes**: `account_info.read`, `files.metadata.read`, `files.content.read`, `sharing.read`, `team_data.member`

---

### Q2: Root Path Configuration ✅

**Answer**: **Yes, supported**
- Users can configure a root path to limit sync scope
- Stored in integration credentials as `root_path`

---

### Q3: Shared Folders Handling ✅

**Answer**: **Include shared folders**
- Default Dropbox behavior is used
- Shared folders accessible via Team namespace

---

### Q4: File Size Limits ✅

**Answer**: **System default (100MB)**
- Uses `settings.MAX_FILE_SIZE` from config.py
- Consistent with other connectors

---

### Q5: Paper Documents Handling ✅

**Answer**: **Skip for Phase 1**
- Paper documents require export API (complex)
- Can be added in Phase 2 if needed

---

### Q6: Team/Business Account Support ✅ (CRITICAL)

**Answer**: **YES - Full Team Space Support via Path Root Header**

**Implementation Details**:
1. In `validate_config`, inspect `root_info` from `/users/get_current_account`
2. If `root_namespace_id` exists, store it in integration credentials
3. Inject `Dropbox-API-Path-Root` header into ALL requests
4. This enables access to Team Folders/Spaces

**Key Method**: `_get_headers(config)` dynamically injects namespace header

---

### Q7: Webhook Support ✅

**Answer**: **No** (polling-based sync is sufficient for Phase 1)

---

### Q8: Frontend Integration Points ✅

**Answer**: Requires updates (tracked separately)
- [ ] Add Dropbox to connector list in ConnectorsList component
- [ ] Add Dropbox icon/branding
- [ ] Add Dropbox-specific connect button
- [ ] File browser integration

---

### Q9: Environment Variables ✅

**Answer**: Confirmed
```bash
DROPBOX_CLIENT_ID=your_app_key
DROPBOX_CLIENT_SECRET=your_app_secret
DROPBOX_REDIRECT_URI=https://app.axiohub.io/api/v1/integrations/dropbox/callback
```

---

### Q10: Priority Level ✅

**Answer**: **High** - Complete within 1 week

---

## Appendix A: Dropbox API Reference

### Useful Documentation Links

- [Dropbox API Explorer](https://dropbox.github.io/dropbox-api-v2-explorer/)
- [OAuth Guide](https://www.dropbox.com/developers/reference/oauth-guide)
- [Rate Limits](https://www.dropbox.com/developers/reference/data-ingress-guide)
- [Files Endpoints](https://www.dropbox.com/developers/documentation/http/documentation#files)

### Response Examples

**list_folder Response**:
```json
{
    "entries": [
        {
            ".tag": "file",
            "name": "report.pdf",
            "id": "id:a4ayc_80_OEAAAAAAAAAXw",
            "path_lower": "/documents/report.pdf",
            "path_display": "/Documents/report.pdf",
            "rev": "a1c10ce0dd78",
            "size": 1024000,
            "server_modified": "2024-01-15T10:30:00Z",
            "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        },
        {
            ".tag": "folder",
            "name": "Archive",
            "id": "id:a4ayc_80_OEAAAAAAAAAXz",
            "path_lower": "/documents/archive",
            "path_display": "/Documents/Archive"
        }
    ],
    "cursor": "ZtkX9_EHj3x7PMkVuFIhwKYXEpwpLwyxp9vMKomUhllil9q7eWiAu",
    "has_more": false
}
```

**get_current_account Response**:
```json
{
    "account_id": "dbid:AAH4f99T0taONIb-OurWxbNQ6ywGRopQngc",
    "name": {
        "given_name": "John",
        "surname": "Doe",
        "display_name": "John Doe"
    },
    "email": "john@example.com",
    "email_verified": true,
    "disabled": false,
    "country": "US",
    "locale": "en"
}
```

---

## Appendix B: Code Templates

### Minimal Dropbox Connector Skeleton

```python
"""Dropbox Connector - Skeleton"""

from __future__ import annotations

import json
import logging
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
from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType

logger = logging.getLogger(__name__)

DROPBOX_API_BASE = "https://api.dropboxapi.com/2"
DROPBOX_CONTENT_BASE = "https://content.dropboxapi.com/2"


class DropboxConnector(EnhancedConnector, BaseConnector):
    """Dropbox connector for unified ingestion pipeline."""

    @property
    def connector_type(self) -> SourceType:
        return SourceType.DROPBOX

    def validate_config(self, config: dict) -> bool:
        # TODO: Implement
        raise NotImplementedError

    def list_files(self, config: dict, since: datetime | None = None) -> Iterator[RemoteFile]:
        # TODO: Implement
        raise NotImplementedError

    def fetch_file_content(self, file_id: str, config: dict) -> bytes:
        # TODO: Implement
        raise NotImplementedError

    async def fetch_documents(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AsyncIterator[SourceDocument]:
        for doc in self.fetch_documents_sync(item_ids, credentials, **kwargs):
            yield doc

    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Iterator[SourceDocument]:
        # TODO: Implement
        raise NotImplementedError
```

---

## Appendix C: Implementation Summary (COMPLETED)

### Files Created/Modified

| File | Status | Description |
|------|--------|-------------|
| `backend/core/config.py` | ✅ Modified | Added `DROPBOX_CLIENT_ID`, `DROPBOX_CLIENT_SECRET`, `DROPBOX_REDIRECT_URI`, `CONNECTOR_CONCURRENCY_DROPBOX` |
| `backend/connectors/registry.py` | ✅ Modified | Added `dropbox` entry with capabilities |
| `backend/connectors/limits.py` | ✅ Modified | Added Dropbox concurrency limit |
| `backend/connectors/dropbox.py` | ✅ Created | Full connector with Team/Namespace support (550+ lines) |
| `backend/services/oauth_token_manager.py` | ✅ Modified | Added `refresh_dropbox_token()` method |
| `backend/scripts/dropbox_helper.py` | ✅ Created | Test helper script |

### Key Features Implemented

1. **Team/Business Account Support**
   - Automatic detection via `root_info.root_namespace_id`
   - `Dropbox-API-Path-Root` header injection
   - Access to Team Folders and Shared Spaces

2. **Dual API Handling**
   - `_rpc_request()` for metadata operations
   - `_content_download()` for file transfers
   - Correct header serialization for each

3. **Resilience**
   - 429 rate limit handling with `Retry-After` parsing
   - Automatic retry with exponential backoff
   - Proper exception mapping (`ConnectorAuthError`, `ConnectorRateLimitError`, `ConnectorTransientError`)

4. **Token Management**
   - Automatic token refresh via `OAuthTokenManager`
   - Secure storage with encryption
   - Expiry detection and proactive refresh

### Testing

Run the helper script to verify:

```bash
cd backend

# Validate token and detect Team account
python scripts/dropbox_helper.py --token YOUR_TOKEN validate

# List files (auto-detects Team namespace)
python scripts/dropbox_helper.py --token YOUR_TOKEN list

# List files with explicit namespace
python scripts/dropbox_helper.py --token YOUR_TOKEN --namespace ns:12345 list

# Full connector test
python scripts/dropbox_helper.py --token YOUR_TOKEN test
```

### Remaining Tasks

- [ ] Add OAuth callback endpoint in `api/v1/integrations.py`
- [ ] Database migration for connector definition
- [ ] Frontend components (connect button, icon)
- [ ] Unit tests
- [ ] Integration tests

---

*Document Updated: 2026-01-14 - Implementation Complete*

