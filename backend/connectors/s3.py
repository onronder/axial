"""
Amazon S3 Connector

Connects to Amazon S3 to fetch and sync documents from buckets.
Uses IAM credentials (Access Key + Secret Key) for authentication.

ENTERPRISE ONLY: This connector requires Enterprise plan.

SECURITY NOTES:
- Credentials are encrypted at rest using Fernet
- Only read operations (ListBucket, GetObject) are supported
- Prefix is REQUIRED to prevent full bucket scans (cost protection)

PRODUCTION SAFEGUARDS:
- Glacier/Deep Archive detection: Skips archived objects to avoid retrieval fees
- Resumable downloads: Large files use Range requests for resilience
- Deterministic IDs: Uses s3://bucket/key format for delete reconciliation
- Object count limits: Prevents bill shock from massive buckets

API Reference:
- https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html

Cost Awareness:
- LIST: $0.005 per 1,000 requests
- GET: $0.0004 per 1,000 requests
- HEAD: $0.0004 per 1,000 requests
- Data transfer: $0.09/GB (first 10TB)
- GLACIER retrieval: $0.03-$0.05/GB (AVOIDED by storage class check)
"""

from __future__ import annotations

import io
import logging
import mimetypes
import os
import time
from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    ReadTimeoutError,
)
from fastapi.concurrency import run_in_threadpool

from connectors.base import (
    BaseConnector,
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorTransientError,
    RemoteFile,
)
from connectors.enhanced import (
    EnhancedConnector,
    ItemNotFoundError,
    SourceDocument,
    SourceType,
)
from connectors.utils import build_config_from_kwargs, load_integration
from core.scopes import build_scope_uri
from core.security import decrypt_token

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

DEFAULT_REGION = "us-east-1"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB per file
MAX_OBJECTS_PER_SYNC = 10_000  # Prevent runaway API costs
LIST_PAGE_SIZE = 1000  # S3 maximum per request

# Network resilience
DEFAULT_TIMEOUT_SECONDS = 30
DOWNLOAD_TIMEOUT_SECONDS = 120
LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50 MB - use Range requests above this
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB chunks for resumable downloads
MAX_RETRIES = 3

# =============================================================================
# Storage Class Handling (GLACIER TRAP PREVENTION)
# =============================================================================

# Storage classes that require restoration before access
# Attempting GetObject on these throws InvalidObjectState or triggers fees
ARCHIVED_STORAGE_CLASSES = frozenset({
    "GLACIER",
    "DEEP_ARCHIVE",
    "GLACIER_IR",  # Glacier Instant Retrieval (cheaper but still archived)
})

# All valid storage classes for reference
STANDARD_STORAGE_CLASSES = frozenset({
    "STANDARD",
    "REDUCED_REDUNDANCY",
    "STANDARD_IA",  # Infrequent Access - accessible immediately
    "ONEZONE_IA",   # One Zone IA - accessible immediately
    "INTELLIGENT_TIERING",  # Auto-tiering - accessible immediately
    "EXPRESS_ONEZONE",  # S3 Express - accessible immediately
})

# =============================================================================
# Supported File Extensions (Cost Protection)
# =============================================================================

SUPPORTED_EXTENSIONS = frozenset({
    # Documents
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
    # Text
    ".txt", ".md", ".markdown", ".rst", ".rtf",
    # Code (if applicable)
    ".py", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".c", ".cpp", ".h",
    # Data
    ".json", ".yaml", ".yml", ".csv", ".xml",
    # Web
    ".html", ".htm",
})

# Patterns to always skip (system files, logs, backups)
SKIP_PATTERNS = frozenset({
    ".log", ".bak", ".tmp", ".swp", ".lock",
    ".gz", ".zip", ".tar", ".rar", ".7z",
    ".exe", ".dll", ".so", ".dylib",
    ".pyc", ".pyo", ".class",
})

COMMON_MIME_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".md": "text/markdown",
}


