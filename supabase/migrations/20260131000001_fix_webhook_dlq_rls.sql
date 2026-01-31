-- =============================================================================
-- Migration: Add explicit RLS policy for webhook_dlq
-- Created: 2026-01-31
-- Purpose: Fix Supabase linter warning about RLS enabled without policies
-- 
-- Background:
-- The webhook_dlq table is intentionally backend-only (service_role access).
-- While service_role bypasses RLS by default, adding an explicit policy:
-- 1. Satisfies the Supabase database linter
-- 2. Documents the access intent explicitly
-- 3. Follows security best practice of explicit > implicit
-- =============================================================================

-- Add explicit service_role policy
-- Note: This is technically redundant since service_role bypasses RLS,
-- but it documents intent and satisfies the linter
CREATE POLICY "Service role full access to webhook_dlq"
    ON public.webhook_dlq
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Add comment explaining the RLS strategy
COMMENT ON TABLE public.webhook_dlq IS 
'Dead Letter Queue for webhook events. 
RLS enabled with service_role-only access. 
Frontend accesses this data through backend API endpoints (/dlq/*) which use service_role.
Direct database access by authenticated users is intentionally blocked.';

-- Refresh Supabase Schema Cache
NOTIFY pgrst, 'reload config';
