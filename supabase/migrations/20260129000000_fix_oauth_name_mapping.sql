-- Migration: Fix OAuth Name Mapping for Google (given_name/family_name)
-- Created: 2026-01-29
-- Description: 
--   1. Updates handle_new_user trigger to support both email signup (first_name/last_name)
--      and OAuth providers like Google (given_name/family_name)
--   2. Backfills existing OAuth users who have NULL or empty names
--   3. Adds ON CONFLICT handling to prevent race conditions

-- TASK 1: Update handle_new_user function to support OAuth metadata formats
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
                    -- Join remaining parts as last name
                    extracted_last_name := array_to_string(full_name_parts[2:], ' ');
                END IF;
            END IF;
        END;
    END IF;

    -- Insert profile with extracted names
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
        'none',  -- Default to no plan (paywall enforced)
        NOW(),
        NOW()
    )
    ON CONFLICT (user_id) DO UPDATE SET
        -- Only update names if they were previously empty and now we have data
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

COMMENT ON FUNCTION public.handle_new_user() IS 
'Creates user profile on signup. Supports both email signup (first_name/last_name) 
and OAuth providers like Google (given_name/family_name). Falls back to parsing 
full_name/name if individual name fields are not available.';


-- TASK 2: Backfill existing OAuth users who have NULL or empty names
-- This updates users whose profiles have empty names but auth.users has name metadata
UPDATE public.user_profiles up
SET 
    first_name = COALESCE(
        NULLIF(up.first_name, ''),
        NULLIF(TRIM(u.raw_user_meta_data->>'first_name'), ''),
        NULLIF(TRIM(u.raw_user_meta_data->>'given_name'), ''),
        CASE 
            WHEN COALESCE(
                NULLIF(TRIM(u.raw_user_meta_data->>'full_name'), ''),
                NULLIF(TRIM(u.raw_user_meta_data->>'name'), '')
            ) IS NOT NULL
            THEN split_part(
                COALESCE(
                    NULLIF(TRIM(u.raw_user_meta_data->>'full_name'), ''),
                    NULLIF(TRIM(u.raw_user_meta_data->>'name'), '')
                ), ' ', 1
            )
            ELSE ''
        END
    ),
    last_name = COALESCE(
        NULLIF(up.last_name, ''),
        NULLIF(TRIM(u.raw_user_meta_data->>'last_name'), ''),
        NULLIF(TRIM(u.raw_user_meta_data->>'family_name'), ''),
        CASE 
            WHEN COALESCE(
                NULLIF(TRIM(u.raw_user_meta_data->>'full_name'), ''),
                NULLIF(TRIM(u.raw_user_meta_data->>'name'), '')
            ) IS NOT NULL
            AND array_length(string_to_array(
                COALESCE(
                    NULLIF(TRIM(u.raw_user_meta_data->>'full_name'), ''),
                    NULLIF(TRIM(u.raw_user_meta_data->>'name'), '')
                ), ' '
            ), 1) > 1
            THEN array_to_string(
                (string_to_array(
                    COALESCE(
                        NULLIF(TRIM(u.raw_user_meta_data->>'full_name'), ''),
                        NULLIF(TRIM(u.raw_user_meta_data->>'name'), '')
                    ), ' '
                ))[2:], ' '
            )
            ELSE ''
        END
    ),
    updated_at = NOW()
FROM auth.users u
WHERE up.user_id = u.id
  AND (
      COALESCE(TRIM(up.first_name), '') = '' 
      OR COALESCE(TRIM(up.last_name), '') = ''
  )
  AND (
      u.raw_user_meta_data->>'first_name' IS NOT NULL
      OR u.raw_user_meta_data->>'given_name' IS NOT NULL
      OR u.raw_user_meta_data->>'last_name' IS NOT NULL
      OR u.raw_user_meta_data->>'family_name' IS NOT NULL
      OR u.raw_user_meta_data->>'full_name' IS NOT NULL
      OR u.raw_user_meta_data->>'name' IS NOT NULL
  );

-- Log the migration
DO $$
BEGIN
    RAISE NOTICE 'OAuth name mapping migration completed successfully';
END $$;
