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
    # SECURITY FIX: Removed raw SQL query with string interpolation (SQL injection risk)
    # Using Supabase ORM which handles parameterization safely
    docs_result = (
        supabase.table("documents")
        .select("id, file_size_bytes")
        .eq("organization_id", organization_id)
        .neq("source_type", "identity")
        .neq("source_type", "scope_identity")
        .execute()
    )
    
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


async def reserve_llm_tokens(
    org_id: str,
    plan_code: Optional[str],
    tokens_to_reserve: int,
) -> dict:
    """
    RACE CONDITION FIX (Issue #3): Atomically reserve tokens BEFORE making LLM call.

    This prevents the time-of-check to time-of-use (TOCTOU) race condition where
    concurrent requests could both pass the quota check and then exceed the quota.

    The reservation pattern:
    1. reserve_llm_tokens(org_id, plan_code, estimated_tokens) - atomic decrement
    2. Make LLM call
    3. release_reserved_tokens(org_id, reserved - actual_used) - return unused

    Returns:
        dict with reservation_id, reserved_tokens, remaining_balance
    """
    supabase = get_supabase()
    tokens_to_reserve = max(0, int(tokens_to_reserve))

    if tokens_to_reserve <= 0:
        return {"reservation_id": None, "reserved_tokens": 0, "remaining_balance": 0}

    try:
        # Atomic reservation via database RPC
        result = supabase.rpc(
            "reserve_llm_tokens",
            {
                "p_org_id": org_id,
                "p_tokens": tokens_to_reserve,
                "p_plan_code": plan_code,
            }
        ).execute()

        if result.data:
            row = result.data[0] if isinstance(result.data, list) else result.data
            if isinstance(row, dict):
                if row.get("success") is False:
                    # Reservation failed due to insufficient balance
                    raise QuotaExceededError(
                        "LLM token quota exceeded during reservation.",
                        {
                            "balance": row.get("remaining_balance", 0),
                            "required": tokens_to_reserve,
                            "plan": plan_code,
                            "organization_id": org_id,
                        },
                    )
                return {
                    "reservation_id": row.get("reservation_id"),
                    "reserved_tokens": row.get("reserved_tokens", tokens_to_reserve),
                    "remaining_balance": row.get("remaining_balance", 0),
                }

        # Fallback if RPC doesn't exist
        logger.warning("⚠️ [Usage] reserve_llm_tokens RPC not found, using check-only fallback")
        return await _reserve_tokens_fallback(org_id, plan_code, tokens_to_reserve)

    except QuotaExceededError:
        raise
    except Exception as exc:
        error_msg = str(exc)
        if "function" in error_msg.lower() and "does not exist" in error_msg.lower():
            logger.warning("⚠️ [Usage] reserve_llm_tokens RPC not found, using fallback")
            return await _reserve_tokens_fallback(org_id, plan_code, tokens_to_reserve)
        logger.error("❌ [Usage] Failed to reserve tokens for %s: %s", org_id, exc)
        raise


async def release_reserved_tokens(
    org_id: str,
    unused_tokens: int,
) -> None:
    """
    Release unused reserved tokens back to the org's balance.

    Call this after LLM request completes if actual usage was less than reserved.
    """
    if unused_tokens <= 0:
        return

    supabase = get_supabase()
    unused_tokens = int(unused_tokens)

    try:
        result = supabase.rpc(
            "release_llm_tokens",
            {
                "p_org_id": org_id,
                "p_tokens": unused_tokens,
            }
        ).execute()

        logger.debug("✅ [Usage] Released %s unused tokens for org %s", unused_tokens, org_id)

    except Exception as exc:
        error_msg = str(exc)
        if "function" in error_msg.lower() and "does not exist" in error_msg.lower():
            # RPC doesn't exist, tokens were never reserved atomically
            logger.debug("⚠️ [Usage] release_llm_tokens RPC not found (expected during migration)")
        else:
            logger.warning("⚠️ [Usage] Failed to release tokens for %s: %s", org_id, exc)


async def _reserve_tokens_fallback(
    org_id: str,
    plan_code: Optional[str],
    tokens_to_reserve: int,
) -> dict:
    """
    Fallback reservation when atomic RPC doesn't exist.

    NOTE: This has the original race condition - only use during migration.
    """
    usage = await check_llm_quota(org_id, plan_code, required_tokens=tokens_to_reserve)
    return {
        "reservation_id": None,
        "reserved_tokens": tokens_to_reserve,
        "remaining_balance": usage.get("balance", 0) - tokens_to_reserve,
    }


