"""
Jobs API Router

Endpoints for tracking background job progress.
Used for polling-based progress updates during ingestion.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from api.v1.dependencies import validate_team_access, require_editor
from core.security import get_current_user
from core.db import get_supabase
from core.ingestion_utils import normalize_provider
from models import IngestionJobResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(validate_team_access)])


@router.get("/jobs/active", response_model=Optional[IngestionJobResponse])
async def get_active_job(
    user_id: str = Depends(get_current_user)
):
    """
    Get the user's current active ingestion job.
    
    Returns the most recent job with status 'pending' or 'processing'.
    Used by frontend for polling-based progress updates.
    
    Returns:
        IngestionJobResponse if active job exists, None otherwise (204)
    """
    supabase = get_supabase()
    
    try:
        # Query for active jobs (pending or processing)
        response = supabase.table("ingestion_jobs")\
            .select("*")\
            .eq("user_id", user_id)\
            .in_("status", ["pending", "processing"])\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if not response.data:
            # No active job - return None (will be 204 or null)
            return None
        
        job = response.data[0]
        
        # Calculate progress percentage
        total = job.get("total_files", 0)
        processed = job.get("processed_files", 0)
        percent = (processed / total * 100) if total > 0 else 0
        
        return IngestionJobResponse(
            id=job["id"],
            provider=normalize_provider(job.get("provider")) or job.get("provider"),
            total_files=total,
            processed_files=processed,
            status=job["status"],
            percent=round(percent, 1),
            error_message=job.get("error_message"),
            created_at=job.get("created_at")
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch active job: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job status")


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_job_by_id(
    job_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Get a specific job by ID.
    
    Ensures user can only access their own jobs.
    """
    supabase = get_supabase()
    
    try:
        try:
            response = supabase.table("ingestion_jobs")\
                .select("id, provider, total_files, processed_files, status, error_message, created_at")\
                .eq("id", job_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()
        except Exception as e:
            message = str(e)
            if "PGRST116" in message or "JSON object requested" in message:
                raise HTTPException(status_code=404, detail="Job not found")
            logger.error(f"Failed to fetch job {job_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch job status")
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = response.data
        
        # Calculate progress percentage
        total = job.get("total_files", 0)
        processed = job.get("processed_files", 0)
        percent = (processed / total * 100) if total > 0 else 0
        
        return IngestionJobResponse(
            id=job["id"],
            provider=normalize_provider(job.get("provider")) or job.get("provider"),
            total_files=total,
            processed_files=processed,
            status=job["status"],
            percent=round(percent, 1),
            error_message=job.get("error_message"),
            created_at=job.get("created_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job status")


@router.get("/jobs", response_model=list[IngestionJobResponse])
async def list_recent_jobs(
    user_id: str = Depends(get_current_user),
    limit: int = 10
):
    """
    List user's recent ingestion jobs.
    
    Useful for showing job history.
    """
    supabase = get_supabase()
    
    try:
        response = supabase.table("ingestion_jobs")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        jobs = []
        for job in response.data or []:
            total = job.get("total_files", 0)
            processed = job.get("processed_files", 0)
            percent = (processed / total * 100) if total > 0 else 0
            
            jobs.append(IngestionJobResponse(
                id=job["id"],
                provider=job["provider"],
                total_files=total,
                processed_files=processed,
                status=job["status"],
                percent=round(percent, 1),
                error_message=job.get("error_message"),
                created_at=job.get("created_at")
            ))
        
        return jobs
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to list jobs")


# ============================================================
# CANCEL / RETRY ENDPOINTS
# ============================================================

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    user_id: str = Depends(require_editor)
):
    """
    Cancel an in-progress ingestion job.
    
    - Updates job status to 'cancelled'
    - Revokes any pending Celery tasks
    - Updates pending file statuses to 'cancelled'
    
    Returns:
        Job ID and cancellation status
    """
    from datetime import datetime, timezone
    
    supabase = get_supabase()
    
    try:
        # Verify ownership
        response = supabase.table("ingestion_jobs")\
            .select("id, status, celery_task_id")\
            .eq("id", job_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = response.data
        
        # Check if job can be cancelled
        if job["status"] in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Job already {job['status']}, cannot cancel"
            )
        
        # Revoke Celery task if exists
        celery_task_id = job.get("celery_task_id")
        if celery_task_id:
            try:
                from worker.celery_app import celery_app
                celery_app.control.revoke(celery_task_id, terminate=True)
                logger.info(f"🛑 Revoked Celery task {celery_task_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to revoke Celery task: {e}")
        
        # Update job status
        supabase.table("ingestion_jobs").update({
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "cancelled_by": user_id,
            "message": "Cancelled by user",
            "status_message": "Cancelled by user"
        }).eq("id", job_id).execute()
        
        # Update any pending/processing file statuses
        supabase.table("ingestion_file_status").update({
            "status": "cancelled",
            "status_message": "Cancelled by user",
            "progress": 0
        }).eq("job_id", job_id)\
         .in_("status", ["pending", "uploading", "parsing", "processing", "embedding", "indexing"])\
         .execute()
        
        logger.info(f"✅ Cancelled job {job_id} for user {user_id}")
        
        return {
            "status": "cancelled",
            "job_id": job_id,
            "message": "Job cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.post("/jobs/files/{file_status_id}/retry")
async def retry_file(
    file_status_id: str,
    user_id: str = Depends(require_editor)
):
    """
    Retry a failed file ingestion.
    
    - Validates file status and ownership
    - Increments retry count (max 3 attempts)
    - Resets status to 'pending' for reprocessing
    
    Returns:
        File status ID and retry count
    """
    supabase = get_supabase()
    
    try:
        # Get file status
        response = supabase.table("ingestion_file_status")\
            .select("*, ingestion_jobs!inner(user_id, provider, celery_task_id)")\
            .eq("id", file_status_id)\
            .single()\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_status = response.data
        
        # Verify ownership through parent job
        if file_status["ingestion_jobs"]["user_id"] != user_id:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if file can be retried
        if file_status["status"] != "failed":
            raise HTTPException(
                status_code=400, 
                detail=f"Only failed files can be retried, current status: {file_status['status']}"
            )
        
        if not file_status.get("can_retry", True):
            raise HTTPException(
                status_code=400, 
                detail="This file cannot be retried (marked as non-retryable)"
            )
        
        # Check retry count
        retry_count = file_status.get("retry_count", 0) + 1
        if retry_count > 3:
            raise HTTPException(
                status_code=400, 
                detail="Maximum retry attempts (3) exceeded for this file"
            )
        
        # Reset file status for retry
        supabase.table("ingestion_file_status").update({
            "status": "pending",
            "progress": 0,
            "status_message": f"Retry attempt {retry_count}/3",
            "error_message": None,
            "retry_count": retry_count
        }).eq("id", file_status_id).execute()
        
        # Update parent job to processing if it was completed/failed
        job_id = file_status["job_id"]
        supabase.table("ingestion_jobs").update({
            "status": "processing",
            "message": f"Retrying failed file ({retry_count}/3)",
            "status_message": f"Retrying failed file ({retry_count}/3)"
        }).eq("id", job_id)\
         .in_("status", ["completed", "failed"])\
         .execute()
        
        # Queue the file for reprocessing
        # This depends on the job type - for now just log it
        # The background worker will pick up pending files
        logger.info(f"🔄 Queued retry for file {file_status_id} (attempt {retry_count})")
        
        return {
            "status": "queued",
            "file_status_id": file_status_id,
            "retry_count": retry_count,
            "message": f"File queued for retry (attempt {retry_count}/3)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry file {file_status_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry file")


@router.get("/jobs/{job_id}/files")
async def get_job_files(
    job_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Get all file statuses for a specific job.
    
    Returns detailed per-file progress information.
    """
    supabase = get_supabase()
    
    try:
        # Verify job ownership
        job_response = supabase.table("ingestion_jobs")\
            .select("id")\
            .eq("id", job_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not job_response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get file statuses
        response = supabase.table("ingestion_file_status")\
            .select("*")\
            .eq("job_id", job_id)\
            .order("created_at", desc=False)\
            .execute()
        
        return response.data or []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get files for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job files")


# ============================================================
# RETRY ENTIRE JOB ENDPOINT
# ============================================================

@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    user_id: str = Depends(require_editor)
):
    """
    Retry an entire failed ingestion job.
    
    - Validates job status and ownership
    - Resets all failed files to 'pending'
    - Resets job status to 'processing'
    - Re-dispatches for processing
    
    Returns:
        Job ID and number of files queued for retry
    """
    from datetime import datetime, timezone
    
    supabase = get_supabase()
    
    try:
        # Verify ownership and get job details
        response = supabase.table("ingestion_jobs")\
            .select("id, status")\
            .eq("id", job_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = response.data
        
        # Check if job can be retried (only failed or completed jobs)
        if job["status"] not in ["failed", "completed"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot retry job with status '{job['status']}'. Only failed or completed jobs can be retried."
            )
        
        # Count failed files
        failed_files_response = supabase.table("ingestion_file_status")\
            .select("id, retry_count")\
            .eq("job_id", job_id)\
            .eq("status", "failed")\
            .execute()
        
        failed_files = failed_files_response.data or []
        
        if not failed_files:
            raise HTTPException(
                status_code=400, 
                detail="No failed files to retry in this job"
            )
        
        # Filter out files that have exceeded max retries
        retryable_files = [f for f in failed_files if (f.get("retry_count", 0) or 0) < 3]
        
        if not retryable_files:
            raise HTTPException(
                status_code=400, 
                detail="All failed files have exceeded maximum retry attempts (3)"
            )
        
        # Reset all retryable failed files to 'pending'
        for file_info in retryable_files:
            retry_count = (file_info.get("retry_count", 0) or 0) + 1
            supabase.table("ingestion_file_status").update({
                "status": "pending",
                "progress": 0,
                "status_message": f"Retry attempt {retry_count}/3",
                "error_message": None,
                "retry_count": retry_count
            }).eq("id", file_info["id"]).execute()
        
        # Reset job status to processing
        supabase.table("ingestion_jobs").update({
            "status": "processing",
            "message": f"Retrying {len(retryable_files)} failed files",
            "status_message": f"Retrying {len(retryable_files)} failed files",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", job_id).execute()
        
        logger.info(f"🔄 Retry job {job_id}: queued {len(retryable_files)} files for reprocessing")
        
        return {
            "status": "queued",
            "job_id": job_id,
            "files_queued": len(retryable_files),
            "files_skipped": len(failed_files) - len(retryable_files),
            "message": f"{len(retryable_files)} files queued for retry"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry job")
