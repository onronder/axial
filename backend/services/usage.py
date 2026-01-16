"""
Usage Service

Provides centralized access to user usage data and quota information.
This is the single source of truth for what a user is allowed to do
vs. what they have consumed.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from core.db import get_supabase
from core.exceptions import QuotaExceededError
from core.quotas import PlanLimits, get_plan_limits, format_bytes
from services.team_service import team_service

logger = logging.getLogger(__name__)


class UserUsage(BaseModel):
    """
    Current usage statistics for a user (organization-scoped).
    
    Attributes:
        user_id: The user's UUID
        files: Number of documents/files in the org
        storage_bytes: Total storage used in bytes
        storage_display: Human-readable storage string
        plan: Current subscription plan name
    """
    user_id: str
    files: int
    storage_bytes: int
    storage_display: str
    plan: str
    subscription_status: str


class UsageWithLimits(BaseModel):
    """
    Usage data combined with plan limits for easy comparison.
    
    Attributes:
        usage: Current usage statistics
        limits: Plan limits for comparison
        files_remaining: How many more files can be uploaded
        storage_remaining_bytes: How many more bytes can be stored
        storage_remaining_display: Human-readable remaining storage
        at_file_limit: Whether user has reached file limit
        at_storage_limit: Whether user has reached storage limit
    """
    usage: UserUsage
    limits: PlanLimits
    files_remaining: int
    storage_remaining_bytes: int
    storage_remaining_display: str
    at_file_limit: bool
    at_storage_limit: bool


async def get_user_usage(user_id: UUID) -> UserUsage:
    """
    Get the current usage statistics for a user.
    
    Strategy: Query documents table directly with SUM/COUNT for accuracy.
    Usage is calculated at the organization scope to reflect shared quotas.
    This is safer than cached columns for MVP to avoid sync issues.
    Consider migrating to cached columns (user_profiles.file_count, 
    total_storage_bytes) if performance becomes an issue.
    
    Args:
        user_id: The user's UUID
        
    Returns:
        UserUsage with current file count, storage, and plan
    """
    supabase = get_supabase()
    
    # Default values
    plan = "free"
    subscription_status = "active"
    
    # Get user's plan from user_profiles (subscription_status comes from subscriptions table)
    # Wrap in try/except to handle race condition where profile doesn't exist yet (PGRST116)
    try:
        profile_result = supabase.table("user_profiles").select("plan").eq(
            "user_id", str(user_id)
        ).single().execute()
        
        if profile_result.data:
            plan = profile_result.data.get("plan", "free")
    except Exception as e:
        error_msg = str(e)
        # Check specifically for PGRST116 (0 rows) or empty result error
        if "PGRST116" in error_msg or "0 rows" in error_msg or "JSON object must be str" in error_msg:
            # "JSON object must be str" can happen if .single() returns None/empty response body depending on client version
            logger.warning(f"User profile not found for {user_id} (PGRST116 race condition): {e}")
            return UserUsage(
                user_id=str(user_id),
                files=0,
                storage_bytes=0,
                storage_display="0 B",
                plan="free",
                subscription_status="inactive"
            )
        
        # Re-raise other unexpected errors
        logger.error(f"Error fetching user profile for {user_id}: {e}")
        raise e
    
    organization_id = str(user_id)
    team_id = None

    # Resolve team_id for org-scoped usage (member -> owner fallback)
    try:
        team_result = supabase.table("team_members").select("team_id").eq(
            "member_user_id", str(user_id)
        ).limit(1).execute()
        team_data = team_result.data if isinstance(team_result.data, list) else []
        if team_data and isinstance(team_data[0], dict):
            team_id = team_data[0].get("team_id")
    except Exception as e:
        logger.warning(f"Could not fetch team membership for {user_id}: {e}")

    if not team_id:
        try:
            owner_team = supabase.table("teams").select("id").eq(
                "owner_id", str(user_id)
            ).limit(1).execute()
            owner_data = owner_team.data if isinstance(owner_team.data, list) else []
            if owner_data and isinstance(owner_data[0], dict):
                team_id = owner_data[0].get("id")
        except Exception as e:
            logger.warning(f"Could not resolve owner team for {user_id}: {e}")

    if team_id:
        organization_id = str(team_id)

        # Get subscription status from subscriptions table via team_id
        try:
            sub_result = supabase.table("subscriptions").select("status").eq(
                "team_id", organization_id
            ).limit(1).execute()

            sub_data = sub_result.data if isinstance(sub_result.data, list) else []
            if sub_data and isinstance(sub_data[0], dict):
                subscription_status = sub_data[0].get("status", "active")
        except Exception as e:
            # Non-critical - default to active if we can't fetch subscription
            logger.warning(f"Could not fetch subscription status for {user_id}: {e}")
    
    # Resolve effective plan from team/subscription (best source of truth)
    try:
        effective_plan = await team_service.get_effective_plan(str(user_id))
        if effective_plan:
            plan = effective_plan
    except Exception as e:
        logger.warning(f"Could not resolve effective plan for {user_id}: {e}")

    # Calculate usage from documents table (accurate, not cached)
    # Using raw SQL via RPC for aggregate functions
    usage_query = f"""
        SELECT 
            COALESCE(COUNT(*), 0) as file_count,
            COALESCE(SUM(file_size_bytes), 0) as total_bytes
        FROM documents
        WHERE user_id = '{str(user_id)}'
    """
    
    # Alternative: Use PostgREST count and iterate (less efficient but works)
    # For MVP, we'll query the documents directly
    docs_result = supabase.table("documents").select(
        "id, file_size_bytes"
    ).eq("organization_id", organization_id).execute()
    
    file_count = 0
    total_bytes = 0
    
    if docs_result.data:
        file_count = len(docs_result.data)
        total_bytes = sum(
            doc.get("file_size_bytes", 0) or 0 
            for doc in docs_result.data
        )
    
    logger.debug(
        f"User {user_id} usage: {file_count} files, {total_bytes} bytes, plan: {plan}"
    )
    
    return UserUsage(
        user_id=str(user_id),
        files=file_count,
        storage_bytes=total_bytes,
        storage_display=format_bytes(total_bytes),
        plan=plan,
        subscription_status=subscription_status
    )


async def get_user_usage_with_limits(user_id: UUID) -> UsageWithLimits:
    """
    Get usage statistics with plan limits for comparison.
    
    Useful for UI display and quota enforcement decisions.
    
    Args:
        user_id: The user's UUID
        
    Returns:
        UsageWithLimits with usage, limits, and derived quota info
    """
    usage = await get_user_usage(user_id)
    limits = get_plan_limits(usage.plan)
    
    files_remaining = max(0, limits.max_files - usage.files)
    storage_remaining = max(0, limits.max_storage_bytes - usage.storage_bytes)
    
    return UsageWithLimits(
        usage=usage,
        limits=limits,
        files_remaining=files_remaining,
        storage_remaining_bytes=storage_remaining,
        storage_remaining_display=format_bytes(storage_remaining),
        at_file_limit=usage.files >= limits.max_files,
        at_storage_limit=usage.storage_bytes >= limits.max_storage_bytes
    )


async def check_can_upload(
    user_id: UUID, 
    file_size_bytes: int, 
    file_count: int = 1
) -> dict:
    """
    Check if a user can upload a file based on their quota.
    
    Args:
        user_id: The user's UUID
        file_size_bytes: Size of the file to upload in bytes
        file_count: Number of files being uploaded (default 1)
        
    Returns:
        dict with:
            - allowed: bool indicating if upload is permitted
            - reason: str explaining why upload is denied (if applicable)
            - usage: current usage stats
            - limits: plan limits
    """
    usage_with_limits = await get_user_usage_with_limits(user_id)
    usage = usage_with_limits.usage
    limits = usage_with_limits.limits
    
    # Check file count limit
    if usage.files + file_count > limits.max_files:
        return {
            "allowed": False,
            "reason": f"File limit reached. You have {usage.files}/{limits.max_files} files. "
                     f"Upgrade your plan to upload more.",
            "usage": usage.model_dump(),
            "limits": limits.model_dump()
        }
    
    # Check storage limit
    if usage.storage_bytes + file_size_bytes > limits.max_storage_bytes:
        return {
            "allowed": False,
            "reason": f"Storage limit reached. You're using {usage.storage_display} of "
                     f"{format_bytes(limits.max_storage_bytes)}. Upgrade your plan for more storage.",
            "usage": usage.model_dump(),
            "limits": limits.model_dump()
        }

    return {
        "allowed": True,
        "reason": None,
        "usage": usage.model_dump(),
        "limits": limits.model_dump(),
    }


async def _get_org_llm_usage(supabase, org_id: str) -> int:
    try:
        res = (
            supabase.table("org_usage")
            .select("llm_tokens_used")
            .eq("org_id", org_id)
            .limit(1)
            .execute()
        )
        row = (res.data or [{}])[0]
        return int(row.get("llm_tokens_used") or 0)
    except Exception as exc:
        logger.error("❌ [Usage] Failed to fetch LLM usage for %s: %s", org_id, exc)
        raise


async def _get_org_llm_balance_override(supabase, org_id: str) -> Optional[int]:
    try:
        res = (
            supabase.table("teams")
            .select("llm_token_balance")
            .eq("id", org_id)
            .limit(1)
            .execute()
        )
        row = (res.data or [{}])[0]
        balance = row.get("llm_token_balance")
        if balance is None:
            return None
        return int(balance)
    except Exception as exc:
        logger.error("❌ [Usage] Failed to fetch LLM balance for %s: %s", org_id, exc)
        raise


async def get_org_llm_balance(org_id: str, plan_code: Optional[str]) -> dict:
    """
    Return remaining LLM tokens for an org.

    If teams.llm_token_balance is set, treat it as the remaining balance.
    Otherwise compute from plan limit - org_usage.llm_tokens_used.
    """
    supabase = get_supabase()
    balance_override = await _get_org_llm_balance_override(supabase, org_id)
    tokens_used = await _get_org_llm_usage(supabase, org_id)
    limits = get_plan_limits(plan_code or "free")
    plan_limit = int(limits.max_llm_tokens or 0)

    if balance_override is not None:
        remaining = max(0, balance_override)
        return {
            "org_id": org_id,
            "balance": remaining,
            "tokens_used": tokens_used,
            "limit": None,
            "source": "balance_override",
        }

    remaining = max(0, plan_limit - tokens_used)
    return {
        "org_id": org_id,
        "balance": remaining,
        "tokens_used": tokens_used,
        "limit": plan_limit,
        "source": "plan_limit",
    }


async def check_llm_quota(
    org_id: str,
    plan_code: Optional[str],
    required_tokens: Optional[int] = None,
) -> dict:
    """
    Ensure the org has remaining LLM token balance before calling any model.
    """
    usage = await get_org_llm_balance(org_id, plan_code)
    balance = int(usage.get("balance") or 0)
    required = max(0, int(required_tokens or 0))

    if balance <= 0 or (required and balance < required):
        raise QuotaExceededError(
            "LLM token quota exceeded.",
            {
                "balance": balance,
                "required": required,
                "limit": usage.get("limit"),
                "used": usage.get("tokens_used"),
                "plan": plan_code,
                "organization_id": org_id,
            },
        )
    return usage


async def record_llm_usage(
    org_id: str,
    tokens_used: int,
    plan_code: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    """
    Increment LLM token usage for the org and decrement balance overrides.
    """
    if tokens_used <= 0:
        return
    supabase = get_supabase()
    tokens_used = int(tokens_used)

    current_used = await _get_org_llm_usage(supabase, org_id)
    next_used = current_used + tokens_used

    try:
        supabase.table("org_usage").upsert(
            {
                "org_id": org_id,
                "llm_tokens_used": next_used,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="org_id",
        ).execute()
        logger.info(
            "✅ [Usage] LLM usage org=%s tokens+=%s provider=%s model=%s",
            org_id,
            tokens_used,
            provider or "unknown",
            model or "unknown",
        )
    except Exception as exc:
        logger.error("❌ [Usage] Failed to update LLM usage for %s: %s", org_id, exc)
        raise

    try:
        balance_override = await _get_org_llm_balance_override(supabase, org_id)
        if balance_override is not None:
            next_balance = max(0, int(balance_override) - tokens_used)
            supabase.table("teams").update(
                {"llm_token_balance": next_balance}
            ).eq("id", org_id).execute()
    except Exception as exc:
        logger.error("❌ [Usage] Failed to decrement LLM balance for %s: %s", org_id, exc)
        raise


async def check_feature_access(user_id: UUID, feature: str) -> dict:
    """
    Check if a user has access to a specific feature.
    
    Args:
        user_id: The user's UUID
        feature: Feature name to check (e.g., 'web_crawl')
        
    Returns:
        dict with:
            - allowed: bool indicating if feature is accessible
            - reason: str explaining why access is denied (if applicable)
            - plan: current plan name
    """
    usage = await get_user_usage(user_id)
    limits = get_plan_limits(usage.plan)
    
    feature_checks = {
        "web_crawl": {
            "allowed": limits.allow_web_crawl,
            "reason": "Web crawling is available on Pro and Enterprise plans."
        },
        "team_seats": {
            "allowed": limits.max_team_seats > 1,
            "reason": "Team collaboration is available on Enterprise plans."
        },
        "premium_models": {
            "allowed": limits.model_tier in ["hybrid", "premium"],
            "reason": "Premium AI models are available on Pro and Enterprise plans."
        }
    }
    
    if feature not in feature_checks:
        logger.warning(f"Unknown feature check requested: {feature}")
        return {
            "allowed": True,  # Default to allowed for unknown features
            "reason": None,
            "plan": usage.plan
        }
    
    check = feature_checks[feature]
    return {
        "allowed": check["allowed"],
        "reason": None if check["allowed"] else check["reason"],
        "plan": usage.plan
    }