class S3Connector(EnhancedConnector, BaseConnector):
    """
    Amazon S3 connector for unified ingestion pipeline.

    ENTERPRISE ONLY - Requires Enterprise plan subscription.

    Features:
    - IAM credential authentication with Fernet encryption
    - Mandatory prefix requirement for cost control
    - Glacier/Deep Archive detection (prevents retrieval fees)
    - Resumable downloads for large files (Range requests)
    - Suffix filtering for supported document types
    - Object count limits to prevent bill shock
    - Deterministic source IDs for delete reconciliation

    Security:
    - Read-only operations only (ListBucket, GetObject, HeadObject)
    - Credentials encrypted at rest
    - Prefix required to prevent full bucket scans
    """

    @property
    def connector_type(self) -> SourceType:
        return SourceType.S3

    @property
    def supports_incremental_sync(self) -> bool:
        return True  # Can filter by LastModified

    @property
    def supports_batch_fetch(self) -> bool:
        return False  # S3 doesn't support batch downloads

    # =========================================================================
    # Configuration & Validation
    # =========================================================================

    def validate_config(self, config: dict) -> bool:
        """
        Validate S3 configuration.

        Validation Steps:
        1. Check required fields (access_key, secret, region, bucket)
        2. Validate prefix is non-empty (COST PROTECTION - raises ValueError)
        3. Attempt HEAD bucket to verify credentials and bucket access

        Cost: 1 HEAD request (essentially free)

        Raises:
            ValueError: If prefix is missing (cost protection)
        """
        if not isinstance(config, dict):
            return False

        # Required fields (excluding prefix, handled separately with ValueError)
        required = ["access_key_id", "secret_access_key", "region", "bucket_name"]
        for field in required:
            if not config.get(field):
                logger.warning(f"❌ [S3] Missing required field: {field}")
                return False

        # COST PROTECTION: Prefix is mandatory - this MUST raise to prevent full bucket scans
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
        except Exception as e:
            logger.warning(f"⚠️ [S3] Validation error (may be transient): {e}")
            return True  # Network errors = config might be OK

    def _verify_access(self, config: dict) -> dict:
        """
        Verify S3 access using HEAD bucket request.

        This is the cheapest way to verify:
        - Credentials are valid
        - Bucket exists
        - User has ListBucket permission

        Cost: HEAD request is essentially free

        Returns:
            Status dict

        Raises:
            ConnectorAuthError: Invalid credentials or access denied
            ConnectorTransientError: Network/service issues
        """
        client = self._get_s3_client(config)

        try:
            # HEAD bucket verifies access without listing
            client.head_bucket(Bucket=config["bucket_name"])
            logger.info(f"✅ [S3] Verified access to bucket: {config['bucket_name']}")
            return {"status": "connected"}

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            if error_code in ("403", "AccessDenied"):
                raise ConnectorAuthError(
                    "S3 access denied. Please verify your IAM policy includes "
                    "s3:ListBucket permission for this bucket."
                )
            elif error_code in ("404", "NoSuchBucket"):
                raise ConnectorAuthError(
                    f"S3 bucket '{config['bucket_name']}' not found. "
                    "Please verify the bucket name and region."
                )
            elif error_code == "InvalidAccessKeyId":
                raise ConnectorAuthError(
                    "Invalid AWS Access Key ID. Please check your credentials."
                )
            elif error_code == "SignatureDoesNotMatch":
                raise ConnectorAuthError(
                    "AWS signature mismatch. Please verify your Secret Access Key."
                )
            else:
                raise ConnectorTransientError(f"S3 error: {error_code} - {e}")

        except NoCredentialsError:
            raise ConnectorAuthError("Invalid or missing AWS credentials")

        except EndpointConnectionError as e:
            raise ConnectorTransientError(f"S3 connection failed: {e}")

    def _get_s3_client(self, config: dict):
        """
        Create boto3 S3 client with proper configuration.

        Features:
        - Automatic credential decryption
        - Adaptive retry mode (exponential backoff)
        - Proper timeouts
        - SigV4 signing
        """
        # Decrypt credentials if encrypted
        access_key = config.get("access_key_id", "")
        secret_key = config.get("secret_access_key", "")

        # Attempt decryption (will return as-is if not encrypted)
        try:
            access_key = decrypt_token(access_key)
        except Exception:
            pass  # Not encrypted — use as-is (expected for plaintext keys)

        try:
            secret_key = decrypt_token(secret_key)
        except Exception:
            pass  # Not encrypted — use as-is (expected for plaintext keys)

        return boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=config.get("region", DEFAULT_REGION),
            config=Config(
                connect_timeout=10,
                read_timeout=DEFAULT_TIMEOUT_SECONDS,
                retries={
                    "max_attempts": MAX_RETRIES,
                    "mode": "adaptive"  # Adaptive retry with exponential backoff
                },
                signature_version="s3v4",
            )
        )

    # =========================================================================
    # File Discovery - list_files()
    # =========================================================================

    def list_files(
        self,
        config: dict,
        since: datetime | None = None,
    ) -> Iterator[RemoteFile]:
        """
        List files from S3 bucket with pagination.

        Features:
        - Prefix-filtered listing (REQUIRED for cost protection)
        - Suffix filtering for supported extensions
        - Glacier/Deep Archive detection (skip archived objects)
        - Object count limit (MAX_OBJECTS_PER_SYNC)
        - Incremental sync support via `since` parameter
        - Deterministic IDs for delete reconciliation

        Cost: $0.005 per 1,000 objects listed

        Args:
            config: S3 configuration dict
            since: Optional datetime for incremental sync

        Yields:
            RemoteFile objects for each accessible document
        """
        resolved = self._resolve_config(config)
        client = self._get_s3_client(resolved)

        bucket = resolved["bucket_name"]
        prefix = self._normalize_prefix(resolved["prefix"])

        logger.info(f"📁 [S3] Listing objects in s3://{bucket}/{prefix}")

        object_count = 0
        skipped_archived = 0
        skipped_extension = 0
        skipped_size = 0

        paginator = client.get_paginator("list_objects_v2")

        try:
            for page in paginator.paginate(
                Bucket=bucket,
                Prefix=prefix,
                PaginationConfig={"PageSize": LIST_PAGE_SIZE}
            ):
                for obj in page.get("Contents", []):
                    # Check object limit (COST PROTECTION)
                    if object_count >= MAX_OBJECTS_PER_SYNC:
                        logger.warning(
                            f"⚠️ [S3] Reached object limit ({MAX_OBJECTS_PER_SYNC}). "
                            f"Consider narrowing your prefix. "
                            f"Skipped: {skipped_archived} archived, {skipped_extension} wrong type"
                        )
                        return

                    key = obj["Key"]

                    # Skip directories (keys ending with /)
                    if key.endswith("/"):
                        continue

                    # GLACIER TRAP: Check storage class
                    storage_class = obj.get("StorageClass", "STANDARD")
                    if storage_class in ARCHIVED_STORAGE_CLASSES:
                        skipped_archived += 1
                        logger.debug(
                            f"⏭️ [S3] Skipping archived object: {key} "
                            f"(StorageClass={storage_class})"
                        )
                        continue

                    # Apply suffix filter (COST PROTECTION)
                    if not self._should_process_object(key):
                        skipped_extension += 1
                        continue

                    # Apply incremental sync filter
                    last_modified = obj.get("LastModified")
                    if since and last_modified:
                        # Ensure timezone-aware comparison
                        if last_modified.tzinfo is None:
                            last_modified = last_modified.replace(tzinfo=timezone.utc)
                        if since.tzinfo is None:
                            since = since.replace(tzinfo=timezone.utc)
                        if last_modified < since:
                            continue

                    # Check file size limit
                    size = obj.get("Size", 0)
                    if size > MAX_FILE_SIZE:
                        skipped_size += 1
                        logger.warning(
                            f"⚠️ [S3] Skipping large file: {key} ({size:,} bytes)"
                        )
                        continue

                    object_count += 1
                    yield self._object_to_remote_file(obj, bucket)

            logger.info(
                f"📁 [S3] Listed {object_count} objects from s3://{bucket}/{prefix} "
                f"(skipped: {skipped_archived} archived, {skipped_extension} unsupported, "
                f"{skipped_size} too large)"
            )

        except ClientError as e:
            self._handle_client_error(e, "list_files")

    def _object_to_remote_file(self, obj: dict, bucket: str) -> RemoteFile:
        """
        Convert S3 object to RemoteFile with deterministic ID.

        CRITICAL: Uses s3://bucket/key format for delete reconciliation.
        """
        key = obj["Key"]

        return RemoteFile(
            id=self._build_canonical_source_id(bucket, key),  # DETERMINISTIC!
            name=os.path.basename(key),
            mime_type=self._guess_mime_type(key),
            size=obj.get("Size"),
            modified_at=obj.get("LastModified"),
            parent_id=os.path.dirname(key) or None,
            web_view_url=f"https://{bucket}.s3.amazonaws.com/{key}",
        )

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

    def _should_process_object(self, key: str) -> bool:
        """
        Check if object should be processed based on extension and patterns.

        Returns False for:
        - Unsupported file extensions
        - System files and backups
        - Log files
        """
        # Get extension
        _, ext = os.path.splitext(key.lower())

        # Skip system patterns
        if any(pattern in key.lower() for pattern in SKIP_PATTERNS):
            return False

        # Skip hidden files and directories
        parts = key.split("/")
        if any(part.startswith(".") for part in parts if part):
            return False

        # Check supported extensions
        return ext in SUPPORTED_EXTENSIONS

    def _normalize_prefix(self, prefix: str) -> str:
        """Normalize prefix to ensure consistent format.

        Raises:
            ValueError: If prefix is empty after normalization (cost protection).
        """
        prefix = prefix.strip()
        # Don't add trailing slash - S3 handles both
        if prefix.startswith("/"):
            prefix = prefix[1:]

        if not prefix:
            raise ValueError(
                "S3 prefix is required to prevent expensive full-bucket scans. "
                "Please specify a folder path (e.g., 'documents/')."
            )

        return prefix

    # =========================================================================
    # Content Fetching - fetch_file_content() & fetch_documents()
    # =========================================================================

    def fetch_file_content(self, file_id: str, config: dict) -> bytes:
        """
        Fetch raw file bytes from S3.

        Args:
            file_id: S3 object key or canonical ID (s3://bucket/key)
            config: Configuration with credentials

        Returns:
            Raw file content as bytes
        """
        resolved = self._resolve_config(config)
        client = self._get_s3_client(resolved)
        bucket = resolved["bucket_name"]

        # Handle canonical ID format
        key = self._extract_key_from_id(file_id, bucket)

        return self._download_object(client, bucket, key)

    async def fetch_documents(
        self,
        item_ids: list[str],
        credentials: dict[str, Any] | None = None,
        **kwargs,
    ) -> AsyncIterator[SourceDocument]:
        """
        Async wrapper for fetch_documents_sync.

        Uses thread pool to avoid blocking the event loop.
        """
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
        credentials: dict[str, Any] | None = None,
        **kwargs,
    ) -> Iterator[SourceDocument]:
        """
        Fetch documents from S3 for ingestion pipeline.

        PRODUCTION SAFEGUARDS:
        - Checks StorageClass before download (Glacier trap prevention)
        - Uses Range requests for large files (resumable downloads)
        - Continues on individual file errors (doesn't fail entire job)

        Args:
            item_ids: List of S3 object keys or canonical IDs
            credentials: S3 credentials dict
            **kwargs: Additional params including user_id

        Yields:
            SourceDocument for each successfully fetched file

        Cost: $0.0004 per GET request + data transfer
        """
        if not item_ids:
            return

        config = self._build_config(credentials, **kwargs)
        resolved = self._resolve_config(config)
        client = self._get_s3_client(resolved)

        bucket = resolved["bucket_name"]
        prefix = self._normalize_prefix(resolved["prefix"])

        logger.info(f"📥 [S3Connector] Fetching {len(item_ids)} object(s)")

        processed_count = 0
        skipped_archived = 0
        failed_count = 0

        for item_id in item_ids:
            key = self._extract_key_from_id(item_id, bucket)

            try:
                # GLACIER TRAP PREVENTION: Check storage class first
                # HEAD request is cheap ($0.0004 per 1000)
                try:
                    head_response = client.head_object(Bucket=bucket, Key=key)
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "Unknown")
                    if error_code in ("404", "NoSuchKey"):
                        logger.warning(f"⚠️ [S3] Object not found: {key}")
                        continue
                    raise

                storage_class = head_response.get("StorageClass", "STANDARD")

                if storage_class in ARCHIVED_STORAGE_CLASSES:
                    skipped_archived += 1
                    logger.warning(
                        f"⚠️ [S3] Skipping archived object: {key} "
                        f"(StorageClass={storage_class}). "
                        "Restore from Glacier required before access."
                    )
                    continue

                content_length = head_response.get("ContentLength", 0)
                content_type = head_response.get("ContentType", "application/octet-stream")
                last_modified = head_response.get("LastModified")
                etag = head_response.get("ETag", "").strip('"')

                # Check size limit
                if content_length > MAX_FILE_SIZE:
                    logger.warning(
                        f"⚠️ [S3] Skipping large file: {key} ({content_length:,} bytes)"
                    )
                    continue

                # Download with appropriate strategy
                content = self._download_object(
                    client, bucket, key, content_length
                )

                # Build source document with deterministic ID
                metadata = {
                    "source": "s3",
                    "bucket": bucket,
                    "prefix": prefix,
                    "key": key,
                    "region": resolved.get("region", DEFAULT_REGION),
                    "storage_class": storage_class,
                    "last_modified": last_modified.isoformat() if last_modified else None,
                    "etag": etag,
                    "content_type": content_type,
                }
                metadata["scope_id"] = build_scope_uri("s3", metadata)

                yield SourceDocument(
                    content=content,
                    metadata=metadata,
                    source_type=SourceType.S3,
                    source_id=self._build_canonical_source_id(bucket, key),
                    filename=os.path.basename(key),
                    mime_type=self._guess_mime_type(key, content_type),
                    size_bytes=len(content),
                    parent_id=os.path.dirname(key) or None,
                )

                processed_count += 1

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code in ("404", "NoSuchKey"):
                    logger.warning(f"⚠️ [S3] Object not found: {key}")
                elif error_code == "AccessDenied":
                    logger.error(f"❌ [S3] Access denied to: {key}")
                    raise ConnectorAuthError(f"S3 access denied to: {key}")
                elif error_code == "InvalidObjectState":
                    # Object is archived - should have been caught by HEAD check
                    skipped_archived += 1
                    logger.warning(f"⚠️ [S3] Object archived (InvalidObjectState): {key}")
                else:
                    failed_count += 1
                    logger.error(f"❌ [S3] Failed to fetch {key}: {error_code}")
                continue

            except Exception as e:
                failed_count += 1
                logger.error(f"❌ [S3] Unexpected error fetching {key}: {e}")
                continue

        logger.info(
            f"📥 [S3Connector] Fetched {processed_count}/{len(item_ids)} objects "
            f"(skipped: {skipped_archived} archived, {failed_count} failed)"
        )

    def _download_object(
        self,
        client,
        bucket: str,
        key: str,
        content_length: int | None = None,
    ) -> bytes:
        """
        Download object with appropriate strategy based on size.

        - Small files (<50MB): Standard streaming download
        - Large files (>=50MB): Chunked Range requests for resilience
        """
        # Get content length if not provided
        if content_length is None:
            try:
                head = client.head_object(Bucket=bucket, Key=key)
                content_length = head.get("ContentLength", 0)
            except ClientError:
                content_length = 0

        # Use Range requests for large files
        if content_length >= LARGE_FILE_THRESHOLD:
            return self._download_large_object(client, bucket, key, content_length)

        # Standard streaming download for smaller files
        return self._download_small_object(client, bucket, key)

    def _download_small_object(self, client, bucket: str, key: str) -> bytes:
        """
        Standard streaming download for files under threshold.
        """
        try:
            response = client.get_object(Bucket=bucket, Key=key)
            body = response["Body"]

            # Stream in chunks
            buffer = io.BytesIO()
            for chunk in body.iter_chunks(chunk_size=1024 * 1024):  # 1MB chunks
                buffer.write(chunk)

            body.close()
            return buffer.getvalue()

        except (ReadTimeoutError, ConnectTimeoutError) as e:
            raise ConnectorTransientError(f"S3 download timeout: {e}")

    def _download_large_object(
        self,
        client,
        bucket: str,
        key: str,
        content_length: int,
    ) -> bytes:
        """
        Download large object using Range requests for resilience.

        If a chunk fails, we retry that specific chunk, not the whole file.
        This prevents wasting bandwidth on partial downloads.
        """
        buffer = io.BytesIO()
        downloaded = 0

        logger.info(
            f"📦 [S3] Large file download ({content_length:,} bytes) "
            f"using Range requests: {key}"
        )

        while downloaded < content_length:
            end = min(downloaded + CHUNK_SIZE - 1, content_length - 1)
            range_header = f"bytes={downloaded}-{end}"

            for attempt in range(MAX_RETRIES):
                try:
                    response = client.get_object(
                        Bucket=bucket,
                        Key=key,
                        Range=range_header,
                    )
                    chunk_data = response["Body"].read()
                    response["Body"].close()

                    buffer.write(chunk_data)
                    downloaded += len(chunk_data)
                    break

                except (ClientError, ReadTimeoutError, ConnectTimeoutError) as e:
                    if attempt == MAX_RETRIES - 1:  # Final attempt
                        raise ConnectorTransientError(
                            f"Failed to download chunk {range_header} after {MAX_RETRIES} attempts: {e}"
                        )

                    delay = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                    logger.warning(
                        f"⏳ [S3] Chunk download failed, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES})"
                    )
                    time.sleep(delay)

        logger.info(f"✅ [S3] Large file download complete: {key}")
        return buffer.getvalue()

    def _extract_key_from_id(self, item_id: str, bucket: str) -> str:
        """
        Extract S3 key from item ID.

        Handles both formats:
        - Canonical: s3://bucket/path/to/file.pdf
        - Raw key: path/to/file.pdf
        """
        if item_id.startswith("s3://"):
            # Extract key from canonical format
            # s3://bucket/key -> key
            prefix = f"s3://{bucket}/"
            if item_id.startswith(prefix):
                return item_id[len(prefix):]
            # Different bucket in ID - just extract key portion
            parts = item_id[5:].split("/", 1)
            return parts[1] if len(parts) > 1 else parts[0]

        return item_id

    # =========================================================================
    # Configuration Resolution
    # =========================================================================

    def _build_config(
        self,
        credentials: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Build configuration dict by merging credentials with kwargs."""
        return build_config_from_kwargs(
            credentials,
            auth_keys=("user_id", "integration_id", "bucket_name", "prefix", "region"),
            **kwargs,
        )

    def _resolve_config(self, config: dict) -> dict:
        """
        Resolve configuration, fetching credentials from database if needed.
        """
        resolved = dict(config or {})

        # If credentials already provided, return as-is
        if resolved.get("access_key_id") and resolved.get("secret_access_key"):
            return resolved

        # Load from user_integrations if user_id provided
        user_id = resolved.get("user_id")
        integration_id = resolved.get("integration_id")

        if user_id or integration_id:
            integration = self._load_integration(resolved)
            creds = integration.get("credentials", {})

            # Merge stored credentials
            resolved["access_key_id"] = creds.get("access_key_id")
            resolved["secret_access_key"] = creds.get("secret_access_key")
            resolved["region"] = creds.get("region", resolved.get("region", DEFAULT_REGION))
            resolved["bucket_name"] = creds.get("bucket_name", resolved.get("bucket_name"))
            resolved["prefix"] = creds.get("prefix", resolved.get("prefix", ""))

        return resolved

    def _load_integration(self, config: dict) -> dict[str, Any]:
        """Load integration record from database using shared utility."""
        return load_integration(
            "s3",
            integration_id=config.get("integration_id"),
            user_id=config.get("user_id"),
        )

    # =========================================================================
    # Error Handling
    # =========================================================================

    def _handle_client_error(self, error: ClientError, operation: str):
        """Map boto3 ClientError to connector exceptions."""
        error_code = error.response.get("Error", {}).get("Code", "Unknown")
        error_message = error.response.get("Error", {}).get("Message", str(error))

        if error_code in ("AccessDenied", "403"):
            raise ConnectorAuthError(f"S3 access denied: {error_message}")
        elif error_code in ("InvalidAccessKeyId", "SignatureDoesNotMatch"):
            raise ConnectorAuthError(f"S3 authentication failed: {error_message}")
        elif error_code in ("NoSuchBucket", "404"):
            raise ConnectorAuthError(f"S3 bucket not found: {error_message}")
        elif error_code == "NoSuchKey":
            raise ItemNotFoundError(f"S3 object not found: {error_message}")
        elif error_code == "SlowDown":
            raise ConnectorRateLimitError(f"S3 rate limit: {error_message}")
        elif error_code == "InvalidObjectState":
            # Glacier/Deep Archive - should be caught earlier
            raise ConnectorTransientError(
                f"S3 object not accessible (archived): {error_message}"
            )
        else:
            raise ConnectorTransientError(f"S3 error ({error_code}): {error_message}")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    @staticmethod
    def _guess_mime_type(
        filename: str,
        content_type: str | None = None,
    ) -> str:
        """
        Guess MIME type from filename, falling back to content_type.
        """
        if filename:
            guessed, _ = mimetypes.guess_type(filename)
            if guessed:
                return guessed
            fallback = COMMON_MIME_TYPES.get(Path(filename).suffix.lower())
            if fallback:
                return fallback

        if content_type and content_type != "application/octet-stream":
            return content_type

        return "application/octet-stream"


# =============================================================================
# Module-level Connector Instance
# =============================================================================

def get_s3_connector() -> S3Connector:
    """Factory function to get an S3Connector instance."""
    return S3Connector()
