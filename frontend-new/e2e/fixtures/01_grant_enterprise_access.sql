-- ============================================================
-- ARTIFACT 1: "God Mode" Enterprise Access Injection
-- ============================================================
-- Purpose: Force a test user into Enterprise plan without payment
-- Usage: Run in Supabase SQL Editor (with service role)
--
-- IMPORTANT: Replace 'admin@axial-test.com' with your actual test user email
-- ============================================================

DO $$
DECLARE
    v_user_email TEXT := 'o.onder@fittechs.com';  -- <<< CHANGE THIS
    v_user_id UUID;
    v_team_id UUID;
    v_polar_id TEXT;
BEGIN
    -- Step 1: Get user_id from auth.users
    SELECT id INTO v_user_id
    FROM auth.users
    WHERE email = v_user_email;
    
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'User not found: %', v_user_email;
    END IF;
    
    RAISE NOTICE 'Found user: % (ID: %)', v_user_email, v_user_id;
    
    -- Step 2: Get team_id (user should own exactly one team)
    SELECT id INTO v_team_id
    FROM public.teams
    WHERE owner_id = v_user_id;
    
    IF v_team_id IS NULL THEN
        RAISE EXCEPTION 'Team not found for user: %', v_user_email;
    END IF;
    
    RAISE NOTICE 'Found team: %', v_team_id;
    
    -- Step 3: Generate a unique test polar_id
    v_polar_id := 'test_polar_enterprise_' || gen_random_uuid()::text;
    
    -- Step 4: UPSERT subscription with Enterprise plan
    INSERT INTO public.subscriptions (
        team_id,
        polar_id,
        status,
        plan_type,
        seats,
        current_period_end,
        cancel_at_period_end,
        created_at,
        updated_at
    ) VALUES (
        v_team_id,
        v_polar_id,
        'active',
        'enterprise',
        100,  -- Generous seat count
        NOW() + INTERVAL '1 year',  -- Valid for 1 year
        false,
        NOW(),
        NOW()
    )
    ON CONFLICT (team_id) DO UPDATE SET
        status = 'active',
        plan_type = 'enterprise',
        seats = 100,
        current_period_end = NOW() + INTERVAL '1 year',
        cancel_at_period_end = false,
        updated_at = NOW();
    
    RAISE NOTICE '✅ SUCCESS: User % now has Enterprise access', v_user_email;
    RAISE NOTICE '   Team ID: %', v_team_id;
    RAISE NOTICE '   Polar ID: %', v_polar_id;
    RAISE NOTICE '   Plan: enterprise (active)';
    RAISE NOTICE '   Seats: 100';
    RAISE NOTICE '   Expires: % (1 year from now)', NOW() + INTERVAL '1 year';
END $$;

-- Verification query: Check the subscription was created
SELECT 
    t.name AS team_name,
    u.email AS owner_email,
    s.plan_type,
    s.status,
    s.seats,
    s.current_period_end
FROM public.subscriptions s
JOIN public.teams t ON t.id = s.team_id
JOIN auth.users u ON u.id = t.owner_id
WHERE u.email = 'o.onder@fittechs.com';  -- <<< CHANGE THIS TO MATCH
