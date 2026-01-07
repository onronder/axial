-- Migration: Update get_effective_plan to use subscriptions as source of truth
-- Timestamp: 2026-01-07

CREATE OR REPLACE FUNCTION public.get_effective_plan(target_user_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    team_id UUID;
    sub_status TEXT;
    sub_plan TEXT;
    owner_plan TEXT;
    own_plan TEXT;
BEGIN
    -- Find the user's team (ignore removed members)
    SELECT tm.team_id INTO team_id
    FROM team_members tm
    WHERE tm.member_user_id = target_user_id
      AND (tm.status IS NULL OR tm.status != 'removed')
    LIMIT 1;

    IF team_id IS NOT NULL THEN
        -- Prefer subscription record for the team
        SELECT s.status, s.plan_type INTO sub_status, sub_plan
        FROM subscriptions s
        WHERE s.team_id = team_id
        LIMIT 1;

        IF sub_status = 'active' THEN
            RETURN COALESCE(sub_plan, 'free');
        ELSIF sub_status = 'trialing' THEN
            RETURN COALESCE(sub_plan, 'free');
        ELSIF sub_status = 'canceled' THEN
            RETURN 'free';
        END IF;

        -- Fallback to team owner's profile plan
        SELECT up.plan INTO owner_plan
        FROM teams t
        JOIN user_profiles up ON up.user_id = t.owner_id
        WHERE t.id = team_id
        LIMIT 1;

        IF owner_plan IS NOT NULL THEN
            RETURN owner_plan;
        END IF;
    END IF;

    -- Final fallback: user's own profile plan
    SELECT plan INTO own_plan
    FROM user_profiles
    WHERE user_id = target_user_id;

    RETURN COALESCE(own_plan, 'free');
END;
$$;

ALTER FUNCTION public.get_effective_plan(UUID) SET search_path = public;

GRANT EXECUTE ON FUNCTION public.get_effective_plan(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_effective_plan(UUID) TO service_role;

COMMENT ON FUNCTION public.get_effective_plan(UUID) IS
    'Returns effective plan with subscriptions as source of truth (team -> subscription -> owner plan -> user plan).';
