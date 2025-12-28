"""
Ingestion API Endpoint - Zero-Copy Architecture

This endpoint acts as a thin proxy:
1. Validates the upload
2. Enforces quota limits (file count, storage, features)
3. Stores file in ephemeral staging bucket
4. Dispatches Celery task for processing
5. Returns job_id immediately

Heavy processing (parsing, embedding) happens in the worker.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from typing import Optional
from uuid import UUID
from models import IngestResponse
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from services.usage import check_can_upload, check_feature_access
from api.v1.dependencies import validate_team_access
from slowapi import Limiter
from slowapi.util import get_remote_address
import magic
import uuid
import datetime
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

# Allowed MIME types for uploaded files
ALLOWED_MIME_TYPES = {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "text/plain": [".txt"],
    "text/markdown": [".md"],
    "text/html": [".html", ".htm"],
}

# Dangerous MIME types that should always be rejected
DANGEROUS_MIME_TYPES = [
    "application/x-dosexec",
    "application/x-executable",
    "application/x-msdownload",
    "application/x-msdos-program",
]

# Storage bucket for ephemeral file staging
STAGING_BUCKET = "ephemeral-staging"


@router.post("/ingest", response_model=IngestResponse)
@limiter.limit("10/minute")
async def ingest_document(
    request: Request,
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    drive_id: Optional[str] = Form(None),
    notion_page_id: Optional[str] = Form(None),
    notion_token: Optional[str] = Form(None),
    metadata: str = Form(...),
    user_id: str = Depends(validate_team_access)  # Validates team access + returns user_id
):
    """
    Zero-Copy Ingestion Endpoint.
    
    Files are stored in ephemeral staging and processed by workers.
    No heavy computation happens in the API process.
    """
    supabase = get_supabase()
    
    # Parse metadata
    try:
        meta_dict = json.loads(metadata)
    except Exception:
        meta_dict = {}

    # =========================================================
    # ROUTE 1: WEB CRAWLING (Already async)
    # =========================================================
    if url:
        # QUOTA CHECK: Verify user has access to web crawling feature
        feature_check = await check_feature_access(UUID(user_id), "web_crawl")
        if not feature_check["allowed"]:
            logger.warning(f"🚫 [Quota] Web crawl blocked for user {user_id}: {feature_check['reason']}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=feature_check["reason"]
            )
        
        from datetime import datetime as dt
        crawl_type = meta_dict.get("crawl_type", "single")
        max_depth = min(int(meta_dict.get("depth", 1)), 10)
        respect_robots = meta_dict.get("respect_robots", True)
        
        crawl_config_data = {
            "user_id": user_id,
            "root_url": url,
            "crawl_type": crawl_type,
            "max_depth": max_depth,
            "respect_robots_txt": respect_robots,
            "status": "pending",
            "created_at": dt.utcnow().isoformat(),
            "updated_at": dt.utcnow().isoformat()
        }
        
        crawl_res = supabase.table("web_crawl_configs").insert(crawl_config_data).execute()
        if not crawl_res.data:
            raise HTTPException(status_code=500, detail="Failed to create crawl config")
        
        crawl_id = str(crawl_res.data[0]["id"])
        
        from worker.tasks import crawl_web_task
        task = crawl_web_task.delay(
            user_id=user_id,
            root_url=url,
            crawl_config={
                "crawl_id": crawl_id,
                "crawl_type": crawl_type,
                "max_depth": max_depth,
                "respect_robots": respect_robots
            }
        )
        
        supabase.table("web_crawl_configs").update({
            "celery_task_id": task.id
        }).eq("id", crawl_id).execute()
        
        logger.info(f"🕸️ [Ingest] Web crawl queued: {url}, task={task.id}")
        return IngestResponse(status="queued", doc_id=crawl_id)

    # =========================================================
    # ROUTE 2: CLOUD CONNECTORS (Drive, Notion)
    # =========================================================
    if drive_id or notion_page_id:
        from worker.tasks import ingest_connector_task
        
        connector_type = "drive" if drive_id else "notion"
        item_id = drive_id if drive_id else notion_page_id
        
        # Create ingestion job for tracking
        job_data = {
            "user_id": user_id,
            "provider": connector_type,
            "total_files": 1,
            "processed_files": 0,
            "status": "pending",
            "created_at": datetime.datetime.utcnow().isoformat(),
            "updated_at": datetime.datetime.utcnow().isoformat()
        }
        
        job_res = supabase.table("ingestion_jobs").insert(job_data).execute()
        if not job_res.data:
            raise HTTPException(status_code=500, detail="Failed to create ingestion job")
        
        job_id = str(job_res.data[0]["id"])
        
        # Dispatch to worker
        task = ingest_connector_task.delay(
            user_id=user_id,
            job_id=job_id,
            connector_type=connector_type,
            item_id=item_id,
            credentials={"access_token": notion_token} if notion_token else None
        )
        
        logger.info(f"🔗 [Ingest] Connector task queued: {connector_type}/{item_id}, task={task.id}")
        return IngestResponse(status="queued", doc_id=job_id)

    # =========================================================
    # ROUTE 3: FILE UPLOAD (Zero-Copy via Storage)
    # =========================================================
    if file:
        # QUOTA CHECK: Read file first to get size, then verify quota
        # We read early to get accurate size for quota check
        file_content = await file.read()
        file_size_bytes = len(file_content)
        await file.seek(0)  # Reset for subsequent reads
        
        # Check if user can upload this file
        quota_check = await check_can_upload(
            user_id=UUID(user_id),
            file_size_bytes=file_size_bytes,
            file_count=1
        )
        if not quota_check["allowed"]:
            logger.warning(f"🚫 [Quota] Upload blocked for user {user_id}: {quota_check['reason']}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=quota_check["reason"]
            )
        
        logger.info(f"✅ [Quota] Upload approved for user {user_id}: {file_size_bytes} bytes")
        
        # SECURITY: Validate file content type
        try:
            header = file_content[:2048]  # Use already-read content
            
            detected_mime = magic.from_buffer(header, mime=True)
            
            if detected_mime in DANGEROUS_MIME_TYPES:
                logger.warning(f"🚨 [Ingest] Blocked dangerous file: {file.filename}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type not allowed: {detected_mime}"
                )
            
            file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
            if detected_mime in ALLOWED_MIME_TYPES:
                allowed_extensions = ALLOWED_MIME_TYPES[detected_mime]
                if file_ext and file_ext not in allowed_extensions:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File extension mismatch: {file_ext} vs {detected_mime}"
                    )
            
            logger.info(f"✅ [Ingest] File validated: {file.filename}, MIME: {detected_mime}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ [Ingest] MIME validation error: {e}")
        
        # Generate unique storage path
        file_uuid = str(uuid.uuid4())
        storage_path = f"{user_id}/{file_uuid}/{file.filename}"
        
        # Upload to ephemeral staging bucket
        try:
            supabase.storage.from_(STAGING_BUCKET).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": detected_mime or "application/octet-stream"}
            )
            logger.info(f"📦 [Ingest] File staged: {storage_path}")
        except Exception as e:
            logger.error(f"❌ [Ingest] Storage upload failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stage file: {str(e)}"
            )
        
        # Create ingestion job for tracking
        job_data = {
            "user_id": user_id,
            "provider": "file",
            "total_files": 1,
            "processed_files": 0,
            "status": "pending",
            "created_at": datetime.datetime.utcnow().isoformat(),
            "updated_at": datetime.datetime.utcnow().isoformat()
        }
        
        job_res = supabase.table("ingestion_jobs").insert(job_data).execute()
        if not job_res.data:
            # Cleanup staged file on failure
            supabase.storage.from_(STAGING_BUCKET).remove([storage_path])
            raise HTTPException(status_code=500, detail="Failed to create ingestion job")
        
        job_id = str(job_res.data[0]["id"])
        
        # Dispatch to worker
        from worker.tasks import ingest_file_task
        task = ingest_file_task.delay(
            user_id=user_id,
            job_id=job_id,
            storage_path=storage_path,
            filename=file.filename,
            metadata=meta_dict
        )
        
        logger.info(f"📄 [Ingest] File task queued: {file.filename}, task={task.id}")
        return IngestResponse(status="queued", doc_id=job_id)

    # No valid input provided
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Either 'file', 'url', 'drive_id', or 'notion_page_id' must be provided."
    )