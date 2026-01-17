-- Migration: Sync user_profiles.plan from subscriptions table
-- Issue: user_profiles.plan may be stale if webhook failed to update it
-- Solution: One-time sync to bring user_profiles.plan in line with subscriptions.plan_type
--
-- This ensures consistency between:
-- - subscriptions.plan_type (source of truth, updated by Polar webhooks)
-- - user_profiles.plan (legacy field, used as fallback)

BEGIN;

-- ==========================================================================
-- Sync user_profiles.plan for all team owners with active subscriptions
-- ==========================================================================

-- Update user_profiles.plan to match their team's subscription
UPDATE public.user_profiles up
SET plan = s.plan_type
FROM public.teams t
JOIN public.subscriptions s ON s.team_id = t.id
WHERE up.user_id = t.owner_id
  AND s.status IN ('active', 'trialing')
  AND (up.plan IS DISTINCT FROM s.plan_type);

-- Log the sync (will show in migration output)
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM public.user_profiles up
    JOIN public.teams t ON t.owner_id = up.user_id
    JOIN public.subscriptions s ON s.team_id = t.id
    WHERE s.status IN ('active', 'trialing');
    
    RAISE NOTICE 'Synced user_profiles.plan for % team owners with active subscriptions', v_count;
END $$;

COMMIT;
