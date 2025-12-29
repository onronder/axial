-- Migration: Fix Auth Sync Trigger and Secure User Profiles
-- Description: 
-- 1. Automate user_profiles creation when auth.users is populated.
-- 2. Enforce 'free' plan default and NOT NULL constraint.
-- 3. Fix existing orphan users or null plans.

-- TASK 1: Handle User Insert Trigger
-- Create function to handle new user creation
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id, email, plan, role)
    VALUES (
        new.id, 
        new.email, 
        'free', 
        'member'
    )
    ON CONFLICT (user_id) DO NOTHING;
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger the function every time a user is created
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();


-- TASK 2: Schema Security and Backfill
-- 1. Backfill existing NULL plans to 'free' (safe/idempotent)
UPDATE public.user_profiles
SET plan = 'free'
WHERE plan IS NULL;

-- 2. Set default value for plan
ALTER TABLE public.user_profiles
ALTER COLUMN plan SET DEFAULT 'free';

-- 3. Enforce NOT NULL constraint
ALTER TABLE public.user_profiles
ALTER COLUMN plan SET NOT NULL;
