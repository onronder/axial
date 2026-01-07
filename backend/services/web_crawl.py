"""
Web crawl queueing helpers.

Shared between legacy /ingest and new /integrations/web/crawl endpoints.
"""

from datetime import datetime, timezone
from typing import Dict

from core.db import get_supabase
from worker.tasks import crawl_discovery_task


def queue_web_crawl(
    *,
    user_id: str,
    root_url: str,
    crawl_type: str,
    max_depth: int,
    respect_robots: bool,
    max_pages: int,
    allow_subdomains: bool,
    is_recrawl: bool = False
) -> Dict[str, str]:
    """Create a crawl config record and dispatch crawl discovery."""
    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

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
            },
        )
    except Exception as exc:
        supabase.table("web_crawl_configs").update({
            "status": "failed",
            "error_message": str(exc),
            "updated_at": now,
        }).eq("id", crawl_id).execute()
        raise

    supabase.table("web_crawl_configs").update({
        "celery_task_id": task.id
    }).eq("id", crawl_id).execute()

    return {"crawl_id": crawl_id, "task_id": task.id}
