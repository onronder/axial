"""
Web crawl queueing helpers.

Shared across web crawl endpoints.
"""

from datetime import datetime, timezone
from typing import Dict, Optional

import logging

from core.db import get_supabase
from core.url_utils import is_youtube_url  # Shared utility
from worker.tasks import crawl_discovery_task

logger = logging.getLogger(__name__)

def queue_web_crawl(
    *,
    user_id: str,
    organization_id: Optional[str] = None,
    root_url: str,
    crawl_type: str,
    max_depth: int,
    respect_robots: bool,
    max_pages: int,
    allow_subdomains: bool,
    is_recrawl: bool = False,
    include_job_id: bool = False
) -> Dict[str, str]:
    """Create a crawl config record and dispatch crawl discovery."""
    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    org_id = organization_id or user_id

    # Detect YouTube vs regular web crawl for proper labeling
    is_youtube = is_youtube_url(root_url)
    provider = "youtube" if is_youtube else "web"

    crawl_config_data = {
        "user_id": user_id,
        "root_url": root_url,
        "crawl_type": crawl_type,
        "max_depth": max_depth,
        "max_pages": max_pages,
        "allow_subdomains": allow_subdomains,
        "respect_robots_txt": respect_robots,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }

    crawl_res = supabase.table("web_crawl_configs").insert(crawl_config_data).execute()
    if not crawl_res.data:
        raise RuntimeError("Failed to create crawl config")

    crawl_id = str(crawl_res.data[0]["id"])
    ingestion_job_id = crawl_id

    # Create ingestion job so progress tray can track crawl
    job_record = {
            "id": ingestion_job_id,
            "user_id": user_id,
            "organization_id": org_id,
            "provider": provider,  # Dynamic: "youtube" or "web"
            "status": "pending",
            "total_files": 0,
            "processed_files": 0,
            "failed_files": 0,
            "progress": 0,
            "message": f"Queued {'YouTube video' if is_youtube else 'crawl'} for {root_url}",
            "status_message": f"Queued {'YouTube video' if is_youtube else 'crawl'} for {root_url}",
        }
    try:
        supabase.table("ingestion_jobs").upsert(job_record, on_conflict="id").execute()
    except Exception as job_exc:
        try:
            supabase.table("ingestion_jobs").insert(job_record).execute()
        except Exception as inner_exc:
            logger.warning("⚠️ [Crawl] Failed to create ingestion job: %s", inner_exc)
            ingestion_job_id = None

    try:
        task = crawl_discovery_task.delay(
            user_id=user_id,
            root_url=root_url,
            crawl_config={
                "crawl_id": crawl_id,
                "crawl_type": crawl_type,
                "max_depth": max_depth,
                "max_pages": max_pages,
                "respect_robots": respect_robots,
                "allow_subdomains": allow_subdomains,
                "is_recrawl": is_recrawl,
                "job_id": ingestion_job_id,
            },
        )
    except Exception as exc:
        logger.error("❌ [Crawl] Celery dispatch failed for %s: %s", crawl_id, exc)
        supabase.table("web_crawl_configs").update(
            {
                "status": "failed",
                "error_message": f"dispatch_failed: {exc}",
                "updated_at": now,
            }
        ).eq("id", crawl_id).execute()
        raise RuntimeError(f"Failed to dispatch crawl: {exc}") from exc

    supabase.table("web_crawl_configs").update(
        {"celery_task_id": task.id, "updated_at": now}
    ).eq("id", crawl_id).execute()

    if ingestion_job_id:
        try:
            supabase.table("ingestion_jobs").update({
                "celery_task_id": task.id
            }).eq("id", ingestion_job_id).execute()
        except Exception:
            pass

    response = {"crawl_id": crawl_id, "task_id": task.id}
    if include_job_id and ingestion_job_id:
        response["job_id"] = ingestion_job_id
    return response
