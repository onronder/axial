-- Phase 2 Step 1: High-Perception Quotas
-- - Add org_usage table for per-tenant consumption tracking
-- - Ensure teams.plan exists with default 'starter'

-- 1) teams.plan column (default starter)
ALTER TABLE IF EXISTS public.teams
    ADD COLUMN IF NOT EXISTS plan TEXT DEFAULT 'starter';

UPDATE public.teams
SET plan = COALESCE(plan, 'starter');

-- 2) org_usage table
CREATE TABLE IF NOT EXISTS public.org_usage (
    org_id UUID PRIMARY KEY REFERENCES public.teams(id) ON DELETE CASCADE,
    storage_used_mb NUMERIC(20, 2) DEFAULT 0 NOT NULL,
    job_count_cycle INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_org_usage_updated_at ON public.org_usage(updated_at);

ALTER TABLE public.org_usage ENABLE ROW LEVEL SECURITY;

-- Allow service_role full access
DROP POLICY IF EXISTS "Service role full access to org_usage" ON public.org_usage;
CREATE POLICY "Service role full access to org_usage"
ON public.org_usage FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Team members/owners can read their org usage (no writes)
DROP POLICY IF EXISTS "Team read org_usage" ON public.org_usage;
CREATE POLICY "Team read org_usage"
ON public.org_usage FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.teams t
        WHERE t.id = org_usage.org_id
        AND (
            t.owner_id = (SELECT auth.uid())
            OR EXISTS (
                SELECT 1 FROM public.team_members tm
                WHERE tm.team_id = t.id
                AND tm.member_user_id = (SELECT auth.uid())
            )
        )
    )
);

COMMENT ON TABLE public.org_usage IS 'Per-tenant usage counters for quotas (storage, job cycle counts).';
