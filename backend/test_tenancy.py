import pytest
import uuid
import asyncio
from core.db import get_supabase
from api.v1.settings import get_profile

# Note: These tests require a running Supabase instance with the Trigger migration applied.

@pytest.mark.asyncio
async def test_orphan_user_recovery():
    """
    TASK 1 Verification:
    Simulate a user creation in auth.users and assert that public.user_profiles 
    is automatically created with plan='free' via Database Trigger.
    """
    supabase = get_supabase()
    
    # Generate random test user
    test_email = f"test_orphan_{uuid.uuid4()}@example.com"
    test_password = "password123"
    
    # 1. Create User in Auth (Simulates Sign Up)
    # Using admin api to create user without signing in, if possible, 
    # or just sign up. Admin is better to avoid rate limits/confirmations.
    # Note: supabase-py admin.create_user creates in auth.users
    
    try:
        user_response = supabase.auth.admin.create_user({
            "email": test_email,
            "password": test_password,
            "email_confirm": True
        })
        user_id = user_response.user.id
        
        # 2. Verify Profile Auto-Creation
        # The Trigger 'on_auth_user_created' should have fired immediately.
        
        # Allow slight delay for trigger propagation if async (usually sync in Postgres)
        await asyncio.sleep(0.5)
        
        profile_response = supabase.table("user_profiles")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
            
        assert len(profile_response.data) > 0, "Profile was not automatically created by Trigger"
        profile = profile_response.data[0]
        
        assert profile["email"] == test_email
        assert profile["plan"] == "free", "Default plan should be 'free'"
        assert profile["role"] == "member", "Default role should be 'member'"
        
    finally:
        # Cleanup
        if 'user_id' in locals():
            supabase.auth.admin.delete_user(user_id)
            # Profile cascade delete should occur if foreign key set, 
            # otherwise we might leave payload. Logic depends on schema FK.

@pytest.mark.asyncio
async def test_invite_skip_onboarding():
    """
    TASK 3 Verification:
    Create a user, add them to a team, and verify that the backend 
    returns has_team=True in the profile endpoint.
    """
    supabase = get_supabase()
    
    # 1. Setup: Create User
    test_email = f"test_invite_{uuid.uuid4()}@example.com"
    user_response = supabase.auth.admin.create_user({
        "email": test_email,
        "password": "password123",
        "email_confirm": True
    })
    user_id = user_response.user.id
    
    try:
        # 2. Setup: Create Team and Add Member
        # Create a dummy team (assuming team table exists and RLS allows or we use service role)
        team_name = f"Team {uuid.uuid4()}"
        
        # Note: We need a team first. If we can't create one due to RLS, 
        # this test implies we are testing the query logic, not the tea creation logic.
        # We'll try to insert directly using service_role client if get_supabase returns one.
        # Assuming get_supabase returns service key client or we mock it. 
        # For this logic test, we'll try to insert a team.
        
        team_res = supabase.table("teams").insert({"name": team_name}).execute()
        team_id = team_res.data[0]["id"]
        
        # Add user to team_members
        supabase.table("team_members").insert({
            "team_id": team_id,
            "user_id": user_id,
            "role": "member"
        }).execute()
        
        # 3. Call the modified get_profile Logic
        # We can call the FastAPI function directly or mock the request.
        # Calling logic directly is easier for unit/integration testing.
        
        # We need to mock the dependency 'get_current_user' effectively by passing user_id explicitly 
        # if we refactored get_profile to take it, but it takes it as dependency.
        # Current signature: async def get_profile(user_id: str = Depends(get_current_user))
        # We can just call it passing the user_id string if FastAPI validation isn't strict at calling time in python.
        
        profile_data = await get_profile(user_id=user_id)
        
        # 4. Assert has_team is True
        assert profile_data.has_team is True, "User in a team should have has_team=True"
        
        # 5. Verify Negative Case
        # Create another user without team
        orphan_email = f"orphan_{uuid.uuid4()}@example.com"
        orphan_user = supabase.auth.admin.create_user({
            "email": orphan_email, "password": "pw", "email_confirm": True
        })
        orphan_data = await get_profile(user_id=orphan_user.user.id)
        assert orphan_data.has_team is False, "User without team should have has_team=False"
        
        # Cleanup negative case
        supabase.auth.admin.delete_user(orphan_user.user.id)
        
    finally:
        # Cleanup primary user
        if 'team_id' in locals():
            supabase.table("teams").delete().eq("id", team_id).execute()
        supabase.auth.admin.delete_user(user_id)
