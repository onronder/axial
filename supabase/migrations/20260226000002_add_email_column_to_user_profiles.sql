-- =============================================================================
-- Add Missing Email Column to user_profiles
-- =============================================================================
-- Issue: handle_new_user trigger references email column that doesn't exist
-- Error: "column "email" of relation "user_profiles" does not exist"
-- 
-- This migration:
-- 1. Adds the email column to user_profiles
-- 2. Backfills existing users with their email from auth.users
-- =============================================================================

-- Step 1: Add email column if it doesn't exist
ALTER TABLE public.user_profiles 
ADD COLUMN IF NOT EXISTS email TEXT;

-- Step 2: Backfill existing users with their email from auth.users
UPDATE public.user_profiles up
SET email = u.email
FROM auth.users u
WHERE up.user_id = u.id
  AND (up.email IS NULL OR up.email = '');

-- Step 3: Create index for email lookups (optional but useful)
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON public.user_profiles(email);

-- Log success
DO $$
BEGIN
    RAISE NOTICE 'Email column added to user_profiles and backfilled successfully';
END $$;
