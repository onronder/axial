-- Migration: Org-scoped ingestion_file_status

BEGIN;

ALTER TABLE public.ingestion_file_status
ADD COLUMN IF NOT EXISTS organization_id UUID;

-- Backfill organization_id from parent jobs
UPDATE public.ingestion_file_status f
SET organization_id = j.organization_id
FROM public.ingestion_jobs j
WHERE f.job_id = j.id
  AND f.organization_id IS NULL;

-- Fallback to active team memberships
UPDATE public.ingestion_file_status f
SET organization_id = tm.team_id
FROM public.team_members tm
WHERE tm.member_user_id = f.user_id
  AND tm.status != 'removed'
  AND f.organization_id IS NULL;

-- Fallback to team ownership
UPDATE public.ingestion_file_status f
SET organization_id = t.id
FROM public.teams t
WHERE t.owner_id = f.user_id
  AND f.organization_id IS NULL;

-- Final fallback to avoid NULLs
UPDATE public.ingestion_file_status
SET organization_id = user_id
WHERE organization_id IS NULL;

ALTER TABLE public.ingestion_file_status
ALTER COLUMN organization_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ingestion_file_status_org_status
ON public.ingestion_file_status(organization_id, status);

-- Refresh RLS policies for org-scoped access
DROP POLICY IF EXISTS "Users can view own file status" ON public.ingestion_file_status;
DROP POLICY IF EXISTS "Service role full access" ON public.ingestion_file_status;
DROP POLICY IF EXISTS "Service role can manage file status" ON public.ingestion_file_status;

CREATE POLICY "ingestion_file_status_select_org"
ON public.ingestion_file_status FOR SELECT
USING (
    public.is_org_member(organization_id, (SELECT auth.uid()))
);

CREATE POLICY "ingestion_file_status_service_role"
ON public.ingestion_file_status FOR ALL
USING ((SELECT auth.role()) = 'service_role')
WITH CHECK ((SELECT auth.role()) = 'service_role');

COMMIT;
