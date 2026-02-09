import asyncio
import os
import uuid
from collections.abc import Awaitable, Callable

from api.v1.settings import get_profile
from core.db import get_supabase


async def verify_orphan_user_recovery(
    supabase,
    *,
    sleep_func: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> dict:
    """
    Verify auth trigger creates a user profile on account creation.
    Returns the created user_id and profile record.
    """
    test_email = f"test_orphan_{uuid.uuid4()}@example.com"
    test_password = "password123"
    user_id: str | None = None

    try:
        user_response = supabase.auth.admin.create_user({
            "email": test_email,
            "password": test_password,
            "email_confirm": True,
        })
        user_id = user_response.user.id

        await sleep_func(0.5)

        profile_response = supabase.table("user_profiles").select("*").eq(
            "user_id", user_id
        ).execute()

        profile = profile_response.data[0]

        assert profile["email"] == test_email
        assert profile["plan"] == "free"
        assert profile["role"] == "member"

        return {"user_id": user_id, "profile": profile}
    finally:
        if user_id:
            supabase.auth.admin.delete_user(user_id)


async def verify_invite_skip_onboarding(
    supabase,
    *,
    get_profile_func: Callable[..., Awaitable],
) -> dict:
    """
    Verify a user in a team returns has_team=True in profile endpoint.
    Returns user/team identifiers for inspection.
    """
    test_email = f"test_invite_{uuid.uuid4()}@example.com"
    user_response = supabase.auth.admin.create_user({
        "email": test_email,
        "password": "password123",
        "email_confirm": True,
    })
    user_id = user_response.user.id
    team_id: str | None = None

    try:
        team_name = f"Team {uuid.uuid4()}"
        team_res = supabase.table("teams").insert({"name": team_name}).execute()
        team_id = team_res.data[0]["id"]

        supabase.table("team_members").insert({
            "team_id": team_id,
            "user_id": user_id,
            "role": "member",
        }).execute()

        profile_data = await get_profile_func(user_id=user_id)
        assert profile_data.has_team is True

        orphan_email = f"orphan_{uuid.uuid4()}@example.com"
        orphan_user = supabase.auth.admin.create_user({
            "email": orphan_email,
            "password": "pw",
            "email_confirm": True,
        })
        orphan_data = await get_profile_func(user_id=orphan_user.user.id)
        assert orphan_data.has_team is False

        supabase.auth.admin.delete_user(orphan_user.user.id)

        return {"user_id": user_id, "team_id": team_id}
    finally:
        if team_id:
            supabase.table("teams").delete().eq("id", team_id).execute()
        supabase.auth.admin.delete_user(user_id)


def run_manual_checks():
    """Run manual tenancy checks against live Supabase."""
    if os.getenv("RUN_MANUAL_TENANCY_CHECKS") != "1":
        return {"status": "skipped"}
    supabase = get_supabase()
    asyncio.run(verify_orphan_user_recovery(supabase))
    asyncio.run(verify_invite_skip_onboarding(supabase, get_profile_func=get_profile))
    return {"status": "completed"}


if __name__ == "__main__":
    run_manual_checks()
