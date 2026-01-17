-- =============================================================================
-- Migration: Fix is_org_member for Solo Users (ISSUE-002)
-- =============================================================================
-- 
-- PROBLEM:
-- When users don't have a team, the system falls back to using user_id as
-- organization_id. However, is_org_member(user_id, user_id) returns FALSE
-- because no teams row exists with id = user_id.
--
-- This breaks RLS for:
-- - documents (can't read own documents)
-- - scope_identities (can't read own scopes)  
-- - conversations (can't read own conversations)
-- - ingestion_jobs (can't read own jobs)
--
-- SOLUTION:
-- Modify is_org_member to handle the "self-ownership" case where org_id = user_id.
-- This is the canonical pattern for solo users who haven't been assigned a team.
--
-- SAFETY:
-- This change is additive - it only allows access that was previously blocked
-- for legitimate solo users. It does NOT grant access to other users' data.
-- =============================================================================

BEGIN;

-- ==========================================================================
-- Step 1: Replace is_org_member with solo-user-aware version
-- ==========================================================================

CREATE OR REPLACE FUNCTION public.is_org_member(
    org_id UUID,
    user_uuid UUID
) RETURNS BOOLEAN AS $$
BEGIN
    -- ==========================================================================
    -- SOLO USER CHECK (NEW)
    -- ==========================================================================
    -- When org_id = user_uuid, the user is accessing their own data
    -- that was stored with organization_id = user_id (the solo user fallback).
    -- This is a valid access pattern for users who:
    -- 1. Haven't been assigned a team yet, OR
    -- 2. Had their data backfilled with organization_id = user_id
    -- ==========================================================================
    IF org_id = user_uuid THEN
        RETURN TRUE;
    END IF;
    
    -- ==========================================================================
    -- Check 1: Is user the team/org owner?
    -- ==========================================================================
    IF EXISTS (
        SELECT 1 FROM public.teams 
        WHERE id = org_id 
        AND owner_id = user_uuid
    ) THEN
        RETURN TRUE;
    END IF;
    
    -- ==========================================================================
    -- Check 2: Is user an active team member?
    -- ==========================================================================
    IF EXISTS (
        SELECT 1 FROM public.team_members 
        WHERE team_id = org_id 
        AND member_user_id = user_uuid
        AND status != 'removed'
    ) THEN
        RETURN TRUE;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql 
   SECURITY DEFINER
   SET search_path = public;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.is_org_member(UUID, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_org_member(UUID, UUID) TO service_role;

-- ==========================================================================
-- Step 2: Add comprehensive comment
-- ==========================================================================

COMMENT ON FUNCTION public.is_org_member(UUID, UUID) IS 
'Check if a user is a member of an organization (team).

Returns TRUE if any of the following conditions are met:
1. SOLO USER: org_id = user_uuid (self-ownership for users without teams)
2. TEAM OWNER: User owns the team (teams.owner_id = user_uuid)
3. TEAM MEMBER: User is an active member (team_members with status != removed)

Used by RLS policies on: documents, scope_identities, conversations, ingestion_jobs.

Fixed in 20260221000000 to handle solo users with organization_id = user_id.';

-- ==========================================================================
-- Step 3: Verify the fix by testing edge cases
-- ==========================================================================
-- This DO block verifies the function works correctly. If any assertion fails,
-- the entire transaction rolls back.

DO $$
DECLARE
    v_test_uuid UUID := gen_random_uuid();
    v_different_uuid UUID := gen_random_uuid();
    v_result BOOLEAN;
BEGIN
    -- Test 1: Solo user case (org_id = user_uuid) should return TRUE
    v_result := public.is_org_member(v_test_uuid, v_test_uuid);
    IF NOT v_result THEN
        RAISE EXCEPTION 'ASSERTION FAILED: is_org_member(uuid, uuid) should return TRUE for solo users';
    END IF;
    
    -- Test 2: Different UUIDs with no team should return FALSE
    v_result := public.is_org_member(v_test_uuid, v_different_uuid);
    IF v_result THEN
        RAISE EXCEPTION 'ASSERTION FAILED: is_org_member should return FALSE when user is not a member';
    END IF;
    
    RAISE NOTICE '✅ is_org_member function verified successfully';
END $$;

-- Notify PostgREST to reload schema
NOTIFY pgrst, 'reload config';

COMMIT;
