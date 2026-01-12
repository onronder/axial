"""
Quota Admission Control (High-Perception: generous concurrency, TPM capped)

Provides per-tenant admission checks for ingestion:
- Concurrency guard (active jobs per org)
- Storage/daily job guards using org_usage

TPM throttling is enforced in the embedding layer; this module focuses on
deciding whether a new job should be accepted.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from core.config import QUOTA_LIMITS, settings
from core.db import get_supabase
from core.exceptions import QuotaExceededError

logger = logging.getLogger(__name__)


def _resolve_plan_limits(plan_code: Optional[str]) -> Dict[str, Any]:
    plan_key = (plan_code or settings.PLAN_STARTER).lower()
    if plan_key == "enterprise":
        plan_key = "enterprise_medium"
    if plan_key == "free":
        plan_key = settings.PLAN_STARTER
    limits = QUOTA_LIMITS.get(plan_key)
    if not limits:
        logger.warning("⚠️ [Quotas] Unknown plan '%s', defaulting to starter", plan_code)
        limits = QUOTA_LIMITS[settings.PLAN_STARTER]
    return limits


def _fetch_org_usage(supabase, org_id: str) -> Dict[str, Any]:
    try:
        res = (
            supabase.table("org_usage")
            .select("storage_used_mb, job_count_cycle")
            .eq("org_id", org_id)
            .limit(1)
            .execute()
        )
        row = (res.data or [{}])[0]
        return {
            "storage_used_mb": float(row.get("storage_used_mb") or 0),
            "job_count_cycle": int(row.get("job_count_cycle") or 0),
        }
    except Exception as exc:
        logger.warning("⚠️ [Quotas] Failed to fetch org_usage for %s: %s", org_id, exc)
        return {"storage_used_mb": 0.0, "job_count_cycle": 0}


def _get_org_user_ids(supabase, org_id: str) -> List[str]:
    user_ids: List[str] = []
    try:
        owner_res = supabase.table("teams").select("owner_id").eq("id", org_id).limit(1).execute()
        if owner_res.data:
            owner_id = owner_res.data[0].get("owner_id")
            if owner_id:
                user_ids.append(owner_id)
    except Exception as exc:
        logger.warning("⚠️ [Quotas] Failed to fetch team owner for %s: %s", org_id, exc)

    try:
        members_res = supabase.table("team_members").select("member_user_id").eq("team_id", org_id).execute()
        for row in members_res.data or []:
            member_id = row.get("member_user_id")
            if member_id:
                user_ids.append(member_id)
    except Exception as exc:
        logger.warning("⚠️ [Quotas] Failed to fetch team members for %s: %s", org_id, exc)

    # Deduplicate and include org_id as a fallback for solo tenants
    if org_id:
        user_ids.append(org_id)
    return list({uid for uid in user_ids if uid})


def _count_active_jobs(supabase, user_ids: List[str]) -> int:
    if not user_ids:
        return 0
    try:
        res = (
            supabase.table("ingestion_jobs")
            .select("id", count="exact")
            .in_("user_id", user_ids)
            .in_("status", ["pending", "processing"])
            .execute()
        )
        return int(res.count or 0)
    except Exception as exc:
        logger.warning("⚠️ [Quotas] Failed to count active jobs: %s", exc)
        return 0


def _to_mb(file_size_bytes: Optional[int]) -> float:
    if not file_size_bytes or file_size_bytes <= 0:
        return 0.0
    return file_size_bytes / (1024 * 1024)


def check_admission(
    org_id: str,
    plan_code: Optional[str],
    file_size_bytes: Optional[int] = None,
    job_count_increment: int = 1,
) -> Dict[str, Any]:
    """
    Admission control for ingestion requests.

    Returns metadata when allowed; raises QuotaExceededError when blocked.
    Fails open on Supabase errors to avoid false negatives but logs loudly.
    """
    supabase = get_supabase()
    limits = _resolve_plan_limits(plan_code)
    usage = _fetch_org_usage(supabase, org_id)
    user_ids = _get_org_user_ids(supabase, org_id)
    active_jobs = _count_active_jobs(supabase, user_ids)
    requested_storage_mb = _to_mb(file_size_bytes)
    requested_jobs = max(1, job_count_increment)
    next_storage_mb = usage["storage_used_mb"] + requested_storage_mb
    next_jobs = usage["job_count_cycle"] + requested_jobs

    # Concurrency guard
    if active_jobs >= limits["concurrent"]:
        logger.warning(
            "🚫 Admission denied for Org %s: active_jobs=%s limit=%s plan=%s",
            org_id,
            active_jobs,
            limits["concurrent"],
            plan_code,
        )
        raise QuotaExceededError(
            f"Active job limit reached for plan '{plan_code or settings.PLAN_STARTER}'",
            {
                "active_jobs": active_jobs,
                "limit": limits["concurrent"],
                "plan": plan_code,
                "org_id": org_id,
            },
        )

    # Storage guard
    if next_storage_mb >= limits["storage_mb"]:
        logger.warning(
            "🚫 Admission denied for Org %s: storage_mb=%.2f next=%.2f limit=%.2f plan=%s",
            org_id,
            usage["storage_used_mb"],
            next_storage_mb,
            limits["storage_mb"],
            plan_code,
        )
        raise QuotaExceededError(
            "Storage quota exceeded",
            {
                "usage_mb": usage["storage_used_mb"],
                "next_usage_mb": next_storage_mb,
                "limit_mb": limits["storage_mb"],
                "plan": plan_code,
                "org_id": org_id,
            },
        )

    # Daily job guard
    if next_jobs > limits["daily_jobs"]:
        logger.warning(
            "🚫 Admission denied for Org %s: jobs=%s next=%s limit=%s plan=%s",
            org_id,
            usage["job_count_cycle"],
            next_jobs,
            limits["daily_jobs"],
            plan_code,
        )
        raise QuotaExceededError(
            "Daily job quota exceeded",
            {
                "jobs": usage["job_count_cycle"],
                "next_jobs": next_jobs,
                "limit": limits["daily_jobs"],
                "plan": plan_code,
                "org_id": org_id,
            },
        )

    return {
        "allowed": True,
        "limits": limits,
        "usage": usage,
        "active_jobs": active_jobs,
    }


def get_plan_max_tpm(plan_code: Optional[str]) -> Optional[int]:
    limits = _resolve_plan_limits(plan_code)
    return limits.get("max_tpm")


def increment_usage(
    org_id: str,
    storage_bytes: Optional[int] = None,
    job_count_increment: int = 1,
) -> None:
    """Increment org usage counters after admission is granted."""
    supabase = get_supabase()
    storage_mb_inc = _to_mb(storage_bytes)
    job_inc = max(1, job_count_increment)

    try:
        current = _fetch_org_usage(supabase, org_id)
        next_storage = current["storage_used_mb"] + storage_mb_inc
        next_jobs = current["job_count_cycle"] + job_inc

        supabase.table("org_usage").upsert(
            {
                "org_id": org_id,
                "storage_used_mb": next_storage,
                "job_count_cycle": next_jobs,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="org_id",
        ).execute()
        logger.info(
            "✅ [Quotas] Incremented usage org=%s storage+=%.2fMB jobs+=%s",
            org_id,
            storage_mb_inc,
            job_inc,
        )
    except Exception as exc:
        logger.warning("⚠️ [Quotas] Failed to increment usage for %s: %s", org_id, exc)
