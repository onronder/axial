-- ============================================================================
-- Migration: Fix Supabase Advisor Security & Performance Findings
-- Date: 2026-01-12
-- Items addressed:
--   1) audit_logs INSERT policy too permissive (WITH CHECK true)
--   2) Service role policies scoped to specific role to avoid multiple permissive policies
--   3) Add covering index for ingestion_jobs.cancelled_by FK
-- ============================================================================

-- 1) Tighten audit_logs INSERT policy to service_role only
DROP POLICY IF EXISTS "Service role can insert audit logs" ON public.audit_logs;
CREATE POLICY "Service role can insert audit logs"
    ON public.audit_logs
    FOR INSERT
    TO service_role
    WITH CHECK (auth.role() = 'service_role');

-- 2) Scope service-role policies to the service_role role
-- failed_tasks
DROP POLICY IF EXISTS "Service role full access to failed_tasks" ON public.failed_tasks;
CREATE POLICY "Service role full access to failed_tasks"
    ON public.failed_tasks
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ingestion_file_status
DROP POLICY IF EXISTS "Service role full access" ON public.ingestion_file_status;
CREATE POLICY "Service role full access"
    ON public.ingestion_file_status
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 3) Add covering index for cancelled_by FK on ingestion_jobs
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_cancelled_by
    ON public.ingestion_jobs(cancelled_by);

-- Notify PostgREST to reload
NOTIFY pgrst, 'reload config';
