# Amazon S3 Connector Design Specification

**Version:** 1.0  
**Author:** Principal Cloud Architect & Security Specialist  
**Date:** January 2026  
**Status:** Technical Feasibility & Risk Analysis

---

## Executive Summary

This document provides a comprehensive technical analysis for integrating Amazon S3 into the Axio platform. Unlike previous connectors (Google Drive, Dropbox, Box) which use OAuth 2.0, S3 requires **IAM-based authentication** via Access Keys. This introduces unique security, cost, and architectural challenges that must be carefully addressed.

**Key Differences from OAuth Connectors:**

| Aspect | OAuth Connectors | S3 Connector |
|--------|------------------|--------------|
| Authentication | OAuth redirect flow | Form-based credential input |
| Token Storage | Access + Refresh tokens | AWS Access Key + Secret Key |
| Token Rotation | Automatic via refresh | Manual (user responsibility) |
| Permission Scope | OAuth scopes | IAM policies |
| Cost Model | API rate limits | Pay-per-request + data transfer |

---

## 1. Critical Risk & Security Analysis

### 1.A. Authentication Model (The "No-OAuth" Problem)

#### Challenge Overview

AWS S3 does not support OAuth 2.0. Users must provide:
- `AWS_ACCESS_KEY_ID` - 20-character alphanumeric identifier
- `AWS_SECRET_ACCESS_KEY` - 40-character secret key
- `AWS_REGION` - Region code (e.g., `us-east-1`)
- `BUCKET_NAME` - Target bucket name

**Security Risk Assessment:**

| Risk | Severity | Mitigation |
|------|----------|------------|
| Secret key exposure in logs | Critical | Never log credentials; mask in UI |
| Secret key stored in plaintext | Critical | Fernet encryption at rest |
| Overly permissive IAM policies | High | Provide least-privilege policy template |
| Key compromise = full account access | High | Enforce read-only policy |
| No automatic rotation | Medium | Document rotation procedures; warn on old keys |

#### Encryption Strategy

**Decision: Use existing Fernet encryption infrastructure**

The platform already has robust credential encryption via `core/security.py`:

```python
from core.security import encrypt_token, decrypt_token

# Store encrypted credentials
encrypted_access_key = encrypt_token(access_key_id)
encrypted_secret_key = encrypt_token(secret_access_key)

# Decrypt when needed
access_key_id = decrypt_token(encrypted_access_key)
secret_access_key = decrypt_token(encrypted_secret_key)
```

**Storage Schema (in `user_integrations.credentials` JSONB):**

```json
{
  "access_key_id": "gAAAA...(encrypted)...",
  "secret_access_key": "gAAAA...(encrypted)...",
  "region": "us-east-1",
  "bucket_name": "my-knowledge-base",
  "prefix": "documents/",
  "suffix_filter": [".pdf", ".docx", ".txt", ".md"]
}
```

**Why not a separate encrypted column?**
- The `credentials` JSONB column already exists and is used by SFTP
- Encryption happens at the field level before storage
- Keeps the schema consistent across connectors
- RLS policies already protect `user_integrations`

#### Least Privilege IAM Policy Template

**CRITICAL:** Users MUST create an IAM policy with minimal permissions. We will provide this template in the UI:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AxioReadOnlyAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR-BUCKET-NAME",
        "arn:aws:s3:::YOUR-BUCKET-NAME/*"
      ]
    }
  ]
}
```

**Actions Explained:**

| Action | Purpose | Required? |
|--------|---------|-----------|
| `s3:ListBucket` | List objects in bucket (file discovery) | ✅ Yes |
| `s3:GetObject` | Download object content | ✅ Yes |
| `s3:GetBucketLocation` | Verify bucket region | ❌ Optional |
| `s3:PutObject` | Upload files | ❌ **NEVER GRANT** |
| `s3:DeleteObject` | Delete files | ❌ **NEVER GRANT** |

**Policy Enforcement in UI:**

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠️ SECURITY NOTICE                                             │
│                                                                 │
│  Before connecting, create an IAM user with READ-ONLY access:   │
│                                                                 │
│  1. Go to AWS IAM Console → Users → Create User                 │
│  2. Attach a custom policy with ONLY these permissions:         │
│     • s3:ListBucket                                             │
│     • s3:GetObject                                              │
│  3. Copy the IAM policy template (click to copy)                │
│  4. NEVER grant write or delete permissions                     │
│                                                                 │
│  [📋 Copy IAM Policy Template]                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 1.B. Scale & Cost Management (The "Bill Shock" Risk)

#### The Problem

S3 pricing is pay-per-request:

| Operation | Cost (us-east-1) |
|-----------|------------------|
| LIST (per 1,000 objects) | $0.005 |
| GET (per 1,000 objects) | $0.0004 |
| Data transfer (per GB) | $0.09 (first 10TB) |

**Worst Case Scenario:**
- User connects a bucket with 10 million log files
- Naive `list_objects` loop = 10,000 LIST requests = **$50 in API costs**
- Downloading all files = massive data transfer costs
- Worker timeout from excessive pagination

#### Mitigation Strategy 1: Mandatory Prefix

**RECOMMENDATION: ENFORCE prefix requirement**

```
┌─────────────────────────────────────────────────────────────────┐
│  S3 Connection Configuration                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Bucket Name: [my-company-bucket          ]                     │
│                                                                 │
│  Folder Path (Required): [documents/knowledge-base/ ]           │
│               └── Must specify a folder path                    │
│                   Cannot sync entire bucket root                │
│                                                                 │
│  ⚠️ Why is this required?                                       │
│  Syncing entire buckets can cause excessive API costs           │
│  and long sync times. Specify the folder containing your        │
│  documents (e.g., "documents/" or "knowledge-base/")            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation:**

