"""
Uploads API Endpoints - Presigned Upload Flow

Supports the presigned upload flow:
1. POST /uploads/upload-url -> Get presigned URL
2. PUT to presigned URL -> Upload file directly to storage
3. POST /uploads/file/reference -> Trigger ingestion
"""

import datetime
import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.v1.dependencies import (
    require_editor,
    require_paid_access,
    validate_team_access,
)
from api.v1.error_utils import ApiErrorCode, api_error, raise_http_error
from core.db import get_supabase
from core.exceptions import QuotaExceededError
from core.log_utils import safe_file_ref
from models import IngestResponse
from services.audit import audit_logger
from services.quotas import check_admission, increment_usage
from services.team_service import team_service
from services.usage import check_can_upload

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(validate_team_access), Depends(require_paid_access)])


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.

    Only allows alphanumeric characters, dots, dashes, and underscores.
    Replaces all other characters (including path separators) with underscores.

    Security: Prevents attacks like "../../etc/passwd" or "%2e%2e/secret.txt"
    """
    if not filename:
        return "unnamed_file"

    # Decode any URL encoding first
    try:
        from urllib.parse import unquote
        filename = unquote(filename)
    except Exception as e:
        logger.debug(f"[Upload] Failed to URL-decode filename: {e}")

    # Extract just the basename (remove any path components)
    filename = filename.split('/')[-1].split('\\')[-1]

    # Replace dangerous characters with underscore
    clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)

    # Ensure we don't have empty filename or just dots
    if not clean_name or clean_name.strip('.') == '':
        return "unnamed_file"

    # Limit length
    return clean_name[:255]


def verify_mime_type(file_bytes: bytes, claimed_mime: str) -> bool:
    """
    Verify file content matches claimed MIME type using magic numbers.

    Args:
        file_bytes: First 2KB+ of file content
        claimed_mime: Client-provided MIME type

    Returns:
        True if content matches claimed type or is in allowed list
    """
    try:
        import magic
        actual_mime = magic.from_buffer(file_bytes[:2048], mime=True)
        if actual_mime == claimed_mime:
            return True
        # Allow common mismatches (e.g., "text/plain" detected for CSV which claims "text/csv")
        if actual_mime in ALLOWED_MIME_TYPES:
            return True
        logger.warning(f"[Upload] MIME mismatch: claimed={claimed_mime}, actual={actual_mime}")
        return False
    except ImportError:
        logger.warning("[Upload] python-magic not installed, skipping MIME verification")
        return True  # Fail-open if library not available
    except Exception as e:
        logger.warning(f"[Upload] MIME verification failed: {e}")
        return True  # Fail-open on errors


def get_idempotency_key(request: Request) -> str | None:
    key = request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")
    if not key:
        return None
    key = key.strip()
    return key if key else None


async def _resolve_org_and_plan(user_id: str) -> tuple[str, str]:
    """
    Determine org_id (team or user) and plan code for quota enforcement.
    """
    team = await team_service.get_user_team(user_id)
    org_id = user_id
    plan_code = None
    if team:
        org_id = team.get("id") or user_id
        plan_code = team.get("plan")
    if not plan_code:
        plan_code = await team_service.get_effective_plan(user_id)
    return org_id, plan_code


def find_existing_ingestion_job(supabase, user_id: str, provider: str, idempotency_key: str) -> dict | None:
    if not idempotency_key:
        return None
    existing = supabase.table("ingestion_jobs").select("id,status").eq(
        "user_id", user_id
    ).eq("provider", provider).eq("idempotency_key", idempotency_key).order(
        "created_at", desc=True
    ).limit(1).execute()
    existing_data = existing.data if isinstance(getattr(existing, "data", None), list) else []
    return existing_data[0] if existing_data else None


# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

# Allowed MIME types for uploaded files
ALLOWED_MIME_TYPES = {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "text/plain": [".txt"],
    "text/markdown": [".md"],
    "text/html": [".html", ".htm"],
    "text/csv": [".csv"],
}

# Storage bucket for ephemeral file staging
STAGING_BUCKET = "ephemeral-staging"


# =============================================================================
# PRESIGNED URL UPLOAD ARCHITECTURE
# =============================================================================

from pydantic import BaseModel, Field


class UploadUrlRequest(BaseModel):
    """Request body for generating a presigned upload URL."""
    filename: str
    file_type: str  # MIME type
    file_size: int = Field(..., gt=0, le=100 * 1024 * 1024)  # Max 100MB
    content_hash: str | None = None  # SHA-256 hex for stable path & dedup
    force_overwrite: bool = False  # User confirmed overwrite of duplicate


class UploadUrlResponse(BaseModel):
    """Response containing the presigned upload URL."""
    upload_url: str
    storage_path: str
    expires_in: int  # Seconds until URL expires


class FileReferenceRequest(BaseModel):
    """Request body for ingesting an already-uploaded file."""
    storage_path: str
    filename: str
    file_size: int = Field(..., gt=0, le=100 * 1024 * 1024)  # Max 100MB
    metadata: dict = Field(default_factory=dict)


# =============================================================================
# DUPLICATE FILE DETECTION
# =============================================================================

from typing import Literal


class DuplicateCheckRequest(BaseModel):
    """Request for pre-flight duplicate check."""
    content_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 hex digest")
    filename: str = Field(..., min_length=1, description="Original filename for display")
    file_size: int = Field(..., gt=0, description="File size in bytes")


class ExistingDocument(BaseModel):
    """Information about an existing duplicate document."""
    id: str
    title: str
    created_at: str
    file_size_bytes: int | None = None


class DuplicateCheckResponse(BaseModel):
    """Response indicating whether file is a duplicate."""
    is_duplicate: bool
    existing_document: ExistingDocument | None = None
    action_required: Literal["none", "confirm_overwrite"]


@router.post("/check-duplicates", response_model=DuplicateCheckResponse)
@limiter.limit("30/minute")
async def check_duplicates(
    request: Request,
    body: DuplicateCheckRequest,
    user_id: str = Depends(require_editor)
):
    """
    Pre-flight duplicate check using content hash (SHA-256).

    Call this endpoint BEFORE uploading to detect if file already exists.
    If is_duplicate=True, show user a confirmation modal before proceeding.

    Security:
    - Validates hash format (64 hex chars)
    - Only checks within user's own documents
    - Rate-limited to prevent enumeration attacks
    """
    supabase = get_supabase()

    # Validate hash format (should be 64 hex characters)
    if not body.content_hash or len(body.content_hash) != 64:
        raise_http_error(
            400,
            ApiErrorCode.INVALID_INPUT.value,
            "Invalid content_hash: must be 64-character SHA-256 hex digest",
        )

    try:
        int(body.content_hash, 16)  # Validate hex
    except ValueError:
        raise_http_error(
            400,
            ApiErrorCode.INVALID_INPUT.value,
            "Invalid content_hash: must be valid hexadecimal",
        )

    # Check for existing document with same hash belonging to this user
    try:
        existing = supabase.table("documents").select(
            "id, title, created_at, file_size_bytes"
        ).eq("user_id", user_id).eq("content_hash", body.content_hash).limit(1).execute()

        if existing.data and len(existing.data) > 0:
            doc = existing.data[0]
            logger.info(f"[DupCheck] Found duplicate for hash {body.content_hash[:12]}... → doc {doc['id']}")
            return DuplicateCheckResponse(
                is_duplicate=True,
                existing_document=ExistingDocument(
                    id=doc["id"],
                    title=doc.get("title", body.filename),
                    created_at=doc.get("created_at", ""),
                    file_size_bytes=doc.get("file_size_bytes")
                ),
                action_required="confirm_overwrite"
            )

        logger.debug(f"[DupCheck] No duplicate found for hash {body.content_hash[:12]}...")
        return DuplicateCheckResponse(
            is_duplicate=False,
            existing_document=None,
            action_required="none"
        )

    except Exception as e:
        logger.error(f"[DupCheck] Database error: {e}")
        # Fail open - allow upload if check fails
        return DuplicateCheckResponse(
            is_duplicate=False,
            existing_document=None,
            action_required="none"
        )


@router.post("/upload-url", response_model=UploadUrlResponse)
@limiter.limit("20/minute")
async def generate_upload_url(
    request: Request,
    body: UploadUrlRequest,
    user_id: str = Depends(require_editor)
):
    """
    Generate a presigned URL for direct-to-storage file upload.

    Flow:
    1. Frontend calls this endpoint to get a presigned URL
    2. Frontend uploads directly to Supabase Storage using the URL
    3. Frontend calls POST /file/reference to trigger ingestion
    """
    supabase = get_supabase()
    org_id, plan_code = await _resolve_org_and_plan(user_id)

    # 1. Validate file type
    if body.file_type.lower() not in [m.lower() for m in ALLOWED_MIME_TYPES]:
        allowed = ", ".join(ALLOWED_MIME_TYPES.keys())
        raise_http_error(
            400,
            ApiErrorCode.INVALID_INPUT.value,
            f"Unsupported file type: {body.file_type}. Allowed: {allowed}",
        )

    # 2. Check quota before generating URL
    quota_check = await check_can_upload(user_id, body.file_size)
    if not quota_check["allowed"]:
        raise_http_error(
            status.HTTP_403_FORBIDDEN,
            "PLAN_LIMIT_EXCEEDED",
            quota_check["reason"],
            {"limits": quota_check.get("limits"), "usage": quota_check.get("usage")},
        )
    try:
        check_admission(
            org_id=org_id,
            plan_code=plan_code,
            file_size_bytes=body.file_size,
            job_count_increment=1,
        )
    except QuotaExceededError as exc:
        logger.warning("🚫 Admission denied for Org %s: %s", org_id, exc)
        audit_logger.log_sync(
            user_id=user_id,
            action="ingest.denied",
            resource_type="ingestion_request",
            resource_id=org_id,
            details={"reason": str(exc), "plan": plan_code, "file_size": body.file_size},
        )
        raise_http_error(
            status.HTTP_403_FORBIDDEN,
            "PLAN_LIMIT_EXCEEDED",
            str(exc),
            exc.details if isinstance(exc, QuotaExceededError) else None,
        )

    # 3. Generate storage path (SECURITY: sanitize filename to prevent path traversal)
    safe_filename = sanitize_filename(body.filename)

    # Use content hash for STABLE path (enables deduplication) or fallback to UUID
    if body.content_hash and len(body.content_hash) >= 12:
        # Use first 12 chars of content hash - stable for same file content
        path_segment = body.content_hash[:12]
        logger.info(f"[Upload] Using content-hash path segment: {path_segment}")
    else:
        # Fallback: random UUID (legacy behavior for clients without hash support)
        path_segment = str(uuid.uuid4())
        logger.debug("[Upload] Using UUID path segment (no content_hash provided)")

    storage_path = f"uploads/{user_id}/{path_segment}/{safe_filename}"

    # 4. Generate signed upload URL (valid for 10 minutes)
    try:
        result = supabase.storage.from_(STAGING_BUCKET).create_signed_upload_url(storage_path)

        if not result:
            logger.error(f"[Upload] Supabase returned None for {storage_path}")
            raise api_error(ApiErrorCode.EXTERNAL_SERVICE_ERROR, None, "get_upload_url")

        if not result.get("signed_url"):
            logger.error(f"[Upload] No signed_url in response: {result}")
            raise api_error(ApiErrorCode.EXTERNAL_SERVICE_ERROR, None, "get_upload_url")

        logger.info(f"[Upload] Generated presigned URL for {safe_file_ref(filename=body.filename)} (path:{storage_path[:16]}...)")

        return UploadUrlResponse(
            upload_url=result["signed_url"],
            storage_path=storage_path,
            expires_in=600  # 10 minutes — short window minimizes leaked URL risk
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Upload] Failed to generate presigned URL: {type(e).__name__}: {e}")
        raise api_error(ApiErrorCode.EXTERNAL_SERVICE_ERROR, e, "get_upload_url")


@router.post("/file/reference", response_model=IngestResponse)
@limiter.limit("10/minute")
async def ingest_file_reference(
    request: Request,
    body: FileReferenceRequest,
    user_id: str = Depends(require_editor)
):
    """
    Trigger ingestion for a file that was already uploaded to storage.

    This is the second step of the presigned URL upload flow:
    1. Frontend uploads file directly to storage using presigned URL
    2. Frontend calls this endpoint to trigger ingestion
    """
    supabase = get_supabase()
    org_id, plan_code = await _resolve_org_and_plan(user_id)
    idempotency_key = get_idempotency_key(request)

    # 1. Verify file exists in storage
    try:
        file_list = supabase.storage.from_(STAGING_BUCKET).list(
            path="/".join(body.storage_path.split("/")[:-1])
        )
        filename = body.storage_path.split("/")[-1]
        file_exists = any(f.get("name") == filename for f in file_list)

        if not file_exists:
            raise_http_error(
                404,
                ApiErrorCode.NOT_FOUND.value,
                "File not found in storage. Upload may have failed or expired.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"[Upload] Could not verify file existence: {e}")

    # 2. Check quota (double-check)
    quota_check = await check_can_upload(user_id, body.file_size)
    if not quota_check["allowed"]:
        try:
            supabase.storage.from_(STAGING_BUCKET).remove([body.storage_path])
        except Exception as e:
            logger.warning(f"[Upload] Failed to cleanup staging file after quota exceeded: {e}")
        raise_http_error(
            status.HTTP_403_FORBIDDEN,
            "PLAN_LIMIT_EXCEEDED",
            quota_check["reason"],
            {"limits": quota_check.get("limits"), "usage": quota_check.get("usage")},
        )
    try:
        check_admission(
            org_id=org_id,
            plan_code=plan_code,
            file_size_bytes=body.file_size,
            job_count_increment=1,
        )
    except QuotaExceededError as exc:
        logger.warning("🚫 Admission denied for Org %s: %s", org_id, exc)
        raise_http_error(
            status.HTTP_403_FORBIDDEN,
            "PLAN_LIMIT_EXCEEDED",
            str(exc),
            exc.details if isinstance(exc, QuotaExceededError) else None,
        )

    if idempotency_key:
        existing_job = find_existing_ingestion_job(supabase, user_id, "file_upload", idempotency_key)
        if existing_job:
            return IngestResponse(status=existing_job.get("status", "queued"), doc_id=existing_job["id"])

    # 3. Create ingestion job
    provider = "file_upload"
    job_data = {
        "user_id": user_id,
        "organization_id": org_id,
        "provider": provider,
        "total_files": 1,
        "processed_files": 0,
        "status": "pending",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    if idempotency_key:
        job_data["idempotency_key"] = idempotency_key

    job_res = supabase.table("ingestion_jobs").insert(job_data).execute()
    if not job_res.data:
        raise api_error(ApiErrorCode.DATABASE_ERROR, None, "ingest_file")

    job_id = str(job_res.data[0]["id"])
    audit_logger.log_sync(
        user_id=user_id,
        action="ingest.queued",
        resource_type="ingestion_job",
        resource_id=job_id,
        details={
            "provider": provider,
            "storage_path": body.storage_path,
            "filename": body.filename,
            "file_size": body.file_size,
            "plan": plan_code,
            "org_id": org_id,
        },
    )

    # Increment usage counters (best-effort)
    try:
        increment_usage(org_id=org_id, storage_bytes=body.file_size, job_count_increment=1)
    except Exception as exc:
        logger.warning("⚠️ [Quotas] Failed to increment usage for %s: %s", org_id, exc)

    # 4. Dispatch to worker using unified ingestion
    from worker.tasks import unified_ingest_task
    try:
        task = unified_ingest_task.delay(
            user_id=user_id,
            job_id=job_id,
            connector_type=provider,
            item_ids=[body.storage_path],
            credentials=None,
            plan_code=plan_code,
        )
    except Exception as e:
        logger.error(f"[Upload] Failed to dispatch unified task: {e}")
        try:
            supabase.storage.from_(STAGING_BUCKET).remove([body.storage_path])
        except Exception as e:
            logger.warning(f"[Upload] Failed to cleanup staging file after task dispatch failure: {e}")
        raise api_error(
            ApiErrorCode.SERVICE_UNAVAILABLE, e, "ingest_file",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    logger.info(f"[Upload] Unified task queued: {safe_file_ref(filename=body.filename)}, task={task.id}")
    return IngestResponse(status="queued", doc_id=job_id)
