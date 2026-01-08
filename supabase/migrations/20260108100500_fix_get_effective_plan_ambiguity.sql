-- Fix get_effective_plan ambiguity by renaming variables

CREATE OR REPLACE FUNCTION public.get_effective_plan(target_user_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    v_team_id UUID;
    v_sub_status TEXT;
    v_sub_plan TEXT;
    v_owner_plan TEXT;
    v_own_plan TEXT;
BEGIN
    -- Find the user's team (ignore removed members)
    SELECT tm.team_id INTO v_team_id
    FROM team_members tm
    WHERE tm.member_user_id = target_user_id
      AND (tm.status IS NULL OR tm.status != 'removed')
    LIMIT 1;

    IF v_team_id IS NOT NULL THEN
        -- Prefer subscription record for the team
        SELECT s.status, s.plan_type INTO v_sub_status, v_sub_plan
        FROM subscriptions s
        WHERE s.team_id = v_team_id
        LIMIT 1;

        IF v_sub_status = 'active' THEN
            RETURN COALESCE(v_sub_plan, 'free');
        ELSIF v_sub_status = 'trialing' THEN
            RETURN COALESCE(v_sub_plan, 'free');
        ELSIF v_sub_status = 'canceled' THEN
            RETURN 'free';
        END IF;

        -- Fallback to team owner's profile plan
        SELECT up.plan INTO v_owner_plan
        FROM teams t
        JOIN user_profiles up ON up.user_id = t.owner_id
        WHERE t.id = v_team_id
        LIMIT 1;

        IF v_owner_plan IS NOT NULL THEN
            RETURN v_owner_plan;
        END IF;
    END IF;

    -- Final fallback: user's own profile plan
    SELECT plan INTO v_own_plan
    FROM user_profiles
    WHERE user_id = target_user_id;

    RETURN COALESCE(v_own_plan, 'free');
END;
$$;

ALTER FUNCTION public.get_effective_plan(UUID) SET search_path = public;

GRANT EXECUTE ON FUNCTION public.get_effective_plan(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_effective_plan(UUID) TO service_role;

COMMENT ON FUNCTION public.get_effective_plan(UUID) IS
    'Returns effective plan with subscriptions as source of truth (team -> subscription -> owner plan -> user plan).';