```python
def validate_config(self, config: dict) -> bool:
    prefix = (config.get("prefix") or "").strip()
    
    # REQUIRE prefix to prevent full bucket scans
    if not prefix:
        raise ValueError(
            "S3 prefix is required. Please specify a folder path "
            "(e.g., 'documents/' or 'knowledge-base/')."
        )
    
    # Ensure prefix ends with / for proper filtering
    if not prefix.endswith("/"):
        prefix = f"{prefix}/"
    
    return True
```

#### Mitigation Strategy 2: Strict Suffix Filtering

**RECOMMENDATION: Whitelist supported file extensions**

Only sync files with supported document extensions:

```python
SUPPORTED_EXTENSIONS = {
    # Documents
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
    # Text
    ".txt", ".md", ".markdown", ".rst", ".rtf",
    # Code (if applicable)
    ".py", ".js", ".ts", ".java", ".go", ".rs", ".rb",
    # Data
    ".json", ".yaml", ".yml", ".csv",
    # Web
    ".html", ".htm",
}

def _should_process_object(self, key: str) -> bool:
    """Check if object should be processed based on extension."""
    ext = os.path.splitext(key.lower())[1]
    
    # Reject system files and backups
    if key.startswith(".") or "/.git/" in key or "/__pycache__/" in key:
        return False
    
    # Reject common log/backup patterns
    if any(pattern in key.lower() for pattern in [
        ".log", ".bak", ".tmp", ".swp", ".lock",
        "access_log", "error_log", ".gz", ".zip", ".tar"
    ]):
        return False
    
    return ext in SUPPORTED_EXTENSIONS
```

#### Mitigation Strategy 3: Object Count Limits

**RECOMMENDATION: Implement safety limits**

```python
MAX_OBJECTS_PER_SYNC = 10_000  # Configurable per plan
MAX_TOTAL_SIZE_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB

def _list_objects_with_limits(self, config: dict) -> Iterator[dict]:
    """List objects with safety limits."""
    object_count = 0
    total_size = 0
    
    paginator = self.s3_client.get_paginator("list_objects_v2")
    
    for page in paginator.paginate(
        Bucket=config["bucket_name"],
        Prefix=config["prefix"],
        PaginationConfig={"PageSize": 1000}
    ):
        for obj in page.get("Contents", []):
            # Check limits
            if object_count >= MAX_OBJECTS_PER_SYNC:
                logger.warning(
                    f"⚠️ [S3] Reached object limit ({MAX_OBJECTS_PER_SYNC}). "
                    "Consider narrowing your prefix."
                )
                return
            
            if total_size + obj["Size"] > MAX_TOTAL_SIZE_BYTES:
                logger.warning(
                    f"⚠️ [S3] Reached size limit ({MAX_TOTAL_SIZE_BYTES} bytes)."
                )
                return
            
            # Apply suffix filter
            if not self._should_process_object(obj["Key"]):
                continue
            
            object_count += 1
            total_size += obj["Size"]
            yield obj
```

#### Cost Estimation Display

**RECOMMENDATION: Show estimated costs before sync**

```python
async def estimate_sync_cost(self, config: dict) -> dict:
    """Estimate API and transfer costs before syncing."""
    # Quick HEAD request to get object count
    response = self.s3_client.list_objects_v2(
        Bucket=config["bucket_name"],
        Prefix=config["prefix"],
        MaxKeys=1
    )
    
    # Use metadata to estimate
    total_objects = response.get("KeyCount", 0)
    
    # If bucket has >1000 objects, do a paginated count
    if response.get("IsTruncated"):
        # Count pages needed (each page = 1000 objects = 1 LIST request)
        pages_needed = (total_objects // 1000) + 1
        list_cost = pages_needed * 0.005
    else:
        list_cost = 0.005  # Minimum 1 LIST request
    
    return {
        "estimated_objects": total_objects,
        "estimated_list_cost_usd": round(list_cost, 4),
        "warning": total_objects > 5000,
        "message": f"Estimated {total_objects} objects. "
                   f"LIST API cost: ~${list_cost:.4f}"
    }
```

---

### 1.C. Library & Performance Decision

#### Options Analysis

| Library | Pros | Cons |
|---------|------|------|
| `boto3` (Official SDK) | Full feature set, well-documented, automatic retries, SigV4 signing | Synchronous (blocking) |
| `aiobotocore` | Async native, good for high concurrency | Less mature, additional dependency |
| `requests` + SigV4 | Full control, no dependencies | Complex signature implementation, error-prone |

#### Decision: `boto3` with `run_in_threadpool`

**Rationale:**
1. `boto3` is the official, battle-tested SDK
2. Automatic retry logic and exponential backoff built-in
3. Proper SigV4 signature handling
4. Thread pool execution prevents event loop blocking

**Implementation Pattern:**

