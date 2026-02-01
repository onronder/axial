-- =============================================================================
-- Fix Plan Check Constraint to Allow 'none'
-- =============================================================================
-- Issue: handle_new_user trigger inserts plan='none' for paywall enforcement,
--        but the CHECK constraint only allows ('free', 'pro', 'enterprise')
-- Error: "violates check constraint user_profiles_plan_check"
-- 
-- Solution: Update the CHECK constraint to include 'none' and 'starter'
-- =============================================================================

-- Step 1: Drop the existing check constraint
ALTER TABLE public.user_profiles 
DROP CONSTRAINT IF EXISTS user_profiles_plan_check;

-- Step 2: Add the updated check constraint with all valid plan values
ALTER TABLE public.user_profiles 
ADD CONSTRAINT user_profiles_plan_check 
CHECK (plan IN ('none', 'free', 'starter', 'pro', 'enterprise'));

-- Log success
DO $$
BEGIN
    RAISE NOTICE 'Plan check constraint updated to include none and starter';
END $$;
