-- Migration: Fix get_effective_plan() function (v3)
-- Issue: Migration 20260216160000 re-introduced reference to subscription_status column
--        that was removed from user_profiles in 20251231130000
-- Solution: Use subscriptions table as source of truth, fall back to user_profiles.plan
--
-- Architecture:
-- 1. Check subscriptions table (team-based, updated by Polar webhooks)
-- 2. Fall back to user_profiles.plan (legacy/solo users)
-- 3. Default to 'free' if nothing found
--
-- History:
-- - 20251227154700: Added subscription_status to user_profiles
-- - 20251231130000: REMOVED subscription_status (moved to subscriptions table)
-- - 20260216160000: Re-introduced bug (referenced removed column)
-- - 20260220000000: THIS MIGRATION - Final fix

BEGIN;

-- ==========================================================================
-- Fix: get_effective_plan - Use subscriptions table instead of user_profiles.subscription_status
-- ==========================================================================

CREATE OR REPLACE FUNCTION public.get_effective_plan(target_user_id UUID)
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
    -- Step 1: Find user's team via team_members
    SELECT tm.team_id INTO v_team_id
    FROM public.team_members tm
    WHERE tm.member_user_id = target_user_id
      AND tm.status != 'removed'
    LIMIT 1;
    
    -- Step 2: If user has a team, check subscriptions table (source of truth)
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
    
    -- Step 3: Fallback to user_profiles.plan (for legacy/solo users without team subscription)
    SELECT up.plan INTO v_plan
    FROM public.user_profiles up
    WHERE up.user_id = target_user_id;
    
    -- Step 4: Default to 'free' if nothing found
    RETURN COALESCE(v_plan, 'free');
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.get_effective_plan(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_effective_plan(UUID) TO service_role;

COMMENT ON FUNCTION public.get_effective_plan(UUID) IS 
'Returns the effective plan for a user. Priority: subscriptions table > user_profiles.plan > free. 
Fixed in 20260220000000 to use correct billing schema.';

NOTIFY pgrst, 'reload config';

COMMIT;