```python
from fastapi.concurrency import run_in_threadpool
import boto3
from botocore.config import Config

class S3Connector(EnhancedConnector, BaseConnector):
    
    def _get_s3_client(self, config: dict):
        """Create boto3 S3 client with proper configuration."""
        return boto3.client(
            "s3",
            aws_access_key_id=decrypt_token(config["access_key_id"]),
            aws_secret_access_key=decrypt_token(config["secret_access_key"]),
            region_name=config["region"],
            config=Config(
                connect_timeout=10,
                read_timeout=30,
                retries={
                    "max_attempts": 3,
                    "mode": "adaptive"  # Adaptive retry with exponential backoff
                },
                signature_version="s3v4",
            )
        )
    
    async def fetch_documents(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncIterator[SourceDocument]:
        """Async wrapper around synchronous boto3 calls."""
        # Run blocking boto3 calls in thread pool
        docs = await run_in_threadpool(
            self.fetch_documents_sync,
            item_ids,
            credentials,
            **kwargs
        )
        for doc in docs:
            yield doc
    
    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Iterator[SourceDocument]:
        """Synchronous fetch using boto3."""
        # Implementation here
        pass
```

**Thread Pool Sizing:**

```python
# In core/config.py
S3_THREADPOOL_SIZE = 4  # Limit concurrent S3 operations
```

---

## 2. Architecture & Schema Implications

### 2.1. The Form-Based Authentication Problem

The current `connector_definitions` table assumes OAuth flow:

```sql
-- Current schema (OAuth-centric)
CREATE TABLE connector_definitions (
    id UUID PRIMARY KEY,
    type TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    icon_path TEXT,
    category TEXT,
    is_active BOOLEAN
);
```

**Problem:** No way to specify that S3 requires a form input instead of OAuth redirect.

### 2.2. Proposed Schema Extension

**Option A: Add `auth_type` and `form_schema` columns**

```sql
-- Migration: Add form-based auth support
ALTER TABLE connector_definitions
    ADD COLUMN IF NOT EXISTS auth_type TEXT DEFAULT 'oauth2',
    ADD COLUMN IF NOT EXISTS form_schema JSONB;

COMMENT ON COLUMN connector_definitions.auth_type IS 
    'Authentication type: oauth2, form, api_key, none';
COMMENT ON COLUMN connector_definitions.form_schema IS 
    'JSON schema for form-based auth connectors';
```

**S3 Connector Definition:**

```sql
INSERT INTO connector_definitions (
    type, name, description, icon_path, category, is_active, auth_type, form_schema
) VALUES (
    's3',
    'Amazon S3',
    'Connect to Amazon S3 buckets to import documents',
    '/icons/s3.svg',
    'cloud',
    true,
    'form',
    '{
        "type": "object",
        "required": ["access_key_id", "secret_access_key", "region", "bucket_name", "prefix"],
        "properties": {
            "access_key_id": {
                "type": "string",
                "title": "AWS Access Key ID",
                "description": "20-character alphanumeric key",
                "pattern": "^[A-Z0-9]{20}$",
                "x-input-type": "text"
            },
            "secret_access_key": {
                "type": "string",
                "title": "AWS Secret Access Key",
                "description": "40-character secret key",
                "x-input-type": "password"
            },
            "region": {
                "type": "string",
                "title": "AWS Region",
                "description": "e.g., us-east-1, eu-west-1",
                "enum": [
                    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
                    "eu-west-1", "eu-west-2", "eu-central-1",
                    "ap-northeast-1", "ap-southeast-1", "ap-southeast-2"
                ],
                "default": "us-east-1"
            },
            "bucket_name": {
                "type": "string",
                "title": "Bucket Name",
                "description": "The S3 bucket to connect",
                "pattern": "^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$"
            },
            "prefix": {
                "type": "string",
                "title": "Folder Path (Required)",
                "description": "e.g., documents/ or knowledge-base/",
                "minLength": 1
            }
        }
    }'
);
```

### 2.3. Frontend Form Rendering

The frontend can use `form_schema` to dynamically render the connection form:

```typescript
// Frontend: Dynamic form rendering based on form_schema
interface ConnectorDefinition {
  id: string;
  type: string;
  name: string;
  auth_type: 'oauth2' | 'form' | 'api_key';
  form_schema?: JSONSchema;
}

const ConnectDialog: React.FC<{ connector: ConnectorDefinition }> = ({ connector }) => {
  if (connector.auth_type === 'oauth2') {
    return <OAuthConnectButton connector={connector} />;
  }
  
  if (connector.auth_type === 'form' && connector.form_schema) {
    return <DynamicForm schema={connector.form_schema} onSubmit={handleFormSubmit} />;
  }
  
  return null;
};
```

### 2.4. Comparison with Existing Connectors

| Connector | Auth Type | Token Storage | Form Fields |
|-----------|-----------|---------------|-------------|
| Google Drive | OAuth 2.0 | `access_token`, `refresh_token` | None |
| Dropbox | OAuth 2.0 | `access_token`, `refresh_token` | None |
| Box | OAuth 2.0 | `access_token`, `refresh_token` | None |
| GitHub | OAuth 2.0 | `access_token` (long-lived) | None |
| SFTP | Form | `credentials` JSONB | host, port, username, password/key |
| **S3** | **Form** | **`credentials` JSONB** | **access_key, secret, region, bucket, prefix** |

---

## 3. Implementation Plan

### 3.1. Class Structure

