-- Migration: Add 'viewer' role and subscriptions support (20251230)
-- Description: Updates team_members role check constraint and ensures subscriptions support.

BEGIN;

-- 1. Update team_members role check constraint
-- Safe way to update check constraint without downtime
ALTER TABLE public.team_members DROP CONSTRAINT IF EXISTS team_members_role_check;

ALTER TABLE public.team_members 
    ADD CONSTRAINT team_members_role_check 
    CHECK (role IN ('owner', 'admin', 'member', 'viewer'));

-- 2. Ensure subscriptions table exists (Idempotent)
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan_type TEXT NOT NULL DEFAULT 'free', -- 'free', 'starter', 'pro', 'enterprise'
    status TEXT NOT NULL DEFAULT 'active',
    polar_subscription_id TEXT, -- External ID from Polar.sh
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure one active subscription per user (optional, depending on biz logic)
    UNIQUE(user_id)
);

-- 3. Sync plan from user_profiles if missing (Data Backfill)
-- If we previously stored plan in user_profiles, we might want to sync it here,
-- or treat user_profiles.plan as the source of truth for simple cases.
-- For now, we assume user_profiles.plan is the master switch for logic.

COMMIT;
