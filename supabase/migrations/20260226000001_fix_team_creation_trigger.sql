-- =============================================================================
-- Fix Team Creation Trigger for OAuth Users
-- =============================================================================
-- Issue: create_personal_team trigger may fail on new user signup
-- This makes the trigger more robust with error handling and ON CONFLICT
-- =============================================================================

-- Update create_personal_team function with better error handling
CREATE OR REPLACE FUNCTION create_personal_team()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    new_team_id UUID;
    user_email TEXT;
    team_name TEXT;
    existing_team_id UUID;
BEGIN
    -- Get user's email for team name
    user_email := NEW.email;
    team_name := COALESCE(
        split_part(user_email, '@', 1) || '''s Team',
        'Personal Team'
    );
    
    -- Check if team already exists for this user (idempotency)
    SELECT id INTO existing_team_id FROM teams WHERE owner_id = NEW.id;
    
    IF existing_team_id IS NOT NULL THEN
        -- Team already exists, skip creation
        RETURN NEW;
    END IF;
    
    -- Create the team
    INSERT INTO teams (name, owner_id, created_at, updated_at)
    VALUES (team_name, NEW.id, now(), now())
    ON CONFLICT (owner_id) DO NOTHING
    RETURNING id INTO new_team_id;
    
    -- If insert was skipped due to conflict, get the existing team
    IF new_team_id IS NULL THEN
        SELECT id INTO new_team_id FROM teams WHERE owner_id = NEW.id;
    END IF;
    
    -- Only create team_member if we have a team_id
    IF new_team_id IS NOT NULL THEN
        -- Add user as admin member of their own team
        INSERT INTO team_members (
            team_id,
            owner_user_id,
            member_user_id,
            email,
            name,
            role,
            status,
            joined_at,
            created_at
        ) VALUES (
            new_team_id,
            NEW.id,
            NEW.id,
            user_email,
            split_part(user_email, '@', 1),
            'admin',
            'active',
            now(),
            now()
        )
        ON CONFLICT DO NOTHING;
    END IF;
    
    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        -- Log error but don't fail user creation
        RAISE WARNING 'create_personal_team failed for user %: %', NEW.id, SQLERRM;
        RETURN NEW;
END;
$$;

-- Ensure trigger exists
DROP TRIGGER IF EXISTS on_auth_user_created_create_team ON auth.users;
CREATE TRIGGER on_auth_user_created_create_team
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION create_personal_team();

COMMENT ON FUNCTION create_personal_team IS 
'Auto-creates personal team when user signs up. Handles duplicates gracefully.';
