"""
Jobs API Router

Endpoints for tracking background job progress.
Used for polling-based progress updates during ingestion.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from core.security import get_current_user
from core.db import get_supabase
from models import IngestionJobResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


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
            provider=job["provider"],
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
        response = supabase.table("ingestion_jobs")\
            .select("*")\
            .eq("id", job_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = response.data
        
        # Calculate progress percentage
        total = job.get("total_files", 0)
        processed = job.get("processed_files", 0)
        percent = (processed / total * 100) if total > 0 else 0
        
        return IngestionJobResponse(
            id=job["id"],
            provider=job["provider"],
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