def check_per_request_token_limit(
    estimated_tokens: int,
    max_tokens_per_request: Optional[int] = None,
) -> None:
    """
    Enforce per-request token limit to prevent single requests from consuming
    entire monthly budget (Issue #9).

    Args:
        estimated_tokens: Estimated input tokens for the request
        max_tokens_per_request: Maximum allowed (defaults to settings.LLM_MAX_TOKENS_PER_REQUEST)

    Raises:
        QuotaExceededError: If estimated tokens exceed per-request limit
    """
    from core.config import settings

    if max_tokens_per_request is None:
        max_tokens_per_request = getattr(settings, 'LLM_MAX_TOKENS_PER_REQUEST', 50000)

    if estimated_tokens > max_tokens_per_request:
        raise QuotaExceededError(
            f"Request exceeds per-request token limit ({estimated_tokens:,} > {max_tokens_per_request:,}).",
            {
                "estimated_tokens": estimated_tokens,
                "max_per_request": max_tokens_per_request,
                "suggestion": "Please reduce context size or split into multiple requests.",
            },
        )


async def record_llm_usage(
    org_id: str,
    tokens_used: int,
    plan_code: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    """
    Atomically increment LLM token usage for the org and decrement balance overrides.
    
    RACE CONDITION FIX: Uses database RPC for atomic increment instead of
    read-modify-write pattern which could cause token drift under concurrent requests.
    """
    if tokens_used <= 0:
        return
    supabase = get_supabase()
    tokens_used = int(tokens_used)

    try:
        # ATOMIC INCREMENT: Uses database function to prevent race conditions
        # This replaces the previous read-modify-write pattern
        result = supabase.rpc(
            "increment_llm_tokens",
            {
                "p_org_id": org_id,
                "p_tokens": tokens_used,
                "p_provider": provider,
                "p_model": model,
            }
        ).execute()
        
        # Extract new total from result
        new_total = None
        previous_total = None
        if result.data:
            # RPC returns a table, get first row
            row = result.data[0] if isinstance(result.data, list) else result.data
            new_total = row.get("new_total") if isinstance(row, dict) else None
            previous_total = row.get("previous_total") if isinstance(row, dict) else None
        
        logger.info(
            "✅ [Usage] LLM usage org=%s tokens+=%s total=%s->%s provider=%s model=%s",
            org_id,
            tokens_used,
            previous_total,
            new_total,
            provider or "unknown",
            model or "unknown",
        )
    except Exception as exc:
        # Fallback to upsert if RPC doesn't exist (migration not applied yet)
        error_msg = str(exc)
        if "function" in error_msg.lower() and "does not exist" in error_msg.lower():
            logger.warning("⚠️ [Usage] increment_llm_tokens RPC not found, using fallback")
            await _record_llm_usage_fallback(supabase, org_id, tokens_used, provider, model)
        else:
            logger.error("❌ [Usage] Failed to update LLM usage for %s: %s", org_id, exc)
            raise

    # Decrement balance override if set (also atomic)
    try:
        # Try atomic decrement first
        result = supabase.rpc(
            "decrement_llm_balance",
            {
                "p_org_id": org_id,
                "p_tokens": tokens_used,
            }
        ).execute()
        
        # Result is NULL if no balance override exists, which is fine
        if result.data is not None:
            logger.debug("✅ [Usage] Decremented LLM balance for %s by %s", org_id, tokens_used)
            
    except Exception as exc:
        error_msg = str(exc)
        if "function" in error_msg.lower() and "does not exist" in error_msg.lower():
            # Fallback if RPC doesn't exist
            await _decrement_llm_balance_fallback(supabase, org_id, tokens_used)
        else:
            logger.error("❌ [Usage] Failed to decrement LLM balance for %s: %s", org_id, exc)
            raise


async def _record_llm_usage_fallback(
    supabase,
    org_id: str,
    tokens_used: int,
    provider: Optional[str],
    model: Optional[str],
) -> None:
    """
    Fallback for record_llm_usage when atomic RPC is not available.
    
    NOTE: This has a race condition - use only as fallback during migration.
    """
    current_used = await _get_org_llm_usage(supabase, org_id)
    next_used = current_used + tokens_used

    supabase.table("org_usage").upsert(
        {
            "org_id": org_id,
            "llm_tokens_used": next_used,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="org_id",
    ).execute()
    
    logger.warning(
        "⚠️ [Usage] LLM usage (FALLBACK) org=%s tokens+=%s provider=%s model=%s",
        org_id,
        tokens_used,
        provider or "unknown",
        model or "unknown",
    )


async def _decrement_llm_balance_fallback(
    supabase,
    org_id: str,
    tokens_used: int,
) -> None:
    """
    Fallback for balance decrement when atomic RPC is not available.
    
    NOTE: This has a race condition - use only as fallback during migration.
    """
    balance_override = await _get_org_llm_balance_override(supabase, org_id)
    if balance_override is not None:
        next_balance = max(0, int(balance_override) - tokens_used)
        supabase.table("teams").update(
            {"llm_token_balance": next_balance}
        ).eq("id", org_id).execute()
        logger.warning("⚠️ [Usage] Decremented LLM balance (FALLBACK) for %s", org_id)


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