```python
"""
Amazon S3 Connector

Connects to Amazon S3 to fetch and sync documents from buckets.
Uses IAM credentials (Access Key + Secret Key) for authentication.

SECURITY NOTES:
- Credentials are encrypted at rest using Fernet
- Only read operations (ListBucket, GetObject) are supported
- Prefix is REQUIRED to prevent full bucket scans

API Reference:
- https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html

Cost Awareness:
- LIST: $0.005 per 1,000 requests
- GET: $0.0004 per 1,000 requests
- Data transfer: $0.09/GB (first 10TB)
"""

from __future__ import annotations

import io
import logging
import mimetypes
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional, AsyncIterator

import boto3
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    EndpointConnectionError,
)
from fastapi.concurrency import run_in_threadpool

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
from core.security import decrypt_token

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

DEFAULT_REGION = "us-east-1"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_OBJECTS_PER_SYNC = 10_000
DOWNLOAD_TIMEOUT_SECONDS = 120
LIST_PAGE_SIZE = 1000

# Supported file extensions for knowledge base
SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
    ".txt", ".md", ".markdown", ".rst", ".rtf",
    ".json", ".yaml", ".yml", ".csv",
    ".html", ".htm",
}


class S3Connector(EnhancedConnector, BaseConnector):
    """
    Amazon S3 connector for unified ingestion pipeline.
    
    Features:
    - IAM credential authentication with Fernet encryption
    - Mandatory prefix requirement for cost control
    - Suffix filtering for supported document types
    - Object count limits to prevent bill shock
    - Streaming downloads for large files
    - Thread pool execution for async compatibility
    """
    
    @property
    def connector_type(self) -> SourceType:
        return SourceType.S3  # Add to SourceType enum
    
    @property
    def supports_incremental_sync(self) -> bool:
        return True  # Can filter by LastModified
    
    @property
    def supports_batch_fetch(self) -> bool:
        return False  # S3 doesn't support batch downloads
```

### 3.2. Key Methods Specification

#### `validate_config()` - Credential Verification

```python
def validate_config(self, config: dict) -> bool:
    """
    Validate S3 configuration.
    
    Validation Steps:
    1. Check required fields (access_key, secret, region, bucket, prefix)
    2. Validate prefix is non-empty (cost protection)
    3. Attempt HEAD bucket to verify credentials and bucket access
    
    Cost: 1 HEAD request ($0.0004 per 1,000)
    """
    if not isinstance(config, dict):
        return False
    
    # Required fields
    required = ["access_key_id", "secret_access_key", "region", "bucket_name", "prefix"]
    for field in required:
        if not config.get(field):
            logger.warning(f"❌ [S3] Missing required field: {field}")
            return False
    
    # ENFORCE prefix requirement (cost protection)
    prefix = config.get("prefix", "").strip()
    if not prefix:
        raise ValueError(
            "S3 prefix is required to prevent expensive full-bucket scans. "
            "Please specify a folder path (e.g., 'documents/')."
        )
    
    # Verify credentials with HEAD bucket
    try:
        self._verify_access(config)
        return True
    except ConnectorAuthError:
        return False
    except Exception:
        return True  # Network errors = config might be OK

def _verify_access(self, config: dict) -> dict:
    """
    Verify S3 access using HEAD bucket request.
    
    This is the cheapest way to verify:
    - Credentials are valid
    - Bucket exists
    - User has ListBucket permission
    
    Cost: Effectively $0 (HEAD requests are free)
    """
    client = self._get_s3_client(config)
    
    try:
        # HEAD bucket verifies access without listing
        client.head_bucket(Bucket=config["bucket_name"])
        logger.info(f"✅ [S3] Verified access to bucket: {config['bucket_name']}")
        return {"status": "connected"}
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        
        if error_code == "403":
            raise ConnectorAuthError(
                "S3 access denied. Please verify your IAM policy includes "
                "s3:ListBucket permission for this bucket."
            )
        elif error_code == "404":
            raise ConnectorAuthError(
                f"S3 bucket '{config['bucket_name']}' not found. "
                "Please verify the bucket name and region."
            )
        else:
            raise ConnectorTransientError(f"S3 error: {error_code}")
            
    except NoCredentialsError:
        raise ConnectorAuthError("Invalid AWS credentials")
        
    except EndpointConnectionError as e:
        raise ConnectorTransientError(f"S3 connection failed: {e}")
```

#### `list_files()` - File Discovery with Pagination

```python
def list_files(
    self,
    config: dict,
    since: Optional[datetime] = None,
) -> Iterator[RemoteFile]:
    """
    List files from S3 bucket with pagination.
    
    Features:
    - Prefix-filtered listing (REQUIRED)
    - Suffix filtering for supported extensions
    - Object count limit (MAX_OBJECTS_PER_SYNC)
    - Incremental sync support via `since` parameter
    
    Cost: $0.005 per 1,000 objects listed
    """
    resolved = self._resolve_config(config)
    client = self._get_s3_client(resolved)
    
    bucket = resolved["bucket_name"]
    prefix = self._normalize_prefix(resolved["prefix"])
    
    logger.info(f"📁 [S3] Listing objects in s3://{bucket}/{prefix}")
    
    object_count = 0
    paginator = client.get_paginator("list_objects_v2")
    
    try:
        for page in paginator.paginate(
            Bucket=bucket,
            Prefix=prefix,
            PaginationConfig={"PageSize": LIST_PAGE_SIZE}
        ):
            for obj in page.get("Contents", []):
                # Check object limit
                if object_count >= MAX_OBJECTS_PER_SYNC:
                    logger.warning(
                        f"⚠️ [S3] Reached object limit ({MAX_OBJECTS_PER_SYNC}). "
                        "Consider narrowing your prefix or increasing the limit."
                    )
                    return
                
                key = obj["Key"]
                
                # Skip directories (keys ending with /)
                if key.endswith("/"):
                    continue
                
                # Apply suffix filter
                if not self._should_process_object(key):
                    continue
                
                # Apply incremental sync filter
                last_modified = obj.get("LastModified")
                if since and last_modified and last_modified < since:
                    continue
                
                # Check file size limit
                if obj.get("Size", 0) > MAX_FILE_SIZE:
                    logger.warning(f"⚠️ [S3] Skipping large file: {key} ({obj['Size']} bytes)")
                    continue
                
                object_count += 1
                yield self._object_to_remote_file(obj, bucket)
        
        logger.info(f"📁 [S3] Listed {object_count} objects from s3://{bucket}/{prefix}")
        
    except ClientError as e:
        self._handle_client_error(e, "list_files")
```

