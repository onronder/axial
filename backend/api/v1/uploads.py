"""
Uploads API Endpoints - Presigned Upload Flow

Supports the presigned upload flow:
1. POST /uploads/upload-url -> Get presigned URL
2. PUT to presigned URL -> Upload file directly to storage
3. POST /uploads/file/reference -> Trigger ingestion
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Optional
from models import IngestResponse
from core.db import get_supabase
from services.usage import check_can_upload
from api.v1.dependencies import validate_team_access, require_editor
from slowapi import Limiter
from slowapi.util import get_remote_address
import uuid
import datetime
import logging
import re

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(validate_team_access)])


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
    except Exception:
        pass
    
    # Extract just the basename (remove any path components)
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Replace dangerous characters with underscore
    clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    
    # Ensure we don't have empty filename or just dots
    if not clean_name or clean_name.strip('.') == '':
        return "unnamed_file"
    
    # Limit length
    return clean_name[:255]


def get_idempotency_key(request: Request) -> Optional[str]:
    key = request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")
    if not key:
        return None
    key = key.strip()
    return key if key else None


def find_existing_ingestion_job(supabase, user_id: str, provider: str, idempotency_key: str) -> Optional[dict]:
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
    file_size: int  # Size in bytes for quota check


class UploadUrlResponse(BaseModel):
    """Response containing the presigned upload URL."""
    upload_url: str
    storage_path: str
    expires_in: int  # Seconds until URL expires


class FileReferenceRequest(BaseModel):
    """Request body for ingesting an already-uploaded file."""
    storage_path: str
    filename: str
    file_size: int
    metadata: dict = Field(default_factory=dict)


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
    
    # 1. Validate file type
    if body.file_type.lower() not in [m.lower() for m in ALLOWED_MIME_TYPES.keys()]:
        allowed = ", ".join(ALLOWED_MIME_TYPES.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {body.file_type}. Allowed: {allowed}"
        )
    
    # 2. Check quota before generating URL
    quota_check = await check_can_upload(user_id, body.file_size)
    if not quota_check["allowed"]:
        raise HTTPException(status_code=403, detail=quota_check["reason"])
    
    # 3. Generate unique storage path (SECURITY: sanitize filename to prevent path traversal)
    unique_id = str(uuid.uuid4())
    safe_filename = sanitize_filename(body.filename)
    storage_path = f"uploads/{user_id}/{unique_id}/{safe_filename}"
    
    # 4. Generate signed upload URL (valid for 1 hour)
    try:
        result = supabase.storage.from_(STAGING_BUCKET).create_signed_upload_url(storage_path)
        
        if not result:
            logger.error(f"[Upload] Supabase returned None for {storage_path}")
            raise HTTPException(status_code=500, detail="Storage service returned empty response")
        
        if not result.get("signed_url"):
            logger.error(f"[Upload] No signed_url in response: {result}")
            raise HTTPException(status_code=500, detail="Failed to generate upload URL")
        
        logger.info(f"[Upload] Generated presigned URL for {body.filename} ({storage_path})")
        
        return UploadUrlResponse(
            upload_url=result["signed_url"],
            storage_path=storage_path,
            expires_in=3600  # 1 hour
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Upload] Failed to generate presigned URL: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")


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
    idempotency_key = get_idempotency_key(request)
    
    # 1. Verify file exists in storage
    try:
        file_list = supabase.storage.from_(STAGING_BUCKET).list(
            path="/".join(body.storage_path.split("/")[:-1])
        )
        filename = body.storage_path.split("/")[-1]
        file_exists = any(f.get("name") == filename for f in file_list)
        
        if not file_exists:
            raise HTTPException(
                status_code=404, 
                detail="File not found in storage. Upload may have failed or expired."
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
        except Exception:
            pass
        raise HTTPException(status_code=403, detail=quota_check["reason"])
    
    if idempotency_key:
        existing_job = find_existing_ingestion_job(supabase, user_id, "file_upload", idempotency_key)
        if existing_job:
            return IngestResponse(status=existing_job.get("status", "queued"), doc_id=existing_job["id"])

    # 3. Create ingestion job
    provider = "file_upload"
    job_data = {
        "user_id": user_id,
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
        raise HTTPException(status_code=500, detail="Failed to create ingestion job")
    
    job_id = str(job_res.data[0]["id"])
    
    # 4. Dispatch to worker using unified ingestion
    from worker.tasks import unified_ingest_task
    try:
        task = unified_ingest_task.delay(
            user_id=user_id,
            job_id=job_id,
            connector_type=provider,
            item_ids=[body.storage_path],
            credentials=None
        )
    except Exception as e:
        logger.error(f"[Upload] Failed to dispatch unified task: {e}")
        try:
            supabase.storage.from_(STAGING_BUCKET).remove([body.storage_path])
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task queue unavailable. Please try again later."
        )
    
    logger.info(f"[Upload] Unified task queued: {body.filename}, task={task.id}")
    return IngestResponse(status="queued", doc_id=job_id)
