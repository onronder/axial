-- =============================================================================
-- Migration: Fix get_effective_plan Parameter Name (ISSUE-001)
-- =============================================================================
--
-- PROBLEM:
-- The get_effective_plan function expects parameter named 'target_user_id'
-- but backend code sends 'p_user_id'. PostgreSQL RPC calls via PostgREST
-- require exact parameter name matching.
--
-- SOLUTION:
-- Recreate the function with parameter name 'p_user_id' to match what the
-- backend sends. The function logic remains identical.
--
-- This is the preferred fix because:
-- 1. Less code changes needed (only migration, not backend)
-- 2. Consistent with other functions (get_user_team_data uses p_user_id)
-- 3. No cache invalidation concerns in backend
-- =============================================================================

BEGIN;

-- ==========================================================================
-- Step 1: Drop existing function to avoid signature conflicts
-- ==========================================================================

DROP FUNCTION IF EXISTS public.get_effective_plan(UUID);

-- ==========================================================================
-- Step 2: Recreate with correct parameter name (p_user_id)
-- ==========================================================================

CREATE OR REPLACE FUNCTION public.get_effective_plan(p_user_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_team_id UUID;
    v_plan TEXT;
BEGIN
    -- ==========================================================================
    -- Step 1: Find user's team via team_members
    -- ==========================================================================
    SELECT tm.team_id INTO v_team_id
    FROM public.team_members tm
    WHERE tm.member_user_id = p_user_id
      AND tm.status != 'removed'
    LIMIT 1;
    
    -- ==========================================================================
    -- Step 2: If user has a team, check subscriptions table (source of truth)
    -- ==========================================================================
    IF v_team_id IS NOT NULL THEN
        SELECT s.plan_type INTO v_plan
        FROM public.subscriptions s
        WHERE s.team_id = v_team_id
          AND s.status IN ('active', 'trialing')
        ORDER BY s.created_at DESC
        LIMIT 1;
        
        IF v_plan IS NOT NULL THEN
            RETURN v_plan;
        END IF;
    END IF;
    
    -- ==========================================================================
    -- Step 3: Fallback - Check if user owns a team with subscription
    -- ==========================================================================
    SELECT t.id INTO v_team_id
    FROM public.teams t
    WHERE t.owner_id = p_user_id
    LIMIT 1;
    
    IF v_team_id IS NOT NULL THEN
        SELECT s.plan_type INTO v_plan
        FROM public.subscriptions s
        WHERE s.team_id = v_team_id
          AND s.status IN ('active', 'trialing')
        ORDER BY s.created_at DESC
        LIMIT 1;
        
        IF v_plan IS NOT NULL THEN
            RETURN v_plan;
        END IF;
    END IF;
    
    -- ==========================================================================
    -- Step 4: Fallback to user_profiles.plan (for legacy/solo users)
    -- ==========================================================================
    SELECT up.plan INTO v_plan
    FROM public.user_profiles up
    WHERE up.user_id = p_user_id;
    
    -- ==========================================================================
    -- Step 5: Default to 'free' if nothing found
    -- ==========================================================================
    RETURN COALESCE(v_plan, 'free');
END;
$$;

-- ==========================================================================
-- Step 3: Grant permissions
-- ==========================================================================

GRANT EXECUTE ON FUNCTION public.get_effective_plan(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_effective_plan(UUID) TO service_role;

-- ==========================================================================
-- Step 4: Add documentation
-- ==========================================================================

COMMENT ON FUNCTION public.get_effective_plan(UUID) IS 
'Returns the effective plan for a user.

Priority:
1. Subscription from user''s team membership (team_members → subscriptions)
2. Subscription from owned team (teams → subscriptions)  
3. user_profiles.plan (legacy fallback)
4. ''free'' (default)

Parameter: p_user_id UUID - The user''s auth.users.id

Fixed in 20260221000001 to use correct parameter name (p_user_id) matching backend calls.';

-- ==========================================================================
-- Step 5: Verify function works
-- ==========================================================================

DO $$
DECLARE
    v_test_result TEXT;
BEGIN
    -- Call with random UUID should return 'free' (no subscription)
    v_test_result := public.get_effective_plan(gen_random_uuid());
    IF v_test_result IS NULL OR v_test_result = '' THEN
        RAISE EXCEPTION 'ASSERTION FAILED: get_effective_plan should return a non-empty string';
    END IF;
    IF v_test_result != 'free' THEN
        RAISE WARNING 'get_effective_plan returned % for unknown user (expected free)', v_test_result;
    END IF;
    
    RAISE NOTICE '✅ get_effective_plan function verified (returned: %)', v_test_result;
END $$;

-- Notify PostgREST to reload schema
NOTIFY pgrst, 'reload config';

COMMIT;