#### `fetch_documents_sync()` - Content Fetching with Streaming

```python
def fetch_documents_sync(
    self,
    item_ids: list[str],
    credentials: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Iterator[SourceDocument]:
    """
    Fetch documents from S3 for ingestion pipeline.
    
    Args:
        item_ids: List of S3 object keys (e.g., "documents/file.pdf")
        credentials: S3 credentials dict
        **kwargs: Additional params including user_id
    
    Cost: $0.0004 per GET request + data transfer
    """
    if not item_ids:
        return
    
    config = self._build_config(credentials, **kwargs)
    resolved = self._resolve_config(config)
    client = self._get_s3_client(resolved)
    
    bucket = resolved["bucket_name"]
    
    logger.info(f"📥 [S3Connector] Fetching {len(item_ids)} object(s)")
    
    processed_count = 0
    
    for key in item_ids:
        try:
            # Get object with streaming
            response = client.get_object(Bucket=bucket, Key=key)
            
            # Stream content with size limit
            content = self._stream_object_content(response)
            
            # Build source document
            yield SourceDocument(
                content=content,
                metadata={
                    "source": "s3",
                    "bucket": bucket,
                    "key": key,
                    "region": resolved["region"],
                    "last_modified": response.get("LastModified", "").isoformat()
                        if response.get("LastModified") else None,
                    "etag": response.get("ETag", "").strip('"'),
                    "content_type": response.get("ContentType"),
                },
                source_type=SourceType.S3,
                source_id=f"s3://{bucket}/{key}",
                filename=os.path.basename(key),
                mime_type=self._guess_mime_type(key, response.get("ContentType")),
                size_bytes=len(content),
                parent_id=os.path.dirname(key) or None,
            )
            
            processed_count += 1
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchKey":
                logger.warning(f"⚠️ [S3] Object not found: {key}")
                continue
            elif error_code == "AccessDenied":
                raise ConnectorAuthError(f"S3 access denied to: {key}")
            else:
                logger.error(f"❌ [S3] Failed to fetch {key}: {error_code}")
                continue
        except Exception as e:
            logger.error(f"❌ [S3] Unexpected error fetching {key}: {e}")
            continue
    
    logger.info(f"📥 [S3Connector] Fetched {processed_count}/{len(item_ids)} objects")

def _stream_object_content(self, response: dict) -> bytes:
    """
    Stream object content with size limit enforcement.
    
    Uses StreamingBody for memory-efficient downloads.
    """
    body = response["Body"]
    content_length = response.get("ContentLength", 0)
    
    if content_length > MAX_FILE_SIZE:
        body.close()
        raise FileTooLargeError(
            f"Object exceeds {MAX_FILE_SIZE} byte limit ({content_length} bytes)"
        )
    
    # Stream in 1MB chunks
    buffer = io.BytesIO()
    total_read = 0
    
    for chunk in body.iter_chunks(chunk_size=1024 * 1024):
        total_read += len(chunk)
        if total_read > MAX_FILE_SIZE:
            body.close()
            raise FileTooLargeError(f"Object exceeds {MAX_FILE_SIZE} byte limit")
        buffer.write(chunk)
    
    body.close()
    return buffer.getvalue()
```

### 3.3. File Structure

```
backend/connectors/s3.py
├── Constants
│   ├── DEFAULT_REGION
│   ├── MAX_FILE_SIZE
│   ├── MAX_OBJECTS_PER_SYNC
│   └── SUPPORTED_EXTENSIONS
│
├── S3Connector(EnhancedConnector, BaseConnector)
│   ├── Properties
│   │   ├── connector_type → SourceType.S3
│   │   ├── supports_incremental_sync → True
│   │   └── supports_batch_fetch → False
│   │
│   ├── Configuration & Validation
│   │   ├── validate_config()
│   │   ├── _verify_access()
│   │   ├── _resolve_config()
│   │   ├── _build_config()
│   │   └── _get_s3_client()
│   │
│   ├── File Discovery
│   │   ├── list_files()
│   │   ├── _should_process_object()
│   │   ├── _object_to_remote_file()
│   │   └── _normalize_prefix()
│   │
│   ├── Content Fetching
│   │   ├── fetch_file_content()
│   │   ├── fetch_documents() [async wrapper]
│   │   ├── fetch_documents_sync()
│   │   └── _stream_object_content()
│   │
│   ├── Error Handling
│   │   ├── _handle_client_error()
│   │   └── _map_boto_error()
│   │
│   └── Helpers
│       ├── _guess_mime_type()
│       └── _parse_last_modified()
│
└── get_s3_connector() - Factory function
```

---

## 4. Integration Requirements

### 4.1. SourceType Enum Extension

**`connectors/enhanced.py`:**

