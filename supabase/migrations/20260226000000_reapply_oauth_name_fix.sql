-- =============================================================================
-- Re-apply OAuth Name Mapping Fix
-- =============================================================================
-- Issue: Migration 20260129000000 was recorded but trigger not actually updated
-- This re-applies the handle_new_user function to support OAuth providers
-- 
-- Fixes: "Database error saving new user" on Google OAuth login
-- =============================================================================

-- Update handle_new_user function to support OAuth metadata formats
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    extracted_first_name TEXT;
    extracted_last_name TEXT;
    full_name_parts TEXT[];
BEGIN
    -- Extract first name: try email signup fields first, then OAuth fields
    extracted_first_name := COALESCE(
        NULLIF(TRIM(new.raw_user_meta_data->>'first_name'), ''),
        NULLIF(TRIM(new.raw_user_meta_data->>'given_name'), ''),
        NULL
    );
    
    -- Extract last name: try email signup fields first, then OAuth fields
    extracted_last_name := COALESCE(
        NULLIF(TRIM(new.raw_user_meta_data->>'last_name'), ''),
        NULLIF(TRIM(new.raw_user_meta_data->>'family_name'), ''),
        NULL
    );
    
    -- Fallback: If we only have full_name/name, try to split it
    IF extracted_first_name IS NULL AND extracted_last_name IS NULL THEN
        DECLARE
            full_name TEXT := COALESCE(
                NULLIF(TRIM(new.raw_user_meta_data->>'full_name'), ''),
                NULLIF(TRIM(new.raw_user_meta_data->>'name'), ''),
                NULL
            );
        BEGIN
            IF full_name IS NOT NULL THEN
                full_name_parts := string_to_array(full_name, ' ');
                IF array_length(full_name_parts, 1) >= 1 THEN
                    extracted_first_name := full_name_parts[1];
                END IF;
                IF array_length(full_name_parts, 1) >= 2 THEN
                    extracted_last_name := array_to_string(full_name_parts[2:], ' ');
                END IF;
            END IF;
        END;
    END IF;

    -- Insert profile with extracted names (NO subscription_status - moved to subscriptions table)
    INSERT INTO public.user_profiles (
        user_id,
        email,
        first_name,
        last_name,
        plan,
        created_at,
        updated_at
    )
    VALUES (
        new.id,
        new.email,
        COALESCE(extracted_first_name, ''),
        COALESCE(extracted_last_name, ''),
        'none',
        NOW(),
        NOW()
    )
    ON CONFLICT (user_id) DO UPDATE SET
        first_name = CASE 
            WHEN COALESCE(TRIM(user_profiles.first_name), '') = '' 
            THEN COALESCE(extracted_first_name, user_profiles.first_name, '')
            ELSE user_profiles.first_name
        END,
        last_name = CASE 
            WHEN COALESCE(TRIM(user_profiles.last_name), '') = '' 
            THEN COALESCE(extracted_last_name, user_profiles.last_name, '')
            ELSE user_profiles.last_name
        END,
        updated_at = NOW();
    
    RETURN new;
END;
$$;

-- Ensure trigger exists and is properly attached
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

COMMENT ON FUNCTION public.handle_new_user() IS 
'Creates user profile on signup. Supports both email signup (first_name/last_name) 
and OAuth providers like Google (given_name/family_name).';