```python
class SourceType(str, Enum):
    # ... existing types ...
    S3 = "s3"
```

### 4.2. Connector Registry

**`connectors/registry.py`:**

```python
CONNECTOR_REGISTRY = {
    # ... existing connectors ...
    "s3": {
        "id": "s3",
        "name": "Amazon S3",
        "capabilities": ["binary_content", "incremental_sync"],
        "rate_limit_rpm": 1000,  # S3 has no rate limit, but we self-limit
        "auth_type": "form",
    },
}
```

### 4.3. Database Migration

```sql
-- Migration: Add S3 connector with form-based auth
-- File: 20260116000000_add_s3_connector.sql

-- First, add auth_type and form_schema columns if not exists
ALTER TABLE connector_definitions
    ADD COLUMN IF NOT EXISTS auth_type TEXT DEFAULT 'oauth2',
    ADD COLUMN IF NOT EXISTS form_schema JSONB;

-- Insert S3 connector definition
INSERT INTO connector_definitions (
    type, name, description, icon_path, category, is_active, auth_type, form_schema
) VALUES (
    's3',
    'Amazon S3',
    'Connect to Amazon S3 buckets to import documents. Requires read-only IAM credentials.',
    '/icons/s3.svg',
    'cloud',
    true,
    'form',
    '{
        "type": "object",
        "required": ["access_key_id", "secret_access_key", "region", "bucket_name", "prefix"],
        "properties": {
            "access_key_id": {
                "type": "string",
                "title": "AWS Access Key ID",
                "description": "Your IAM user access key (20 characters)",
                "pattern": "^[A-Z0-9]{20}$",
                "x-input-type": "text"
            },
            "secret_access_key": {
                "type": "string",
                "title": "AWS Secret Access Key",
                "description": "Your IAM user secret key (keep this confidential)",
                "x-input-type": "password"
            },
            "region": {
                "type": "string",
                "title": "AWS Region",
                "enum": ["us-east-1", "us-east-2", "us-west-1", "us-west-2", "eu-west-1", "eu-west-2", "eu-central-1", "ap-northeast-1", "ap-southeast-1", "ap-southeast-2"],
                "default": "us-east-1"
            },
            "bucket_name": {
                "type": "string",
                "title": "Bucket Name",
                "description": "The S3 bucket name",
                "pattern": "^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$"
            },
            "prefix": {
                "type": "string",
                "title": "Folder Path (Required)",
                "description": "Folder prefix to sync (e.g., documents/)",
                "minLength": 1
            }
        }
    }'
) ON CONFLICT (type) DO NOTHING;

NOTIFY pgrst, 'reload config';
```

### 4.4. API Endpoint for Form-Based Connect

**`api/v1/integrations.py`:**

```python
class S3ConnectRequest(BaseModel):
    """S3 connection request with IAM credentials."""
    access_key_id: str = Field(..., min_length=20, max_length=20)
    secret_access_key: str = Field(..., min_length=40)
    region: str = Field(default="us-east-1")
    bucket_name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
    prefix: str = Field(..., min_length=1)

@router.post("/connect/s3")
@limiter.limit("5/minute")
async def connect_s3(
    request: Request,
    body: S3ConnectRequest,
    user_id: str = Depends(get_current_user),
):
    """Connect S3 bucket with IAM credentials."""
    from connectors.s3 import S3Connector
    
    connector = S3Connector()
    
    # Build config for validation
    config = {
        "access_key_id": body.access_key_id,
        "secret_access_key": body.secret_access_key,
        "region": body.region,
        "bucket_name": body.bucket_name,
        "prefix": body.prefix,
    }
    
    # Validate credentials and access
    try:
        connector._verify_access(config)
    except ConnectorAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ConnectorTransientError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    # Store encrypted credentials
    supabase = get_supabase()
    
    # Get connector definition
    def_res = supabase.table("connector_definitions").select("id").eq("type", "s3").single().execute()
    if not def_res.data:
        raise HTTPException(status_code=500, detail="S3 connector not configured")
    
    connector_definition_id = def_res.data["id"]
    
    # Encrypt sensitive fields
    credentials = {
        "access_key_id": encrypt_token(body.access_key_id),
        "secret_access_key": encrypt_token(body.secret_access_key),
        "region": body.region,
        "bucket_name": body.bucket_name,
        "prefix": body.prefix,
    }
    
    # Upsert integration
    data = {
        "user_id": user_id,
        "connector_definition_id": connector_definition_id,
        "credentials": credentials,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    result = supabase.table("user_integrations").upsert(
        data,
        on_conflict="user_id,connector_definition_id"
    ).execute()
    
    return {
        "status": "connected",
        "bucket": body.bucket_name,
        "prefix": body.prefix,
        "region": body.region,
    }
```

### 4.5. Dependencies

**`requirements.txt`:**

```
boto3>=1.34.0
botocore>=1.34.0
```

---

## 5. Risk Assessment & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Bill shock from full bucket scan** | High | High | ENFORCE prefix requirement; object count limits |
| **Credential exposure in logs** | Medium | Critical | Never log credentials; use encryption |
| **Secret key stored in plaintext** | Low | Critical | Fernet encryption mandatory |
| **Overly permissive IAM policy** | High | High | Provide least-privilege template; UI warnings |
| **Thread pool exhaustion** | Medium | Medium | Limit concurrent S3 operations; use dedicated pool |
| **Large file memory issues** | Medium | Medium | Streaming downloads with size limits |
| **Region mismatch errors** | Medium | Low | Verify region on connect; clear error messages |
| **Eventual consistency issues** | Low | Low | Document S3 consistency model; retry logic |

---

## 6. Testing Strategy

### Unit Tests

```python
# tests/unit/test_s3_connector.py

def test_validate_config_requires_prefix():
    """Prefix is mandatory for cost protection."""
    connector = S3Connector()
    
    with pytest.raises(ValueError, match="prefix is required"):
        connector.validate_config({
            "access_key_id": "A" * 20,
            "secret_access_key": "B" * 40,
            "region": "us-east-1",
            "bucket_name": "test-bucket",
            "prefix": "",  # Empty prefix should fail
        })

def test_should_process_object_filters_extensions():
    """Only supported extensions should be processed."""
    connector = S3Connector()
    
    assert connector._should_process_object("docs/file.pdf") is True
    assert connector._should_process_object("docs/file.docx") is True
    assert connector._should_process_object("logs/access.log") is False
    assert connector._should_process_object("backup/data.gz") is False

def test_credentials_are_encrypted():
    """Credentials must be encrypted before storage."""
    with patch("core.security.encrypt_token") as mock_encrypt:
        mock_encrypt.return_value = "encrypted"
        # Test encryption is called
```

### Integration Tests

```python
# tests/integration/test_s3_connector_integration.py

@pytest.mark.integration
def test_s3_list_files_with_prefix(s3_test_bucket):
    """Test listing files with prefix filtering."""
    connector = S3Connector()
    
    files = list(connector.list_files({
        "access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
        "secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
        "region": "us-east-1",
        "bucket_name": s3_test_bucket,
        "prefix": "test-docs/",
    }))
    
    assert len(files) > 0
    assert all(f.id.startswith("test-docs/") for f in files)
```

### Cost Validation Tests

```python
def test_object_limit_prevents_runaway_costs():
    """Object limit should stop enumeration at threshold."""
    connector = S3Connector()
    
    with patch.object(connector, "_get_s3_client") as mock_client:
        # Simulate paginator returning many objects
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": f"file_{i}.pdf", "Size": 100, "LastModified": datetime.now()} 
                          for i in range(1000)]}
            for _ in range(20)  # 20 pages = 20,000 objects
        ]
        mock_client.return_value.get_paginator.return_value = mock_paginator
        
        files = list(connector.list_files({...}))
        
        # Should stop at MAX_OBJECTS_PER_SYNC
        assert len(files) <= MAX_OBJECTS_PER_SYNC
```

---

## 7. Open Questions for Review

1. **Prefix Enforcement:** Should we allow advanced users to sync bucket root with explicit confirmation?

2. **Cross-Region Buckets:** Should we auto-detect bucket region using `GetBucketLocation`?

3. **Assume Role Support:** Should we support IAM role assumption for enterprise customers?

4. **S3 Event Notifications:** Should we implement S3 → SNS → webhook for real-time sync?

5. **Cost Estimation UI:** Should we show estimated costs before initiating a sync?

6. **Key Rotation Reminders:** Should we track key age and warn users about rotation?

---

## Appendix A: AWS S3 API Reference

| Operation | Method | Cost per 1,000 |
|-----------|--------|----------------|
| HeadBucket | HEAD | Free |
| ListObjectsV2 | GET | $0.005 |
| GetObject | GET | $0.0004 |
| HeadObject | HEAD | $0.0004 |

## Appendix B: Error Code Mapping

| AWS Error | HTTP Status | Our Exception |
|-----------|-------------|---------------|
| AccessDenied | 403 | `ConnectorAuthError` |
| InvalidAccessKeyId | 403 | `ConnectorAuthError` |
| SignatureDoesNotMatch | 403 | `ConnectorAuthError` |
| NoSuchBucket | 404 | `ConnectorAuthError` (bucket not found) |
| NoSuchKey | 404 | `ItemNotFoundError` |
| SlowDown | 503 | `ConnectorRateLimitError` |
| ServiceUnavailable | 503 | `ConnectorTransientError` |

## Appendix C: IAM Policy Template (Copy-Paste)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AxioReadOnlyS3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR-BUCKET-NAME",
        "arn:aws:s3:::YOUR-BUCKET-NAME/*"
      ]
    }
  ]
}
```

---

## 8. Production Edge Cases (CTO Review Feedback)

### 8.1. The "Deep Archive" Trap (CRITICAL)

**Problem:** Enterprise S3 buckets often contain objects in `GLACIER` or `DEEP_ARCHIVE` storage classes. Attempting to `GetObject` on these:
- Throws `InvalidObjectState` error
- Or triggers **massive retrieval fees** ($0.03-$0.05 per GB + retrieval requests)

**Solution:** Check `StorageClass` before attempting download.

```python
# Storage classes that require restoration before access
ARCHIVED_STORAGE_CLASSES = {
    "GLACIER",
    "DEEP_ARCHIVE", 
    "GLACIER_IR",  # Glacier Instant Retrieval (still needs check)
}

def _is_object_accessible(self, obj: dict) -> tuple[bool, str]:
    """
    Check if object is immediately accessible.
    
    Returns:
        (is_accessible, reason)
    """
    storage_class = obj.get("StorageClass", "STANDARD")
    
    if storage_class in ARCHIVED_STORAGE_CLASSES:
        return False, f"Object archived in {storage_class}. Restore required before access."
    
    return True, "OK"

def fetch_documents_sync(self, item_ids: list[str], ...):
    for key in item_ids:
        # Get object metadata first (HEAD request - $0.0004 per 1000)
        head_response = client.head_object(Bucket=bucket, Key=key)
        storage_class = head_response.get("StorageClass", "STANDARD")
        
        if storage_class in ARCHIVED_STORAGE_CLASSES:
            logger.warning(
                f"⚠️ [S3] Skipping archived object: {key} "
                f"(StorageClass={storage_class}). Restore required."
            )
            continue  # Skip, don't fail entire job
        
        # Proceed with GET
        content = self._download_object(client, bucket, key)
```

### 8.2. Network Resilience & Resumable Downloads

**Problem:** Large files (50MB+) can fail mid-download due to network issues. Losing 99% of a download wastes bandwidth and time.

**Solution:** Implement chunked downloads with retry logic for large files.

```python
LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50 MB
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB chunks

def _download_large_object_with_resume(
    self,
    client,
    bucket: str,
    key: str,
    content_length: int,
) -> bytes:
    """
    Download large object using Range requests for resilience.
    
    If a chunk fails, we retry that specific chunk, not the whole file.
    """
    buffer = io.BytesIO()
    downloaded = 0
    
    while downloaded < content_length:
        end = min(downloaded + CHUNK_SIZE - 1, content_length - 1)
        range_header = f"bytes={downloaded}-{end}"
        
        for attempt in range(3):  # 3 retries per chunk
            try:
                response = client.get_object(
                    Bucket=bucket,
                    Key=key,
                    Range=range_header,
                )
                chunk_data = response["Body"].read()
                buffer.write(chunk_data)
                downloaded += len(chunk_data)
                break
                
            except ClientError as e:
                if attempt == 2:  # Final attempt
                    raise ConnectorTransientError(
                        f"Failed to download chunk {range_header} after 3 attempts"
                    )
                time.sleep(2 ** attempt)  # Exponential backoff
    
    return buffer.getvalue()
```

### 8.3. The "Ghost File" Problem (Delete Reconciliation)

**Problem:** When a user deletes a file in S3, it remains in our Vector DB forever, causing hallucination risk.

**Solution:** 
1. Use deterministic, canonical source IDs: `s3://{bucket}/{key}`
2. Ensure `list_files` yields complete inventory for delete detection
3. Parent sync job can compare current inventory vs stored documents

```python
def _build_canonical_source_id(self, bucket: str, key: str) -> str:
    """
    Build deterministic source ID for delete reconciliation.
    
    Format: s3://bucket-name/path/to/file.pdf
    
    This ID MUST be:
    - Deterministic (same input = same output)
    - Unique across all sources
    - Stable (doesn't change on re-sync)
    """
    return f"s3://{bucket}/{key}"

# In list_files:
yield RemoteFile(
    id=self._build_canonical_source_id(bucket, key),  # Deterministic!
    name=os.path.basename(key),
    # ...
)
```

**Parent Job Delete Detection Pattern:**
```python
# In sync job (not connector)
current_inventory = set(f.id for f in connector.list_files(config))
stored_inventory = set(doc.source_id for doc in get_user_documents(user_id, source="s3"))

# Files to delete (in DB but not in S3 anymore)
ghost_files = stored_inventory - current_inventory

for ghost_id in ghost_files:
    soft_delete_document(ghost_id)  # V1.5: implement soft delete
```

### 8.4. Symlink & Submodule Protection

**Context:** While S3/Box don't have symlinks, this is a defensive pattern for future local/GitHub connectors.

**For S3:** Not applicable (S3 is flat key-value store, no symlinks).

**For Box:** Box doesn't expose symlinks through API.

**For Future GitHub/Local Connectors:**
```python
# In traversal logic
import os

def _walk_directory(self, path: str) -> Iterator[str]:
    for entry in os.scandir(path):
        # CRITICAL: Never follow symlinks
        if entry.is_symlink():
            logger.warning(f"⚠️ Skipping symlink: {entry.path}")
            continue
        
        # Skip git internals
        if entry.name in {".git", ".gitmodules", "node_modules"}:
            continue
        
        if entry.is_dir(follow_symlinks=False):
            yield from self._walk_directory(entry.path)
        elif entry.is_file(follow_symlinks=False):
            yield entry.path
```

### 8.5. Enterprise Gate Enforcement

**Business Rule:** S3 connector is **Enterprise Only**.

**Implementation in API:**

```python
from api.v1.dependencies import get_effective_plan

@router.post("/connect/s3")
async def connect_s3(
    request: Request,
    body: S3ConnectRequest,
    user_id: str = Depends(get_current_user),
    plan: str = Depends(get_effective_plan),  # Get user's plan
):
    """Connect S3 bucket. **ENTERPRISE ONLY**."""
    
    # ENTERPRISE GATE: Non-negotiable
    ENTERPRISE_PLANS = {"enterprise", "enterprise_small", "enterprise_medium", "enterprise_large"}
    
    if plan not in ENTERPRISE_PLANS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ENTERPRISE_REQUIRED",
                "current_plan": plan,
                "message": "Amazon S3 connector is available exclusively on Enterprise plans. "
                           "Please upgrade to access cloud storage integrations.",
                "upgrade_url": "/settings/billing"
            }
        )
    
    # ... proceed with connection logic
```

---

**Document Status:** Ready for Architecture Review  
**Next Steps:** Upon approval, proceed with implementation phase  
**Estimated Implementation:** 3-5 days including tests
